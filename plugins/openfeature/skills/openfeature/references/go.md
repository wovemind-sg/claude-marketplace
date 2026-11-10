# OpenFeature Go SDK — deep-dive reference

Verified against source on 2026-09-21.

| Component | Version | Import path |
|---|---|---|
| go-sdk | **v1.18.0** (commit `213d8f7`, released 2026-07-31, requires Go 1.26) | `github.com/open-feature/go-sdk/openfeature` |
| flagd provider | 0.6.0 | `github.com/open-feature/go-sdk-contrib/providers/flagd/pkg` (package `flagd`) |
| OFREP provider | 0.1.7 | `github.com/open-feature/go-sdk-contrib/providers/ofrep` |
| from-env provider | 0.1.6 | `github.com/open-feature/go-sdk-contrib/providers/from-env/pkg` |
| OpenTelemetry hooks | 0.3.7 | `github.com/open-feature/go-sdk-contrib/hooks/open-telemetry/pkg` (package `otel`) |
| validator hook | 0.1.7 | `github.com/open-feature/go-sdk-contrib/hooks/validator/pkg/validator` |
| codereadiness hook | 0.1.1 | `github.com/open-feature/go-sdk-contrib/hooks/codereadiness` |

```sh
go get github.com/open-feature/go-sdk/openfeature@v1.18.0
go get github.com/open-feature/go-sdk-contrib/providers/flagd        # only if you use flagd
go get github.com/open-feature/go-sdk-contrib/hooks/open-telemetry   # only if you use the OTel hooks
```

Breaking change in 1.18.0: the long-deprecated `github.com/open-feature/go-sdk/pkg/openfeature` alias package was deleted. If a codebase still imports it, rewrite the import to `github.com/open-feature/go-sdk/openfeature` (the API is identical) and run `go mod tidy`.

## Contents

1. [Minimal program](#1-minimal-program)
2. [Evaluation API](#2-evaluation-api)
3. [Evaluation context and transaction context](#3-evaluation-context-and-transaction-context)
4. [Hooks](#4-hooks)
5. [Events](#5-events)
6. [Provider lifecycle, states and writing a provider](#6-provider-lifecycle-states-and-writing-a-provider)
7. [In-memory provider, NoopProvider, TestProvider, isolated API](#7-in-memory-provider-noopprovider-testprovider-isolated-api)
8. [Multi-provider](#8-multi-provider)
9. [Tracking](#9-tracking)
10. [Logging and telemetry helpers](#10-logging-and-telemetry-helpers)
11. [Contrib providers and hooks](#11-contrib-providers-and-hooks)
12. [Integration recipes](#12-integration-recipes)
13. [Gotchas](#13-gotchas)
14. [When this file is silent](#14-when-this-file-is-silent)

---

## 1. Minimal program

The SDK is a process-wide singleton (`openfeature.SetProvider`, `openfeature.NewClient`, ...). Provider initialisation is **asynchronous** unless you use one of the `...AndWait` functions; until the provider reports `READY`, every evaluation returns the default value with error code `PROVIDER_NOT_READY`.

```go
package main

import (
	"context"
	"log"

	"github.com/open-feature/go-sdk/openfeature"
	"github.com/open-feature/go-sdk/openfeature/memprovider"
)

func main() {
	provider := memprovider.NewInMemoryProvider(map[string]memprovider.InMemoryFlag{
		"new-checkout": {
			Key:            "new-checkout",
			State:          memprovider.Enabled,
			DefaultVariant: "on",
			Variants:       map[string]any{"on": true, "off": false},
		},
	})

	// Blocks until Init finishes (or fails). Prefer this at startup.
	if err := openfeature.SetProviderAndWait(provider); err != nil {
		log.Fatalf("provider init failed: %v", err)
	}
	defer openfeature.Shutdown()

	client := openfeature.NewDefaultClient()          // bound to the default provider
	evalCtx := openfeature.NewEvaluationContext("user-123", map[string]any{"plan": "pro"})

	enabled, err := client.BooleanValue(context.Background(), "new-checkout", false, evalCtx)
	if err != nil {
		log.Printf("evaluation error (default returned): %v", err)
	}
	log.Printf("new-checkout=%v", enabled)
}
```

### Provider setters (all in package `openfeature`)

| Function | Blocks until ready? | Notes |
|---|---|---|
| `SetProvider(p FeatureProvider) error` | No | Returns immediately; only errors for nil provider or a provider already bound to another API instance. Init runs in a goroutine. |
| `SetProviderAndWait(p FeatureProvider) error` | Yes | Returns the `Init` error wrapped as `failed to initialize default provider %q: ...`. |
| `SetProviderWithContext(ctx, p) error` | No | Passes `ctx` to `InitWithContext` if the provider implements `ContextAwareStateHandler`. A cancelled ctx does **not** make this return an error (CHANGELOG 1.18.0 doc fix). |
| `SetProviderWithContextAndWait(ctx, p) error` | Yes | Returns `ctx.Err()` if the context ends first. |
| `SetNamedProvider(domain, p)` / `SetNamedProviderAndWait(domain, p)` | No / Yes | Bind a provider to a *domain*. Clients created with `NewClient(domain)` use it. |
| `SetNamedProviderWithContext(ctx, domain, p)` / `SetNamedProviderWithContextAndWait(ctx, domain, p)` | No / Yes | Context-aware variants. |

Clients:

```go
client := openfeature.NewDefaultClient()      // *Client, default provider (domain "")
billing := openfeature.NewClient("billing")   // *Client, provider set via SetNamedProvider("billing", ...)
                                              // falls back to the default provider if no "billing" provider exists
client.Metadata().Domain()                    // "" or "billing"; Metadata().Name() is deprecated
client.State()                                // openfeature.State of the bound provider
```

Replacing a provider: calling `SetProvider` again initialises the new provider and calls `Shutdown` on the old one in a goroutine, unless the old provider is still bound to another domain (spec 1.1.2.2 / 1.1.2.3).

`func Shutdown()` (no return value — `_ = openfeature.Shutdown()` is a compile error) / `func ShutdownWithContext(ctx context.Context) error` shuts down **all** providers and resets the API: hooks, event handlers, providers and evaluation context are all dropped, and a fresh singleton is installed. Only call it when the process is exiting.

---

## 2. Evaluation API

All evaluation methods live on `*openfeature.Client` and take a `context.Context` first (request cancellation, transaction context, OTel span) and an `EvaluationContext` fourth (targeting data — do not confuse the two).

### Signatures (copied from `client.go`)

```go
// value + error
func (c *Client) BooleanValue(ctx context.Context, flag string, defaultValue bool,    evalCtx EvaluationContext, options ...Option) (bool, error)
func (c *Client) StringValue (ctx context.Context, flag string, defaultValue string,  evalCtx EvaluationContext, options ...Option) (string, error)
func (c *Client) FloatValue  (ctx context.Context, flag string, defaultValue float64, evalCtx EvaluationContext, options ...Option) (float64, error)
func (c *Client) IntValue    (ctx context.Context, flag string, defaultValue int64,   evalCtx EvaluationContext, options ...Option) (int64, error)
func (c *Client) ObjectValue (ctx context.Context, flag string, defaultValue any,     evalCtx EvaluationContext, options ...Option) (any, error)

// full details + error
func (c *Client) BooleanValueDetails(...) (BooleanEvaluationDetails, error)   // = GenericEvaluationDetails[bool]
func (c *Client) StringValueDetails (...) (StringEvaluationDetails, error)    // = GenericEvaluationDetails[string]
func (c *Client) FloatValueDetails  (...) (FloatEvaluationDetails, error)     // = GenericEvaluationDetails[float64]
func (c *Client) IntValueDetails    (...) (IntEvaluationDetails, error)       // = GenericEvaluationDetails[int64]
func (c *Client) ObjectValueDetails (...) (InterfaceEvaluationDetails, error) // = GenericEvaluationDetails[any]

// value only — errors are swallowed, default returned
func (c *Client) Boolean(...) bool
func (c *Client) String (...) string
func (c *Client) Float  (...) float64
func (c *Client) Int    (...) int64
func (c *Client) Object (...) any
```

### Details struct

```go
type GenericEvaluationDetails[T any] struct {
	Value T
	EvaluationDetails
}
type EvaluationDetails struct {
	FlagKey  string
	FlagType Type            // Boolean | String | Float | Int | Object  (String() gives "bool","string","float","int","object")
	ResolutionDetail
}
type ResolutionDetail struct {
	Variant      string
	Reason       Reason
	ErrorCode    ErrorCode
	ErrorMessage string
	FlagMetadata FlagMetadata  // map[string]any, never nil (empty map on early errors)
}
```

`FlagMetadata` has typed accessors that return an error on missing key or wrong type: `GetString(key)`, `GetBool(key)`, `GetInt(key) (int64, error)` (accepts any signed int width), `GetFloat(key) (float64, error)` (accepts float32/float64).

### Reason and ErrorCode constants

| `Reason` | value | | `ErrorCode` | value |
|---|---|---|---|---|
| `DefaultReason` | `DEFAULT` | | `ProviderNotReadyCode` | `PROVIDER_NOT_READY` |
| `TargetingMatchReason` | `TARGETING_MATCH` | | `ProviderFatalCode` | `PROVIDER_FATAL` |
| `SplitReason` | `SPLIT` | | `FlagNotFoundCode` | `FLAG_NOT_FOUND` |
| `DisabledReason` | `DISABLED` | | `ParseErrorCode` | `PARSE_ERROR` |
| `StaticReason` | `STATIC` | | `TypeMismatchCode` | `TYPE_MISMATCH` |
| `CachedReason` | `CACHED` | | `TargetingKeyMissingCode` | `TARGETING_KEY_MISSING` |
| `UnknownReason` | `UNKNOWN` | | `InvalidContextCode` | `INVALID_CONTEXT` |
| `ErrorReason` | `ERROR` | | `GeneralCode` | `GENERAL` |

Inspect failures through `details.ErrorCode`, not by type-asserting the error. For provider errors the client returns `fmt.Errorf("error code: %w", errors.New("FLAG_NOT_FOUND: <msg>"))` — `ProviderResolutionDetail.Error()` rebuilds the error with `errors.New`, so `errors.As(err, &openfeature.ResolutionError{})` does **not** match and the provider's wrapped original error is not reachable from the client. The only `ResolutionError` values returned directly are the short-circuit sentinels `openfeature.ProviderNotReadyError` and `openfeature.ProviderFatalError`, which do work with `errors.Is`.

```go
details, err := client.BooleanValueDetails(ctx, "new-checkout", false, evalCtx)
if err != nil {
	// err.Error() == "error code: FLAG_NOT_FOUND: flag for key new-checkout not found"
	switch details.ErrorCode {
	case openfeature.FlagNotFoundCode:     // flag missing in provider
	case openfeature.TypeMismatchCode:     // flag exists with a different type
	case openfeature.ProviderNotReadyCode: // evaluated before Init finished; errors.Is(err, openfeature.ProviderNotReadyError)
	}
}
```

### Per-invocation options

```go
type Option func(*EvaluationOptions)
func WithHooks(hooks ...Hook) Option
func WithHookHints(hookHints HookHints) Option   // hints := openfeature.NewHookHints(map[string]any{"k": "v"})

v := client.Boolean(ctx, "flag", false, evalCtx,
	openfeature.WithHooks(myHook{}),
	openfeature.WithHookHints(openfeature.NewHookHints(map[string]any{"trace": true})))
```

### Evaluation pipeline (what `Client.evaluate` actually does)

1. Reject non-UTF-8 flag keys with `PARSE_ERROR`.
2. Snapshot provider, API hooks and API context for this domain (so a concurrent `SetProvider` cannot change the provider mid-evaluation).
3. Merge evaluation contexts (section 3), concatenate hooks `API → Client → Invocation → Provider`.
4. If the provider is not `NoopProvider` and `client.State()` is `NOT_READY` or `FATAL`, short-circuit: error hooks, then finally hooks, default returned with `PROVIDER_NOT_READY` / `PROVIDER_FATAL` (spec 1.7.x).
5. Run `Before` hooks (forward order); an error aborts with `before hook: ...`.
6. Call the provider's typed `*Evaluation` method with a `FlattenedContext` (attributes map plus `"targetingKey"`).
7. Provider `ResolutionError` → error hooks, `Reason` forced to `ERROR`, default returned.
8. Run `After` hooks (reverse order), then `Finally` hooks (reverse order, always, via `defer`).
9. Typed getters then assert the value type; a mismatch returns the default with `TYPE_MISMATCH`.

---

## 3. Evaluation context and transaction context

`EvaluationContext` is immutable; construct it, never mutate:

```go
type EvaluationContext struct { /* unexported */ }
func NewEvaluationContext(targetingKey string, attributes map[string]any) EvaluationContext
func NewTargetlessEvaluationContext(attributes map[string]any) EvaluationContext
func (e EvaluationContext) TargetingKey() string
func (e EvaluationContext) Attribute(key string) any
func (e EvaluationContext) Attributes() map[string]any   // returns a copy
const TargetingKey = "targetingKey"                      // key used in FlattenedContext
```

Both constructors copy the attribute map. `openfeature.EvaluationContext{}` (zero value) is the idiom for "no context".

### Where context can be set

| Level | API |
|---|---|
| API (global) | `openfeature.SetEvaluationContext(ec)` |
| Transaction (per `context.Context`) | `ctx = openfeature.WithTransactionContext(ctx, ec)`; read back with `openfeature.TransactionContext(ctx)`; add to existing with `openfeature.MergeTransactionContext(ctx, ec)` (the new `ec` wins on conflicts) |
| Client | `client.SetEvaluationContext(ec)`; read with `client.EvaluationContext()` |
| Invocation | the `evalCtx` argument of every evaluation method |
| Before hooks | return a `*EvaluationContext` from `Before` |

### Merge order (spec 3.2.3)

`API (lowest) → transaction → client → invocation → before hooks (highest)`. Implemented in `client.go` as `mergeContexts(evalCtx, c.evaluationContext, TransactionContext(ctx), globalEvalCtx)` where earlier arguments win. Attributes are merged key by key; the targeting key is taken from the highest-precedence context that has a non-empty one. Tracking (`client.Track`) uses the same four-level merge.

```go
openfeature.SetEvaluationContext(openfeature.NewTargetlessEvaluationContext(map[string]any{"region": "eu"}))
ctx := openfeature.WithTransactionContext(context.Background(),
	openfeature.NewEvaluationContext("user-42", map[string]any{"tier": "gold"}))
client.SetEvaluationContext(openfeature.NewTargetlessEvaluationContext(map[string]any{"service": "checkout"}))

// provider sees: targetingKey=user-42, region=eu, tier=gold, service=checkout, beta=true
v := client.Boolean(ctx, "flag", false, openfeature.NewTargetlessEvaluationContext(map[string]any{"beta": true}))
```

---

## 4. Hooks

```go
type Hook interface {
	Before (ctx context.Context, hookContext HookContext, hookHints HookHints) (*EvaluationContext, error)
	After  (ctx context.Context, hookContext HookContext, flagEvaluationDetails InterfaceEvaluationDetails, hookHints HookHints) error
	Error  (ctx context.Context, hookContext HookContext, err error, hookHints HookHints)
	Finally(ctx context.Context, hookContext HookContext, flagEvaluationDetails InterfaceEvaluationDetails, hookHints HookHints)
}
```

Embed `openfeature.UnimplementedHook` to get no-op defaults for stages you do not override.

`HookContext` accessors: `FlagKey() string`, `FlagType() Type`, `DefaultValue() any`, `ClientMetadata() ClientMetadata` (→ `.Domain()`), `ProviderMetadata() Metadata` (→ `.Name`), `EvaluationContext() EvaluationContext`. `openfeature.NewHookContext(...)` exists for unit-testing hooks. `HookHints.Value(key) any` reads hints.

### Registration and order (spec 4.4.2)

| Level | Register |
|---|---|
| API | `openfeature.AddHooks(h1, h2)` |
| Client | `client.AddHooks(h)` |
| Invocation | `openfeature.WithHooks(h)` option |
| Provider | returned from the provider's `Hooks()` method |

`Before` runs `API → Client → Invocation → Provider`, in registration order within a level. `After`, `Error` and `Finally` run in **reverse** (`Provider → Invocation → Client → API`); 1.17.1 fixed same-level reverse order. A `Before` error stops remaining `Before` hooks and returns the default (spec 4.4.6/4.4.7); an `After` error is reported through `Error` hooks. `Finally` always runs. A `*EvaluationContext` returned by `Before` is merged on top of the current context and is visible to later hooks and to the provider.

### Complete example: timing hook

```go
package flags

import (
	"context"
	"log/slog"
	"time"

	"github.com/open-feature/go-sdk/openfeature"
)

type timingKey struct{}

// TimingHook logs how long each evaluation took and whether it errored.
type TimingHook struct {
	openfeature.UnimplementedHook
	Logger *slog.Logger
}

func (h TimingHook) Before(ctx context.Context, hc openfeature.HookContext, _ openfeature.HookHints) (*openfeature.EvaluationContext, error) {
	// Hooks cannot mutate ctx for later stages; stash state in the hook via hints or a sync.Map if needed.
	// Here we attach a start time to the evaluation context attributes instead (visible to the provider too).
	ec := openfeature.NewTargetlessEvaluationContext(map[string]any{"_evalStartedAt": time.Now().UnixNano()})
	return &ec, nil
}

func (h TimingHook) Finally(ctx context.Context, hc openfeature.HookContext, d openfeature.InterfaceEvaluationDetails, _ openfeature.HookHints) {
	start, _ := hc.EvaluationContext().Attribute("_evalStartedAt").(int64)
	h.Logger.InfoContext(ctx, "flag evaluated",
		"flag", hc.FlagKey(),
		"type", hc.FlagType().String(),
		"provider", hc.ProviderMetadata().Name,
		"domain", hc.ClientMetadata().Domain(),
		"reason", string(d.Reason),
		"variant", d.Variant,
		"error_code", string(d.ErrorCode),
		"duration", time.Since(time.Unix(0, start)))
}

func (h TimingHook) Error(ctx context.Context, hc openfeature.HookContext, err error, _ openfeature.HookHints) {
	h.Logger.ErrorContext(ctx, "flag evaluation failed", "flag", hc.FlagKey(), "err", err)
}

var _ openfeature.Hook = TimingHook{}
```

Register with `openfeature.AddHooks(flags.TimingHook{Logger: slog.Default()})`.

---

## 5. Events

```go
const (
	ProviderReady        EventType = "PROVIDER_READY"
	ProviderConfigChange EventType = "PROVIDER_CONFIGURATION_CHANGED"
	ProviderStale        EventType = "PROVIDER_STALE"
	ProviderError        EventType = "PROVIDER_ERROR"
)

type EventCallback *func(details EventDetails)      // note: pointer to func (needed so RemoveHandler can compare)
type EventDetails struct {
	ProviderName string
	ProviderEventDetails
}
type ProviderEventDetails struct {
	Message       string
	FlagChanges   []string
	EventMetadata map[string]any
	ErrorCode     ErrorCode
}

func openfeature.AddHandler(eventType EventType, callback EventCallback)     // API level: every provider
func openfeature.RemoveHandler(eventType EventType, callback EventCallback)
func (c *Client) AddHandler(eventType EventType, callback EventCallback)     // client level: only its domain's provider
func (c *Client) RemoveHandler(eventType EventType, callback EventCallback)
```

```go
onReady := func(d openfeature.EventDetails) {
	log.Printf("provider %s ready: %s", d.ProviderName, d.Message)
}
openfeature.AddHandler(openfeature.ProviderReady, &onReady)

onChange := func(d openfeature.EventDetails) {
	log.Printf("flags changed: %v", d.FlagChanges)   // may be empty depending on provider
}
client.AddHandler(openfeature.ProviderConfigChange, &onChange)
```

Behaviour verified in `event_executor.go`:

- Each callback runs on **its own goroutine** (`go func()`), with a `recover()` that logs via `slog.Info("recovered from a panic")`. Handlers must be goroutine-safe and must not assume ordering relative to other handlers.
- Provider state is written **before** handlers are invoked (spec 5.3.5; fixed in 1.18.0), so `client.State()` inside a `PROVIDER_READY` handler already returns `ReadyState`.
- If you register a handler when the provider is already in the matching state (`READY`/`ERROR`/`STALE`), the handler fires immediately with a message such as `"provider is in ready state"`.
- The `EventDetails` handed to callbacks carries `Message`, `FlagChanges` and `EventMetadata` — the `ErrorCode` field is **not** copied through by `executeHandler`. Do not rely on `d.ErrorCode` inside a handler in 1.18.0.
- The SDK emits `PROVIDER_READY` or `PROVIDER_ERROR` itself after `Init`; providers that want to emit later events implement `EventHandler` (see section 6). The listener goroutine starts lazily the first time an `EventHandler` provider is registered.

---

## 6. Provider lifecycle, states and writing a provider

### Interfaces

```go
type FeatureProvider interface {
	Metadata() Metadata                                   // Metadata{Name string}
	BooleanEvaluation(ctx context.Context, flag string, defaultValue bool,    flatCtx FlattenedContext) BoolResolutionDetail
	StringEvaluation (ctx context.Context, flag string, defaultValue string,  flatCtx FlattenedContext) StringResolutionDetail
	FloatEvaluation  (ctx context.Context, flag string, defaultValue float64, flatCtx FlattenedContext) FloatResolutionDetail
	IntEvaluation    (ctx context.Context, flag string, defaultValue int64,   flatCtx FlattenedContext) IntResolutionDetail
	ObjectEvaluation (ctx context.Context, flag string, defaultValue any,     flatCtx FlattenedContext) InterfaceResolutionDetail
	Hooks() []Hook
}

// optional
type StateHandler interface {
	Init(evaluationContext EvaluationContext) error
	Shutdown()
}
type ContextAwareStateHandler interface {          // preferred for network providers
	StateHandler
	InitWithContext(ctx context.Context, evaluationContext EvaluationContext) error
	ShutdownWithContext(ctx context.Context) error
}
type EventHandler interface { EventChannel() <-chan Event }   // Event{ProviderName string; EventType; ProviderEventDetails}
type Tracker interface {
	Track(ctx context.Context, trackingEventName string, evaluationContext EvaluationContext, details TrackingEventDetails)
}
```

`FlattenedContext` is `map[string]any` containing the merged attributes plus `openfeature.TargetingKey` (`"targetingKey"`) when set.

### Resolution detail types

```go
type GenericResolutionDetail[T any] struct {
	Value T
	ProviderResolutionDetail
}
type BoolResolutionDetail      = GenericResolutionDetail[bool]
type StringResolutionDetail    = GenericResolutionDetail[string]
type FloatResolutionDetail     = GenericResolutionDetail[float64]
type IntResolutionDetail       = GenericResolutionDetail[int64]
type InterfaceResolutionDetail = GenericResolutionDetail[any]

type ProviderResolutionDetail struct {
	ResolutionError ResolutionError   // zero value == no error
	Reason          Reason
	Variant         string
	FlagMetadata    FlagMetadata
}
```

`ResolutionError` has unexported fields; build one with a constructor: `NewFlagNotFoundResolutionError(msg)`, `NewTypeMismatchResolutionError(msg)`, `NewParseErrorResolutionError(msg, errs ...error)`, `NewTargetingKeyMissingResolutionError(msg)`, `NewInvalidContextResolutionError(msg)`, `NewProviderNotReadyResolutionError(msg)`, `NewProviderFatalResolutionError(msg)`, `NewGeneralResolutionError(msg, errs ...error)`. The two variadic ones keep the original error behind `Unwrap()`, but note this only helps code that inspects the `ResolutionError` inside the provider or in the multi-provider; the client re-creates the error with `errors.New` (see section 2), and `Error()` deliberately omits the original message to avoid leaking internals.

To fail `Init` with a specific code (e.g. so the SDK enters `FATAL`), return `&openfeature.ProviderInitError{ErrorCode: openfeature.ProviderFatalCode, Message: "bad credentials"}`.

### States (spec 1.7.x)

`NotReadyState "NOT_READY"`, `ReadyState "READY"`, `ErrorState "ERROR"`, `StaleState "STALE"`, `FatalState "FATAL"`. The SDK derives state from events: `PROVIDER_READY`/`PROVIDER_CONFIGURATION_CHANGED` → READY, `PROVIDER_STALE` → STALE, `PROVIDER_ERROR` → ERROR, or FATAL if `ErrorCode == ProviderFatalCode`. Read it via `client.State()`. A provider without `StateHandler` is treated as READY immediately.

### Minimal custom provider (compiles as-is)

```go
package mapprovider

import (
	"context"
	"fmt"
	"sync"

	"github.com/open-feature/go-sdk/openfeature"
)

// Provider serves flags from a map and emits PROVIDER_CONFIGURATION_CHANGED on Update.
type Provider struct {
	mu     sync.RWMutex
	flags  map[string]any
	events chan openfeature.Event
}

func New(flags map[string]any) *Provider {
	return &Provider{flags: flags, events: make(chan openfeature.Event, 8)}
}

func (p *Provider) Metadata() openfeature.Metadata { return openfeature.Metadata{Name: "map-provider"} }
func (p *Provider) Hooks() []openfeature.Hook       { return nil }

// StateHandler
func (p *Provider) Init(_ openfeature.EvaluationContext) error { return nil }
func (p *Provider) Shutdown()                                  { close(p.events) }

// EventHandler
func (p *Provider) EventChannel() <-chan openfeature.Event { return p.events }

func (p *Provider) Update(flags map[string]any) {
	p.mu.Lock()
	p.flags = flags
	p.mu.Unlock()
	p.events <- openfeature.Event{
		ProviderName: p.Metadata().Name,
		EventType:    openfeature.ProviderConfigChange,
		ProviderEventDetails: openfeature.ProviderEventDetails{Message: "flags replaced"},
	}
}

func resolve[T any](p *Provider, flag string, def T) openfeature.GenericResolutionDetail[T] {
	p.mu.RLock()
	raw, ok := p.flags[flag]
	p.mu.RUnlock()
	if !ok {
		return openfeature.GenericResolutionDetail[T]{Value: def, ProviderResolutionDetail: openfeature.ProviderResolutionDetail{
			ResolutionError: openfeature.NewFlagNotFoundResolutionError(fmt.Sprintf("flag %q not found", flag)),
			Reason:          openfeature.ErrorReason,
		}}
	}
	v, ok := raw.(T)
	if !ok {
		return openfeature.GenericResolutionDetail[T]{Value: def, ProviderResolutionDetail: openfeature.ProviderResolutionDetail{
			ResolutionError: openfeature.NewTypeMismatchResolutionError(fmt.Sprintf("flag %q is %T", flag, raw)),
			Reason:          openfeature.ErrorReason,
		}}
	}
	return openfeature.GenericResolutionDetail[T]{Value: v, ProviderResolutionDetail: openfeature.ProviderResolutionDetail{
		Reason:       openfeature.StaticReason,
		Variant:      "static",
		FlagMetadata: openfeature.FlagMetadata{"source": "map"},
	}}
}

func (p *Provider) BooleanEvaluation(_ context.Context, flag string, def bool, _ openfeature.FlattenedContext) openfeature.BoolResolutionDetail {
	return resolve(p, flag, def)
}
func (p *Provider) StringEvaluation(_ context.Context, flag string, def string, _ openfeature.FlattenedContext) openfeature.StringResolutionDetail {
	return resolve(p, flag, def)
}
func (p *Provider) FloatEvaluation(_ context.Context, flag string, def float64, _ openfeature.FlattenedContext) openfeature.FloatResolutionDetail {
	return resolve(p, flag, def)
}
func (p *Provider) IntEvaluation(_ context.Context, flag string, def int64, _ openfeature.FlattenedContext) openfeature.IntResolutionDetail {
	return resolve(p, flag, def)
}
func (p *Provider) ObjectEvaluation(_ context.Context, flag string, def any, _ openfeature.FlattenedContext) openfeature.InterfaceResolutionDetail {
	return resolve(p, flag, def)
}

var (
	_ openfeature.FeatureProvider = (*Provider)(nil)
	_ openfeature.StateHandler    = (*Provider)(nil)
	_ openfeature.EventHandler    = (*Provider)(nil)
)
```

Use a **pointer** receiver and register the pointer: the SDK tracks provider identity by pointer to enforce spec 1.8.4 (one provider instance may not be bound to two API instances) and to decide whether to shut down an old provider that is still bound to another domain. Value-type providers (like `memprovider.InMemoryProvider`) are allowed but skip that tracking.

---

## 7. In-memory provider, NoopProvider, TestProvider, isolated API

### `memprovider` (ships with the SDK)

```go
import "github.com/open-feature/go-sdk/openfeature/memprovider"

type InMemoryFlag struct {
	Key              string
	State            State            // memprovider.Enabled | memprovider.Disabled
	DefaultVariant   string
	Variants         map[string]any
	ContextEvaluator ContextEvaluator // *func(this InMemoryFlag, flatCtx openfeature.FlattenedContext) (any, openfeature.ProviderResolutionDetail)
}
func NewInMemoryProvider(from map[string]InMemoryFlag) InMemoryProvider   // value type, implements FeatureProvider + Tracker
```

- `Disabled` flags return the default with `Reason: DISABLED`.
- Without a `ContextEvaluator`, `Variants[DefaultVariant]` is returned with `Reason: STATIC`.
- `ContextEvaluator` is a **pointer to a func** — declare `fn := func(...)...; ContextEvaluator: &fn`.
- Ints in `Variants` are coerced to `int64` and int/float32 to `float64` (1.17.2), so `Variants: map[string]any{"ten": 10}` works with `IntValue`. Unsigned ints are a `TYPE_MISMATCH`.
- Unknown key → `FLAG_NOT_FOUND`; wrong type → `TYPE_MISMATCH`.

```go
targeted := func(f memprovider.InMemoryFlag, fc openfeature.FlattenedContext) (any, openfeature.ProviderResolutionDetail) {
	if fc["plan"] == "pro" {
		return f.Variants["on"], openfeature.ProviderResolutionDetail{Reason: openfeature.TargetingMatchReason, Variant: "on"}
	}
	return f.Variants[f.DefaultVariant], openfeature.ProviderResolutionDetail{Reason: openfeature.DefaultReason, Variant: f.DefaultVariant}
}
flags := map[string]memprovider.InMemoryFlag{
	"pro-dashboard": {Key: "pro-dashboard", State: memprovider.Enabled, DefaultVariant: "off",
		Variants: map[string]any{"on": true, "off": false}, ContextEvaluator: &targeted},
}
```

### `NoopProvider`

`openfeature.NoopProvider{}` is the default provider before you set one. It returns the default value with `Variant: "default-variant"`, `Reason: DEFAULT`, never errors, and is exempt from the NOT_READY short-circuit.

### `testing.TestProvider` (per-test flags, parallel-safe)

```go
import oftest "github.com/open-feature/go-sdk/openfeature/testing"

tp := oftest.NewTestProvider()
_ = openfeature.SetProviderAndWait(tp)   // once, e.g. in TestMain

func TestCheckout(t *testing.T) {
	ctx := tp.UsingFlags(t, map[string]memprovider.InMemoryFlag{ /* ... */ })  // auto-cleanup via t.Cleanup
	// evaluations on this goroutine resolve against these flags; pass ctx to evaluations made from other goroutines
	got := openfeature.NewDefaultClient().Boolean(ctx, "my_flag", false, openfeature.EvaluationContext{})
}
```

It panics with `unable to detect test name` if an evaluation happens without a preceding `UsingFlags` on that goroutine (or without the returned ctx).

### `isolated.NewAPI()` — non-singleton instances (experimental, 1.18.0)

```go
import "github.com/open-feature/go-sdk/openfeature/isolated"

api := isolated.NewAPI()                       // *openfeature.EvaluationAPI, independent of the global singleton
defer api.Shutdown(ctx)
err := api.SetProviderAndWait(ctx, provider)   // EvaluationAPI methods take ctx first
err  = api.SetProviderAndWait(ctx, other, openfeature.WithDomain("billing"))
client := api.NewClient(openfeature.WithDomain("billing"))
api.AddHooks(h); api.AddHandler(openfeature.ProviderReady, &cb); api.SetEvaluationContext(ec)
```

Use it for dependency injection, multi-tenant processes or test isolation (each test gets its own API, no global reset). A given provider *pointer* can be bound to only one API instance at a time.

---

## 8. Multi-provider

Use `github.com/open-feature/go-sdk/openfeature/multi` (in the SDK, experimental). The contrib module `providers/multi-provider` (0.0.5) is **deprecated** in favour of it.

```go
import "github.com/open-feature/go-sdk/openfeature/multi"

mp, err := multi.NewProvider(
	multi.StrategyFirstMatch,
	multi.WithProvider("new-vendor", newVendorProvider),        // evaluated first
	multi.WithProvider("legacy", legacyProvider, legacyHook),   // optional per-provider hooks
	multi.WithGlobalHooks(auditHook),
	multi.WithLogger(slog.Default()),                            // logs discarded by default
)
if err != nil { return err }
openfeature.SetProviderAndWait(mp)
```

| Strategy constant | Behaviour |
|---|---|
| `multi.StrategyFirstMatch` | Sequential. Skip a provider only on `FLAG_NOT_FOUND`; any other error stops and returns the default. |
| `multi.StrategyFirstSuccess` | Sequential. First non-error result wins; errors of any kind move to the next provider. |
| `multi.StrategyComparison` | Parallel. All non-`FLAG_NOT_FOUND` results must agree, otherwise `WithFallbackProvider(p)` is consulted (result reason `multi.ReasonAggregatedFallback`) or the default is returned. Non-`comparable` object values need `WithCustomComparator(func(values []any) bool)`. |
| `multi.StrategyCustom` | Supply `multi.WithCustomStrategy(func(providers []multi.NamedProvider) multi.StrategyFn[multi.FlagTypes])`; helpers `multi.Evaluate` and `multi.BuildDefaultResult` are exported for this. |

`*multi.Provider` implements `StateHandler`, `ContextAwareStateHandler`, `EventHandler` (forwards child `PROVIDER_CONFIGURATION_CHANGED` since 1.17.2) and `Tracker`; `Status()` aggregates child states. Result `FlagMetadata` includes `multi.MetadataSuccessfulProviderName`, `multi.MetadataStrategyUsed`, `multi.MetadataFallbackUsed`, etc.

---

## 9. Tracking

```go
func (c *Client) Track(ctx context.Context, trackingEventName string, evalCtx EvaluationContext, details TrackingEventDetails)

func NewTrackingEventDetails(value float64) TrackingEventDetails
func (t TrackingEventDetails) Add(key string, value any) TrackingEventDetails   // chainable
func (t TrackingEventDetails) Value() float64
func (t TrackingEventDetails) Attributes() map[string]any
func (t TrackingEventDetails) Attribute(key string) any

client.Track(ctx, "purchase-completed", evalCtx,
	openfeature.NewTrackingEventDetails(99.77).Add("currencyCode", "USD"))
```

The merged evaluation context (same four-level merge as evaluation) is passed to the provider's `Track`. If the provider does not implement `Tracker`, the call is a silent no-op. `memprovider.InMemoryProvider` records events internally (not exposed via a getter).

---

## 10. Logging and telemetry helpers

The SDK itself is almost silent: per spec it does not log during evaluation. The only internal logging is `slog.Info` for a recovered handler panic and an internal event-executor bug guard. There is no `SetLogger`. Use hooks:

```go
import "github.com/open-feature/go-sdk/openfeature/hooks"

logger := slog.New(slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{Level: slog.LevelDebug}))
openfeature.AddHooks(hooks.NewLoggingHook(false /* includeEvaluationContext */, logger))
```

`hooks.LoggingHook` logs `Before`/`After` at DEBUG and `Error` at ERROR with attributes `domain`, `provider_name`, `flag_key`, `default_value`, `reason`, `variant`, `value`, `error_message`, `stage`; `Finally` is a no-op. Pass `true` to also log `targeting_key` and `attributes` (be careful with PII).

`github.com/open-feature/go-sdk/openfeature/telemetry` provides `telemetry.CreateEvaluationEvent(hookContext, details) EvaluationEvent` for building an OTel-semconv `feature_flag.evaluation` log record from inside a `Finally` hook (attribute keys exported as `telemetry.FlagKey`, `telemetry.ResultReasonKey`, `telemetry.ProviderNameKey`, ...).

---

## 11. Contrib providers and hooks

### Providers (`github.com/open-feature/go-sdk-contrib/providers/...`)

| Provider | Import path | Constructor | Notes |
|---|---|---|---|
| flagd | `.../providers/flagd/pkg` (pkg `flagd`) | `flagd.NewProvider(opts ...ProviderOption) (*Provider, error)` | RPC / in-process / file modes; events; see below |
| OFREP | `.../providers/ofrep` | `ofrep.NewProvider(baseUri string, options ...Option) *Provider` | Any OFREP server (flagd, GO Feature Flag, ...); stateless HTTP per evaluation |
| from-env | `.../providers/from-env/pkg` | `NewProvider(opts ...ProviderOption) *FromEnvProvider` | JSON flag definitions in env vars |
| GO Feature Flag (relay proxy) | `.../providers/go-feature-flag/pkg` (pkg `gofeatureflag`) | `NewProvider(options ProviderOptions) (*Provider, error)` | also `NewProviderWithContext` |
| GO Feature Flag in-process | `.../providers/go-feature-flag-in-process/pkg` | `NewProvider(options ProviderOptions) (*Provider, error)` | |
| LaunchDarkly | `.../providers/launchdarkly/pkg` | `NewProvider(ldclient LDClient, opts ...Option) *Provider` | wraps an existing LD client |
| ConfigCat | `.../providers/configcat/pkg` | `NewProvider(client Client) *Provider` | |
| Flagsmith | `.../providers/flagsmith/pkg` | `NewProvider(client *flagsmith.Client, opts ...ProviderOption) *Provider` | |
| Flipt | `.../providers/flipt/pkg/provider` (pkg `flipt`) | `NewProvider(opts ...Option) *Provider` | |
| Unleash | `.../providers/unleash/pkg` | `NewProvider(providerConfig ProviderConfig) (*Provider, error)` | 0.1.1-alpha |
| Harness | `.../providers/harness/pkg` | `NewProvider(providerConfig ProviderConfig) (*Provider, error)` | 0.0.5-alpha |
| Statsig | `.../providers/statsig/pkg` | `NewProvider(providerConfig ProviderConfig) (*Provider, error)` | |
| Prefab | `.../providers/prefab/pkg` | `NewProvider(providerConfig ProviderConfig) (*Provider, error)` | |
| Optimizely | `.../providers/optimizely` | `NewProvider(client *optimizely.OptimizelyClient, opts ...Option) *Provider` | |
| RocketFlag | `.../providers/rocketflag` | `NewProvider(client Client, opts ...ProviderOption) *Provider` | |
| AWS SSM | `.../providers/aws-ssm` (pkg `awsssm`) | `NewProvider(cfg aws.Config, opts ...ProviderOption) (*Provider, error)` | 1.0.0 |
| multi-provider | `.../providers/multi-provider/pkg` | deprecated → use `openfeature/multi` | |
| flagd-in-process, gcp | — | deprecated / empty stubs | do not use |

Each provider is its own Go module; `go get` the module path (without `/pkg`), then import the `/pkg` path shown.

### flagd provider (0.6.0) — brief; see the `flagd` skill for the daemon itself

```go
import flagd "github.com/open-feature/go-sdk-contrib/providers/flagd/pkg"

// RPC mode (default): evaluation happens inside flagd over gRPC, localhost:8013
p, err := flagd.NewProvider(flagd.WithHost("flagd.internal"), flagd.WithPort(8013))

// In-process mode: provider pulls the flag set over the sync API (default port 8015) and evaluates locally
p, err := flagd.NewProvider(flagd.WithInProcessResolver(), flagd.WithHost("flagd"), flagd.WithPort(8015),
	flagd.WithSelector("source=my-app"))

// File mode: local flag definition file, evaluated in-process, watched for changes
p, err := flagd.NewProvider(flagd.WithFileResolver(), flagd.WithOfflineFilePath("./flags.flagd.json"))

if err != nil { log.Fatal(err) }
if err := openfeature.SetProviderAndWait(p); err != nil { log.Fatal(err) }
```

Options are functions returning `flagd.ProviderOption`: `WithHost`, `WithPort(uint16)`, `WithTargetUri`, `WithTLS(certPath)`, `WithCertificatePath`, `WithSocketPath`, `WithRPCResolver`, `WithInProcessResolver`, `WithFileResolver`, `WithOfflineFilePath`, `WithSelector`, `WithProviderID`, `WithLRUCache(size)`, `WithBasicInMemoryCache`, `WithoutCache`, `WithEventStreamConnectionMaxAttempts`, `WithRetryGracePeriod`, `WithRetryBackoffMs`, `WithRetryBackoffMaxMs`, `WithDeadline(ms)`, `WithFatalStatusCodes`, `WithOtelInterceptor(bool)`, `WithLogger(logr.Logger)`, `WithGrpcDialOptionsOverride`, `WithCustomSyncProvider`, `WithCustomSyncProviderAndUri`, and `FromEnv()`.

Environment variables read (lowest precedence unless `flagd.FromEnv()` is placed after other options): `FLAGD_HOST`, `FLAGD_PORT`, `FLAGD_SYNC_PORT`, `FLAGD_TARGET_URI`, `FLAGD_TLS`, `FLAGD_SERVER_CERT_PATH`, `FLAGD_SOCKET_PATH`, `FLAGD_RESOLVER`, `FLAGD_OFFLINE_FLAG_SOURCE_PATH`, `FLAGD_SOURCE_SELECTOR`, `FLAGD_PROVIDER_ID`, `FLAGD_CACHE`, `FLAGD_MAX_CACHE_SIZE`, `FLAGD_MAX_EVENT_STREAM_RETRIES`, `FLAGD_RETRY_GRACE_PERIOD`, `FLAGD_RETRY_BACKOFF_MS`, `FLAGD_RETRY_BACKOFF_MAX_MS`, `FLAGD_DEADLINE_MS`, `FLAGD_FATAL_STATUS_CODES`.

`*flagd.Provider` implements `Init`, `Shutdown`, `Status()`, `EventChannel()`; it emits `PROVIDER_READY`, `PROVIDER_ERROR` and `PROVIDER_CONFIGURATION_CHANGED`. In RPC mode, `STATIC` results are cached (LRU, 1000 entries) and served with `Reason: CACHED` until a change event invalidates them.

### OFREP provider (0.1.7)

```go
import "github.com/open-feature/go-sdk-contrib/providers/ofrep"

p := ofrep.NewProvider("http://localhost:8016",
	ofrep.WithBearerToken(os.Getenv("OFREP_TOKEN")),            // Authorization: Bearer ...
	// ofrep.WithApiKeyAuth("key")                               // X-API-Key
	// ofrep.WithHeader("X-Tenant", "acme")
	// ofrep.WithHeaderProvider(func() (name, value string) { return "Authorization", "Bearer " + refresh() })
	ofrep.WithClient(&http.Client{Timeout: 2 * time.Second}),  // or ofrep.WithTimeout(d) when not passing a client
)
openfeature.SetProviderAndWait(p)
```

It calls the single-flag endpoint on every evaluation; there is no polling, caching, `Init`, or event emission in this version, so it reports READY immediately and each evaluation is a network round-trip. Put a timeout on the client.

### from-env provider (0.1.6)

Each flag is a JSON document in an environment variable named after the flag key (or mapped via `WithFlagToEnvMapper(func(flagKey string) string)`): `{"defaultVariant":"off","variants":[{"name":"on","targetingKey":"","criteria":[{"key":"plan","value":"pro"}],"value":true},{"name":"off","criteria":[],"value":false}]}`. First variant whose criteria all match the evaluation context wins (`TARGETING_MATCH`).

### OpenTelemetry hooks (0.3.7)

```go
import otelhook "github.com/open-feature/go-sdk-contrib/hooks/open-telemetry/pkg"

// Traces: adds feature_flag events/attributes to the span found in ctx (no-op if ctx has no span)
openfeature.AddHooks(otelhook.NewTracesHook(otelhook.WithErrorStatusEnabled()))

// Metrics: feature_flag.evaluation_requests_total / _success_total / _error_total / _active_count
mh, err := otelhook.NewMetricsHook()                          // uses the global otel MeterProvider
// mh, err := otelhook.NewMetricsHookForProvider(meterProvider, otelhook.WithFlagMetadataDimensions(
//     otelhook.DimensionDescription{Key: "scope", Type: otelhook.String}))
if err != nil { return err }
openfeature.AddHooks(mh)
```

Both accept `WithTracesAttributeSetter` / `WithMetricsAttributeSetter(func(openfeature.FlagMetadata) []attribute.KeyValue)` to turn flag metadata into extra attributes.

### Validator hook (0.1.7) and code-readiness hook (0.1.1)

```go
import (
	"github.com/open-feature/go-sdk-contrib/hooks/validator/pkg/regex"
	"github.com/open-feature/go-sdk-contrib/hooks/validator/pkg/validator"
	"github.com/open-feature/go-sdk-contrib/hooks/codereadiness"
)

hex, _ := regex.Hex()                                   // or validator.NewValidator(`^#[0-9a-f]{6}$`)
colour, err := client.StringValueDetails(ctx, "brand-colour", "#0000ff", evalCtx,
	openfeature.WithHooks(validator.Hook{Validator: hex}))   // invalid result → default + error in After

crh, err := codereadiness.New("v1.4.0", codereadiness.WithStrictValidation(true))
openfeature.AddHooks(crh)   // flags whose metadata minCodeVersion > v1.4.0 resolve to their default
```

---

## 12. Integration recipes

### net/http middleware: request → transaction context

```go
func WithFlagContext(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		userID := r.Header.Get("X-User-ID")          // or from your auth middleware
		ec := openfeature.NewEvaluationContext(userID, map[string]any{
			"ip":        r.RemoteAddr,
			"userAgent": r.UserAgent(),
			"path":      r.URL.Path,
		})
		ctx := openfeature.WithTransactionContext(r.Context(), ec)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

// downstream handlers just pass r.Context(); no evalCtx plumbing needed
func checkout(w http.ResponseWriter, r *http.Request) {
	if flags.Boolean(r.Context(), "new-checkout", false, openfeature.EvaluationContext{}) {
		// ...
	}
}
```

Later middleware can add attributes with `openfeature.MergeTransactionContext(ctx, extra)`.

### Startup and graceful shutdown

```go
func main() {
	initCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	provider, err := flagd.NewProvider()
	if err != nil { log.Fatal(err) }
	if err := openfeature.SetProviderWithContextAndWait(initCtx, provider); err != nil {
		log.Fatalf("flag provider not ready: %v", err)   // or continue with defaults — your call
	}

	srv := &http.Server{Addr: ":8080", Handler: WithFlagContext(mux)}
	go srv.ListenAndServe()

	<-signalChan
	shutdownCtx, cancel2 := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel2()
	_ = srv.Shutdown(shutdownCtx)
	if err := openfeature.ShutdownWithContext(shutdownCtx); err != nil {
		log.Printf("flag provider shutdown: %v", err)
	}
}
```

### Goroutine safety

`*Client` is safe for concurrent use (RWMutex-guarded); create one per domain at startup and share it. All API-level setters are locked. Evaluation snapshots the provider at the start of each call, so swapping providers at runtime is safe. Event handlers run on their own goroutines. `EvaluationContext`, `HookHints`, and `TrackingEventDetails` are immutable value types (attribute maps are copied on construction and on `Attributes()`).

### Tests with `memprovider` and goleak

```go
func TestMain(m *testing.M) {
	prov := memprovider.NewInMemoryProvider(testFlags)
	if err := openfeature.SetProviderAndWait(prov); err != nil { panic(err) }
	code := m.Run()
	openfeature.Shutdown()   // stops the event-executor goroutine; keeps go.uber.org/goleak happy
	os.Exit(code)
}
```

For per-test variation use `testing.TestProvider` (section 7) or an `isolated.NewAPI()` per test.

---

## 13. Gotchas

All verified in `client.go`, `openfeature_api.go`, `event_executor.go`, tests or CHANGELOG.

- **`SetProvider` is async.** Evaluations before `PROVIDER_READY` return the default with `ErrorCode: PROVIDER_NOT_READY` and `Reason: ERROR`. Use `SetProviderAndWait` / `SetProviderWithContextAndWait` at startup, or gate on a `ProviderReady` handler.
- **`SetProviderWithContext` ignores ctx cancellation for its own return value**; it only forwards ctx to the background `InitWithContext`. Only the `...AndWait` variants return `ctx.Err()`.
- **Shorthand getters swallow errors.** `client.Boolean(...)` returns the default on any error with no signal. Use `BooleanValue`/`BooleanValueDetails` when you need to distinguish "flag off" from "flag missing".
- **Type mismatch → default + `TYPE_MISMATCH`.** The SDK type-asserts after the provider returns; a string flag read via `BooleanValue` yields the default and `errNotBoolean`-style error. Reason becomes `ERROR`.
- **Ints are `int64`, floats are `float64`.** `IntValue(ctx, key, 10, ...)` — the untyped constant converts, but a variable must be `int64`. `ObjectValue` returns `any` (typically `map[string]any` from JSON providers); assert it.
- **Nil provider is rejected**: `SetProvider(nil)` returns `errNilDefaultProvider` (`"default provider cannot be set to nil"`).
- **Same provider pointer in two API instances** (global + `isolated.NewAPI()`, or two isolated APIs) fails with `provider %q is already bound to a different API instance` (spec 1.8.4).
- **`openfeature.Shutdown()` wipes everything** — hooks, handlers, global context, all providers — and installs a fresh API. Do not call it between requests; call it at process exit. Also, calling it in tests after registering hooks means re-registering them.
- **Event handlers run concurrently on separate goroutines**, unordered, panics are recovered and logged at INFO via `slog`. `EventCallback` is `*func(EventDetails)`, so keep the function in a variable and pass `&fn` (needed for `RemoveHandler` equality).
- **`EventDetails.ErrorCode` is not populated for handlers** in 1.18.0 (`executeHandler` copies only `Message`, `FlagChanges`, `EventMetadata`). Check `client.State()` (`FatalState`) or the message instead.
- **Flag keys must be valid UTF-8** or you get `PARSE_ERROR` before any hook or provider runs.
- **Before-hook context precedence**: a context returned from `Before` is merged *on top* of the merged invocation context (newest hook wins), and it is what the provider sees. Hooks cannot change the `context.Context` seen by later stages.
- **`FlagMetadata` is never nil** on `EvaluationDetails` (empty map on early errors, issue #542), so `details.FlagMetadata["k"]` is safe without a nil check.
- **`ClientMetadata.Name()` is deprecated** — use `Domain()`. `IEvaluation` is deprecated in favour of `*EvaluationAPI`.
- **A named client with no named provider silently uses the default provider.** Typos in domain names do not error.
- **`memprovider.InMemoryFlag.ContextEvaluator` is `*func`**, and its `Variants` values for int flags may be `int` (coerced) but not `uint`.
- **Replacing a provider shuts down the old one in a goroutine** — unless the same instance is still bound under another domain. Do not reuse a provider after replacing it.
- **Hooks run even when the provider is NOT_READY/FATAL** (`Error` and `Finally`, not `Before`/`After`), so hook code must tolerate `Reason: ERROR` with a zero `Variant`.

---

## 14. When this file is silent

Authoritative sources, in order of preference:

1. SDK docs page: <https://openfeature.dev/docs/reference/sdks/server/go>
2. Go package docs (exact signatures for the pinned version): <https://pkg.go.dev/github.com/open-feature/go-sdk@v1.18.0/openfeature> — subpackages: `/memprovider`, `/multi`, `/hooks`, `/isolated`, `/testing`, `/telemetry`
3. SDK source and CHANGELOG: <https://github.com/open-feature/go-sdk> (`openfeature/*.go`, `CHANGELOG.md`, `e2e/`)
4. Contrib providers and hooks, each with its own README and `go.mod`: <https://github.com/open-feature/go-sdk-contrib> (`providers/`, `hooks/`, versions in `.release-please-manifest.json`)
5. Specification (requirement numbers cited above): <https://openfeature.dev/specification/> — sections 01 flag evaluation, 02 providers, 03 evaluation context, 04 hooks, 05 events, 06 tracking
6. Getting-started tutorial (Gin + flagd): <https://openfeature.dev/docs/tutorials/getting-started/go>

Grep recipes on a fresh clone (`git clone https://github.com/open-feature/go-sdk && cd go-sdk`):

```sh
# every public function/method of the core package
grep -nE '^func (\([a-z]+ \*?[A-Z][A-Za-z]*\) )?[A-Z]' openfeature/*.go | grep -v _test

# all constants (reasons, error codes, states, event types)
grep -nE '^\s+[A-Z][A-Za-z]+\s+(Reason|ErrorCode|State|EventType|Type)\s*=' openfeature/*.go

# hook execution order and context merge
grep -n 'slices.Backward\|mergeContexts(' openfeature/client.go

# provider options for a contrib provider (e.g. flagd)
git clone https://github.com/open-feature/go-sdk-contrib && \
  grep -nE '^func (With|From)[A-Za-z]*\(' go-sdk-contrib/providers/flagd/pkg/configuration.go && \
  grep -ohE 'FLAGD_[A-Z_]+' go-sdk-contrib/providers/flagd/pkg/*.go | sort -u

# what changed between versions
sed -n '1,80p' CHANGELOG.md
```
