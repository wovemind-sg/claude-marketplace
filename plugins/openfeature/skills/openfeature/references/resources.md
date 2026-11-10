# OpenFeature resources: where to look when this skill does not cover it

Worked from local clones taken 2026-09-21: `open-feature/spec` @ 24f98d7, `openfeature.dev` docs @ 9e19e66, `go-sdk` 1.18.0 @ 213d8f7, `python-sdk` 0.10.0 @ a1b9c69, `dotnet-sdk` 2.14.1 @ 385ef26, plus the three `*-sdk-contrib` repos and `open-feature/protocol` @ 56d798e. Every URL below returned HTTP 200 on 2026-09-21 unless marked otherwise. The SDKs move fast (Python is pre-1.0, .NET DI/Hosting and multi-provider are "experimental"); when a snippet here does not compile, trust the live source over this skill and say so.

## Decision tree

| You need | Go to |
| --- | --- |
| The normative rule ("must the SDK throw?", "what is the merge order?") | Spec: https://openfeature.dev/specification/ (section URLs below); machine-readable list https://github.com/open-feature/spec/blob/main/specification.json |
| How a concept is *explained*, with per-language snippets | https://openfeature.dev/docs/reference/concepts/<evaluation-api\|provider\|evaluation-context\|hooks\|events\|sdk-paradigms\|tracking> |
| The exact API of one SDK | The SDK README (rendered at https://openfeature.dev/docs/reference/sdks/server/<lang> or `/client/<lang>`), then the source (`git clone --depth 1`) |
| Which provider/hook exists for a vendor and language | https://openfeature.dev/ecosystem (filter by type/technology/vendor); raw data in https://github.com/open-feature/openfeature.dev/tree/main/src/datasets |
| A provider's constructor options / env vars | Its README in the contrib repo (paths below), then `grep` its source |
| An error string | GitHub issues search scoped to `org:open-feature` (recipes below) |
| Getting-started tutorials with a runnable app | https://openfeature.dev/docs/tutorials/getting-started/<go\|python\|dotnet\|node\|php\|rust> , `/java/spring-boot` , `/java/dropwizard` ; https://openfeature.dev/docs/tutorials/five-minutes-to-feature-flags (Node, also on https://killercoda.com/open-feature/scenario/five-minutes-to-feature-flags) |
| flagd / Kubernetes operator | The sibling `flagd` skill; https://flagd.dev/ ; https://openfeature.dev/docs/tutorials/open-feature-operator/quick-start |

## openfeature.dev (rendered from `docs/` in github.com/open-feature/openfeature.dev)

| URL | Use it for |
| --- | --- |
| https://openfeature.dev/ | Landing page, links to docs / spec / ecosystem / community / blog |
| https://openfeature.dev/docs/reference/intro | What feature flags and OpenFeature are; component overview (evaluation API, context, providers, hooks, events) |
| https://openfeature.dev/docs/reference/concepts/evaluation-api | Setting a provider, clients, basic vs detailed evaluation, evaluation-details field table (TS/Java/C#/Go/PHP/Python tabs) |
| https://openfeature.dev/docs/reference/concepts/provider | Provider responsibilities, naming conventions, domain-scoped providers, multi-provider, implementation checklist + FAQ (targeting key, errors, disabled flags, unsupported types) |
| https://openfeature.dev/docs/reference/concepts/evaluation-context | Global/client/invocation context, merging, static-context SDKs, targeting key, PII |
| https://openfeature.dev/docs/reference/concepts/hooks | Stages before/after/error/finally, ordering, implementing hooks (Go/Python/… snippets) |
| https://openfeature.dev/docs/reference/concepts/events | Handlers on client vs API, event types incl. RECONCILING / CONTEXT_CHANGED |
| https://openfeature.dev/docs/reference/concepts/sdk-paradigms | Dynamic-context (server) vs static-context (client) |
| https://openfeature.dev/docs/reference/concepts/tracking | Tracking API rationale and snippets |
| https://openfeature.dev/docs/reference/sdks/ and https://openfeature.dev/docs/reference/sdks/sdk-compatibility | Every SDK with version, spec version and feature matrix |
| https://openfeature.dev/docs/reference/sdks/server/go , /dotnet , /python , /java , /javascript , /javascript/nestjs , /php , /ruby , /rust , /cpp , /dart | Server SDK pages = the repo README rendered |
| https://openfeature.dev/docs/reference/sdks/client/web , /web/react , /web/angular , /kotlin , /swift , /dart | Client SDK pages |
| https://openfeature.dev/docs/reference/other-technologies/ofrep and /ofrep/openapi | OFREP overview and the rendered OpenAPI |
| https://openfeature.dev/docs/reference/other-technologies/cli | `openfeature` CLI: install, `init` / `manifest` / `compare` / `generate` / `pull` / `push`, manifest schema, `.openfeature.yaml` |
| https://openfeature.dev/docs/reference/other-technologies/mcp | OpenFeature MCP server (`npx -y @openfeature/mcp`), editor configs, `OPENFEATURE_OFREP_*` env vars |
| https://openfeature.dev/docs/tutorials/open-feature-cli | CLI walkthrough |
| https://openfeature.dev/docs/reference/contributing | How to contribute docs / add a provider or hook to the ecosystem page |
| https://openfeature.dev/ecosystem | Filterable catalogue of providers, hooks, OFREP APIs, integrations |
| https://openfeature.dev/community | Meetings calendar, Slack, contributing |
| https://openfeature.dev/blog | Announcements, release notes, deep dives (e.g. spec releases, new SDK features) |

## Specification (github.com/open-feature/spec, `specification/`)

| URL | Content |
| --- | --- |
| https://openfeature.dev/specification/ | Index + conformance rules (RFC 2119 keywords under H5 headings; each is one numbered requirement) |
| https://openfeature.dev/specification/glossary | Roles, client, provider, domain, evaluation context, targeting key, flag set, paradigms |
| https://openfeature.dev/specification/types | Evaluation/resolution details, full `Reason`, `Error Code`, `Provider Status`, `Provider Events` tables, flag metadata, tracking event details |
| https://openfeature.dev/specification/sections/flag-evaluation | §1 API singleton, provider registration/domains, clients, evaluation, details, shutdown, transaction context, isolated API instances |
| https://openfeature.dev/specification/sections/providers | §2 provider interface, lifecycle (initialize/shutdown), status, events emitted by providers, context reconciliation |
| https://openfeature.dev/specification/sections/evaluation-context | §3 structure, merge order (Requirement 3.2.3), transaction context propagator |
| https://openfeature.dev/specification/sections/hooks | §4 hook context, hints, stages, ordering (4.4.2), error semantics (4.4.3–4.4.7), hook data |
| https://openfeature.dev/specification/sections/events | §5 event types, handlers, status mapping |
| https://openfeature.dev/specification/sections/tracking | §6 `track` API and tracking event details |
| https://openfeature.dev/specification/appendix-a | Included utilities: in-memory provider, multi-provider strategies, logging hook, no-op provider |
| https://openfeature.dev/specification/appendix-b | Gherkin suites shared across SDKs |
| https://openfeature.dev/specification/appendix-c | OFREP appendix |
| https://openfeature.dev/specification/appendix-d | Observability: OpenTelemetry semantic conventions for flag evaluation |
| https://openfeature.dev/specification/appendix-e | Migrations (spec version changes, e.g. provider-emitted events) |
| https://github.com/open-feature/spec/releases | Spec version tags (SDK READMEs badge the version they implement) |
| https://github.com/open-feature/spec/issues and https://github.com/orgs/open-feature/discussions | Design discussions; https://github.com/open-feature/ofep holds accepted enhancement proposals (e.g. `OFEP/provider-client-mapping.md` for domains) |

Grep the spec instead of reading it: `git clone --depth 1 https://github.com/open-feature/spec /tmp/of-spec && grep -rn "Requirement 3.2.3" -A2 /tmp/of-spec/specification/sections/` or `jq '.rules[] | select(.id=="Requirement 1.4.10")' /tmp/of-spec/specification.json` (check the actual key names with `jq 'keys'` first).

## SDK repositories and package pages

| Language | Repo | Package / API docs | Contrib (providers + hooks) |
| --- | --- | --- | --- |
| Go | https://github.com/open-feature/go-sdk | https://pkg.go.dev/github.com/open-feature/go-sdk/openfeature (the authoritative API reference; sub-packages `hooks`, `memprovider`, `multi`, `isolated`) | https://github.com/open-feature/go-sdk-contrib (`providers/<name>`, `hooks/<name>`, each its own Go module) |
| .NET | https://github.com/open-feature/dotnet-sdk (`src/OpenFeature`, `src/OpenFeature.DependencyInjection`, `src/OpenFeature.Hosting`, `src/OpenFeature.Providers.MultiProvider`, `samples/AspNetCore`, `docs/AOT_COMPATIBILITY.md`) | https://www.nuget.org/packages/OpenFeature , https://www.nuget.org/packages/OpenFeature.DependencyInjection , https://www.nuget.org/packages/OpenFeature.Hosting | https://github.com/open-feature/dotnet-sdk-contrib/tree/main/src (`OpenFeature.Providers.*` new naming, `OpenFeature.Contrib.Providers.*` older) |
| Python | https://github.com/open-feature/python-sdk | https://pypi.org/project/openfeature-sdk/ (no hosted API docs: https://open-feature.github.io/python-sdk/ is 404 — read docstrings in `openfeature/`) | https://github.com/open-feature/python-sdk-contrib (`providers/openfeature-provider-<name>`, `hooks/openfeature-hooks-opentelemetry`) |
| Java | https://github.com/open-feature/java-sdk | Maven `dev.openfeature:sdk` | https://github.com/open-feature/java-sdk-contrib/tree/main/providers |
| JS/TS (Node, web, React, Angular, NestJS) | https://github.com/open-feature/js-sdk (`packages/server`, `packages/web`, `packages/react`, `packages/angular`, `packages/nest`, `packages/shared`) | npm `@openfeature/server-sdk`, `@openfeature/web-sdk`, `@openfeature/react-sdk`, `@openfeature/angular-sdk`, `@openfeature/nestjs-sdk`, `@openfeature/core` | https://github.com/open-feature/js-sdk-contrib/tree/main/libs/providers (+ `libs/hooks`) |
| Kotlin / Android | https://github.com/open-feature/kotlin-sdk | | https://github.com/open-feature/kotlin-sdk-contrib (unverified) |
| Swift / iOS | https://github.com/open-feature/swift-sdk | | |
| PHP | https://github.com/open-feature/php-sdk | Packagist `open-feature/sdk` | https://github.com/open-feature/php-sdk-contrib |
| Ruby | https://github.com/open-feature/ruby-sdk | gem `openfeature-sdk` | |
| Rust | https://github.com/open-feature/rust-sdk | crate `open-feature` | https://github.com/open-feature/rust-sdk-contrib |
| C++ | https://github.com/open-feature/cpp-sdk | | |
| Dart | https://github.com/open-feature/dart-server-sdk (client SDK repo listed on the ecosystem page) | | |

All repos: https://github.com/orgs/open-feature/repositories . Package names for the non-Go/.NET/Python rows are as listed in `references/other-sdks.md`; verify on the registry before pinning a version.

## Protocol, tooling, testing

- **OFREP**: https://github.com/open-feature/protocol — OpenAPI at https://github.com/open-feature/protocol/blob/main/service/openapi.yaml , provider-author guidelines `guideline/dynamic-context-provider.md` and `guideline/static-context-provider.md`. Rendered at https://openfeature.dev/docs/reference/other-technologies/ofrep/openapi .
- **CLI**: https://github.com/open-feature/cli — command docs under `docs/commands/openfeature_<cmd>.md`, manifest JSON schema https://raw.githubusercontent.com/open-feature/cli/refs/heads/main/schema/v0/flag-manifest.json , sync API `api/v0/sync.yaml`, installer https://openfeature.dev/scripts/install_cli.sh , image `ghcr.io/open-feature/cli`.
- **MCP server**: https://github.com/open-feature/mcp (npm `@openfeature/mcp`, registry entry `dev.openfeature/mcp` on https://registry.modelcontextprotocol.io).
- **Conformance tests**: https://github.com/open-feature/flagd-testbed (Gherkin + containers every provider/SDK runs against), spec Gherkin under `spec/specification/assets/gherkin/`.
- **flagd** (reference backend): https://github.com/open-feature/flagd , https://flagd.dev/ ; **Operator**: https://github.com/open-feature/open-feature-operator ; **Playground / demos**: https://github.com/open-feature/playground , https://github.com/open-feature/five-minutes-to-feature-flags .

## Community

- CNCF project page https://www.cncf.io/projects/openfeature/ (accepted 2022-06-17, Incubating since 2023-11-21); landscape entry https://landscape.cncf.io/?item=observability-and-analysis--feature-flagging--openfeature .
- Slack: `#openfeature` on CNCF Slack — join via https://slack.cncf.io/ (deep links https://cloud-native.slack.com/archives/C0344AANLA1 and, for the CLI, `C07DY4TUDK6` return 403 without login). Governance, meeting notes and calendar: https://github.com/open-feature/community ; meeting times on https://openfeature.dev/community .
- YouTube (community meetings, talks): https://www.youtube.com/@openfeature . Blog: https://openfeature.dev/blog .

## Search recipes

- **Error string** → WebSearch `"<exact error text>" site:github.com/open-feature` ; narrow to the SDK (`site:github.com/open-feature/go-sdk/issues`) or the contrib repo for provider bugs. GitHub search UI: `org:open-feature "<text>"` in issues.
- **Behaviour change / breaking change** → open the SDK's `CHANGELOG.md` and search `⚠ BREAKING` or the method name; spec changes → https://openfeature.dev/specification/appendix-e and https://github.com/open-feature/spec/releases .
- **"Does SDK X support feature Y?"** → https://openfeature.dev/docs/reference/sdks/sdk-compatibility (matrix generated from `src/datasets/sdks/sdk-compatibility.json`).
- **Exact signature** → clone and grep, do not guess:
  - Go: `git clone --depth 1 https://github.com/open-feature/go-sdk /tmp/go-sdk && grep -n "^func " /tmp/go-sdk/openfeature/openfeature.go /tmp/go-sdk/openfeature/client.go`
  - Python: `git clone --depth 1 https://github.com/open-feature/python-sdk /tmp/py-sdk && grep -n "^def \|^    def " /tmp/py-sdk/openfeature/api.py /tmp/py-sdk/openfeature/client.py`
  - .NET: `git clone --depth 1 https://github.com/open-feature/dotnet-sdk /tmp/dotnet-sdk && grep -rn "public .*(" /tmp/dotnet-sdk/src/OpenFeature/Api.cs /tmp/dotnet-sdk/src/OpenFeature/IFeatureClient.cs` ; DI extension methods: `grep -rn "public static" /tmp/dotnet-sdk/src/OpenFeature.DependencyInjection /tmp/dotnet-sdk/src/OpenFeature.Hosting`
- **Provider options / env vars** → the provider README in the contrib repo, then e.g. `grep -rn "FLAGD_" providers/flagd/pkg/` (Go), `grep -rn "FLAGD_" providers/openfeature-provider-flagd/src/` (Python), `grep -rn "FLAGD_" src/OpenFeature.Providers.Flagd/` (.NET).
- **Which vendors speak OFREP / have a provider in language X** → https://openfeature.dev/ecosystem?instant_search%5BrefinementList%5D%5Btype%5D%5B0%5D=Provider&instant_search%5BrefinementList%5D%5Btechnology%5D%5B0%5D=Go (swap `Go`), or read `src/datasets/providers/*.ts` and `src/datasets/ofrep-api/*.ts` in the openfeature.dev repo.
- **Vendor-specific provider behaviour** (LaunchDarkly, ConfigCat, Split, DevCycle, ...) → the vendor hosts the provider in its own org; follow the link from the ecosystem card, then the vendor's docs. The contrib repos only hold community-maintained providers.
