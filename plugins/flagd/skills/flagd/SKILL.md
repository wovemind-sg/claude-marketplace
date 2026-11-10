---
name: flagd
description: Complete reference for flagd (https://flagd.dev), the CNCF/OpenFeature feature-flag evaluation engine. Use whenever the user mentions flagd, flagd-proxy, the OpenFeature Operator, OFREP, `flagSetId`, a `*.flagd.json`/`*.flagd.yaml` file, `$evaluators`, `fractional`/`sem_ver` targeting, or the OpenFeature flagd provider in any language (Go, Java, Node, web, Python, .NET, PHP, Rust). Also trigger when the user wants self-hosted / open-source / vendor-neutral feature flags, percentage rollouts, A/B variants or context-based targeting via OpenFeature, even if they never say "flagd" — flagd is the reference OpenFeature backend. Covers writing and debugging flag definitions, running flagd (Docker, binary, Kubernetes, systemd), sync sources, RPC vs in-process providers, calling flagd over gRPC/Connect/OFREP, monitoring, and troubleshooting.
---
# flagd — OpenFeature flag evaluation engine

flagd = stateless Go daemon (or embeddable engine) that loads flag definitions from **sync sources** (file, http, gRPC, Kubernetes CRD), merges them, evaluates flags with **JSON Logic** targeting, and serves results over gRPC/Connect (:8013), OFREP REST (:8016) and a sync stream for in-process providers (:8015). No UI, no DB — the flag file *is* the source of truth (git-ops it). Current release: flagd v0.16.x (Sep 2026), image `ghcr.io/open-feature/flagd`.

Reference docs bundled in this skill (`references/`) — read the one matching the task, not all:

| Task | Read |
|------|------|
| Write / fix a flag file, targeting rule, rollout, semver gate, `$evaluators`, metadata | `references/flag-definitions.md` |
| Install, run, configure `flagd start`, `--sources`, Docker/k8s/systemd, flag sets & selectors, metrics, flagd-proxy | `references/deployment.md` |
| Wire an app: OpenFeature SDK + flagd provider per language, rpc vs in-process vs offline, provider env vars | `references/providers.md` |
| Call flagd directly: curl/grpcurl, evaluation v1/v2 protos, OFREP, sync service, EventStream, `GET /v1/flags` | `references/api.md` |
| Something not working; FAQ; debug checklist; recent breaking changes | `references/troubleshooting.md` |
| Topic not covered here → where to look online | `references/resources.md` |

## Mental model (30 seconds)

```
 flag sources ──sync──▶ flagd (merge + evaluate) ──▶ :8013 evaluation gRPC/Connect  ◀── RPC provider
 file / http /                                   ──▶ :8016 OFREP REST               ◀── web/any HTTP client
 grpc / k8s CRD                                  ──▶ :8015 sync stream + GET /v1/flags ◀── in-process provider
                                                 ──▶ :8014 /healthz /readyz /metrics
```

Two ways to evaluate:
- **RPC mode** — app's flagd provider asks flagd over gRPC per evaluation (cached, invalidated via `EventStream`). Simple clients, ~ms latency, flagd runs as sidecar/service.
- **In-process mode** — provider pulls the whole flag config via the sync service (or a local file, "offline mode") and evaluates locally. Zero I/O per evaluation; needs flagd/flagd-proxy only as a sync source.
Pick RPC for polyglot/simple setups and central control; in-process for hot paths, edge, or when you don't want a sidecar. Both use the same flag file format and the same OpenFeature SDK code — only provider construction differs.

## Quick start (copy-paste)

```bash
# flags.flagd.json  (the .flagd.json suffix gives IDE schema autocompletion)
cat > flags.flagd.json <<'JSON'
{
  "$schema": "https://flagd.dev/schema/v0/flags.json",
  "flags": {
    "show-welcome-banner": {
      "state": "ENABLED",
      "variants": { "on": true, "off": false },
      "defaultVariant": "off",
      "targeting": {
        "if": [ { "ends_with": [ { "var": "email" }, "@initech.com" ] }, "on" ]
      }
    }
  }
}
JSON

docker run --rm -it -p 8013:8013 -p 8014:8014 -p 8015:8015 -p 8016:8016 \
  -v "$PWD":/flags ghcr.io/open-feature/flagd:latest start --uri file:./flags/flags.flagd.json

# OFREP (simplest)
curl -s -X POST localhost:8016/ofrep/v1/evaluate/flags/show-welcome-banner \
  -H 'Content-Type: application/json' -d '{"context":{"email":"a@initech.com"}}'
# Connect/HTTP-JSON onto the gRPC evaluation service
curl -s -X POST localhost:8013/flagd.evaluation.v2.Service/ResolveBoolean \
  -H 'Content-Type: application/json' -d '{"flagKey":"show-welcome-banner","context":{}}'
curl -s localhost:8014/readyz
```
Edits to the file are picked up live (no restart). `reason` in the response tells you what happened: `STATIC` (no targeting), `DEFAULT` (targeting fell through), `TARGETING_MATCH`, `DISABLED`, `ERROR`.

## Flag definition essentials

- Top level: `$schema`, `flags` (map key → flag), optional `$evaluators` (shared JSON Logic snippets referenced with `{"$ref":"name"}`), optional `metadata` (e.g. `flagSetId`).
- Flag: `state` (`ENABLED`|`DISABLED`), `variants` (name → value; all values same JSON type), `defaultVariant`, optional `targeting` (JSON Logic that must return a **variant name** or `null` → falls to default), optional `metadata`.
- Targeting reads evaluation context via `{"var":"key"}` (dot paths ok); reserved: `targetingKey`, `$flagd.flagKey`, `$flagd.timestamp` (unix seconds).
- Custom ops: `fractional` (weighted pseudo-random bucketing by `targetingKey` by default — pass a custom bucket expression as the first element to bucket by e.g. `email`), `sem_ver` (`=`, `!=`, `<`, `<=`, `>`, `>=`, `^`, `~`), `starts_with`, `ends_with`. Standard JSON Logic (`if`, `==`/`===`, `in`, `and`/`or`, `!`, `<`, `cat`, …) all work.
- `DISABLED` flag → provider returns code default with reason `DISABLED`; targeting that returns an unknown variant → `ERROR`/`GENERAL`.
- YAML accepted (`.flagd.yaml`); same shape. Validate: `npx ajv-cli validate -s https://flagd.dev/schema/v0/flags.json -d flags.flagd.json` (or the playground at https://flagd.dev/playground/).
Full field tables, operator semantics, 8 worked examples → `references/flag-definitions.md`.

## Deployment essentials

- Sources: `--uri file:path` (watched), `--uri https://…` (polled every 5s by default, ETag-aware; set `interval` via `--sources`), `--uri grpc(s)://host:port` (stream from flagd / flagd-proxy / your own sync server), `--uri core.openfeature.dev/ns/name` (k8s `FeatureFlag` CRD). Repeat `--uri` for many; use `--sources '[{...}]'` JSON when you need auth headers, TLS, `selector`, `providerID`, `interval`.
- Multiple sources merge; **later sources win** on duplicate keys. Group flags with `metadata.flagSetId` and filter via `Flagd-Selector: flagSetId=…` header or provider `selector`.
- Static context for every evaluation: `-X key=value`. Map request headers into context: `-H "X-User-Tier=tier"`. Priority: header-mapped > static > request body.
- Kubernetes: install the OpenFeature Operator, define `FeatureFlag` + `FeatureFlagSource`, annotate the workload with the `openfeature.dev/*` annotations to inject a flagd sidecar or in-process config — exact annotation names in `references/deployment.md` (operator docs: https://github.com/open-feature/open-feature-operator/tree/main/docs).
- Env-var form of every flag: `FLAGD_<FLAG_IN_UPPER_SNAKE>` (e.g. `FLAGD_PORT`, `FLAGD_LOG_FORMAT=json`). Metrics: Prometheus on `:8014/metrics` or `--metrics-exporter otel --otel-collector-uri …`.
Full CLI table, `--sources` schema, systemd/k8s/compose manifests → `references/deployment.md`.

## Provider essentials

All languages: install OpenFeature SDK + `flagd` provider → `OpenFeature.setProvider(new FlagdProvider({...}))` → `client = OpenFeature.getClient()` → `client.getBooleanValue("key", default, {targetingKey, email, …})`. Provider options are the same everywhere: `host`/`port` (8013 rpc, 8015 in-process), `resolverType` (`rpc` | `in-process` | `file`), `tls`, `certPath`, `selector`, `offlineFlagSourcePath`, `cache`/`maxCacheSize`, `providerId`; each also reads `FLAGD_HOST`, `FLAGD_PORT`, `FLAGD_RESOLVER`, `FLAGD_SOURCE_SELECTOR`, `FLAGD_OFFLINE_FLAG_SOURCE_PATH`, `FLAGD_TLS`, … Browser: `@openfeature/flagd-web-provider` (static context, bulk evaluation over OFREP/Connect). Exact package names, constructors and snippets per language → `references/providers.md`.

## Working rules

1. **Always set `targetingKey`** in evaluation context when a flag uses `fractional` with the default bucketing; without it the evaluation errors and falls to the code default. Bucket on another attribute by passing an expression (e.g. `{"var":"email"}`) as the first `fractional` element.
2. **Targeting must return a variant *name*, not a value.** `"if":[cond, true]` is a bug; write `"if":[cond, "on"]`.
3. **Keep all variants the same type** and call the matching `get<Type>Value`; type mismatch → `TYPE_MISMATCH` error and code default.
4. **Prefer `.flagd.json` naming + `$schema`** so editors validate; validate in CI before deploying — a malformed file is rejected as a whole and flagd keeps serving the previous good state.
5. **Don't reach for a UI** — flagd has none by design; flags live in git / a ConfigMap / an HTTP endpoint you control. If the user wants a hosted UI, point them at OpenFeature-compatible vendors, but flagd itself stays file-driven.
6. **Check `reason` and `errorCode`** before blaming targeting: `DEFAULT` means the rule evaluated but matched nothing; `FLAG_NOT_FOUND` often means the wrong selector / flag set.
7. When the docs bundled here are silent or ambiguous, follow `references/resources.md`: read the live page on https://flagd.dev/, grep the source (`git clone --depth 1 https://github.com/open-feature/flagd`, evaluator lives in `core/pkg/evaluator`), or search issues on https://github.com/open-feature/flagd/issues. Say which source you used.
