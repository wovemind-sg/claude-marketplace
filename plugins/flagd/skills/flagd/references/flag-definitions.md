# flagd Flag Definitions — Reference

Source of truth: flagd repo `docs/` (rendered at https://flagd.dev) at commit `b13483f` (2026-09-18) plus hosted schemas `https://flagd.dev/schema/v0/flags.json` and `.../targeting.json` fetched 2026-09-21. Behaviour notes marked *(source)* were verified against `core/pkg/evaluator/json.go` in the same commit.

## Contents

1. File formats, naming, schema URLs
2. Top-level structure
3. Flag fields
4. Flag types
5. Evaluation algorithm, reasons, error codes
6. Targeting: JSON Logic basics, `var`, reserved context
7. Standard operators
8. Custom operations: `fractional`, `sem_ver`, `starts_with`/`ends_with`
9. `$evaluators` and `$ref`
10. Metadata (flag set, flag, variant/rule-level)
11. Disabled flags and code defaults
12. Numeric coercion
13. Multiple sources, duplicate keys, flag sets
14. Complete examples
15. Debug checklist

---

## 1. File formats, naming, schema URLs

- Formats: JSON or YAML. The `file`, `http`, `gcs`, `azblob`, `s3` syncs pick the parser from the file extension; if there is no extension, the HTTP media type is used.
- Name files `*.flagd.json` / `*.flagd.yaml` (flagd's own samples use this). The suffix is what SchemaStore-aware editors match to the flagd schema, giving autocompletion without any config. Works with plain `.json`/`.yaml` too if you add the `$schema` key.
- JSON: add `"$schema": "https://flagd.dev/schema/v0/flags.json"` as the first key. flagd ignores it at runtime; editors use it.
- YAML: add a first-line comment `# yaml-language-server: $schema=https://flagd.dev/schema/v0/flags.json`. Quote `'on'`/`'off'` in YAML — unquoted they parse as booleans and break variant keys.
- Schemas (JSON Schema draft-07):
  - `https://flagd.dev/schema/v0/flags.json` — whole file (map-form `flags`). Also validates each `targeting`.
  - `https://flagd.dev/schema/v0/flags.json#/definitions/flagdConfig` — daemon superset that also allows array-form `flags` (see §13).
  - `https://flagd.dev/schema/v0/targeting.json` — a single `targeting` value only.
  - `https://flagd.dev/schema/v0/flagd.json` — shape of what flagd *returns* from its sync API (wraps `flagdConfig`).
- Validate offline with any draft-07 validator (ajv, python-jsonschema). `targeting.json` is referenced relatively (`./targeting.json`), so when validating locally keep both files in one directory.

Source: https://flagd.dev/reference/schema/ , https://flagd.dev/reference/sync-configuration/

## 2. Top-level structure

```jsonc
{
  "$schema": "https://flagd.dev/schema/v0/flags.json", // optional, editor-only
  "flags": { "<flagKey>": { /* flag */ } },            // REQUIRED. Object keyed by flag key (min length 1)
  "$evaluators": { "<name>": { /* JSON Logic */ } },   // optional shared rules, referenced via {"$ref": "<name>"}
  "metadata": { "flagSetId": "…", "version": "…", "<any>": "string|number|boolean" } // optional flag-set metadata
}
```

- `flags` is required and must contain valid flags; unknown top-level keys are allowed by the schema but ignored.
- Flag keys: any non-empty string; must be unique within a flag set. Convention: kebab-case, intent-revealing (`new-welcome-banner`).
- `metadata` values must be scalar (`string | number | boolean`) — no nested objects/arrays. `flagSetId` and `version` are the only schema-declared keys; any other key is allowed.

Source: https://flagd.dev/reference/flag-definitions/

## 3. Flag fields

| Field | Type | Required | Rules |
|---|---|---|---|
| `state` | `"ENABLED" \| "DISABLED"` | yes | `DISABLED` short-circuits evaluation: no targeting, no value/variant returned, `reason=DISABLED` (§11). |
| `variants` | object, ≥1 entry | yes | Keys are variant names (non-empty strings). **All values must be the same JSON type** (all boolean, all string, all number, or all object). Mixed types fail schema validation. |
| `defaultVariant` | string or `null` | no | If a string, **must name a key in `variants`** (schema cannot check this; flagd errors at evaluation). If `null` or omitted → flagd returns no value and `reason=DEFAULT`, the SDK uses the code default (§11). |
| `targeting` | JSON Logic object | no | `{}` or omitted = static flag (`reason=STATIC`, cacheable). Must return a variant name, `true`/`false`, `null`, or (future) a tagged object (§10). |
| `metadata` | object of scalars | no | Merged over flag-set metadata; flag wins on key collision. |

Array-form flags (daemon only, §13) add a required `key` string to each flag object.

Source: https://flagd.dev/reference/flag-definitions/

## 4. Flag types

The variant value type decides which resolver a client must call. Calling the wrong one → `reason=ERROR`, `errorCode=TYPE_MISMATCH`.

| Type | `variants` values | Resolver (gRPC/HTTP) | OpenFeature accessor |
|---|---|---|---|
| boolean | `true` / `false` | `ResolveBoolean` | `getBooleanValue` |
| string | strings | `ResolveString` | `getStringValue` |
| number | JSON numbers (int or float) | `ResolveInt` / `ResolveFloat` | `getIntegerValue` / `getDoubleValue` (§12) |
| object | JSON objects | `ResolveObject` | `getObjectValue` |

Note: over the HTTP gateway, `ResolveInt` returns the value as a JSON *string* (`"value":"1"`) due to proto3 JSON mapping of int64. Use `ResolveFloat` if you need a JSON number from curl.

Source: https://flagd.dev/reference/flag-definitions/ , https://flagd.dev/troubleshooting/

## 5. Evaluation algorithm, reasons, error codes

Order of operations for one flag *(source)*:

1. Look up `(flagKey, flagSetId)` in the store. Missing → `reason=ERROR`, `errorCode=FLAG_NOT_FOUND`.
2. Merge flag-set metadata, then flag metadata (flag wins).
3. `state == DISABLED` → return `reason=DISABLED`, no `value`, no `variant`, metadata included. Stop.
4. No `targeting` (or `{}`):
   - `defaultVariant` set → `reason=STATIC`, `variant=defaultVariant`, `value=variants[defaultVariant]`.
   - `defaultVariant` null/omitted → `reason=DEFAULT`, no value/variant (code default).
5. `targeting` present: inject `$flagd.flagKey` and `$flagd.timestamp` into a copy of the context, run JSON Logic.
   - Rule error / unparseable → `reason=ERROR`, `errorCode=PARSE_ERROR`.
   - Result `null` → `defaultVariant` set: `reason=DEFAULT`, `variant=defaultVariant`. Not set: `reason=DEFAULT`, no value/variant.
   - Result string (or `true`/`false`, converted to `"true"`/`"false"`) that **is** a key in `variants` → `reason=TARGETING_MATCH`.
   - Result is anything else (string not in `variants`, number, array, object) → `reason=ERROR`, `errorCode=GENERAL` ("invalid or missing variant"). Numbers and arrays are explicitly "behaviour undefined" in the schema — never return them.
6. Cast the chosen variant's value to the requested type; mismatch → `reason=ERROR`, `errorCode=TYPE_MISMATCH`.

Reasons you will see on the wire: `STATIC`, `TARGETING_MATCH`, `DEFAULT`, `DISABLED`, `ERROR`. Also defined: `SPLIT` (OpenFeature reason some providers use for fractional), `UNKNOWN`. Internally flagd uses `FALLBACK` for the code-default path and rewrites it to `DEFAULT` on gRPC v2 and OFREP *(source)*.

Error codes: `FLAG_NOT_FOUND`, `PARSE_ERROR`, `TYPE_MISMATCH`, `GENERAL`. `FLAG_DISABLED` existed in old releases; the accepted ADR removes it in favour of `reason=DISABLED`. Old gRPC v1 clients may still see `FLAG_NOT_FOUND` for `defaultVariant: null` flags *(source: `ProtoVersionKey` branch)*.

Caching: RPC providers cache only `reason=STATIC` results. Adding any `targeting` (even one that always returns `null`) disables caching for that flag.

Source: https://flagd.dev/reference/flag-definitions/ , https://flagd.dev/reference/specifications/providers/

## 6. Targeting: JSON Logic basics, `var`, reserved context

flagd evaluates `targeting` with a modified [JsonLogic](https://jsonlogic.com) engine plus pre-processing (`$ref` inlining, `$flagd.*` injection). Every rule is `{"<operator>": [args…]}`; args may be literals or nested rules. Operators never throw: bad input yields `null`/`false`, which in an `if` falls through to the else branch.

`var`:

| Form | Meaning |
|---|---|
| `{"var": "email"}` | context property; `null` if missing |
| `{"var": "user.email"}` | dotted path into nested context object |
| `{"var": ["email", "nobody@x.com"]}` | with default when missing/null |
| `{"var": ""}` | the whole context object |

Property names are **case-sensitive**.

Reserved / injected context keys:

| Key | Value |
|---|---|
| `targetingKey` | OpenFeature targeting key from the SDK call. Default bucketing input for `fractional`. |
| `$flagd.flagKey` | key of the flag being evaluated (v0.6.4+) |
| `$flagd.timestamp` | Unix epoch **seconds** at evaluation time (v0.6.7+) |

Only `$flagd.flagKey` and `$flagd.timestamp` are valid `$flagd.*` names — the schema rejects any other `$flagd.` var.

Context sources (daemon), merged highest-priority-first: header-mapped (`-H "X-User-Tier=tier"`) > static (`-X region=eu`) > request body. In-process providers additionally inject sync-metadata properties.

Return values: a **string** (variant name); `true`/`false` (→ `"true"`/`"false"` variant names — "boolean shorthand": `"targeting": {"ends_with": [{"var":"email"}, "@x.com"]}` works when variants are named `true`/`false`); `null` (exit to `defaultVariant`, `reason=DEFAULT`).

Source: https://flagd.dev/reference/flag-definitions/

## 7. Standard operators

Schema-allowed JsonLogic operators (anything else fails validation):

| Group | Operators | Notes |
|---|---|---|
| Control | `if` | `["cond", "then", "else"]` or chained `["c1","v1","c2","v2","else"]` |
| Logic | `and`, `or`, `!`, `!!` | variadic; `!!` = truthy test / "exists" (`""`, `0`, `null`, `[]` are falsy) |
| Equality | `==`, `!=` (coercing), `===`, `!==` (strict) | `{"==":[1,"1"]}` → true; `{"===":[1,"1"]}` → false. Prefer strict. |
| Compare | `<`, `<=`, `>`, `>=` | numeric. `<`/`<=` accept 3 args for between: `{"<":[1,{"var":"age"},10]}` |
| Membership | `in` | `{"in":["needle", "haystack-string"]}` substring; `{"in":[{"var":"x"}, ["a","b"]]}` array membership. Negate with `!`. |
| Data | `var`, `missing`, `missing_some` | `missing` returns array of absent keys (empty array is falsy) |
| Math | `+`, `-`, `*`, `/`, `%`, `min`, `max` | `-` with one arg negates |
| String | `cat`, `substr` | `cat` concatenates and stringifies — use it to build bucketing keys |
| Array | `map`, `filter`, `reduce`, `all`, `some`, `none`, `merge` | rarely needed in flags |
| flagd | `fractional`, `sem_ver`, `starts_with`, `ends_with`, `$ref` | §8, §9 |

Source: https://flagd.dev/reference/flag-definitions/ , https://flagd.dev/schema/v0/targeting.json

## 8. Custom operations

### `fractional` — deterministic weighted split (v0.6.4+)

```jsonc
"fractional": [
  <bucketing expression>,          // OPTIONAL first element; any rule that is not an array
  ["<variant>", <weight>],         // weight: non-negative integer OR a JSON Logic expr yielding a number
  ["<variant>"],                   // weight omitted → 1
  …
]
```

Rules:
- Bucketing expression (first element) is optional. If omitted, flagd hashes the pair `(flagKey, targetingKey)`. If `targetingKey` is missing or not a string in that case → evaluation error (`null` → falls to default / errors depending on context). Always send a targetingKey when relying on the default.
- Recommended explicit key: `{"cat": [{"var":"$flagd.flagKey"}, {"var":"email"}]}` — salting with the flag key makes assignments independent across flags. Bucketing on the same raw value without salt makes every flag with the same weights bucket users identically.
- Bucketing value types: historically must be a string (cast with `cat`). Accepted ADR (pre-1.0) extends to boolean/number/object via deterministic CBOR encoding; arrays and `null` are rejected. Expect one-time rebucketing when that ships.
- Hash: MurmurHash3 32-bit, treated as unsigned. Bucket = `(hash * sumOfWeights) >> 32`; variants are laid out in array order as cumulative ranges; first range containing the bucket wins. Same input → same variant, everywhere (Go daemon and all in-process providers agree).
- Weights are **relative**; they do **not** need to sum to 100. `[["a",1],["b",3]]` = 25/75. Legacy docs requiring sum=100 with 1% granularity are obsolete: current precision is limited only by the total weight; sum of weights must be ≤ 2,147,483,647 (MaxInt32) and each weight a non-negative integer. `[["canary",1],["control",1000000]]` gives ~0.0001%.
- Weights may be expressions: `["on", {"-":[{"var":"$flagd.timestamp"}, 1743360000]}]` grows over time. Negative computed weights are clamped to 0. This is how to do time-based progressive rollouts — there is no separate rollout operator.
- Variant slot may itself be an expression evaluated only if that bucket wins: `[{"if":[{"in":[{"var":"locale"},["us","ca"]]},"red","grey"]}, 25]`.
- Add new variants at the **end** to minimise reassignment; changing weights moves only the users at range boundaries.
- `fractional` returns the variant string directly. Both strings are truthy, so **never use it as an `if` condition** without wrapping: `{"==": [{"fractional":[…]}, "on"]}`.
- The reason returned by flagd for a fractional match is `TARGETING_MATCH` (some providers report `SPLIT`).
- Legacy operator `fractionalEvaluation` (bucketing key given as a plain string) is deprecated — replace the string with `{"var": "…"}` and rename to `fractional`.

Source: https://flagd.dev/reference/custom-operations/fractional-operation/ , https://flagd.dev/reference/specifications/custom-operations/fractional-operation-spec/ , https://flagd.dev/architecture-decisions/fractional/ , https://flagd.dev/architecture-decisions/high-precision-fractional-bucketing/ , https://flagd.dev/architecture-decisions/fractional-non-string-rand-units/

### `sem_ver` — semantic version comparison

```jsonc
"sem_ver": [{"var": "appVersion"}, ">=", "2.1.0"]
```

- Exactly 3 items: `[<version-or-var>, <operator>, <version-or-var>]`. Returns boolean; returns `null` (falsy) if either side is not a valid semver or the operator is unknown.
- Operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `~` (same major.minor — patch may differ), `^` (same major — minor/patch may differ).
- Input normalisation: leading `v`/`V` stripped; partial versions `1` / `1.0` padded to `1.0.0`; numeric context values coerced to string; build metadata (`+build`) ignored; pre-release tags (`-beta.1`) compared per semver precedence.
- Literal versions in the rule must match the strict semver regex (`MAJOR.MINOR.PATCH[-pre][+build]`) or schema validation fails — write `"2.1.0"`, not `"2.1"`, in the flag file even though context values are padded.

Source: https://flagd.dev/reference/custom-operations/semver-operation/ , https://flagd.dev/reference/specifications/custom-operations/semver-operation-spec/

### `starts_with` / `ends_with`

```jsonc
"starts_with": [{"var": "email"}, "admin@"]
"ends_with":   [{"var": "email"}, "@example.com"]
```

- Exactly 2 items, both must resolve to strings; otherwise `null` (falsy). Case-sensitive. Returns boolean.
- Use `in` for substring, `==` for exact match.

Source: https://flagd.dev/reference/custom-operations/string-comparison-operation/ , https://flagd.dev/reference/specifications/custom-operations/string-comparison-operation-spec/

## 9. `$evaluators` and `$ref`

```jsonc
"$evaluators": {
  "isInternal": { "ends_with": [{"var": "email"}, "@example.com"] }
},
"flags": {
  "x": { …, "targeting": { "if": [ {"$ref": "isInternal"}, "on", null ] } }
}
```

- `$evaluators` is a top-level map name → JSON Logic rule. `{"$ref": "<name>"}` anywhere inside `targeting` is textually replaced by that rule before evaluation *(source: `transposeEvaluators`)*.
- `$ref` names are case-sensitive. Replacement is textual, so `{"$ref": "name"}` must be an object with `$ref` as its **only** key. A `$ref` to an undefined name is *not* caught at load: it is left in place and fails at evaluation (`reason=ERROR`, `PARSE_ERROR`) *(source)*.
- **No nesting**: an evaluator body cannot contain `$ref`. Each must be self-contained.
- Use for shared audiences (internal users, beta cohort, region gates). Put the rule in `$evaluators` once; reference from many flags.

Source: https://flagd.dev/reference/flag-definitions/

## 10. Metadata (flag set, flag, variant/rule-level)

- **Flag-set metadata** (top-level `metadata`): applies to every flag in the file. Well-known keys: `flagSetId` (used by selectors and as part of the flag's identity, §13), `version`. Values scalar only.
- **Flag metadata** (`flags.<key>.metadata`): flag-specific; merged over set metadata, flag value wins per key, non-overridden set keys are inherited.
- Evaluation responses return the merged map as `metadata` / `flagMetadata` on every reason including `DISABLED` and `DEFAULT`. Selector info used in the request is reflected in the response's top-level metadata.
- Providers expose the top-level metadata as provider metadata; in-process providers can also inject sync-metadata into context.
- **Rule-level (variant) metadata** — accepted ADR (2026-09), **not yet in the hosted v0 schema**: a targeting branch may return `{"variant": "on", "reason": "KILL_SWITCH", "metadata": {"details": "incident-42"}}` instead of `"on"`. `variant` required; `reason` overrides `TARGETING_MATCH`; `metadata` (scalars, optional `details` string) merges highest-priority over flag metadata. Older flagd binaries fail on this shape — do not emit it until the schema version bump ships and the fleet is upgraded.

Source: https://flagd.dev/concepts/metadata/ , https://flagd.dev/architecture-decisions/targeting-variant-metadata/

## 11. Disabled flags and code defaults

| Config | Response | SDK behaviour |
|---|---|---|
| `state: DISABLED` | `reason=DISABLED`, no `value`, no `variant`, metadata present; HTTP 200 on OFREP | uses the code default passed to `getXValue(key, default)` |
| flag key absent | `reason=ERROR`, `errorCode=FLAG_NOT_FOUND` | uses code default, but as an *error* (shows in error metrics) |
| `defaultVariant: null` or omitted, no targeting match | `reason=DEFAULT`, no `value`/`variant` | uses code default, successful evaluation |
| `defaultVariant: "off"`, no targeting match | `reason=DEFAULT`, `variant=off`, value present | uses flagd's value |

Guidance:
- Prefer `DISABLED` over deleting a flag when turning something off operationally — it is a success, not an error, and stays visible in bulk evaluation.
- Prefer `defaultVariant: null` when the application already has a sensible code default and you only want targeting to override it — one source of truth, and DISABLED↔ENABLED transitions behave the same for non-targeted users.
- Never "force" a code default by returning an invalid variant from targeting; that yields `ERROR/GENERAL`.
- Pre-`DISABLED`-ADR releases returned `reason=ERROR`, `errorCode=FLAG_DISABLED` (gRPC v1 NotFound, OFREP 404). Old clients using `defaultVariant: null` may receive zero values (`false`, `0`, `""`) instead of the code default — upgrade providers before adopting `null` defaults.

Source: https://flagd.dev/architecture-decisions/disabled-flag-evaluation/ , https://flagd.dev/architecture-decisions/support-code-default/ , https://flagd.dev/troubleshooting/

## 12. Numeric coercion

JSON has one number type; flagd resolvers distinguish int vs float. Contract (ADR, draft — Go/Java historically truncated silently, Python/.NET returned `TYPE_MISMATCH`):

| Variant value | Fetched as Integer | Fetched as Float |
|---|---|---|
| int within accessor range (int32 for 32-bit accessors, int64 for long) | value | value |
| int > accessor max but ≤ 2^53−1 | `TYPE_MISMATCH` | value |
| whole-valued float e.g. `10.0` | `10` | `10.0` |
| fractional float e.g. `3.14` | `TYPE_MISMATCH` | value |
| magnitude > 2^53−1 (`9007199254740991`) | rejected at load / `PARSE_ERROR` | rejected at load / `PARSE_ERROR` |

Rule of thumb: keep numeric variants within ±2^53−1; use integer literals for int flags and call the matching accessor. Targeting comparisons (`<`, `==`) treat all numbers uniformly — coercion applies only at the typed accessor boundary. `==` coerces `"1"` to `1`; `===` does not.

Source: https://flagd.dev/architecture-decisions/numeric-coercion/

## 13. Multiple sources, duplicate keys, flag sets

- flagd can load many sources (`--uri file:a.json --uri file:b.json …` or `--sources '[…]'`). All are merged into one store.
- **Identity** of a flag is the composite `(flagKey, flagSetId)`. `flagSetId` comes from top-level `metadata.flagSetId`, else per-flag `metadata.flagSetId`, else `""`. Same key in different flag sets = different flags; query one with the selector `flagSetId=<id>` (`Flagd-Selector` header / provider `selector` option).
- **Same composite key in several sources**: the **last-defined / most-recently-synced source wins**; earlier definitions are discarded. If the winning source later deletes the flag, flagd triggers a resync of all sources and the next source's version reappears. Ownership therefore depends on sync order — avoid relying on it; give each source a distinct `flagSetId` instead.
- **Same composite key twice in one source** → config invalid (rejected). Same key with different `flagSetId`s in one source is valid only in **array form**:

```json
{
  "$schema": "https://flagd.dev/schema/v0/flags.json#/definitions/flagdConfig",
  "flags": [
    { "key": "checkout", "state": "ENABLED", "variants": {"on": true, "off": false}, "defaultVariant": "on",  "metadata": {"flagSetId": "web"} },
    { "key": "checkout", "state": "ENABLED", "variants": {"on": true, "off": false}, "defaultVariant": "off", "metadata": {"flagSetId": "mobile"} }
  ]
}
```

- Array form is accepted by the flagd daemon only (`flagdConfig`); in-process providers expect the map form (`providerConfig`). A source may update a subset of flags; each sync from a source is treated as the full state of that source's flags — flags missing from the new payload are removed.

Source: https://flagd.dev/concepts/syncs/ , https://flagd.dev/concepts/selectors/ , https://flagd.dev/architecture-decisions/duplicate-flag-keys/

## 14. Complete examples

All examples are full files; paste and run `flagd start --uri file:./flags.flagd.json`.

### 14.1 Boolean kill switch (static)

```json
{
  "$schema": "https://flagd.dev/schema/v0/flags.json",
  "flags": {
    "new-checkout": {
      "state": "ENABLED",
      "variants": { "on": true, "off": false },
      "defaultVariant": "off"
    }
  }
}
```
Result: `reason=STATIC`, `variant=off`, `value=false`; cacheable. Flip `defaultVariant` to `on` to release.

### 14.2 String flag targeted by email domain

```json
{
  "$schema": "https://flagd.dev/schema/v0/flags.json",
  "flags": {
    "header-color": {
      "state": "ENABLED",
      "variants": { "red": "#FF0000", "blue": "#0000FF", "green": "#00FF00" },
      "defaultVariant": "red",
      "targeting": {
        "if": [
          { "ends_with": [{ "var": "email" }, "@example.com"] }, "blue",
          { "in": [{ "var": "email" }, ["qa1@test.io", "qa2@test.io"]] }, "green",
          null
        ]
      }
    }
  }
}
```
`email` missing → `ends_with` returns null → falls through → final `null` → `reason=DEFAULT`, `variant=red`.

### 14.3 Percentage rollout (default bucketing on targetingKey)

```json
{
  "$schema": "https://flagd.dev/schema/v0/flags.json",
  "flags": {
    "new-search": {
      "state": "ENABLED",
      "variants": { "on": true, "off": false },
      "defaultVariant": "off",
      "targeting": {
        "fractional": [
          ["on", 10],
          ["off", 90]
        ]
      }
    }
  }
}
```
Requires the SDK to set a targeting key; bucketing input is `(flagKey, targetingKey)`. Raise `on` to 25/50/100 to progress. Callers without a targeting key get an evaluation error → SDK code default.

### 14.4 Fractional with a custom bucketing key (per-tenant, salted)

```json
{
  "$schema": "https://flagd.dev/schema/v0/flags.json",
  "flags": {
    "pricing-experiment": {
      "state": "ENABLED",
      "variants": { "control": "control", "variant-a": "variant-a", "variant-b": "variant-b" },
      "defaultVariant": "control",
      "targeting": {
        "if": [
          { "!!": [{ "var": "tenantId" }] },
          {
            "fractional": [
              { "cat": [{ "var": "$flagd.flagKey" }, { "var": "tenantId" }] },
              ["control", 50],
              ["variant-a", 25],
              ["variant-b", 25]
            ]
          },
          null
        ]
      }
    }
  }
}
```
Every user of a tenant lands in the same bucket; `$flagd.flagKey` salt keeps this split independent of other flags bucketing on `tenantId`. No `tenantId` → `control` with `reason=DEFAULT`.

### 14.5 Semver gate (number flag)

```json
{
  "$schema": "https://flagd.dev/schema/v0/flags.json",
  "flags": {
    "max-upload-mb": {
      "state": "ENABLED",
      "variants": { "legacy": 25, "modern": 500 },
      "defaultVariant": "legacy",
      "targeting": {
        "if": [
          { "and": [
            { "sem_ver": [{ "var": "appVersion" }, ">=", "3.2.0"] },
            { "!": { "sem_ver": [{ "var": "appVersion" }, "^", "4.0.0"] } }
          ] },
          "modern",
          null
        ]
      }
    }
  }
}
```
Matches `3.2.0 ≤ v < 4.0.0`. Context `appVersion: "v3.5"` is normalised to `3.5.0`. Fetch with the integer accessor (values are whole).

### 14.6 Time-based: scheduled launch and 7-day ramp via `$flagd.timestamp`

```json
{
  "$schema": "https://flagd.dev/schema/v0/flags.json",
  "flags": {
    "holiday-banner": {
      "state": "ENABLED",
      "variants": { "on": true, "off": false },
      "defaultVariant": "off",
      "targeting": {
        "if": [
          { ">=": [{ "var": "$flagd.timestamp" }, 1764547200] },
          "on",
          null
        ]
      }
    },
    "new-feed-ramp": {
      "state": "ENABLED",
      "variants": { "on": true, "off": false },
      "defaultVariant": "off",
      "targeting": {
        "fractional": [
          { "cat": [{ "var": "$flagd.flagKey" }, { "var": "targetingKey" }] },
          ["on",  { "max": [0, { "-": [{ "var": "$flagd.timestamp" }, 1764547200] }] }],
          ["off", { "max": [0, { "-": [1765152000, { "var": "$flagd.timestamp" }] }] }]
        ]
      }
    }
  }
}
```
`holiday-banner` turns on at 2025-12-01T00:00Z. `new-feed-ramp` goes 0→100% over the 7 days after that (weights are seconds elapsed vs seconds remaining; `max` keeps them ≥0, though flagd also clamps). Time-based flags are never `STATIC`, so they are not cached.

### 14.7 Shared `$evaluators`

```json
{
  "$schema": "https://flagd.dev/schema/v0/flags.json",
  "$evaluators": {
    "isInternal": { "ends_with": [{ "var": "email" }, "@example.com"] },
    "isBetaRegion": { "in": [{ "var": "region" }, ["eu-west-1", "us-east-2"]] }
  },
  "flags": {
    "admin-console-v2": {
      "state": "ENABLED",
      "variants": { "on": true, "off": false },
      "defaultVariant": "off",
      "targeting": { "if": [{ "$ref": "isInternal" }, "on", null] }
    },
    "checkout-flow": {
      "state": "ENABLED",
      "variants": { "legacy": "legacy", "express": "express" },
      "defaultVariant": "legacy",
      "targeting": {
        "if": [
          { "or": [{ "$ref": "isInternal" }, { "$ref": "isBetaRegion" }] },
          "express",
          null
        ]
      }
    }
  }
}
```
Evaluator bodies may not contain `$ref` themselves.

### 14.8 Object flag (structured config)

```json
{
  "$schema": "https://flagd.dev/schema/v0/flags.json",
  "flags": {
    "rate-limits": {
      "state": "ENABLED",
      "variants": {
        "standard": { "rps": 100, "burst": 200, "tiers": ["free", "pro"] },
        "premium":  { "rps": 1000, "burst": 5000, "tiers": ["enterprise"] }
      },
      "defaultVariant": "standard",
      "targeting": {
        "if": [{ "===": [{ "var": "plan" }, "enterprise"] }, "premium", null]
      },
      "metadata": { "owner": "platform-team", "version": "3" }
    }
  },
  "metadata": { "flagSetId": "api-gateway", "team": "platform" }
}
```
Returned metadata: `{flagSetId: api-gateway, team: platform, owner: platform-team, version: "3"}`. Object variants may nest arrays/objects freely — only *metadata* is restricted to scalars.

### 14.9 Disabled flag and code-default flag

```json
{
  "$schema": "https://flagd.dev/schema/v0/flags.json",
  "flags": {
    "legacy-export": {
      "state": "DISABLED",
      "variants": { "on": true, "off": false },
      "defaultVariant": "on"
    },
    "beta-dashboard": {
      "state": "ENABLED",
      "variants": { "on": true, "off": false },
      "defaultVariant": null,
      "targeting": { "if": [{ "===": [{ "var": "userType" }, "beta"] }, "on", null] }
    }
  }
}
```
`legacy-export` → `{"reason":"DISABLED","metadata":{}}` (no value; targeting and `defaultVariant` ignored). `beta-dashboard` for non-beta users → `{"reason":"DEFAULT","metadata":{}}`; SDK returns the code default passed by the app.

### 14.10 Same file in YAML

```yaml
# yaml-language-server: $schema=https://flagd.dev/schema/v0/flags.json
flags:
  new-checkout:
    state: ENABLED
    variants:
      'on': true
      'off': false
    defaultVariant: 'off'
    targeting:
      if:
        - ends_with:
            - var: email
            - "@example.com"
        - 'on'
        - null
$evaluators: {}
```

Source: https://flagd.dev/reference/flag-definitions/ , https://github.com/open-feature/flagd/tree/main/samples

## 15. Debug checklist

| Symptom | Likely cause |
|---|---|
| `FLAG_NOT_FOUND` | key typo; wrong `flagSetId`/selector; source not loaded (check `--uri`); flag removed by a later source's sync; very old client + `defaultVariant: null` |
| `TYPE_MISMATCH` | resolver/accessor type ≠ variant value type; mixed variant types; float variant fetched as int (§12) |
| `PARSE_ERROR` | invalid JSON Logic; unknown operator; file failed schema validation; malformed YAML (`on`/`off` unquoted) |
| `GENERAL` ("invalid or missing variant") | targeting returned a string not in `variants` (case mismatch), a number, array, or `fractional` variant name that does not exist |
| Always `DEFAULT`, never matches | context attribute name/case mismatch; attribute not sent by SDK (check with `-X` static context or `--debug`); `sem_ver` literal not full `x.y.z`; `ends_with` vs `starts_with` mixed up |
| Everyone gets same fractional variant | no/constant `targetingKey`; bucketing expr returns null (falls to default); all users share the bucketing attribute |
| Fractional inside `if` always takes the then-branch | `fractional` returns a truthy string — wrap in `{"==":[{"fractional":[…]},"on"]}` |
| Value/variant missing in response | expected: `DISABLED` or code-default (`DEFAULT` with `defaultVariant` null) — not a bug |
| Not cached / `TARGETING_MATCH` on a "static" flag | any non-empty `targeting` disables `STATIC` |
| Editor shows no autocomplete | missing `$schema` key (JSON) or `yaml-language-server` comment (YAML); file not named `*.flagd.json` |

Enable verbose logs with `flagd start --debug` (or `FLAGD_DEBUG=true`) to see per-evaluation targeting output.

Source: https://flagd.dev/troubleshooting/
