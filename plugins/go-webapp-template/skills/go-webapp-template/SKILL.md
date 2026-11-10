---
name: go-webapp-template
description: Scaffolds a complete Go web application skeleton with server-side rendering (net/http + html/template), HTMX + Alpine.js, PostgreSQL via pgx with goose migrations, Redis caching, and OpenRouter AI — the Go counterpart of fastapi-template, with no Python anywhere. Always use this skill when the user wants to create a new Go web app, start a new Go server project, scaffold a golang backend with templates, set up a Go project structure, or bootstrap a full-stack app in Go. Invoke whenever the user says "new Go web app", "scaffold a Go project", "start a Go server", "Go + HTMX", "golang backend", "net/http app with templates", or anything about bootstrapping a Go web application from scratch. If the user asks for Python/FastAPI, use fastapi-template instead.
argument-hint: "[--host railway|generic] [--ai-model <openrouter model id>]"
---

## Stack

Go port of the `fastapi-template` stack — same features, same env var names, same frontend:

- **Server**: Go `net/http` (1.22+ method/path route patterns) + `html/template` (server-side rendering)
- **Client**: HTMX 2.x (server-driven updates) + Alpine.js 3.x (local state)
- **Database**: PostgreSQL via `pgx/v5` (`pgxpool`, hand-written SQL) + goose (SQL migrations, embedded in the binary)
- **AI**: OpenRouter via plain `net/http`, prompts as `text/template` `.txt` files
- **Cache**: Redis via `go-redis/v9` + a small generic JSON cache helper (`internal/cache`)
- **Auth/session state**: HMAC-signed cookies (`internal/auth`, keyed by `SESSION_SECRET`) — no session store
- **Config**: `godotenv` + `.env.example`
- **Logging**: `log/slog`
- **Deploy**: Railway via `Procfile` + `railpack.json` (explicit `go build ... -o out ./cmd/server` build command) (only when host is `railway`)
- **Tooling**: Go only — `go test`, `gofmt`, `go vet`. No Python, no uv, no pytest.

## Generation Process

Two optional flags in `$ARGUMENTS`; remove them before reading the rest of the arguments:
- `--host railway|generic` (default `railway`). With `generic`, skip every part marked "only when host is `railway`": `Procfile`, `railpack.json`, the `internal/wake` package (see the "Host `generic`" note at the top of `references/go-files.md` for the edits in the files that import it), the Railway pre-deploy command `./out migrate up`, and Railway deploy instructions. The app still reads `PORT` and its connection strings from the environment. Migrations then run by hand (`./out migrate up` against the production `ENGINE_URL`) or in the host's release step.
- `--ai-model <openrouter model id>` (default `openai/gpt-4o-mini`) — the value of `DefaultModel` in `internal/ai/ai.go`.

1. Ask for **app name** (kebab-case) if not provided. It is also the Go module path (`module <app-name>`), so imports are `<app-name>/internal/...`. Derive `<App Name>` (display name in templates) as Title Case of the kebab name (`my-app` → `My App`) unless the user gives one.
2. Confirm which optional features to include:
   - Database/goose (default: yes)
   - AI/OpenRouter (default: ask)
   - Redis caching (default: yes if AI included, otherwise ask)
3. Ask for target directory (default: current directory)
4. Read the three reference files below, then generate all files with both placeholders replaced
5. Copy `.env.example` to `.env` (gitignored) so `make dev` works out of the box

Read these reference files before generating:
- `references/go-files.md` — all Go source templates
- `references/config-files.md` — go.mod, Makefile, Procfile, railpack.json, first migration, .env.example, .gitignore
- `references/html-templates.md` — base.html, index.html, prompt template, static files

After writing files, run in the target directory:

```
go mod tidy && gofmt -l . && go build ./... && go vet ./... && go test ./...
```

`go mod tidy` resolves dependency versions (never hand-pin them) and may raise the `go` directive in `go.mod` to whatever the dependencies require — that is expected. `gofmt -l` must print nothing.

## Project Structure

```
<app-name>/
├── cmd/server/main.go        # `server` serves; `server migrate up|down|status|create <name>`
├── embed.go                  # //go:embed templates static migrations → app.Assets, app.Migrations
├── internal/
│   ├── config/config.go      # godotenv load, MustEnv (fail at startup), DevMode, Env helpers
│   ├── wake/                 # only when host is `railway`
│   │   ├── wake.go           # Ping with retry + Waker (fresh-skip, shared wake) for a sleeping Railway DB/Redis
│   │   └── wake_test.go
│   ├── auth/cookies.go       # HMAC-signed cookies: Get/Set/Clear, IsAuthenticated, RequireAuth
│   ├── db/
│   │   ├── db.go             # pgxpool connect, pool sizing, ping retry
│   │   ├── migrate.go        # goose provider over embedded migrations (wakes the DB first)
│   │   └── items.go          # example Item + hand-written SQL (List/Get/Create/Update/Delete)
│   ├── cache/cache.go        # go-redis client, ping retry, Cached[T] JSON helper
│   ├── ai/ai.go              # RenderPrompt, Invoke (cached), GetResponse, GetJSONResponse
│   └── server/
│       ├── server.go         # Deps, New(): mux, routes, /static/, middleware chain
│       ├── middleware.go     # logRequests (method, path, status, ms), recoverPanics
│       ├── errors.go         # HTTPError + handle(): 401 → 303 "/", log 5xx error / 4xx warn
│       ├── render.go         # html/template parsing (base + page), Render()
│       ├── home.go           # GET /
│       └── server_test.go    # httptest: GET / → 200
├── migrations/
│   └── 00001_create_items.sql   # goose SQL (-- +goose Up / -- +goose Down)
├── templates/
│   ├── base.html             # HTMX + Alpine.js CDNs, hx-boost, blocks
│   ├── index.html            # defines "title" + "content"
│   ├── partials/             # optional: {{define}} blocks for HTMX fragments (RenderPartial)
│   └── prompts/example.txt   # text/template prompt
├── static/css/app.css, static/js/app.js
├── go.mod                    # module <app-name>; go 1.26 (tidy may raise it)
├── Makefile
├── Procfile                  # web: ./out (only when host is `railway`)
├── railpack.json             # explicit build: go build -o out ./cmd/server (only when host is `railway`)
├── .env.example
├── .env                      # local only (gitignored)
└── .gitignore
```

## Critical Patterns (always follow these)

**Env validation** — `config.MustEnv(name)` for every required env var, called in `main` before anything connects. Fail at startup, not on the first request.

**DEV_MODE** — `DEV_MODE=ON` sets `config.DevMode`. Wire it to: slog level (DEBUG vs INFO), cookie `Secure` flag (off in dev so cookies work on http://localhost), cache prefix suffix (`-dev`), and asset source (`os.DirFS(".")` in dev so template/CSS edits show without rebuild; embedded `app.Assets` in prod).

**slog** — one `TextHandler` on stdout with `AddSource: true`; `ReplaceAttr` shortens source to `file:line` and time to `YYYY-MM-DD HH:mm:ss`. Never `log.Printf` or `fmt.Println` for app logs.

**Startup / shutdown** (the lifespan equivalent) — in `run()`: connect pgxpool and ping (with retry), connect Redis and ping (with retry), log both. `signal.NotifyContext` + `srv.Shutdown` with a 10s timeout; `defer pool.Close()` / `defer cache.Close()`.

**Wake before use** (only when host is `railway`; with `generic`, startup and `migrate` ping once and there is no `wakeDeps` middleware) — Railway sleeps idle Postgres/Redis services, so a startup ping is not enough. `wake.Ping` (retry `DB_PING_RETRIES`/`REDIS_PING_RETRIES` times, `*_PING_INTERVAL` seconds apart) runs at startup and in `migrate` before goose touches the DB. On the request path the `wakeDeps` middleware wraps the whole mux (every route except `/static/`, including route middleware) and calls a `wake.Waker`: it pings only when the last result is older than 10s (a failed loop is remembered for 10s too, so requests fail fast instead of each retrying), and concurrent requests share one retry loop. A DB that stays down → 500; a down Redis only logs and continues (nil `Pool`/`Cache` are skipped). Anything that uses the DB/Redis outside a request (goroutines, workers) keeps its own `wake.New(...)` and calls `Wake` before each job or tick.

**Request logging middleware** — always wrap the mux with `logRequests`: a status-capturing `ResponseWriter`, log `METHOD /path -> status (Nms)`. In dev, add `Cache-Control: no-store` to `/static/` responses.

**Error handling** — handlers have the signature `func(w, r) error` and are wrapped by `s.handle()`. Return `server.Err(code, msg)` (an `*HTTPError`); `handle` redirects 401 → `/` (303), logs 5xx as error and 4xx as warning, and turns unknown errors into a logged 500. Render into a buffer first so an error never lands mid-body.

**hx-boost, always** — put `hx-boost="true"` on `<body>` in `base.html` so every link and form navigates via HTMX's AJAX swap instead of a full-page browser navigation. This matters most when the app is wrapped with Capacitor: a full-page reload/redirect flashes white and breaks the native app feel in a WKWebView, while a boosted swap doesn't. Never introduce plain `<a href>` full-page navigation as the primary nav path, and don't add JS `window.location` redirects where an hx-boosted link or form would do.

**Signed cookies, never a session store** — all per-user state that must survive requests (login, OAuth `state`/PKCE, preferences) goes through `auth.Cookies.Get`/`Set`, which HMAC-SHA256-sign values with `SESSION_SECRET` and compare with `hmac.Equal`. `IsAuthenticated`/`RequireAuth` read the `user_id` cookie this way. Do not add `gorilla/sessions`, server-side session tables, or JWT libraries. Call `Set` on the `ResponseWriter` before writing the body — headers are frozen once the first byte is written.

**DB access** — `*pgxpool.Pool` is passed in `server.Deps`, never a package global. One Go process serves all requests, so the pool is sized once (`MaxConns=20`, `MaxConnLifetime=5m`, `HealthCheckPeriod=30s`) — there is no gunicorn-style per-worker split. Queries are plain SQL strings scanned with `pgx.CollectRows`/`pgx.RowToStructByPos`; add `sqlc` only when the query count makes hand-scanning painful.

**Migrations** — goose SQL files only (`-- +goose Up` / `-- +goose Down`), embedded via `app.Migrations` and run by the server binary itself: `make migrate-up` locally; in prod the Railway pre-deploy command (`./out migrate up`, set by the user in the dashboard) runs on every deploy, before the new version takes traffic (the deploy image has only the binary — no `make`, no goose CLI). `make migrate-create name=add_users` writes a timestamped file through `goose.Create`. With `--host generic` there is no Railway pre-deploy command: run `./out migrate up` by hand or in the host's release step.

**AI caching** — `ai.Invoke` hashes the exact request JSON (sha256) and goes through `cache.Cached[*ai.Response]` in namespace `ai-model` with no TTL. The cached value decodes straight back into `*Response`, so there is no dict-vs-object split to handle (unlike the Python version).

**Models** — UUID PKs via `id uuid PRIMARY KEY DEFAULT gen_random_uuid()` in the migration; Go structs use `ID string` and queries select `id::text` so no uuid dependency is needed.

**Prompt templates** — `text/template` `.txt` files under `templates/prompts/`, parsed once in `ai.New` with `template.ParseFS(assets, "templates/prompts/*.txt")`. Render with `RenderPrompt("example", data)`.

**HTMX loading** — `<script src="https://unpkg.com/htmx.org@2.0.4" integrity="sha384-HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+" crossorigin="anonymous"></script>` in `<head>`.

**Alpine.js loading** — `<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js"></script>` at end of `<body>`, after `app.js`.

## Customization Checklist

After generating, remind the user to:
- Fill in real values in `.env` (`ENGINE_URL`, `REDIS_CONNECTION_STRING`, `SESSION_SECRET`, `OPENROUTER_API_KEY`)
- Delete the example `internal/db/items.go` and `migrations/00001_create_items.sql`, then `make migrate-create name=<first_table>` and write real SQL
- Replace `templates/prompts/example.txt` with real prompt templates
- Run `make migrate-up` after adding migrations
- With a database and host `railway`: in Railway, open the service → Settings → Deploy → Pre-deploy Command and set `./out migrate up` before the first deploy (this skill uses no `railway.json` / config-as-code)
- With a database and host `generic`: run `./out migrate up` by hand or in the host's release step on every deploy
- Run `make dev` to start the dev server
