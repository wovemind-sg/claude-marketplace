# openfeature

Complete reference skill for [OpenFeature](https://openfeature.dev/), the CNCF vendor-neutral feature-flag specification and SDKs.

## Purpose

Gives Claude everything it needs to add, debug and evolve OpenFeature-based feature flags without browsing:

- the specification digest: evaluation API, providers and their lifecycle, evaluation context and merge order, hooks (stages, ordering, error semantics), events, tracking, `Reason` / `ErrorCode` tables, multi-provider strategies, OpenTelemetry conventions, requirement numbers
- deep-dive references for the **Go**, **.NET / C#** and **Python** SDKs: exact signatures, provider registration and readiness, all evaluation getters, context and transaction context, writing hooks and custom providers, in-memory providers for tests, contrib providers (flagd, OFREP, env-var, ...) with their options and env vars, framework recipes (net/http, ASP.NET Core with `OpenFeature.Hosting`, FastAPI/Flask/Django), verified gotchas
- coverage of the other SDKs (Java, Node/NestJS, web/React/Angular, Kotlin, Swift, PHP, Ruby, Rust, C++, Dart) with package names, versions and hello-flag snippets
- the ecosystem: which provider exists for which vendor and language, hooks catalogue, the OFREP protocol (endpoints, payloads, errors), the `openfeature` CLI, the OpenFeature MCP server, the Kubernetes Operator, vendor migration patterns, community channels
- a symptom → cause → fix troubleshooting table, and a curated map of online resources plus grep recipes for anything the skill does not cover

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install openfeature@wovemind
```

## Requirements

None for the skill itself. To run what it writes you need the OpenFeature SDK for your language and a provider for your flag backend, for example flagd (covered by the sibling `flagd` plugin), OFREP or a vendor provider.

## Usage

The skill triggers automatically when OpenFeature, its SDKs, providers, hooks, OFREP, evaluation context or vendor-agnostic feature flagging come up, in any language. Invoke explicitly with `/openfeature:openfeature`.

Example prompts:

- "Add OpenFeature to this Go service with the flagd provider and gate `/checkout` on `new-checkout` for 10% of users"
- "Wire OpenFeature into my ASP.NET Core app with DI, an OFREP provider and a logging hook, and unit-test the controller with the in-memory provider"
- "My Python FastAPI app returns the default for every flag with reason ERROR — why?"
- "Write an OpenFeature hook that adds the request's tenant id to the evaluation context and emits an OTel span attribute"
- "How do I migrate from LaunchDarkly to flagd without touching call sites?"

## Example

Ask Claude:

> "My Python FastAPI app returns the default for every flag with reason ERROR. Why?"

Claude checks the usual causes in order, using the troubleshooting table: the provider was registered but not ready when the first evaluation ran, the flag key does not exist in the provider (`FLAG_NOT_FOUND`), the variant type does not match the getter you called (`TYPE_MISMATCH`), or a percentage rollout received no `targetingKey`. For each one it shows how to confirm it from the evaluation details (`reason`, `error_code`, `error_message`) and the code change that fixes it, such as registering the provider with `api.set_provider_and_wait(...)` so it is ready before the app serves requests.

## Layout

```
skills/openfeature/
├── SKILL.md                  overview, mental model, Go / C# / Python quick starts, working rules
└── references/
    ├── concepts.md           spec digest: glossary, evaluation API, providers, context, hooks, events, tracking, appendices
    ├── go.md                 Go SDK deep dive (go-sdk 1.18.0 + go-sdk-contrib)
    ├── dotnet.md             .NET SDK deep dive (OpenFeature 2.14.1, OpenFeature.Hosting, MultiProvider, contrib)
    ├── python.md             Python SDK deep dive (openfeature-sdk 0.10.0 + python-sdk-contrib)
    ├── other-sdks.md         Java, Node, web/React/Angular, Kotlin, Swift, PHP, Ruby, Rust, C++, Dart
    ├── ecosystem.md          providers/hooks catalogue, OFREP, CLI, MCP server, Operator, migration, community
    ├── troubleshooting.md    symptom → cause → fix, debug checklist, FAQ
    └── resources.md          online sources and grep recipes to consult when the skill is silent
```

Sibling plugin: `flagd` covers the flagd daemon itself (flag file format, targeting, deployment).

## Environment variables

None required by the skill. Providers read their own variables (for example `FLAGD_HOST`, `FLAGD_PORT`, `FLAGD_RESOLVER` for the flagd provider); these are documented in the language reference files.

## Source

References distilled from local clones taken 2026-09-21: `open-feature/spec` (24f98d7), `open-feature/openfeature.dev` docs (9e19e66), `go-sdk` 1.18.0, `dotnet-sdk` 2.14.1, `python-sdk` 0.10.0, the three `*-sdk-contrib` repos and `open-feature/protocol`. Re-run the distillation when an SDK ships a new minor version.
