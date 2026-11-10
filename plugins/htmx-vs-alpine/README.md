# htmx-vs-alpine

Guides Claude to make principled decisions between HTMX and Alpine.js when building client-side interactivity in server-rendered web applications.

## What it does

When you're building a server-rendered app and need to add interactivity, Claude often has to decide whether a feature should be driven by HTMX (server fetches and swaps HTML) or Alpine.js (local browser state). This skill encodes a clear decision framework so Claude consistently picks the right tool — and explains why.

## When it activates

The skill triggers whenever Claude needs to implement any client-side behavior in a server-rendered context:

- Form submission, CRUD operations, search, filtering, pagination
- Modals, dropdowns, tabs, accordions, toggles
- Infinite scroll, lazy loading, polling
- Any scenario where you'd otherwise reach for custom JavaScript

## Decision framework

**Use HTMX when the server owns the state** — form submissions, database queries, authenticated UI, multi-step workflows, real-time updates from the backend.

**Use Alpine.js when the browser owns the state temporarily** — open/close dropdowns, show/hide modals, tabs, copy-to-clipboard, transient UI polish.

**Use both together** — HTMX fetches server-rendered fragments; Alpine.js enhances interactivity inside those fragments.

The two quick questions to ask:
1. *Who owns this state?* → Server = HTMX, Browser = Alpine.js
2. *Should this survive a page refresh?* → Yes = HTMX, No = Alpine.js

## Installation

```bash
/plugin install htmx-vs-alpine@wovemind
```

## Usage

The skill activates automatically when Claude is writing frontend code in a server-rendered context. No explicit invocation needed.

You can also invoke it directly:

```
/htmx-vs-alpine:htmx-vs-alpine
```

## Architecture philosophy

This skill defaults to HTMX as the primary interaction model for business apps, dashboards, admin tools, and internal tooling — with Alpine.js as a lightweight complement for UI-only behavior. It actively discourages recreating SPA patterns manually and avoids unnecessary client-side complexity.
