# Wovemind Claude Code plugins

Open-source Claude Code plugins from Wovemind: skills, agents and hooks for web, mobile and AI app development. Each plugin lives in its own folder under `plugins/`, and each folder has a `README.md` with its requirements, settings and an example.

## Install

Add the marketplace once:

```bash
claude plugin marketplace add wovemind-sg/claude-marketplace
```

Then install the plugins you want, from your shell or inside a Claude Code session:

```bash
claude plugin install <plugin>@wovemind
```

```
/plugin install <plugin>@wovemind
```

For example, `claude plugin install ntfy@wovemind`.

## Refresh after changes

Fetch the latest version of the marketplace, then update each plugin you installed:

```bash
claude plugin marketplace update wovemind
claude plugin update <plugin>@wovemind
```

Inside a session, run `/reload-plugins` afterwards so the session picks up the new versions.

## Plugins

### Development

- **singapore-lta**: query Singapore's Land Transport Authority DataMall API for bus arrivals, traffic, car parks, train alerts and more (Singapore only).
- **supabase-python**: FastAPI with Supabase for auth and storage, and SQLAlchemy or SQLModel for database queries.
- **htmx-vs-alpine**: decides whether HTMX or Alpine.js should drive each piece of interactivity in a server-rendered app.
- **fastapi-template**: scaffolds a FastAPI, Jinja2, HTMX and Alpine.js web app with PostgreSQL, Redis and OpenRouter AI.
- **go-webapp-template**: scaffolds the same kind of app in Go, and migrates an existing fastapi-template project to Go.
- **plan-tools**: plan-driven workflow: bootstrap a new web or mobile app, split plans into context-sized sessions, and drive them to pull requests.
- **ntfy**: send push notifications to your phone or desktop through an ntfy server.
- **evolution-api**: endpoint reference for writing WhatsApp client code against an Evolution API server.
- **whatsapp-safety**: keeps WhatsApp automation through Evolution API from getting the number flagged or banned.
- **user-flows**: extracts the user flows of an application into `user-flows.md` and keeps Playwright tests for them in sync.
- **product-experience-strategist**: product strategy, UX/UI and business judgment for designing and reviewing digital products and their flows.
- **python-arq**: reference for the arq library: async job queues in Python with asyncio and Redis.
- **flagd**: reference for flagd, the OpenFeature feature-flag evaluation engine.
- **openfeature**: reference for OpenFeature, the vendor-neutral feature-flag standard, with deep dives for Go, .NET and Python.
- **ui-change-guard**: reviews UX/UI changes before you push, for lost functionality, broken wiring and regressions.
- **compliance-audit**: audits a product repository for legal and regulatory compliance gaps and implements the fixes as pull requests (not legal advice).
- **ui-audit**: before and after screenshots and clips of every screen a pull request changed, linked from the pull request.

### Productivity

- **sg-card-benefits**: monitors Singapore credit and debit card benefits and terms for changes (Singapore only).
- **desktop-notify**: sends macOS desktop notifications through `claude-notifier` when a task finishes or Claude needs you.
- **launch-video**: turns an app repository into a launch video with a presenter, screen recordings, voice-over and captions.
- **explain**: explains code and concepts in the current project, building on what you already know.
- **session-overview**: a side pane (`/sessions`) listing every open Claude Code session on the machine, grouped by project.
- **marketplace-promote**: gets your plugin marketplace listed in plugin directories and awesome lists, with pre-flight checks, PRs, prefilled web forms and a status report.

## Licence

MIT. See [`LICENSE`](LICENSE).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).
