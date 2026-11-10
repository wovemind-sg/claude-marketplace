# OpenFeature SDKs beyond Go, .NET and Python

Reference for the remaining official OpenFeature SDKs. Go, .NET and Python have their own deep-dive files in this directory; core concepts (evaluation API, providers, context, hooks, events, paradigms) are covered in the concepts file. This file gives, per SDK, the package, the current version and spec level, the feature matrix, and the minimum code to install a provider, wait for it, evaluate a flag, attach a hook, and listen for events.

Source of truth: `openfeature.dev` docs (generated from each SDK's README) and `src/datasets/sdks/sdk-compatibility.json` as of 2026-08/09. Versions move fast; when a number here matters, re-check the compatibility page linked at the end.

## Table of contents

1. [Compatibility matrix](#compatibility-matrix)
2. [Server-side SDKs (dynamic context)](#server-side-sdks-dynamic-context)
   - [Java](#java)
   - [Node.js](#nodejs)
   - [NestJS](#nestjs)
   - [PHP](#php)
   - [Ruby](#ruby)
   - [Rust](#rust)
   - [C++](#c)
   - [Dart (server)](#dart-server)
3. [Client-side SDKs (static context)](#client-side-sdks-static-context)
   - [Web (JavaScript)](#web-javascript)
   - [React](#react)
   - [Angular](#angular)
   - [Kotlin (Android / multiplatform)](#kotlin-android--multiplatform)
   - [Swift (iOS / Apple platforms)](#swift-ios--apple-platforms)
   - [Dart (client, beta)](#dart-client-beta)
4. [Client-side vs server-side paradigm differences](#client-side-vs-server-side-paradigm-differences)
5. [The JavaScript package family](#the-javascript-package-family)
6. [When this file is silent](#when-this-file-is-silent)

## Compatibility matrix

Data from `sdk-compatibility.json`. "Stable" means the latest release is >= 1.0. Feature columns: Prov = providers, Targ = targeting, Hook = hooks, Log = logging, Dom = domains (formerly "named clients"), Evt = eventing, Trk = tracking, TxC = transaction context propagation (server-side only), Shut = shutdown, Ext = extending (custom providers/hooks), Multi = multi-provider. Legend: ✅ implemented, ⚠️ in progress, ❌ not implemented, ❓ unknown.

### Server-side

| SDK | Package / install | Release | Spec | Stable | Prov | Targ | Hook | Log | Dom | Evt | Trk | TxC | Shut | Ext | Multi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Java | `dev.openfeature:sdk` (Maven Central) | 1.22.1 | 0.7.0 | yes | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❓ (docs: experimental `MultiProvider`) |
| Node.js | `npm install --save @openfeature/server-sdk` | 1.23.0 | 0.8.0 | yes | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| NestJS | `npm install --save @openfeature/nestjs-sdk` | inherits Node.js | inherits | yes | wrapper over Node.js SDK; not listed separately in the matrix |
| PHP | `composer require open-feature/sdk` | 2.3.0 | 0.5.1 | yes | ✅ | ✅ | ✅ | ✅ | ❌ | ⚠️ | ❓ | ❓ | ❌ | ✅ | ❓ (docs: `MultiProvider` present) |
| Ruby | `bundle add openfeature-sdk` | 0.6.5 | 0.8.0 | no | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❓ |
| Rust | `open-feature = "0.3.0"` (crates.io) | 0.3.0 | 0.5.2 | no | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❓ | ❓ | ✅ | ✅ | ❓ |
| C++ | Bazel module (`cpp-sdk`) | 0.0.1 | 0.2.0 | no | ⚠️ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ❓ |
| Dart (server) | `openfeature_dart_server_sdk: ^0.0.24` (pub.dev) | 0.0.24 | 0.8.0 | no | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |

For comparison, the SDKs covered elsewhere: Go 1.18.0 (spec 0.7.0, stable), .NET 2.14.1 (spec 0.8.0, stable), Python 0.10.0 (spec 0.8.0, not stable).

### Client-side

| SDK | Package / install | Release | Spec | Stable | Prov | Targ | Hook | Log | Dom | Evt | Trk | Shut | Ext | Multi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Web (JS) | `npm install --save @openfeature/web-sdk` | 1.10.0 | 0.8.0 | yes | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| React | `npm install --save @openfeature/react-sdk` | inherits Web | inherits | yes | wrapper over Web SDK; not listed separately in the matrix |
| Angular | `npm install --save @openfeature/angular-sdk` | inherits Web | inherits | yes | wrapper over Web SDK; not listed separately in the matrix |
| Kotlin | `dev.openfeature:kotlin-sdk:0.8.0` (Maven Central) | 0.8.0 | 0.8.0 | no | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Swift (iOS) | SPM `open-feature/swift-sdk` from 0.6.0; CocoaPods `pod 'OpenFeature', '~> 0.5.0'` | 0.6.0 | 0.8.0 | no | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ❓ (docs: `MultiProvider` present) |
| Dart (client) | `openfeature_dart_client_sdk: ^0.0.1-beta.1` | 0.0.1-beta.1 | n/a | no (beta) | excluded from the matrix until conformance completes |

The React, Angular and NestJS entries inherit the Web / Node.js compatibility row in the ecosystem dataset (`includeInSupportMatrix: false`); the Vercel Flags SDK adapters for Next.js and SvelteKit are also listed in the SDK dataset but link to `https://flags-sdk.dev/docs/api-reference/adapters/openfeature` and are not OpenFeature-maintained.

## Server-side SDKs (dynamic context)

All server SDKs accept an evaluation context per call and merge it with API-level and client-level context. Every SDK here exposes a singleton API object, a provider registration method, `getClient()` (optionally with a domain), and typed `getXValue` / `getXDetails` evaluation methods.

### Java

- Docs: https://openfeature.dev/docs/reference/sdks/server/java — Repo: https://github.com/open-feature/java-sdk — Contrib: https://github.com/open-feature/java-sdk-contrib — Javadoc: https://javadoc.io/doc/dev.openfeature/sdk
- Requires Java 11+ (compiler target 11). Uses SLF4J for logging.

Install:

```xml
<dependency>
    <groupId>dev.openfeature</groupId>
    <artifactId>sdk</artifactId>
    <version>1.22.1</version>
</dependency>
```

```groovy
implementation 'dev.openfeature:sdk:1.22.1'
```

Hello flag (the SDK ships an `InMemoryProvider` whose flags are built with `Flag.builder()`; the docs do not show its package, check the javadoc):

```java
Map<String, Flag<?>> myFlags = new HashMap<>();
myFlags.put("v2_enabled", Flag.builder()
    .variant("on", true).variant("off", false).defaultVariant("on").build());

OpenFeatureAPI api = OpenFeatureAPI.getInstance();
try {
    api.setProviderAndWait(new InMemoryProvider(myFlags)); // blocks until READY or throws
} catch (Exception e) { /* handle initialization failure */ }

Client client = api.getClient();                       // or api.getClient("my-domain")
Map<String, Value> attrs = new HashMap<>();
attrs.put("email", new Value("user@example.com"));
EvaluationContext ctx = new ImmutableContext("user-123", attrs);
boolean flagValue = client.getBooleanValue("v2_enabled", false, ctx);
```

- Wait for ready: `api.setProviderAndWait(provider)` (blocking, throws on failure). Non-blocking: `api.setProvider(provider)`, then watch events. Domain-scoped: `api.setProvider("my-domain", provider)`.
- Hooks: `api.addHooks(new ExampleHook())`, `client.addHooks(...)`, or per call `client.getBooleanValue(key, false, ctx, FlagEvaluationOptions.builder().hook(new ExampleHook()).build())`. A built-in `LoggingHook` logs at debug level.
- Events: `client.onProviderConfigurationChanged((EventDetails d) -> {...})`, `OpenFeatureAPI.getInstance().onProviderStale(...)`, and equivalents for ready/error.
- Transaction context: `api.setTransactionContextPropagator(new ThreadLocalTransactionContextPropagator())` then `api.setTransactionContext(ctx)` in a request handler; default is `NoOpTransactionContextPropagator`.
- Tracking: `api.getClient().track("visited-promo-page", new MutableTrackingEventDetails(99.77).add("currency", "USD"))`. Throws `IllegalArgumentException` on an empty event name.
- Multi-provider (experimental): `new MultiProvider(List.of(primary, fallback))` from `dev.openfeature.sdk.multiprovider`.
- Shutdown: `OpenFeatureAPI.getInstance().shutdown()`.
- Custom provider: implement `FeatureProvider` (`getMetadata`, `initialize`, `shutdown`, `getBooleanEvaluation`, ...); extend `EventProvider` and call `emitProviderConfigurationChanged(details)` to fire events. Provider state is queried via `client.getProviderState()`.
- Framework tutorials: Spring Boot (https://openfeature.dev/docs/tutorials/getting-started/java/spring-boot) exposes `OpenFeatureAPI.getInstance()` as a `@Bean` and calls `setProviderAndWait(new FlagdProvider())`, catching `OpenFeatureError`; flagd provider artifact `dev.openfeature.contrib.providers:flagd` (0.11.20 in that tutorial). Dropwizard (https://openfeature.dev/docs/tutorials/getting-started/java/dropwizard) either uses the SDK directly or the community module `io.github.sideshowcoder:dropwizard-openfeature:1.0.1` (not officially supported), and injects `OpenFeatureAPI.getInstance().getClient("dev.openfeature.OpenFeatureExample")` into a Jersey resource.

### Node.js

- Docs: https://openfeature.dev/docs/reference/sdks/server/javascript — Repo: https://github.com/open-feature/js-sdk (package `packages/server`) — Contrib: https://github.com/open-feature/js-sdk-contrib — API: https://open-feature.github.io/js-sdk/modules/_openfeature_server_sdk.html
- Requires Node.js 18+. `@openfeature/core` is a peer dependency: npm installs it automatically, yarn does not (`yarn add @openfeature/server-sdk @openfeature/core`).

```ts
import { OpenFeature, TypedInMemoryProvider, ProviderEvents } from '@openfeature/server-sdk';

const myFlags = {
  v2_enabled: { variants: { on: true, off: false }, disabled: false, defaultVariant: 'on' },
} as const;

try {
  await OpenFeature.setProviderAndWait(new TypedInMemoryProvider(myFlags));
} catch (error) { console.error('Failed to initialize provider:', error); }

const client = OpenFeature.getClient();           // or OpenFeature.getClient('my-domain')
const v2Enabled = await client.getBooleanValue('v2_enabled', false, {
  targetingKey: req.session.id, email: req.session.email,
});
```

- Wait for ready: `await OpenFeature.setProviderAndWait(provider)`; `OpenFeature.setProvider(provider)` is synchronous and you track status with events. Domains: `OpenFeature.setProvider('my-domain', provider)`.
- Hooks: `OpenFeature.addHooks(new ExampleGlobalHook())`, `client.addHooks(...)`, or `client.getBooleanValue('bool-flag', false, { hooks: [new ExampleHook()] })`. A hook implements `Hook` with optional `before/after/error/finally` methods.
- Events: `OpenFeature.addHandler(ProviderEvents.Ready, (eventDetails) => {...})` and `client.addHandler(ProviderEvents.Error, ...)`.
- Context layering: `OpenFeature.setContext({ region })`, `client.setContext({ version })`, per-invocation object as third argument.
- Transaction context: `OpenFeature.setTransactionContextPropagator(new AsyncLocalStorageTransactionContextPropagator())`, then in Express middleware `OpenFeature.setTransactionContext({ targetingKey: req.user.id, ipAddress: ip }, () => next())`.
- Logging: `OpenFeature.setLogger(logger)` / `client.setLogger(logger)` with anything matching the `Logger` interface (console works).
- Multi-provider: `new MultiProvider([{ provider: a }, { provider: b }], new FirstMatchStrategy())`; strategies `FirstMatchStrategy` (default; skips `FLAG_NOT_FOUND`, stops on other errors), `FirstSuccessfulStrategy` (skips any error), `ComparisonStrategy(fallbackProvider, onMismatch)`.
- Tracking: `client.track('new-feature-used')`. Shutdown: `await OpenFeature.close()`.
- Type-safe flag keys via TypeScript module augmentation; see the `@openfeature/core` README.
- Custom provider: implement `Provider` with `runsOn = 'server'`, `metadata`, async `resolveBooleanEvaluation(flagKey, defaultValue, context, logger)` and siblings, optional `initialize`, `onClose`, `events` (an `OpenFeatureEventEmitter`).
- Library authors: list `@openfeature/server-sdk` as a `peerDependency`; do not add a peer on `@openfeature/core` yourself.
- Tutorial: Express walkthrough at https://openfeature.dev/docs/tutorials/getting-started/node uses `@openfeature/flagd-provider` and `OpenFeature.setProvider(new FlagdProvider())`.

### NestJS

- Docs: https://openfeature.dev/docs/reference/sdks/server/javascript/nestjs — Repo: https://github.com/open-feature/js-sdk (package `packages/nest`)
- Requires Node.js 20+, NestJS 8+. Peer deps: `@openfeature/server-sdk` (^1.17.1 minimum), `@nestjs/common`, `@nestjs/core` (^8 to ^11), `rxjs` (^7 or ^8). Yarn: `yarn add @openfeature/nestjs-sdk @openfeature/server-sdk @openfeature/core`.

Module registration (providers, hooks, logging and event handlers are all configured in `forRoot`):

```ts
import { Module } from '@nestjs/common';
import { OpenFeatureModule, TypedInMemoryProvider } from '@openfeature/nestjs-sdk';

@Module({
  imports: [
    OpenFeatureModule.forRoot({
      defaultProvider: new TypedInMemoryProvider({
        testBooleanFlag: { defaultVariant: 'default', variants: { default: true }, disabled: false },
      }),
      providers: { differentProvider: new TypedInMemoryProvider() }, // domain-bound providers
      // contextFactory: (ctx: ExecutionContext) => ({ targetingKey: ... }),  // per-request context
      // useGlobalInterceptor: false,                                          // opt out of the global interceptor
    }),
  ],
})
export class AppModule {}
```

Decorators:

```ts
// Inject an evaluation as an Observable<EvaluationDetails<boolean>> into a route handler
@Get('/welcome')
welcome(@BooleanFeatureFlag({ flagKey: 'testBooleanFlag', defaultValue: false }) feature: Observable<EvaluationDetails<boolean>>) {
  return feature.pipe(map((d) => (d.value ? 'new' : 'old')));
}

// Inject clients into services
constructor(
  @OpenFeatureClient() private defaultClient: Client,
  @OpenFeatureClient({ domain: 'my-domain' }) private scopedClient: Client,
) {}

// Gate a route or controller; throws if the flag is not enabled
@RequireFlagsEnabled({ flags: [{ flagKey: 'testBooleanFlag' }] })
@Get('/welcome')
```

`contextFactory` runs inside a NestJS interceptor and its result is used for every evaluation in that request (HTTP headers, client IP, and so on). Everything from the Node.js SDK (events, hooks, `OpenFeature.setProviderAndWait`) is re-exported from `@openfeature/nestjs-sdk`.

### PHP

- Docs: https://openfeature.dev/docs/reference/sdks/server/php — Repo: https://github.com/open-feature/php-sdk — Contrib: https://github.com/open-feature/php-sdk-contrib
- Requires PHP 8.0+. Logging via PSR-3 `LoggerInterface` (`$api->setLogger()`, `$client->setLogger()`; a client copies the API logger at creation and does not re-sync later).

```php
use OpenFeature\OpenFeatureAPI;
use OpenFeature\implementation\flags\EvaluationContext;
use OpenFeature\implementation\flags\Attributes;

$api = OpenFeatureAPI::getInstance();
$api->setProvider(new MyProvider());          // no setProviderAndWait in PHP
$client = $api->getClient();                   // getClient('MyClass') gives a named client
$context = new EvaluationContext('targetingKey', new Attributes(['email' => 'user@example.com']));
$enabled = $client->getBooleanValue('v2_enabled', false, $context);
```

- Not yet available (tracked in https://github.com/open-feature/php-sdk/issues/93): events, shutdown, named clients / domains. Registration is synchronous; there is nothing to "wait" for.
- Hooks: `$api->addHooks(new ExampleGlobalHook())`, `$client->addHooks(...)`, or per call `$client->getBooleanValue("boolFlag", false, $context, new EvaluationOptions([new ExampleInvocationHook()]))`. Implement `OpenFeature\interfaces\hooks\Hook` (`before/after/error/finally/supportsFlagValueType`) or extend a typed base (`BooleanHook`, `StringHook`, `IntegerHook`, `FloatHook`, `ObjectHook`).
- Multi-provider: `new OpenFeature\implementation\multiprovider\MultiProvider([['name' => 'A', 'provider' => $a], ['provider' => $b]], new FirstSuccessfulStrategy())`; strategies live in `OpenFeature\implementation\multiprovider\strategy\` (`FirstMatchStrategy` default, `FirstSuccessfulStrategy`, `ComparisonStrategy($fallbackProvider, $onMismatch)`); custom strategies extend `BaseEvaluationStrategy`. Known limitation: hooks registered on sub-providers are not executed; register at API or client level instead.
- In-memory provider: the docs' multi-provider example constructs `new InMemoryProvider(['feature-enabled' => true, 'api-timeout' => 30])` but do not show its namespace; check the SDK repo before relying on it.
- Custom provider: implement `OpenFeature\interfaces\provider\Provider` (`resolveBooleanValue`, `resolveStringValue`, `resolveIntegerValue`, `resolveFloatValue`, `resolveObjectValue`, `getMetadata`, `getHooks`, `setLogger`) or extend `OpenFeature\implementation\provider\AbstractProvider`.
- Tutorial: Laravel walkthrough at https://openfeature.dev/docs/tutorials/getting-started/php installs `open-feature/flagd-provider` and builds `new FlagdProvider(['httpConfig' => new HttpConfig($guzzleClient, $httpFactory, $httpFactory)])` (namespace `OpenFeature\Providers\Flagd`).

### Ruby

- Docs: https://openfeature.dev/docs/reference/sdks/server/ruby — Repo: https://github.com/open-feature/ruby-sdk — Contrib: https://github.com/open-feature/ruby-sdk-contrib
- Supports Ruby 3.4.x and 4.0.x (all versions in active maintenance). Install with `bundle add openfeature-sdk` or `gem install openfeature-sdk`.

```ruby
require 'open_feature/sdk'

OpenFeature::SDK.configure do |config|
  config.set_provider(OpenFeature::SDK::Provider::InMemoryProvider.new({ "v2_enabled" => true }))
  config.evaluation_context = OpenFeature::SDK::EvaluationContext.new("host" => "myhost.com")
end

client = OpenFeature::SDK.build_client            # build_client(domain: "legacy_flags", evaluation_context: ...)
enabled = client.fetch_boolean_value(
  flag_key: 'v2_enabled', default_value: false,
  evaluation_context: OpenFeature::SDK::EvaluationContext.new(targeting_key: "user-123")
)
details = client.fetch_boolean_details(flag_key: 'v2_enabled', default_value: false)
```

- Wait for ready: `OpenFeature::SDK.set_provider_and_wait(provider, timeout: 60, domain: "feature-flags")` (default timeout 30 s) raises `OpenFeature::SDK::ProviderInitializationError` (`error_code`, `original_error`). Also available inside `configure` as `config.set_provider_and_wait`.
- Hooks: a class that `include OpenFeature::SDK::Hooks::Hook` defining any of `before(hook_context:, hints:)`, `after(hook_context:, evaluation_details:, hints:)`, `error(hook_context:, exception:, hints:)`, `finally(hook_context:, evaluation_details:, hints:)`. Register with `OpenFeature::SDK.hooks << MyHook.new`, `client.hooks << MyHook.new`, or `fetch_boolean_value(..., hooks: [MyHook.new])`. Built-in `OpenFeature::SDK::Hooks::LoggingHook.new(logger:, include_evaluation_context: true)`.
- Events: `OpenFeature::SDK.add_handler(OpenFeature::SDK::ProviderEvent::PROVIDER_READY, ->(event_details) { ... })` and `remove_handler`. Providers `include OpenFeature::SDK::Provider::EventEmitter` and call `emit_event(OpenFeature::SDK::ProviderEvent::PROVIDER_CONFIGURATION_CHANGED, message: "...")`.
- Domains: `config.set_provider(provider, domain: "legacy_flags")`, `build_client(domain: "legacy_flags")`. `OpenFeature::SDK::Provider::NoOpProvider` exists too.
- Transaction context: `OpenFeature::SDK.set_transaction_context_propagator(OpenFeature::SDK::ThreadLocalTransactionContextPropagator.new)` then `OpenFeature::SDK.set_transaction_context(EvaluationContext.new(...))`; merge order invocation > client > transaction > API. Custom propagators `include OpenFeature::SDK::TransactionContextPropagator`.
- Tracking: `client.track("purchase", evaluation_context: ..., tracking_event_details: OpenFeature::SDK::TrackingEventDetails.new(value: 99.99, plan: "premium"))`; no-op if the provider has no `track`.
- Shutdown: `OpenFeature::SDK.shutdown`.
- Custom provider is duck-typed: `init` (not `initialize`, to avoid clashing with Ruby's constructor), `shutdown`, `fetch_boolean_value(flag_key:, default_value:, evaluation_context: nil)` and the string/number/integer/float/object siblings, optional `track`.

### Rust

- Docs: https://openfeature.dev/docs/reference/sdks/server/rust — Repo: https://github.com/open-feature/rust-sdk — Contrib: https://github.com/open-feature/rust-sdk-contrib — API: https://docs.rs/open-feature
- Built with Rust 1.80.1. `Cargo.toml`: `open-feature = "0.3.0"`; add `features = ["structured-logging"]` for JSON log output from the logging hook.

```rust
let mut api = OpenFeature::singleton_mut().await;   // async lock guards the singleton
api.set_provider(MyProvider::default()).await;       // awaiting completes provider initialization
let client = api.create_client();                     // or api.create_named_client("named")

let ctx = EvaluationContext::default()
    .with_targeting_key("user-123")
    .with_custom_field("email", "user@example.com".to_string());
let enabled = client.get_bool_value("v2_enabled", Some(&ctx), None).await.unwrap_or(false);
let details = client.get_int_details("key", Some(&ctx), None).await;
```

- The default provider is `NoOpProvider`, which always returns `Err`; there is no in-memory provider in the docs, so tests typically use `NoOpProvider::default()` plus `unwrap_or`, or a small custom `FeatureProvider`.
- Hooks: `api.add_hook(MyHook::default()).await`, `api.create_client().with_hook(MyHook::default())`, or `EvaluationOptions::default().with_hook(MyHook::default())` passed as the third argument. Implement `Hook` with `#[async_trait]` and all four of `before/after/error/finally`. Built-in logging hook: `api.create_client().with_logging_hook(true)` (argument = include evaluation context).
- Named clients: `api.set_named_provider("named", provider).await`, `api.create_named_client("named")`.
- Events are not yet available. Shutdown: `api.shutdown().await`.
- Struct flags: `client.get_struct_value::<T>()` converts the provider's `StructValue` via `TryFrom<StructValue>`, returning `EvaluationErrorCode::TypeMismatch` on failure.
- Tutorial: Axum walkthrough at https://openfeature.dev/docs/tutorials/getting-started/rust uses the `open-feature-flagd` crate (`FlagdProvider::new(FlagdOptions { .. })`).

### C++

- Docs: https://openfeature.dev/docs/reference/sdks/server/cpp — Repo: https://github.com/open-feature/cpp-sdk — Contrib: https://github.com/open-feature/cpp-sdk-contrib
- Requires C++17 and the Bazel build system; add the dependency to `MODULE.bazel` or `WORKSPACE`. Release 0.0.1 against spec 0.2.0: hooks, logging, eventing, tracking and transaction context are listed as not implemented.

```cpp
std::unordered_map<std::string, std::any> my_flags = {{"v2_enabled", true}};
openfeature::OpenFeatureAPI& api = openfeature::OpenFeatureAPI::GetInstance();
api.SetProviderAndWait(std::make_shared<openfeature::InMemoryProvider>(my_flags));  // SetProvider() is non-blocking

std::shared_ptr<openfeature::Client> client = api.GetClient();  // api.GetClient("my-domain")
openfeature::EvaluationContext req_ctx = openfeature::EvaluationContext::Builder()
    .WithTargetingKey("session-id-12345").WithAttribute("email", "user@example.com").build();
bool flag_value = client->GetBooleanValue("v2_enabled", false, req_ctx);
```

- Domains: `api.SetProvider("my-domain", std::make_shared<CachedProvider>())`. Shutdown: `openfeature::OpenFeatureAPI::GetInstance().Shutdown()`.
- Custom provider: subclass `openfeature::FeatureProvider` (`GetMetadata`, `Init` and `Shutdown` returning `absl::Status`, `GetBooleanEvaluation` returning `std::unique_ptr<openfeature::BoolResolutionDetails>`, and the string/int/double/object variants). Hooks conform to the `Hook` interface; use `UnimplementedHook` to avoid empty method bodies.

### Dart (server)

- Docs: https://openfeature.dev/docs/reference/sdks/server/dart — Repo: https://github.com/open-feature/dart-sdk (package `packages/openfeature_dart_server_sdk`) — Contrib: https://github.com/open-feature/dart-server-sdk-contrib — API: https://pub.dev/documentation/openfeature_dart_server_sdk/latest/
- Requires Dart 3.12.2 (latest maintained versions only). `pubspec.yaml`: `openfeature_dart_server_sdk: ^0.0.24`, then `dart pub get`. Git dependencies must now add `path: packages/openfeature_dart_server_sdk`.

```dart
import 'package:openfeature_dart_server_sdk/feature_provider.dart';
import 'package:openfeature_dart_server_sdk/open_feature_api.dart';

final api = OpenFeatureAPI();
await api.setProviderAndWait(InMemoryProvider({'new-feature': true, 'welcome-message': 'Hello'}));
final client = api.getClient('my-app');                     // getClient('name', domain: 'cache-domain')
final enabled = await client.getBooleanFlag('new-feature', defaultValue: false,
    context: const EvaluationContext(attributes: {'user': 'user-123'}));
final details = await client.getBooleanDetails('new-feature', defaultValue: false);
```

- Note the method names: `getBooleanFlag` / `getStringFlag` / `getIntegerFlag` / `getDoubleFlag` / `getObjectFlag` plus `getXDetails`, all async. Global context via `api.setGlobalContext(OpenFeatureEvaluationContext({...}))`.
- Hooks: `api.addHooks([MyGlobalHook()])`, `client.addHook(MyClientHook())`; invocation-level hooks are not yet supported. Extend `BaseHook` (`before` may return a context map to merge, `after`, `error`, `finally_`). Built-in `LoggingHook` (redacts context values unless `includeContext: true`) and `OpenTelemetryHook`.
- Events: `api.events.listen((event) { if (event.type == OpenFeatureEventType.PROVIDER_CONFIGURATION_CHANGED) ... })`; client-scoped `client.addHandler(...)` / `client.removeHandler(sub)`; an SDK-level bus `OpenFeatureEvents.instance.subscribe(..., filter: EventFilter(types: {OpenFeatureEventType.flagEvaluated}))`.
- Domains: `api.registerProviderAndWait(provider)` returns an id; `api.bindClientToProviderAndWait('cache-domain', id)`.
- Multi-provider (experimental): `MultiProvider([InMemoryProvider({...}), InMemoryProvider({...})])` from `multi_provider.dart`, `FirstMatchStrategy` default.
- Transaction context: `TransactionContextManager().pushContext(TransactionContext(transactionId:, attributes:))` / `withContext(id, attrs, () async {...})` / `popContext()`.
- Shutdown: `await api.dispose()`, optionally orchestrated with `ShutdownManager().registerHook(ShutdownHook(name:, phase: ShutdownPhase.PROVIDER_SHUTDOWN, execute:))`.
- Testing: set an `InMemoryProvider` in `setUp` and call `await OpenFeatureAPI.resetInstance()` in `tearDown`.

## Client-side SDKs (static context)

Client SDKs evaluate against a single, global evaluation context (one user or session). Providers fetch or compute all flags when the context is set, so evaluation is synchronous and cheap; changing context triggers reconciliation. See the paradigm section below.

### Web (JavaScript)

- Docs: https://openfeature.dev/docs/reference/sdks/client/web — Repo: https://github.com/open-feature/js-sdk (package `packages/web`) — Contrib: https://github.com/open-feature/js-sdk-contrib — API: https://open-feature.github.io/js-sdk/modules/_openfeature_web_sdk.html
- Requires an ES2015 browser. Yarn: `yarn add @openfeature/web-sdk @openfeature/core`.

```ts
import { OpenFeature, TypedInMemoryProvider, ProviderEvents } from '@openfeature/web-sdk';

// Context is set at (or after) provider registration, not per evaluation
try {
  await OpenFeature.setProviderAndWait(new TypedInMemoryProvider(myFlags), { targetingKey: 'user-123' });
} catch (error) { console.error('Failed to initialize provider:', error); }

const client = OpenFeature.getClient();
const v2Enabled = client.getBooleanValue('v2_enabled', false);   // synchronous, no context argument
await OpenFeature.setContext({ targetingKey: 'user-456' });      // async; provider reconciles its cache
```

- Wait for ready: `await OpenFeature.setProviderAndWait(provider[, context])`, or `OpenFeature.setProvider(provider[, context])` and wait for `ProviderEvents.Ready`. Evaluating before READY returns defaults.
- Hooks: `OpenFeature.addHooks(...)`, `client.addHooks(...)`, `client.getBooleanValue('bool-flag', false, { hooks: [new ExampleHook()] })`.
- Events: `OpenFeature.addHandler(ProviderEvents.Ready, (eventDetails) => {...})`, `client.addHandler(ProviderEvents.Error, ...)`; providers may also emit `PROVIDER_CONFIGURATION_CHANGED`.
- Domains: `OpenFeature.setProvider('my-domain', provider, context)`, `OpenFeature.getClient('my-domain')`, `await OpenFeature.setContext('my-domain', {...})`, `OpenFeature.clearContext('my-domain')`, `OpenFeature.clearContexts()`. A domain context overrides the global one for clients bound to it.
- Multi-provider: `new MultiProvider([{ provider: new ProviderA() }, { provider: new ProviderB() }], new FirstSuccessfulStrategy())`; `client.track(...)` fans out to all providers.
- Logging, tracking (`client.track('new-feature-used')`), shutdown (`await OpenFeature.close()`) and type-safe flag keys work as in the Node.js SDK.
- Custom provider: `runsOn = 'client'`, synchronous `resolveBooleanEvaluation(...)` returning `ResolutionDetails<boolean>`, optional `onContextChange(oldContext, newContext): Promise<void>` to reconcile the cache, `initialize`, `onClose`, `events`.

### React

- Docs: https://openfeature.dev/docs/reference/sdks/client/web/react — Repo: https://github.com/open-feature/js-sdk (package `packages/react`) — Example app: https://github.com/open-feature/react-test-app
- Requires React 16.8+. Peer deps `@openfeature/web-sdk` and `react`; yarn: `yarn add @openfeature/react-sdk @openfeature/web-sdk @openfeature/core`. Import everything from `@openfeature/react-sdk` (it re-exports the web SDK and core).

```tsx
import { OpenFeature, OpenFeatureProvider, TypedInMemoryProvider, useFlag } from '@openfeature/react-sdk';

// Set the provider once; no need to await, the React SDK handles re-render and suspense
OpenFeature.setProvider(new TypedInMemoryProvider(flagConfig));

function App() {
  return (
    <OpenFeatureProvider>          {/* or <OpenFeatureProvider domain="my-domain"> / client={client} */}
      <Page />
    </OpenFeatureProvider>
  );
}

function Page() {
  const { value: showNewMessage } = useFlag('new-message', false);   // query-style hook
  return showNewMessage ? <p>New</p> : <p>Old</p>;
}
```

- Evaluation hooks: `useFlag(key, default, options)`, typed `useBooleanFlagValue`, `useBooleanFlagDetails` (returns `{ value, variant, reason, flagMetadata }`) and the string/number/object equivalents, `useSuspenseFlag(key, default)` (equivalent to `{ suspend: true }`), `useTrack()` returning `{ track }`, `useWhenProviderReady()` (boolean gate), `useOpenFeatureClientStatus()` (`ProviderStatus.NOT_READY | ERROR | FATAL | ...`).
- Declarative component: `<FeatureFlag flagKey="theme" matchValue="dark" defaultValue="light" fallback={<Other/>} predicate={(expected, details) => ...}>` renders children (JSX or a render function receiving evaluation details) when the flag matches; `matchValue` is required except for boolean flags.
- Re-render options (per hook or on `OpenFeatureProvider`): `updateOnContextChanged` (default true; re-render when evaluation context changes) and `updateOnConfigurationChanged` (default true; re-render on `PROVIDER_CONFIGURATION_CHANGED`, using the event's `flagsChanged` list to diff when present).
- Suspense (experimental): `suspend`, `suspendUntilReady`, `suspendWhileReconciling` options; wrap flag-using components in `<Suspense fallback={...}>` or you get "A React component suspended while rendering, but no fallback UI was specified". React 16/17 legacy suspense mounts siblings early; use `useWhenProviderReady` there or upgrade to React 18.
- Testing: `<OpenFeatureTestProvider flagValueMap={{ 'my-boolean-flag': true }} delayMs={1000} provider={new MyTestProvider()}>`; `provider` accepts `Partial<Provider>`.
- Observability: React re-renders can inflate evaluation telemetry; use the debounce hook from `js-sdk-contrib/libs/hooks/debounce`.

### Angular

- Docs: https://openfeature.dev/docs/reference/sdks/client/web/angular — Repo: https://github.com/open-feature/js-sdk (`packages/angular/projects/angular-sdk`) — Example app: https://github.com/open-feature/angular-test-app
- Requires Angular 16+. Peer deps `@openfeature/web-sdk`, `@angular/common`, `@angular/core`; yarn: `yarn add @openfeature/angular-sdk @openfeature/web-sdk @openfeature/core`. Import from `@openfeature/angular-sdk` only.

Standalone configuration (recommended; `OpenFeatureModule.forRoot()` is deprecated):

```ts
import { provideOpenFeature } from '@openfeature/angular-sdk';

export const appConfig: ApplicationConfig = {
  providers: [
    provideOpenFeature({
      provider: yourFeatureProvider,
      domainBoundProviders: { domain1: new YourOpenFeatureProvider() },  // optional
      context: { user: { id: 'user123', role: 'admin' } },              // object or () => EvaluationContext
    }),
  ],
};
```

Structural directives (`booleanFeatureFlag`, `numberFeatureFlag`, `stringFeatureFlag`, `objectFeatureFlag`; each is standalone and must be imported into the component):

```html
<div *booleanFeatureFlag="'isFeatureEnabled'; default: true">Shown when enabled.</div>

<div *booleanFeatureFlag="'isFeatureEnabled'; default: true; domain: 'userDomain';
      else: featureElse; initializing: featureInit; reconciling: featureRecon;
      updateOnContextChanged: false; updateOnConfigurationChanged: false">...</div>
<ng-template #featureElse>disabled</ng-template>
<ng-template #featureInit>provider initializing</ng-template>
<ng-template #featureRecon>context reconciling</ng-template>

<!-- non-boolean directives compare against `value`; omit it to always render and just bind the result -->
<div *stringFeatureFlag="'themeColor'; value: 'dark'; default: 'light'; let value; let details = evaluationDetails">
  {{ value }} because {{ details.reason }}
</div>
```

- Programmatic access: `inject(FeatureFlagService).getBooleanDetails('my-feature', false, 'my-domain', { updateOnConfigurationChanged: false })` returns an Observable of evaluation details that re-emits on flag or context changes; `toSignal(...)` converts to a Signal. Also `getStringDetails`, `getNumberDetails`, `getObjectDetails<T>`.
- Update context at runtime through the global API: `OpenFeature.setContext({...})`.
- Same debounce-hook advice as React for telemetry.

### Kotlin (Android / multiplatform)

- Docs: https://openfeature.dev/docs/reference/sdks/client/kotlin — Repo: https://github.com/open-feature/kotlin-sdk
- Static-context SDK for mobile, web and desktop clients. Artifact `dev.openfeature:kotlin-sdk:0.8.0` (before 0.6.0 it was `android-sdk`); base package is `dev.openfeature.kotlin.sdk` (was `dev.openfeature.sdk` before 0.6.0). Multiplatform: add to `commonMain.dependencies`.

```kotlin
coroutineScope.launch(Dispatchers.Default) {
    OpenFeatureAPI.setEvaluationContext(
        ImmutableContext(targetingKey = session.getId, attributes = mutableMapOf("region" to Value.String("us-east-1"))))
    OpenFeatureAPI.setProviderAndWait(MyProvider())          // suspends until READY
    val client = OpenFeatureAPI.getClient()
    val enabled = client.getBooleanValue("boolFlag", defaultValue = false)
}
```

- Non-blocking: `OpenFeatureAPI.setProvider(MyProvider())` (initialization runs on the IO dispatcher); poll `OpenFeatureAPI.getStatus()` or observe events. Evaluations are only meaningful once the status is Ready.
- Hooks: `OpenFeatureAPI.addHooks(listOf(ExampleHook()))`, `client.addHooks(listOf(...))`, `client.getBooleanValue(key, false, FlagEvaluationOptions(listOf(ExampleHook())))`. Built-in `LoggingHook(logger = LoggerFactory.getLogger("FeatureFlags"), logEvaluationContext = false, ...)` with PII allow/deny lists (`includeAttributes`, `excludeAttributes`, `LoggingHook.DEFAULT_SENSITIVE_KEYS`).
- Events: `OpenFeatureAPI.observe<OpenFeatureProviderEvents>().collect { ... }` (a Kotlin `Flow`).
- Tracking: `OpenFeatureAPI.getClient().track("Checkout", TrackingEventDetails(499.99, ImmutableStructure("numberOfItems" to Value.Integer(4))))`.
- Domains are "currently in development"; multi-provider is documented in the repo at `docs/multiprovider/README.md`. Shutdown: `OpenFeatureAPI.shutdown()`.
- No in-memory provider is shown in the docs; the repo ships a sample app for provider/hook development that should not be used as a reference implementation.
- Custom provider: implement `FeatureProvider` (`getBooleanEvaluation`, `getDoubleEvaluation`, `getIntegerEvaluation`, `getLongEvaluation`, `getObjectEvaluation`, `getStringEvaluation`, `suspend fun initialize(initialContext)`, `suspend fun onContextSet(oldContext, newContext)`, optional `track`, `observe(): Flow<OpenFeatureProviderEvents>`).

### Swift (iOS / Apple platforms)

- Docs: https://openfeature.dev/docs/reference/sdks/client/swift — Repo: https://github.com/open-feature/swift-sdk
- Supports iOS 15+, macOS 12+, watchOS 8+, tvOS 15+; Swift 5.5+; uses Combine and swift-log. SPM: `.package(url: "git@github.com:open-feature/swift-sdk.git", from: "0.6.0")` with product `.product(name: "OpenFeature", package: "swift-sdk")`; CocoaPods: `pod 'OpenFeature', '~> 0.5.0'`.

```swift
import OpenFeature

Task {
    let ctx = ImmutableContext(targetingKey: userId,
                               structure: ImmutableStructure(attributes: ["product": Value.string(productId)]))
    OpenFeatureAPI.shared.setEvaluationContext(evaluationContext: ctx)
    await OpenFeatureAPI.shared.setProviderAndWait(provider: CustomProvider())   // non-waiting variant also exists
    let client = OpenFeatureAPI.shared.getClient()
    let flagValue = client.getBooleanValue(key: "boolFlag", defaultValue: false)
}
```

- Hooks: `OpenFeatureAPI.shared.addHooks(hooks: ExampleHook())`, `client.addHooks(ExampleHook())`, `client.getValue(key:, defaultValue:, options: FlagEvaluationOptions(hooks: [ExampleHook()]))`. A `Hook` must define all of `before/after/error/finally` (generic over `HookValue`).
- Events: `let cancellable = OpenFeatureAPI.shared.observe().sink { event in switch event { case ProviderEvent.ready: ... default: ... } }`.
- Logging: swift-log `Logger`, set with `OpenFeatureAPI.shared.setLogger(logger)`, `client.setLogger(logger)`, or `FlagEvaluationOptions(logger:)`; disabled if none configured.
- Tracking: `client.track(key: "test")`, `client.track(key: "test-value", details: ImmutableTrackingEventDetails(value: 5))`; context is not accepted at track time (static-context rule).
- Not available: domains, shutdown. Multi-provider: `MultiProvider(providers: [primary, fallback], strategy: FirstMatchStrategy())` or `FirstSuccessfulStrategy()`.
- Custom provider: implement `FeatureProvider`; providers own their `status` and must emit lifecycle events themselves (`.ready`, `.error`, `.reconciling`, `.contextChanged`), most easily by delegating to `ProviderStatusTracker`. `initialize(initialContext:)` and `onContextSet(oldContext:newContext:)` return `Future<Void, Never>`.
- No in-memory provider appears in the docs.

### Dart (client, beta)

- Docs: https://openfeature.dev/docs/reference/sdks/client/dart — Repo: https://github.com/open-feature/dart-sdk (package `packages/openfeature_dart_client_sdk`); architecture and conformance matrix under `doc/` in that repo; progress tracked in https://github.com/open-feature/dart-sdk/issues/117.
- Pure Dart, no Flutter or `dart:io` dependency; Dart 3.12.2+. `pubspec.yaml`: `openfeature_dart_client_sdk: ^0.0.1-beta.1`. Static-context paradigm; beta, so the public contract may still change.

```dart
import 'package:openfeature_dart_client_sdk/openfeature_dart_client_sdk.dart';

final provider = InMemoryProvider({'new-checkout': true, 'welcome-message': 'Hello'});
await OpenFeatureAPI.instance.setProviderAndWait(provider);
await OpenFeatureAPI.instance.setEvaluationContextAndWait(EvaluationContext(targetingKey: 'user-123'));
final client = OpenFeatureAPI.instance.getClient('checkout');
final enabled = client.getBooleanValue('new-checkout', false);        // synchronous
await OpenFeatureAPI.instance.shutdown();
```

- Note the asymmetry with the Dart server SDK: here the singleton is `OpenFeatureAPI.instance`, evaluation is `getBooleanValue` and synchronous, and context changes are `setEvaluationContextAndWait`.
- Providers implement `FeatureProvider` with synchronous, I/O-free resolvers and opt into capabilities via `InitializableProvider`, `ContextReconciliationProvider`, `ShutdownProvider`, `ProviderEventSource`, `DomainScopedProvider`, `TrackingProvider`. Lifecycle waits are bounded (30 s default; `createIsolatedOpenFeatureAPI(lifecycleTimeout: ...)` for tests); a timed-out provider is quarantined and must be replaced with a new instance.
- Out of scope for this package: HTTP transport, OFREP provider, vendor providers, persistent storage, Flutter APIs.

## Client-side vs server-side paradigm differences

The concepts file explains the two paradigms; this is how they surface in the SDKs above.

| Aspect | Server SDKs (Java, Node.js, PHP, Ruby, Rust, C++, Dart server) | Client SDKs (Web, React, Angular, Kotlin, Swift, Dart client) |
|---|---|---|
| Where context lives | API, client, transaction and invocation levels, merged per evaluation | One global context (optionally per domain on Web), set on the API |
| Per-call context | Yes, e.g. `client.getBooleanValue(key, def, ctx)` | No context parameter on evaluation methods |
| Evaluation call | Often async (Node.js `await`, Rust `.await`, Dart server `Future`); Java/PHP/Ruby/C++ are synchronous calls that may hit the network in the provider | Synchronous, served from the provider's local cache |
| Changing context | Build a new context object per request | `OpenFeature.setContext(...)` (Web, async), `OpenFeatureAPI.setEvaluationContext(...)` (Kotlin/Swift), `setEvaluationContextAndWait` (Dart client); the provider's `onContextChange` / `onContextSet` reconciles its cache, often with a network round trip |
| Lifecycle events | `PROVIDER_READY`, `PROVIDER_ERROR`, `PROVIDER_STALE`, `PROVIDER_CONFIGURATION_CHANGED` | Same, plus `PROVIDER_RECONCILING` (emitted when the context is invalidated) and `PROVIDER_CONTEXT_CHANGED` (after reconciliation succeeds) |
| Readiness | `setProviderAndWait` or listen for READY; evaluating early returns defaults | Same, and additionally UI wrappers expose it: React suspense / `useWhenProviderReady`, Angular `initializing` and `reconciling` templates |
| Transaction context propagation | Java, Node.js, Ruby, Dart server (and Go/.NET/Python) | Not applicable |
| Tracking context | May be passed per `track` call (Ruby, Dart server) | Uses the stored context; Swift explicitly rejects context at track time |
| Multi-user safety | Designed for many users per process | One user per process; sharing a reconciling provider across domains is discouraged (Dart client requires one instance per domain) |

Practical consequences: on the web, never build a context object per evaluation and expect the provider to use it; set it once, await it, and let the framework wrappers re-render. On the server, avoid mutating global context per request; use invocation context or a transaction context propagator instead.

## The JavaScript package family

| Package | Runs on | Purpose |
|---|---|---|
| `@openfeature/core` | both | Shared types, hooks and event plumbing used by every JS SDK. A peer dependency pinned to an exact version by each SDK release; install it manually with yarn. Never import from it directly in apps |
| `@openfeature/server-sdk` | Node.js 18+ | Dynamic-context server SDK (`OpenFeature`, `TypedInMemoryProvider`, `MultiProvider`, `AsyncLocalStorageTransactionContextPropagator`) |
| `@openfeature/web-sdk` | browsers (ES2015) | Static-context client SDK; same surface minus transaction context, evaluation is synchronous |
| `@openfeature/nestjs-sdk` | Node.js 20+, NestJS 8+ | `OpenFeatureModule`, decorators; re-exports the server SDK |
| `@openfeature/react-sdk` | React 16.8+ | `OpenFeatureProvider`, hooks, `FeatureFlag`, `OpenFeatureTestProvider`; re-exports the web SDK |
| `@openfeature/angular-sdk` | Angular 16+ | `provideOpenFeature`, directives, `FeatureFlagService`; re-exports the web SDK |
| `@openfeature/flagd-provider` | Node.js | flagd provider used in the Node tutorial (contrib repo) |

Providers declare `runsOn: 'server' | 'client'` and the SDK validates it at registration, so a web provider cannot be registered in the server SDK by mistake. Library authors must declare the SDK they build on as a `peerDependency` to avoid duplicate singletons.

## When this file is silent

- Per-SDK documentation follows the pattern `https://openfeature.dev/docs/reference/sdks/<server|client>/<name>` where `<name>` is `java`, `javascript`, `javascript/nestjs`, `php`, `ruby`, `rust`, `cpp`, `dart` (server) or `web`, `web/react`, `web/angular`, `kotlin`, `swift`, `dart` (client). These pages are generated from each repo's README, so the README on `main` may be newer.
- Repositories follow `https://github.com/open-feature/<lang>-sdk` (`java-sdk`, `js-sdk` for Node/Web/React/Angular/NestJS, `php-sdk`, `ruby-sdk`, `rust-sdk`, `cpp-sdk`, `dart-sdk`, `kotlin-sdk`, `swift-sdk`) and community providers and hooks live in `https://github.com/open-feature/<lang>-sdk-contrib` (`java-sdk-contrib`, `js-sdk-contrib`, `php-sdk-contrib`, `ruby-sdk-contrib`, `rust-sdk-contrib`, `cpp-sdk-contrib`, `dart-server-sdk-contrib`). Kotlin and Swift have no contrib repo listed in the docs.
- Versions, spec levels and the feature matrix: https://openfeature.dev/docs/reference/sdks/sdk-compatibility (backed by `src/datasets/sdks/sdk-compatibility.json` in https://github.com/open-feature/openfeature.dev).
- Which providers exist for a given SDK: https://openfeature.dev/ecosystem filtered by type and technology; see the ecosystem reference file in this directory.
- Specification text for any behaviour described here: https://openfeature.dev/specification.
