# OpenFeature ecosystem: providers, hooks, OFREP, tooling, community

Everything around the SDKs: which providers exist for which vendor and language, the hooks and integrations catalogue, the OpenFeature Remote Evaluation Protocol (OFREP), the CLI and MCP server, the Kubernetes operator, migration guidance, commercial support and community links.

Source of truth: the datasets under `src/datasets/` in https://github.com/open-feature/openfeature.dev (which render https://openfeature.dev/ecosystem), the `open-feature/protocol` repo, and the spec appendices, as cloned in 2026-09. Anything not present in those sources is marked `(unverified)`.

## Table of contents

1. [Provider catalogue](#provider-catalogue)
   - [Open-source backends and self-hosted systems](#open-source-backends-and-self-hosted-systems)
   - [Commercial vendors](#commercial-vendors)
   - [Cloud and config-store providers](#cloud-and-config-store-providers)
   - [Utility providers](#utility-providers)
   - [Providers by language](#providers-by-language)
2. [Hooks catalogue](#hooks-catalogue)
3. [Integrations](#integrations)
4. [OFREP: OpenFeature Remote Evaluation Protocol](#ofrep-openfeature-remote-evaluation-protocol)
5. [OpenFeature CLI](#openfeature-cli)
6. [OpenFeature MCP server](#openfeature-mcp-server)
7. [OpenFeature Operator and flagd on Kubernetes](#openfeature-operator-and-flagd-on-kubernetes)
8. [Migrating between vendors](#migrating-between-vendors)
9. [Commercial support](#commercial-support)
10. [Community](#community)
11. [When this file is silent](#when-this-file-is-silent)

## Provider catalogue

The dataset records, per provider, one entry per language with `vendorOfficial` (true = maintained by the vendor, false = community-maintained, usually in an `open-feature/*-sdk-contrib` repo) and `category` (Server = dynamic context, Client = static context). The grouping into open-source / commercial / cloud / utility below is editorial; the dataset itself has no such field.

Language key: Java, Go, .NET, PHP, Py = Python, Rb = Ruby, Rs = Rust, Dart; JS(S) = JavaScript server (Node.js, also usable from NestJS), JS(C) = JavaScript client (Web, also usable from React and Angular); Nest, React, Ang = framework-specific packages; Kt = Kotlin/Android, Sw = Swift/iOS. "contrib" means the code lives in the corresponding `open-feature/<lang>-sdk-contrib` repository.

### Open-source backends and self-hosted systems

| Provider | Languages | Where | Notes |
|---|---|---|---|
| flagd | JS(S), JS(C) (`flagd-web`), Go, Java, .NET, PHP, Py, Rs | all in contrib repos, e.g. https://github.com/open-feature/js-sdk-contrib/tree/main/libs/providers/flagd, https://github.com/open-feature/go-sdk-contrib/tree/main/providers/flagd, https://github.com/open-feature/java-sdk-contrib/tree/main/providers/flagd, https://github.com/open-feature/dotnet-sdk-contrib/tree/main/src/OpenFeature.Providers.Flagd, https://github.com/open-feature/php-sdk-contrib/tree/main/providers/Flagd, https://github.com/open-feature/python-sdk-contrib/tree/main/providers/openfeature-provider-flagd, https://github.com/open-feature/rust-sdk-contrib/tree/main/crates/flagd | OpenFeature's own flag daemon; also speaks OFREP. See the sibling `flagd` skill |
| GO Feature Flag | Go, Java, .NET, PHP, Py, Rb, Rs, JS(S), Nest, JS(C), React, Ang, Kt, Sw | https://gofeatureflag.org/docs/sdk/server_providers/openfeature_<lang> and `client_providers/openfeature_<lang>` | Widest language coverage of any provider; also an OFREP API |
| Flipt | Go, Java, JS(S), JS(C) (`flipt-web`), Rs (vendor-official, in contrib), Py (community, contrib) | https://github.com/open-feature/go-sdk-contrib/tree/main/providers/flipt and siblings | Also an OFREP API |
| Unleash | JS(S) (vendor), Kt, PHP, Py, Rb, Rs, Sw (vendor, `github.com/Unleash/unleash-openfeature-*-provider`); Go, Java, .NET, JS(C) `unleash-web` (+React, Angular) community in contrib | https://github.com/Unleash/unleash-openfeature-node-provider etc.; https://github.com/open-feature/js-sdk-contrib/tree/main/libs/providers/unleash-web | Mix of vendor and community packages |
| Flagsmith | Go, Java, JS(S), JS(C) `flagsmith-client`, .NET, Rb, Rs (contrib, vendor-official); Kt, Py, Sw (`github.com/Flagsmith/flagsmith-openfeature-*`) | https://github.com/open-feature/go-sdk-contrib/tree/main/providers/flagsmith etc. | |
| FeatBit | Java, .NET, JS(S), JS(C) | https://github.com/featbit/featbit-openfeature-provider-java-server, https://github.com/featbit/openfeature-provider-dotnet-server, https://github.com/featbit/openfeature-provider-node-server, https://github.com/featbit/openfeature-provider-js-client | |
| Featurevisor | JS(C), JS(S), Go, Sw, Java, Rb, Py, PHP | https://featurevisor.com/docs/sdks/<lang>/#open-feature | Git-ops, build-time datafiles |
| Bucketeer | Sw, Kt, JS(C) (+React), JS(S), Go | https://github.com/bucketeer-io/openfeature-swift-client-sdk and siblings; npm `@bucketeer/openfeature-js-client-sdk`, `@bucketeer/openfeature-node-server-sdk` | |
| Nona | JS(S) (`nona-openfeature-provider`), JS(C) (`nona-openfeature-web-provider`), .NET (`Nona.OpenFeature.Provider`) | npm / NuGet | Self-hosted flags and remote config |
| Superposition (Juspay) | Java, JS(S), Py, Rs, Kt | https://github.com/juspay/superposition (clients/...) | |
| Switchbox | JS(C), React, Py | https://github.com/ignat14/switchbox-sdk-js/tree/main/packages/openfeature, https://switchbox.dev/docs/sdk/openfeature | |
| Feat | JS(C), JS(S), Dart (server) | https://github.com/feathq/openfeature-web, https://github.com/feathq/js-sdk, https://github.com/feathq/openfeature-dart | |
| Intellitoggle | Dart (server) | https://github.com/aortem/intellitoggle-openfeature-provider-dart-server | Only third-party Dart provider besides Feat |
| Flipswitch | JS(C), JS(S), Ang, Nest, React, .NET, Go, Java, PHP, Py, Rb, Rs, Sw | https://docs.flipswitch.io/docs/sdks/<lang> | Also an OFREP API |

### Commercial vendors

| Provider | Languages | Where | Notes |
|---|---|---|---|
| LaunchDarkly | JS(S), Java, .NET, PHP, Py, Rb (vendor, `github.com/launchdarkly/openfeature-<lang>-server`); JS(C) `launchdarkly-client` and Go are community (contrib) | https://github.com/launchdarkly/openfeature-node-server etc.; https://github.com/open-feature/js-sdk-contrib/tree/main/libs/providers/launchdarkly-client; https://github.com/open-feature/go-sdk-contrib/tree/main/providers/launchdarkly | Commercial support listed |
| Split | JS(S), JS(C), Go, Java, .NET, Sw, Kt (vendor); PHP community (contrib) | https://github.com/splitio/split-openfeature-provider-<lang> | |
| Harness | Go (community, contrib) | https://github.com/open-feature/go-sdk-contrib/tree/main/providers/harness | Harness Feature Management & Experimentation is on the commercial-support list |
| ConfigCat | JS(S) `config-cat`, JS(C) `config-cat-web`, Go, Java, .NET (vendor-official, in contrib); Nest, Ang, React docs; PHP, Py, Rs, Rb, Kt, Sw (`github.com/configcat/openfeature-<lang>`) | https://configcat.com/docs/sdk-reference/openfeature/ | Also an OFREP API |
| DevCycle | JS(S), Nest, Java, Go, .NET, PHP, Py, Rb, JS(C), React, Ang, Sw, Kt | https://docs.devcycle.com/sdk/<server-side-sdks|client-side-sdks>/<lang>/<lang>-openfeature/ | OpenFeature-native SDKs; also an OFREP API |
| Statsig | .NET, Go, Java (community, contrib) | https://github.com/open-feature/dotnet-sdk-contrib/tree/main/src/OpenFeature.Contrib.Providers.Statsig etc. | |
| PostHog | JS(S), JS(C), Py (vendor); JS(S) `@tapico/node-openfeature-posthog` and Go (community) | https://github.com/PostHog/posthog-js/tree/main/packages/openfeature-node-provider, `.../openfeature-web-provider`, https://github.com/PostHog/posthog-python/tree/main/openfeature-provider | |
| GrowthBook | JS(C) (docs), JS(S) (contrib), Py, Java, Go, .NET | https://docs.growthbook.io/lib/openfeature; https://github.com/growthbook/growthbook-openfeature-provider-<lang> | |
| Optimizely | Go, Java (community, contrib) | https://github.com/open-feature/go-sdk-contrib/tree/main/providers/optimizely, https://github.com/open-feature/java-sdk-contrib/tree/main/providers/optimizely | |
| Kameleoon | .NET, Java, Py, Go, Rb, PHP, JS(S), Kt, Sw, JS(C) | https://github.com/Kameleoon-new/openfeature-<lang> | |
| Datadog | JS(S), JS(C), React, Sw, Kt, Go, .NET, Java, Py, Rb, PHP | https://docs.datadoghq.com/feature_flags/<server|client>/<lang>/ | Datadog Feature Flags; distinct from the Datadog tracing hook |
| Confidence by Spotify | JS(S), JS(C), Java, Kt, Sw, Py, Go | https://github.com/spotify/confidence-sdk-<lang> | |
| CloudBees | JS(S), JS(C), Go, Java, .NET, Py (vendor); PHP community (contrib) | https://github.com/cloudbees-oss/cloudbees-openfeature-provider-<lang> | |
| AB Tasty (Flagship) | JS(S), JS(C), Sw | https://github.com/flagship-io/openfeature-provider-js, `-js-client`, `-iOS` | |
| Mixpanel | Go, Java, JS(S), JS(C), Kt, Py, Rb, Sw | inside the Mixpanel SDK repos, e.g. https://github.com/mixpanel/mixpanel-go/tree/main/openfeature | |
| Hypertune | JS(S), JS(C) | npm `@hypertune/openfeature-server-provider`, `@hypertune/openfeature-web-provider` | |
| Hyphen AI | .NET, Java, JS(C), JS(S), Py, Sw (vendor); Go community | https://github.com/Hyphen/openfeature-provider-<lang> | |
| Pendo | JS(S), JS(C) | npm `@pendo/openfeature-server-provider`, `@pendo/openfeature-web-provider` | |
| Reflag | JS(S), JS(C) | https://github.com/reflagcom/javascript/tree/main/packages/openfeature-node-provider, `openfeature-browser-provider` | |
| Tggl | JS(S), JS(C), .NET | https://tggl.io/developers/sdks/open-feature/<node|web|dotnet> | Commercial support listed |
| VWO | JS(S), .NET, Java, PHP, Py, Go | https://github.com/wingify/vwo-openfeature-provider-<lang> | Commercial support listed |
| Featureflip | JS(S), .NET, Py, Go, Java, PHP | https://featureflip.io/docs/integrations/openfeature/ | Commercial support listed |
| Octopus Deploy | .NET, Java, JS(C) | https://github.com/OctopusDeploy/openfeature-provider-<dotnet|java|ts-web> | |
| Prefab | Go (community, contrib) | https://github.com/open-feature/go-sdk-contrib/tree/main/providers/prefab | |
| ConfigBee | JS(C) | https://github.com/configbee/cb-openfeature-provider-web | |
| ConfigDirector | JS(C), JS(S) | https://docs.configdirector.com/sdks/<browser|server>/openfeature-<web|node> | |

### Cloud and config-store providers

| Provider | Languages | Where | Notes |
|---|---|---|---|
| AWS SSM (Parameter Store) | JS(S), Go (community, contrib) | https://github.com/open-feature/js-sdk-contrib/tree/main/libs/providers/aws-ssm, https://github.com/open-feature/go-sdk-contrib/tree/main/providers/aws-ssm | |
| Azure App Configuration | JS(S) (community, contrib) | https://github.com/open-feature/js-sdk-contrib/tree/main/libs/providers/azure-app-configuration | |
| Firebase Remote Config | Sw (community) | https://github.com/fumito-ito/FirebaseRemoteConfig-OpenFeature-Provider-Swift | |
| Cloudflare Flagship | JS(C), JS(S), Go, Py | https://developers.cloudflare.com/flagship/sdk/<client-provider|server-provider|go|python>/ | |
| Vercel Flags | JS(S) | https://vercel.com/docs/flags/vercel-flags/sdks/openfeature | The reverse direction (Vercel Flags SDK consuming OpenFeature providers) is at https://flags-sdk.dev/docs/api-reference/adapters/openfeature |
| GCP | none listed | | No Google Cloud provider appears in the dataset `(unverified)` |
| MongoDB + Rules | Go (community) | https://github.com/ZackarySantana/openfeature-go | Rules evaluated against MongoDB documents |

### Utility providers

These are not vendors; they solve testing, local development, composition or protocol needs.

| Provider | Languages | Where | Use |
|---|---|---|---|
| In-memory | built into the SDKs (`InMemoryProvider` in Java, C++, Ruby, Dart; `TypedInMemoryProvider` in the JS SDKs; see the other-SDKs file) | SDK repos | Unit tests and demos |
| Environment Variable | Go (`from-env`), Java (`env-var`), JS(S) (`env-var`), Rs (`env-var`) | https://github.com/open-feature/go-sdk-contrib/tree/main/providers/from-env, https://github.com/open-feature/java-sdk-contrib/tree/main/providers/env-var, https://github.com/open-feature/js-sdk-contrib/tree/main/libs/providers/env-var, https://github.com/open-feature/rust-sdk-contrib/tree/main/crates/env-var | Flags from env vars, no backend |
| Multi-Provider | JS(S), JS(C) (in the SDK), Java (contrib `providers/multiprovider`), .NET (in the SDK, `OpenFeature.Providers.MultiProvider`); also documented in PHP, Kotlin, Swift, Dart server SDKs | https://github.com/open-feature/js-sdk/tree/main/packages/server#multi-provider, https://github.com/open-feature/java-sdk-contrib/tree/main/providers/multiprovider, https://github.com/open-feature/dotnet-sdk/tree/main/src/OpenFeature.Providers.MultiProvider | Compose providers with a strategy; migrations and fallbacks (see below) |
| OFREP | JS(C) `ofrep-web`, JS(S) `ofrep`, Go, Py, .NET, Java | see the OFREP section | Generic provider for any OFREP-speaking backend |
| UserDefaults | Sw (community) | https://github.com/fumito-ito/UserDefaults-OpenFeature-Provider-Swift | Flags from Apple `UserDefaults` |

### Providers by language

Derived mechanically from the same dataset (counts include utility providers). React, Angular and NestJS rows list only packages published specifically for that framework; every JavaScript Client provider also works with React and Angular, and every JavaScript Server provider with NestJS, which is how the ecosystem page itself presents them.

| Language | Side | Count | Providers |
|---|---|---|---|
| JavaScript | Server | 39 | AB Tasty, AWS SSM, Azure App Configuration, Bucketeer, CloudBees, Cloudflare Flagship, Confidence by Spotify, ConfigCat, ConfigDirector, Datadog, DevCycle, Environment Variable, Feat, FeatBit, Featureflip, Featurevisor, Flagsmith, Flipswitch, Flipt, GO Feature Flag, GrowthBook, Hypertune, Hyphen AI, Kameleoon, LaunchDarkly, Mixpanel, Multi-Provider, Nona, OFREP, Pendo, PostHog, Reflag, Split, Superposition, Tggl, Unleash, VWO, Vercel Flags, flagd |
| JavaScript | Client | 35 | AB Tasty, Bucketeer, CloudBees, Cloudflare Flagship, Confidence by Spotify, ConfigBee, ConfigCat, ConfigDirector, Datadog, DevCycle, Feat, FeatBit, Featurevisor, Flagsmith, Flipswitch, Flipt, GO Feature Flag, GrowthBook, Hypertune, Hyphen AI, Kameleoon, LaunchDarkly, Mixpanel, Multi-Provider, Nona, OFREP, Octopus Deploy, Pendo, PostHog, Reflag, Split, Switchbox, Tggl, Unleash, flagd |
| Go | Server | 31 | AWS SSM, Bucketeer, CloudBees, Cloudflare Flagship, Confidence by Spotify, ConfigCat, Datadog, DevCycle, Environment Variable, Featureflip, Featurevisor, Flagsmith, Flipswitch, Flipt, GO Feature Flag, GrowthBook, Harness, Hyphen AI, Kameleoon, LaunchDarkly, Mixpanel, MongoDB + Rules, OFREP, Optimizely, PostHog, Prefab, Split, Statsig, Unleash, VWO, flagd |
| Java | Server | 28 | CloudBees, Confidence by Spotify, ConfigCat, Datadog, DevCycle, Environment Variable, FeatBit, Featureflip, Featurevisor, Flagsmith, Flipswitch, Flipt, GO Feature Flag, GrowthBook, Hyphen AI, Kameleoon, LaunchDarkly, Mixpanel, Multi-Provider, OFREP, Octopus Deploy, Optimizely, Split, Statsig, Superposition, Unleash, VWO, flagd |
| .NET | Server | 23 | CloudBees, ConfigCat, Datadog, DevCycle, FeatBit, Featureflip, Flagsmith, Flipswitch, GO Feature Flag, GrowthBook, Hyphen AI, Kameleoon, LaunchDarkly, Multi-Provider, Nona, OFREP, Octopus Deploy, Split, Statsig, Tggl, Unleash, VWO, flagd |
| Python | Server | 24 | CloudBees, Cloudflare Flagship, Confidence by Spotify, ConfigCat, Datadog, DevCycle, Featureflip, Featurevisor, Flagsmith, Flipswitch, Flipt, GO Feature Flag, GrowthBook, Hyphen AI, Kameleoon, LaunchDarkly, Mixpanel, OFREP, PostHog, Superposition, Switchbox, Unleash, VWO, flagd |
| PHP | Server | 14 | CloudBees, ConfigCat, Datadog, DevCycle, Featureflip, Featurevisor, Flipswitch, GO Feature Flag, Kameleoon, LaunchDarkly, Split, Unleash, VWO, flagd |
| Ruby | Server | 11 | ConfigCat, Datadog, DevCycle, Featurevisor, Flagsmith, Flipswitch, GO Feature Flag, Kameleoon, LaunchDarkly, Mixpanel, Unleash (no flagd or OFREP provider listed) |
| Rust | Server | 9 | ConfigCat, Environment Variable, Flagsmith, Flipswitch, Flipt, GO Feature Flag, Superposition, Unleash, flagd |
| Dart | Server | 2 | Feat, Intellitoggle |
| Kotlin | Client | 12 | Bucketeer, Confidence by Spotify, ConfigCat, Datadog, DevCycle, Flagsmith, GO Feature Flag, Kameleoon, Mixpanel, Split, Superposition, Unleash |
| Swift | Client | 17 | AB Tasty, Bucketeer, Confidence by Spotify, ConfigCat, Datadog, DevCycle, Featurevisor, Firebase Remote Config, Flagsmith, Flipswitch, GO Feature Flag, Hyphen AI, Kameleoon, Mixpanel, Split, Unleash, UserDefaults |
| React | Client | 8 | Bucketeer, ConfigCat, Datadog, DevCycle, Flipswitch, GO Feature Flag, Switchbox, Unleash |
| Angular | Client | 5 | ConfigCat, DevCycle, Flipswitch, GO Feature Flag, Unleash |
| NestJS | Server | 4 | ConfigCat, DevCycle, Flipswitch, GO Feature Flag |

No providers are listed for C++ or for the Dart client SDK.

## Hooks catalogue

| Hook | Purpose | Languages and location |
|---|---|---|
| OpenTelemetry Trace | Adds flag evaluation metadata (key, variant, provider, reason, and so on) to the active OpenTelemetry span | JS(S) https://github.com/open-feature/js-sdk-contrib/tree/main/libs/hooks/open-telemetry; Go https://github.com/open-feature/go-sdk-contrib/tree/main/hooks/open-telemetry; Java https://github.com/open-feature/java-sdk-contrib/tree/main/hooks/open-telemetry; PHP https://github.com/open-feature/php-sdk-contrib/tree/main/hooks/OpenTelemetry; .NET https://github.com/open-feature/dotnet-sdk/tree/main/src/OpenFeature/Hooks (in the SDK itself); Python https://github.com/open-feature/python-sdk-contrib/tree/main/hooks/openfeature-hooks-opentelemetry. The Dart server SDK ships its own `OpenTelemetryHook` |
| Datadog | Adds evaluation metadata to a Datadog (DDTrace) trace | PHP only: https://github.com/open-feature/php-sdk-contrib/tree/main/hooks/DDTrace |
| Sentry | Adds evaluation metadata to Sentry events (vendor-official) | JS https://docs.sentry.io/platforms/javascript/configuration/integrations/openfeature/; Python https://docs.sentry.io/platforms/python/configuration/integrations/openfeature/ (both tagged Client in the dataset) |
| Validator | Validates the result of an evaluation (for example a hex colour matches a regex) and errors if it does not | Go https://github.com/open-feature/go-sdk-contrib/tree/main/hooks/validator; PHP https://github.com/open-feature/php-sdk-contrib/tree/main/hooks/Validators |
| Debounce | Rate-limits ("debounces") other hooks; recommended in the React and Angular docs to stop UI re-renders inflating evaluation telemetry | JS server and client: https://github.com/open-feature/js-sdk-contrib/tree/main/libs/hooks/debounce |

Several SDKs also ship a built-in `LoggingHook` (Java, Kotlin, Ruby, Rust, Dart server); those are documented in the per-SDK files rather than the ecosystem catalogue.

## Integrations

| Integration | Language | Where | What it does |
|---|---|---|---|
| Dropwizard OpenFeature | Java | https://github.com/sideshowcoder/dropwizard-openfeature (Maven `io.github.sideshowcoder:dropwizard-openfeature`) | Dropwizard module: health checks and managed startup/shutdown of the OpenFeature API. Community-maintained, not officially supported |
| FlagLint | JS(S) | https://github.com/flaglint/flaglint | CLI that audits LaunchDarkly Node.js SDK usage and generates OpenFeature migration plans |

## OFREP: OpenFeature Remote Evaluation Protocol

### What and why

OFREP is an HTTP/JSON API specification (OpenAPI 3.1, currently `info.version: 0.3.0`, Apache-2.0) that sits between an OpenFeature provider and a flag management system. It is "a protocol, not a provider": any backend that implements it works with the community-maintained generic OFREP provider for each language, so a new vendor does not need to write N providers and an application can switch backends without changing provider code. Repo: https://github.com/open-feature/protocol (spec at `service/openapi.yaml`, provider guidelines under `guideline/`, design decisions under `service/adrs/`). Docs: https://openfeature.dev/docs/reference/other-technologies/ofrep and the rendered spec at https://openfeature.dev/docs/reference/other-technologies/ofrep/openapi. Spec appendix: https://openfeature.dev/specification/appendix-c. Slack: `#openfeature-remote-evaluation-protocol` (https://cloud-native.slack.com/archives/C066A48LK35).

It maps onto the two SDK paradigms: server-side providers call the single-flag endpoint with a fresh context on every evaluation; client-side providers call the bulk endpoint once with the static context, cache every flag locally, evaluate from the cache, and re-fetch on polling, on context change, or on a push notification.

### Endpoints (tag "OFREP Core", both required)

| Endpoint | Used by | Request | Success response |
|---|---|---|---|
| `POST /ofrep/v1/evaluate/flags/{key}` | server-side (dynamic context) providers | `evaluationRequest`: `{ "context": { "targetingKey": "...", ...any } }`; `targetingKey` is required in the `context` schema | `200` `evaluationSuccess` |
| `POST /ofrep/v1/evaluate/flags` | client-side (static context) providers | `bulkEvaluationRequest`, same body; optional header `If-None-Match: <etag>`; optional query params `flagConfigEtag` and `flagConfigLastModified` (only on re-fetches triggered by an event stream, ADR-0008) | `200` `bulkEvaluationSuccess` with an `ETag` response header, or `304 Not Modified` with no body |

Base URL convention: the provider is configured with the URL before the `/ofrep` segment (for example `http://localhost:8016`), and the guideline says the provider must validate that URL at construction.

### Response schemas

`evaluationSuccess` (single flag, and each element of the bulk `flags` array):

| Field | Type | Notes |
|---|---|---|
| `key` | string | required |
| `reason` | enum `STATIC`, `TARGETING_MATCH`, `SPLIT`, `DISABLED`, `UNKNOWN` | required; OpenFeature resolution reasons |
| `variant` | string | optional |
| `value` | boolean, string, integer, number (float) or object | present for every type except `codeDefaultFlag`, which has no `value` and tells the provider to use the application's code default (ADR-0006) |
| `metadata` | object of string/boolean/number values | optional flag metadata for telemetry |

`evaluationFailure` (a flag that exists but could not be evaluated): `key` (required), `errorCode` (required; enum `PARSE_ERROR`, `TARGETING_KEY_MISSING`, `INVALID_CONTEXT`, `GENERAL`), `errorDetails` (string), `metadata`. `flagNotFound`: same shape with `errorCode: FLAG_NOT_FOUND`.

`bulkEvaluationSuccess`: `flags` (array whose items are `evaluationSuccess` or `evaluationFailure`, so partial failure is normal), optional `metadata` for the whole flag set, optional `eventStreams` (array of `{ type: "sse", url | endpoint: { origin?, requestUri }, inactivityDelaySec: 120 }`; providers connect to known types and re-fetch when notified, ignore unknown types, and treat the URL as sensitive). `bulkEvaluationFailure` (whole request failed): `errorCode` (required), `errorDetails`.

Server-Sent Events are documented separately in `service/event-streams.yaml` (OpenAPI 3.2.0): each SSE `data` payload is JSON with `type` (`refetchEvaluation` is the only defined value), optional `etag` and `lastModified`, which the provider forwards as the `flagConfigEtag` / `flagConfigLastModified` query parameters on its re-fetch.

### HTTP status codes and how providers must react

| Status | Meaning | Provider behaviour per `guideline/*.md` |
|---|---|---|
| `200` | evaluated | Map to evaluation details. Bulk: clear cache, store new details, store `ETag`, emit `PROVIDER_CONFIGURATION_CHANGED` with `flagsChanged` |
| `304` | bulk only, cache still valid | Keep cache |
| `400` | malformed request or invalid context (`evaluationFailure` / `bulkEvaluationFailure` body) | Map `errorCode` to the OpenFeature error and return it |
| `401`, `403` | missing/invalid credentials, or forbidden | Server provider: return an error. Client provider: emit a `fatal` event, stop polling, enter the terminal error state |
| `404` | flag not found (`flagNotFound` body) | Return `FLAG_NOT_FOUND` |
| `429` | rate limited; `Retry-After` header is a date-time or a number of seconds | Do not call again before `Retry-After`; server-side evaluations in the meantime return the default with an error |
| `500` | `generalErrorResponse` (`errorDetails`) | Error |

### Authentication headers

The spec declares two optional security schemes, `BearerAuth` (`Authorization: Bearer <token>`) and `ApiKeyAuth` (`X-API-Key: <key>`); which one a backend accepts is backend-specific. Every OFREP provider must accept arbitrary `headers`, a `baseURL`, and a `timeout` (default 10 s / `10_000` ms); client-side providers add `pollInterval` (0 disables polling). ADR-0007 standardises environment variables for SDK configuration: `OFREP_ENDPOINT`, `OFREP_HEADERS` (comma-separated `key=value`, URL-decode the whole string first, e.g. `OFREP_HEADERS=Authorization=Bearer%20token,X-Custom=value`), `OFREP_TIMEOUT_MS`.

### curl examples

```bash
# Single flag, dynamic context (server-side pattern)
curl -sS -X POST http://localhost:8016/ofrep/v1/evaluate/flags/discount-banner \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer $TOKEN' \
  -d '{"context":{"targetingKey":"user-123","email":"user@example.com","country":"CA"}}'
# -> {"key":"discount-banner","value":true,"reason":"TARGETING_MATCH","variant":"enabled"}

# Bulk, static context (client-side pattern), with ETag revalidation
curl -sS -i -X POST http://localhost:8016/ofrep/v1/evaluate/flags \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: $KEY' \
  -H 'If-None-Match: abc123xyz' \
  -d '{"context":{"targetingKey":"user-456","plan":"free"}}'
# -> 304 Not Modified (unchanged), or 200 with an ETag header and
#    {"flags":[{"key":"discount-banner","value":true,"reason":"TARGETING_MATCH","variant":"enabled"},
#              {"key":"non-existent-flag","errorCode":"FLAG_NOT_FOUND","errorDetails":"..."}],
#     "metadata":{"version":"v12"}}
```

Add `-L` if the backend redirects http to https; `curl -d` silently follows nothing by default.

### Backends that implement OFREP (`src/datasets/ofrep-api`)

| Backend | Docs | Note |
|---|---|---|
| flagd | https://flagd.dev/reference/flagd-ofrep/ | Serves OFREP on its own port |
| GO Feature Flag | https://gofeatureflag.org/docs/sdk/ofrep | |
| Flipt | https://docs.flipt.io/integration/openfeature#remote-evaluation-protocol | |
| ConfigCat | https://configcat.com/docs/sdk-reference/openfeature/overview/#openfeature-remote-evaluation-protocol-ofrep | |
| DevCycle | https://docs.devcycle.com/integrations/openfeature#openfeature-remote-evaluation-api | Bucketing API implementation |
| Flipswitch | https://docs.flipswitch.io/docs/sdks/ofrep | |
| FFlags | https://fflags.com | Built entirely on OFREP |
| Flaghoist | https://docs.flaghoist.dev/api-reference/ | Self-hosted, runs on serverless/edge runtimes |
| Pydantic Logfire | https://pydantic.dev/docs/logfire/manage/client-side-feature-flags/ | Serves managed variables to browser, mobile and edge clients |

### OFREP providers per language (`src/datasets/providers/ofrep.ts`)

| Language | Location | Package / constructor |
|---|---|---|
| JavaScript server | https://github.com/open-feature/js-sdk-contrib/tree/main/libs/providers/ofrep | npm `@openfeature/ofrep-provider` (0.2.5 on 2026-09-21, verified via the npm registry) |
| JavaScript web | https://github.com/open-feature/js-sdk-contrib/tree/main/libs/providers/ofrep-web | npm `@openfeature/ofrep-web-provider` (0.4.3 on 2026-09-21, verified via the npm registry) |
| Go | https://github.com/open-feature/go-sdk-contrib/tree/main/providers/ofrep | `go get github.com/open-feature/go-sdk-contrib/providers/ofrep`; `ofrep.NewProvider("http://localhost:8016", ofrep.WithBearerToken("TOKEN"), ofrep.WithClient(&http.Client{Timeout: time.Second}))`; other options `WithApiKeyAuth`, `WithHeader`, `WithHeaderProvider`, `WithBaseURI`, `WithTimeout` |
| Python | https://github.com/open-feature/python-sdk-contrib/tree/main/providers/openfeature-provider-ofrep | `pip install openfeature-provider-ofrep`; `from openfeature.contrib.provider.ofrep import OFREPProvider`; `api.set_provider(OFREPProvider(base_url="http://localhost:8016", headers_factory=lambda: {"Authorization": f"Bearer {token}"}))` — `base_url` is required (the upstream README's bare `OFREPProvider()` does not run) |
| .NET | https://github.com/open-feature/dotnet-sdk-contrib/tree/main/src/OpenFeature.Providers.Ofrep | `dotnet add package OpenFeature.Providers.Ofrep`; `new OfrepProvider(new OfrepOptions("https://flags.example.com") { Timeout = TimeSpan.FromSeconds(10), Headers = new Dictionary<string,string>{...} })`; `await Api.Instance.SetProviderAsync(provider)` |
| Java | https://github.com/open-feature/java-sdk-contrib/tree/main/providers/ofrep | Maven group `dev.openfeature.contrib.providers`, artifact `ofrep` `(coordinates unverified — check the provider README)` |

No OFREP provider is listed for PHP, Ruby, Rust, Kotlin, Swift or Dart. Writing one means following `guideline/dynamic-context-provider.md` (server) or `guideline/static-context-provider.md` (client) in the protocol repo, then filing an issue on `open-feature/openfeature.dev` to be listed.

## OpenFeature CLI

Docs: https://openfeature.dev/docs/reference/other-technologies/cli; tutorial: https://openfeature.dev/docs/tutorials/open-feature-cli; repo: https://github.com/open-feature/cli; Slack `#openfeature-cli` (https://cloud-native.slack.com/archives/C07DY4TUDK6). The tutorial marks the CLI as experimental (expect breaking changes) and the reference page carries a "WIP" badge.

The CLI's core idea is a **flag manifest** (`flags.json` at the project root, validated by https://raw.githubusercontent.com/open-feature/cli/refs/heads/main/schema/v0/flag-manifest.json) from which it generates strongly typed accessors so application code stops using string keys and untyped defaults.

Install (binary is called `openfeature`):

```bash
curl -fsSL https://openfeature.dev/scripts/install_cli.sh | sh          # Unix-like
docker run -it -v $(pwd):/local -w /local ghcr.io/open-feature/cli:latest
go install github.com/open-feature/cli/cmd/openfeature@latest           # Go >= 1.25 per the reference page (>= 1.23 per the tutorial)
# or download a release from https://github.com/open-feature/cli/releases
```

Manifest example (the quick start and tutorial use `flagType`; the prose "structure" section calls the field `type`, so treat `flagType` as the key that actually appears in working examples):

```json
{
  "$schema": "https://raw.githubusercontent.com/open-feature/cli/refs/heads/main/schema/v0/flag-manifest.json",
  "flags": {
    "newUserOnboarding": { "description": "Shows the new streamlined onboarding flow", "flagType": "boolean", "defaultValue": false },
    "maxLoginAttempts":  { "description": "Maximum number of login attempts before lockout", "flagType": "integer", "defaultValue": 3 },
    "welcomeMessage":    { "description": "Personalized welcome message for users", "flagType": "string", "defaultValue": "Welcome!" }
  }
}
```

Commands:

| Command | What it does |
|---|---|
| `openfeature init` | Creates `flags.json` with the schema reference |
| `openfeature manifest add <key> [--type string] [--default-value ...] [--description ...]`, `manifest list`, `manifest delete <key>` | Edit the manifest without hand-writing JSON |
| `openfeature compare --against other.json [--output tree|flat|json|yaml]` | Diff two manifests |
| `openfeature generate` | Lists generators; `openfeature generate <lang> [--output ./src/flags]` writes typed accessors |
| `openfeature pull --flag-source-url <url> [--auth-token <token>]` | Fetch flags from an HTTP endpoint implementing the Manifest Management API, or a direct JSON/YAML file URL |
| `openfeature push --flag-source-url <url> --auth-token <token> [--dry-run]` | Create/update remote flags from the local manifest |
| `openfeature version` | Print the version |

Generator targets on the reference page: `react` (hooks), `go`, `csharp`, `java`, `python`, `nestjs` (decorators), `nodejs`, `angular` (requires `@openfeature/angular-sdk` >= 1.1.0). The tutorial's `openfeature generate` listing shows all of these except `angular`, each at stability "alpha". The Node.js generator emits an `openfeature.ts` exporting `getGeneratedClient(domain?, context?)` whose methods (`newUserOnboarding()`, `newUserOnboardingDetails()`, ...) call `client.getBooleanValue("newUserOnboarding", false, context, options)` on `@openfeature/server-sdk`. Other languages' output shapes are not shown in the docs `(unverified)`.

Remote sync uses the Manifest Management API (`api/v0/sync.yaml` in the CLI repo): `GET /openfeature/v0/manifest`, `POST /openfeature/v0/manifest/flags`, `PUT /openfeature/v0/manifest/flags/{key}`, `DELETE /openfeature/v0/manifest/flags/{key}`. This is separate from OFREP, which is for evaluation, not flag administration.

Configuration file `.openfeature.yaml` or `.openfeature.json` (defaults < config file < CLI args):

```yaml
manifest: "flags/manifest.json"
generate:
  output: "src/flags"
  react: { output: "src/flags/react" }
  go: { package: "github.com/myorg/myrepo/flags", output: "src/flags/go" }
```

## OpenFeature MCP server

Docs: https://openfeature.dev/docs/reference/other-technologies/mcp; repo: https://github.com/open-feature/mcp; published to the MCP Registry as `dev.openfeature/mcp`; npm package `@openfeature/mcp` (binary `openfeature-mcp`). It is a local stdio server that gives AI coding assistants two tools:

| Tool | Parameters | Purpose |
|---|---|---|
| `install_openfeature_sdk` | `technology` (required; one of `android`, `dotnet`, `go`, `ios`, `java`, `javascript`, `nestjs`, `nodejs`, `php`, `python`, `react`, `ruby`), `providers` (optional string[] of provider identifiers) | Returns SDK installation instructions, optionally with provider-specific setup, sourced from the ecosystem dataset |
| `ofrep_flag_eval` | `base_url`, `flag_key` (omit for bulk), `context` (e.g. `{ targetingKey: "user-123" }`), `etag`, `auth.bearer_token`, `auth.api_key` | Evaluates one flag or all flags against an OFREP backend |

Configure in any MCP client with npx (no install):

```json
{ "mcpServers": { "OpenFeature": { "command": "npx", "args": ["-y", "@openfeature/mcp"] } } }
```

Claude Code: `claude mcp add --transport stdio openfeature npx -y @openfeature/mcp`, then manage with `/mcp`. Cursor: `~/.cursor/mcp_settings.json`; VS Code: `.vscode/mcp.json`; Windsurf: raw MCP config; Codex CLI: `~/.codex/config.toml` with `[mcp_servers.openfeature] command = "npx" args = ["-y", "@openfeature/mcp"]`; Gemini CLI: `~/.gemini/settings.json`; Claude Desktop: `claude_desktop_config.json`. Global install alternative: `npm install -g @openfeature/mcp` and `"command": "openfeature-mcp"`.

OFREP configuration precedence: tool arguments, then environment variables (`OFREP_ENDPOINT` preferred, or `OPENFEATURE_OFREP_BASE_URL` / `OFREP_BASE_URL`; `OFREP_HEADERS`; `OFREP_TIMEOUT_MS`; `OPENFEATURE_OFREP_BEARER_TOKEN` / `OFREP_BEARER_TOKEN`; `OPENFEATURE_OFREP_API_KEY` / `OFREP_API_KEY`), then `~/.openfeature-mcp.json` (`{"OFREP": {"baseUrl", "bearerToken", "apiKey", "headers", "timeoutMs"}}`, path overridable with `OPENFEATURE_MCP_CONFIG_PATH`). Logs go to stderr; stdout is reserved for the protocol. The docs warn that agents are non-deterministic and changes should be reviewed before committing.

## OpenFeature Operator and flagd on Kubernetes

The OpenFeature Operator (https://github.com/open-feature/open-feature-operator) is a Kubernetes operator that injects flagd into workloads. In the simplest mode it watches for the annotations `openfeature.dev/enabled: "true"` and `openfeature.dev/featureflagsource: <name>` on a Deployment, adds a flagd sidecar, and points it at flag definitions stored as `FeatureFlag` custom resources, grouped by a `FeatureFlagSource` CR that says which flag CRs a workload consumes. Editing a `FeatureFlag` CR and `kubectl apply`-ing it changes flag values in the running application without a redeploy. Installation needs cert-manager (webhooks), then either the release manifest (`kubectl apply -f https://github.com/open-feature/open-feature-operator/releases/download/v0.9.0/release.yaml`) or Helm (`helm repo add openfeature https://open-feature.github.io/open-feature-operator/ && helm upgrade --install open-feature-operator openfeature/open-feature-operator`). Quick start: https://openfeature.dev/docs/tutorials/open-feature-operator/quick-start (uses a kind cluster and the `open-feature/playground` demo at `config/k8s/end-to-end.yaml`).

The advanced tutorial (https://openfeature.dev/docs/tutorials/open-feature-operator/advanced-topics) runs flagd as a central standalone deployment instead of a sidecar, which enables in-process evaluation (the application SDK's flagd provider pulls rules and evaluates locally, https://flagd.dev/architecture/#in-process-evaluation) and client-side evaluation for web and mobile apps through an ingress. CRD reference: https://flagd.dev/reference/openfeature-operator/crds/featureflagsource/. flagd itself, its flag definition format, providers and OFREP endpoint are covered by the sibling `flagd` skill in this marketplace; use that for anything about flagd configuration or the flag JSON schema.

## Migrating between vendors

OpenFeature's value proposition is that application code depends only on the SDK API, so a vendor migration is a provider swap plus a flag-data migration. The documented pattern for doing this gradually is the **Multi-Provider**:

1. Register `new MultiProvider([{ provider: newProvider }, { provider: oldProvider }], new FirstMatchStrategy())` (JS shown; Java, .NET, PHP, Kotlin, Swift and Dart have equivalents). `FirstMatchStrategy` asks providers in order and treats `FLAG_NOT_FOUND` as "try the next one", so flags are served from the new vendor as soon as they exist there and fall back to the old vendor otherwise.
2. Use `ComparisonStrategy(fallbackProvider, onMismatch)` during a verification window to evaluate both providers on every call, log discrepancies, and keep serving the trusted provider's value.
3. Use `FirstSuccessfulStrategy` when the goal is high availability across two sources rather than migration (any error moves to the next provider).
4. Remove the old provider once the new one owns every flag. The PHP docs note that sub-provider hooks are not executed by its MultiProvider; register hooks at the API or client level.

For LaunchDarkly Node.js codebases specifically, FlagLint (https://github.com/flaglint/flaglint) audits SDK usage and generates a migration plan to OpenFeature.

The spec's Appendix E (https://openfeature.dev/specification/appendix-e, `appendix-e-migrations.md`) is about a different kind of migration: moving providers and SDKs to spec `v0.9.0`, where providers must emit their own lifecycle events instead of relying on the SDK's synthetic `PROVIDER_READY` / `PROVIDER_ERROR`. Provider authors emit `PROVIDER_READY` after successful `initialize`, `PROVIDER_ERROR` on failure, and for static-context providers `PROVIDER_RECONCILING` when context reconciliation starts and `PROVIDER_CONTEXT_CHANGED` when it ends, signalling this via an SDK-defined opt-in marker. Providers without the marker keep working on a deprecated legacy path where the SDK emits the events after lifecycle methods return (duplicates are possible if both emit). The Swift SDK's `ProviderStatusTracker` is an example of the new model in practice. Relevant if you maintain a provider; irrelevant to application code.

## Commercial support

From `src/datasets/support/commercial-support.ts`. Listing requires at least one provider in the ecosystem and a public statement of OpenFeature support; the extent of support is defined by each company.

| Company | Support page |
|---|---|
| ConfigCat | https://configcat.com/docs/sdk-reference/openfeature/overview |
| DevCycle | https://docs.devcycle.com/integrations/openfeature |
| Featureflip | https://featureflip.io/docs/integrations/openfeature/ |
| Flagsmith | https://www.flagsmith.com/openfeature |
| Flipt | https://docs.flipt.io/integration/openfeature |
| GO Feature Flag | https://gofeatureflag.org/docs/openfeature_sdk/sdk |
| Harness Feature Management & Experimentation | https://developer.harness.io/docs/feature-management-experimentation/sdks-and-infrastructure/openfeature |
| Kameleoon | https://developers.kameleoon.com/feature-management-and-experimentation/open-feature-providers/ |
| LaunchDarkly | https://docs.launchdarkly.com/sdk/openfeature/ |
| Tggl | https://tggl.io/developers/sdks/open-feature |
| VWO | https://developers.vwo.com/v2/docs/openfeature-providers |

## Community

- Governance and project status: OpenFeature is a CNCF **Incubating** project — accepted to the CNCF on 2022-06-17, moved to Incubating on 2023-11-21 (verified on https://www.cncf.io/projects/openfeature/ on 2026-09-21). Governance lives in https://github.com/open-feature/community .
- Slack: `#openfeature` on CNCF Slack, https://cloud-native.slack.com/archives/C0344AANLA1 (join via https://slack.cncf.io/). Topic channels: `#openfeature-cli` (C07DY4TUDK6), `#openfeature-remote-evaluation-protocol` (C066A48LK35).
- Community repo: https://github.com/open-feature/community (governance, working-group configuration such as `config/open-feature/spec-evaluation/workgroup.yaml`, logo assets; the openfeature.dev "Community" section is rendered from it). Community meeting schedule and links are not in the local sources `(unverified)`; the community repo is where they are published.
- YouTube: https://www.youtube.com/@openfeature. Blog: https://openfeature.dev/blog. Twitter/X: https://twitter.com/openfeature. LinkedIn: https://www.linkedin.com/company/openfeature/.
- Contributing a provider or hook to the catalogue: open an issue on https://github.com/open-feature/openfeature.dev using the "document-provider" or "document-hook" issue template (each SDK page links to it), or edit `src/datasets/providers/*.ts` directly.
- Zero-install tutorial: https://killercoda.com/open-feature/scenario/five-minutes-to-feature-flags (Node/Express, repo https://github.com/open-feature/five-minutes-to-feature-flags).

## When this file is silent

- Filterable, always-current catalogue of SDKs, providers, hooks, OFREP APIs and integrations: https://openfeature.dev/ecosystem (filter by type, technology, vendor, server/client).
- The data behind that page, one TypeScript file per provider/hook/backend: https://github.com/open-feature/openfeature.dev/tree/main/src/datasets (`providers/`, `hooks/`, `integrations/`, `ofrep-api/`, `sdks/`, `support/`).
- OFREP protocol, OpenAPI spec, ADRs and provider-writing guidelines: https://github.com/open-feature/protocol; spec appendix https://openfeature.dev/specification/appendix-c; rendered OpenAPI https://openfeature.dev/docs/reference/other-technologies/ofrep/openapi.
- CLI source, command reference (`docs/commands/openfeature_*.md`) and the Manifest Management API (`api/v0/sync.yaml`): https://github.com/open-feature/cli.
- MCP server source and prompts: https://github.com/open-feature/mcp.
- Operator and flagd: https://github.com/open-feature/open-feature-operator, https://flagd.dev, and the sibling `flagd` skill.
- Specification (including Appendix D on observability and Appendix E on migrations): https://openfeature.dev/specification.
