# flagd troubleshooting

Worked from the flagd repo at commit `b13483f` (2026-09-18), release-please manifest: flagd 0.16.3, core 0.17.0, flagd-proxy 0.9.9.
Default ports: 8013 evaluation (gRPC + Connect/HTTP), 8014 management (`/healthz`, `/readyz`, `/metrics`), 8015 sync (gRPC + `GET /v1/flags`), 8016 OFREP.

## Debug checklist (run in this order)

1. Is flagd up and ready? `curl -i http://localhost:8014/readyz` (liveness: `/healthz`). Not 200 -> a sync source has not delivered its first payload yet; check flagd logs for the source error.
2. Turn on verbose logs: `flagd start --debug ...` (or `-x`, or env `FLAGD_DEBUG=true`); JSON logs with `--log-format json`. In-process providers: enable debug logging in the SDK's own logger.
3. Does flagd actually hold your flags? `curl http://localhost:8015/v1/flags | jq` (raw config as loaded) or `curl -X POST localhost:8013/flagd.evaluation.v1.Service/ResolveAll -H 'Content-Type: application/json' -d '{"context":{}}' | jq`.
4. Evaluate one flag directly, bypassing your SDK: `curl -X POST 'http://localhost:8016/ofrep/v1/evaluate/flags/<key>' -H 'Content-Type: application/json' -d '{"context":{"email":"a@b.com"}}'`. Read `reason` (`STATIC`, `DEFAULT`, `TARGETING_MATCH`, `DISABLED`, `ERROR`) and `errorCode` (`FLAG_NOT_FOUND`, `PARSE_ERROR`, `TYPE_MISMATCH`, `GENERAL`).
5. Validate the flag file against the schema (draft-07): `npx --yes ajv-cli validate -s <(curl -s https://flagd.dev/schema/v0/flags.json) -d flags.json` or `pip install check-jsonschema && check-jsonschema --schemafile https://flagd.dev/schema/v0/flags.json flags.json`. Add `"$schema": "https://flagd.dev/schema/v0/flags.json"` to the file so IDEs validate on save.
6. Same failure through the SDK but not curl? It is the provider: check host/port/resolver mode, `deadlineMs` (default 500 ms), TLS, selector. Watch `PROVIDER_ERROR` / `PROVIDER_STALE` events.
7. Compare against the changelog for behaviour changes: `flagd/CHANGELOG.md` and `core/CHANGELOG.md` (not the stale root `CHANGELOG.md`).

Source: https://flagd.dev/troubleshooting/ , https://flagd.dev/reference/cheat-sheet/ , https://flagd.dev/reference/monitoring/

## Recent breaking changes you will hit when following old docs/blogs

- 0.16.0 (2026-06): a `DISABLED` flag is now a successful evaluation with `reason=DISABLED` and no value/variant; previously an error `FLAG_DISABLED`. Code inspecting `errorCode == FLAG_DISABLED` breaks. ADR: https://flagd.dev/architecture-decisions/disabled-flag-evaluation/
- 0.15.0 (2026-04): fractional bucketing algorithm changed (murmur3 over canonical bytes, `math.MaxInt32` weight space). Bucket assignments differ from pre-0.15 flagd and from older providers. Upgrade flagd and all in-process providers together or users will flip variants.
- 0.14.0 (2026-03): a flag with no `defaultVariant` (or `defaultVariant: null`) now returns `reason=DEFAULT` with `value`/`variant` omitted (SDK uses code default); previously `FLAG_NOT_FOUND`.
- 0.13.0 (2025-12): selectors moved from `source=<file>` to `flagSetId=<id>`; array-based `flags: [...]` format with explicit `key`; `flagSetId + key` is the flag identity.
- 0.12.9: `--disable-sync-metadata` added; the sync `GetMetadata` RPC is deprecated and slated for removal (#2069). Providers that still call it will need updating.
- core 0.17.0 (2026-09): file poll interval configurable (fileinfo watcher default 1000 ms). Not yet exposed in flagd 0.16.3 CLI; check `flagd start --help` on newer builds.
- `--keep-alive-min-time` / `--keep-alive-permit-without-stream` are now no-ops on the sync server (connect over net/http). Keepalive tuning belongs on the client.

Source: https://github.com/open-feature/flagd/blob/main/flagd/CHANGELOG.md , https://github.com/open-feature/flagd/blob/main/core/CHANGELOG.md

## Problems, causes, fixes

### 1. Provider stuck in NOT_READY / `connection refused` / `PROVIDER_ERROR` on init

Symptom: SDK never emits `PROVIDER_READY`; logs show `connection refused`, `UNAVAILABLE`, or `provider initialization deadline exceeded`.
Cause (pick): wrong port for the resolver mode (RPC talks to 8013, in-process talks to the sync service on 8015); flagd not listening on the interface (Docker without `-p 8013:8013 -p 8015:8015`); `deadlineMs` default 500 ms too short for a cold start or a remote flagd; TLS mismatch (provider `tls=true`, flagd plaintext).
Fix: set `FLAGD_RESOLVER=in-process` with `FLAGD_PORT=8015` (Java: `FLAGD_SYNC_PORT`), or `FLAGD_RESOLVER=rpc` with port 8013. Confirm from the app's network namespace: `curl -sf http://flagd:8014/readyz`. Raise `FLAGD_DEADLINE_MS=2000` for init. Provider spec env var table: https://flagd.dev/reference/specifications/providers/
Related: after `shutdown()` not every provider can be re-initialised (#2048); create a new provider instance instead.
Source: https://github.com/open-feature/flagd/issues/2048 , https://github.com/open-feature/js-sdk-contrib/issues/936

### 2. `/readyz` is 200 but evaluations return FLAG_NOT_FOUND right after start; or `/healthz` stays 200 after the sync source died

Symptom: first requests after a pod passes readiness get `FLAG_NOT_FOUND`; or HTTP sync target is down, flagd keeps answering `/healthz` 200, gRPC health `SERVING`, but evaluation port refuses connections.
Cause: readiness is derived from the sync provider signalling "ready" before the payload is applied to the store (race of 14-51 ms, #2047); health endpoints do not reflect sync failures (#1614). Multi-gRPC-source readiness bug fixed in core 0.16.1 (#1985).
Fix: add a startup probe or `initialDelaySeconds` and have the SDK wait for `PROVIDER_READY` before serving; in k8s use `readinessProbe: httpGet: {path: /readyz, port: 8014}` plus a small `initialDelaySeconds`. For #1614 restart the process (`kill -9` was the only workaround reported). Track PR #2049/#2050.
Source: https://github.com/open-feature/flagd/issues/2047 , https://github.com/open-feature/flagd/issues/1614

### 3. In-process provider gets no flags / `FLAG_NOT_FOUND` for flags that exist (selector mismatch)

Symptom: `ResolveAll` on flagd shows the flags, but the in-process provider (or `GET /v1/flags` with a selector) returns `{"flags":{}}`.
Cause: selector `flagSetId=x` does not match `metadata.flagSetId` in the config (case-sensitive), old `source=` selector after the file was renamed, wrong syntax (`flagSetId:x` or bare `x`), or an empty value (`flagSetId=` matches only flags with no flagSetId). `Flagd-Selector` header overrides body selector, which overrides the provider's configured selector.
Fix: `curl -H 'Flagd-Selector: flagSetId=my-app' http://localhost:8015/v1/flags` - 400 means malformed selector, 200 with empty flags means valid but no match. Then check `metadata.flagSetId` at top level and per-flag overrides. Test once with no selector to confirm the flags load at all. Set the provider selector with `FLAGD_SOURCE_SELECTOR=flagSetId=my-app`.
Source: https://flagd.dev/troubleshooting/#selector-issues , https://flagd.dev/reference/selector-syntax/

### 4. Migrating to flag sets: which flags belong to which set

Symptom: after adding `flagSetId` some flags disappear from one provider and appear in another; duplicate keys behave unpredictably.
Cause: flag identity is `flagSetId + key`. A flag-level `metadata.flagSetId` overrides the top-level one. The same `flagSetId + key` in two sources has undefined precedence.
Fix: put `"metadata": {"flagSetId": "my-app"}` at the top of each file; change provider selectors from `source=path.json` to `flagSetId=my-app`; verify with `curl -H 'Flagd-Selector: flagSetId=my-app' -X POST http://localhost:8016/ofrep/v1/evaluate/flags` (note: the guide's example uses port 8014, OFREP is 8016). Old `source=` selectors still work.
Source: https://flagd.dev/guides/migrating-to-flag-sets/ , https://flagd.dev/concepts/selectors/

### 5. Targeting rule returns the default unexpectedly (`reason: DEFAULT`)

Symptom: rule looks right, evaluation returns `defaultVariant` with `reason=DEFAULT`, or `reason=ERROR` with `PARSE_ERROR`/`GENERAL`.
Cause: the JsonLogic returned `null`, or a variant name that does not exist in `variants` (falls back to default). Typical: context key spelled differently than `{"var": "email"}`; the key was sent as a top-level SDK attribute but the rule expects `targetingKey`; `==` coerces types but `===` does not (`{"===":[1,"1"]}` is false); `in` argument order (`{"in": ["@x.com", {"var":"email"}]}` = substring, needle first); `starts_with`/`ends_with` need string operands (absent property is logged at debug since #2065, not an error); `$flagd.flagKey`/`$flagd.timestamp` misspelled; header-mapped `-H` and static `-X` context override body context.
Fix: reproduce with curl and an explicit context: `curl -X POST localhost:8016/ofrep/v1/evaluate/flags/<key> -H 'Content-Type: application/json' -d '{"context":{"email":"a@example.com","targetingKey":"u1"}}'`. Paste the rule into https://jsonlogic.com/play.html with the same data. Run flagd with `--debug` to see rule evaluation. Make the rule return a variant name string, not `true`/`false` (unless your variants are literally named `"true"`/`"false"`).
Source: https://flagd.dev/reference/flag-definitions/#targeting-rules , https://github.com/open-feature/flagd/pull/2065

### 6. Fractional is not sticky / users flip between variants

Symptom: the same user gets different variants across requests, services, or SDK languages.
Cause: no bucketing expression and no `targetingKey` in context (pre-0.15.5 this errored or fell to default; #1949); bucketing on a value that changes per request (`$flagd.timestamp`, request id); the bucketing expression resolves to a non-string (cast with `cat`); mixed flagd/provider versions across the 0.15.0 bucketing change; Rust in-process provider used a different divisor before rust-sdk-contrib#102 was fixed.
Fix: always seed with the flag key and a stable identity: `"fractional": [{"cat": [{"var": "$flagd.flagKey"}, {"var": "email"}]}, ["on", 50], ["off", 50]]`, or omit the expression and always send `targetingKey`. Weights are relative (need not sum to 100). Upgrade every in-process provider to a version that implements the high-precision bucketing ADR.
Source: https://flagd.dev/reference/custom-operations/fractional-operation/ , https://github.com/open-feature/flagd/issues/1949 , https://github.com/open-feature/rust-sdk-contrib/issues/102

### 7. File sync does not pick up changes (Docker bind mount, k8s ConfigMap) or fires too many events

Symptom: editing the flag file changes nothing until restart; or one save triggers several `configuration_change` events.
Cause: k8s updates ConfigMap volumes by atomically swapping the `..data` symlink, and editors write-temp-then-rename; both replace the inode, so a watch on the old file sees nothing. `file` uses `fsnotify` when flagd detects k8s and a 1 s `fileinfo` stat poller elsewhere. Some bind mounts (Docker Desktop on macOS, NFS) do not deliver inotify events at all. Multiple events per save are normal editor/FS behaviour.
Fix: force the poller: `--sources='[{"uri":"/flags/flags.json","provider":"fileinfo"}]'`. In production watch a symlink and update its target (single atomic event; this is how OFO `file` mode works). Core 0.16.1 fixed re-watching after delete+restore (#2001). ConfigMap propagation itself takes up to the kubelet sync period (~60 s); `subPath` mounts never update.
Source: https://flagd.dev/troubleshooting/#extra-duplicate-events-in-file-syncs , https://flagd.dev/reference/sync-configuration/ , https://github.com/open-feature/flagd/issues/2001

### 8. `flagd start` fails: unsupported extension, invalid sync URI, YAML parse errors

Symptom: startup errors like `invalid sync uri`, file with `.yml`/`.json` required, or YAML that "looks fine" fails to parse.
Cause: `--uri` values need a scheme prefix (`file:`, `http(s)://`, `grpc(s)://`, `gs://`, `azblob://`, `s3://`, `core.openfeature.dev/ns/name`); with `--sources` the `uri` field has no scheme and `provider` picks the implementation. Serialization is decided by extension (`.json`, `.yaml`, `.yml`) or, for HTTP, the media type. YAML maps with non-string keys (e.g. `on:`/`yes:` parsed as booleans, numeric keys) broke parsing before core 0.16.1 (#1990); quote such keys.
Fix: `flagd start --uri file:./flags.yaml` (relative path allowed) or `--uri file:/etc/flagd/flags.json`. Quote YAML keys like `"on"`/`"off"` under `variants`. Validate with the schema one-liner in the checklist (convert YAML first: `yq -o=json flags.yaml > /tmp/f.json`).
Source: https://flagd.dev/reference/sync-configuration/#uri-patterns , https://flagd.dev/reference/flagd-cli/flagd_start/

### 9. Schema validation failures / `$evaluators` `$ref` not resolved

Symptom: IDE or `ajv` reports errors; flagd logs `transposing evaluators`, `unmarshalling provided configurations`, or `evaluator object is empty`; a rule with `{"$ref": "name"}` always falls to default.
Cause: `$evaluators` is top-level (sibling of `flags`), and the `$ref` name must match exactly. flagd resolves refs by literal substitution of `{"$ref":"name"}`, so a `$ref` object with extra keys is not replaced. An empty evaluator `{}` is rejected. Common schema errors: `state` missing or not `ENABLED`/`DISABLED`; `variants` of mixed types; `defaultVariant` not a key of `variants`; legacy `fractionalEvaluation` with a bare string instead of `{"var": "email"}`.
Fix: keep `$ref` objects as exactly `{"$ref": "emailWithFaas"}`; define `"$evaluators": {"emailWithFaas": {...}}` at top level. Run the schema validator; the flags schema also validates each `targeting` block, and https://flagd.dev/schema/v0/targeting.json validates a rule alone.
Source: https://flagd.dev/reference/flag-definitions/#shared-evaluators , https://flagd.dev/reference/schema/

### 10. HTTP `ResolveInt` returns a string; OFREP returns numbers fine

Symptom: `{"value":"1", ...}` from `/flagd.evaluation.v2.Service/ResolveInt`.
Cause: proto3 JSON mapping encodes int64 as a string.
Fix: use `ResolveFloat` (returns a JSON number) or OFREP `/ofrep/v1/evaluate/flags/<key>`. Numeric coercion across accessors (int vs float, overflow) is being standardised in the numeric-coercion ADR; expect `TYPE_MISMATCH` for lossy conversions.
Source: https://flagd.dev/troubleshooting/#http-integer-response-behavior , https://github.com/open-feature/flagd/issues/1978

### 11. `Received unexpected EOS on empty DATA frame from server` / gRPC stream drops behind a proxy

Symptom: in-process or RPC provider connects then errors with the EOS message, `DEADLINE_EXCEEDED`, or reconnect loops (`Provider did not reconnect successfully within 5s`, then `PROVIDER_ERROR`).
Cause: the load balancer / ingress / mesh is not passing HTTP/2 (gRPC needs it for the sync and event streams), has an idle timeout shorter than the stream, or drops keepalive pings.
Fix: enable HTTP/2 or gRPC backend protocol on the proxy (e.g. `appProtocol: grpc` on the k8s Service, nginx `grpc_pass`, ALB gRPC target group). Set `FLAGD_STREAM_DEADLINE_MS` below the proxy idle timeout so the client cycles the stream cleanly; server-side `--stream-deadline`. Retry knobs: `FLAGD_RETRY_BACKOFF_MS`, `FLAGD_RETRY_BACKOFF_MAX_MS`, `FLAGD_RETRY_GRACE_PERIOD` (STALE -> ERROR after 10 s). Custom resolvers: `envoy://host:port/service`.
Source: https://flagd.dev/troubleshooting/#received-unexpected-eos-on-empty-data-frame-from-server , https://flagd.dev/reference/specifications/providers/ , https://github.com/open-feature/flagd/issues/2053

### 12. TLS errors: `certificate signed by unknown authority`, `x509: certificate relies on legacy Common Name`

Symptom: `grpcs://` sync or provider `tls=true` fails the handshake.
Cause: server cert has no SANs (Go rejects CN-only certs since 1.15); CA not provided to the client; provider `tls` flag not set while flagd runs with `--server-cert-path`/`--server-key-path`.
Fix: issue a cert with `subjectAltName=DNS:flagd,DNS:localhost,IP:127.0.0.1`; on flagd `flagd start -c server.crt -k server.key ...`; client side `FLAGD_TLS=true` and `FLAGD_SERVER_CERT_PATH=/certs/ca.crt`; for flagd-as-client sync `{"uri":"host:8015","provider":"grpc","tls":true,"certPath":"/certs/ca.crt"}`. FIPS builds (`ghcr.io/open-feature/flagd:latest-fips`) reject non-approved ciphers/curves; test your proxy's cipher suite.
Source: https://github.com/open-feature/flagd-testbed/issues/410 , https://flagd.dev/reference/fips-140-3/

### 13. Port conflicts / wrong port

Symptom: `bind: address already in use`; or the SDK connects but gets HTTP 404 / `unimplemented` (talking to the wrong service).
Cause: four listeners by default (8013/8014/8015/8016); another flagd (e.g. the OFO sidecar) or the app already owns a port; provider pointed at 8013 for in-process (needs 8015) or at 8014 for OFREP (needs 8016).
Fix: `flagd start -p 9013 -m 9014 -g 9015 -r 9016`, or Unix sockets `-d /tmp/flagd.sock` / `-e /tmp/flagd-sync.sock`. Check with `lsof -iTCP:8013 -sTCP:LISTEN`. Disable what you do not use: `--sync-http-enabled=false`, `--ofrep-sse-enabled=false`.
Source: https://flagd.dev/reference/flagd-cli/flagd_start/ , https://flagd.dev/reference/cheat-sheet/#default-ports

### 14. Browser / web provider blocked by CORS, `Flagd-Selector` header rejected

Symptom: browser console: `No 'Access-Control-Allow-Origin' header`, or preflight fails only when a selector is set.
Cause: flagd sends no CORS headers unless `--cors-origin` is set; before 0.14.3 the OFREP CORS middleware omitted `AllowedHeaders`, so `Flagd-Selector` preflights failed (#1900).
Fix: `flagd start -C 'https://app.example.com' -C 'http://localhost:5173' ...` (or `-C '*'` for local dev). Upgrade to >= 0.14.3. The web provider uses OFREP/Connect on 8016/8013 over HTTP/1.1, so no HTTP/2 is needed, but the browser must reach flagd's public URL (`--ofrep-sse-public-url` when behind a proxy).
Source: https://github.com/open-feature/flagd/issues/1900 , https://flagd.dev/providers/web/

### 15. OFREP returns 404 / 405 / 413

Symptom: `404` on `/ofrep/v1/evaluate/flags/<key>`; `405`; `413 Request Entity Too Large`.
Cause: 404 with a JSON body and `errorCode: FLAG_NOT_FOUND` means the key is not loaded (check selector, `GET :8015/v1/flags`); a bare 404 means wrong port (OFREP is 8016, not 8013/8014) or path (`/ofrep/v1/evaluate/flags`, POST only, so GET gives 405). 413 is the 1 MB default body limit (`--max-request-body`), 431 for headers (`--max-request-header`).
Fix: `curl -i -X POST http://localhost:8016/ofrep/v1/evaluate/flags/<key>`; compare against `curl :8015/v1/flags`. Bulk evaluate returns `ETag`; send `If-None-Match` to get 304s. Change notifications: SSE at `/ofrep/v1/sse/{selector}` (0.16.3+).
Source: https://flagd.dev/reference/flagd-ofrep/ , https://github.com/open-feature/protocol

### 16. `value`/`variant` missing from the response

Symptom: `{"reason":"DEFAULT","metadata":{}}` or `{"reason":"DISABLED"}` with no `value`.
Cause: intentional since 0.14.0/0.16.0: no `defaultVariant` (code default) or `state: DISABLED` delegates to the SDK's code default.
Fix: set `defaultVariant` if you want a server-side default; otherwise handle the absent value client-side (SDKs already do).
Source: https://flagd.dev/troubleshooting/#variantvalue-not-included-in-response

### 17. OpenFeature Operator: sidecar not injected / sidecar has no flags

Symptom: pod has only the app container; or flagd sidecar runs but logs `not found` for the FeatureFlag CR, or app gets `connection refused` on 8013.
Cause: missing annotations (both are required): `openfeature.dev/enabled: "true"` and `openfeature.dev/featureflagsource: "<name>"` or `"<ns>/<name>"` on the pod template (not the Deployment metadata); FeatureFlagSource in another namespace without the `ns/` prefix; the mutating webhook did not run (operator pod not ready, namespace excluded, pod created before operator install); GitOps reconciling away the ClusterRoleBinding the operator adds for the pod's service account, so the sidecar cannot read FeatureFlag CRs.
Fix: `kubectl get pod <p> -o jsonpath='{.spec.containers[*].name}'` should list `flagd`; `kubectl logs <p> -c flagd`; `kubectl get featureflagsource,featureflag -A`; `kubectl describe mutatingwebhookconfiguration | grep -A3 openfeature`; restart the Deployment after fixing annotations. For restricted RBAC use the `flagd-proxy` source type instead of direct CR access.
Source: https://github.com/open-feature/open-feature-operator/blob/main/docs/feature_flag_source.md , https://github.com/open-feature/open-feature-operator/blob/main/docs/annotations.md , https://github.com/open-feature/open-feature-operator/blob/main/docs/permissions.md

### 18. Memory growth / metrics cardinality; zombie after metrics server failure

Symptom: RSS climbs with unique flag keys or context; flagd stays alive but useless when the metrics port fails.
Cause: unbounded metric label cardinality (fixed 0.15.1, #1931); zombie process on metrics server bind failure (fixed 0.15.1, #1926).
Fix: upgrade to >= 0.15.1; scrape `http://localhost:8014/metrics`; for OTLP use `--metrics-exporter otel --otel-collector-uri host:4317`.
Source: https://github.com/open-feature/flagd/blob/main/flagd/CHANGELOG.md , https://flagd.dev/reference/monitoring/

## FAQ (condensed)

- Why not environment variables? Env vars need a restart and cannot target users, randomise, or schedule rollouts. If a value is truly static, env vars are fine.
- Why "flagd"? Unix daemon naming convention; see https://flagd.dev/reference/naming/
- Relationship to OpenFeature? flagd is an OpenFeature sub-project and aims to be fully OpenFeature-compliant.
- How do I run it? Standalone daemon (sidecar, central service, or local binary) over gRPC/HTTP/OFREP, or embedded via in-process providers reading from a file or the sync service. See https://flagd.dev/architecture/ and https://flagd.dev/installation/
- SBOM? Attached to GitHub releases; container SBOM: `docker buildx imagetools inspect ghcr.io/open-feature/flagd:latest --format '{{ json (index .SBOM "linux/amd64").SPDX }}'`
- Missing feature? Open an issue or PR at https://github.com/open-feature/flagd/issues

Source: https://flagd.dev/faq/
