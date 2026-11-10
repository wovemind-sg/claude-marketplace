# Claude Code Skills Marketplace

A collection of Claude Code skills — domain-specific knowledge packs that make Claude more capable for specific tasks.

## Available Skills

### HTMX vs Alpine.js (`htmx-vs-alpine`)

Guides Claude to choose between HTMX and Alpine.js for client-side interactivity in server-rendered web applications.

**Triggers when you ask about:**
- Form submission, search, pagination, modals, dropdowns
- UI toggles, tabs, accordions, infinite scroll, polling
- Any interactive element in a server-rendered context

---

### Supabase Python (`supabase-python`)

FastAPI with Supabase and SQLAlchemy/SQLModel patterns.

**Triggers when you ask about:**
- FastAPI + Supabase projects
- SQLModel or SQLAlchemy with Supabase
- Python backend with Supabase auth or database

---

### Singapore LTA DataMall API (`singapore-lta`)

Query Singapore's Land Transport Authority (LTA) DataMall API for real-time and static transport data. Covers bus arrivals, routes and stops, taxi availability, car park availability, traffic incidents, train service alerts, station crowd density, EV charging points, and more.

**Triggers when you ask about:**
- Singapore bus arrivals, routes, or stops
- Singapore traffic incidents, speed bands, or travel times
- Singapore taxi or car park availability
- Singapore train/MRT service alerts or crowd levels
- LTA DataMall API

---

### ntfy (`ntfy`)

Send push notifications to phone/desktop via a self-hosted [ntfy](https://ntfy.sh) instance over its HTTP API. Covers titles, priority, tags, action buttons, attachments, scheduled delivery, and markdown formatting.

**Triggers when you ask about:**
- Being notified, pinged, or alerted when a task finishes or fails
- Sending a push notification, even without saying "ntfy" explicitly

### OpenFeature (`openfeature`)

Complete reference for [OpenFeature](https://openfeature.dev/), the CNCF vendor-neutral feature-flag standard: spec concepts, providers, hooks, events, evaluation context, OFREP, CLI, MCP server and ecosystem, with deep-dive references for the Go, .NET (C#) and Python SDKs.

**Triggers when you ask about:**
- Adding feature flags, percentage rollouts, A/B tests or kill switches to an app in any language
- OpenFeature SDKs, providers, hooks, `EvaluationContext`, `targetingKey`, `PROVIDER_READY`, `FLAG_NOT_FOUND`
- OFREP, the `openfeature` CLI, migrating between flag vendors, writing a custom provider

---

### UI Audit (`ui-audit`)

Before/after screenshots and motion clips of every screen a PR really changed, with unintended changes flagged, published as a Claude artifact or to Cloudflare Pages (behind a password on private repos) and linked from the PR. Web via Playwright (desktop and mobile emulation); Capacitor and Expo via simulators (untested on real apps).

**Triggers when you ask about:**
- Screenshots of UI changes, a visual audit or visual regression check for a PR
- Before/after images to show reviewers what the UI looks like

---

## Installation

```bash
claude plugin marketplace add wovemind-sg/claude-marketplace
claude plugin install htmx-vs-alpine@wovemind --scope user
claude plugin install supabase-python@wovemind --scope user
claude plugin install singapore-lta@wovemind --scope user
claude plugin install fastapi-template@wovemind --scope user
claude plugin install ntfy@wovemind --scope user
claude plugin install ui-audit@wovemind --scope user
```

## Refreshing After Changes

```bash
claude plugin marketplace remove wovemind
claude plugin marketplace add wovemind-sg/claude-marketplace
claude plugin install htmx-vs-alpine@wovemind --scope user
claude plugin install supabase-python@wovemind --scope user
claude plugin install singapore-lta@wovemind --scope user
claude plugin install fastapi-template@wovemind --scope user
claude plugin install ntfy@wovemind --scope user
```
