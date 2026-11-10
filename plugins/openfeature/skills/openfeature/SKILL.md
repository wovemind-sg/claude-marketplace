---
name: openfeature
description: Complete reference for OpenFeature (https://openfeature.dev), the CNCF vendor-neutral feature-flag standard — specification, SDKs, providers, hooks, events, evaluation context, OFREP, CLI, MCP server and ecosystem. Use whenever the user mentions OpenFeature, `openfeature-sdk`, `@openfeature/*`, `dev.openfeature`, `OpenFeature` NuGet, `go-sdk`, a *-sdk-contrib repo, an OpenFeature provider or hook, OFREP, `EvaluationContext`, `targetingKey`, `PROVIDER_READY`, `FLAG_NOT_FOUND`, `TYPE_MISMATCH`, or the flagd/GO Feature Flag/Flipt/Unleash/LaunchDarkly/ConfigCat/DevCycle/Split/PostHog... *OpenFeature provider*. Also trigger when the user wants to add feature flags, percentage rollouts, A/B tests, kill switches or vendor-agnostic flagging to an app in any language (especially Go, C#/.NET, Python), wants to swap or migrate flag vendors, write a custom provider or hook, unit-test flag-dependent code with an in-memory provider, or asks "which feature flag library should I use" — OpenFeature is the standard answer. Deep detail for Go, .NET and Python; coverage for Java, Node, web/React/Angular, Kotlin, Swift, PHP, Ruby, Rust, C++, Dart.
---
# OpenFeature — vendor-neutral feature flags

OpenFeature = an open **specification** + per-language **SDKs** that give your code one flag-evaluation API, with pluggable **providers** that talk to whatever flag backend you use (flagd, GO Feature Flag, Flipt, Unleash, LaunchDarkly, ConfigCat, env vars, an in-memory map, ...). CNCF incubating project (accepted 2022-06-17, incubating since 2023-11-21). It is **not** a flag backend: you always pair the SDK with a provider. Snapshot used here: spec repo 2026-09-21 (SDKs implement spec v0.7.0–v0.8.0); go-sdk 1.18.0, dotnet-sdk 2.14.1, python-sdk 0.10.0.

Reference docs bundled in this skill (`references/`) — read the one matching the task, not all:

| Task | Read |
|------|------|
| Spec-level questions: glossary, evaluation details, `Reason`/`ErrorCode` lists, hook stages & order, events, provider lifecycle/states, context merging, tracking, OTel semantic conventions, requirement numbers | `references/concepts.md` |
| Go: `openfeature` package API, providers, hooks, events, memprovider tests, net/http middleware, flagd/OFREP/from-env providers, OTel hooks, gotchas | `references/go.md` |
| C# / .NET: `Api.Instance`, `OpenFeature.Hosting` (`AddOpenFeature` builder, hosted lifecycle, `AddPolicyName` domains), ASP.NET Core wiring, `IFeatureClient`, hooks, events, `InMemoryProvider`, MultiProvider, contrib providers, flagd `FLAGD_*` options | `references/dotnet.md` |
| Python: `openfeature.api`, sync + `_async` evaluation, `EvaluationContext`, hooks, events, `InMemoryProvider`, FastAPI/Flask/Django recipes, `ContextVarsTransactionContextPropagator`, contrib providers, OTel hook | `references/python.md` |
| Java, Node/NestJS, Web/React/Angular, Kotlin, Swift, PHP, Ruby, Rust, C++, Dart: packages, versions, hello-flag snippets, static-context (client) paradigm | `references/other-sdks.md` |
| Which provider/vendor exists for which language, hooks catalogue, OFREP protocol (endpoints, payloads, error codes), OpenFeature CLI (`openfeature generate`), MCP server, Kubernetes Operator, vendor migration, community | `references/ecosystem.md` |
| Symptom → cause → fix; FAQ; debug checklist | `references/troubleshooting.md` |
| Topic not covered here → where to look online, grep recipes | `references/resources.md` |

Sibling skill: **`flagd`** covers the flagd daemon itself (flag file format, JSON Logic targeting, deployment). Use it when the question is about flagd configuration rather than the OpenFeature API.

## Mental model (30 seconds)

```
your code ──▶ Client (per domain, optional) ──▶ Evaluation API (global singleton) ──▶ Provider ──▶ flag backend
                 │  hooks: before → [resolve] → after / error → finally (API, client, invocation, provider levels)
                 │  evaluation context merged: API < transaction < client < invocation < before-hooks (later wins)
                 ◀── events: PROVIDER_READY / PROVIDER_ERROR / PROVIDER_CONFIGURATION_CHANGED / PROVIDER_STALE (+ RECONCILING, CONTEXT_CHANGED on client SDKs)
```

- **Evaluation never throws.** Every getter takes a *default value* and returns it on any error (provider not ready, flag missing, type mismatch...). The `*Details` variant exposes `value, variant, reason, errorCode, errorMessage, flagMetadata` so you can tell *why*.
- **Five flag types**: boolean, string, number (int/float split per language), object/structure. Call the getter matching the flag's type or you get `TYPE_MISMATCH` + default.
- **Reasons**: `STATIC`, `DEFAULT`, `TARGETING_MATCH`, `SPLIT`, `CACHED`, `DISABLED`, `STALE`, `UNKNOWN`, `ERROR`. **Error codes**: `PROVIDER_NOT_READY`, `PROVIDER_FATAL`, `FLAG_NOT_FOUND`, `PARSE_ERROR`, `TYPE_MISMATCH`, `TARGETING_KEY_MISSING`, `INVALID_CONTEXT`, `GENERAL`.
- **Evaluation context** = optional `targetingKey` (who/what is being evaluated — needed for deterministic percentage rollouts) + flat attributes (string/number/bool/datetime/structure). Server SDKs (*dynamic-context paradigm*) accept context per call; client/web/mobile SDKs (*static-context paradigm*) set it once on the API and the provider re-evaluates everything (`PROVIDER_RECONCILING` → `PROVIDER_CONTEXT_CHANGED`).
- **Providers** have a lifecycle: `NOT_READY → READY | ERROR | FATAL`, plus `STALE`. Setting a provider is asynchronous in most SDKs; use the "and wait" form (or await the returned task) before the first evaluation, or handle `PROVIDER_NOT_READY` defaults.
- **Domains** bind a named client to a named provider so one app can use several backends. **Multi-provider** (appendix A) combines providers under one client with `FirstMatch` / `FirstSuccessful` / `Comparison` strategies.
- **Hooks** run code around every evaluation (logging, OTel, validation, context enrichment). **Tracking** (`client.track(...)`) links user actions to flag exposures for experimentation.

## Quick start — Go

```bash
go get github.com/open-feature/go-sdk            # SDK (Go 1.26+ per README; module targets current Go releases)
go get github.com/open-feature/go-sdk-contrib/providers/flagd   # or ofrep, from-env, launchdarkly, ...
```
```go
package main

import (
    "context"
    "fmt"

    "github.com/open-feature/go-sdk/openfeature"
    "github.com/open-feature/go-sdk/openfeature/memprovider"
)

func main() {
    flags := map[string]memprovider.InMemoryFlag{
        "new-checkout": {State: memprovider.Enabled, DefaultVariant: "off",
            Variants: map[string]any{"on": true, "off": false}},
    }
    // blocks until PROVIDER_READY (or returns the init error) — prefer this over SetProvider
    if err := openfeature.SetProviderAndWait(memprovider.NewInMemoryProvider(flags)); err != nil {
        panic(err)
    }
    defer openfeature.Shutdown()

    client := openfeature.NewDefaultClient()            // or openfeature.NewClient("checkout") for a domain
    evalCtx := openfeature.NewEvaluationContext("user-123", map[string]any{"plan": "pro"})

    on := client.Boolean(context.Background(), "new-checkout", false, evalCtx) // value only
    details, err := client.BooleanValueDetails(context.Background(), "new-checkout", false, evalCtx)
    fmt.Println(on, details.Variant, details.Reason, details.ErrorCode, err)
}
```
`client.Boolean/String/Int/Float/Object` return the value; `client.BooleanValue(...) (bool, error)` and `client.BooleanValueDetails(...)` expose errors/details. Ints are `int64`. Full API → `references/go.md`.

## Quick start — C# / .NET (ASP.NET Core with DI)

```bash
dotnet add package OpenFeature                   # core SDK (.NET 8+, .NET Framework 4.6.2+), NativeAOT-compatible
dotnet add package OpenFeature.Hosting           # AddOpenFeature(...) builder + hosted lifecycle (init on start, shutdown on stop)
dotnet add package OpenFeature.Providers.Flagd   # or OpenFeature.Providers.Ofrep, OpenFeature.Contrib.Providers.EnvVar, ...
# OpenFeature.DependencyInjection is DEPRECATED (merged into OpenFeature.Hosting in 2.9.0) — do not add it
```
```csharp
using OpenFeature;                       // IFeatureClient, Api
using OpenFeature.Hooks;                 // LoggingHook, MetricsHook, TraceEnricherHook (built into the core SDK)
using OpenFeature.Model;                 // EvaluationContext, Value, Structure
using OpenFeature.Providers.Memory;      // InMemoryProvider, Flag<T>
using OpenFeature.Hosting.Providers.Memory; // AddInMemoryProvider extension

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddOpenFeature(of => of        // registers an *isolated* Api + HostedFeatureLifecycleService automatically
    .AddHook(sp => new LoggingHook(sp.GetRequiredService<ILogger<LoggingHook>>()))
    .AddInMemoryProvider(flags => flags["new-checkout"] =
        new Flag<bool>(new Dictionary<string, bool> { ["on"] = true, ["off"] = false }, "off"))
    .AddContext((ctx, sp) => ctx.Set("region", "eu-west-1")));      // API-level context

var app = builder.Build();
app.MapGet("/checkout", async (IFeatureClient flags, HttpContext http) =>   // IFeatureClient is Scoped
{
    var ctx = EvaluationContext.Builder()
        .SetTargetingKey(http.User.Identity?.Name ?? "anonymous")
        .Set("plan", "pro").Build();
    var details = await flags.GetBooleanDetailsAsync("new-checkout", false, ctx);
    return Results.Ok(new { details.Value, details.Variant, details.Reason, details.ErrorType });
});
app.Run();
```
`AddHostedFeatureLifecycle()` is `[Obsolete]` (added automatically). Since 2.14 `AddOpenFeature` uses its own isolated `Api`, **not** `Api.Instance` — do not mix `Api.Instance.GetClient()` with the DI client in one app. Without DI: `await Api.Instance.SetProviderAsync(provider); var client = Api.Instance.GetClient(); await client.GetBooleanValueAsync("key", false, ctx);` and `await Api.Instance.ShutdownAsync()` at exit. Provider `InitializeAsync` failures are caught by the SDK and surface as `ProviderStatus.Error`/`Fatal` + a `ProviderError` event (the README's try/catch is belt-and-braces). Full API, MultiProvider, transaction context (`AsyncLocalTransactionContextPropagator`) → `references/dotnet.md`.

## Quick start — Python

```bash
pip install openfeature-sdk                 # Python 3.10+
pip install openfeature-provider-flagd      # or openfeature-provider-ofrep, openfeature-provider-env-var, ...
```
```python
from openfeature import api
from openfeature.evaluation_context import EvaluationContext
from openfeature.provider.in_memory_provider import InMemoryFlag, InMemoryProvider

flags = {"new-checkout": InMemoryFlag("off", {"on": True, "off": False})}
api.set_provider_and_wait(InMemoryProvider(flags))   # set_provider() is non-blocking; this one raises on init failure
client = api.get_client()                            # api.get_client("checkout") for a domain

ctx = EvaluationContext(targeting_key="user-123", attributes={"plan": "pro"})
on = client.get_boolean_value("new-checkout", False, ctx)
details = client.get_boolean_details("new-checkout", False, ctx)
print(on, details.variant, details.reason, details.error_code)

# asyncio: every getter has an *_async twin (falls back to the sync provider path if the provider is sync)
# on = await client.get_boolean_value_async("new-checkout", False, ctx)
api.shutdown()   # at process exit
```
Request-scoped context for Flask/FastAPI: `api.set_transaction_context_propagator(ContextVarsTransactionContextPropagator())` once, then `api.set_transaction_context(EvaluationContext(...))` in middleware. Note the client's context is a plain attribute (`client.context = EvaluationContext(...)`) — there is no `client.set_evaluation_context` method despite what some docs snippets show. Full API → `references/python.md`.

## Working rules

1. **Default values are the safety net.** Pick the default that is correct when the flag system is down (usually the old/off behaviour); never "the value we want in prod".
2. **Evaluate flags where the decision is made, per request**, not once at import/module load or in a constructor: an early evaluation races provider init (returns the default with `PROVIDER_NOT_READY`), never picks up later flag changes, and defeats per-user targeting. Cache only deliberately, and refresh on `PROVIDER_CONFIGURATION_CHANGED`.
3. **Wait for readiness once, at startup**: Go `SetProviderAndWait`, .NET `await SetProviderAsync` (or let `AddOpenFeature`'s hosted lifecycle do it before the app serves), Python `set_provider_and_wait`, JS `await OpenFeature.setProviderAndWait(...)`, Java `setProviderAndWait`. Otherwise early evaluations silently return defaults with `PROVIDER_NOT_READY`.
4. **Always pass a `targetingKey`** when the flag does percentage rollouts or per-user targeting; otherwise bucketing is undefined (`TARGETING_KEY_MISSING` on strict providers). Prefer a stable id (user id / session id / hostname), not an email.
5. **Debug with details, not values.** `reason` + `errorCode` tell you `FLAG_NOT_FOUND` vs `TYPE_MISMATCH` vs `DEFAULT` (rule matched nothing) vs `DISABLED`. Attach the SDK's `LoggingHook` at debug level when in doubt; the SDK itself is silent by design.
6. **Match the getter to the flag type**, including int vs float (Go `Int`/`Float`, .NET `GetIntegerValueAsync`/`GetDoubleValueAsync`, Python `get_integer_value`/`get_float_value`). Object flags come back as `any` / `Value` / `dict|list`.
7. **Request-scoped data goes in transaction context**, not in a new client per request: Go `openfeature.WithTransactionContext(ctx, ec)`, .NET `Api.Instance.SetTransactionContextPropagator(new AsyncLocalTransactionContextPropagator())` + `SetTransactionContext`, Python `ContextVarsTransactionContextPropagator`. Merge order: API < transaction < client < invocation < before-hooks.
8. **Use domains (named clients + named providers) or the multi-provider** when two backends coexist (e.g. migrating LaunchDarkly → flagd). Don't hand-roll fallbacks.
9. **Test with the in-memory provider** (`memprovider.NewInMemoryProvider`, `InMemoryProvider` + `Flag<T>`, `InMemoryProvider` + `InMemoryFlag`) — no network, deterministic, supports variants + context evaluators. Reset the API between tests (`api.clear_providers()` in Python; re-set a provider in others).
10. **Shut down on exit** (`openfeature.Shutdown()`, `Api.Instance.ShutdownAsync()`, `api.shutdown()`) so providers flush events/tracking and close streams.
11. **Keep PII out of context** unless the provider is trusted to hold it; a `before` hook can strip/anonymize attributes.
12. **Hooks must be cheap and must not throw** in `after`/`finally`; an error in `before` aborts the evaluation and returns the default (spec 4.5.x). Put telemetry in `after`/`finally`, context enrichment in `before`.
13. **Client-side (web/mobile) is different**: set context on the API (`OpenFeature.setContext`), evaluation getters are synchronous against a cached bulk evaluation, react to `PROVIDER_CONFIGURATION_CHANGED`/`PROVIDER_CONTEXT_CHANGED` to re-render. See `references/other-sdks.md`.
14. **Vendor choice is orthogonal**: pick the provider by backend (`references/ecosystem.md`), keep application code on the OpenFeature API. For a self-hosted open-source backend recommend flagd (see the `flagd` skill) or GO Feature Flag; for "just a REST API" use the generic OFREP provider.
14. When the docs bundled here are silent or ambiguous, follow `references/resources.md`: read the live page on https://openfeature.dev/, the spec at https://openfeature.dev/specification/, or grep the SDK source (`git clone --depth 1 https://github.com/open-feature/<lang>-sdk`). Say which source you used and note the version you checked, because SDK APIs are still moving (Python is pre-1.0).
