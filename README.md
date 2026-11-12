# Wovemind Claude Code plugins

```bash
claude plugin marketplace add wovemind-sg/claude-marketplace
claude plugin install <plugin>@wovemind
```

Open-source Claude Code plugins from Wovemind: skills, agents and hooks for web, mobile and AI app development. Each plugin lives in its own folder under `plugins/`, and each folder has a `README.md` with its requirements, settings and an example.

## Who we are, how we use it, our zen

We are Wovemind. Our team is a UX/UI designer who is not a software engineer, and a very small team of software engineers. The idea is to empower the designer to be independent and make code changes with Claude Code, without compromising on the safety and correctness of the products. These plugins are how we do that, published so you can use them too.

How we use it: we write a plan before any code, and split big plans into context-sized sessions that each run on their own (`plan-tools`). Work moves from a GitHub issue to a merged pull request with as little hand-holding as possible, so the designer does not need to know the engineering workflow. Every pull request that touches the UI carries before and after screenshots (`ui-audit`), and UI changes are reviewed before we push (`ui-change-guard`), so a change can be checked by looking at it and mistakes are caught before they ship.

Our zen:

- Plan before code.
- Ask instead of guessing.
- Make the smallest complete change.
- Show the result, not just the diff, so a designer can check it.
- Automate the loop from issue to merged pull request.

## Plugins

### Workflow

| Plugin | What it does | Install |
|---|---|---|
| [plan-tools](plugins/plan-tools) | plan-driven workflow: bootstrap a new web or mobile app, split plans into context-sized sessions, and drive them to pull requests. | `claude plugin install plan-tools@wovemind` |
| [explain](plugins/explain) | explains code and concepts in the current project, building on what you already know. | `claude plugin install explain@wovemind` |
| [session-overview](plugins/session-overview) | a side pane (`/sessions`) listing every open Claude Code session on the machine, grouped by project. | `claude plugin install session-overview@wovemind` |

### UI quality

| Plugin | What it does | Install |
|---|---|---|
| [ui-audit](plugins/ui-audit) | before and after screenshots and clips of every screen a pull request changed, linked from the pull request. | `claude plugin install ui-audit@wovemind` |
| [design-inspiration](plugins/design-inspiration) | finds design references for your app on Dribbble-like sites, lets you rate a shortlist per page, optionally mocks up your pages in that look, then plans how to apply the ones you picked. | `claude plugin install design-inspiration@wovemind` |
| [ui-change-guard](plugins/ui-change-guard) | reviews UX/UI changes before you push, for lost functionality, broken wiring and regressions. | `claude plugin install ui-change-guard@wovemind` |
| [user-flows](plugins/user-flows) | extracts the user flows of an application into `user-flows.md` and keeps Playwright tests for them in sync. | `claude plugin install user-flows@wovemind` |
| [product-experience-strategist](plugins/product-experience-strategist) | product strategy, UX/UI and business judgment for designing and reviewing digital products and their flows. | `claude plugin install product-experience-strategist@wovemind` |

### Scaffolding

| Plugin | What it does | Install |
|---|---|---|
| [fastapi-template](plugins/fastapi-template) | scaffolds a FastAPI, Jinja2, HTMX and Alpine.js web app with PostgreSQL, Redis and OpenRouter AI. | `claude plugin install fastapi-template@wovemind` |
| [go-webapp-template](plugins/go-webapp-template) | scaffolds the same kind of app in Go, and migrates an existing fastapi-template project to Go. | `claude plugin install go-webapp-template@wovemind` |
| [htmx-vs-alpine](plugins/htmx-vs-alpine) | decides whether HTMX or Alpine.js should drive each piece of interactivity in a server-rendered app. | `claude plugin install htmx-vs-alpine@wovemind` |

### Libraries and references

| Plugin | What it does | Install |
|---|---|---|
| [python-arq](plugins/python-arq) | reference for the arq library: async job queues in Python with asyncio and Redis. | `claude plugin install python-arq@wovemind` |
| [flagd](plugins/flagd) | reference for flagd, the OpenFeature feature-flag evaluation engine. | `claude plugin install flagd@wovemind` |
| [openfeature](plugins/openfeature) | reference for OpenFeature, the vendor-neutral feature-flag standard, with deep dives for Go, .NET and Python. | `claude plugin install openfeature@wovemind` |

### Notifications

| Plugin | What it does | Install |
|---|---|---|
| [ntfy](plugins/ntfy) | send push notifications to your phone or desktop through an ntfy server. | `claude plugin install ntfy@wovemind` |
| [desktop-notify](plugins/desktop-notify) | sends macOS desktop notifications through `claude-notifier` when a task finishes or Claude needs you. | `claude plugin install desktop-notify@wovemind` |

### Compliance

| Plugin | What it does | Install |
|---|---|---|
| [compliance-audit](plugins/compliance-audit) | audits a product repository for legal and regulatory compliance gaps and implements the fixes as pull requests (not legal advice). | `claude plugin install compliance-audit@wovemind` |

### Media

| Plugin | What it does | Install |
|---|---|---|
| [launch-video](plugins/launch-video) | turns an app repository into a launch video with a presenter, screen recordings, voice-over and captions. | `claude plugin install launch-video@wovemind` |

## Refresh after changes

Fetch the latest version of the marketplace, then update each plugin you installed:

```bash
claude plugin marketplace update wovemind
claude plugin update <plugin>@wovemind
```

Inside a session, run `/reload-plugins` afterwards so the session picks up the new versions.

## Licence

MIT. See [`LICENSE`](LICENSE).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).
