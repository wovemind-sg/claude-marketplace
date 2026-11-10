# flagd resources: where to look when this skill does not cover it

Worked from the flagd repo at commit `b13483f` (2026-09-18); flagd 0.16.3, core 0.17.0, flagd-proxy 0.9.9. Every URL below returned 200 on 2026-09-21 unless marked `(unverified)`.

## flagd.dev (rendered from `docs/` in the flagd repo)

Start at https://flagd.dev/ ; the search box covers all pages. Page-by-page map (`docs/<path>.md` -> `https://flagd.dev/<path>/`):

| URL | Use it for |
| --- | --- |
| https://flagd.dev/ | What flagd is, feature list, quick links |
| https://flagd.dev/quick-start/ | Docker one-liner, first flag file, first curl |
| https://flagd.dev/installation/ | Docker, binary, release archives, systemd unit |
| https://flagd.dev/playground/ | Browser evaluator: paste flags + context, see result |
| https://flagd.dev/concepts/feature-flagging/ | Terms, code defaults, OpenFeature compliance |
| https://flagd.dev/concepts/syncs/ | Sync source types, merge order, HTTP ETag polling |
| https://flagd.dev/concepts/selectors/ | flagSetId vs source, array flags, multi-tenancy |
| https://flagd.dev/concepts/metadata/ | Set/flag metadata, inheritance, selector reflection |
| https://flagd.dev/architecture/ | RPC vs in-process, sidecar vs central deployment diagrams |
| https://flagd.dev/guides/migrating-to-flag-sets/ | Steps from `source=` to `flagSetId=` selectors |
| https://flagd.dev/providers/ | Provider matrix: which language has RPC / in-process |
| https://flagd.dev/providers/go/ , /java/ , /nodejs/ , /php/ , /dotnet/ , /python/ , /rust/ , /web/ | Provider README mirrored from each contrib repo |
| https://flagd.dev/reference/cheat-sheet/ | Copy-paste curl/grpcurl for every endpoint and port |
| https://flagd.dev/reference/flagd-cli/flagd/ , /flagd_start/ , /flagd_version/ | Every CLI flag with defaults (generated from cobra) |
| https://flagd.dev/reference/sync-configuration/ | `--uri` prefixes, `--sources` JSON fields, OAuth, headers |
| https://flagd.dev/reference/selector-syntax/ | Grammar of `flagSetId=`, `source=`, precedence |
| https://flagd.dev/reference/grpc-sync-service/ | Sync service, `GET /v1/flags`, ETag/Last-Modified |
| https://flagd.dev/reference/flagd-ofrep/ | OFREP endpoints on 8016, SSE, metrics |
| https://flagd.dev/reference/flag-definitions/ | Full flag schema, every JsonLogic op, `$evaluators`, `$flagd.*` |
| https://flagd.dev/reference/custom-operations/fractional-operation/ | Fractional weights, bucketing seed, legacy migration |
| https://flagd.dev/reference/custom-operations/semver-operation/ | `sem_ver` operator forms |
| https://flagd.dev/reference/custom-operations/string-comparison-operation/ | `starts_with` / `ends_with` |
| https://flagd.dev/reference/schema/ | flags.json, targeting.json, flagd.json schema usage |
| https://flagd.dev/reference/monitoring/ | healthz/readyz, Prometheus and OTel metric names, tracing |
| https://flagd.dev/reference/fips-140-3/ | `-fips` images/archives, what FIPS mode restricts |
| https://flagd.dev/reference/specifications/providers/ | Normative provider behaviour, env var table, retry policy |
| https://flagd.dev/reference/specifications/protos/ | Generated protobuf docs for evaluation v1/v2 and sync v1 |
| https://flagd.dev/reference/specifications/custom-operations/fractional-operation-spec/ , /semver-operation-spec/ , /string-comparison-operation-spec/ | Exact semantics providers must implement |
| https://flagd.dev/reference/specifications/proposal/rfc-grpc-custom-name-resolver/ | `envoy://`, `xds://` target URIs |
| https://flagd.dev/reference/openfeature-operator/overview/ | One-paragraph pointer to the operator repo docs |
| https://flagd.dev/reference/naming/ | Naming conventions for flagd artifacts |
| https://flagd.dev/faq/ , https://flagd.dev/troubleshooting/ | FAQ; official troubleshooting page |
| https://flagd.dev/architecture-decisions/<slug>/ | ADRs: `disabled-flag-evaluation`, `support-code-default`, `high-precision-fractional-bucketing`, `fractional-non-string-rand-units`, `decouple-flag-source-and-set`, `duplicate-flag-keys`, `multiple-sync-sources`, `numeric-coercion`, `static-and-dynamic-context`, `semantic-versioning-policy`, `sync-server-keepalive-enforcement`, `targeting-variant-metadata`, `rollout-operator`, `supported-languages`, `cucumber-gherkin-test-suite`, `flag-configuration`, `fractional` |

Published schemas: https://flagd.dev/schema/v0/flags.json (flags + targeting, draft-07), https://flagd.dev/schema/v0/targeting.json (a single `targeting` block), https://flagd.dev/schema/v0/flagd.json (what flagd emits from `GET /v1/flags`). Sample flag files used by the cheat sheet: https://flagd.dev/assets/cheat-sheet-flags.json

## GitHub: open-feature/flagd

- https://github.com/open-feature/flagd : monorepo, Go. `flagd/` (daemon), `core/` (evaluator + syncs, importable), `flagd-proxy/`, `docs/`, `test/` (Gherkin e2e).
- https://github.com/open-feature/flagd/issues : search here first for any error string. https://github.com/open-feature/flagd/discussions for design questions.
- https://github.com/open-feature/flagd/releases : per-component tags (`flagd/v0.16.3`, `core/v0.17.0`), binaries, SBOMs, `-fips` variants.
- Changelogs: https://github.com/open-feature/flagd/blob/main/flagd/CHANGELOG.md and https://github.com/open-feature/flagd/blob/main/core/CHANGELOG.md (the root `CHANGELOG.md` stops at 0.4.2 in 2023; ignore it).
- https://github.com/open-feature/flagd/tree/main/docs : markdown behind flagd.dev; https://github.com/open-feature/flagd/tree/main/docs/architecture-decisions for ADRs (statuses draft/proposed/accepted).
- Samples: https://github.com/open-feature/flagd/tree/main/samples and https://github.com/open-feature/flagd/tree/main/config/samples (`example_flags.json/.yaml`, `.flagd.json` array format). k8s manifests: https://github.com/open-feature/flagd/tree/main/config/deployments
- Source you will actually read: https://github.com/open-feature/flagd/tree/main/core/pkg/evaluator (`json.go` JsonLogic + `$evaluators`, `fractional.go`, `semver.go`, `string_comparison.go`), https://github.com/open-feature/flagd/tree/main/core/pkg/sync (`file/`, `http/`, `grpc/`, `kubernetes/`, `blob/`), `core/pkg/model/error.go` (error codes), `core/pkg/model/reason.go`.
- flagd-proxy: https://github.com/open-feature/flagd/tree/main/flagd-proxy (README + deployment); image `ghcr.io/open-feature/flagd-proxy` at https://github.com/open-feature/flagd/pkgs/container/flagd-proxy ; operator docs https://github.com/open-feature/open-feature-operator/blob/main/docs/flagd_proxy.md
- Contributing / running tests locally: https://github.com/open-feature/flagd/blob/main/CONTRIBUTING.md

## Schemas and protocols

- https://github.com/open-feature/flagd-schemas : source of the JSON schemas (https://github.com/open-feature/flagd-schemas/tree/main/json) and protobuf (https://github.com/open-feature/flagd-schemas/tree/main/protobuf : `flagd/evaluation/v1`, `flagd/evaluation/v2`, `flagd/sync/v1`). Clone it for `grpcurl -import-path`.
- https://buf.build/open-feature/flagd : BSR module, browse messages/services, generate SDKs.
- OFREP: https://github.com/open-feature/protocol (OpenAPI at https://github.com/open-feature/protocol/blob/main/service/openapi.yaml), spec appendix https://openfeature.dev/specification/appendix-c , overview https://openfeature.dev/docs/reference/other-technologies/ofrep/
- https://github.com/open-feature/flagd-testbed : Gherkin suites and container used by every provider for conformance; read it to know exactly what a provider must do.

## OpenFeature SDK and specification

- https://openfeature.dev/specification/ (repo https://github.com/open-feature/spec , files under `specification/`); glossary https://openfeature.dev/specification/glossary (targeting key, flag set, reasons).
- Concepts: https://openfeature.dev/docs/reference/concepts/evaluation-api (detailed evaluation, `reason`/`errorCode`), https://openfeature.dev/docs/reference/concepts/evaluation-context , https://openfeature.dev/docs/reference/concepts/provider (states READY/STALE/ERROR/FATAL), https://openfeature.dev/docs/reference/concepts/events , https://openfeature.dev/docs/reference/concepts/hooks
- Per-language SDK docs: https://openfeature.dev/docs/reference/technologies/ (e.g. https://openfeature.dev/docs/reference/technologies/server/go). Ecosystem/provider list: https://openfeature.dev/ecosystem

## flagd providers (exact paths; README in each is the config reference)

| Language | Path | Package |
| --- | --- | --- |
| Go | https://github.com/open-feature/go-sdk-contrib/tree/main/providers/flagd | https://pkg.go.dev/github.com/open-feature/go-sdk-contrib/providers/flagd |
| Java | https://github.com/open-feature/java-sdk-contrib/tree/main/providers/flagd | https://central.sonatype.com/artifact/dev.openfeature.contrib.providers/flagd |
| Node.js | https://github.com/open-feature/js-sdk-contrib/tree/main/libs/providers/flagd | `@openfeature/flagd-provider` (npm page blocks bots; verified via https://registry.npmjs.org/@openfeature/flagd-provider) |
| Web | https://github.com/open-feature/js-sdk-contrib/tree/main/libs/providers/flagd-web | `@openfeature/flagd-web-provider` (verified via registry) |
| Python | https://github.com/open-feature/python-sdk-contrib/tree/main/providers/openfeature-provider-flagd | https://pypi.org/project/openfeature-provider-flagd/ |
| .NET | https://github.com/open-feature/dotnet-sdk-contrib/tree/main/src/OpenFeature.Providers.Flagd | NuGet `OpenFeature.Providers.Flagd` (older: `OpenFeature.Contrib.Providers.Flagd`) |
| PHP (RPC only) | https://github.com/open-feature/php-sdk-contrib/tree/main/providers/Flagd | https://packagist.org/packages/open-feature/flagd-provider |
| Rust | https://github.com/open-feature/rust-sdk-contrib/tree/main/crates/flagd | crate `open-feature-flagd` (crates.io page blocks bots; verified via API) |

Go core library (embed the evaluator yourself): https://pkg.go.dev/github.com/open-feature/flagd/core , evaluator package https://pkg.go.dev/github.com/open-feature/flagd/core/pkg/evaluator

## Kubernetes

- OpenFeature Operator: https://github.com/open-feature/open-feature-operator ; docs index https://github.com/open-feature/open-feature-operator/tree/main/docs (rendered at https://open-feature.github.io/open-feature-operator/). Key pages: `installation.md`, `quick_start.md`, `concepts.md`, `annotations.md`, `feature_flag.md`, `feature_flag_source.md`, `permissions.md`, `flagd_proxy.md`.
- Helm chart: https://artifacthub.io/packages/helm/open-feature-operator/open-feature-operator (source https://github.com/open-feature/open-feature-operator/tree/main/chart/open-feature-operator). There is no separate flagd chart on Artifact Hub; flagd is deployed by the operator or as a plain Deployment from `config/deployments`.
- Tutorial: https://openfeature.dev/docs/tutorials/open-feature-operator/quick-start/
- Images: https://github.com/open-feature/flagd/pkgs/container/flagd (`ghcr.io/open-feature/flagd:<tag>`, `:latest-fips`). No Docker Hub image (`hub.docker.com/r/openfeature/flagd` is 404).

## Targeting language

- JsonLogic operator reference: https://jsonlogic.com/operations.html ; live tester https://jsonlogic.com/play.html (paste the `targeting` block as rule and the evaluation context as data). flagd adds `fractional`, `sem_ver`, `starts_with`, `ends_with`, `$ref`, and `$flagd.flagKey` / `$flagd.timestamp`, which the playground does not know; use https://flagd.dev/playground/ for those.

## Community

- CNCF Slack `#openfeature` : join via https://slack.cncf.io/ (channel deep link https://cloud-native.slack.com/archives/C0344AANLA1 requires login (unverified)).
- https://github.com/open-feature/community : governance, meeting notes, calendar. https://openfeature.dev/community/ for meeting times.
- YouTube: https://www.youtube.com/@openfeature (community meetings and talk recordings). Demos: https://github.com/open-feature/playground

## Search recipes

- GitHub issues by error string: WebSearch `"<exact error text>" site:github.com/open-feature` ; narrow with `site:github.com/open-feature/flagd/issues`. Provider-side bugs live in the contrib repos: `"<error>" flagd site:github.com/open-feature/java-sdk-contrib` (swap the language).
- Behaviour change hunting: WebSearch `flagd "BREAKING CHANGES" <keyword>` or open `flagd/CHANGELOG.md` and search for `⚠`.
- Grep the source instead of guessing:
  `git clone --depth 1 https://github.com/open-feature/flagd /tmp/flagd && grep -rn '"fractional"\|targetingKey' /tmp/flagd/core/pkg/evaluator/*.go | grep -v _test`
  Error codes: `grep -n 'ErrorCode' /tmp/flagd/core/pkg/model/error.go`. Sync `--sources` fields (the `SourceConfig` struct): `grep -n 'json:"' /tmp/flagd/core/pkg/sync/isync.go`. CLI flags with defaults: `grep -n 'flags\.\(String\|Int32\|Bool\|Duration\|StringToString\|StringSlice\)' /tmp/flagd/flagd/cmd/start.go`.
- When docs are ambiguous about a targeting op, read the Go evaluator (`core/pkg/evaluator/json.go` for `$ref`/context enrichment, `fractional.go` for bucketing, `semver.go`, `string_comparison.go`) and the matching `*_test.go`, which doubles as an example table. The Gherkin features in `test/` and https://github.com/open-feature/flagd-testbed define cross-language expected results.
- Provider env vars and options: read the provider's README at the path in the table above, then confirm against its source, e.g. Go `grep -rn 'FLAGD_' /tmp/go-sdk-contrib/providers/flagd/pkg/`, Java `grep -rn 'FLAGD_' .../providers/flagd/src/main/java/`, JS `grep -rn 'FLAGD_' libs/providers/flagd/src/`. The normative table is https://flagd.dev/reference/specifications/providers/ ; a provider may lag it.
- Schema questions: `curl -s https://flagd.dev/schema/v0/flags.json | jq '.definitions | keys'` then `jq '.definitions.<name>'`.
- Kubernetes/operator: WebSearch `open-feature-operator "<CRD field or error>" site:github.com` ; CRD reference is `kubectl explain featureflagsource.spec` once the operator is installed.
