# OpenFeature Python SDK — deep-dive reference

Verified against source on 2026-09-21. Every identifier below was grepped in the cloned repos; where the
source and the upstream README disagree, the source wins and the disagreement is called out.

| Package (PyPI) | Version | Import root | Notes |
|---|---|---|---|
| `openfeature-sdk` | 0.10.0 (commit a1b9c69) | `openfeature` | zero runtime deps; Python >= 3.10 (3.10–3.14 classifiers); spec v0.8.0 |
| `openfeature-provider-flagd` | 0.5.2 | `openfeature.contrib.provider.flagd` | grpcio, protobuf, pyyaml, cachebox, openfeature-flagd-core |
| `openfeature-provider-ofrep` | 0.3.0 | `openfeature.contrib.provider.ofrep` | requests |
| `openfeature-provider-env-var` | 0.1.1 | `openfeature.contrib.provider.envvar` | no extra deps |
| `openfeature-provider-flipt` | 0.1.3 | `openfeature.contrib.provider.flipt` | subclass of OFREP provider |
| `openfeature-provider-unleash` | 0.1.2 | `openfeature.contrib.provider.unleash` | UnleashClient >= 6.3.0 |
| `openfeature-provider-aws-ssm` | 0.1.1 | `openfeature.contrib.provider.awsssm` | boto3, cachebox; `[async]` extra adds aioboto3 |
| `openfeature-hooks-opentelemetry` | 0.3.1 | `openfeature.contrib.hook.opentelemetry` | opentelemetry-api, opentelemetry-semantic-conventions |

All contrib packages are PEP 420 namespace packages under `openfeature.contrib.*`; they install side by side with the SDK
and there is no `openfeature/contrib/__init__.py`. The SDK itself logs to the `openfeature` logger; the OFREP provider
logs to `openfeature.contrib.ofrep`.

## Contents

1. [Install and minimal program](#1-install-and-minimal-program)
2. [Evaluation API (sync and async)](#2-evaluation-api-sync-and-async)
3. [Evaluation context and transaction context](#3-evaluation-context-and-transaction-context)
4. [Hooks](#4-hooks)
5. [Events](#5-events)
6. [Provider lifecycle, custom providers, test providers](#6-provider-lifecycle-custom-providers-test-providers)
7. [Async providers](#7-async-providers)
8. [Tracking](#8-tracking)
9. [Telemetry helpers and the OpenTelemetry hook](#9-telemetry-helpers-and-the-opentelemetry-hook)
10. [Contrib providers](#10-contrib-providers)
11. [Recipes](#11-recipes)
12. [Gotchas](#12-gotchas)
13. [When this file is silent](#13-when-this-file-is-silent)

---

## 1. Install and minimal program

```bash
pip install openfeature-sdk==0.10.0
# plus a provider, e.g.
pip install openfeature-provider-flagd   # or openfeature-provider-ofrep, ...
```

```python
from openfeature import api
from openfeature.provider.in_memory_provider import InMemoryFlag, InMemoryProvider

flags = {"v2_enabled": InMemoryFlag("on", {"on": True, "off": False})}
api.set_provider_and_wait(InMemoryProvider(flags))   # blocks until PROVIDER_READY

client = api.get_client()
print(client.get_boolean_value("v2_enabled", False))  # True
api.shutdown()
```

### The `openfeature.api` module (complete public surface, from `api.__all__`)

| Function | Signature | What it does |
|---|---|---|
| `set_provider` | `(provider: FeatureProvider, domain: str \| None = None) -> None` | Registers the provider (default or per-domain) and **returns immediately**; `initialize()` runs on a daemon thread. Evaluations before READY return the default with `PROVIDER_NOT_READY`. |
| `set_provider_and_wait` | same | Registers and blocks until `initialize()` returns. If `initialize()` raises, the exception is **re-raised to the caller** (and a `PROVIDER_ERROR` event is dispatched). |
| `get_client` | `(domain: str \| None = None, version: str \| None = None) -> OpenFeatureClient` | Returns a new `OpenFeatureClient`; the client resolves its provider lazily on every call via the registry, so it always sees the current provider for its domain. |
| `get_provider_metadata` | `(domain=None) -> Metadata` | `Metadata(name=...)` dataclass. |
| `clear_providers` | `() -> None` | Shuts every provider down, resets to `NoOpProvider`, drops all event handlers. |
| `shutdown` | `() -> None` | `clear_providers()` + `clear_hooks()` + `clear_evaluation_context()` + `clear_transaction_context_propagator()`. Spec §1.6. |
| `add_hooks` / `clear_hooks` / `get_hooks` | `(hooks: list[Hook])` | API-level hooks (re-exported from `openfeature.hook`). |
| `set_evaluation_context` / `get_evaluation_context` | `(EvaluationContext)` | API-level (global) context. |
| `set_transaction_context` / `get_transaction_context` / `set_transaction_context_propagator` | see §3 | |
| `add_handler` / `remove_handler` | `(event: ProviderEvent, handler: EventHandler)` | Global event handlers. |

Behaviour of `set_provider` / registry (`openfeature/provider/_registry.py`):

- Since **0.10.0** registration is non-blocking (CHANGELOG "make set_provider non-blocking, add set_provider_and_wait", #595). Before 0.10.0 `set_provider` blocked.
- A provider instance already bound to another domain is **not** initialized twice (0.9.0 fix "Prevent providers from being initialized multiple times").
- Replacing a provider shuts the old one down on a daemon thread if it is no longer bound anywhere (spec Requirement 1.1.2.3). A failing `shutdown()` dispatches `PROVIDER_ERROR` with `ErrorCode.PROVIDER_FATAL`.
- Status transitions: `PROVIDER_READY` → `READY`, `PROVIDER_STALE` → `STALE`, `PROVIDER_ERROR` → `ERROR` (or `FATAL` when `details.error_code == ErrorCode.PROVIDER_FATAL`). A provider object without an `initialize` attribute is marked READY synchronously.

### Waiting for readiness without blocking the registration call

```python
import threading
from openfeature import api
from openfeature.event import EventDetails, ProviderEvent

ready = threading.Event()
api.add_handler(ProviderEvent.PROVIDER_READY, lambda d: ready.set())
api.set_provider(FlagdProvider())
ready.wait(timeout=5)                      # or just use api.set_provider_and_wait(...)
print(api.get_client().get_provider_status())   # ProviderStatus.READY
```

Handlers registered when the provider is already in the matching state are invoked immediately (`_event_support._run_immediate_handler`).

### Domains (named clients)

```python
api.set_provider(FlagdProvider(), domain="checkout")   # domain-scoped provider
api.set_provider(InMemoryProvider(flags))              # default provider

checkout = api.get_client(domain="checkout")   # bound to FlagdProvider
other    = api.get_client()                    # bound to default
api.get_client(domain="unknown")               # falls back to the default provider
```

`client.domain`, `client.get_metadata()` → `ClientMetadata(name=None, domain=...)`, `client.provider` (property), `client.get_provider_status()` → `ProviderStatus`.

---

## 2. Evaluation API (sync and async)

`OpenFeatureClient` (`openfeature/client.py`) exposes five typed getters, each in four flavours. Signatures are identical apart from the type of `default_value`:

```python
def get_boolean_value(self, flag_key: str, default_value: bool,
                      evaluation_context: EvaluationContext | None = None,
                      flag_evaluation_options: FlagEvaluationOptions | None = None) -> bool
def get_boolean_details(...) -> FlagEvaluationDetails[bool]
async def get_boolean_value_async(...) -> bool
async def get_boolean_details_async(...) -> FlagEvaluationDetails[bool]
```

| Type | `_value` / `_details` / `_value_async` / `_details_async` | `default_value` type | `FlagType` |
|---|---|---|---|
| bool | `get_boolean_*` | `bool` | `FlagType.BOOLEAN` |
| str | `get_string_*` | `str` | `FlagType.STRING` |
| int | `get_integer_*` | `int` | `FlagType.INTEGER` |
| float | `get_float_*` | `float` | `FlagType.FLOAT` |
| object | `get_object_*` | `Sequence[FlagValueType] \| Mapping[str, FlagValueType]` (a `dict` or `list`) | `FlagType.OBJECT` |

Generic entry points also exist: `client.evaluate_flag_details(flag_type, flag_key, default_value, evaluation_context=None, flag_evaluation_options=None)` and `evaluate_flag_details_async(...)`. There is no separate `AsyncClient`; the same client object has both sync and `_async` methods.

### Result types (`openfeature.flag_evaluation`)

```python
@dataclass
class FlagEvaluationDetails(Generic[T_co]):
    flag_key: str
    value: T_co
    variant: str | None = None
    flag_metadata: FlagMetadata = field(default_factory=dict)   # Mapping[str, bool|int|float|str]
    reason: str | Reason | None = None
    error_code: ErrorCode | None = None
    error_message: str | None = None
    def get_exception(self) -> OpenFeatureError | None: ...

@dataclass
class FlagEvaluationOptions:
    hooks: list[Hook] = field(default_factory=list)
    hook_hints: HookHints = field(default_factory=dict)         # Mapping[str, HookHintValue]

class FlagType(StrEnum):  BOOLEAN, STRING, OBJECT, FLOAT, INTEGER
class Reason(StrEnum):    CACHED, DEFAULT, DISABLED, ERROR, SPLIT, STATIC, STALE, TARGETING_MATCH, UNKNOWN
```

`ErrorCode` (`openfeature.exception`, a `StrEnum`): `PROVIDER_NOT_READY`, `PROVIDER_FATAL`, `FLAG_NOT_FOUND`, `PARSE_ERROR`, `TYPE_MISMATCH`, `TARGETING_KEY_MISSING`, `INVALID_CONTEXT`, `GENERAL`. Each has a matching exception class (`ProviderNotReadyError`, `ProviderFatalError`, `FlagNotFoundError`, `ParseError`, `TypeMismatchError`, `TargetingKeyMissingError`, `InvalidContextError`, `GeneralError`), all subclasses of `OpenFeatureError(error_code, error_message)`. `ErrorCode.to_exception(code, message)` maps back. `Reason`/`ErrorCode` are `StrEnum`s, so `details.reason == "TARGETING_MATCH"` works and `str(Reason.ERROR) == "ERROR"` (the backport in `openfeature/_backports/strenum.py` guarantees this on 3.10).

### The evaluation pipeline (what `evaluate_flag_details` actually does)

1. Merge context: API → transaction → client → invocation (spec Requirement 3.2.3).
2. Build `HookContext` for every hook in order API → client → invocation → provider (`get_provider_hooks()`), Requirement 4.4.2.
3. If provider status is `NOT_READY` → `ProviderNotReadyError`; `FATAL` → `ProviderFatalError`; run `error` hooks, return default with `reason=Reason.ERROR`. Other statuses (`ERROR`, `STALE`) still evaluate.
4. Run `before` hooks; merge any returned `EvaluationContext` on top (highest precedence).
5. Call `provider.resolve_<type>_details(...)` (or `_async`). If the resolution carries `error_code`, or the returned value fails the type check, run `error` hooks and return `default_value` with the error code.
6. Otherwise run `after` hooks (reverse order: provider → invocation → client → API).
7. Always run `finally_after` hooks in the same reverse order.

Exceptions raised inside `before`/`after` hooks or inside the provider are caught by the client: `OpenFeatureError` keeps its code, anything else becomes `ErrorCode.GENERAL` and is logged with `logger.exception`. **Evaluation never raises; you always get the default back.** Exceptions from `error` and `finally_after` hooks are swallowed and logged (`hook/_hook_support.py`).

Type check (`client._typecheck_flag_value`): `BOOLEAN → bool`, `STRING → str`, `INTEGER → int` **but `bool` is rejected for INTEGER**, `FLOAT → float` (an `int` such as `1` is a `TYPE_MISMATCH` for a float flag), `OBJECT → (dict, list)`.

```python
d = client.get_string_details("banner", "none", EvaluationContext(targeting_key="u-1"))
if d.error_code:
    log.warning("flag %s fell back: %s %s", d.flag_key, d.error_code, d.error_message)
print(d.value, d.variant, d.reason, d.flag_metadata)
```

Async:

```python
import asyncio
from openfeature import api

async def main() -> None:
    client = api.get_client()
    enabled, limit = await asyncio.gather(
        client.get_boolean_value_async("v2_enabled", False),
        client.get_integer_value_async("page_size", 20),
    )

asyncio.run(main())
```

If the provider does not implement `_async` resolvers, `AbstractProvider` defaults delegate to the sync method, so the `await` is non-yielding (it blocks the event loop for the duration of the sync call). Wrap such providers with `asyncio.to_thread` if that matters.

---

## 3. Evaluation context and transaction context

```python
from openfeature.evaluation_context import EvaluationContext

ctx = EvaluationContext(
    targeting_key="user-42",
    attributes={"email": "a@b.c", "plan": "pro", "beta": True, "signup": datetime(2025, 1, 1)},
)
```

`EvaluationContext` is a plain (mutable, non-frozen) dataclass with two fields: `targeting_key: str | None` and `attributes: Mapping[str, EvaluationContextAttribute]` where attribute values may be `bool | int | float | str | datetime | Sequence[...] | Mapping[str, ...]` (Requirement 3.1.2). `ctx.merge(other)` returns a **new** context: attributes are `{**self.attributes, **other.attributes}` and `targeting_key = other.targeting_key or self.targeting_key`. Merging with an empty context returns the non-empty one. The SDK never mutates your context objects, but it does not copy them either; do not mutate a context after handing it to `set_evaluation_context`.

Merge order (Requirement 3.2.3), lowest to highest precedence:

| Level | How to set | Scope |
|---|---|---|
| API | `api.set_evaluation_context(ctx)` | process-wide |
| transaction | `api.set_transaction_context(ctx)` (needs a propagator) | current `contextvars` context, i.e. current thread / asyncio task |
| client | `OpenFeatureClient(domain, version, context=ctx)` or `client.context = ctx` | that client instance |
| invocation | `client.get_*("key", default, evaluation_context=ctx)` | one call |
| before hooks | return an `EvaluationContext` from `Hook.before` | one call |

There is **no `client.set_context()` method** in 0.10.0. `OpenFeatureClient.__init__(self, domain, version, context=None, hooks=None)` takes the client context, and `client.context` is a public attribute you can reassign. `api.get_client()` does not accept `context`, so either construct `OpenFeatureClient(domain=None, version=None, context=ctx)` directly or assign after `get_client()`.

### Transaction context

```python
from openfeature import api
from openfeature.evaluation_context import EvaluationContext
from openfeature.transaction_context import ContextVarsTransactionContextPropagator

api.set_transaction_context_propagator(ContextVarsTransactionContextPropagator())   # once, at startup

# anywhere in a request handler / task:
api.set_transaction_context(EvaluationContext(targeting_key=user_id, attributes={"ip": ip}))
# every evaluation in this thread / asyncio task now sees it
```

- Default propagator is `NoOpTransactionContextPropagator` (returns an empty context, `set_transaction_context` is a no-op), so calling `set_transaction_context` **without** installing a propagator silently does nothing.
- `ContextVarsTransactionContextPropagator` stores the context in a class-level `ContextVar("transaction_context")`; it works for threads and asyncio tasks (each task gets a copy of the parent's context at creation; changes inside the task do not leak out).
- Custom propagators implement the `TransactionContextPropagator` Protocol: `get_transaction_context() -> EvaluationContext` and `set_transaction_context(EvaluationContext) -> None`.
- `api.shutdown()` resets the propagator to the no-op one.

---

## 4. Hooks

```python
from openfeature.hook import Hook, HookContext, HookHints, HookType, HookData
from openfeature.flag_evaluation import FlagEvaluationDetails, FlagValueType, FlagType
from openfeature.evaluation_context import EvaluationContext

class Hook:
    def before(self, hook_context: HookContext, hints: HookHints) -> EvaluationContext | None: ...
    def after(self, hook_context: HookContext, details: FlagEvaluationDetails[FlagValueType], hints: HookHints) -> None: ...
    def error(self, hook_context: HookContext, exception: Exception, hints: HookHints) -> None: ...
    def finally_after(self, hook_context: HookContext, details: FlagEvaluationDetails[FlagValueType], hints: HookHints) -> None: ...
    def supports_flag_value_type(self, flag_type: FlagType) -> bool: return True
```

`HookContext` attributes: `flag_key`, `flag_type`, `default_value`, `evaluation_context` (the **merged** context, Requirement 4.1.4), `client_metadata: ClientMetadata | None`, `provider_metadata: Metadata | None`, `hook_data: HookData` (a `MutableMapping[str, Any]`). `flag_key`, `flag_type`, `default_value`, `client_metadata`, `provider_metadata` are immutable after construction (`__setattr__` raises `AttributeError`); `evaluation_context` and `hook_data` may be reassigned. Each hook gets its **own** `HookContext` (and therefore its own `hook_data`) per evaluation; `hook_data` is the sanctioned way to pass state from `before` to `after`/`finally_after` (Requirement 4.3.2 / 4.6.1). `HookHints` is a `Mapping[str, HookHintValue]` supplied via `FlagEvaluationOptions(hook_hints=...)`; it may be `None` for stages the client invokes with no hints, so guard with `hints or {}`.

Registration levels and order (Requirement 4.4.2): `before` runs API → client → invocation → provider hooks, in insertion order within a level; `after`, `error`, `finally_after` run in the exact reverse.

```python
from openfeature import api
from openfeature.flag_evaluation import FlagEvaluationOptions

api.add_hooks([MyHook()])                                        # API level
client = api.get_client(); client.add_hooks([MyHook()])          # client level
client.get_boolean_value("f", False,
    flag_evaluation_options=FlagEvaluationOptions(hooks=[MyHook()], hook_hints={"team": "growth"}))  # invocation
# provider level: override AbstractProvider.get_provider_hooks() -> list[Hook]
```

A complete timing/metrics hook:

```python
import logging, time
from openfeature.hook import Hook, HookContext, HookHints
from openfeature.flag_evaluation import FlagEvaluationDetails, FlagValueType, Reason

log = logging.getLogger("flags")

class TimingHook(Hook):
    def before(self, hook_context: HookContext, hints: HookHints):
        hook_context.hook_data["t0"] = time.perf_counter()
        return None  # or return EvaluationContext(attributes={"region": "eu"}) to enrich

    def finally_after(self, hook_context: HookContext, details: FlagEvaluationDetails[FlagValueType], hints: HookHints) -> None:
        ms = (time.perf_counter() - hook_context.hook_data.get("t0", time.perf_counter())) * 1000
        log.info("flag=%s variant=%s reason=%s error=%s ms=%.2f domain=%s",
                 details.flag_key, details.variant, details.reason, details.error_code, ms,
                 hook_context.client_metadata.domain if hook_context.client_metadata else None)

    def error(self, hook_context: HookContext, exception: Exception, hints: HookHints) -> None:
        log.warning("flag=%s failed: %r", hook_context.flag_key, exception)
```

The SDK ships `openfeature.hook.logging_hook.LoggingHook(include_evaluation_context: bool = False, logger: logging.Logger | None = None)` (added 0.9.0). It logs `before`/`after` at DEBUG and `error` at ERROR on the `openfeature` logger by default; set that logger to DEBUG to see it.

Async hooks: **not supported**. Hook methods are called synchronously from both `evaluate_flag_details` and `evaluate_flag_details_async`; an `async def before` would return an un-awaited coroutine (and the client would then try to `.merge()` it). Keep hooks synchronous and cheap.

---

## 5. Events

```python
from openfeature.event import ProviderEvent, EventDetails, ProviderEventDetails, EventHandler

class ProviderEvent(Enum):
    PROVIDER_READY, PROVIDER_CONFIGURATION_CHANGED, PROVIDER_ERROR, PROVIDER_STALE

@dataclass
class ProviderEventDetails:        # what a provider emits
    flags_changed: list[str] | None = None
    message: str | None = None
    error_code: ErrorCode | None = None
    metadata: dict[str, bool | str | int | float] = field(default_factory=dict)

@dataclass
class EventDetails(ProviderEventDetails):   # what handlers receive; adds
    provider_name: str = ""

EventHandler = Callable[[EventDetails], None]
```

```python
def on_change(details: EventDetails) -> None:
    print(details.provider_name, details.flags_changed)

api.add_handler(ProviderEvent.PROVIDER_CONFIGURATION_CHANGED, on_change)   # all providers
client.add_handler(ProviderEvent.PROVIDER_ERROR, on_error)                 # only this client's provider
api.remove_handler(...); client.remove_handler(...)
```

Semantics (`openfeature/_event_support.py`):

- Handlers run on a shared `ThreadPoolExecutor(thread_name_prefix="openfeature-event-handler")`, **not** on the emitting thread; exceptions are logged (`"Unhandled exception in OpenFeature event handler"`) and isolated (0.10.0 fix #599). Do not assume a handler has finished when `emit` returns; in tests, poll or use a `threading.Event`.
- Adding a handler for `PROVIDER_READY`/`PROVIDER_ERROR`/`PROVIDER_STALE` when the provider is already `READY`/`ERROR|FATAL`/`STALE` fires it immediately with `EventDetails(provider_name=...)` (Requirement 5.3.3 style behaviour).
- Client handlers are keyed by the client object and matched via `client.provider == provider`, so a client created for a domain receives events from whichever provider is bound to that domain at emit time.
- `api.clear_providers()`/`api.shutdown()` drop all handlers.

Providers emit via `AbstractProvider.emit_provider_ready(details)`, `emit_provider_configuration_changed(details)`, `emit_provider_error(details)`, `emit_provider_stale(details)` or the generic `emit(event, details)`. These call the `on_emit` callback the registry injected through `attach(on_emit)`; before `attach` (or after `detach`) `emit` is a no-op. You do **not** emit `PROVIDER_READY` yourself for the initial readiness: the registry dispatches it when `initialize()` returns normally, and `PROVIDER_ERROR` when it raises.

---

## 6. Provider lifecycle, custom providers, test providers

`openfeature.provider` exports `AbstractProvider`, `FeatureProvider` (a `typing.Protocol`), `Metadata`, `ProviderStatus`.

```python
class ProviderStatus(Enum): NOT_READY, READY, ERROR, STALE, FATAL

class AbstractProvider(FeatureProvider):
    def attach(self, on_emit) -> None        # set by the registry; keep the default
    def detach(self) -> None
    def initialize(self, evaluation_context: EvaluationContext) -> None   # default: pass
    def shutdown(self) -> None                                            # default: pass
    def track(self, tracking_event_name, evaluation_context=None, tracking_event_details=None) -> None  # default: pass
    @abstractmethod def get_metadata(self) -> Metadata
    def get_provider_hooks(self) -> list[Hook]: return []
    @abstractmethod def resolve_boolean_details(self, flag_key: str, default_value: bool, evaluation_context: EvaluationContext | None = None) -> FlagResolutionDetails[bool]
    @abstractmethod def resolve_string_details(...)  -> FlagResolutionDetails[str]
    @abstractmethod def resolve_integer_details(...) -> FlagResolutionDetails[int]
    @abstractmethod def resolve_float_details(...)   -> FlagResolutionDetails[float]
    @abstractmethod def resolve_object_details(...)  -> FlagResolutionDetails[Sequence | Mapping]
    async def resolve_*_details_async(...)            # defaults delegate to the sync methods
    def emit_provider_ready / emit_provider_configuration_changed / emit_provider_error / emit_provider_stale / emit
```

`FlagResolutionDetails` (`openfeature.flag_evaluation`):

```python
@dataclass
class FlagResolutionDetails(Generic[U_co]):
    value: U_co
    error_code: ErrorCode | None = None
    error_message: str | None = None
    reason: str | Reason | None = None
    variant: str | None = None
    flag_metadata: FlagMetadata = field(default_factory=dict)
    def raise_for_error(self) -> None
    def to_flag_evaluation_details(self, flag_key: str) -> FlagEvaluationDetails[U_co]
```

A provider signals an error either by returning `FlagResolutionDetails(value=default_value, error_code=ErrorCode.FLAG_NOT_FOUND, reason=Reason.ERROR, error_message=...)` or by raising an `OpenFeatureError` subclass; the client turns both into a default-valued result. Raising a non-OpenFeature exception becomes `ErrorCode.GENERAL`. Spec §2.2.

### Complete minimal custom provider (runnable)

```python
from collections.abc import Mapping, Sequence
from openfeature import api
from openfeature.evaluation_context import EvaluationContext
from openfeature.event import ProviderEventDetails
from openfeature.exception import ErrorCode
from openfeature.flag_evaluation import FlagResolutionDetails, FlagValueType, Reason
from openfeature.provider import AbstractProvider, Metadata


class DictProvider(AbstractProvider):
    """Resolves flags from a dict; per-user overrides keyed by targeting_key."""

    def __init__(self, flags: dict[str, object], overrides: dict[str, dict[str, object]] | None = None):
        self._flags = flags
        self._overrides = overrides or {}

    def get_metadata(self) -> Metadata:
        return Metadata(name="dict-provider")

    def initialize(self, evaluation_context: EvaluationContext) -> None:
        # connect / warm caches here; raise to signal PROVIDER_ERROR
        pass

    def shutdown(self) -> None:
        self._flags = {}

    def reload(self, flags: dict[str, object]) -> None:
        self._flags = flags
        self.emit_provider_configuration_changed(ProviderEventDetails(flags_changed=list(flags)))

    def _resolve(self, flag_key, default_value, ctx):
        if flag_key not in self._flags:
            return FlagResolutionDetails(value=default_value, reason=Reason.ERROR,
                                         error_code=ErrorCode.FLAG_NOT_FOUND,
                                         error_message=f"{flag_key!r} not found")
        if ctx and ctx.targeting_key in self._overrides and flag_key in self._overrides[ctx.targeting_key]:
            return FlagResolutionDetails(value=self._overrides[ctx.targeting_key][flag_key],
                                         reason=Reason.TARGETING_MATCH, variant="override")
        return FlagResolutionDetails(value=self._flags[flag_key], reason=Reason.STATIC, variant="default")

    # The client type-checks the returned value, so one implementation serves all five.
    def resolve_boolean_details(self, flag_key: str, default_value: bool, evaluation_context: EvaluationContext | None = None) -> FlagResolutionDetails[bool]:
        return self._resolve(flag_key, default_value, evaluation_context)
    def resolve_string_details(self, flag_key: str, default_value: str, evaluation_context: EvaluationContext | None = None) -> FlagResolutionDetails[str]:
        return self._resolve(flag_key, default_value, evaluation_context)
    def resolve_integer_details(self, flag_key: str, default_value: int, evaluation_context: EvaluationContext | None = None) -> FlagResolutionDetails[int]:
        return self._resolve(flag_key, default_value, evaluation_context)
    def resolve_float_details(self, flag_key: str, default_value: float, evaluation_context: EvaluationContext | None = None) -> FlagResolutionDetails[float]:
        return self._resolve(flag_key, default_value, evaluation_context)
    def resolve_object_details(self, flag_key: str, default_value: Sequence[FlagValueType] | Mapping[str, FlagValueType], evaluation_context: EvaluationContext | None = None) -> FlagResolutionDetails[Sequence[FlagValueType] | Mapping[str, FlagValueType]]:
        return self._resolve(flag_key, default_value, evaluation_context)


if __name__ == "__main__":
    api.set_provider_and_wait(DictProvider({"dark_mode": False}, {"u1": {"dark_mode": True}}))
    c = api.get_client()
    assert c.get_boolean_value("dark_mode", False) is False
    assert c.get_boolean_value("dark_mode", False, EvaluationContext(targeting_key="u1")) is True
    assert c.get_boolean_details("missing", True).error_code == ErrorCode.FLAG_NOT_FOUND
    api.shutdown()
```

### `NoOpProvider`

`openfeature.provider.no_op_provider.NoOpProvider` — the default before any `set_provider`. Returns the passed default with `reason=Reason.DEFAULT`, `variant="Passed in default"`, metadata name `"No-op Provider"`. Status is `READY` from the start.

### `InMemoryProvider` (for tests and demos)

```python
from openfeature.provider.in_memory_provider import InMemoryFlag, InMemoryProvider

@dataclass(frozen=True)
class InMemoryFlag(Generic[T_co]):
    default_variant: str
    variants: dict[str, T_co]
    flag_metadata: FlagMetadata = {}
    state: InMemoryFlag.State = State.ENABLED          # ENABLED | DISABLED
    context_evaluator: Callable[[InMemoryFlag[T_co], EvaluationContext], FlagResolutionDetails[T_co]] | None = None

InMemoryProvider(flags: dict[str, InMemoryFlag], tracking_events: dict | None = None)
```

- Missing key → `FLAG_NOT_FOUND`. Present key → `variants[default_variant]` with `reason=STATIC`, `variant=default_variant`, `flag_metadata` copied through.
- `context_evaluator(flag, ctx)` replaces the static resolution entirely and lets you do targeting:

```python
def by_plan(flag: InMemoryFlag, ctx: EvaluationContext) -> FlagResolutionDetails:
    variant = "on" if ctx.attributes.get("plan") == "pro" else flag.default_variant
    return FlagResolutionDetails(value=flag.variants[variant], variant=variant, reason=Reason.TARGETING_MATCH)

flags = {"pro_only": InMemoryFlag("off", {"on": True, "off": False}, context_evaluator=by_plan)}
```

- Runtime updates: `provider.update_flags(flags)` (replaces all, emits `PROVIDER_CONFIGURATION_CHANGED` with the union of old and new keys), `provider.update_flag(key, flag)` (one key), `provider.flag(key)` (read back).
- `track()` stores `InMemoryTrackingEvent(value, details, eval_context_attributes)` in `provider._tracking_events[name]`, useful for asserting on tracking calls.
- **`state=InMemoryFlag.State.DISABLED` is not enforced**: `InMemoryFlag.resolve()` never reads `state` (grep `state` in `in_memory_provider.py`; there is no branch on it and no test for it). Do not rely on it to simulate a disabled flag; use a `context_evaluator` that returns `reason=Reason.DISABLED` instead.

---

## 7. Async providers

There is a single provider class hierarchy; "async support" means overriding the five `resolve_*_details_async` coroutines on your `AbstractProvider` subclass:

```python
class MyProvider(AbstractProvider):
    ...
    async def resolve_boolean_details_async(self, flag_key: str, default_value: bool,
                                            evaluation_context: EvaluationContext | None = None) -> FlagResolutionDetails[bool]:
        raw = await self._http.get(f"/flags/{flag_key}")
        return FlagResolutionDetails(value=raw["value"], variant=raw.get("variant"), reason=Reason.TARGETING_MATCH)
```

- `client.get_*_async` → `evaluate_flag_details_async` → `provider.resolve_*_details_async`; hooks and status checks are identical to the sync path and run synchronously.
- `AbstractProvider` provides default `_async` methods that just call the sync ones, so every provider is usable from async code, only without yielding. `InMemoryProvider` and `NoOpProvider` (via defaults) behave this way. Among the contrib providers only **`AwsSsmProvider`** implements real `_async` resolvers (`_resolve_with_cache_async`, requires the `[async]` extra / aioboto3). Flagd, OFREP, env-var, Flipt and Unleash are sync-only.
- `initialize()` and `shutdown()` are always synchronous; the registry runs `initialize` on a thread (or inline for `set_provider_and_wait`). If your provider needs an event loop to initialize, do it lazily on first resolution or run your own loop inside `initialize`.

---

## 8. Tracking

```python
from openfeature.track import TrackingEventDetails

client.track(
    "checkout-completed",
    evaluation_context=EvaluationContext(targeting_key="user-42"),
    tracking_event_details=TrackingEventDetails(value=99.77).add("currency", "USD").add("items", 3),
)
```

- `OpenFeatureClient.track(tracking_event_name: str, evaluation_context: EvaluationContext | None = None, tracking_event_details: TrackingEventDetails | None = None) -> None` merges API → transaction → client → invocation context exactly like evaluation and calls `provider.track(...)`. Spec §6.
- `TrackingEventDetails(value: float | None = None, attributes: dict[str, TrackingValue] | None = None)`; `.add(key, value)` returns `self` for chaining; `.value` and `.attributes` are public.
- `AbstractProvider.track` is a no-op, so unsupported providers silently ignore it. Among contrib providers, `UnleashProvider` and `InMemoryProvider` implement `track`.

---

## 9. Telemetry helpers and the OpenTelemetry hook

`openfeature.telemetry` (in the SDK) builds an OTel-semantic-convention event from a hook stage, for use in your own hook:

```python
from openfeature.telemetry import create_evaluation_event, EvaluationEvent, TelemetryAttribute, TelemetryBodyField, TelemetryFlagMetadata

class OtelLogHook(Hook):
    def finally_after(self, hook_context, details, hints):
        ev: EvaluationEvent = create_evaluation_event(hook_context, details)
        # ev.name == "feature_flag.evaluation"
        # ev.attributes: {TelemetryAttribute.KEY: ..., TelemetryAttribute.EVALUATION_REASON: "static", ...}
        # ev.body: {TelemetryBodyField.VALUE: value}  (only when there is no variant)
```

`TelemetryAttribute` values: `feature_flag.key`, `feature_flag.evaluation.reason`, `feature_flag.variant`, `feature_flag.context.id`, `feature_flag.set.id`, `feature_flag.version`, `feature_flag.provider_name`, `error.type`, `feature_flag.evaluation.error.message`. `TelemetryFlagMetadata` names the well-known `flag_metadata` keys the helper reads: `contextId`, `flagSetId`, `version` (spec Appendix D). `context.id` falls back to `evaluation_context.targeting_key`.

### `openfeature-hooks-opentelemetry` 0.3.1

```python
from openfeature.contrib.hook.opentelemetry import TracingHook
api.add_hooks([TracingHook(exclude_exceptions=False)])
```

- Only **`TracingHook`** exists in this package (there is no `MetricsHook` in 0.3.1). It adds a span event named `feature_flag.evaluation` to the **current** span in `finally_after` with attributes `feature_flag.key`, `feature_flag.result.value` (JSON-encoded), `feature_flag.result.reason`, `feature_flag.result.variant`, `feature_flag.context.id` (targeting key), `feature_flag.provider.name`, and on error `error.type` / `error.message`. In `error` it calls `span.record_exception(...)` unless `exclude_exceptions=True`.
- Note the attribute names differ from the SDK's `openfeature.telemetry` helper (`result.value`/`result.reason`/`provider.name` vs `evaluation.reason`/`variant`/`provider_name`): the hook follows the newer OTel semconv, the helper the older one.
- Register it globally or per client, never both (duplicate events). It needs an active span from your OTel SDK setup; with no span it writes to the non-recording span and is a no-op.

---

## 10. Contrib providers

| Package | Class / import | Constructor | Notes |
|---|---|---|---|
| `openfeature-provider-flagd` 0.5.2 | `from openfeature.contrib.provider.flagd import FlagdProvider` | `FlagdProvider(host=None, port=None, tls=None, deadline_ms=None, timeout=None (deprecated, seconds), retry_backoff_ms=None, selector=None, provider_id=None, resolver_type: ResolverType | None = None, offline_flag_source_path=None, stream_deadline_ms=None, keep_alive_time=None, cache: CacheType | None = None, max_cache_size=None, retry_backoff_max_ms=None, retry_grace_period=None, cert_path=None, default_authority=None, channel_credentials: grpc.ChannelCredentials | None = None, sync_metadata_disabled=None, fatal_status_codes: list[str] | None = None)` | `ResolverType`/`CacheType` from `openfeature.contrib.provider.flagd.config`. Every `None` falls back to a `FLAGD_*` env var, then a default. Sync only. |
| `openfeature-provider-ofrep` 0.3.0 | `from openfeature.contrib.provider.ofrep import OFREPProvider` | `OFREPProvider(base_url: str, *, headers_factory: Callable[[], dict[str, str]] | None = None, timeout: float = 5.0)` | POSTs to `{base_url}/ofrep/v1/evaluate/flags/{key}` with a `requests.Session`; `headers_factory()` is called per request (put auth here). Honors `Retry-After` on 429 by raising `GeneralError` until the deadline. Metadata name `"OpenFeature Remote Evaluation Protocol Provider"`. The upstream README's `OFREPProvider()` with no args is wrong; `base_url` is required. |
| `openfeature-provider-env-var` 0.1.1 | `from openfeature.contrib.provider.envvar import EnvVarProvider` | `EnvVarProvider()` | Flag key == env var name. Missing → `FlagNotFoundError`; int/float via `int()`/`float()` → `ParseError` on failure; object via `json.loads`, must be dict or list. **Boolean parsing is `bool(value)`**, so any non-empty string including `"false"` and `"0"` is `True`. Reason is always `DEFAULT`. |
| `openfeature-provider-flipt` 0.1.3 | `from openfeature.contrib.provider.flipt import FliptProvider` | `FliptProvider(base_url: str, namespace: str, *, headers_factory=None, timeout=5.0)` | `OFREPProvider` subclass that injects `X-Flipt-Namespace`. |
| `openfeature-provider-unleash` 0.1.2 | `from openfeature.contrib.provider.unleash import UnleashProvider` | `UnleashProvider(url: str, app_name: str, api_token: str, fetch_toggles: bool = True, cache: BaseCache | None = None)` | Wraps `UnleashClient`; `targeting_key` → Unleash `userId`, attributes merged as-is. Booleans via `is_enabled`, other types from the variant payload. Emits READY/ERROR/CONFIGURATION_CHANGED; also has its own `add_handler`/`remove_handler`/`track`. README calls `provider.initialize()` explicitly before `api.set_provider(provider)`. |
| `openfeature-provider-aws-ssm` 0.1.1 | `from openfeature.contrib.provider.awsssm import AwsSsmProvider, AwsSsmProviderConfig, CacheConfig` | `AwsSsmProvider(config: AwsSsmProviderConfig | None = None)`; `AwsSsmProviderConfig(config: botocore.config.Config | None, endpoint_url: str | None, enable_decryption: bool = False, cache_config: CacheConfig | None = CacheConfig())`; `CacheConfig(cache_type: "lru" | "ttl" = "lru", ttl: int = 300, size: int = 1000)` | Flag key → parameter name (leading `/` added if missing). Real async resolvers with `pip install openfeature-provider-aws-ssm[async]`. |

### Flagd provider quick reference

The flagd daemon, its flag-definition JSON and its CLI are covered by the separate **`flagd` skill**; this table is only the Python client side.

```python
from openfeature import api
from openfeature.contrib.provider.flagd import FlagdProvider
from openfeature.contrib.provider.flagd.config import ResolverType, CacheType

api.set_provider_and_wait(FlagdProvider())                                   # RPC to localhost:8013
api.set_provider_and_wait(FlagdProvider(resolver_type=ResolverType.IN_PROCESS, host="flagd", port=8015, selector="prod"))
api.set_provider_and_wait(FlagdProvider(resolver_type=ResolverType.FILE, offline_flag_source_path="flags.json"))  # no daemon
api.set_provider_and_wait(FlagdProvider(tls=True, cert_path="/etc/ssl/ca.crt", deadline_ms=1000, cache=CacheType.DISABLED))
```

| Constructor arg | Env var | Default | Resolver |
|---|---|---|---|
| `resolver_type` | `FLAGD_RESOLVER` (`rpc` / `in-process` / `file`) | `rpc` | — |
| `host` | `FLAGD_HOST` | `localhost` | all |
| `port` | `FLAGD_PORT` (rpc), `FLAGD_SYNC_PORT` then `FLAGD_PORT` (in-process/file) | 8013 rpc / 8015 in-process | all |
| `tls` / `cert_path` | `FLAGD_TLS` / `FLAGD_SERVER_CERT_PATH` | `false` / none | all |
| `deadline_ms` | `FLAGD_DEADLINE_MS` | 500 | all |
| `stream_deadline_ms` | `FLAGD_STREAM_DEADLINE_MS` | 600000 | all |
| `keep_alive_time` | `FLAGD_KEEP_ALIVE_TIME_MS` | 0 | all |
| `retry_backoff_ms` / `retry_backoff_max_ms` / `retry_grace_period` | `FLAGD_RETRY_BACKOFF_MS` / `FLAGD_RETRY_BACKOFF_MAX_MS` / `FLAGD_RETRY_GRACE_PERIOD` (seconds) | 1000 / 12000 / 5 | all |
| `cache` / `max_cache_size` | `FLAGD_CACHE` (`lru` / `disabled`) / `FLAGD_MAX_CACHE_SIZE` | `lru` / 1000 | rpc |
| `selector` | `FLAGD_SOURCE_SELECTOR` | none | in-process |
| `provider_id` | `FLAGD_PROVIDER_ID` | none | in-process |
| `offline_flag_source_path` | `FLAGD_OFFLINE_FLAG_SOURCE_PATH` | none | file (setting it with `IN_PROCESS` silently switches to `FILE`; `FILE` without it raises `AttributeError`) |
| (poll interval) | `FLAGD_OFFLINE_POLL_MS` | 5000 | file |
| `default_authority` | `FLAGD_DEFAULT_AUTHORITY` | none | all |
| `fatal_status_codes` | `FLAGD_FATAL_STATUS_CODES` (comma list) | `[]` | all |

Other details: `FlagdProvider.get_provider_hooks()` returns a `SyncMetadataHook` that enriches context with flagd sync-metadata in in-process mode (disable with `sync_metadata_disabled=True`); `timeout` (seconds) is deprecated in favour of `deadline_ms`; RPC-mode evaluations that exceed the deadline default with a gRPC `DEADLINE_EXCEEDED`; connection loss emits `PROVIDER_ERROR` and reconnects indefinitely.

---

## 11. Recipes

### FastAPI: transaction context middleware + lifespan shutdown

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from openfeature import api
from openfeature.contrib.provider.flagd import FlagdProvider
from openfeature.evaluation_context import EvaluationContext
from openfeature.transaction_context import ContextVarsTransactionContextPropagator

@asynccontextmanager
async def lifespan(app: FastAPI):
    api.set_transaction_context_propagator(ContextVarsTransactionContextPropagator())
    api.set_provider(FlagdProvider())        # non-blocking; or set_provider_and_wait to fail fast
    yield
    api.shutdown()                            # shuts provider down, clears hooks/context

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def flag_context(request: Request, call_next):
    api.set_transaction_context(EvaluationContext(
        targeting_key=request.headers.get("x-user-id"),
        attributes={"ip": request.client.host if request.client else "", "path": request.url.path},
    ))
    return await call_next(request)

@app.get("/greeting")
async def greeting():
    client = api.get_client()
    msg = await client.get_string_value_async("greeting", "Hello")      # sees the transaction context
    return {"message": msg}

@app.get("/sync-style")
def sync_route():
    return {"v2": api.get_client().get_boolean_value("v2_enabled", False)}  # also sees it (same contextvars)
```

Starlette runs each request in its own contextvars context (sync routes run in a threadpool that copies the context), so the `ContextVar` set in the middleware is visible in the route. If you prefer explicit over implicit, make a dependency that returns an `EvaluationContext` and pass it as `evaluation_context=` instead of using transaction context.

### Django middleware

```python
# myproject/flags.py
from openfeature import api
from openfeature.evaluation_context import EvaluationContext
from openfeature.transaction_context import ContextVarsTransactionContextPropagator

class OpenFeatureContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        api.set_transaction_context_propagator(ContextVarsTransactionContextPropagator())

    def __call__(self, request):
        user = getattr(request, "user", None)
        api.set_transaction_context(EvaluationContext(
            targeting_key=str(user.pk) if user is not None and user.is_authenticated else None,
            attributes={"path": request.path, "staff": bool(getattr(user, "is_staff", False))},
        ))
        return self.get_response(request)
```

Add it to `MIDDLEWARE` after `AuthenticationMiddleware`. Call `api.set_provider(...)` from `AppConfig.ready()` and `api.shutdown()` from an `atexit` handler or your process manager's shutdown hook (Django has no built-in shutdown signal).

### pytest fixture with `InMemoryProvider`

```python
# conftest.py
import pytest
from openfeature import api
from openfeature.provider.in_memory_provider import InMemoryFlag, InMemoryProvider

@pytest.fixture(autouse=True)
def _reset_openfeature():
    yield
    api.clear_providers()          # mirrors the SDK's own tests/conftest.py

@pytest.fixture
def flags():
    provider = InMemoryProvider({
        "v2_enabled": InMemoryFlag("on", {"on": True, "off": False}),
        "page_size": InMemoryFlag("small", {"small": 10, "large": 50}),
    })
    api.set_provider_and_wait(provider)   # READY before the test body runs
    return provider

def test_large_pages(flags):
    flags.update_flag("page_size", InMemoryFlag("large", {"small": 10, "large": 50}))
    assert api.get_client().get_integer_value("page_size", 1) == 50

@pytest.mark.asyncio        # requires pytest-asyncio
async def test_async(flags):
    assert await api.get_client().get_boolean_value_async("v2_enabled", False) is True
```

### Logging configuration

```python
import logging
from openfeature import api
from openfeature.hook.logging_hook import LoggingHook

logging.getLogger("openfeature").setLevel(logging.DEBUG)   # SDK internals + LoggingHook output
api.add_hooks([LoggingHook(include_evaluation_context=True)])
```

Provider errors surface as `error_code`/`error_message` on the details object rather than as exceptions, so a hook or `LoggingHook` is the only way to see them without inspecting every call.

---

## 12. Gotchas

- **Evaluation never raises; watch `error_code`.** `NOT_READY`/`FATAL` provider, missing flag, type mismatch, provider exception, hook exception: all return `default_value` with `reason=Reason.ERROR`. Check `details.error_code` (or `details.get_exception()`) when it matters.
- **`set_provider` no longer blocks (0.10.0).** Code written against <= 0.9 that evaluates right after `set_provider` now gets `PROVIDER_NOT_READY` defaults during startup. Use `set_provider_and_wait` or subscribe to `PROVIDER_READY`.
- **`set_provider_and_wait` re-raises `initialize()` failures**, so wrap it if a flag backend outage must not crash startup.
- **Int vs float vs bool are strict.** A flag holding `1` fails a `get_float_value` (`TYPE_MISMATCH`), `1.0` fails `get_integer_value`, and `True` fails `get_integer_value` even though `bool` subclasses `int`. JSON sources that produce `1` for a float flag are the usual culprit.
- **`get_object_value` returns whatever the provider returned** (a `dict` or `list`; anything else is `TYPE_MISMATCH`). It is not deep-copied or frozen; treat it as read-only.
- **Transaction context silently no-ops without a propagator.** Install `ContextVarsTransactionContextPropagator` first. Under gevent/eventlet, `contextvars` follows greenlets only with recent gevent versions that patch it; verify, or pass context explicitly per call.
- **`api.shutdown()` wipes everything**: providers, API hooks, global context, propagator. Re-register after it (e.g. between pytest modules).
- **Event handlers run on a worker thread**, possibly after `set_provider` returns; assertions in tests must wait.
- **`InMemoryFlag.state = DISABLED` does nothing** (see §6).
- **`EnvVarProvider` booleans**: `bool("false") is True`. Only an unset variable yields `False`-ish behaviour (and that is `FLAG_NOT_FOUND`, returning your default).
- **Hooks are sync-only**; `async def` hook methods are not awaited.
- **`HookHints` may be `None`** in `error`/`finally_after` when no options were passed; the SDK forwards `hints=None`. Use `(hints or {}).get(...)`.
- **Client-level context**: there is no `set_context()`; construct `OpenFeatureClient(domain, version, context=...)` or assign `client.context`.
- **`FlagMetadata` values must be scalars** (`bool | int | float | str`); the telemetry helper reads `contextId`, `flagSetId`, `version` from it.
- **Namespace-package imports**: `import openfeature.contrib` alone does nothing useful; import the leaf module (`openfeature.contrib.provider.flagd`). If two contrib packages are installed in different site-packages (e.g. a venv plus system), namespace resolution still works, but editable installs of the contrib monorepo need `uv sync` per package.
- **Python 3.9 is unsupported** since 0.9.0; the SDK uses `X | Y` unions at runtime.
- The upstream README's OFREP snippet (`OFREPProvider()`) and Unleash snippet (`event_details['provider_name']` dict access) do not match the code; `base_url` is required and `EventDetails` is a dataclass (`event_details.provider_name`).

---

## 13. When this file is silent

Official pages (paths taken from the cloned repos; only the GitHub Pages URL was actually fetched):

- SDK docs page: https://openfeature.dev/docs/reference/sdks/server/python (rendered from the SDK README)
- Getting-started tutorial (Flask + flagd): https://openfeature.dev/docs/tutorials/getting-started/python
- SDK source and CHANGELOG: https://github.com/open-feature/python-sdk (see `CHANGELOG.md` for behaviour changes such as the 0.10.0 non-blocking `set_provider`)
- Contrib providers: https://github.com/open-feature/python-sdk-contrib/tree/main/providers
- Contrib hooks: https://github.com/open-feature/python-sdk-contrib/tree/main/hooks
- PyPI: https://pypi.org/project/openfeature-sdk/ (and `openfeature-provider-*`, `openfeature-hooks-opentelemetry`)
- Generated API docs: https://open-feature.github.io/python-sdk/ returned **HTTP 404** on 2026-09-21; there is no published API-reference site. Read the source instead (it is small: `openfeature/` is about 15 files).
- Spec: https://openfeature.dev/specification/ (sections 1 flag evaluation, 2 providers, 3 evaluation context, 4 hooks, 5 events, 6 tracking, Appendix D observability)

Grep recipes on a fresh clone (`git clone https://github.com/open-feature/python-sdk && cd python-sdk`):

```bash
grep -n "    def \|    async def " openfeature/client.py          # every client method + signature line
grep -n "^def \|^__all__" openfeature/api.py                       # the whole public api module
grep -rn "class .*Error(OpenFeatureError)" openfeature/exception.py
grep -rn "def emit_\|def attach\|def initialize\|def shutdown" openfeature/provider/__init__.py
grep -rn "ProviderEvent\.\|ProviderStatus\." openfeature/provider/_registry.py   # status/event transitions
grep -rn "def test_" tests/test_api.py | grep -i "wait\|ready\|handler"          # readiness semantics
sed -n 1,40p CHANGELOG.md                                          # breaking changes first

# contrib
git clone https://github.com/open-feature/python-sdk-contrib && cd python-sdk-contrib
cat .release-please-manifest.json                                  # current version of every package
grep -n "ENV_VAR_\|DEFAULT_" providers/openfeature-provider-flagd/src/openfeature/contrib/provider/flagd/config.py
grep -rn "^class \|    def __init__" providers/*/src/openfeature/contrib/provider/*/__init__.py providers/*/src/openfeature/contrib/provider/*/provider.py
grep -rn "_async" providers/*/src                                  # which providers are really async
```

Installed-version check: `python -c "import openfeature.version as v; print(v.__version__)"` or `pip show openfeature-sdk openfeature-provider-flagd`.
