# OpenFeature .NET / C# SDK reference

Pinned to `OpenFeature` **2.14.1** (dotnet-sdk commit `385ef26`, 2026-09-05), dotnet-sdk-contrib `main` as of **2026-09-21**. Every identifier below was checked against that source; when the SDK moves on, re-grep before trusting a signature (see the last section).

| NuGet package | Version | What it is |
|---|---|---|
| `OpenFeature` | 2.14.1 | Core SDK: `Api`, `FeatureClient`, `FeatureProvider`, `Hook`, `InMemoryProvider`, built-in `LoggingHook`/`MetricsHook`/`TraceEnricherHook`, `OpenFeature.Isolated` |
| `OpenFeature.Hosting` | 2.14.1 | `services.AddOpenFeature(...)`, `IFeatureClient` injection, hosted lifecycle service, `AddInMemoryProvider` |
| `OpenFeature.DependencyInjection` | 2.14.1 | **Deprecated** since 2.9.0. Package now contains only a README; all DI code lives in `OpenFeature.Hosting` |
| `OpenFeature.Providers.MultiProvider` | 2.14.1 | Composite provider with FirstMatch / FirstSuccessful / Comparison strategies |
| `OpenFeature.Providers.Flagd` | 0.7.3 | flagd provider (RPC, in-process, file resolvers) |
| `OpenFeature.Providers.Ofrep` | 0.1.5 | OpenFeature Remote Evaluation Protocol client provider |
| `OpenFeature.Providers.ConfigCat` | 1.0.0 | ConfigCat |
| `OpenFeature.Providers.GOFeatureFlag` | 1.2.0 | GO Feature Flag (in-process WASM or remote) |
| `OpenFeature.Providers.Unleash` | 0.1.1 | Unleash |
| `OpenFeature.Contrib.Providers.EnvVar` | 0.0.7 | Environment-variable provider |
| `OpenFeature.Contrib.Providers.FeatureManagement` | 0.1.2 | Bridge to `Microsoft.FeatureManagement` |
| `OpenFeature.Contrib.Providers.Flagsmith` | 0.3.1 | Flagsmith |
| `OpenFeature.Contrib.Providers.Flipt` | 0.0.5 | Flipt |
| `OpenFeature.Contrib.Providers.Statsig` | 0.1.1 | Statsig |
| `OpenFeature.Contrib.Hooks.Otel` | — | **Deprecated**; OTel hooks moved into `OpenFeature` core in 2.7.0 |

Naming split: newer contrib packages are `OpenFeature.Providers.*` (namespace matches), older ones are `OpenFeature.Contrib.Providers.*`. The package id and the root namespace agree in every case above, so `using` the package name works. One exception: the flagd DI extensions live in namespace `OpenFeature.DependencyInjection.Providers.Flagd` even though the package is `OpenFeature.Providers.Flagd`.

```sh
dotnet add package OpenFeature
dotnet add package OpenFeature.Hosting                 # ASP.NET Core / Generic Host
dotnet add package OpenFeature.Providers.MultiProvider  # optional
dotnet add package OpenFeature.Providers.Flagd          # or any provider above
```

Target frameworks for all first-party packages: `net462; netstandard2.0; net8.0; net9.0; net10.0`. README states support as ".NET 8+ and .NET Framework 4.6.2+". Core SDK is NativeAOT-compatible (`IsAotCompatible` for net8+); contrib providers may not be. Spec version implemented: v0.8.0.

## Contents

1. [Console quick start and domains](#1-console-quick-start-and-domains)
2. [ASP.NET Core / Generic Host wiring](#2-aspnet-core--generic-host-wiring)
3. [Evaluation API](#3-evaluation-api)
4. [Evaluation context](#4-evaluation-context)
5. [Hooks](#5-hooks)
6. [Events](#6-events)
7. [Provider lifecycle and custom providers](#7-provider-lifecycle-and-custom-providers)
8. [Multi-provider](#8-multi-provider)
9. [Tracking](#9-tracking)
10. [Logging and telemetry](#10-logging-and-telemetry)
11. [Contrib providers](#11-contrib-providers)
12. [Recipes](#12-recipes)
13. [Gotchas](#13-gotchas)
14. [When this file is silent](#14-when-this-file-is-silent)

## 1. Console quick start and domains

`Api.Instance` is the process-wide singleton (`public static Api Instance`). Setting a provider is async and awaits `InitializeAsync`; the returned task completes when the provider is READY (or has failed, see gotchas).

```csharp
using OpenFeature;
using OpenFeature.Model;
using OpenFeature.Providers.Memory;

var flags = new Dictionary<string, Flag>
{
    { "bool-flag", new Flag<bool>(new Dictionary<string, bool> { { "on", true }, { "off", false } }, defaultVariant: "on") },
    { "string-flag", new Flag<string>(new Dictionary<string, string> { { "greeting", "Hello" } }, defaultVariant: "greeting") },
};

await Api.Instance.SetProviderAsync(new InMemoryProvider(flags));

IFeatureClient client = Api.Instance.GetClient();          // FeatureClient, default (unnamed) domain
bool enabled = await client.GetBooleanValueAsync("bool-flag", false);
string greeting = await client.GetStringValueAsync("string-flag", "default");

await Api.Instance.ShutdownAsync();                         // shuts down every provider, clears hooks/context
```

Real signatures on `Api`:

```csharp
Task SetProviderAsync(FeatureProvider featureProvider);
Task SetProviderAsync(FeatureProvider featureProvider, CancellationToken cancellationToken);
Task SetProviderAsync(string domain, FeatureProvider featureProvider);
Task SetProviderAsync(string domain, FeatureProvider featureProvider, CancellationToken cancellationToken);
FeatureProvider GetProvider();                 // default
FeatureProvider GetProvider(string domain);    // falls back to default if domain unbound
Metadata? GetProviderMetadata();
FeatureClient GetClient(string? name = null, string? version = null, ILogger? logger = null, EvaluationContext? context = null);
Task ShutdownAsync();
```

**Domains** (spec section 1.1.3): a client created with `GetClient("billing")` resolves against the provider bound with `SetProviderAsync("billing", provider)`; if none is bound, it silently uses the default provider. Passing a null/empty domain to `SetProviderAsync(string, ...)` throws `ArgumentNullException`.

```csharp
await Api.Instance.SetProviderAsync(new InMemoryProvider(defaultFlags));
await Api.Instance.SetProviderAsync("billing", new InMemoryProvider(billingFlags));

var billing = Api.Instance.GetClient("billing");   // backed by billingFlags
var other   = Api.Instance.GetClient("search");    // no provider for "search" -> default provider
```

Replacing a provider: the old one is shut down (`ShutdownAsync`) once no domain references it, and its API binding is cleared. A single provider instance may not be registered with two different `Api` instances at once (`InvalidOperationException`, spec 1.8.4).

## 2. ASP.NET Core / Generic Host wiring

This is the section most C# code should follow. Install `OpenFeature.Hosting`; everything is in namespace `OpenFeature` (`AddOpenFeature`, builder extensions) plus `OpenFeature.Hosting` (`OpenFeatureBuilder`, `OpenFeatureOptions`, `PolicyNameOptions`) and `OpenFeature.Hosting.Providers.Memory` (`AddInMemoryProvider`).

### What `AddOpenFeature` registers

From `OpenFeatureServiceCollectionExtensions.AddOpenFeature(this IServiceCollection, Action<OpenFeatureBuilder>)`:

1. A **singleton `Api`** created with `OpenFeatureFactory.CreateIsolated()` — *not* `Api.Instance`. Inject `Api` if you need the API object; do not mix with `Api.Instance` in the same app (changed in 2.14.0, #760).
2. `IFeatureLifecycleManager` singleton.
3. **`HostedFeatureLifecycleService`** as an `IHostedLifecycleService`, automatically. `AddHostedFeatureLifecycle()` still exists but is `[Obsolete]` — calling it just adds the same hosted service again.
4. `IFeatureClient` as a **scoped** service (keyed by domain when you register domain providers).
5. If more than one provider is registered and no policy is configured, a default `PolicyNameOptions.DefaultNameSelector` returning the first registered provider name.

At host start (`StartingAsync` by default) the lifecycle manager resolves each registered `FeatureProvider` (default one from the container, domain ones as keyed services), calls `api.SetProviderAsync(...)` for each (so initialization is awaited before the app serves traffic), adds every registered hook via `api.AddHooks(...)`, and wires `AddHandler` event handlers. At `StoppedAsync` it calls `api.ShutdownAsync()`.

### Minimal API example

```csharp
using Microsoft.AspNetCore.Mvc;
using OpenFeature;
using OpenFeature.Hooks;
using OpenFeature.Hosting.Providers.Memory;
using OpenFeature.Providers.Memory;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddOpenFeature(featureBuilder =>
{
    featureBuilder
        .AddHook(sp => new LoggingHook(sp.GetRequiredService<ILogger<LoggingHook>>()))
        .AddHook<TraceEnricherHook>()
        .AddContext((ctx, sp) => ctx.Set("environment", builder.Environment.EnvironmentName))
        .AddHandler(ProviderEventTypes.ProviderReady, details => Console.WriteLine($"ready: {details?.ProviderName}"))
        .AddInMemoryProvider(_ => new Dictionary<string, Flag>
        {
            { "welcome-message", new Flag<bool>(new Dictionary<string, bool> { { "show", true }, { "hide", false } }, "show") }
        });
});

var app = builder.Build();

app.MapGet("/hello", async ([FromServices] IFeatureClient client) =>
    await client.GetBooleanValueAsync("welcome-message", false) ? "Hello, welcome!" : "Hello!");

app.Run();
```

Controllers get the same `IFeatureClient` by constructor injection. It is scoped, so one client per request; the client's context is whatever `AddContext` built for that scope.

### Builder methods (all on `OpenFeatureBuilder`, verified in `OpenFeatureBuilderExtensions.cs`)

| Method | Effect |
|---|---|
| `AddProvider(Func<IServiceProvider, FeatureProvider>)` | Default provider (transient factory, resolved once at startup) |
| `AddProvider<TOptions>(Func<IServiceProvider, FeatureProvider>, Action<TOptions>?)` | Same, with an `OpenFeatureOptions`-derived options class |
| `AddProvider(string domain, Func<IServiceProvider, string, FeatureProvider>)` | Domain-bound provider; also registers keyed `IFeatureClient` for that domain |
| `AddInMemoryProvider(Func<IServiceProvider, IDictionary<string, Flag>?>)` / `(string domain, ...)` / `(Action<IDictionary<string, Flag>>?)` | `InMemoryProvider` convenience (namespace `OpenFeature.Hosting.Providers.Memory`; marked `[Experimental("OFDI001")]` on net8+) |
| `AddHook<THook>(Func<IServiceProvider, THook>? factory = null)` | Keyed singleton hook, key = `typeof(THook).Name`; no factory means DI constructs it |
| `AddHook<THook>(THook hook)` / `AddHook<THook>(string hookName, THook hook)` / `AddHook<THook>(string hookName, Func<IServiceProvider, THook>?)` | Instance or named variants (use a name to register two hooks of the same type) |
| `AddContext(Action<EvaluationContextBuilder>)` / `AddContext(Action<EvaluationContextBuilder, IServiceProvider>)` | Registers a **transient** `EvaluationContext`; applied with `client.SetContext` when the scoped client is created — so it is *client* context, rebuilt per scope |
| `AddHandler(ProviderEventTypes, EventHandlerDelegate)` / `AddHandler(ProviderEventTypes, Func<IServiceProvider, EventHandlerDelegate>)` | API-level event handler added at startup |
| `AddPolicyName(Action<PolicyNameOptions>)` | `options.DefaultNameSelector = sp => "domain"` chooses which domain the un-keyed `IFeatureClient` resolves to |
| `AddHostedFeatureLifecycle(Action<FeatureLifecycleStateOptions>?)` | Obsolete; see below for the supported way to set lifecycle options |

### Domain-scoped providers and `AddPolicyName`

```csharp
builder.Services.AddOpenFeature(fb =>
{
    fb.AddInMemoryProvider("default")
      .AddInMemoryProvider("beta")
      .AddPolicyName(p => p.DefaultNameSelector = sp => "default");
});

// un-keyed client -> the policy's domain
app.MapGet("/", async (IFeatureClient client) => await client.GetBooleanValueAsync("f", false));
// explicit domain
app.MapGet("/beta", async ([FromKeyedServices("beta")] IFeatureClient client) => await client.GetBooleanValueAsync("f", false));
```

`OpenFeatureBuilder.Validate()` throws `InvalidOperationException` at `AddOpenFeature` time if several providers are registered without a policy ("Multiple providers have been registered, but no policy has been configured."), or if a default provider plus one domain provider exist without a policy. A single default provider needs no policy.

### Lifecycle options

`FeatureLifecycleStateOptions` (namespace `OpenFeature`) has `StartState` (`FeatureStartState.Starting | Start | Started`, default `Starting`) and `StopState` (`FeatureStopState.Stopping | Stop | Stopped`, default `Stopped`). There are no timeout properties; the host's own start/stop timeouts apply. Configure through options:

```csharp
builder.Services.Configure<FeatureLifecycleStateOptions>(o =>
{
    o.StartState = FeatureStartState.Start;
    o.StopState = FeatureStopState.Stop;
});
```

On hosts that only implement `IHostedService` (legacy `WebHost`), 2.14.1 falls back to `StartAsync`/`StopAsync` automatically and logs event id 201 "The host does not support IHostedLifecycleService callbacks".

### Custom provider through DI

```csharp
builder.Services.AddOpenFeature(fb =>
    fb.AddProvider(sp => new MyProvider(sp.GetRequiredService<IOptions<MySettings>>().Value)));

// domain-scoped, factory receives the domain string
builder.Services.AddOpenFeature(fb =>
    fb.AddProvider("tenant-a", (sp, domain) => new MyProvider(domain)));
```

## 3. Evaluation API

All methods live on `IFeatureClient` (implemented by `sealed FeatureClient`). Each type has a value method and a details method; the value method is `(await GetXDetailsAsync(...)).Value`.

```csharp
Task<bool>   GetBooleanValueAsync(string flagKey, bool defaultValue,   EvaluationContext? context = null, FlagEvaluationOptions? config = null, CancellationToken cancellationToken = default);
Task<string> GetStringValueAsync (string flagKey, string defaultValue, EvaluationContext? context = null, FlagEvaluationOptions? config = null, CancellationToken cancellationToken = default);
Task<int>    GetIntegerValueAsync(string flagKey, int defaultValue,    EvaluationContext? context = null, FlagEvaluationOptions? config = null, CancellationToken cancellationToken = default);
Task<double> GetDoubleValueAsync (string flagKey, double defaultValue, EvaluationContext? context = null, FlagEvaluationOptions? config = null, CancellationToken cancellationToken = default);
Task<Value>  GetObjectValueAsync (string flagKey, Value defaultValue,  EvaluationContext? context = null, FlagEvaluationOptions? config = null, CancellationToken cancellationToken = default);
Task<FlagEvaluationDetails<bool>>   GetBooleanDetailsAsync(...same parameters...);
Task<FlagEvaluationDetails<string>> GetStringDetailsAsync(...);
Task<FlagEvaluationDetails<int>>    GetIntegerDetailsAsync(...);
Task<FlagEvaluationDetails<double>> GetDoubleDetailsAsync(...);
Task<FlagEvaluationDetails<Value>>  GetObjectDetailsAsync(...);
ProviderStatus ProviderStatus { get; }
```

The `CancellationToken` is passed to before/after/error/finally hooks and to the provider's `Resolve*Async`.

### `FlagEvaluationDetails<T>` (namespace `OpenFeature.Model`)

| Property | Type | Notes |
|---|---|---|
| `Value` | `T` | Resolved value, or the default on error |
| `FlagKey` | `string` | |
| `Reason` | `string?` | Compare with constants in `OpenFeature.Constant.Reason` (it is a static class, not an enum) |
| `Variant` | `string?` | |
| `ErrorType` | `ErrorType` | `None` when successful |
| `ErrorMessage` | `string?` | |
| `FlagMetadata` | `ImmutableMetadata?` | `GetBool/GetInt/GetDouble/GetString(key)`, `IsEmpty`, `Count` |

`Reason` constants: `TargetingMatch` ("TARGETING_MATCH"), `Split`, `Disabled`, `Default`, `Static`, `Cached`, `Unknown`, `Error`.

`ErrorType` enum: `None`, `ProviderNotReady`, `FlagNotFound`, `ParseError`, `TypeMismatch`, `General`, `InvalidContext`, `TargetingKeyMissing`, `ProviderFatal`.

```csharp
var details = await client.GetStringDetailsAsync("theme", "light", ctx);
if (details.ErrorType != ErrorType.None)
    logger.LogWarning("flag {Key} fell back: {Error} {Msg}", details.FlagKey, details.ErrorType, details.ErrorMessage);
else if (details.Reason == Reason.TargetingMatch)
    logger.LogDebug("variant {Variant}", details.Variant);
```

### `FlagEvaluationOptions`

```csharp
new FlagEvaluationOptions(IImmutableList<Hook> hooks, IImmutableDictionary<string, object>? hookHints = null);
new FlagEvaluationOptions(Hook hook, ImmutableDictionary<string, object>? hookHints = null);
// properties: IImmutableList<Hook> Hooks; IImmutableDictionary<string, object> HookHints
```

Hook hints are passed as the `hints` argument to every hook stage of that evaluation.

### `Value` and `Structure` for object flags

`Value` (namespace `OpenFeature.Model`) is a tagged union. Constructors: `Value()` (null), `Value(bool)`, `Value(int)` (stored as double), `Value(double)`, `Value(string)`, `Value(Structure)`, `Value(IList<Value>)`, `Value(DateTime)`, `Value(Value)`, and `Value(object)` which accepts only those inner types and throws `ArgumentException` otherwise. Inspect with `IsNull/IsBoolean/IsNumber/IsString/IsStructure/IsList/IsDateTime` and read with `AsBoolean`, `AsInteger`, `AsDouble`, `AsString`, `AsStructure`, `AsList`, `AsDateTime`, `AsObject` (all nullable). `Value` implements `IEquatable<Value>` and `==`. `ValueJsonConverter` is public for System.Text.Json source generators.

```csharp
var defaultCfg = new Value(Structure.Builder().Set("Threshold", 50).Set("Enabled", true).Build());
Value cfg = await client.GetObjectValueAsync("test-config", defaultCfg);
int threshold = cfg.AsStructure?.GetValue("Threshold").AsInteger ?? 50;
```

`Structure`: `Structure.Builder().Set(key, string|int|double|long|bool|Structure|DateTime|IList<Value>|Value).Build()`, `new Structure(IDictionary<string, Value>)`, `Structure.Empty`, `GetValue`, `TryGetValue`, `ContainsKey`, indexer, `Keys`, `Values`, `Count`, `AsDictionary()`.

## 4. Evaluation context

```csharp
EvaluationContext ctx = EvaluationContext.Builder()
    .SetTargetingKey("user-123")
    .Set("email", "a@b.c")           // string
    .Set("age", 42)                  // int (or long, double)
    .Set("beta", true)               // bool
    .Set("signup", DateTime.UtcNow)  // DateTime
    .Set("org", Structure.Builder().Set("plan", "pro").Build())
    .Set("raw", new Value(3.5))
    .Merge(otherContext)             // copies every key from another context (later Set wins)
    .Build();

ctx.TargetingKey;                    // string?  (stored under key "targetingKey")
ctx.GetValue("email").AsString;
ctx.TryGetValue("age", out Value? age);
ctx.ContainsKey("beta"); ctx.Count; ctx.AsDictionary();
EvaluationContext.Empty;
```

Levels and merge order **as implemented in `FeatureClient.EvaluateFlagAsync`**:

```
API (Api.Instance.SetContext)  ->  client (client.SetContext / GetClient(context:))  ->  transaction  ->  invocation argument  ->  before-hook results
lowest precedence                                                                                                          highest precedence
```

Duplicate keys are overwritten by the later level. Note the SDK merges **client before transaction**, whereas spec Requirement 3.2.3 says API → transaction → client → invocation. In practice: a key set in transaction context beats the same key in client context in .NET.

```csharp
Api.Instance.SetContext(EvaluationContext.Builder().Set("region", "eu").Build());   // global
client.SetContext(EvaluationContext.Builder().Set("service", "checkout").Build());  // per client
await client.GetBooleanValueAsync("f", false, EvaluationContext.Builder().SetTargetingKey(userId).Build()); // invocation
```

### Transaction context (request-scoped)

Default propagator is `NoOpTransactionContextPropagator` (stores nothing). Register the `AsyncLocal<T>`-backed one once at startup, then set per request:

```csharp
Api.Instance.SetTransactionContextPropagator(new AsyncLocalTransactionContextPropagator());   // once

// in middleware / auth handler
Api.Instance.SetTransactionContext(EvaluationContext.Builder().SetTargetingKey(userId).Set("ip", ip).Build());
EvaluationContext current = Api.Instance.GetTransactionContext();
```

Custom propagators implement `OpenFeature.Model.ITransactionContextPropagator` (`EvaluationContext GetTransactionContext(); void SetTransactionContext(EvaluationContext)`). `SetTransactionContextPropagator(null)` and `SetTransactionContext(null)` throw `ArgumentNullException`. `ShutdownAsync` resets the propagator to no-op. When using DI, call these on the injected `Api`, not `Api.Instance`.

## 5. Hooks

`OpenFeature.Hook` is an abstract class with four virtual generic methods (override only what you need). Signatures copied from `Hook.cs`:

```csharp
public virtual ValueTask<EvaluationContext> BeforeAsync<T>(HookContext<T> context, IReadOnlyDictionary<string, object>? hints = null, CancellationToken cancellationToken = default);
public virtual ValueTask AfterAsync<T>(HookContext<T> context, FlagEvaluationDetails<T> details, IReadOnlyDictionary<string, object>? hints = null, CancellationToken cancellationToken = default);
public virtual ValueTask ErrorAsync<T>(HookContext<T> context, Exception error, IReadOnlyDictionary<string, object>? hints = null, CancellationToken cancellationToken = default);
public virtual ValueTask FinallyAsync<T>(HookContext<T> context, FlagEvaluationDetails<T> evaluationDetails, IReadOnlyDictionary<string, object>? hints = null, CancellationToken cancellationToken = default);
```

`HookContext<T>` (namespace `OpenFeature.Model`): `FlagKey`, `DefaultValue` (`T`), `FlagValueType` (`Boolean|String|Number|Object`), `EvaluationContext`, `ClientMetadata` (`Name`, `Version`), `ProviderMetadata` (`Name`), and `Data` (`HookData`). `HookData` is a per-hook, per-evaluation bag shared across that hook's stages: `Set(key, object)`, `Get(key)` (throws `KeyNotFoundException`), indexer, `Count`, `Keys`, `Values`, `AsDictionary()`. It is not thread-safe and should not be retained after the evaluation.

Registration levels and order (spec 4.4.2; documented in `FeatureProvider.GetProviderHooks`):

```csharp
Api.Instance.AddHooks(new MyHook());                          // API level; AddHooks(IEnumerable<Hook>) also exists
client.AddHooks(new MyHook());                                // client level
await client.GetBooleanValueAsync("k", false, ctx, new FlagEvaluationOptions(new MyHook()));   // invocation level
public override IImmutableList<Hook> GetProviderHooks() => ImmutableList.Create<Hook>(new MyHook()); // provider level
```

Before hooks run API → Client → Invocation → Provider; after, error and finally run in reverse (Provider → Invocation → Client → API). `Api.Instance.GetHooks()` / `ClearHooks()` and `client.GetHooks()` / `ClearHooks()` exist.

Behaviour rules verified in `FeatureClient.EvaluateFlagAsync` and `HookRunner`:

- The `EvaluationContext` returned by each before hook is merged into the context for the following hooks and the provider. Returning `EvaluationContext.Empty` (the base implementation) changes nothing.
- If a before hook throws, or the provider throws, or the provider returns `ErrorType != None`, **error hooks run and after hooks do not**. After hooks run only on `ErrorType.None`.
- Finally hooks always run; an exception in an error or finally hook is logged (event ids 103/104) and does not stop the remaining hooks (spec 4.4.3).
- Exceptions from before/after hooks propagate into the evaluation `catch` and turn into `ErrorType.General` (or `TypeMismatch` for `InvalidCastException`) with `Reason.Error`; the caller still gets the default value, never an exception.

### Complete example: timing hook using `HookData`

```csharp
using System.Diagnostics;
using OpenFeature;
using OpenFeature.Model;

public sealed class TimingHook : Hook
{
    private readonly ILogger<TimingHook> _logger;
    public TimingHook(ILogger<TimingHook> logger) => _logger = logger;

    public override ValueTask<EvaluationContext> BeforeAsync<T>(HookContext<T> context,
        IReadOnlyDictionary<string, object>? hints = null, CancellationToken cancellationToken = default)
    {
        context.Data.Set("sw", Stopwatch.StartNew());
        return new ValueTask<EvaluationContext>(EvaluationContext.Empty);   // no context changes
    }

    public override ValueTask FinallyAsync<T>(HookContext<T> context, FlagEvaluationDetails<T> evaluationDetails,
        IReadOnlyDictionary<string, object>? hints = null, CancellationToken cancellationToken = default)
    {
        var sw = (Stopwatch)context.Data.Get("sw");
        _logger.LogDebug("flag {Key} -> {Value} ({Reason}) in {Ms}ms via {Provider}",
            context.FlagKey, evaluationDetails.Value, evaluationDetails.Reason, sw.ElapsedMilliseconds, context.ProviderMetadata.Name);
        return default;
    }
}
```

### Built-in hooks (namespace `OpenFeature.Hooks`)

| Hook | Constructor | Purpose |
|---|---|---|
| `LoggingHook` | `LoggingHook(ILogger logger, bool includeContext = false)` | Debug-level structured log of before/after/error stages |
| `MetricsHook` | `MetricsHook(MetricsHookOptions? options = null)` | `System.Diagnostics.Metrics` counters on meter `"OpenFeature"`: `feature_flag.evaluation_requests_total`, `feature_flag.evaluation_success_total`, `feature_flag.evaluation_error_total`, `feature_flag.evaluation_active_count`; options via `MetricsHookOptions.CreateBuilder().WithCustomDimension(k, v).WithFlagEvaluationMetadata(k, meta => meta.GetBool("x")).Build()` |
| `TraceEnricherHook` | `TraceEnricherHook(TraceEnricherHookOptions? options = null)` | Adds flag tags/events to the *current* `Activity` in `FinallyAsync` (no-op without an active span); options via `TraceEnricherHookOptions.CreateBuilder().WithTag(k, v).WithFlagEvaluationMetadata(...).Build()` |

## 6. Events

Types (namespaces `OpenFeature.Constant` and `OpenFeature.Model`):

```csharp
public enum ProviderEventTypes { ProviderReady, ProviderError, ProviderConfigurationChanged, ProviderStale }
public delegate void EventHandlerDelegate(ProviderEventPayload? eventDetails);
public class ProviderEventPayload
{
    public string? ProviderName; public ProviderEventTypes Type; public string? Message;
    public ErrorType? ErrorType; public List<string>? FlagsChanged; public ImmutableMetadata? EventMetadata;
}
```

```csharp
Api.Instance.AddHandler(ProviderEventTypes.ProviderReady, p => Console.WriteLine($"{p?.ProviderName} ready"));
Api.Instance.AddHandler(ProviderEventTypes.ProviderConfigurationChanged,
    p => Console.WriteLine($"changed: {string.Join(",", p?.FlagsChanged ?? new List<string>())}"));
Api.Instance.RemoveHandler(ProviderEventTypes.ProviderReady, handler);

var client = Api.Instance.GetClient("billing");
client.AddHandler(ProviderEventTypes.ProviderError, p => { /* only events from the provider bound to "billing" (or default) */ });
```

Both `Api` and `IFeatureClient` implement `IEventBus` (`AddHandler`, `RemoveHandler`). Handlers run on the SDK's event-processing loop under a lock; keep them fast. If a handler is added for `ProviderReady` after the provider is already READY, `EventExecutor` invokes it immediately with a synthetic payload (spec 5.3.3).

How a provider emits: `FeatureProvider` owns `protected readonly Channel<object> EventChannel = Channel.CreateBounded<object>(1)`. Write a `ProviderEventPayload` to it; the SDK reads it, updates `provider.Status` (Ready / Stale / Error / Fatal based on `ErrorType == ProviderFatal`) and fans out to API, client and default-provider handlers.

```csharp
await this.EventChannel.Writer.WriteAsync(new ProviderEventPayload
{
    Type = ProviderEventTypes.ProviderConfigurationChanged,
    ProviderName = GetMetadata()?.Name,
    FlagsChanged = changedKeys,
    Message = "flags changed",
}, cancellationToken);
```

`InMemoryProvider.UpdateFlagsAsync(IDictionary<string, Flag>?)` does exactly this and is a handy way to exercise change handlers in tests. READY and ERROR on initialization are emitted by the SDK itself; a provider must not emit READY from `InitializeAsync`.

## 7. Provider lifecycle and custom providers

`OpenFeature.FeatureProvider` abstract class:

```csharp
public abstract Metadata? GetMetadata();
public abstract Task<ResolutionDetails<bool>>   ResolveBooleanValueAsync  (string flagKey, bool defaultValue,   EvaluationContext? context = null, CancellationToken cancellationToken = default);
public abstract Task<ResolutionDetails<string>> ResolveStringValueAsync   (string flagKey, string defaultValue, EvaluationContext? context = null, CancellationToken cancellationToken = default);
public abstract Task<ResolutionDetails<int>>    ResolveIntegerValueAsync  (string flagKey, int defaultValue,    EvaluationContext? context = null, CancellationToken cancellationToken = default);
public abstract Task<ResolutionDetails<double>> ResolveDoubleValueAsync   (string flagKey, double defaultValue, EvaluationContext? context = null, CancellationToken cancellationToken = default);
public abstract Task<ResolutionDetails<Value>>  ResolveStructureValueAsync(string flagKey, Value defaultValue,  EvaluationContext? context = null, CancellationToken cancellationToken = default);
public virtual Task InitializeAsync(EvaluationContext context, CancellationToken cancellationToken = default);  // default: completed
public virtual Task ShutdownAsync(CancellationToken cancellationToken = default);                              // default: completed
public virtual IImmutableList<Hook> GetProviderHooks();                                                        // default: empty
public virtual void Track(string trackingEventName, EvaluationContext? evaluationContext = default, TrackingEventDetails? trackingEventDetails = default);
public Channel<object> GetEventChannel();
```

`ProviderStatus` (`OpenFeature.Constant`): `NotReady`, `Ready`, `Stale`, `Error`, `Fatal`. The status is `internal set` — the SDK manages it: `Ready` after `InitializeAsync` succeeds, `Error` (or `Fatal` when the exception is `ProviderFatalException`) when it throws, and thereafter driven by emitted events. Read it via `client.ProviderStatus`.

Evaluation short-circuits with `ProviderNotReadyException` when status is `NotReady` and `ProviderFatalException` when `Fatal`; status `Error` and `Stale` still call the provider.

`ResolutionDetails<T>` constructor: `(string flagKey, T value, ErrorType errorType = ErrorType.None, string? reason = null, string? variant = null, string? errorMessage = null, ImmutableMetadata? flagMetadata = null)`.

Signalling errors from a provider: either return `ResolutionDetails` with a non-`None` `ErrorType`, or throw one of `OpenFeature.Error.*`: `FlagNotFoundException`, `TypeMismatchException`, `ParseErrorException`, `InvalidContextException`, `TargetingKeyMissingException`, `ProviderNotReadyException`, `ProviderFatalException`, `GeneralException`, or the base `FeatureProviderException(ErrorType, string? message = null, Exception? inner = null)`. The client maps these to `ErrorType` and returns the default value; any other exception becomes `ErrorType.General`.

### Minimal custom provider (compiles against 2.14.1)

```csharp
using System.Collections.Concurrent;
using OpenFeature;
using OpenFeature.Constant;
using OpenFeature.Error;
using OpenFeature.Model;

public sealed class DictionaryProvider : FeatureProvider
{
    private readonly ConcurrentDictionary<string, object> _flags;
    private static readonly Metadata Meta = new("dictionary");

    public DictionaryProvider(IDictionary<string, object> flags) => _flags = new(flags);

    public override Metadata GetMetadata() => Meta;

    public override Task InitializeAsync(EvaluationContext context, CancellationToken cancellationToken = default)
        => Task.CompletedTask; // connect / warm caches here; throw ProviderFatalException for unrecoverable failures

    public override Task<ResolutionDetails<bool>> ResolveBooleanValueAsync(string flagKey, bool defaultValue, EvaluationContext? context = null, CancellationToken cancellationToken = default)
        => Task.FromResult(Resolve(flagKey, defaultValue));
    public override Task<ResolutionDetails<string>> ResolveStringValueAsync(string flagKey, string defaultValue, EvaluationContext? context = null, CancellationToken cancellationToken = default)
        => Task.FromResult(Resolve(flagKey, defaultValue));
    public override Task<ResolutionDetails<int>> ResolveIntegerValueAsync(string flagKey, int defaultValue, EvaluationContext? context = null, CancellationToken cancellationToken = default)
        => Task.FromResult(Resolve(flagKey, defaultValue));
    public override Task<ResolutionDetails<double>> ResolveDoubleValueAsync(string flagKey, double defaultValue, EvaluationContext? context = null, CancellationToken cancellationToken = default)
        => Task.FromResult(Resolve(flagKey, defaultValue));
    public override Task<ResolutionDetails<Value>> ResolveStructureValueAsync(string flagKey, Value defaultValue, EvaluationContext? context = null, CancellationToken cancellationToken = default)
        => Task.FromResult(Resolve(flagKey, defaultValue));

    private ResolutionDetails<T> Resolve<T>(string flagKey, T defaultValue)
    {
        if (!_flags.TryGetValue(flagKey, out var raw))
            throw new FlagNotFoundException($"flag '{flagKey}' not found");
        if (raw is not T typed)
            throw new TypeMismatchException($"flag '{flagKey}' is {raw.GetType().Name}, requested {typeof(T).Name}");
        return new ResolutionDetails<T>(flagKey, typed, ErrorType.None, Reason.Static);
    }
}
```

### `NoOpProvider` and `InMemoryProvider`

Before any `SetProviderAsync`, the default provider is the internal `NoOpProvider` (metadata name "No-op Provider"): it returns the default value with reason `"No-op"` and variant `"No-op"`, status READY. Handy for tests where flags do not matter.

`InMemoryProvider` (namespace `OpenFeature.Providers.Memory`, metadata name "InMemory"):

```csharp
public InMemoryProvider(IDictionary<string, Flag>? flags = null);
public Task UpdateFlagsAsync(IDictionary<string, Flag>? flags = null);   // replaces all flags, emits ProviderConfigurationChanged

public sealed class Flag<T> : Flag
{
    public Flag(Dictionary<string, T> variants, string defaultVariant,
                Func<EvaluationContext, string>? contextEvaluator = null,
                ImmutableMetadata? flagMetadata = null, bool disabled = false);
}
```

Evaluation rules: `disabled: true` returns the *caller's default* with `Reason.Disabled`; no `contextEvaluator` returns the default variant with `Reason.Static`; a `contextEvaluator` returning a known variant gives `Reason.TargetingMatch`; if it throws or names an unknown variant the default variant is returned with `Reason.Default`; a default variant that does not exist throws `GeneralException`. Wrong requested type surfaces as `ErrorType.TypeMismatch`; unknown key as `ErrorType.FlagNotFound`.

```csharp
var flags = new Dictionary<string, Flag>
{
    { "checkout-v2", new Flag<bool>(
        new Dictionary<string, bool> { { "on", true }, { "off", false } }, "off",
        ctx => ctx.TryGetValue("plan", out var plan) && plan?.AsString == "pro" ? "on" : "off") },
    { "limits", new Flag<Value>(
        new Dictionary<string, Value> { { "std", new Value(Structure.Builder().Set("max", 10).Build()) } }, "std",
        flagMetadata: new ImmutableMetadata(new Dictionary<string, object> { { "version", "3" } })) },
};
```

## 8. Multi-provider

Package `OpenFeature.Providers.MultiProvider`; namespaces `OpenFeature.Providers.MultiProvider` (`MultiProvider`), `.Models` (`ProviderEntry`), `.Strategies` (`BaseEvaluationStrategy`, `FirstMatchStrategy`, `FirstSuccessfulStrategy`, `ComparisonStrategy`), `.DependencyInjection` (`AddMultiProvider`, `MultiProviderBuilder`). Experimental per README.

```csharp
public MultiProvider(IEnumerable<ProviderEntry> providerEntries, BaseEvaluationStrategy? evaluationStrategy = null, ILogger? logger = null);
public ProviderEntry(FeatureProvider provider, string? name = null);
public ComparisonStrategy(FeatureProvider? fallbackProvider = null, Action<IDictionary<string, object>>? onMismatch = null);
```

| Strategy | `RunMode` | Result |
|---|---|---|
| `FirstMatchStrategy` (default when `null`) | Sequential | First result that is not `FlagNotFound`; any other error is returned immediately |
| `FirstSuccessfulStrategy` | Sequential | First result with no error; errors ignored unless every provider fails |
| `ComparisonStrategy` | Parallel | Evaluates all; returns the agreed value, otherwise the fallback provider's (or first provider's) value and calls `onMismatch` |

```csharp
var multi = new MultiProvider(new[]
{
    new ProviderEntry(new FlagdProvider(), "flagd"),
    new ProviderEntry(new InMemoryProvider(fallbackFlags), "fallback"),
}, new FirstSuccessfulStrategy());
await Api.Instance.SetProviderAsync(multi);
```

DI (from the AspNetCore sample):

```csharp
using OpenFeature.Providers.MultiProvider.DependencyInjection;
using OpenFeature.Providers.MultiProvider.Strategies;

builder.Services.AddOpenFeature(fb => fb.AddMultiProvider("multi", mp => mp
    .AddProvider("p1", sp => new InMemoryProvider(flags1))
    .AddProvider("p2", new InMemoryProvider(flags2))          // instance overload
    .AddProvider<MyProvider>("p3")                            // resolved from DI
    .UseStrategy<FirstMatchStrategy>()));                     // or UseStrategy(instance) / UseStrategy(sp => ...)
```

`AddMultiProvider(Action<MultiProviderBuilder>)` registers it as the default provider; the `(string domain, ...)` overload binds a domain. `MultiProvider` initializes and shuts down all children, forwards `Track`, aggregates child status (emits `ProviderStale`/`ProviderError` only when the aggregate changes), always re-emits `ProviderConfigurationChanged`, and implements `IAsyncDisposable`. Custom strategies subclass `BaseEvaluationStrategy` (`RunMode`, `ShouldEvaluateThisProvider`, `ShouldEvaluateNextProvider`, `DetermineFinalResult`, `ShouldTrackWithThisProvider`).

## 9. Tracking

```csharp
void Track(string trackingEventName, EvaluationContext? evaluationContext = default, TrackingEventDetails? trackingEventDetails = default);

client.Track("purchase-completed",
    EvaluationContext.Builder().SetTargetingKey(userId).Build(),
    TrackingEventDetails.Builder().SetValue(99.77).Set("currency", "USD").Set("items", 3).Build());
```

`Track` throws `ArgumentException` for a null/empty name, merges API + client + supplied context (no transaction context, no hooks), and calls `provider.Track(...)`. The base `FeatureProvider.Track` is a no-op, so nothing happens unless the provider overrides it. `TrackingEventDetails` has a `double? Value` field, `Empty`, and the same `GetValue/TryGetValue/ContainsKey/AsDictionary` shape as `EvaluationContext`; the builder mirrors `EvaluationContextBuilder` plus `SetValue(double?)` and `Merge(TrackingEventDetails)`.

## 10. Logging and telemetry

- `Api.Instance.SetLogger(ILogger logger)` sets the logger for the event executor and provider repository (init/shutdown errors, handler exceptions). `GetClient(logger: ...)` gives a client its own logger; otherwise `NullLogger`. Per spec, the SDK does not log during successful evaluations; failed evaluations log at Error (event ids 101/102). Use `LoggingHook` for per-evaluation logs.
- **Native spans (since 2.14.0):** every evaluation is wrapped in an `Activity` named `feature_flag.evaluation` from `ActivitySource` `"OpenFeature"`, tagged with `feature_flag.key`, `feature_flag.provider.name`, `feature_flag.result.reason`, `feature_flag.result.value`, `feature_flag.result.variant`, and on error `error.type` / `feature_flag.error.message`. Enable with `tracing.AddSource("OpenFeature")` — no hook required. `TraceEnricherHook` is for tagging *your* surrounding span instead.
- **Metrics:** `MetricsHook` uses a `Meter` whose name is the SDK assembly name (`"OpenFeature"`); register `metrics.AddMeter("OpenFeature")`.
- **`OpenFeature.Telemetry`:** `EvaluationEventBuilder<T>.Build(HookContext<T> hookContext, FlagEvaluationDetails<T> details)` (static) returns an `EvaluationEvent` (`Name`, `IReadOnlyDictionary<string, object?> Attributes`) shaped per the OTel feature-flag semantic conventions; `TelemetryConstants` holds the attribute keys (`feature_flag.key`, `feature_flag.result.variant`, `feature_flag.context.id`, `feature_flag.set.id`, `feature_flag.version`, `error.type`, …) and `TelemetryFlagMetadata` the flag-metadata keys it reads (`contextId`, `flagSetId`, `version`). Use it inside a custom hook to emit log records or span events.
- The contrib `OpenFeature.Contrib.Hooks.Otel` package is deprecated; its README points to the core hooks above.

```csharp
builder.Services.AddOpenTelemetry()
    .WithTracing(t => t.AddAspNetCoreInstrumentation().AddSource("OpenFeature").AddOtlpExporter())
    .WithMetrics(m => m.AddAspNetCoreInstrumentation().AddMeter("OpenFeature").AddOtlpExporter());
```

## 11. Contrib providers

| Package (version) | Namespace / class | Construction | Notes |
|---|---|---|---|
| `OpenFeature.Providers.Flagd` (0.7.3) | `OpenFeature.Providers.Flagd.FlagdProvider` | `new FlagdProvider()` (env vars), `new FlagdProvider(Uri)` (`http://host:8013` or `unix://path`), `new FlagdProvider(FlagdConfig)` | See below |
| `OpenFeature.Providers.Ofrep` (0.1.5) | `OpenFeature.Providers.Ofrep.OfrepProvider` | `new OfrepProvider(new OfrepOptions("https://flags.example.com") { Timeout = TimeSpan.FromSeconds(10), Headers = { ["Authorization"] = "Bearer …" } })`; also `OfrepOptions.FromEnvironment()` / `FromConfiguration(IConfiguration)` | Env vars `OFREP_ENDPOINT`, `OFREP_HEADERS` (`K=V,K2=V2`), `OFREP_TIMEOUT_MS` (default 10000). DI: `fb.AddOfrepProvider(o => { o.BaseUrl = …; o.HttpClientName = …; })` from `OpenFeature.Providers.Ofrep.DependencyInjection`. Object flags unsupported in this version (only bool/string/int/double resolvers are overridden) |
| `OpenFeature.Contrib.Providers.EnvVar` (0.0.7) | `OpenFeature.Contrib.Providers.EnvVar.EnvVarProvider` | `new EnvVarProvider()` or `new EnvVarProvider("FF_")` | Looks up `{prefix}{flagKey}` verbatim (case as given); missing var → `FlagNotFound`; unparsable → `TypeMismatch`; object flags return the raw string as `Value` |
| `OpenFeature.Contrib.Providers.FeatureManagement` (0.1.2) | `OpenFeature.Contrib.Providers.FeatureManagement.FeatureManagementProvider` | `new FeatureManagementProvider(IConfiguration)` or `(IConfiguration, FeatureManagementOptions)` | Bridges `Microsoft.FeatureManagement`: flags come from the `FeatureManagement` configuration section (appsettings.json, Azure App Configuration, …) with `Variants` / `Allocation` / `EnabledFor` filters. Useful when an existing ASP.NET app already manages flags with `IFeatureManager` and you want OpenFeature-shaped code paths without changing the flag source |
| `OpenFeature.Providers.ConfigCat` (1.0.0) | `OpenFeature.Providers.ConfigCat.ConfigCatProvider` | `new ConfigCatProvider("#SDK-KEY#", options => { options.PollingMode = PollingModes.LazyLoad(...); })` | Implements `InitializeAsync`/`ShutdownAsync`; call `Api.Instance.ShutdownAsync()` on exit |
| `OpenFeature.Providers.GOFeatureFlag` (1.2.0) | `OpenFeature.Providers.GOFeatureFlag.GOFeatureFlagProvider` | `new GOFeatureFlagProvider(new GOFeatureFlagProviderOptions { Endpoint = "http://localhost:1031", EvaluationType = EvaluationType.InProcess, ApiKey = … })` | `Endpoint` is `required`; in-process (WASM) or remote evaluation; data-collection flush options |
| `OpenFeature.Providers.Unleash` (0.1.1) | `OpenFeature.Providers.Unleash.UnleashProvider` | `new UnleashProvider(UnleashSettings settings)` | Wraps the Unleash client |
| `OpenFeature.Contrib.Providers.Flagsmith` (0.3.1) | `OpenFeature.Contrib.Providers.Flagsmith.FlagsmithProvider` | `new FlagsmithProvider(new FlagsmithProviderConfiguration(), flagsmithConfiguration)` (+ `HttpClient` or `IFlagsmithClient` overloads) | |
| `OpenFeature.Contrib.Providers.Flipt` (0.0.5) | `OpenFeature.Contrib.Providers.Flipt.FliptProvider` | `new FliptProvider(fliptUrl, namespaceKey = "default", clientToken = "", timeoutInSeconds = 30)` | |
| `OpenFeature.Contrib.Providers.Statsig` (0.1.1) | `OpenFeature.Contrib.Providers.Statsig.StatsigProvider` | `new StatsigProvider(sdkKey, statsigServerOptions)` | |

Several contrib READMEs still show the removed synchronous `Api.Instance.SetProvider(...)`; use `await SetProviderAsync(...)`.

### flagd provider in more detail

For running the daemon, flag file format and the flagd CLI, see the **`flagd` skill**; this covers only the .NET client side.

`ResolverType` enum: `RPC` (default; gRPC to flagd on 8013), `IN_PROCESS` (syncs flag definitions from flagd's sync service on 8015 and evaluates locally), `FILE` (reads a local flag JSON, polls for changes — good for ConfigMaps and air-gapped setups). `FlagdConfig.Builder()` or `new FlagdConfigBuilder()` exposes `WithHost`, `WithPort`, `WithTls`, `WithCertificatePath`, `WithSocketPath`, `WithCache(bool)`, `WithMaxCacheSize`, `WithMaxEventStreamRetries`, `WithResolverType`, `WithSourceSelector`, `WithOfflineFlagSourcePath`, `WithUseHashFileChangeDetection`, `WithOfflinePollIntervalMs`, `WithDeadlineMs`, `WithRetryBackoffMs`, `WithRetryBackoffMaxMs`, `WithLogger`, `Build()`.

```csharp
using OpenFeature.Providers.Flagd;

var rpc = new FlagdProvider(new Uri("http://localhost:8013"));

var inProcess = new FlagdProvider(FlagdConfig.Builder()
    .WithHost("flagd").WithPort(8015).WithResolverType(ResolverType.IN_PROCESS).WithSourceSelector("my-source").Build());

var file = new FlagdProvider(FlagdConfig.Builder()
    .WithResolverType(ResolverType.FILE).WithOfflineFlagSourcePath("/etc/flags/flags.json").Build());
```

Environment variables read by the empty constructor / `FlagdConfig.Builder()`: `FLAGD_HOST` (localhost), `FLAGD_PORT` (8013; 8015 for in-process), `FLAGD_SYNC_PORT` (priority for in-process), `FLAGD_TLS`, `FLAGD_SERVER_CERT_PATH`, `FLAGD_SOCKET_PATH` (takes precedence over host/port/tls), `FLAGD_CACHE` (`lru`), `FLAGD_MAX_CACHE_SIZE` (10), `FLAGD_MAX_EVENT_STREAM_RETRIES` (3), `FLAGD_RESOLVER` (`rpc`|`in-process`|`file`), `FLAGD_SOURCE_SELECTOR`, `FLAGD_OFFLINE_FLAG_SOURCE_PATH`, `FLAGD_HASH_FILE_CHANGE`, `FLAGD_OFFLINE_POLL_MS` (5000), `FLAGD_DEADLINE_MS` (300000), `FLAGD_RETRY_BACKOFF_MS` (1000), `FLAGD_RETRY_BACKOFF_MAX_MS` (12000). On .NET Framework 4.6.2–4.8 gRPC requires TLS plus a certificate path.

DI: `using OpenFeature.DependencyInjection.Providers.Flagd;` then `fb.AddFlagdProvider()`, `fb.AddFlagdProvider(o => { o.Host = …; o.Port = 8013; o.ResolverType = ResolverType.IN_PROCESS; })`, or the `(string domain, …)` overloads. `FlagdProviderOptions` is a record with the same properties as the builder (`Host`, `Port`, `UseTls`, `CacheEnabled`, `MaxCacheSize`, `CertificatePath`, `SocketPath`, `MaxEventStreamRetries`, `ResolverType`, `SourceSelector`, `OfflineFlagSourcePath`, `UseHashFileChangeDetection`, `OfflinePollIntervalMs`, `DeadlineMs`). The provider adds a `SyncMetadataHook` as a provider hook in in-process mode and emits `ProviderConfigurationChanged` with `FlagsChanged` from the stream.

## 12. Recipes

### Middleware: build context from `HttpContext.User`, set transaction context

Register the propagator once, on the *same* `Api` the clients use (the injected one when using `AddOpenFeature`):

```csharp
// Program.cs
var app = builder.Build();
app.Services.GetRequiredService<Api>().SetTransactionContextPropagator(new AsyncLocalTransactionContextPropagator());
app.UseMiddleware<FlagContextMiddleware>();

public sealed class FlagContextMiddleware
{
    private readonly RequestDelegate _next;
    private readonly Api _api;
    public FlagContextMiddleware(RequestDelegate next, Api api) { _next = next; _api = api; }

    public Task InvokeAsync(HttpContext http)
    {
        var b = EvaluationContext.Builder()
            .Set("ip", http.Connection.RemoteIpAddress?.ToString() ?? "")
            .Set("path", http.Request.Path.Value ?? "/");
        var user = http.User;
        if (user.Identity?.IsAuthenticated == true)
        {
            var id = user.FindFirst(ClaimTypes.NameIdentifier)?.Value ?? user.Identity.Name;
            if (id is not null) b.SetTargetingKey(id);
            var email = user.FindFirst(ClaimTypes.Email)?.Value;
            if (email is not null) b.Set("email", email);
            b.Set("roles", new Value(user.FindAll(ClaimTypes.Role).Select(c => new Value(c.Value)).ToList()));
        }
        _api.SetTransactionContext(b.Build());   // AsyncLocal: flows through the rest of this request
        return _next(http);
    }
}
```

Alternative without transaction context: `AddContext((ctx, sp) => { var http = sp.GetRequiredService<IHttpContextAccessor>().HttpContext; … })` plus `services.AddHttpContextAccessor()`. That context is built when the scoped `IFeatureClient` is first resolved in the request.

### Feature-gated endpoint in a minimal API

```csharp
app.MapPost("/checkout", async (IFeatureClient flags, CheckoutRequest req, CancellationToken ct) =>
{
    var details = await flags.GetBooleanDetailsAsync("checkout-v2", false, cancellationToken: ct);
    if (details.ErrorType != ErrorType.None)
        app.Logger.LogWarning("checkout-v2 fell back to default: {Error}", details.ErrorType);
    return details.Value ? Results.Ok(await CheckoutV2(req)) : Results.Ok(await CheckoutV1(req));
});
```

For an endpoint filter that returns 404 when a flag is off:

```csharp
public sealed class RequireFlagFilter(string flagKey) : IEndpointFilter
{
    public async ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext ctx, EndpointFilterDelegate next)
    {
        var client = ctx.HttpContext.RequestServices.GetRequiredService<IFeatureClient>();
        return await client.GetBooleanValueAsync(flagKey, false, cancellationToken: ctx.HttpContext.RequestAborted)
            ? await next(ctx) : Results.NotFound();
    }
}
app.MapGet("/beta", () => "beta").AddEndpointFilter(new RequireFlagFilter("beta-page"));
```

### Unit-testing a service with `InMemoryProvider`

Prefer an isolated API so tests do not share `Api.Instance` state (xUnit runs classes in parallel):

```csharp
using OpenFeature.Isolated;
using OpenFeature.Providers.Memory;

public class PricingServiceTests
{
    private static async Task<IFeatureClient> ClientWith(bool discounts)
    {
#pragma warning disable OFISO001   // isolated API is [Experimental] on net8+
        var api = OpenFeatureFactory.CreateIsolated();
#pragma warning restore OFISO001
        await api.SetProviderAsync(new InMemoryProvider(new Dictionary<string, Flag>
        {
            { "discounts", new Flag<bool>(new() { { "on", true }, { "off", false } }, discounts ? "on" : "off") },
        }));
        return api.GetClient();
    }

    [Fact]
    public async Task Applies_discount_when_flag_on()
    {
        var sut = new PricingService(await ClientWith(discounts: true));
        Assert.Equal(90m, await sut.PriceAsync(100m));
    }
}
```

`PricingService` should depend on `IFeatureClient` (constructor injection), exactly as production code gets it from `AddOpenFeature`. If you must use the singleton, call `await Api.Instance.ShutdownAsync()` in test teardown; there is no public reset.

### Graceful startup/shutdown

With `AddOpenFeature` nothing extra is needed: providers initialize during host `Starting` (before Kestrel accepts traffic) and `Api.ShutdownAsync()` runs at `Stopped`. To make startup fail fast when a provider cannot initialize, add a `ProviderError` handler that logs/throws, or check `client.ProviderStatus` in a health check:

```csharp
builder.Services.AddHealthChecks().AddCheck("feature-flags", () =>
{
    using var scope = app.Services.CreateScope();
    var status = scope.ServiceProvider.GetRequiredService<IFeatureClient>().ProviderStatus;
    return status is ProviderStatus.Ready or ProviderStatus.Stale
        ? HealthCheckResult.Healthy(status.ToString()) : HealthCheckResult.Unhealthy(status.ToString());
});
```

Without the hosting package: `await Api.Instance.SetProviderAsync(...)` before serving, and `IHostApplicationLifetime.ApplicationStopping.Register(() => Api.Instance.ShutdownAsync().GetAwaiter().GetResult())` or an `IHostedService` whose `StopAsync` awaits `ShutdownAsync`.

## 13. Gotchas

- **`SetProviderAsync` does not throw on init failure.** `ProviderRepository.SetProviderAsync` catches the exception from `InitializeAsync`, sets status to `Error` (or `Fatal` for `ProviderFatalException`) and emits `ProviderError`. Your `await` completes normally; check `client.ProviderStatus` or subscribe to `ProviderError`. (The XML doc still says "May throw".)
- **Evaluating before READY returns defaults**, with `ErrorType.ProviderNotReady` and `Reason.Error`. Always `await SetProviderAsync` (or let `OpenFeature.Hosting` do it) before evaluating. A `Fatal` provider likewise short-circuits with `ProviderFatal`; `Error`/`Stale` still call the provider.
- **Evaluation never throws** for provider/hook problems — errors surface in `FlagEvaluationDetails<T>.ErrorType`. It *can* throw `ArgumentNullException`-style errors from your own code in hooks before the SDK's catch, and `Track` throws on an empty event name.
- **DI uses an isolated `Api`, not `Api.Instance`** (since 2.14.0). `Api.Instance.SetTransactionContextPropagator(...)`, `Api.Instance.AddHooks(...)` or `Api.Instance.GetClient()` in an app wired with `AddOpenFeature` talk to a different API with only the no-op provider. Inject `Api` or `IFeatureClient` instead.
- **A provider instance can be bound to one `Api` only**; registering it with a second (e.g. both `Api.Instance` and the DI instance) throws `InvalidOperationException`. `ShutdownAsync` unbinds it.
- **Merge order deviates from the spec**: client context is merged *before* transaction context, so transaction values override client values (spec 3.2.3 says the opposite).
- **`GetIntegerValueAsync` is `int`, not `long`.** `Value(int)` and `Value(long)`-via-`Set(string, long)` store numbers as `double`; `Value.AsInteger` does `Convert.ToInt32` on that double. There is no `decimal` anywhere in the API — money-style values must be `double` or strings.
- **Object flags need a `Value`, not a POCO.** Wrap with `new Value(Structure.Builder()...Build())`; `new Value(someDto)` throws `ArgumentException("Invalid value type")`. To get a typed object, serialize the `Value` with System.Text.Json (`ValueJsonConverter`) and deserialize into your type, as the AspNetCore sample does.
- **Requesting the wrong type from `InMemoryProvider`** (e.g. `GetStringValueAsync` on a `Flag<bool>`) yields `ErrorType.TypeMismatch` and the default, not an exception.
- **`Flag<T>(disabled: true)`** returns the *caller's* default value (not the default variant) with `Reason.Disabled`.
- **Experimental diagnostics on net8+:** `OpenFeatureFactory.CreateIsolated()` is `[Experimental("OFISO001")]` and the `AddInMemoryProvider` extension class is `[Experimental("OFDI001")]`. If the compiler reports them, suppress with `#pragma warning disable OFISO001` (as the console sample does) or `<NoWarn>$(NoWarn);OFISO001;OFDI001</NoWarn>`.
- **`AddHostedFeatureLifecycle()` is obsolete** — `AddOpenFeature` already registers the hosted service. Many contrib READMEs still show it; drop it. `OpenFeature.DependencyInjection` is a dead package: reference `OpenFeature.Hosting`.
- **`AddContext` context is per DI scope, not global.** It is attached with `client.SetContext` on the scoped `IFeatureClient`. For truly global context call `api.SetContext(...)` on the injected `Api` at startup.
- **Hooks registered through DI are singletons** keyed by `typeof(THook).Name`; registering the same hook type twice without distinct names keeps only the first (`TryAddKeyedSingleton`).
- **Thread safety:** `Api`/`FeatureClient` are safe for concurrent use (locks and `ConcurrentStack` for hooks; `GetContext()` returns an immutable snapshot). `EvaluationContext`, `Structure`, `Value` are immutable. `HookData` is not thread-safe and is per evaluation. `InMemoryProvider.UpdateFlagsAsync` swaps the whole dictionary; do not mutate the dictionary you passed in.
- **Event handlers run serially under a lock** in the SDK's background loop; a slow or throwing handler delays the others (exceptions are logged, not propagated).
- **Domain fallback is silent**: `GetClient("typo")` with no provider bound to `"typo"` uses the default provider without any warning.
- **`Api.Instance.ShutdownAsync()` resets everything** — hooks, global context, transaction propagator, handlers and providers — and leaves the API reusable. After it, you are back on the no-op provider.

## 14. When this file is silent

- Official SDK page: https://openfeature.dev/docs/reference/sdks/server/dotnet (mirrors the repo README). Getting-started tutorial: https://openfeature.dev/docs/tutorials/getting-started/dotnet
- Source: https://github.com/open-feature/dotnet-sdk — `README.md` (features, hooks, DI, multi-provider), `src/OpenFeature.Hosting/README.md`, `src/OpenFeature.Providers.MultiProvider/README.md`, `docs/AOT_COMPATIBILITY.md`, `samples/AspNetCore/Program.cs`, `samples/Console/app.cs`, `CHANGELOG.md`
- Contrib providers and hooks: https://github.com/open-feature/dotnet-sdk-contrib/tree/main/src (one README per package; versions in `.release-please-manifest.json`)
- NuGet: https://www.nuget.org/packages/OpenFeature (and `/packages/OpenFeature.Hosting`, `/packages/OpenFeature.Providers.Flagd`, …)
- Specification: https://openfeature.dev/specification (sections 01 flag evaluation, 02 providers, 03 evaluation context, 04 hooks, 05 events, 06 tracking, appendix A multi-provider/in-memory)

Grep recipes on a fresh clone (`git clone https://github.com/open-feature/dotnet-sdk && cd dotnet-sdk`):

```sh
grep -rn "public .*Async(" src/OpenFeature/IFeatureClient.cs            # evaluation signatures
grep -rn "public static OpenFeatureBuilder" src/OpenFeature.Hosting/    # every DI builder method
grep -rn "public virtual\|public abstract" src/OpenFeature/FeatureProvider.cs src/OpenFeature/Hook.cs
grep -rn "class .*Options" src/OpenFeature.Hosting/                     # OpenFeatureOptions, PolicyNameOptions, FeatureLifecycleStateOptions
grep -rn "Description(" src/OpenFeature/Constant/                       # ErrorType / ProviderStatus string values
grep -rn "Obsolete\|Experimental(" src/                                 # deprecated and experimental surface
sed -n 1,80p CHANGELOG.md                                               # behaviour changes since this file was written
# contrib
git clone https://github.com/open-feature/dotnet-sdk-contrib && cd dotnet-sdk-contrib
cat .release-please-manifest.json                                       # current package versions
grep -rn "public .*Provider(" src/*/ --include='*.cs' | grep -v Test    # every provider constructor
grep -rn "internal const string EnvVar" src/OpenFeature.Providers.Flagd/FlagdConfig.cs
```
