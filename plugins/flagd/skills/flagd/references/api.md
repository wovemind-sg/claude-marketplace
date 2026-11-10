# flagd API reference (evaluation gRPC/Connect, OFREP, sync, management)

Worked from flagd `main` @ `b13483f77df9006887e69cf6ce1f3bb320328dbb` (2026-09-18, "chore: mark accepted"); protos from
`open-feature/flagd-schemas` `main`; OFREP spec from `open-feature/protocol` `main` (openapi `info.version: 0.3.0`).
Where docs and source disagreed, source wins and the discrepancy is called out.

## Contents

1. [Ports and protocols](#1-ports-and-protocols)
2. [Evaluation service (:8013) — flagd.evaluation.v2 / v1 / legacy schema.v1](#2-evaluation-service-8013)
3. [OFREP (:8016)](#3-ofrep-8016)
4. [Sync service (:8015) — flagd.sync.v1.FlagSyncService + GET /v1/flags](#4-sync-service-8015)
5. [Management (:8014)](#5-management-8014)
6. [grpcurl recipes](#6-grpcurl-recipes)
7. [Cheat-sheet essentials and playground](#7-cheat-sheet-essentials-and-playground)
8. [RFC: custom gRPC name resolver (`envoy://`)](#8-rfc-custom-grpc-name-resolver-envoy)

---

## 1. Ports and protocols

| Port | Flag | Protocols | What is served |
|------|------|-----------|----------------|
| 8013 | `--port/-p` | gRPC, gRPC-Web, Connect (HTTP/1.1 JSON), h2c | `flagd.evaluation.v2.Service`, `flagd.evaluation.v1.Service` (deprecated), legacy `schema.v1.Service` |
| 8014 | `--management-port/-m` | HTTP (+ grpc health v1 on h2) | `/healthz`, `/readyz`, `/metrics` (Prometheus) |
| 8015 | `--sync-port/-g` | gRPC, gRPC-Web, Connect, h2c, plain HTTP GET | `flagd.sync.v1.FlagSyncService`, `GET /v1/flags` |
| 8016 | `--ofrep-port/-r` | HTTP/JSON (REST) + SSE | `/ofrep/v1/evaluate/flags[/{key}]`, `/ofrep/v1/sse[/{channel}]` |

- Every RPC port is a Connect handler over `net/http`: one port speaks native gRPC (`Content-Type: application/grpc`, HTTP/2), gRPC-Web, and the Connect protocol (`POST /<package>.<Service>/<Method>` with `Content-Type: application/json`). Plaintext HTTP/2 via h2c, so gRPC clients need no TLS. TLS (`--server-cert-path/-c`, `--server-key-path/-k`) covers all protocols on that port.
- **No gRPC server reflection.** `grpcurl list` fails; pass `-proto` files (see §6).
- Connect JSON codec: `EmitUnpopulated: true` (falsy/empty fields are emitted, e.g. `"value": false`, `"metadata": {}`), `DiscardUnknown: true` on input. proto3 JSON rules apply: `int64` is a JSON **string** (`"value": "50"`), field names are lowerCamelCase (`flagKey`, `flagConfiguration`), `google.protobuf.Struct` is a plain JSON object.
- Selector for all services: HTTP header `Flagd-Selector: flagSetId=<id>` | `source=<uri>` | bare `<uri>` (legacy = source). Header beats any body `selector` field. `flagSetId=` (empty) selects flags with no named flag set. Malformed/unknown selector → OFREP 400, Connect/gRPC `invalid_argument`, `GET /v1/flags` 400 (selector-syntax.md claims 404 for unknown filter on that endpoint; grpc-sync-service.md and cheat-sheet.md say 400).
- Context merge order for every evaluation path (highest wins): header-mapped values (`-H "X-User-Tier=tier"`), static `-X key=value`, request-body `context`. flagd also injects `$flagd.flagKey` and `$flagd.timestamp` (unix seconds) into the JsonLogic context.
- Request limits: `--max-request-body/-B` (default 1 000 000 bytes; `0` = unlimited) → OFREP `413`, Connect `resource_exhausted` (HTTP 429). `--max-request-header/-R` (default 1 000 000) → `431`. `--stream-deadline` (default 0 = none) closes EventStream/SyncFlags with `deadline_exceeded` (gRPC code 4). Unix sockets: `--socket-path/-d` (evaluation), `--sync-socket-path/-e`. CORS: `--cors-origin/-C` (`*` allows all).
- Note: `docs/reference/flagd-ofrep.md` and `selector-syntax.md` still show old port numbers in places (8014 for OFREP); the CLI default is authoritative: **OFREP = 8016, management = 8014**.

Source: docs/reference/cheat-sheet.md → https://flagd.dev/reference/cheat-sheet/ ; docs/reference/flagd-cli/flagd_start.md → https://flagd.dev/reference/flagd-cli/flagd_start/ ; flagd/pkg/service/flag-evaluation/connect_service.go

---

## 2. Evaluation service (:8013)

Three services are multiplexed by URL prefix on the same port:

| Path prefix | Service | Status |
|-------------|---------|--------|
| `/flagd.evaluation.v2.Service/*` | `flagd.evaluation.v2.Service` | current; use for single-flag resolution |
| `/flagd.evaluation.v1.Service/*` | `flagd.evaluation.v1.Service` | deprecated (`option deprecated = true` in proto) but served; **only place `ResolveAll` exists** |
| anything else (`/schema.v1.Service/*`) | legacy `schema.v1.Service` | pre-rename schema, served for old providers |

### 2.1 RPCs

| RPC | Request | Response | v2 | v1 |
|-----|---------|----------|----|----|
| `ResolveBoolean` | `{flag_key, context}` | `{value: bool, reason, variant, metadata}` | yes | yes |
| `ResolveString` | `{flag_key, context}` | `{value: string, …}` | yes | yes |
| `ResolveFloat` | `{flag_key, context}` | `{value: double, …}` | yes | yes |
| `ResolveInt` | `{flag_key, context}` | `{value: int64 (JSON string), …}` | yes | yes |
| `ResolveObject` | `{flag_key, context}` | `{value: Struct, …}` | yes | yes |
| `ResolveAll` | `{context}` | `{flags: map<string, AnyFlag>, metadata}` | **no** | yes |
| `EventStream` | `{}` | stream `{type, data}` | yes | yes |

Request fields (all Resolve*): `flag_key` (string, JSON `flagKey`), `context` (`google.protobuf.Struct`, JSON `context`, arbitrary attrs; `targetingKey` conventional for bucketing).

Response fields: `value` (typed; unset on error), `reason` (string), `variant` (string), `metadata` (Struct: flag `metadata` from the definition, merged with flag-set metadata, plus reflected `flagSetId`; empty `{}` when none).

**v1 vs v2 proto difference**: identical field numbers, but v2 marks `value` and `variant` as `optional` (presence-tracked), so v2 can return a response with **no value/variant** (reason-only) for `DISABLED` and code-default (`FALLBACK`→`DEFAULT`) results. v1 (and legacy) run the evaluator in "old proto" mode: a flag with no `defaultVariant` whose targeting yields nothing is a `FLAG_NOT_FOUND` error instead of a code default, and `DISABLED` comes back with the zero value. v2 drops `ResolveAll`. Package options: `go_package = "flagd/evaluation/v2"`, `java_package = "dev.openfeature.flagd.grpc.evaluation.v2"`, `csharp_namespace = "OpenFeature.Flagd.Grpc.Evaluation.V2"`.

`AnyFlag` (ResolveAll map value): `reason`, `variant`, `oneof value { bool_value(3) | string_value(4) | double_value(5) | object_value(6) }`, `metadata(7)`. Connect JSON emits whichever oneof member is set, e.g. `{"reason":"STATIC","variant":"on","boolValue":true,"metadata":{}}`. `ResolveAllResponse.metadata` carries flag-set-level metadata.

### 2.2 `reason` values (core/pkg/model/reason.go)

| reason | Meaning |
|--------|---------|
| `STATIC` | no `targeting` on the flag (or empty); `defaultVariant` returned. RPC providers may cache these. |
| `DEFAULT` | targeting evaluated but yielded no variant (rule returned null / no match) → `defaultVariant`. Also what v2/OFREP report for a code-default result (internal `FALLBACK`), with value+variant omitted. |
| (code default) | flag has **no `defaultVariant`** and targeting returns null/no match (or there is no targeting): evaluator reason `FALLBACK` → wire `reason: "DEFAULT"`, no `value`, no `variant`; the SDK must use the in-code default. v1/legacy instead return `FLAG_NOT_FOUND`. |
| `TARGETING_MATCH` | targeting rule returned a variant. |
| `SPLIT` | fractional (`fractional` operator) bucketing chose the variant. |
| `DISABLED` | flag `state: "DISABLED"`; value/variant omitted (v2, OFREP); v1 returns zero value. |
| `ERROR` | set on every error response alongside a gRPC/Connect error. |
| `UNKNOWN` | catch-all. |
| `FALLBACK` | internal only — never on the wire in v2/OFREP; mapped to `DEFAULT` with no value (see row above). |

### 2.3 Error codes and Connect/gRPC mapping (flag_evaluator.go `errFormat`)

| flagd error code | Human message | Connect/gRPC code | HTTP (Connect JSON) |
|------------------|---------------|-------------------|---------------------|
| `FLAG_NOT_FOUND` | "Flag not found" | `not_found` (5) | 404 |
| `FLAG_DISABLED` | "Flag is disabled" | `not_found` (5) | 404 — defined and mapped, but the current evaluator never raises it: disabled flags come back 200 with `reason: DISABLED` (value/variant omitted in v2/OFREP, zero value in v1) |
| `TYPE_MISMATCH` | "Type mismatch error" | `invalid_argument` (3) | 400 |
| `PARSE_ERROR` | "Error parsing input or configuration" | `data_loss` (15) | 500 |
| `GENERAL` | "General error" | `unknown` (2) | 500 |
| `INVALID_CONTEXT` | "Invalid context provided" | (OFREP only) | 400 |

Connect JSON error body: `{"code":"not_found","message":"Flag not found"}`. Bad selector header → `invalid_argument`. Oversized body → `resource_exhausted` (429). Stream deadline → `deadline_exceeded` (4).

### 2.4 Connect/HTTP-JSON calls (curl)

```bash
# boolean
curl -s -X POST localhost:8013/flagd.evaluation.v2.Service/ResolveBoolean \
  -H 'Content-Type: application/json' \
  -d '{"flagKey":"show-welcome-banner","context":{"company":"initech"}}'
# → {"value":false,"reason":"STATIC","variant":"off","metadata":{}}

# string / float / int / object — same shape, different method
curl -s -X POST localhost:8013/flagd.evaluation.v2.Service/ResolveString -H 'Content-Type: application/json' \
  -d '{"flagKey":"background-color","context":{"company":"initech"}}'
# → {"value":"#00FF00","reason":"TARGETING_MATCH","variant":"green","metadata":{}}
curl -s -X POST localhost:8013/flagd.evaluation.v2.Service/ResolveInt -H 'Content-Type: application/json' \
  -d '{"flagKey":"simple-number","context":{}}'
# → {"value":"50","reason":"STATIC","variant":"medium","metadata":{}}   (int64 → JSON string)

# with selector
curl -s -X POST localhost:8013/flagd.evaluation.v2.Service/ResolveBoolean -H 'Content-Type: application/json' \
  -H 'Flagd-Selector: flagSetId=app-flags' -d '{"flagKey":"simple-boolean","context":{}}'

# bulk (v1 only)
curl -s -X POST localhost:8013/flagd.evaluation.v1.Service/ResolveAll -H 'Content-Type: application/json' \
  -d '{"context":{"tier":"premium"}}'
# → {"flags":{"simple-boolean":{"reason":"STATIC","variant":"on","boolValue":true,"metadata":{}}, ...},"metadata":{}}

# error
curl -s -X POST localhost:8013/flagd.evaluation.v2.Service/ResolveBoolean -H 'Content-Type: application/json' \
  -d '{"flagKey":"nope","context":{}}'
# HTTP 404 → {"code":"not_found","message":"Flag not found"}
```

Type mismatch example: calling `ResolveBoolean` on a string flag → 400 `{"code":"invalid_argument","message":"Type mismatch error"}`.

### 2.5 EventStream

Server stream; request body is empty `{}`; selector only via `Flagd-Selector` header (filters which flags' changes are reported). Message: `EventStreamResponse{type: string, data: Struct}`.

| `type` | When | `data` |
|--------|------|--------|
| `provider_ready` | first message on every stream | unset (providers surface it as provider metadata) |
| `configuration_change` | any flag added/removed/changed (compares state, defaultVariant, variants, targeting, metadata; first store emission is swallowed so no spurious event on connect) | `{"flags": {"<flagKey>": {"type": "write" \| "update" \| "delete"}, ...}}` |
| `keep_alive` | every 20 s of silence | unset |
| `provider_shutdown` | defined in core (`Shutdown`), emitted on server shutdown via `EmitToAll` | unset |

Provider contract: on `configuration_change` invalidate cached flags listed in `data.flags` and emit `PROVIDER_CONFIGURATION_CHANGED`; on disconnect purge the whole cache. (providers.md documents an older per-flag shape `{type, source, flagKey}`; the current server emits the `flags` map above — see core/pkg/notifications/notifications.go.)

Connect streaming over HTTP/1.1 is possible (enveloped frames, `Content-Type: application/connect+json`) but grpcurl is the practical CLI (§6). Deadline: `--stream-deadline` → `deadline_exceeded`; providers treat any stream end as reconnect (STALE → after `retryGracePeriod` ERROR).

Source: docs/reference/specifications/protos.md → https://flagd.dev/reference/specifications/protos/ ; https://github.com/open-feature/flagd-schemas/blob/main/protobuf/flagd/evaluation/v2/evaluation.proto ; …/v1/evaluation.proto ; docs/reference/specifications/providers.md → https://flagd.dev/reference/specifications/providers/ ; flagd/pkg/service/flag-evaluation/{flag_evaluator.go,flag_evaluator_v2.go,eventing.go}

---

## 3. OFREP (:8016)

Status in docs: EXPERIMENTAL badge. Implements OFREP Core (`POST /ofrep/v1/evaluate/flags/{key}`, `POST /ofrep/v1/evaluate/flags`) plus the ADR-0008 SSE change stream. No auth (spec's `X-API-Key` / `Authorization: Bearer` are optional; flagd ignores them). Metrics via OpenTelemetry HTTP + evaluation metrics. Trailing slash on bulk path accepted (`flags` or `flags/`).

### 3.1 Request

Body (both endpoints): `{"context": {"targetingKey": "user-123", ...}}`. flagd does **not** require `targetingKey` (spec marks it required) and accepts an **empty body** (`curl -X POST …` with no `-d` works; EOF is tolerated). Non-object `context` is ignored with a warning, not rejected. Malformed JSON → 400. Body > `--max-request-body` → 413 `{"errorDetails":"request body too large"}`. Selector: `Flagd-Selector` header. Header→context mapping (`-H`) and static context (`-X`) apply.

### 3.2 Single flag — `POST /ofrep/v1/evaluate/flags/{key}`

| HTTP | Body | When |
|------|------|------|
| 200 | `{"key","value","reason","variant","metadata"}` | success. `value`/`variant` omitted when `reason` is `DEFAULT`-from-fallback (code default: SDK uses its own default) or `DISABLED`. `metadata` always present (`{}` if empty). |
| 400 | `{"key","errorCode":"INVALID_CONTEXT","errorDetails":"Provider context is not valid","metadata":null}` | JSON decode failure |
| 400 | `{"key","errorCode":"GENERAL","errorDetails":"invalid selector: …"}` | bad `Flagd-Selector` |
| 400 | `{"key","errorCode":"PARSE_ERROR","errorDetails":"error parsing the flag `k`"}` | targeting/definition parse error |
| 400 | `{"key","errorCode":"GENERAL","errorDetails":"error processing the flag for evaluation"}` | any other evaluator error (incl. TYPE_MISMATCH — OFREP is untyped so this rarely occurs) |
| 404 | `{"key","errorCode":"FLAG_NOT_FOUND","errorDetails":"flag `k` does not exist","metadata":…}` | unknown key (or filtered out by selector) |
| 413 | `{"errorDetails":"request body too large"}` | body limit |
| 500 | `{"errorDetails":"failed to obtain the flag key from the request"}` | router failure (should not happen) |

flagd never returns 401/403/429 (`Retry-After`) — those are spec-allowed but unimplemented.

```bash
curl -s -X POST localhost:8016/ofrep/v1/evaluate/flags/email-based-feature \
  -H 'Content-Type: application/json' -d '{"context":{"email":"user@example.com"}}'
# → {"key":"email-based-feature","reason":"TARGETING_MATCH","variant":"on","value":true,"metadata":{}}
curl -s -X POST localhost:8016/ofrep/v1/evaluate/flags/simple-boolean            # no body is fine
curl -s -X POST localhost:8016/ofrep/v1/evaluate/flags/payment-provider -H 'Flagd-Selector: flagSetId=payment-flags'
```

### 3.3 Bulk — `POST /ofrep/v1/evaluate/flags`

200 body:

```jsonc
{
  "flags": [                                   // one entry per flag visible to the selector; success and failure items mixed
    {"key":"simple-boolean","reason":"STATIC","variant":"on","value":true,"metadata":{}},
    {"key":"broken","errorCode":"PARSE_ERROR","errorDetails":"error parsing the flag `broken`","metadata":{}}
  ],
  "metadata": {"flagSetId":"app-flags", "flagConfigLastModified": 1758400000},   // flag-set metadata; lastModified only when SSE enabled and a stream exists for this selector
  "eventStreams": [{"type":"sse","endpoint":{"requestUri":"/ofrep/v1/sse/flagSetId%3Dapp-flags"},"inactivityDelaySec":120}]  // omitted if --ofrep-sse-enabled=false
}
```

Errors: 400 `{"errorCode":"INVALID_CONTEXT","errorDetails":"Provider context is not valid","metadata":null}` (bad JSON); 400 `{"errorCode":"GENERAL","errorDetails":"invalid selector: …"}`; 500 `{"errorCode":"GENERAL","errorDetails":"Bulk evaluation failed. Tracking ID: <xid>"}`; 413 as above.

**ETag / 304**: every 200 carries a strong `ETag: "<sha256 hex of the response body>"` — it hashes the *response*, so it is correct per context+selector. Send `If-None-Match: "<etag>"` (quoted, unquoted, `W/`, or `*`; comma lists honored) → `304 Not Modified`, empty body, no Content-Type. Exception (ADR-0008 §9): if the request carries `?flagConfigEtag=<x>` and `<x>` differs from the current config version for that selector, flagd returns 200 regardless of `If-None-Match`. `?flagConfigLastModified=` is accepted but not used for conditional logic.

```bash
curl -si -X POST localhost:8016/ofrep/v1/evaluate/flags -H 'Content-Type: application/json' -d '{"context":{"tier":"enterprise"}}' | grep -i etag
curl -si -X POST localhost:8016/ofrep/v1/evaluate/flags -H 'Content-Type: application/json' \
  -H 'If-None-Match: "<etag>"' -d '{"context":{"tier":"enterprise"}}'   # HTTP/1.1 304
```

### 3.4 SSE change stream — `GET /ofrep/v1/sse[/{channel}]`

Enabled by default (`--ofrep-sse-enabled`, default true). `{channel}` is a URL-escaped selector expression (`/ofrep/v1/sse/flagSetId%3Dpayments`); bare `/ofrep/v1/sse` = all flags. 400 on invalid selector, 503 if subscription fails. Response is `text/event-stream`; a `: keep-alive` comment line every 30 s; on configuration change for that channel one event:

```text
event: message
id: <xid>
data: {"type":"refetchEvaluation","etag":"<config sha256>","lastModified":1758400000}
```

Client behaviour (spec): on `refetchEvaluation`, re-POST bulk evaluate with `?flagConfigEtag=<etag>&flagConfigLastModified=<lastModified>`. `--ofrep-sse-inactivity-delay` (120) is advertised as `inactivityDelaySec`; `--ofrep-sse-public-url` sets `endpoint.origin` when flagd is behind a proxy (otherwise clients resolve `requestUri` against their OFREP base URL). Note the SSE `etag` is a *config* version token, distinct from the bulk response `ETag`.

### 3.5 OFREP spec quick facts (open-feature/protocol, openapi 0.3.0)

- Reasons enum: `STATIC, TARGETING_MATCH, SPLIT, DISABLED, UNKNOWN` (flagd also emits `DEFAULT`; spec says reason is free-form).
- Error codes enum: `PARSE_ERROR, TARGETING_KEY_MISSING, INVALID_CONTEXT, GENERAL`; `FLAG_NOT_FOUND` → 404 only. flagd never emits `TARGETING_KEY_MISSING`.
- Value types: boolean, string, integer, number(float), object, or **codeDefault** (no `value` key ⇒ SDK uses code default).
- `metadata` values must be bool/string/number. Bulk `eventStreams[].type` currently only `sse`; unknown types must be ignored.
- Single-flag endpoint = server-side/dynamic-context providers; bulk = client-side/static-context providers (evaluate once, cache, poll or SSE).

Source: docs/reference/flagd-ofrep.md → https://flagd.dev/reference/flagd-ofrep/ ; https://github.com/open-feature/protocol/blob/main/service/openapi.yaml ; https://github.com/open-feature/protocol/blob/main/service/adrs/0008-sse-for-bulk-evaluation-changes.md ; flagd/pkg/service/flag-evaluation/ofrep/{handler.go,etag.go,ofrep_service.go,sse/*.go} ; core/pkg/service/ofrep/models.go

---

## 4. Sync service (:8015)

Purpose: in-process providers (and other flagd instances / flagd-proxy) pull the **flag definition document** and evaluate locally. Default stream = all sources merged (later `--uri` wins on duplicate keys); with a selector, only the matching source/flag set. Requesting a selector that matches no *source* fails (`invalid_argument`); a valid `flagSetId` matching zero flags succeeds with `{"flags":{}}`.

### 4.1 `flagd.sync.v1.FlagSyncService`

| RPC | Request | Response | Notes |
|-----|---------|----------|-------|
| `SyncFlags` | `{provider_id(1), selector(2, deprecated)}` | stream `{flag_configuration(1): string, sync_context(2): optional Struct}` | first message = current full config immediately, then a **full document** on every change (not a diff). `sync_context` = the `-X` static context values, sent on every message. |
| `FetchAllFlags` | `{provider_id(1), selector(2, deprecated)}` | `{flag_configuration(1): string}` | unary; same JSON document as a string. |
| `GetMetadata` | `{}` | `{metadata(2): Struct}` (field 1 reserved) | **deprecated** — same `-X` values as `sync_context`. `--disable-sync-metadata` → `unimplemented` (12). Will default to disabled in later versions. |

- `flag_configuration` is JSON text conforming to https://raw.githubusercontent.com/open-feature/flagd-schemas/main/json/flags.json (`{"$schema"?, "flags": {...}, "$evaluators"?, "metadata"?}`).
- `provider_id`: optional client identity, only used for metrics attributes (`provider_id`) in flagd.
- `selector` body field is deprecated in favour of the `Flagd-Selector` header; header wins if both present. Note the request JSON field is `selector`, header is `Flagd-Selector`.
- Errors: bad selector → `invalid_argument` (3); store/marshal failure → `data_loss` (15) or `internal` (13); `--stream-deadline` hit → `deadline_exceeded` (4); body limit → `resource_exhausted` (8).
- **Keepalive**: `--keep-alive-min-time` and `--keep-alive-permit-without-stream` are accepted but **no-ops** (warning logged if non-default). Served by Connect over `net/http`: no minimum ping interval, pings without active streams allowed, any client keepalive cadence accepted. A connection with zero streams is reclaimed after 5 min. Providers use `streamDeadlineMs` (default 600000) as an application-layer keepalive and reconnect forever with `retryBackoffMaxMs` flat backoff; gRPC retry policy retries `UNAVAILABLE`/`UNKNOWN` 3× (1s, 2s, 4s).
- In-process provider consumption: open `SyncFlags` on init; parse each `flag_configuration` into the local flag set, emit `PROVIDER_CONFIGURATION_CHANGED` with the diffed keys; inject `sync_context` (or legacy `GetMetadata`) into every evaluation context (`contextEnricher` can filter); add `$flagd.flagKey`/`$flagd.timestamp`; provider metadata = top-level `metadata` of the definition. Java example: `FlagdOptions.builder().resolverType(Config.Evaluator.IN_PROCESS).host("localhost").port(8015).selector("myFlags.json")`.

Connect JSON:

```bash
curl -s -X POST localhost:8015/flagd.sync.v1.FlagSyncService/FetchAllFlags -H 'Content-Type: application/json' -d '{}'
# → {"flagConfiguration":"{\"flags\":{\"simple-boolean\":{...}}}"}
curl -s -X POST localhost:8015/flagd.sync.v1.FlagSyncService/FetchAllFlags -H 'Content-Type: application/json' \
  -d '{"providerId":"my-app-sidecar","selector":"flagSetId=payment-flags"}'
curl -s -X POST localhost:8015/flagd.sync.v1.FlagSyncService/GetMetadata -H 'Content-Type: application/json' -d '{}'
# → {"metadata":{"region":"eu"}}   (values from -X)
```

### 4.2 `GET /v1/flags` (same port)

Plain, cacheable HTTP form of `FetchAllFlags`; body is the document itself (byte-identical to `flag_configuration`). Disable with `--sync-http-enabled=false`.

- Selector: `Flagd-Selector` header. Malformed/unknown filter → 400; valid but empty → 200 `{"flags":{}}`.
- Validators: `ETag` (hash of body, exact per selector) and `Last-Modified` (last change to *any* configuration — conservative). `If-None-Match` (precedence) and `If-Modified-Since` honored → `304`.
- Chaining: `flagd start --uri http://other-flagd:8015/v1/flags` or with subset:
  `--sources='[{"uri":"http://other:8015/v1/flags","provider":"http","headers":{"Flagd-Selector":"flagSetId=payments"}}]'`. flagd's HTTP sync sends `If-None-Match` on each poll, so steady state is a bodiless 304.

```bash
curl -si localhost:8015/v1/flags -H 'Flagd-Selector: flagSetId=payments'
curl -si localhost:8015/v1/flags -H 'If-None-Match: "<etag>"'      # 304
```

Source: docs/reference/grpc-sync-service.md → https://flagd.dev/reference/grpc-sync-service/ ; https://github.com/open-feature/flagd-schemas/blob/main/protobuf/flagd/sync/v1/sync.proto ; docs/reference/specifications/providers.md → https://flagd.dev/reference/specifications/providers/ ; flagd/pkg/service/flag-sync/handler.go

---

## 5. Management (:8014)

| Path | Response |
|------|----------|
| `GET /healthz` | always `200` (liveness) |
| `GET /readyz` | `200` when every sync source has delivered its first payload; `412 Precondition Failed` otherwise |
| `GET /metrics` | Prometheus text (default exporter); `--metrics-exporter otel` + `--otel-collector-uri` switches to OTLP push and this stays served |
| gRPC `grpc.health.v1.Health` | on the same port over HTTP/2 `application/grpc` (h2c) |

Readiness definition: `/readyz` is 412 until every sync provider has completed at least one successful sync, then 200 for the life of the process. Metrics of interest (see monitoring reference): `http.server.request.duration` / `http.server.request.body.size` / `http.server.response.body.size` (OTel HTTP semconv, per handler), `feature_flag.flagd.impression` and `feature_flag.flagd.result.reason` (attrs `feature_flag.key`, `feature_flag.result.variant`, `feature_flag.reason`, `feature_flag.provider.name=flagd`), and gRPC sync stream active/duration with `selector`, `provider_id`, exit `reason` (`normal_close|client_disconnect|deadline_exceeded|error`).

Source: docs/reference/cheat-sheet.md#health-check → https://flagd.dev/reference/cheat-sheet/ ; docs/reference/monitoring.md → https://flagd.dev/reference/monitoring/ ; flagd/pkg/service/flag-evaluation/connect_service.go

---

## 6. grpcurl recipes

No reflection: fetch protos first (also on buf: `buf.build/open-feature/flagd`).

```bash
git clone https://github.com/open-feature/flagd-schemas.git
PROTO_DIR=flagd-schemas/protobuf          # contains flagd/evaluation/v1, flagd/evaluation/v2, flagd/sync/v1, schema/v1
G="grpcurl -plaintext -import-path $PROTO_DIR"

# evaluation v2 (unary)
$G -proto flagd/evaluation/v2/evaluation.proto -d '{"flagKey":"simple-boolean","context":{}}' localhost:8013 flagd.evaluation.v2.Service/ResolveBoolean
$G -proto flagd/evaluation/v2/evaluation.proto -d '{"flagKey":"user-tier-flag","context":{"tier":"premium"}}' localhost:8013 flagd.evaluation.v2.Service/ResolveString
$G -proto flagd/evaluation/v2/evaluation.proto -H 'Flagd-Selector: flagSetId=app-flags' -d '{"flagKey":"simple-object","context":{}}' localhost:8013 flagd.evaluation.v2.Service/ResolveObject

# bulk (v1 only)
$G -proto flagd/evaluation/v1/evaluation.proto -d '{"context":{}}' localhost:8013 flagd.evaluation.v1.Service/ResolveAll

# event stream (prints provider_ready, then configuration_change / keep_alive until Ctrl-C)
$G -proto flagd/evaluation/v1/evaluation.proto -d '{}' localhost:8013 flagd.evaluation.v1.Service/EventStream
$G -proto flagd/evaluation/v2/evaluation.proto -H 'Flagd-Selector: flagSetId=payment-flags' -d '{}' localhost:8013 flagd.evaluation.v2.Service/EventStream

# sync
$G -proto flagd/sync/v1/sync.proto -d '{}' localhost:8015 flagd.sync.v1.FlagSyncService/FetchAllFlags
$G -proto flagd/sync/v1/sync.proto -d '{"providerId":"cli","selector":"flagSetId=app-flags"}' localhost:8015 flagd.sync.v1.FlagSyncService/FetchAllFlags
$G -proto flagd/sync/v1/sync.proto -d '{}' localhost:8015 flagd.sync.v1.FlagSyncService/SyncFlags      # streams full config on each change
$G -proto flagd/sync/v1/sync.proto -d '{}' localhost:8015 flagd.sync.v1.FlagSyncService/GetMetadata

# TLS: drop -plaintext, add -cacert ca.pem (and -authority if fronted by a proxy)
```

Expected shapes: `ResolveInt` prints `"value": "50"`; `EventStream` prints `{"type":"provider_ready"}` then e.g. `{"type":"configuration_change","data":{"flags":{"simple-boolean":{"type":"update"}}}}`; `SyncFlags` prints `{"flagConfiguration":"{...}","syncContext":{...}}`.

Source: docs/reference/cheat-sheet.md#proto-files-for-grpcurl → https://flagd.dev/reference/cheat-sheet/ ; https://buf.build/open-feature/flagd

---

## 7. Cheat-sheet essentials and playground

Run (Docker, all ports):

```bash
docker run --rm -it -p 8013:8013 -p 8014:8014 -p 8015:8015 -p 8016:8016 -v $(pwd):/flags \
  ghcr.io/open-feature/flagd:latest start \
  --uri file:./flags/cheat-sheet-flags.json --uri file:./flags/cheat-sheet-flags-payments.json \
  -X region=eu -H "X-User-Tier=tier" -C '*'
# binary: flagd start --uri file:./cheat-sheet-flags.json [--uri https://flagd.dev/assets/cheat-sheet-flags.json]
```

Sample sets: https://flagd.dev/assets/cheat-sheet-flags.json (flagSetId `app-flags`: `simple-boolean`, `simple-string`, `simple-number`, `simple-object`, `user-tier-flag`[tier], `email-based-feature`[email domain], `region-config`[region]) and https://flagd.dev/assets/cheat-sheet-flags-payments.json (flagSetId `payment-flags`: `payment-provider`, `max-transaction-amount`[account-verified], `enable-crypto-payments`[country]). Quick-start file: https://raw.githubusercontent.com/open-feature/flagd/main/docs/assets/demo.flagd.json (`show-welcome-banner` bool, `background-color` string with `company == "initech" → green` targeting; file changes are hot-reloaded — no restart).

Decision table — which protocol to call:

| Need | Call |
|------|------|
| One flag, typed, from a service | `POST :8013/flagd.evaluation.v2.Service/Resolve<Type>` |
| One flag, untyped REST | `POST :8016/ofrep/v1/evaluate/flags/{key}` |
| All flags for a user (client-side) | `POST :8016/ofrep/v1/evaluate/flags` (+ ETag/304, SSE) or `POST :8013/flagd.evaluation.v1.Service/ResolveAll` |
| Raw definition document | `GET :8015/v1/flags` (cacheable) or `FetchAllFlags` |
| Live definition stream (in-process) | `SyncFlags` |
| Change notifications (RPC providers) | `EventStream`; (OFREP clients) `GET :8016/ofrep/v1/sse/{channel}` |
| Readiness | `GET :8014/readyz` |

Context tips: header mapping `-H "X-User-Email=email"` then `curl -H 'X-User-Email: dev@example.com' …`; static `-X environment=production`; body `{"context":{...}}`. Priority: header > static > body.

**Playground** (https://flagd.dev/playground/): in-browser flagd evaluator — no server. Pick a scenario, edit the flag definition (left) and the evaluation context (right), see `value`/`variant`/`reason` live. Scenarios: Basic boolean/numeric/string/object flag, Enable for a specific email domain, Enable based on users locale, Enable based on release version (`sem_ver`), Enable based on the current time (`$flagd.timestamp`), Chainable if/else/then, Multi-variant experiment (`fractional`), Stepped rollout, Gradual rollout, Shared evaluators (`$evaluators`), Boolean variant shorthand, Targeting key, Flag metadata, Code default (targeting returns null → `reason: DEFAULT`, no value). Use it to validate JsonLogic targeting before shipping a definition; it runs the same evaluator semantics as flagd (built from `playground-app/`, published with `make playground-publish`).

Source: docs/reference/cheat-sheet.md → https://flagd.dev/reference/cheat-sheet/ ; docs/quick-start.md → https://flagd.dev/quick-start/ ; docs/playground/index.md → https://flagd.dev/playground/ ; playground-app/src/scenarios/index.ts

---

## 8. RFC: custom gRPC name resolver (`envoy://`)

Status: proposal (`docs/reference/specifications/proposal/`). Problem: providers and flagd's gRPC sync source dial plain `host:port` (DNS resolver). Service meshes / sidecars (Envoy, Istio, Consul) route on the gRPC `:authority` header, so callers need a custom target.

Proposed target string: `envoy://<proxy-host>:<proxy-port>/<service-name>`, e.g. `envoy://localhost:9211/flagd-sync.service` — connect the channel to `localhost:9211` (the sidecar) and set `authority = flagd-sync.service` so the proxy applies its policy/routing to the real backend. Providers expose it via `targetUri` / `FLAGD_TARGET_URI` (documented under providers.md "Custom Name Resolution"); only Java and Go gRPC expose the `NameResolver` interface needed, hence limited language support and inconsistent UX (listed drawbacks).

Alternatives in the RFC: (1) just let users override the default authority header (`grpc.WithAuthority` / `overrideAuthority` / Python channel args) — simple, covers host-header-routing proxies (Java PR open-feature/java-sdk-contrib#949); (2) rely solely on gRPC's built-in `xds://` scheme (no custom code, mesh-native, mTLS handled by gRPC core); (3) TBD. Open questions: unsupported languages, a generic resolver beyond proxies.

Practical takeaway for callers: with grpcurl use `-authority flagd-sync.service localhost:9211`; with hand-written clients set the authority override on the channel when going through an L7 proxy.

Source: docs/reference/specifications/proposal/rfc-grpc-custom-name-resolver.md → https://flagd.dev/reference/specifications/proposal/rfc-grpc-custom-name-resolver/ ; https://grpc.io/docs/guides/custom-name-resolution/
