---
name: htmx-vs-alpine
description: >
  Decides whether to use HTMX or Alpine.js when writing frontend code for server-rendered web apps.
  Use this skill whenever you are implementing any client-side behavior — form submission, UI toggles,
  search, pagination, modals, dropdowns, filtering, infinite scroll, tabs, accordions, polling, lazy
  loading, or any interactive element — even if the user hasn't explicitly mentioned HTMX or Alpine.js.
  Always apply this skill before reaching for custom JavaScript in a server-rendered context.
---

# HTMX vs Alpine.js Decision Guide

You are an expert web application architect specializing in server-driven web applications. Before
writing any client-side interactivity, apply the decision framework below.

---

## Core Philosophy

- **HTMX** — server drives state and renders HTML. The browser is a dumb terminal.
- **Alpine.js** — browser drives ephemeral UI state. No server round-trip needed.
- Prefer server-rendered HTML over JSON APIs. Avoid SPA patterns unless the user explicitly needs them.

---

## The Two Key Questions

Before implementing anything, ask:

**1. Who owns this state?**
- Server owns it → HTMX
- Browser owns it temporarily → Alpine.js

**2. Should this state survive a page refresh?**
- Yes → HTMX (server must persist it)
- No → Alpine.js is fine

If you're still unsure: **default to HTMX** for data/state, **Alpine.js** for presentation/interactivity.

---

## Use HTMX When…

The server should render or own the result. Common cases:

| Scenario | Why HTMX |
|---|---|
| Form submission / CRUD | Server validates and persists |
| Search / filter / sort | Server queries the database |
| Pagination / infinite scroll | Server returns the next page |
| Lazy loading content | Server renders the fragment |
| Multi-step workflows | Server tracks step state |
| Notifications from backend | Server owns notification data |
| Authentication-gated UI | Server checks auth |
| Polling for updates | Server is the source of truth |

### HTMX Attribute Cheatsheet

```html
hx-get="/results"           <!-- fetch HTML via GET -->
hx-post="/items"            <!-- submit via POST -->
hx-put="/items/1"           <!-- update via PUT -->
hx-delete="/items/1"        <!-- delete via DELETE -->
hx-trigger="click"          <!-- when to fire (default: natural event) -->
hx-target="#results"        <!-- where to inject the response -->
hx-swap="innerHTML"         <!-- how to swap: innerHTML, outerHTML, beforeend… -->
hx-select="#partial"        <!-- extract a subset of the response -->
hx-indicator="#spinner"     <!-- show a loading element while request is in flight -->
```

### HTMX Best Practices

- Return **HTML fragments** from the server, not JSON.
- Use `hx-indicator` to show loading state — don't duplicate it with Alpine.js.
- Lean on progressive enhancement: the page should still work without JavaScript when possible.
- Avoid duplicating server state on the client; the server is the single source of truth.
- Make failed requests visible: htmx 2 does not swap 4xx/5xx responses, so handle `htmx:responseError`, `htmx:sendError` and `htmx:timeout` app-wide with user-visible feedback (the UI is the app's choice), never console-only.

---

## Use Alpine.js When…

The interactivity is local, visual, and ephemeral — no server round-trip needed. Common cases:

| Scenario | Why Alpine.js |
|---|---|
| Dropdown open/close | Pure browser state |
| Modal show/hide | Triggered locally |
| Tabs / accordions | No persistence needed |
| Toggle buttons | Local boolean |
| Copy-to-clipboard | Browser API call |
| Client-side input formatting | Cosmetic, pre-submission |
| Loading / skeleton states | Transient UI polish |
| Simple animations | CSS-driven |
| Keyboard shortcuts | Browser event listeners |

### Alpine.js Attribute Cheatsheet

```html
x-data="{ open: false }"    <!-- component scope -->
x-show="open"               <!-- conditional visibility -->
x-bind:class="{ ... }"      <!-- dynamic class binding -->
x-model="query"             <!-- two-way input binding -->
x-transition                <!-- enter/leave animations -->
@click="open = !open"       <!-- event listener -->
x-effect="..."              <!-- reactive side effect -->
x-init="fetchSomething()"   <!-- run on mount -->
```

### Alpine.js Best Practices

- Keep `x-data` scopes small and local. One component, one concern.
- Avoid global stores (`Alpine.store`) unless you genuinely need cross-component state.
- Don't duplicate business logic from the server in Alpine.js — use it only for display behavior.
- Don't reach for Alpine.js to build client-side routing or SPA patterns.

---

## Using Both Together

HTMX and Alpine.js complement each other naturally:

- **HTMX** fetches and swaps server-rendered HTML fragments.
- **Alpine.js** adds interactivity *inside* those fragments.

**Example — notifications panel:**
```html
<!-- HTMX loads the panel from the server -->
<div hx-get="/notifications" hx-trigger="load" hx-target="#panel">
  <div id="panel">Loading…</div>
</div>

<!-- Alpine.js controls expand/collapse within the server-rendered fragment -->
<div x-data="{ expanded: false }">
  <button @click="expanded = !expanded">Toggle details</button>
  <div x-show="expanded" x-transition>…notification body…</div>
</div>
```

The server owns *which* notifications exist. The browser owns *whether* a notification is expanded.

---

## Architecture Defaults

For standard apps (dashboards, admin tools, internal tools, forms, business apps):

1. HTMX is the **primary** interaction model.
2. Alpine.js is a **lightweight complement** for UI behavior only.
3. Custom JavaScript should be the **exception**, not the rule.

Avoid recreating React or Vue patterns manually. If the requirement calls for complex client-side state,
recommend a proper SPA framework rather than fighting against the server-rendered model.
