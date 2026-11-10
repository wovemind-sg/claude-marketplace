# go-webapp-template

Scaffolds a complete Go web application skeleton — the Go counterpart of `fastapi-template`, with the same features, env var names and frontend, and no Python anywhere.

## Stack

- **Server**: Go `net/http` + `html/template` (server-side rendering)
- **Client**: HTMX 2.x + Alpine.js 3.x
- **Database**: PostgreSQL via pgx/v5 + goose SQL migrations (embedded, run by the server binary)
- **AI**: OpenRouter + `text/template` prompt templates + Redis caching
- **Cache**: Redis via go-redis/v9 + generic `Cached[T]` helper
- **Auth/session state**: HMAC-signed cookies (`internal/auth`), no session store
- **Logging**: `log/slog`
- **Deploy**: Railway (Procfile + `railpack.json` with an explicit `go build -o out ./cmd/server`) by default; with `--host generic`, none of the Railway files or wake-up code, so you deploy the `./out` binary to any host

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install go-webapp-template@wovemind
```

## Requirements

To run the generated app:

- Go. The generated `go.mod` says `go 1.26`; Go 1.21 or newer downloads that toolchain automatically. The code itself needs 1.22+ for its route patterns.
- `make` for the `make dev`, `make test` and migration targets.
- A PostgreSQL database and a Redis server, when those parts are included.
- An OpenRouter API key, when the AI part is included.
- For deploying with the default host, a Railway account.

The `fastapi-go-migration` skill has its own requirements, listed in its section below, and uses the `plan-tools` plugin for big repos (it asks you to install `plan-tools@wovemind` if it is missing).

## Opinionated defaults

| Default | Change it with |
|---|---|
| Deploy to Railway: `Procfile`, `railpack.json`, the `internal/wake` package that retries a sleeping Railway database or Redis, and `./out migrate up` as Railway's pre-deploy command | `--host generic` (then run `./out migrate up` by hand or in your host's release step) |
| AI calls go to OpenRouter with the model `openai/gpt-4o-mini` | `--ai-model <openrouter model id>` |
| Server listens on port 8000 | `PORT` in the environment |
| `fastapi-go-migration` works on a branch named `go-migration` | `--branch <name>` |

## Usage

Invoke the skill by asking Claude to scaffold a new Go web app:

```
/go-webapp-template:go-webapp-template create a new app called my-app
/go-webapp-template:go-webapp-template [--host railway|generic] [--ai-model <openrouter model id>]   # defaults railway, openai/gpt-4o-mini
```

Or just describe what you want:

> "Scaffold a new Go web app with HTMX for a task management tool"

## Generated Structure

```
<app-name>/
├── cmd/server/main.go       # serve, or `migrate up|down|status|create <name>`
├── embed.go                 # embeds templates/, static/, migrations/
├── internal/
│   ├── config/
│   ├── wake/                # ping-with-retry for a sleeping Railway DB/Redis (railway host only)
│   ├── auth/                # signed cookies
│   ├── db/                  # pgxpool, goose, example queries
│   ├── cache/
│   ├── ai/
│   └── server/              # routes, middleware, errors, rendering, tests
├── migrations/
├── templates/
│   ├── base.html
│   ├── index.html
│   └── prompts/
├── static/
├── go.mod
├── Makefile
├── Procfile                 # railway host only (the default)
├── .env.example
└── .gitignore
```

## Environment variables

The plugin itself needs none and has no plugin settings. The generated app reads these from `.env`:

| Variable | Description |
|---|---|
| `ENGINE_URL` | PostgreSQL connection string |
| `REDIS_CONNECTION_STRING` | Redis URL |
| `SESSION_SECRET` | Random secret for HMAC-signing cookies (`internal/auth`) |
| `OPENROUTER_API_KEY` | OpenRouter API key (if using AI) |
| `DEV_MODE` | Set to `ON` for development |
| `PORT` | Listen port (default `8000`; Railway sets it) |

## Quick Start

After scaffolding:

```bash
cd <app-name>
cp .env.example .env
# edit .env with real values
go mod tidy
make migrate-up   # apply migrations
make dev          # start dev server at localhost:8000
make test         # go test ./...
```

With `--host generic`, run `./out migrate up` against the production `ENGINE_URL` yourself, or in your host's release step. Deployed on Railway, set `./out migrate up` as the service's pre-deploy command in the Railway dashboard (Settings → Deploy → Pre-deploy Command) so it runs on every deploy. To run it by hand:

```bash
railway ssh --service "<service name>" -- ./out migrate up
```

## Example

```
/go-webapp-template:go-webapp-template create a new app called recipe-box --host generic
```

This generates `recipe-box/` with no `Procfile`, `railpack.json` or `internal/wake`. Follow the Quick Start above, then build with `go build -o out ./cmd/server` and run `./out` on your host.

## Migrating a fastapi-template project (`fastapi-go-migration`)

The second skill in this plugin converts an existing project that was scaffolded with `fastapi-template` into this Go stack, in place, in the same repo:

```
/go-webapp-template:fastapi-go-migration [--branch <name>]   # default branch go-migration
```

Or just say "migrate this app to Go" inside the project. What it does:

1. **Inventory** — `scripts/inventory.py` (stdlib only) lists every route, model, Jinja construct, custom filter, env var, grown feature (arq, OAuth, email, …), and how tests/deploy start the app. Written to `.planning/inventory.md` so later sessions never need the Python source wholesale.
2. **Baseline migration** — `scripts/baseline_ddl.py` (run with `uv run` while Python still exists) emits `migrations/00001_baseline.sql` from the SQLModel metadata with `CREATE … IF NOT EXISTS`: a no-op on the production DB Alembic already migrated, a full schema on a fresh one. `Down` is intentionally empty.
3. **Plan** — a Plan subagent writes `.planning/SPEC.md` (sessions per router group, FuncMap for custom filters, cookie-signer check, unit-test port/delete list); every feature with no Go counterpart is resolved with you in one question; big repos go through `plan-tools:split-plan`.
4. **Port** — session by session: `internal/db/<table>.go` → handlers → templates (Jinja2 → `html/template` per `references/templates.md`), with `go build/vet/test` and a Python-vs-Go route parity check (`inventory.py --go-routes`) after each.
5. **Gates** — route parity, cookie vector test (existing sessions survive), render-every-page with `missingkey=error`, baseline applied twice, e2e suite green against the Go binary.
6. **Cutover** — rewrite `tests/conftest.py` to run `./out`, tests-only `pyproject.toml`, `railpack.json` (Go provider plus an explicit `./cmd/server` build command, so Railway neither picks Python nor builds the root `embed.go` package), delete `app/`, `alembic/`, update CI/README/CLAUDE.md, and print the deploy checklist. The skill never deploys or touches the production DB.

Requirements: Go ≥ 1.22, `uv`, a reachable Postgres for proving the baseline, Redis if the app uses it. Python Playwright e2e tests under `tests/` are kept (they are black-box HTTP tests); Python unit tests are ported to Go or deleted per file.
