# OpenFeature Core Concepts and Specification Digest

Language-neutral summary of the OpenFeature specification and the openfeature.dev concept docs.
Source snapshot: `open-feature/spec` commit `24f98d7` (2026-09-21). The clone is shallow and carries no tags, so the exact spec version tag could not be read locally; Appendix E refers to `v0.9.0` as the release that introduced provider-emitted lifecycle events, so the snapshot is at least that version (latest tag otherwise unverified).
Requirement numbers below ("Requirement 1.4.10", "Conditional Requirement 3.2.2.2") are the spec's own identifiers and are also listed in `specification.json` in the spec repo.

## Table of contents

1. [What OpenFeature is](#1-what-openfeature-is)
2. [Glossary](#2-glossary)
3. [Architecture and mental model](#3-architecture-and-mental-model)
4. [Evaluation API (spec section 1)](#4-evaluation-api-spec-section-1)
5. [Providers (spec section 2)](#5-providers-spec-section-2)
6. [Evaluation context (spec section 3)](#6-evaluation-context-spec-section-3)
7. [Hooks (spec section 4)](#7-hooks-spec-section-4)
8. [Events (spec section 5)](#8-events-spec-section-5)
9. [Tracking (spec section 6)](#9-tracking-spec-section-6)
10. [SDK paradigms: dynamic vs static context](#10-sdk-paradigms-dynamic-vs-static-context)
11. [Appendix A: included utilities](#11-appendix-a-included-utilities)
12. [Appendix D: observability conventions](#12-appendix-d-observability-conventions)
13. [Appendix E migrations and the five-minute tutorial](#13-appendix-e-migrations-and-the-five-minute-tutorial)
14. [Conformance, statuses and Gherkin suites](#14-conformance-statuses-and-gherkin-suites)
15. [Spec term to SDK name mapping](#15-spec-term-to-sdk-name-mapping)
16. [When this file is silent](#16-when-this-file-is-silent)

---

## 1. What OpenFeature is

OpenFeature is "an open specification that provides a vendor-agnostic, community-driven API for feature flagging that works with your favorite feature flag management tool or in-house solution" (spec README, docs intro). It consists of three things:

- **The specification** (`open-feature/spec`): normative requirements for SDK behaviour, written with RFC 2119 keywords, plus a glossary, a types document, and appendices.
- **The SDKs**: per-language implementations of the spec (server-side and client-side "flavours"). The SDK exposes the Evaluation API to application code and manages providers, hooks, context and events.
- **Providers and integrations**: the ecosystem of adapters that connect the SDK to a concrete flag backend (flagd, a SaaS vendor, a file, environment variables, and so on) and of hooks that add telemetry, logging or tracking.

OpenFeature is a Cloud Native Computing Foundation **incubating** project (the openfeature.dev site footer states "OpenFeature is a Cloud Native Computing Foundation incubating project"). Community discussion happens in the `#openfeature` channel of the CNCF Slack.

**The problem it solves.** Feature flags need a flag management system (rules, UI, audit trail, environment management). Historically each vendor shipped its own SDK, so switching vendors or running two systems side by side meant rewriting every evaluation call. OpenFeature puts one stable evaluation API in application code and moves the vendor-specific part into a swappable *provider*. The design principles listed in the spec README are: compatibility with existing feature flag offerings, simple understandable APIs, vendor agnosticism, language agnosticism, low/no dependency, and extensibility.

**What it is not.** The SDK "does not itself handle the flag evaluation logic" (spec README). Without a provider, the API uses the built-in No-op provider, which simply returns the default value you passed (section 1 overview; the five-minute tutorial demonstrates this). You always need a provider plus a backend: flagd, an in-memory provider for tests, or a vendor provider. OpenFeature also does not define flag-key naming rules, a flag configuration format (flagd has its own), or a management UI.

---

## 2. Glossary

All definitions are condensed from `specification/glossary.md`.

| Term | Meaning |
| --- | --- |
| Feature flag | A mechanism that lets an application author define alternative code paths in deployed software, chosen at runtime based on a rule set. |
| Flag | A single pivot point of logic with a type (`boolean`, `string`, `number`, `json`/structure). Examples: `redesign_enabled`, `header-order`. |
| Flag key | A string that logically identifies a particular flag. OpenFeature places no restrictions on valid keys; providers may transform them for their backend. |
| Flag set | A collection of related flags, grouped for management and deployment. Surfaces in telemetry as `feature_flag.set.id`. |
| Variant | A semantic identifier for a value (`"on"`, `"control"`, `"pi"`), so a value can be referred to without shipping the value itself. |
| Value | The concrete data associated with a variant; it adheres to the flag's type. |
| Rule | Criteria or logic used to assign a variant during an evaluation. |
| Targeting | The application of rules, specific user overrides, or fractional evaluations during flag resolution. |
| Targeting key | A string logically identifying the subject of evaluation (end user, service, device). Many providers require it for deterministic fractional rollouts. |
| Fractional evaluation | Pseudorandomly resolving a flag using a context property (usually the targeting key) according to a configured proportion (for example 50/50). |
| Evaluating flag values | The full process: hook effects, provider resolution, and fallback to the supplied default on abnormal execution. |
| Resolving flag values | The provider's part only: fetching a value from its source of truth. |
| Evaluation API | The subset of the Feature Flag API the application author uses to evaluate flags (set provider, get client, `getXValue`, `getXDetails`). |
| Feature Flag API | All interfaces and abstractions used by application, integration and provider authors. |
| Feature flag SDK | The libraries an application author depends on; they implement the Feature Flag API. |
| Client | A lightweight abstraction that exposes evaluation functions. A client is associated with a single provider through its domain. |
| Provider | An SDK-compliant implementation that resolves flag values from a particular flag management system. |
| Provider lifecycle | The states and transitions of a provider (NOT_READY, READY, STALE, ERROR, FATAL, RECONCILING). |
| Flag management system | The source of truth for flag values and rules: a SaaS vendor, in-house infrastructure, or an open-source implementation such as flagd. |
| Domain | An identifier that logically binds clients to providers so several providers can coexist in one application. Binding is dynamic: a client on an unbound domain uses the default provider until a provider is set for that domain. |
| Isolated API instance | An independent, non-singleton API instance created through a factory function, with its own providers, context, hooks and handlers. For micro-frontends, DI containers and tests. |
| Integration | An SDK-compliant secondary function abstracted by the API and needing minimal configuration: telemetry, tracking, logging, monitoring. |
| Evaluation context | The context object for flag evaluation: runtime environment, transport details, host, client, subject (user). Built by merging global context, evaluation arguments and implicit propagation. |
| Transaction context propagator | An implementation that stores and returns transaction-specific evaluation context (a web request, a thread) using thread-local storage, continuations, etc. |
| Tracking event | A user action or application state representing a business objective, identified by a unique string and recorded through the tracking API. |
| Hook | Application author or integrator supplied logic called by the framework at a specific stage of evaluation (before, after, error, finally). |
| Application author | Writes application code that calls the SDK to make flagging decisions. |
| Application integrator | Sets up or configures the application to use the SDK: chooses the provider, wires telemetry. |
| Provider author | Maintains an API-compliant provider. |
| Integration author | Maintains an API-compliant integration (something other than flag evaluation, such as a telemetry hook). |
| Library author | Maintains a shared library that uses the SDK so its consumers can manage library behaviour with flags. |
| Client-side SDK | Built for single-user client applications (SPAs, mobile); typically uses the static-context paradigm. |
| Server-side SDK | Built for multi-user server applications; typically uses the dynamic-context paradigm. |
| Dynamic-context paradigm | Static context at initialisation plus per-request dynamic context supplied to each evaluation. |
| Static-context paradigm | Context set once for the single user; flags fetched and cached in bulk; a context change triggers re-evaluation (reconciliation). |

---

## 3. Architecture and mental model

```
+-----------------------------+
|  Application code           |  client.getBooleanValue("with-cows", false, ctx)
+--------------+--------------+
               |
               v
+-----------------------------+   global singleton (Requirement 1.1.1)
|  OpenFeature API            |   - default provider + per-domain providers
|  (evaluation API)           |   - global evaluation context, global hooks
|                             |   - global event handlers, transaction propagator
+------+-------------+--------+
       |             |
       v             v
+-----------+  +-----------+    one client per domain (or many clients per domain);
| Client    |  | Client    |    each has its own context, hooks and event handlers
| (default) |  | ("billing")|
+-----+-----+  +-----+-----+
      |              |
      v              v
+-----------+  +-----------+    exactly one provider per domain; the same provider
| Provider  |  | Provider  |    instance may serve several domains unless it is
| (flagd)   |  | (vendor)  |    "domain-scoped" (Requirement 2.4.3)
+-----+-----+  +-----+-----+
      |              |
      v              v
+-----------+  +-----------+
| flagd     |  | vendor    |    flag management system / backend
+-----------+  +-----------+

Hooks wrap every evaluation:   before -> [resolve] -> after | error -> finally
                                (API -> client -> invocation -> provider, then reversed)

Events flow upward:            provider --emit--> API --run--> API handlers
                                                   +--> bound client(s) --run--> client handlers
```

Reading the diagram:

- Application code only ever touches a **client**. A client is cheap; it can be created per module or even per HTTP request (Requirement 1.1.7 says client creation must not throw for exactly this reason).
- The **API singleton** owns configuration: which provider serves which domain, the global context, global hooks and handlers, the transaction context propagator, and shutdown.
- A **provider** translates the generic call (`flag key`, `default value`, `evaluation context`) into whatever its backend needs and returns a `resolution details` structure. The SDK wraps that into `evaluation details`, adds the hook pipeline and guarantees the default on any failure.
- **Events** originate in the provider and are fanned out to API-level handlers (all providers) and to handlers on clients bound to the emitting provider's domain (Requirements 5.1.2, 5.1.3).

---

## 4. Evaluation API (spec section 1)

Section 1 is marked **stable**; subsections 1.3, 1.4, 1.6 and 1.7 are marked **hardening**, and 1.8 (isolated instances) is **experimental**.

### 4.1 The global singleton

Requirement 1.1.1: the API and its state SHOULD exist as a global singleton, even when several versions of the API are present at runtime. The point is that the registered provider, the global evaluation context and the global hooks behave predictably.

Section 1.8 (experimental) adds an escape hatch: Requirement 1.8.1 says the API MUST expose a factory that returns an independent API instance with its own providers, context, hooks, handlers and propagators; Requirement 1.8.2 says such instances MUST honour the same contract as the singleton; Requirement 1.8.3 says the factory SHOULD live in a distinct module or import path so it is deliberately less discoverable; Requirement 1.8.4 says a provider instance SHOULD NOT be registered with more than one API instance at once.

### 4.2 Setting providers

- Requirement 1.1.2.1: the API MUST define a **provider mutator** that sets the default provider, for example `OpenFeature.setProvider(new MyProvider())`. The default provider serves any client whose domain has no bound provider.
- Requirement 1.1.3: the API MUST provide a way to bind a provider to a **domain**, for example `OpenFeature.setProvider("domain-1", new MyProvider())`. Setting a provider for a domain that already has one overwrites the mapping.
- Requirement 1.1.2.2: the mutator MUST call the new provider's `initialize` (passing the bound domain, if any) before using it to resolve flags. A provider instance already active on another domain is not initialised again.
- Requirement 1.1.2.3: the mutator MUST call `shutdown` on the previously registered provider once it is no longer used by any domain.
- Requirement 1.1.2.4: the API SHOULD provide a "set provider and wait" variant that blocks (or settles) once `initialize` has terminated **and** the resulting `PROVIDER_READY` or `PROVIDER_ERROR` event has been processed. Errors are reported idiomatically (thrown, returned). Application event handlers need not have completed when the call returns. This is the recommended way to start up; the plain `setProvider` is non-blocking and you would otherwise wait on the `PROVIDER_READY` event.
- Condition 1.1.8 / Conditional Requirement 1.1.8.1: if a provider declares itself **domain-scoped** (Requirement 2.4.3), the mutator MUST NOT bind that instance to more than one domain; the attempt is rejected idiomatically and the existing binding stays intact.
- Requirement 1.1.5: the API MUST expose the configured provider's metadata, optionally by domain (`getProviderMetadata("domain-1")`); an unbound domain returns the default provider's metadata.

### 4.3 Clients and domains

- Requirement 1.1.6: the API MUST provide a client factory that accepts an optional `domain` string: `getClient()` or `getClient("domain-1")`. A client uses the provider bound to its domain, falling back to the default provider.
- Requirement 1.1.7: client creation MUST NOT throw or abnormally terminate.
- Requirement 1.2.2: the client MUST expose `metadata` containing an immutable `domain` field matching the value given at creation. Earlier drafts called this `name`; implementations should treat `name` as an alias.
- Requirement 1.1.4 and Requirement 1.2.1: both the API and the client MUST provide `addHooks(...)`, which appends to (never replaces) the existing hook collection.

Domains are what make "multiple providers in one process" work: bind provider A to domain `"search"`, provider B to domain `"billing"`, hand each team a client for its domain, and each client's evaluations and events are scoped to its own provider.

### 4.4 Flag types and the value methods

The spec defines five value shapes in `types.md`: **boolean**, **string**, **number** (of unspecified size; Condition 1.3.3 / Conditional Requirement 1.3.3.1 says languages that distinguish integers from floats SHOULD offer separate `int`/`float` (or `long`/`double`) functions), and **structure** (structured data, JSON-like; usually called "object" in SDKs). `Datetime` exists as a context attribute type, not a flag type.

- Conditional Requirement 1.3.1.1 (dynamic-context paradigm): the client MUST provide typed evaluation methods with parameters `flag key` (required), `default value` (required), `evaluation context` (optional) and `evaluation options` (optional), returning the value.
- Conditional Requirement 1.3.2.1 (static-context paradigm): same, but **without** the `evaluation context` parameter, because context is global in that paradigm.
- Requirement 1.3.4: the client SHOULD guarantee the returned value has the expected type; a type mismatch from the provider is abnormal execution and the default is returned (error code `TYPE_MISMATCH`).
- Requirement 1.4.12: the client SHOULD offer asynchronous or non-blocking evaluation, especially in single-threaded runtimes.

### 4.5 Detailed evaluation and `evaluation details`

Conditional Requirements 1.4.1.1 (dynamic) and 1.4.2.1 (static) mirror the value methods but return an `evaluation details` structure. Per `types.md` its fields are:

| Field | Required | Rule |
| --- | --- | --- |
| `flag key` | yes | Requirement 1.4.5: MUST equal the key passed in. |
| `value` | yes | Requirement 1.4.3: MUST contain the evaluated value (the default on error). |
| `variant` | optional | Requirement 1.4.6: on normal execution MUST carry the provider's variant if set. |
| `reason` | optional | Requirement 1.4.7: on normal execution MUST carry the provider's reason if set; Requirement 1.4.9: on abnormal execution SHOULD indicate an error. |
| `error code` | optional | Requirement 1.4.8: on abnormal execution MUST contain an error code. |
| `error message` | optional | Requirement 1.4.13: MAY contain a human-readable detail. |
| `flag metadata` | always present | Requirement 1.4.14: MUST carry the provider's flag metadata if set, otherwise an empty record. Conditional Requirement 1.4.15.1: MUST be immutable where the language allows. |

Conditional Requirement 1.4.4.1: where the language has generics, `evaluation details` SHOULD be generic over the value type. The spec notes metadata in the details is "best effort", since not every provider can supply a reason or variant.

**Resolution reasons** (complete list from `types.md`; Requirement 2.2.5 says a provider SHOULD populate one of these "or some other string", so treat `reason` as an open string, not a closed enum):

| Reason | Meaning |
| --- | --- |
| `STATIC` | The resolved value is static (no dynamic evaluation). |
| `DEFAULT` | The value fell back to a pre-configured default in the flag system (no dynamic evaluation occurred, or it yielded no result). Note this is the *provider's* default variant, not your code default. |
| `TARGETING_MATCH` | The value came from a dynamic evaluation such as a rule or specific user targeting. |
| `SPLIT` | The value came from pseudorandom (fractional/percentage) assignment. |
| `CACHED` | The value was retrieved from a cache. |
| `DISABLED` | The flag is disabled in the management system. Not an error: the docs FAQ explains disabled flags are expected to be evaluated, so there is a disabled *reason* but no disabled *error code*. |
| `UNKNOWN` | The reason could not be determined. |
| `STALE` | The value is non-authoritative or possibly out of date. |
| `ERROR` | The value is the result of an error (you are looking at your code default). |

**Error codes** (complete list from `types.md`):

| Error code | When it occurs |
| --- | --- |
| `PROVIDER_NOT_READY` | The flag was evaluated before the provider finished initialising. |
| `FLAG_NOT_FOUND` | The flag key does not exist in the backend. |
| `PARSE_ERROR` | Data such as a flag configuration could not be parsed. |
| `TYPE_MISMATCH` | The flag's value type does not match the method used (asked for boolean, flag is a string). |
| `TARGETING_KEY_MISSING` | The provider requires a targeting key and the merged context had none. |
| `INVALID_CONTEXT` | The evaluation context does not meet provider requirements (wrong attribute type, missing required attribute). |
| `PROVIDER_FATAL` | The provider entered an irrecoverable error state (bad credentials, invalid configuration). |
| `GENERAL` | Any other error. |

### 4.6 Evaluation never throws

Requirement 1.4.10: methods, functions or operations on the **client** MUST NOT throw or otherwise abnormally terminate; evaluation calls always return the `default value` on abnormal execution. The exceptions are configuration and setup functions (setting a provider, instantiating providers, configuring the API) which may fail loudly. Consequences for you as an author:

- Pick defaults that are the *safe* behaviour, because you will see them whenever the provider is down, the flag is missing, or the type is wrong. The docs put it as "give consideration to your default values!".
- To find out *why* you got a default, call the details method and inspect `reason` / `error code`; do not rely on exceptions.
- Requirement 1.4.11: client methods SHOULD NOT write log messages. Evaluation is a hot path and a missing flag could flood logs with `FLAG_NOT_FOUND`. Attach the logging hook (Appendix A) when debugging instead. Logging is encouraged in configuration, initialisation and shutdown code.

### 4.7 Evaluation options

`Evaluation options` (`types.md`) carry two optional fields: `hooks` (one or more hooks to run for this invocation only; Requirement 1.5.1 says the client MUST run them in addition to configured hooks) and `hook hints` (see section 7).

### 4.8 Shutdown

- Requirement 1.6.1: the API MUST define a `shutdown` function that calls `shutdown` on every registered provider, unconditionally and regardless of provider state. Language idioms such as disposables or cancellation signals are acceptable alternatives.
- Requirement 1.6.2: `shutdown` MUST also reset all API state: hooks, event handlers, evaluation context, transaction context propagators and providers, leaving the No-op provider in place. This is intended for application exit and for resetting state between test suites.

### 4.9 Provider lifecycle as seen from the client

Requirement 1.7.1: the client MUST expose a `provider status` accessor with values `NOT_READY`, `READY`, `STALE`, `ERROR` or `FATAL`; Conditional Requirement 1.7.2.1 adds `RECONCILING` in the static-context paradigm. The SDK derives status purely from provider events (Requirements 1.7.3 to 1.7.5: `PROVIDER_READY` gives `READY`, `PROVIDER_ERROR` gives `ERROR`, `PROVIDER_ERROR` with error code `PROVIDER_FATAL` gives `FATAL`), except shutdown: Requirement 1.7.6 says status MUST be `NOT_READY` once the provider's `shutdown` terminates, inferred by the SDK because it initiated the call.

```
              initialize()
 NOT_READY ------------------> READY <----> ERROR
     |   \                      |  ^          ^
     |    \--> ERROR            |  |          |
     |     \-> FATAL --> [end]  v  |          |
     |                        STALE ----------+
     |                          |
     +<--- shutdown() ----------+ (from READY, STALE or ERROR)

 static-context only:  READY --setContext()--> RECONCILING --> READY | ERROR
```

Appendix A's multi-provider section adds a practical note: the only statuses that change client behaviour are `FATAL` and `NOT_READY`, in which case evaluation is skipped and the default returned; the others are informational.

### 4.10 Transaction context (pointer)

The API in the dynamic-context paradigm SHOULD accept a transaction context propagator and MUST offer a way to set transaction context when one is installed (Conditional Requirements 3.3.1.1 and 3.3.1.2.1). Details in section 6.

---

## 5. Providers (spec section 2)

Section 2 is **stable**; 2.4 (initialisation), 2.5 (shutdown), 2.6 (context reconciliation) and 2.8 (status) are **hardening**; 2.7 (tracking) is **experimental**.

Providers are "the translator between the flag evaluation calls made in application code and the flag management system". A provider may wrap a vendor SDK, embed a REST client, read a local file, or evaluate rules itself.

### 5.1 The feature provider interface

- Requirement 2.1.1: `metadata` with a `name` string identifying the implementation.
- Requirement 2.2.1 and Conditional Requirement 2.2.2.1: typed resolution methods, one per type (boolean, string, number, structure; languages that distinguish int/float usually split number), each taking `flag key`, `default value` and optional `evaluation context`, returning `resolution details`.
- Requirement 2.3.1: a **provider hooks** mechanism (a `hooks` member or accessor) that lets the provider author inject hooks into every evaluation made through this provider. Application authors do not control these.
- Requirement 2.4.1: MAY define `initialize(evaluationContext, domain?)`.
- Requirement 2.5.1: MAY define `shutdown`.
- Requirement 2.6.1: MAY define `onContextChanged(oldContext, newContext)` (static-context paradigm).
- Condition 2.7.1: MAY define `track(eventName, context?, details?)`.
- Requirement 5.1.1: MUST define an event emission mechanism (event emitter, channel, observable, as idiomatic).

`Resolution details` (`types.md`) is the provider-facing subset of `evaluation details`: `value` (required), `variant`, `reason`, `error code`, `error message`, `flag metadata`. It is never exposed to the application author; the SDK adds `flag key` and produces `evaluation details`.

Rules for filling it in:

- Requirement 2.2.3: on normal execution `value` MUST be the resolved value.
- Requirement 2.2.4: `variant` SHOULD be a string identifier for the returned value (a name, a UUID, an index; meaningful only to that backend).
- Requirement 2.2.5: `reason` SHOULD be one of the standard reasons or another string.
- Requirement 2.2.6 and Requirement 2.3.2: on normal execution `error code` and `error message` MUST NOT be populated (or must be null/falsy).
- Requirement 2.2.7: on abnormal execution the provider MUST signal an error idiomatically, with an `error code` and optional `error message`. Throwing an exception, returning an error value, or populating `error code` on the returned structure are all acceptable. This includes "not yet initialised" (`PROVIDER_NOT_READY`) and "irrecoverable" (`PROVIDER_FATAL`); the client then returns the default per Requirement 1.4.10.
- Requirement 2.2.9 and Requirement 2.2.10: SHOULD populate `flag metadata`, which MUST be a string-keyed map of `boolean | string | number`.

The docs FAQ adds guidance for provider authors: if the backend needs a targeting key that is missing, either indicate an error (`TARGETING_KEY_MISSING`, which yields the default) or generate one, and document the choice; if the backend lacks a flag type, convert (JSON in a string, booleans as `0`/`1`) or return an error, and document it.

### 5.2 Lifecycle: initialize, shutdown, reconciliation

**initialize** (Requirement 2.4.1) receives the global evaluation context and the bound domain (absent for the default provider). Typical work: an initial bulk fetch, opening a streaming connection, starting a poller. A provider instance is initialised once even if bound to several domains; the domain passed is the one it was first registered under. Conditional Requirement 2.4.2.1: if `initialize` cannot make the provider ready it SHOULD terminate abnormally, using `PROVIDER_FATAL` for irrecoverable problems.

**Domain-scoped providers** (Requirements 2.4.3, 2.4.4): a provider that keeps per-domain state (for example a persistent cache partitioned by domain) MAY declare itself domain-scoped, which forces the API to bind it to at most one domain, and it MUST then accept and use the domain given to `initialize`.

**shutdown** (Requirement 2.5.1): release connections, timers, threads; flush pending tracking data. Requirement 2.5.2: afterwards the provider SHOULD revert to its uninitialised state (some allow re-initialisation). Requirement 2.5.3: `shutdown` SHOULD be idempotent. Shutdown during initialisation aborts initialisation.

**onContextChanged** (Requirement 2.6.1): static-context providers keep evaluated flags for the current context; when the global context changes the SDK calls this function with old and new context so the provider can re-evaluate in bulk. Conditional Requirement 3.2.4.1 says the SDK MUST run it on all providers using the global context when that context changes; Conditional Requirement 3.2.4.2 says a change to a domain-specific context MUST run it only on that domain's provider.

### 5.3 Provider status and the events a provider must emit

Since spec `v0.9.0` (Appendix E) the SDK no longer synthesises lifecycle events. Section 2.8:

- Requirement 2.8.1: the provider MUST emit an event for **every** status transition, including those caused by `initialize` and `onContextChanged`, and spontaneous ones (connection lost, cache stale).
- Requirement 2.8.2: MUST emit `PROVIDER_READY` before `initialize` terminates normally.
- Requirement 2.8.3: MUST emit `PROVIDER_ERROR` before `initialize` terminates abnormally, with error code `PROVIDER_FATAL` when irrecoverable.
- Requirement 2.8.4: MUST emit `PROVIDER_CONTEXT_CHANGED` when `onContextChanged` terminates normally and `PROVIDER_ERROR` when it fails. The return value of `onContextChanged` is only a synchronisation signal; status and handlers are driven by the event.
- Conditional Requirement 2.8.5.1: a provider with no `initialize` MUST be treated as `READY` from registration, and the SDK MUST run `PROVIDER_READY` handlers on its behalf.

Event to status mapping (Requirement 5.3.5, which also demands the status be updated **before** handlers run):

| Event | Resulting status |
| --- | --- |
| `PROVIDER_READY` | `READY` |
| `PROVIDER_STALE` | `STALE` |
| `PROVIDER_ERROR` | `ERROR`, or `FATAL` when the error code is `PROVIDER_FATAL` |
| `PROVIDER_CONFIGURATION_CHANGED` | unchanged |
| `PROVIDER_CONTEXT_CHANGED` | `READY` |
| `PROVIDER_RECONCILING` | `RECONCILING` |

### 5.4 Tracking on providers

Condition 2.7.1: a provider MAY implement `track(trackingEventName, evaluationContext?, trackingEventDetails?)` returning nothing. Any I/O should not block the call, and pending tracking data should be flushed before shutdown. If the provider lacks `track`, the client's `track` is a no-op (Requirement 6.1.4).

### 5.5 flagd and OFREP in one paragraph

flagd is the OpenFeature project's own open-source flag evaluation engine and backend; the flagd provider is one provider among many and the reference for the spec's Gherkin suites (the SDK e2e suites are also run against in-memory providers). OFREP, the OpenFeature Remote Evaluation Protocol (spec Appendix C, repo `open-feature/protocol`), is a vendor-neutral HTTP API "that adheres to the OpenFeature semantics" so that a single generic OFREP provider per language can talk to any OFREP-compliant backend, flagd included, instead of each vendor shipping a bespoke provider. Its OpenAPI document is published at `https://openfeature.dev/docs/reference/other-technologies/ofrep/openapi`.

---

## 6. Evaluation context (spec section 3)

Section 3 is **hardening**; 3.3 (context propagation) is **experimental**.

### 6.1 Structure

- Requirement 3.1.1: an optional `targeting key` string identifying the subject. Providers may require it for fractional evaluation, rules or overrides and "may behave unpredictably" without it.
- Requirement 3.1.2: custom fields with string keys and values of type `boolean | string | number | datetime | structure` (nested structures allowed).
- Requirement 3.1.3: fields must be retrievable by key and as a whole.
- Requirement 3.1.4: keys MUST be unique across all types, to avoid collisions when the provider marshals the context.

Field casing is left to language idiom (`targetingKey`, `targeting_key`, `TargetingKey`). The docs warn against circular structures because many providers serialise the context.

### 6.2 Levels and merge order

Conditional Requirement 3.2.1.1 (dynamic-context paradigm): the API, the client and the invocation MUST each accept evaluation context. The static-context paradigm instead has Conditional Requirement 3.2.2.1 (API MUST have a global context setter), Conditional Requirement 3.2.2.2 (client and invocation MUST NOT accept context), and Conditional Requirements 3.2.2.3 and 3.2.2.4 (API MUST allow setting and managing context per domain; the global context is used when no domain-specific one exists).

Requirement 3.2.3 fixes the merge order, lowest precedence first:

```
API (global)  ->  transaction  ->  client  ->  invocation  ->  before hooks
```

Duplicate keys are overwritten by the later (more specific) level. In practice: put static facts (application name, region, hostname, version) in the API context, request-scoped facts (user id, IP, user agent) in transaction context, module-specific facts on the client, and anything call-specific at invocation. A `before` hook can still override everything (Requirement 4.3.5).

Requirement 6.1.3 applies the same order (API, transaction, client, invocation) to the context passed to a provider's `track`.

### 6.3 Transaction context propagation (dynamic paradigm only)

Transaction context is request-scoped context that you set once where the data is available (auth middleware, request handler) and that the SDK merges into every evaluation within that transaction, without threading the context through every function call. Conditional Requirement 3.3.1.1: the API SHOULD accept a `transaction context propagator` (replacing any existing one). If the SDK implements propagation (Condition 3.3.1.2), the API MUST provide `setTransactionContext(context)` (Conditional Requirement 3.3.1.2.1) and the propagator MUST provide setter and getter for the current transaction's context (Conditional Requirements 3.3.1.2.2, 3.3.1.2.3). Carriers are language specific: ThreadLocal or `ScopedValue` in Java, `AsyncLocalStorage` in Node, `contextvars` in Python, `context.Context` in Go. Conditional Requirement 3.3.2.1: static-context SDKs MUST NOT offer a propagator, since context there is global.

### 6.4 Targeting key and bucketing

The targeting key is the input for deterministic fractional evaluation: a provider hashes `targetingKey` (often together with the flag key) and maps the hash onto the configured percentage buckets, so the same subject always lands in the same variant for the same flag. Use a stable identifier: a user UUID, a hash of an email, a device id, or for service-to-service flags the hostname or service name. A missing key either yields `TARGETING_KEY_MISSING` or non-sticky assignment, depending on the provider.

### 6.5 Privacy

The docs' PII section: be deliberate about personal data in the context, since providers may transmit or persist it. A `before` hook is the recommended place to restrict, filter, hash or anonymise attributes before the provider sees them. Appendix D adds the same caution for flag *values* in telemetry.

---

## 7. Hooks (spec section 4)

Section 4 is **hardening**. Hooks "operate similarly to middleware in many web frameworks" and attach at four stages:

- `before`: immediately before resolution; may enrich or replace the evaluation context.
- `after`: immediately after successful resolution; may validate the value.
- `error`: after an unsuccessful evaluation (including an error thrown in `before` or `after`).
- `finally`: unconditionally at the end (named `finallyAfter` where `finally` is reserved; Conditional Requirement 4.3.9.1).

Requirement 4.3.1: a hook MUST implement at least one stage.

### 7.1 Hook context, hints and hook data

- Requirement 4.1.1: `hook context` MUST provide `flag key`, `flag value type`, `evaluation context` (the **merged** context per Requirement 3.2.3), `default value` and `hook data`. Requirement 4.1.2: it SHOULD also expose client metadata and provider metadata.
- Requirement 4.1.3: `flag key`, `flag type` and `default value` are immutable. Conditional Requirement 4.1.4.1 (dynamic paradigm): the evaluation context is mutable only in `before`.
- **Hook hints** (Requirement 4.2.1): an immutable string-keyed map of `boolean | string | number | datetime | structure` supplied through `evaluation options` (Requirement 4.5.1) and passed to every hook (Requirement 4.5.2); hooks MUST NOT alter it (Requirement 4.5.3). Use it to pass per-call knobs to hooks ("skip logging here", a trace id).
- **Hook data** (Requirements 4.1.5, 4.3.2, 4.6.1): a mutable, string-keyed, any-valued scratch map created before a hook's first stage runs for a given evaluation and shared across that hook's stages only; other hooks get their own. The canonical use is starting a span or timer in `before` and closing it in `after`/`finally`.

### 7.2 Stage signatures

- Conditional Requirement 4.3.2.1 (dynamic): `before(hookContext, hints?) -> evaluationContext | nothing`. Conditional Requirement 4.3.3.1 (static): `before(hookContext, hints?) -> nothing`.
- Requirement 4.3.4: context returned from one `before` hook MUST be visible to subsequent `before` hooks. Requirement 4.3.5: after all `before` hooks, the resulting context MUST be merged with the existing context (it has the highest precedence).
- Requirement 4.3.6: `after(hookContext, evaluationDetails, hints?)`.
- Requirement 4.3.7: `error(hookContext, exception, hints?)`; runs for errors in `before`, `after` or resolution.
- Requirement 4.3.8: `finally(hookContext, evaluationDetails, hints?)`; the details equal what the application receives.

### 7.3 Registration levels and execution order

Requirement 4.4.1: the API, client, provider and invocation MUST each accept hooks. Requirement 4.4.2 defines the order:

```
before:                 API  ->  Client  ->  Invocation  ->  Provider   (each level in insertion order)
after/error/finally:    Provider  ->  Invocation  ->  Client  ->  API   (each level in reverse insertion order)
```

This is stack-like (LIFO) behaviour, so an API-level hook wraps everything and a provider hook sits closest to resolution. The openfeature.dev hooks page lists only API, client and invocation; the spec is authoritative and includes the provider level.

### 7.4 Error semantics

- Requirement 4.4.5: an error in `before` or `after` MUST trigger the `error` hooks.
- Requirement 4.4.6: once a `before` or `after` hook fails, the remaining hooks of that stage MUST NOT run.
- Requirement 4.4.7: an error in `before` MUST result in the default value being returned (a `before` hook may have corrupted the context, so the evaluation is treated as abnormal).
- Requirements 4.4.3 and 4.4.4: an error thrown by an `error` or `finally` hook MUST NOT stop evaluation; remaining `error`/`finally` hooks still run.

Put together, a failing `before` hook produces: `before` (aborted) -> `error` hooks -> `finally` hooks -> default value returned with `reason = ERROR`.

### 7.5 Common uses

Logging (Appendix A logging hook), validation of resolved values in `after`, OpenTelemetry spans/events (Appendix D), context enrichment or PII scrubbing in `before`, and reporting exposures for experimentation in `after` (section 9).

---

## 8. Events (spec section 5)

Section 5 is **hardening**. Events let consumers react to provider or backend state changes. The provider's domain is the scope: clients bound to a domain run handlers only for that domain's provider.

### 8.1 Event types (complete list from `types.md`)

| Event | Meaning | Paradigm |
| --- | --- | --- |
| `PROVIDER_READY` | The provider can perform evaluations (after initialisation or after recovering from an error). | both |
| `PROVIDER_ERROR` | The provider signalled an error, for example lost connection; evaluations will default. With error code `PROVIDER_FATAL` the state becomes `FATAL`. | both |
| `PROVIDER_CONFIGURATION_CHANGED` | The backend flag configuration changed (values or rules); `flags changed` lists affected keys when available. | both |
| `PROVIDER_STALE` | The provider's cached state may be out of date (disconnected but still serving cached values). | both |
| `PROVIDER_RECONCILING` | The context changed and the provider has not yet reconciled its state. | static-context only |
| `PROVIDER_CONTEXT_CHANGED` | The context changed and the provider has reconciled; flags should be re-evaluated. | static-context only |

### 8.2 Payloads

`Provider event details` (what the provider emits): `flags changed` (string[], optional), `message` (optional), `error code` (optional), `event metadata` (string-keyed `boolean | string | number`). `Event details` (what handlers receive) adds `provider name` (required; Requirement 5.2.3). Requirements 5.1.4 and 5.1.5: `PROVIDER_ERROR` SHOULD carry `error message` and `error code`.

### 8.3 Handlers

- Requirement 5.2.1 and Requirement 5.2.2: both client and API MUST offer `addHandler(eventType, handler)`; Requirement 5.2.7: both MUST offer removal.
- Requirement 5.2.4: a handler MUST accept an `event details` parameter.
- Requirement 5.1.2 / Requirement 5.1.3: when a provider emits, the API handlers and the handlers of clients bound to that provider MUST run; handlers on clients bound to other providers MUST NOT.
- Requirement 5.2.5: a throwing handler MUST NOT prevent other handlers from running.
- Requirement 5.2.6: handlers MUST persist across provider changes, so registration order relative to `setProvider` does not matter.
- Requirement 5.3.3: a handler attached when the provider is **already** in the corresponding state MUST run immediately (attach a `PROVIDER_READY` handler late and it still fires). Implementations must avoid out-of-order processing in multi-threaded runtimes.
- Requirements 5.3.1 and 5.3.2: `PROVIDER_READY` / `PROVIDER_ERROR` handlers MUST run when the provider emits those events after initialisation.
- Conditional Requirements 5.3.4.1 to 5.3.4.3 (static paradigm): `RECONCILING` handlers MUST run while `onContextChanged` executes (skippable if reconciliation is synchronous); `PROVIDER_CONTEXT_CHANGED` handlers MUST run when it terminates normally and no other invocation is still pending; `PROVIDER_ERROR` handlers MUST run when it fails. Providers coalesce rapid reentrant context changes and emit only after the last one.

### 8.4 Use cases

API-level handlers suit cross-cutting monitoring: alert on `PROVIDER_ERROR`, log `provider name` and `error code`. Client-level handlers suit domain logic: on `PROVIDER_CONFIGURATION_CHANGED` invalidate a local cache or re-evaluate the flags in `flags changed`; in UIs, on `PROVIDER_RECONCILING` show a loading state and on `PROVIDER_CONTEXT_CHANGED` re-render components that depend on flags; await `PROVIDER_READY` before rendering flag-dependent UI to avoid a flash of default content.

---

## 9. Tracking (spec section 6)

Section 6 is **experimental**. The tracking API "enables the association of feature flag evaluations with subsequent actions or application states" for experimentation and impact analysis. The pattern: a hook reports each flag *exposure* (who saw which variant) to the analytics platform; `track` reports the *outcome* (conversion, click, revenue); the platform joins the two on the subject.

- Conditional Requirement 6.1.1.1 (dynamic): `client.track(trackingEventName, evaluationContext?, trackingEventDetails?) -> nothing`.
- Conditional Requirement 6.1.2.1 (static): `client.track(trackingEventName, trackingEventDetails?) -> nothing` (context is already global).
- Requirement 6.1.3: the context handed to the provider is merged API -> transaction -> client -> invocation.
- Requirement 6.1.4: if the provider does not implement tracking, `track` MUST be a no-op.

`Tracking event details` (Requirements 6.2.1, 6.2.2): an optional numeric `value` (a well-defined scalar many providers map natively, for example revenue) plus arbitrary custom fields with values of type `boolean | string | number | structure`, nesting allowed. Example from the spec: `client.track("clicked-checkout", ctx, TrackingEventDetails(99.77).add("currencyCode", "USD"))`. `track` is fire-and-forget: it may trigger I/O but need not be awaited.

---

## 10. SDK paradigms: dynamic vs static context

The glossary and `06-sdk-paradigms.mdx` define two flavours. Several requirements above are conditional on which one an SDK implements.

| Aspect | Dynamic-context paradigm (server SDKs) | Static-context paradigm (client/web/mobile SDKs) |
| --- | --- | --- |
| Who is the subject | Many users; changes per request | One user (the device owner) |
| Where context lives | API + transaction + client + invocation (Conditional Requirement 3.2.1.1) | API only, optionally per domain (Conditional Requirements 3.2.2.1 to 3.2.2.4); no context parameter on evaluation methods |
| Evaluation call | `getBooleanValue(key, default, context?, options?)` | `getBooleanValue(key, default, options?)` |
| Provider model | Resolve per call against rules or a remote service | Fetch/evaluate flags in bulk for the current context at init, cache, serve from cache |
| Context change | Just pass a different context | `setContext(newContext)` -> SDK calls provider `onContextChanged` -> `PROVIDER_RECONCILING` -> `PROVIDER_CONTEXT_CHANGED` or `PROVIDER_ERROR` |
| Extra status/events | none | `RECONCILING`; `PROVIDER_RECONCILING`, `PROVIDER_CONTEXT_CHANGED` |
| `before` hook | may return context (Conditional Requirement 4.3.2.1) | returns nothing (Conditional Requirement 4.3.3.1) |
| Transaction propagator | SHOULD exist (Conditional Requirement 3.3.1.1) | MUST NOT exist (Conditional Requirement 3.3.2.1) |
| `track` | `track(name, context?, details?)` | `track(name, details?)` |

Why web SDKs have synchronous getters: because flags were already evaluated in bulk and cached during initialisation or reconciliation, a static-context evaluation is a cache lookup and can be synchronous, which suits render paths. The cost is that every context change is an asynchronous round trip; hence the reconciliation events and loading-state guidance. The glossary notes that providers written for dynamic context can generally be adapted to the static model, but not the reverse.

---

## 11. Appendix A: included utilities

### 11.1 In-memory provider

SDKs SHOULD ship an in-memory provider intended for tests (application code may also use it). Required features: constructed with a pre-defined flag set; a minimal flag structure with evaluation-context support through callbacks/lambdas ("context evaluator"); a way to update the flag set that emits `PROVIDER_CONFIGURATION_CHANGED` with `flags changed` set to the union of old and new keys; maintained in step with the spec. Typical flag shape (from the JS tutorial, Go `memprovider.InMemoryFlag` and Python `InMemoryFlag`):

```
"with-cows": {
  variants:         { on: true, off: false },   // variant name -> value
  defaultVariant:   "on",                        // used when no context evaluator matches
  disabled/state:   false | ENABLED,             // disabled flags resolve with reason DISABLED
  contextEvaluator: (ctx) => ctx.cow == "Bessie" ? "on" : "off",   // optional targeting
  flagMetadata:     { ... }                      // optional (Python exposes it)
}
```

The Gherkin suites (Appendix B) are written to run against this provider.

### 11.2 Multi-provider

A provider that wraps an ordered list of providers behind one provider interface. Use cases named in the appendix: migration between vendors (new provider first, fall back to the old), combining data sources (env vars, files, database, SaaS), and fanning out tracking events. Behaviour summary:

- Each inner provider gets a unique name: constructor-supplied name, else `metadata.name` if unique, else `${metadata.name}_${index}`; conflicting explicit names throw.
- `initialize` runs all inner initialisations in parallel and re-throws any error.
- Status is aggregated by precedence `FATAL > NOT_READY > ERROR > STALE > READY`; inner status events are swallowed unless they change the aggregate, in which case the original event details are re-emitted. `PROVIDER_CONFIGURATION_CHANGED` is always re-emitted.
- Provider hooks of each inner provider run against that provider's own copy of the context so they cannot leak into another provider's evaluation.
- Thrown and returned errors are both treated as errors; an error result's `value` is ignored.
- `track` goes to all inner providers in `READY` state (skipping `NOT_READY`/`FATAL` and providers without `track`); individual failures are logged, not thrown; a strategy's `shouldTrackWithThisProvider` can filter.
- Aggregated errors are thrown as `{ message, code, originalErrors: [{ source, error }] }`; metadata is `{ name: "multiprovider", originalMetadata: { ... } }`.

**Strategies** (verified against the appendix):

| Strategy | Behaviour |
| --- | --- |
| `FirstMatchStrategy` (default) | Evaluate in order; skip a provider only on `FLAG_NOT_FOUND`; any other error aborts the whole evaluation with that provider's error; short-circuit on the first value. |
| `FirstSuccessfulStrategy` | Like First Match but errors do not halt; return the first successful result; error only if all fail. |
| `ComparisonStrategy` | Evaluate all; if all succeed and values disagree, return the configurable fallback provider's result and call `onMismatch`; otherwise return the first provider's result. |
| Custom (`BaseEvaluationStrategy`) | Implement `runMode` (`parallel` or `sequential`), `shouldEvaluateThisProvider`, `shouldEvaluateNextProvider`, `determineFinalResult`, `shouldTrackWithThisProvider`. |

### 11.3 Logging hook

SDKs SHOULD ship a logging hook. What it logs per stage:

| Stage | Fields |
| --- | --- |
| before | `stage`, `domain`, `provider_name`, `flag_key`, `default_value`, `evaluation_context` (opt-in) |
| after | the above plus `reason`, `variant`, `value` |
| error | the before fields plus `error_code`, `error_message` |
| finally | nothing |

The evaluation context SHOULD be logged only when an option (for example `printContext`) enables it, and then in a human-readable form such as JSON. Where the logger has levels, before/after SHOULD use debug/info and error SHOULD use error. This hook is the sanctioned replacement for the client-side logging that Requirement 1.4.11 discourages. It does not use hook hints in the appendix's description.

### 11.4 No-op provider

Not an appendix item but relied on throughout: the provider installed when none is set and after `shutdown` (section 1 overview, Requirement 1.6.2). It returns the supplied default for every evaluation.

---

## 12. Appendix D: observability conventions

Appendix D maps OpenFeature data onto the OpenTelemetry feature-flag semantic conventions (`opentelemetry.io/docs/specs/semconv/feature-flags/feature-flags-logs/`), which at the time of the snapshot were a release candidate. Enumerations (`error.type`, `feature_flag.result.reason`) MUST be transformed from OpenFeature's `UPPER_SNAKE` to OTel's lowercase `snake_case` (`FLAG_NOT_FOUND` -> `flag_not_found`, `TARGETING_MATCH` -> `targeting_match`).

From `evaluation details`:

| Attribute | Source | Level |
| --- | --- | --- |
| `feature_flag.key` | `flag key` | Required |
| `feature_flag.result.variant` | `variant` | Conditionally required (whenever the provider supplies it) |
| `feature_flag.result.value` | `value` | Conditionally required when no variant; recommended otherwise; redact large or sensitive values |
| `feature_flag.result.reason` | `reason` | Recommended |
| `error.type` | `error code` | Conditionally required, only when an error occurred |
| `error.message` | `error message` | Conditionally required, only when an error occurred |

From `flag metadata` (camelCase keys populated by the provider):

| Attribute | Flag metadata key | Level |
| --- | --- | --- |
| `feature_flag.context.id` | `contextId` | Recommended; falls back to the targeting key |
| `feature_flag.set.id` | `flagSetId` | Recommended |
| `feature_flag.version` | `version` | Recommended |

From `provider metadata`: `feature_flag.provider.name` <- `name` (Recommended), available through the hook context.

Renamed attributes (history table): `feature_flag.variant` -> `feature_flag.result.variant` and `feature_flag.evaluation.reason` -> `feature_flag.result.reason` (semconv v1.32.0); `feature_flag.evaluation.error.message` -> `error.message` and `feature_flag.provider_name` -> `feature_flag.provider.name` (v1.33.0); `value` -> `feature_flag.result.value` (v1.34.0).

**Telemetry hook implementation guide.** Three emission patterns: span events (recommended for low overhead, but need an active span, and OTel is moving away from span events), event logging (works without spans, needs an event exporter), standalone spans (one span per evaluation; detailed but noisy). Stage roles: `before` creates spans for the standalone pattern, recommended span name `feature_flag.evaluation`, stored in hook data; `error` records the exception unless `excludeExceptions`; `finally` emits the signal with the full attribute set and cleans up. Suggested options: `attributeMapper`, `excludeAttributes`, `excludeExceptions`, `eventMutator`. Hooks must never throw into the evaluation. SDK "telemetry helpers" that build this attribute set from a hook context and evaluation details are what the per-language SDKs expose (names differ by SDK; see the SDK reference files). The OTel log-record event name used for the evaluation event is not stated in the local appendix text; OTel's convention names it `feature_flag.evaluation` (unverified locally).

---

## 13. Appendix E migrations and the five-minute tutorial

### 13.1 Appendix E: provider lifecycle event emission

Non-normative migration guidance. Before `v0.9.0` the SDK emitted synthetic `PROVIDER_READY`/`PROVIDER_ERROR` after lifecycle methods returned, which raced with providers emitting from background threads. Now providers own their events (section 5.3). Provider authors must emit `PROVIDER_READY` after successful init, `PROVIDER_ERROR` after failed init, and for static-context providers `PROVIDER_RECONCILING`, `PROVIDER_CONTEXT_CHANGED` or `PROVIDER_ERROR` around reconciliation, and implement the SDK's opt-in marker (an interface, boolean or type tag) to signal this. Patterns: blocking init emits `PROVIDER_READY` right before returning; event-driven init keeps `initialize` pending until the vendor SDK signals ready; reconciliation coalesces reentrant calls. Anti-patterns: emitting `PROVIDER_READY` before init work is done; returning from `initialize` before emitting. SDKs keep a deprecated legacy path (synthetic events, deprecation warning) for providers without the marker; duplicates are possible in mixed mode.

### 13.2 Migrating between vendors

The mechanism is the provider boundary itself: application code calls the same client methods; switching backends is "as simple as configuring a different provider" (tutorial). For a gradual cutover, Appendix A's multi-provider with `FirstMatchStrategy` lists the new provider first and falls back to the old one for flags not yet migrated, or `ComparisonStrategy` runs both and reports mismatches through `onMismatch` before switching. Flag keys, variants and targeting rules still have to be recreated in the new system; OpenFeature standardises the API, not the flag definitions.

### 13.3 Lessons from the five-minute tutorial

The tutorial (Node/Express) walks from a hard-coded `const withCow = false` to `client.getBooleanValue("with-cows", false)` with no provider (always the default), then an `InMemoryProvider` with `variants`/`defaultVariant`, then targeting through a `contextEvaluator` that reads `context.cow` supplied at invocation from an HTTP header. Takeaways that are in the docs: the default value is what you get with no provider or on any error, so choose it as the safe fallback; start with the in-memory provider and swap providers later without touching evaluation code; targeting data enters through the evaluation context at the call site. The local docs do not contain flag lifecycle guidance (naming conventions, cleaning up stale flags, not using flags for static configuration), so none is asserted here (unverified).

---

## 14. Conformance, statuses and Gherkin suites

**How requirements are written** (`specification/README.md`): a statement is normative only if it sits under a markdown H5 heading, inside a block quote, and contains an uppercase RFC 2119 keyword. Each such H5 defines exactly one requirement, so enumerating them yields the test-assertion list that `specification.json` holds (135 top-level entries at this snapshot, each with `id`, `machine_id`, `content`, `RFC 2119 keyword`, and `children`). Numbering is `section.subsection.index` (`Requirement 1.4.10`); optional behaviour is expressed as a `Condition x.y.z` ("The implementation uses the static-context paradigm") whose children are `Conditional Requirement x.y.z.n` that only apply when the condition holds. An implementation is compliant when it satisfies every MUST / MUST NOT / REQUIRED / SHALL / SHALL NOT.

**Document statuses**: Experimental (breaking changes any time, not for production), Hardening (production-ready, breaking changes need TSC consensus but may land in minor versions), Stable (no breaking changes without a major version). No badge means Experimental. Current badges: sections 1 and 2 Stable (with hardening subsections), 3, 4 and 5 Hardening, 6 Tracking Experimental, 1.8 isolated instances and 3.3 context propagation Experimental.

**Gherkin suites** (Appendix B): language-agnostic end-to-end tests in `specification/assets/gherkin/`, run by each SDK with a Cucumber-style runner against its in-memory provider (Appendix A states e2e tests must use the in-memory provider and be self-contained). Files at this snapshot: `evaluation.feature` (marked `@deprecated`, 13 scenarios), `evaluation_v2.feature` (21), `contextMerging.feature` (7), `hooks.feature` (3), `metadata.feature` (2). Scenarios cover typed value and details evaluation, variant/reason expectations (for example variant `"on"` with reason `STATIC`), context merging precedence, hook invocation and flag metadata. The appendix text itself only references `evaluation.feature`. A separate flagd test-bed suite exists for flagd providers, but it is not described in the local spec sources (unverified).

---

## 15. Spec term to SDK name mapping

Verified against `go-sdk/README.md`, `dotnet-sdk/README.md`, `python-sdk/README.md`, the SDK sources in the clone, and the openfeature.dev concept and SDK pages. Java and JS names come from the openfeature.dev pages and spec examples only.

| Spec term | Go | .NET | Python | Java | JS (server) |
| --- | --- | --- | --- | --- | --- |
| API singleton | package-level funcs in `openfeature` | `Api.Instance` | module `openfeature.api` | `OpenFeatureAPI.getInstance()` | `OpenFeature` from `@openfeature/server-sdk` |
| Set provider and wait | `openfeature.SetProviderAndWait(p)`, `SetNamedProviderAndWait(domain, p)` | `await Api.Instance.SetProviderAsync(p)` (throws on init failure) | `api.set_provider_and_wait(p, domain=None)` | `api.setProviderAndWait(p)` | `await OpenFeature.setProviderAndWait(p)` |
| Get client | `openfeature.NewDefaultClient()`, `NewClient(domain)` | `Api.Instance.GetClient(domain?)` -> `FeatureClient` | `api.get_client(domain=None)` | `api.getClient(domain?)` -> `Client` | `OpenFeature.getClient(domain?)` |
| Boolean value | `client.BooleanValue(ctx, key, def, evalCtx)` (also `client.Boolean(...)` ignoring error) | `await client.GetBooleanValueAsync(key, def, ctx?)` | `client.get_boolean_value(key, default, ctx?)` | `client.getBooleanValue(key, def, ctx?)` | `await client.getBooleanValue(key, def, ctx?)` |
| Boolean details | `client.BooleanValueDetails(...)` -> `BooleanEvaluationDetails` | `await client.GetBooleanDetailsAsync(...)` -> `FlagEvaluationDetails<bool>` | `client.get_boolean_details(...)` -> `FlagEvaluationDetails` | `client.getBooleanDetails(...)` -> `FlagEvaluationDetails<Boolean>` | `client.getBooleanDetails(...)` -> `EvaluationDetails<boolean>` |
| Evaluation context | `openfeature.NewEvaluationContext(targetingKey, map[string]any)` | `EvaluationContext.Builder().Set(k, v).Build()` | `openfeature.evaluation_context.EvaluationContext(targeting_key, attributes)` | `MutableContext` / `EvaluationContext` | plain object `{ targetingKey, ... }` typed `EvaluationContext` |
| Hook base | interface `openfeature.Hook`; embed `openfeature.UnimplementedHook` | abstract class `Hook` (`BeforeAsync`, `AfterAsync`, `ErrorAsync`, `FinallyAsync`) | `openfeature.hook.Hook` (`before`, `after`, `error`, `finally_after`) | `Hook` / typed `BooleanHook` (`finallyAfter`) | interface `Hook` (`before`, `after`, `error`, `finally`) |
| Event handler registration | `openfeature.AddHandler(openfeature.ProviderReady, &cb)`; `client.AddHandler(...)` | `Api.Instance.AddHandler(ProviderEventTypes.ProviderReady, cb)`; `client.AddHandler(...)` | `api.add_handler(ProviderEvent.PROVIDER_READY, fn)`; `client.add_handler(...)` | `api.onProviderReady(...)`, `client.onProviderConfigurationChanged(...)` | `OpenFeature.addHandler(ProviderEvents.Ready, cb)`; `client.addHandler(...)` |
| In-memory provider | `memprovider.NewInMemoryProvider(map[string]memprovider.InMemoryFlag)` | `OpenFeature.Providers.Memory.InMemoryProvider` | `openfeature.provider.in_memory_provider.InMemoryProvider({key: InMemoryFlag(default_variant, variants)})` | `new InMemoryProvider(myFlags)` | `InMemoryProvider` from `@openfeature/server-sdk` |
| Transaction context | `openfeature.WithTransactionContext(ctx, evalCtx)` on `context.Context` | `Api.Instance.SetTransactionContextPropagator(new AsyncLocalTransactionContextPropagator())`, then `Api.Instance.SetTransactionContext(ctx)` | `api.set_transaction_context_propagator(ContextVarsTransactionContextPropagator())`, `api.set_transaction_context(ctx)` | (unverified) | `OpenFeature.setTransactionContext(ctx, callback)` with an `AsyncLocalStorage` propagator (spec example) |

The sibling reference files for each SDK are authoritative where they differ from this table.

---

## 16. When this file is silent

- Rendered specification: `https://openfeature.dev/specification/` with per-section pages `https://openfeature.dev/specification/sections/flag-evaluation`, `/sections/providers`, `/sections/evaluation-context`, `/sections/hooks`, `/sections/events`, `/sections/tracking`, and `https://openfeature.dev/specification/glossary`, `/types`, `/appendix-a`, `/appendix-b`, `/appendix-c`, `/appendix-d`, `/appendix-e`.
- Spec source: `https://github.com/open-feature/spec` (`specification/*.md`, `specification/sections/*.md`, `specification/assets/gherkin/*.feature`, and the machine-readable `specification.json`).
- Concept docs: `https://openfeature.dev/docs/reference/concepts/<evaluation-api|provider|evaluation-context|hooks|events|sdk-paradigms|tracking>`; intro at `https://openfeature.dev/docs/reference/intro`; tutorial at `https://openfeature.dev/docs/tutorials/five-minutes-to-feature-flags`.
- OFREP: `https://github.com/open-feature/protocol` and `https://openfeature.dev/docs/reference/other-technologies/ofrep/openapi`.
- OpenTelemetry feature-flag conventions: `https://opentelemetry.io/docs/specs/semconv/feature-flags/feature-flags-logs/`.

Grep recipes over a fresh clone (`git clone --depth 1 https://github.com/open-feature/spec`):

```bash
# find a requirement by number
grep -n "Requirement 4.4.2" -r specification/sections
# list every requirement id with its RFC 2119 keyword
python3 -c 'import json; [print(r["id"], r["RFC 2119 keyword"]) for r in json.load(open("specification.json"))["rules"]]'
# all normative statements about a term
grep -n -i "targeting key" -r specification/sections specification/types.md
# enum tables
grep -n -A 12 "### Error Code" specification/types.md
grep -n -A 14 "#### Resolution Reason" specification/types.md
```
