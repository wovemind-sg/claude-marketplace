# flagd Providers — wiring an app to flagd (all languages)

Worked from flagd repo `main` @ `b13483f77df9006887e69cf6ce1f3bb320328dbb` (2026-09-18) plus the
`*-sdk-contrib` provider READMEs fetched 2026-09-21. Where a README and the spec disagree, the
per-language section says so; the README wins for that language.

## Contents

1. [Model: OpenFeature SDK + flagd provider](#1-model)
2. [Resolver modes and how to choose](#2-resolver-modes)
3. [Lifecycle, events, reconnection, caching](#3-lifecycle-events-reconnection-caching)
4. [Standard configuration options / env vars](#4-configuration-options-spec)
5. [Selectors, name resolution (envoy://), metadata](#5-selectors-name-resolution-metadata)
6. [Go](#6-go) · 7. [Java](#7-java) · 8. [Node.js (server)](#8-nodejs-server) · 9. [Web / browser](#9-web-browser-flagd-web)
10. [Python](#10-python) · 11. [.NET](#11-net) · 12. [PHP](#12-php) · 13. [Rust](#13-rust)
14. [Support tiers, server-side context enrichment](#14-support-tiers-and-server-side-context-enrichment)

## 1. Model

flagd is OpenFeature-native. An app never talks to flagd directly; it uses the **OpenFeature SDK**
for its language and plugs in the **flagd provider** (provider name is always `flagd`).

```
your code ──▶ OpenFeature client ──▶ flagd provider ──▶ flagd (gRPC :8013 / sync :8015 / OFREP :8016) or a local file
```

- **Provider**: one per process (or per named domain). `setProvider(p)` starts init; `setProviderAndWait`
  (or `SetProviderAsync`/`set_provider` + `PROVIDER_READY` handler) blocks until the stream is up.
- **Client**: `getClient([name])`. Evaluation API is uniform across SDKs:
  `getBooleanValue / getStringValue / getNumberValue (Int|Float|Double) / getObjectValue(key, default, ctx)`
  and `get*Details(...)` returning `{ value, variant, reason, errorCode, errorMessage, flagMetadata }`.
  Reasons you will see from flagd: `STATIC`, `DEFAULT`, `TARGETING_MATCH`, `DISABLED`, `CACHED`, `STALE`, `ERROR`.
  Errors never throw from `get*Value`; the default you pass is returned and `reason=ERROR`.
- **Evaluation context**: a map of attributes plus a `targetingKey` (user id, session id, …). flagd targeting
  rules read it via JsonLogic `{"var": "email"}`; the targeting key is exposed as `targetingKey`. Context can be
  set globally (`OpenFeature.setContext`), per client, per call, and per hook — merged in that order.
  In-process providers also inject `$flagd.flagKey`, `$flagd.timestamp` and sync-metadata properties.
- **Hooks**: `before / after / error / finally` stages at API, client, provider or invocation level (logging, OTel).
- **Events**: `PROVIDER_READY`, `PROVIDER_CONFIGURATION_CHANGED` (payload has `flagsChanged` keys),
  `PROVIDER_STALE`, `PROVIDER_ERROR` (and terminal `PROVIDER_FATAL` error code). Subscribe with
  `client.addHandler(ProviderEvents.ConfigurationChanged, handler)` (name varies by SDK).

Source: https://flagd.dev/providers/ · https://flagd.dev/reference/specifications/providers/ ·
https://openfeature.dev/docs/reference/concepts/provider

## 2. Resolver modes

| Mode | Where evaluation happens | Wire protocol | Default port | Pick when |
|---|---|---|---|---|
| `rpc` (default) | in flagd | gRPC `flagd.evaluation.v1.Service` unary calls + `EventStream` for change notifications | 8013 | simplest; sidecar/central flagd; results for `STATIC` flags cached client-side |
| `in-process` | in your process | gRPC `flagd.sync.v1.FlagSyncService.SyncFlags` stream pulls the whole flag set from flagd **or flagd-proxy** (or any sync-server) + `GetMetadata` | 8015 | lowest latency, no per-eval network hop, survives flagd outages with last-known rules; flag definitions (rules) are visible to the app |
| `file` (offline in-process) | in your process | none — polls a local flag-definition JSON/YAML file (mtime, ~5 s) | — | local dev, tests, air-gapped, ConfigMap-mounted flags; no sync-metadata enrichment |
| `rest` (Rust only) / OFREP | in flagd | HTTP OFREP `/ofrep/v1/evaluate/flags/{key}` | 8016 | gRPC unavailable; any generic OFREP provider also works against flagd |

Rules of thumb: browser/mobile → RPC only (rules never ship to the client; bulk-evaluate + cache, see §9).
Server with a flagd sidecar → `rpc` (cheap, cached). Latency-critical or many evaluations per request →
`in-process` against flagd or flagd-proxy on `:8015`. CI/unit tests → `file`. In-process resolvers take exactly
one source; precedence when several are configured: custom connector/sync provider > offline file > gRPC.

Source: https://flagd.dev/reference/specifications/providers/#overview-of-resolver-types · https://flagd.dev/providers/

## 3. Lifecycle, events, reconnection, caching

**Init**: open the stream for the mode (event stream for rpc, sync stream + `GetMetadata` for in-process).
Success within `deadlineMs` → SDK emits `PROVIDER_READY` (in-process stores the flag set). Failure → `PROVIDER_ERROR`,
then reconnect forever (except `fatalStatusCodes`, e.g. `UNAUTHENTICATED`, `PERMISSION_DENIED` → `PROVIDER_FATAL`).

**Connected**: rpc caches `reason=STATIC` results (flags without targeting rules) in an LRU (`cache=lru`,
`maxCacheSize=1000`); cached hits come back `reason=CACHED`. Flags with targeting are never cached. A
`configuration_change` event `{type: write|update|delete, source, flagKey}` evicts that key and emits
`PROVIDER_CONFIGURATION_CHANGED`. In-process replaces the stored rules and diffs added/removed/mutated
(default variant, targeting, metadata) keys into `flagsChanged`.

**Disconnected**: `PROVIDER_STALE` immediately; rpc serves from cache (`reason=STALE`), in-process from stored
rules. After `retryGracePeriod` seconds (spec 10; most impls 5) → `PROVIDER_ERROR`, rpc cache purged (events were
missed), in-process keeps serving stored rules. On reconnect → `PROVIDER_READY` + `PROVIDER_CONFIGURATION_CHANGED`.

**Retry layers**: (1) gRPC retry policy on every RPC — `UNAVAILABLE`/`UNKNOWN`, 4 attempts, 1s/2s/4s backoff
capped at `retryBackoffMaxMs`; (2) application-level stream re-establish with flat `retryBackoffMaxMs` delay
(avoids tight loops behind L7 proxies); (3) `streamDeadlineMs` (default 600000) closes and reopens the stream as
an application keepalive; `keepAliveTime` sets HTTP/2 pings (0 = off). `shutdown()` closes streams.

Source: https://flagd.dev/reference/specifications/providers/#flagd-provider-lifecycle ·
https://flagd.dev/reference/specifications/providers/#flag-evaluation-caching

## 4. Configuration options (spec)

Constructor options override env vars (Go is the exception: env is lowest unless `flagd.FromEnv()` is passed).
Not every implementation supports every row — see per-language tables.

| Option | Env var | Meaning | Type / values | Default | Resolvers |
|---|---|---|---|---|---|
| resolver | `FLAGD_RESOLVER` | mode | `rpc`, `in-process` (`file` in Java/.NET/Python/Rust) | `rpc` | all |
| host | `FLAGD_HOST` | remote host | string | `localhost` | rpc, in-process |
| port | `FLAGD_PORT` (`FLAGD_SYNC_PORT` wins for in-process in Go/Java/Python/.NET) | remote port | int | 8013 rpc / 8015 in-process | rpc, in-process |
| targetUri | `FLAGD_TARGET_URI` | replaces host/port; gRPC name resolution (`dns:`, `xds:`, `envoy://`) | string | null | rpc, in-process |
| tls | `FLAGD_TLS` | encrypt connection | bool | `false` | rpc, in-process |
| socketPath | `FLAGD_SOCKET_PATH` | unix socket instead of host/port | string | null | rpc, in-process |
| certPath | `FLAGD_SERVER_CERT_PATH` (docs sometimes say `FLAGD_CERT_PATH`) | PEM CA cert for TLS | string | null | rpc, in-process |
| deadlineMs | `FLAGD_DEADLINE_MS` | unary-call deadline and init timeout | int ms | 500 (.NET 300000) | all |
| streamDeadlineMs | `FLAGD_STREAM_DEADLINE_MS` | stream deadline / app-layer keepalive | int ms | 600000 | rpc, in-process |
| retryBackoffMs | `FLAGD_RETRY_BACKOFF_MS` | initial stream retry backoff | int ms | 1000 | rpc, in-process |
| retryBackoffMaxMs | `FLAGD_RETRY_BACKOFF_MAX_MS` | max stream retry backoff | int ms | 5000 spec (Java/.NET 12000, JS/Rust 120000) | rpc, in-process |
| retryGracePeriod | `FLAGD_RETRY_GRACE_PERIOD` | seconds STALE before ERROR | int s | 10 spec (impls 5) | all |
| keepAliveTime | `FLAGD_KEEP_ALIVE_TIME_MS` | HTTP/2 keepalive ping interval | long ms | 0 (off) | rpc, in-process |
| selector | `FLAGD_SOURCE_SELECTOR` | filter flags: `flagSetId=x`, `source=y`, bare `y` = source | string | null | rpc, in-process |
| cache | `FLAGD_CACHE` | static-flag cache | `lru`, `disabled` (`mem` in Go/Rust) | `lru` | rpc |
| maxCacheSize | `FLAGD_MAX_CACHE_SIZE` | cache entries | int | 1000 (.NET 10) | rpc |
| providerId | `FLAGD_PROVIDER_ID` (`FLAGD_SOURCE_PROVIDER_ID` older/Go) | identifies this client to the sync server | string | null | in-process |
| offlineFlagSourcePath | `FLAGD_OFFLINE_FLAG_SOURCE_PATH` | flag file; overrides host/port/targetUri | string | null | file |
| offlinePollIntervalMs | `FLAGD_OFFLINE_POLL_MS` | file poll interval | int ms | 5000 | file |
| contextEnricher | — | fn(sync-metadata) → context to merge into every eval | function | identity | in-process |
| fatalStatusCodes | `FLAGD_FATAL_STATUS_CODES` | gRPC codes that abort init → PROVIDER_FATAL | list | `[]` | rpc, in-process |
| defaultAuthority | `FLAGD_DEFAULT_AUTHORITY` | override `:authority` header (proxies) | string | null | rpc, in-process (Java, JS) |
| maxEventStreamRetries | `FLAGD_MAX_EVENT_STREAM_RETRIES` | legacy: event-stream connect attempts | int | 5 (Go), 3 (.NET) | rpc (Go, .NET) |

Not in the spec table but seen in the wild: `FLAGD_SYNC_METADATA_DISABLED` (skip `GetMetadata` on init; Java/Go
in-process — verify against your provider version), `FLAGD_CACHE_TTL` (Rust), `FLAGD_HASH_FILE_CHANGE` (.NET),
`FLAGD_COMPILE_TARGETING`, `FLAGD_REINITIALIZE_ON_ERROR` (Java, experimental).

Source: https://flagd.dev/reference/specifications/providers/#configuration-options

## 5. Selectors, name resolution, metadata

**Selector syntax**: `flagSetId=<id>` (preferred; matches the flag set's top-level `metadata.flagSetId`),
`source=<uri-or-name>` (legacy, matches a flagd `--uri` source), bare `<name>` = source. Providers send it as the
`flagd-selector` gRPC metadata header (and, for compatibility with flagd < 0.11, also in the request body).
Precedence: request header `Flagd-Selector` > provider `selector` option. flagd reflects the effective selector
back in response `metadata` (e.g. `flagSetId`), useful for debugging empty results.

**Custom name resolution** (Go, Java, Rust; JS via `defaultAuthority`): `targetUri` accepts any gRPC core
resolver (`dns:///flagd.svc:8015`, `xds:///…`) plus a custom `envoy://<proxyHost>:<proxyPort>/<authority>`
scheme — connects to the proxy and sets `:authority` to the path, e.g. `envoy://localhost:9211/flagd-sync.service`.

**Flag metadata**: `get*Details().flagMetadata` is the flag-set metadata merged with the flag's own metadata
(flag wins); returned best-effort even for disabled/missing flags. Go additionally reports `scope` (selector) and
`providerID`.

Source: https://flagd.dev/reference/specifications/providers/#selector-configuration ·
https://flagd.dev/reference/specifications/providers/#custom-name-resolution

## 6. Go

Package `github.com/open-feature/go-sdk-contrib/providers/flagd` (module path; import as `flagd`), SDK
`github.com/open-feature/go-sdk/openfeature`. Modes: rpc, in-process, file.

```sh
go get github.com/open-feature/go-sdk-contrib/providers/flagd github.com/open-feature/go-sdk
```

```go
package main

import (
	"context"
	"log"

	flagd "github.com/open-feature/go-sdk-contrib/providers/flagd/pkg"
	"github.com/open-feature/go-sdk/openfeature"
)

func main() {
	provider, err := flagd.NewProvider( // rpc → localhost:8013
		flagd.WithHost("localhost"), flagd.WithPort(8013),
	)
	if err != nil {
		log.Fatal(err)
	}
	if err := openfeature.SetProviderAndWait(provider); err != nil { // blocks until PROVIDER_READY
		log.Fatal(err)
	}
	defer openfeature.Shutdown()

	client := openfeature.NewClient("my-app")
	evalCtx := openfeature.NewEvaluationContext("user-123", map[string]interface{}{
		"email": "a@example.com", "plan": "pro",
	})
	on, _ := client.BooleanValue(context.Background(), "new-checkout", false, evalCtx)
	details, _ := client.BooleanValueDetails(context.Background(), "new-checkout", false, evalCtx)
	log.Println(on, details.Variant, details.Reason)
}
```

In-process (sync from flagd/flagd-proxy `:8015`) and file mode:

```go
provider, _ := flagd.NewProvider(flagd.WithInProcessResolver(),
	flagd.WithHost("flagd-proxy"), flagd.WithPort(8015), flagd.WithSelector("flagSetId=my-app"))

provider, _ := flagd.NewProvider(flagd.WithFileResolver(), flagd.WithOfflineFilePath("./flags.json"))

// envoy / xds name resolution, or custom dial options for an authenticated sync server
provider, _ := flagd.NewProvider(flagd.WithInProcessResolver(), flagd.WithTargetUri("envoy://localhost:9211/flagd-sync.service"))
provider, _ := flagd.NewProvider(flagd.WithInProcessResolver(), flagd.WithHost("sync.example.com"), flagd.WithPort(443),
	flagd.WithGrpcDialOptionsOverride([]grpc.DialOption{grpc.WithTransportCredentials(creds), grpc.WithAuthority("…")}))

// bring your own flag source: implement flagd core sync.ISync
provider, _ := flagd.NewProvider(flagd.WithInProcessResolver(), flagd.WithCustomSyncProviderAndUri(mySync, "myscheme://x"))
```

| Option fn | Env | Default | Resolver |
|---|---|---|---|
| `WithHost` | `FLAGD_HOST` | localhost | rpc, in-process |
| `WithPort` | `FLAGD_PORT` (rpc); `FLAGD_SYNC_PORT` > `FLAGD_PORT` (in-process) | 8013 / 8015 | rpc, in-process |
| `WithTargetUri` | `FLAGD_TARGET_URI` | "" | in-process |
| `WithTLS(bool)`, `WithCertificatePath` | `FLAGD_TLS`, `FLAGD_SERVER_CERT_PATH` | false, "" | rpc, in-process |
| `WithSocketPath` | `FLAGD_SOCKET_PATH` | "" | rpc, in-process |
| `WithLRUCache(n)` / `WithBasicInMemoryCache()` / `WithoutCache()` | `FLAGD_CACHE`=lru\|mem\|disabled, `FLAGD_MAX_CACHE_SIZE` | lru, 1000 | rpc |
| `WithEventStreamConnectionMaxAttempts` | `FLAGD_MAX_EVENT_STREAM_RETRIES` | 5 | rpc |
| `WithInProcessResolver()`, `WithFileResolver()`, `WithRPCResolver()` | `FLAGD_RESOLVER` | rpc | — |
| `WithOfflineFilePath` | `FLAGD_OFFLINE_FLAG_SOURCE_PATH` | "" | file |
| `WithProviderID` | `FLAGD_SOURCE_PROVIDER_ID` | "" | in-process |
| `WithSelector` | `FLAGD_SOURCE_SELECTOR` | "" | in-process |
| `WithCustomSyncProvider[AndUri]`, `WithGrpcDialOptionsOverride`, `WithLogger(logr.Logger)`, `FromEnv()` | — | — | — |

Quirks: env vars are read at **lowest** priority; option order matters (later wins) — put `flagd.FromEnv()` last to
let env override code. Logging via `logr` (warn=V(0), info=V(1), debug=V(2)); default is stdlib `log` errors only.
File-mode change detection is best-effort (fs events differ per OS).

Source: https://flagd.dev/providers/go/ · https://github.com/open-feature/go-sdk-contrib/tree/main/providers/flagd

## 7. Java

Artifact `dev.openfeature.contrib.providers:flagd` (README version **0.14.2**), SDK `dev.openfeature:sdk`.
Modes: rpc, in-process, file. Class `dev.openfeature.contrib.providers.flagd.FlagdProvider`, options via
`FlagdOptions.builder()`, resolver enum `Config.Resolver.{RPC, IN_PROCESS, FILE}`.

```xml
<dependency>
  <groupId>dev.openfeature.contrib.providers</groupId>
  <artifactId>flagd</artifactId>
  <version>0.14.2</version>
</dependency>
```

```java
import dev.openfeature.contrib.providers.flagd.FlagdOptions;
import dev.openfeature.contrib.providers.flagd.FlagdProvider;
import dev.openfeature.sdk.*;
import java.util.Map;

public class App {
  public static void main(String[] args) {
    FlagdProvider provider = new FlagdProvider(
        FlagdOptions.builder().host("localhost").port(8013).build()); // rpc default
    OpenFeatureAPI api = OpenFeatureAPI.getInstance();
    api.setProviderAndWait(provider); // blocks for PROVIDER_READY (throws on init failure)

    Client client = api.getClient("my-app");
    EvaluationContext ctx = new ImmutableContext("user-123",
        Map.of("email", new Value("a@example.com"), "plan", new Value("pro")));
    boolean on = client.getBooleanValue("new-checkout", false, ctx);
    FlagEvaluationDetails<Boolean> d = client.getBooleanDetails("new-checkout", false, ctx);
    System.out.println(on + " " + d.getVariant() + " " + d.getReason());
    client.onProviderConfigurationChanged(e -> System.out.println("changed: " + e.getFlagsChanged()));
    api.shutdown();
  }
}
```

```java
// in-process from flagd / flagd-proxy :8015
new FlagdProvider(FlagdOptions.builder().resolverType(Config.Resolver.IN_PROCESS)
    .host("flagd-proxy").port(8015).selector("flagSetId=my-app").build());
// file / offline
new FlagdProvider(FlagdOptions.builder().resolverType(Config.Resolver.FILE)
    .offlineFlagSourcePath("/etc/flags/flags.json").build());
// TLS, proxy authority, custom headers/credentials for a hosted sync API
new FlagdProvider(FlagdOptions.builder().host("sync.example.com").port(443).tls(true).certPath("etc/cert/ca.crt")
    .defaultAuthority("authority-host.sync.example.com").clientInterceptors(List.of(headerInterceptor)).build());
// envoy name resolution
FlagdOptions.builder().resolverType(Config.Resolver.IN_PROCESS).targetUri("envoy://localhost:9211/flag-source.service").build();
// custom flag source: implement resolver.process.storage.connector.Connector (example: tools/flagd-http-connector)
FlagdOptions.builder().resolverType(Config.Resolver.IN_PROCESS).customConnector(myConnector).build();
// OpenTelemetry traces for RPC calls
FlagdOptions.builder().openTelemetry(otel).build();   // or .withGlobalTelemetry(true)
```

| Builder option | Env | Default | Resolver |
|---|---|---|---|
| `resolverType` | `FLAGD_RESOLVER` | rpc | — |
| `host` / `port` | `FLAGD_HOST` / `FLAGD_PORT` (`FLAGD_SYNC_PORT` first for in-process) | localhost / 8013, 8015 | rpc, in-process |
| `targetUri`, `defaultAuthority` | `FLAGD_TARGET_URI`, `FLAGD_DEFAULT_AUTHORITY` | null | rpc, in-process |
| `tls`, `certPath`, `socketPath` | `FLAGD_TLS`, `FLAGD_SERVER_CERT_PATH`, `FLAGD_SOCKET_PATH` | false, null, null | rpc, in-process |
| `deadline`, `streamDeadlineMs`, `keepAliveTime` | `FLAGD_DEADLINE_MS`, `FLAGD_STREAM_DEADLINE_MS`, `FLAGD_KEEP_ALIVE_TIME_MS` | 500, 600000, 0 | rpc, in-process (+file for deadline) |
| `selector`, `providerId` | `FLAGD_SOURCE_SELECTOR`, `FLAGD_PROVIDER_ID` (`FLAGD_SOURCE_PROVIDER_ID` deprecated) | null | in-process |
| `cacheType`, `maxCacheSize` | `FLAGD_CACHE` (lru\|disabled), `FLAGD_MAX_CACHE_SIZE` | lru, 1000 | rpc |
| `retryBackoffMs`, `retryBackoffMaxMs`, `retryGracePeriod` | `FLAGD_RETRY_BACKOFF_MS`, `FLAGD_RETRY_BACKOFF_MAX_MS`, `FLAGD_RETRY_GRACE_PERIOD` | 1000, 12000, 5 | rpc, in-process |
| `fatalStatusCodes` | `FLAGD_FATAL_STATUS_CODES` | [] | rpc, in-process |
| `offlineFlagSourcePath`, `offlinePollIntervalMs` | `FLAGD_OFFLINE_FLAG_SOURCE_PATH`, `FLAGD_OFFLINE_POLL_MS` | null, 5000 | file |
| `contextEnricher(Function<Structure,EvaluationContext>)` | — | identity (whole sync-metadata) | in-process |
| `compileTargeting` (experimental) | `FLAGD_COMPILE_TARGETING` = enabled\|disabled\|auto | auto | in-process |
| `reinitializeOnError` (experimental) | `FLAGD_REINITIALIZE_ON_ERROR` | false | rpc, in-process |
| `customConnector`, `clientInterceptors`, `openTelemetry`, `withGlobalTelemetry` | — | — | — |

Quirks: `compileTargeting=auto` JIT-compiles JsonLogic to bytecode when `jdk.compiler` is present — absent in
JRE-only/distroless images (falls back silently; set `disabled` for predictable first-eval latency). Unix sockets
only on linux-x86_64 (netty epoll). `getSyncMetadata()` exposes the last `GetMetadata` payload (in-process only);
`deadline` in file mode bounds the file read. Netty cert-validation advisory noted in README.

Source: https://flagd.dev/providers/java/ · https://github.com/open-feature/java-sdk-contrib/tree/main/providers/flagd

## 8. Node.js (server)

Package `@openfeature/flagd-provider` (peers: `@openfeature/server-sdk`, `@grpc/grpc-js`, `@openfeature/flagd-core`
— npm installs peers automatically, yarn does not). Class `FlagdProvider`. Modes: rpc, in-process, file (via
`offlineFlagSourcePath`). The in-process engine is the shared `@openfeature/flagd-core` package.

```sh
npm install @openfeature/server-sdk @openfeature/flagd-provider
# yarn: yarn add @openfeature/server-sdk @grpc/grpc-js @openfeature/flagd-core @openfeature/flagd-provider
```

```ts
import { OpenFeature, ProviderEvents } from '@openfeature/server-sdk';
import { FlagdProvider } from '@openfeature/flagd-provider';

await OpenFeature.setProviderAndWait(new FlagdProvider({ host: 'localhost', port: 8013 })); // rpc

const client = OpenFeature.getClient('my-app');
const ctx = { targetingKey: 'user-123', email: 'a@example.com', plan: 'pro' };
const on = await client.getBooleanValue('new-checkout', false, ctx);
const details = await client.getBooleanDetails('new-checkout', false, ctx); // { value, variant, reason, flagMetadata }
client.addHandler(ProviderEvents.ConfigurationChanged, (e) => console.log('changed', e?.flagsChanged));
process.on('SIGTERM', () => OpenFeature.close());
```

```ts
new FlagdProvider({ resolverType: 'in-process', host: 'flagd-proxy', port: 8015, selector: 'flagSetId=my-app' });
new FlagdProvider({ resolverType: 'in-process', offlineFlagSourcePath: './flags.json' }); // file mode (fs.watchFile, 5 s)
new FlagdProvider({ socketPath: '/tmp/flagd.socks' });                                    // unix socket, rpc
new FlagdProvider({ resolverType: 'in-process', defaultAuthority: 'b-target-api.service', keepAliveTime: 30000 });
new FlagdProvider({ fatalStatusCodes: ['UNAUTHENTICATED', 'PERMISSION_DENIED'], retryGracePeriod: 5 });
```

| Option | Env | Default | Resolver |
|---|---|---|---|
| `host`, `port` | `FLAGD_HOST`, `FLAGD_PORT` | localhost, 8013 rpc / 8015 in-process | rpc, in-process |
| `tls`, `certPath`, `socketPath` | `FLAGD_TLS`, `FLAGD_SERVER_CERT_PATH`, `FLAGD_SOCKET_PATH` | false, -, - | rpc, in-process |
| `resolverType` | `FLAGD_RESOLVER` = rpc\|in-process | rpc | — |
| `offlineFlagSourcePath` | `FLAGD_OFFLINE_FLAG_SOURCE_PATH` | - | in-process (file) |
| `selector` | `FLAGD_SOURCE_SELECTOR` | - | rpc, in-process |
| `cache`, `maxCacheSize` | `FLAGD_CACHE` (lru\|disabled), `FLAGD_MAX_CACHE_SIZE` | lru, 1000 | rpc |
| `defaultAuthority`, `keepAliveTime` | `FLAGD_DEFAULT_AUTHORITY`, `FLAGD_KEEP_ALIVE_TIME_MS` | -, 0 | rpc, in-process |
| `retryBackoffMs`, `retryBackoffMaxMs` | `FLAGD_RETRY_BACKOFF_MS`, `FLAGD_RETRY_BACKOFF_MAX_MS` | 1000, 120000 | in-process |
| `retryGracePeriod`, `fatalStatusCodes` | `FLAGD_RETRY_GRACE_PERIOD`, `FLAGD_FATAL_STATUS_CODES` | 5, - | all |

Quirks: no `targetUri` (use `defaultAuthority` for envoy-style routing); no `file` resolverType string — file mode is
`in-process` + `offlineFlagSourcePath`; `deadlineMs`/`streamDeadlineMs` not exposed in the README table.

Source: https://flagd.dev/providers/nodejs/ · https://github.com/open-feature/js-sdk-contrib/tree/main/libs/providers/flagd

## 9. Web / browser (`flagd-web`)

Package `@openfeature/flagd-web-provider` (experimental, breaking changes allowed) with `@openfeature/web-sdk`.
Class `FlagdWebProvider`. **RPC only**, speaks flagd's `flagd.evaluation.v1` service over the **Connect protocol**
(HTTP/1.1 or h2, JSON/proto — `@connectrpc/connect-web`), so it hits flagd's `:8013` port through your
TLS-terminating ingress; flag rules never reach the browser. Uses the OpenFeature **static-context paradigm**:
context is set once (`OpenFeature.setContext`), the provider does a **bulk `ResolveAll`** for every flag, caches the
results in memory, and `client.get*Value` is **synchronous** from that cache. Re-evaluation (new bulk call) happens
on init, on `setContext`, and when a `configuration_change` event arrives on the event stream.

```sh
npm install @openfeature/web-sdk @openfeature/flagd-web-provider
```

```ts
import { OpenFeature, ProviderEvents } from '@openfeature/web-sdk';
import { FlagdWebProvider } from '@openfeature/flagd-web-provider';

await OpenFeature.setContext({ targetingKey: 'user-123', plan: 'pro' }); // set BEFORE provider so first bulk eval is targeted
await OpenFeature.setProviderAndWait(new FlagdWebProvider({
  host: 'flags.myapp.com', port: 443, tls: true, pathPrefix: '/api/flagd', maxRetries: 10, maxDelay: 30000,
}));

const client = OpenFeature.getClient();
const on = client.getBooleanValue('new-checkout', false);          // sync, from cache
client.addHandler(ProviderEvents.ConfigurationChanged, () => rerender());
client.addHandler(ProviderEvents.Ready, () => rerender());
await OpenFeature.setContext({ targetingKey: 'user-123', plan: 'enterprise' }); // triggers re-evaluation (emits ContextChanged)
```

| Option | Type | Default | Meaning |
|---|---|---|---|
| `host` | string | — (required) | flagd host |
| `port` | number | 443 | flagd port (local dev: 8013) |
| `tls` | boolean | true | https vs http (local dev: `false`) |
| `pathPrefix` | string | "" | path where flagd gRPC/Connect service is mounted behind a proxy, e.g. `/api/flagd` |
| `maxRetries` | number | 0 = unlimited | reconnect attempts (negative = none) |
| `maxDelay` | number ms | 60000 | max exponential back-off between reconnects |

Quirks: no env-var config (browser). No `selector`/cache options — bulk evaluation *is* the cache, invalidated by
change events. flagd must allow CORS from your origin (`flagd start --cors-origin https://app.example.com`).
Alternative for browsers: the generic OFREP web provider (`@openfeature/ofrep-web-provider`) against flagd `:8016`
`/ofrep/v1/evaluate/flags` — same bulk semantics, no streaming.

Source: https://flagd.dev/providers/web/ · https://github.com/open-feature/js-sdk-contrib/tree/main/libs/providers/flagd-web ·
https://flagd.dev/reference/specifications/providers/#client-side-providers

## 10. Python

Package `openfeature-provider-flagd` (SDK `openfeature-sdk`). Class `openfeature.contrib.provider.flagd.FlagdProvider`,
enum `openfeature.contrib.provider.flagd.config.ResolverType.{RPC, IN_PROCESS, FILE}`. Modes: rpc, in-process, file.

```sh
pip install openfeature-sdk openfeature-provider-flagd
```

```python
from openfeature import api
from openfeature.evaluation_context import EvaluationContext
from openfeature.event import ProviderEvent
from openfeature.contrib.provider.flagd import FlagdProvider

api.set_provider(FlagdProvider(host="localhost", port=8013))  # rpc default; set_provider blocks on init
client = api.get_client("my-app")
ctx = EvaluationContext(targeting_key="user-123", attributes={"email": "a@example.com", "plan": "pro"})
on = client.get_boolean_value("new-checkout", False, ctx)
details = client.get_boolean_details("new-checkout", False, ctx)  # .value .variant .reason .flag_metadata
client.add_handler(ProviderEvent.PROVIDER_CONFIGURATION_CHANGED, lambda e: print("changed", e.flags_changed))
api.shutdown()
```

```python
from openfeature.contrib.provider.flagd.config import ResolverType
api.set_provider(FlagdProvider(resolver_type=ResolverType.IN_PROCESS, host="flagd-proxy", port=8015,
                               selector="flagSetId=my-app"))
api.set_provider(FlagdProvider(resolver_type=ResolverType.FILE, offline_flag_source_path="./flags.json"))
api.set_provider(FlagdProvider(tls=True, cert_path="etc/cert/ca.crt"))
```

| Kwarg | Env | Default | Resolver |
|---|---|---|---|
| `resolver_type` | `FLAGD_RESOLVER` = rpc\|in-process (+`ResolverType.FILE` in code) | rpc | — |
| `host`, `port` | `FLAGD_HOST`; `FLAGD_SYNC_PORT` (in-process) / `FLAGD_PORT` (rpc, fallback) | localhost; 8013 / 8015 | rpc, in-process |
| `tls`, `cert_path` | `FLAGD_TLS`, `FLAGD_SERVER_CERT_PATH` | false, None | rpc, in-process |
| `deadline`, `stream_deadline_ms`, `keep_alive_time` | `FLAGD_DEADLINE_MS`, `FLAGD_STREAM_DEADLINE_MS`, `FLAGD_KEEP_ALIVE_TIME_MS` | 500, 600000, 0 | rpc, in-process |
| `selector` | `FLAGD_SOURCE_SELECTOR` | None | in-process only |
| `cache_type`, `max_cache_size` | `FLAGD_CACHE` (lru\|disabled), `FLAGD_MAX_CACHE_SIZE` | lru, 1000 | rpc |
| `retry_backoff_ms` | `FLAGD_RETRY_BACKOFF_MS` | 1000 | rpc |
| `offline_flag_source_path` | `FLAGD_OFFLINE_FLAG_SOURCE_PATH` | None | file |

Quirks: **not implemented** per README: `target_uri`, `socket_path`, `context_enricher`, configurable offline poll
(fixed 5 s); selector is in-process only; README prose says in-process connects to `localhost:8013` but the table
(8015) is correct; the sync-metadata accessor is commented out in the README (treat as unavailable).

Source: https://flagd.dev/providers/python/ · https://github.com/open-feature/python-sdk-contrib/tree/main/providers/openfeature-provider-flagd

## 11. .NET

NuGet `OpenFeature.Providers.Flagd` (requires `OpenFeature` SDK >= 2.0.0, < 3.0.0; the old
`OpenFeature.Contrib.Providers.Flagd` path/package is gone). Namespace `OpenFeature.Providers.Flagd`, class
`FlagdProvider`, config via `FlagdConfigBuilder`, `ResolverType.{RPC, IN_PROCESS, FILE}`. DI helpers in
`OpenFeature.DependencyInjection.Providers.Flagd` (needs `OpenFeature.Hosting`). Modes: rpc, in-process, file.

```sh
dotnet add package OpenFeature
dotnet add package OpenFeature.Providers.Flagd
dotnet add package OpenFeature.Hosting          # only for AddOpenFeature()/AddFlagdProvider() DI
```

```csharp
using OpenFeature;
using OpenFeature.Model;
using OpenFeature.Providers.Flagd;

var provider = new FlagdProvider(new Uri("http://localhost:8013")); // rpc; new FlagdProvider() reads env vars
await Api.Instance.SetProviderAsync(provider);                        // awaits PROVIDER_READY

var client = Api.Instance.GetClient("my-app");
var ctx = EvaluationContext.Builder().SetTargetingKey("user-123")
    .Set("email", "a@example.com").Set("plan", "pro").Build();
bool on = await client.GetBooleanValueAsync("new-checkout", false, ctx);
var details = await client.GetBooleanDetailsAsync("new-checkout", false, ctx); // .Value .Variant .Reason .FlagMetadata
client.AddHandler(ProviderEventTypes.ProviderConfigurationChanged, e => Console.WriteLine("changed"));
await Api.Instance.ShutdownAsync();
```

```csharp
// in-process from flagd / flagd-proxy
var cfg = new FlagdConfigBuilder().WithHost("flagd-proxy").WithPort("8015")
    .WithResolverType(ResolverType.IN_PROCESS)
    .WithSourceSelector("core.openfeature.dev/flags/sample-flags")   // e.g. a FeatureFlag CR watched by flagd-proxy
    .WithLogger(loggerFactory.CreateLogger<Program>())               // schema-validation warnings need a logger
    .Build();
await Api.Instance.SetProviderAsync(new FlagdProvider(cfg));

// file / offline (hash detection for NFS/overlay mounts with unreliable mtimes)
var fileCfg = new FlagdConfigBuilder().WithResolverType(ResolverType.FILE)
    .WithOfflineFlagSourcePath("/etc/flags/my-flags.json")
    .WithUseHashFileChangeDetection(true).WithOfflinePollIntervalMs(30000).WithDeadlineMs(60000).Build();

// unix socket rpc
new FlagdProvider(new Uri("unix://socket.tmp"));

// ASP.NET DI
builder.Services.AddOpenFeature(c => c.AddHostedFeatureLifecycle()
    .AddFlagdProvider(o => { o.Host = "flagd"; o.Port = 8013; }));   // options type FlagdProviderOptions
```

| Builder / option | Env | Default | Notes |
|---|---|---|---|
| `WithHost`, `WithPort(string)` | `FLAGD_HOST`; `FLAGD_SYNC_PORT` (in-process, priority) / `FLAGD_PORT` | localhost; 8013 / 8015 | |
| TLS, cert | `FLAGD_TLS`, `FLAGD_SERVER_CERT_PATH` | false | net462–net48 **must** use TLS + cert |
| unix socket | `FLAGD_SOCKET_PATH` | | if set, host/port/tls/cert are ignored |
| cache | `FLAGD_CACHE`=lru, `FLAGD_MAX_CACHE_SIZE` | -, **10** | rpc only; tiny default, raise it |
| `WithResolverType` | `FLAGD_RESOLVER` = rpc\|in-process\|file (`IN_PROCESS` accepted) | rpc | |
| `WithSourceSelector` | `FLAGD_SOURCE_SELECTOR` | | in-process |
| `WithOfflineFlagSourcePath`, `WithOfflinePollIntervalMs`, `WithUseHashFileChangeDetection` | `FLAGD_OFFLINE_FLAG_SOURCE_PATH`, `FLAGD_OFFLINE_POLL_MS`, `FLAGD_HASH_FILE_CHANGE` | -, 5000, false | file |
| `WithDeadlineMs` | `FLAGD_DEADLINE_MS` | **300000** | init timeout (file: wait for file to appear) |
| `WithRetryBackoffMs`, `WithRetryBackoffMaxMs` | `FLAGD_RETRY_BACKOFF_MS`, `FLAGD_RETRY_BACKOFF_MAX_MS` | 1000, 12000 | exponential, doubles |
| max event-stream retries | `FLAGD_MAX_EVENT_STREAM_RETRIES` | 3 | rpc |
| `WithLogger(ILogger)` | — | none | Microsoft.Extensions.Logging |

Quirks: in-process validates flag sets against `https://flagd.dev/schema/v0/flags.json` / `targeting.json` and logs
warnings (needs a logger). `WithPort` takes a **string**. Env-only construction: `new FlagdProvider()`.

Source: https://flagd.dev/providers/dotnet/ · https://github.com/open-feature/dotnet-sdk-contrib/tree/main/src/OpenFeature.Providers.Flagd

## 12. PHP

Package `open-feature/flagd-provider` (SDK `open-feature/sdk`), PHP >= 8.0. **RPC over HTTP only** (no in-process,
no file): calls flagd's `flagd.evaluation.v2.Service` via its HTTP/gRPC-web endpoints on `:8013` using PSR-18/17
implementations you supply. **Requires flagd >= v0.16.0**. No env-var config, no event stream, no caching.

```sh
composer require open-feature/sdk open-feature/flagd-provider
composer require guzzlehttp/guzzle guzzlehttp/psr7   # any PSR-18 client + PSR-17 factories
```

```php
<?php
use OpenFeature\OpenFeatureAPI;
use OpenFeature\implementation\flags\{EvaluationContext, Attributes};
use OpenFeature\Providers\Flagd\FlagdProvider;
use GuzzleHttp\Client;
use GuzzleHttp\Psr7\HttpFactory;

$factory = new HttpFactory();
OpenFeatureAPI::setProvider(new FlagdProvider([
    'protocol' => 'http',        // only "http" is supported
    'host'     => 'localhost',
    'port'     => 8013,
    'secure'   => false,         // true → https
    'httpConfig' => ['client' => new Client(), 'requestFactory' => $factory, 'streamFactory' => $factory],
]));

$client = OpenFeatureAPI::getInstance()->getClient('my-app');
$ctx = new EvaluationContext('user-123', new Attributes(['email' => 'a@example.com', 'plan' => 'pro']));
$on = $client->getBooleanValue('new-checkout', false, $ctx);
$details = $client->getBooleanDetails('new-checkout', false, $ctx); // getValue() getVariant() getReason()
```

| Option | Default | Notes |
|---|---|---|
| `protocol` | `http` | only value |
| `host` / `port` | `localhost` / `8013` | flagd evaluation port (HTTP side of the same listener) |
| `secure` | `false` | https when true |
| `httpConfig` | — | array or `HttpConfig`: `client` (PSR-18 `ClientInterface`), `requestFactory`, `streamFactory` (PSR-17) |

Quirks: each evaluation is a synchronous HTTP round-trip — keep flagd as a sidecar/localhost. No `selector`
option; pass `Flagd-Selector` as a header via a PSR-18 middleware if needed.

Source: https://flagd.dev/providers/php/ · https://github.com/open-feature/php-sdk-contrib/tree/main/providers/Flagd

## 13. Rust

Crate `open-feature-flagd` (README version **0.0.8**), SDK crate `open-feature`. Types
`open_feature_flagd::{FlagdProvider, FlagdOptions, ResolverType::{Rpc, Rest, InProcess, File}, CacheSettings}`.
Async (tokio). Cargo features `rpc`, `rest`, `in-process` (all on by default; `in-process` includes File).

```sh
cargo add open-feature open-feature-flagd
# slim: open-feature-flagd = { version = "0.0.8", default-features = false, features = ["rpc"] }
```

```rust
use open_feature::{EvaluationContext, OpenFeature};
use open_feature_flagd::{FlagdOptions, FlagdProvider, ResolverType};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let provider = FlagdProvider::new(FlagdOptions {
        host: "localhost".into(), port: 8013, resolver_type: ResolverType::Rpc, ..Default::default()
    }).await?;                                            // awaits initial connection

    let mut api = OpenFeature::singleton_mut().await;
    api.set_provider(provider).await;
    drop(api);
    let client = OpenFeature::singleton().await.create_client();

    let ctx = EvaluationContext::default().with_targeting_key("user-123")
        .with_custom_field("email", "a@example.com").with_custom_field("plan", "pro");
    let on = client.get_bool_value("new-checkout", Some(&ctx), None).await.unwrap_or(false);
    let details = client.get_bool_details("new-checkout", Some(&ctx), None).await?; // .value .variant .reason
    println!("{on} {:?}", details.reason);
    Ok(())
}
```

```rust
// in-process (sync stream from flagd / flagd-proxy :8015)
FlagdOptions { host: "flagd-proxy".into(), port: 8015, resolver_type: ResolverType::InProcess,
    selector: Some("flagSetId=my-app".into()), cache_settings: Some(CacheSettings::default()), ..Default::default() }
// file / offline
FlagdOptions { resolver_type: ResolverType::File, source_configuration: Some("./flags.json".into()), ..Default::default() }
// OFREP over HTTP (no gRPC deps with features = ["rest"])
FlagdOptions { host: "localhost".into(), port: 8016, resolver_type: ResolverType::Rest, ..Default::default() }
// envoy name resolution
FlagdOptions { target_uri: Some("envoy://localhost:9211/flagd-sync.service".into()), resolver_type: ResolverType::InProcess, ..Default::default() }
```

| Field | Env | Default | Resolver |
|---|---|---|---|
| `host`, `port` | `FLAGD_HOST`, `FLAGD_PORT` | localhost; 8013 rpc / 8016 rest (set 8015 yourself for in-process) | all |
| `target_uri` | `FLAGD_TARGET_URI` | "" | rpc, in-process |
| `tls`, `certificate_path` | `FLAGD_TLS`, `FLAGD_SERVER_CERT_PATH` | false, "" | rpc, in-process |
| `socket_path` | `FLAGD_SOCKET_PATH` | "" | rpc |
| `cache_settings` (type lru\|mem\|disabled, ttl, max size) | `FLAGD_CACHE`, `FLAGD_CACHE_TTL`, `FLAGD_MAX_CACHE_SIZE` | in-process: disabled, else lru; 60 s; 1000 | rpc, in-process, file |
| `source_configuration` | `FLAGD_OFFLINE_FLAG_SOURCE_PATH` | "" | file |
| `retry_backoff_ms`, `retry_backoff_max_ms`, `retry_grace_period` | `FLAGD_RETRY_BACKOFF_MS`, `FLAGD_RETRY_BACKOFF_MAX_MS`, `FLAGD_RETRY_GRACE_PERIOD` | 1000, 120000, 5 | rpc, in-process |
| `stream_deadline_ms` | `FLAGD_STREAM_DEADLINE_MS` | 600000 | rpc |
| `offline_poll_interval_ms` | `FLAGD_OFFLINE_POLL_MS` | 5000 | file |
| `selector` | `FLAGD_SOURCE_SELECTOR` | "" | in-process |

Quirks: only provider with a first-class OFREP (`Rest`) resolver and a cache TTL. `FlagdProvider::new` is async and
fails fast if the initial connection cannot be made. The README evaluates directly on the provider
(`provider.resolve_bool_value`); going through the `OpenFeature` client as above is the normal path.

Source: https://flagd.dev/providers/rust/ · https://github.com/open-feature/rust-sdk-contrib/tree/main/crates/flagd

## 14. Support tiers and server-side context enrichment

**Language support policy** (ADR, accepted 2026-01-27): Tier 1 "core" providers must pass 100% of the OpenFeature
conformance suite and the flagd Gherkin e2e suite, have >= 2 maintainers, and ride a **release train** with feature
parity per release (a feature is cut, delayed, or shipped as experimental everywhere if one language lags). Tier 2
"community" match Tier 1 version numbers but may lag; no SLO. Tier 3 "experimental" may be archived after 6 months
idle. Core / experimental / language-specific feature classes govern what an option table may legitimately lack
(e.g. Java-only `compileTargeting`). Practical read: rpc + in-process + file with the §4 option set is the
cross-language core; PHP (HTTP-only) and flagd-web (bulk RPC) are intentionally narrower.

**Server-side context enrichment** (ADR, accepted 2026-01-21): flagd itself can add context so clients send less.
`flagd start -X region=europe` (`--context-value`) injects static key/values into every evaluation;
`flagd start -H X-User-Email:userEmail` (`--context-from-header`) maps an inbound HTTP/gRPC header into a context
attribute per request (OFREP and evaluation v2 over Connect). Merge precedence: header-derived (`-H`) > static
(`-X`) > request-body context. Only applies to **rpc/OFREP** evaluation in flagd; in-process providers get the
equivalent via **sync-metadata** injected into context (`contextEnricher` to filter), not available in file mode.

Source: https://flagd.dev/architecture-decisions/supported-languages/ ·
https://flagd.dev/architecture-decisions/static-and-dynamic-context/
