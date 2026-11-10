---
name: fastapi-go-migration
description: Migrates an existing FastAPI web app that was scaffolded with the fastapi-template skill (FastAPI + Jinja2 + SQLModel/Alembic + fastapi-cache2 + OpenRouter + signed cookies) to the go-webapp-template stack (net/http + html/template + pgx/goose + go-redis + slog) in place, in the same repo — inventory, idempotent goose baseline from the Alembic schema, per-module port, template conversion, parity gates, then Python removal and Railway cutover. Use this skill whenever the user wants to move, port, convert, rewrite, or migrate a Python/FastAPI backend to Go or golang, says "replace FastAPI with Go", "rewrite the backend in Go", "fastapi to go", "make this a Go app", or asks what it would take to drop Python from a web app — even if they do not name either template. Not for scaffolding a brand-new Go app (use go-webapp-template) and not for Python-only changes.
---

## What this skill does

Turns a `fastapi-template` project into a `go-webapp-template` project **in the same repository**: same routes, same templates (converted), same env var names, same cookies (existing sessions survive), same Railway service. Python is deleted at the end, after the Go build passes every gate. The two templates were designed as mirrors, so the skeleton maps 1:1; the real work is the routes, models, templates and whatever the project grew beyond the skeleton.

Fixed decisions — do not re-ask:
- In place, on a `go-migration` branch. Nothing is committed without the user's ok; nothing is deployed by the skill.
- Alembic is replaced by one **idempotent** goose baseline (`CREATE ... IF NOT EXISTS`) that is a no-op on the production DB and builds the schema on a fresh one. `alembic_version` stays until a later migration drops it.
- Python Playwright e2e tests under `tests/` are kept and pointed at the Go binary (the only Python left; `uv` stays for them). Python unit tests are ported or deleted per file.
- Go source comes from the `go-webapp-template:go-webapp-template` skill at runtime. Load it with the Skill tool and read its three reference files; never copy its templates into this skill.

## References (read when the phase needs them)

- `references/mapping.md` — Python → Go for every skeleton file and FastAPI construct (routing, forms, responses, Depends, cookies, cache, AI, SQLModel → SQL + structs, deploy files).
- `references/templates.md` — Jinja2 → html/template syntax table, the four additions to `render.go` (layout chains, FuncMap, `view()` globals, `missingkey=error`), autoescape differences, render-all-pages test.
- `references/grown-features.md` — arq, OAuth, push, Capacitor, email, webhooks, Pillow, numpy, MCP, i18n, websockets… each with a Go equivalent or an explicit **ask**.
- `references/pitfalls.md` — each pitfall with the check that catches it.
- `references/cutover.md` — conftest rewrite, tests-only pyproject, `railpack.json`, Python deletion list, CI/README/CLAUDE.md, the deploy checklist for the user (including the pre-deploy command they set in Railway).

Scripts (invoke with `${CLAUDE_PLUGIN_ROOT}/skills/fastapi-go-migration/scripts/...`):
- `inventory.py <repo> [--json|--md] [--go-routes]` — stdlib-only; everything the migration must account for, and later the Python-vs-Go route parity gate.
- `baseline_ddl.py --models app.db.models [--exclude-schema auth]` — run with `uv run` inside the project while Python still exists; prints the goose baseline.

## Phase 0 — Preflight

1. Confirm this is a fastapi-template project: `app/__init__.py` with `_assert_env`, `app/main.py`, `alembic/`, `pyproject.toml`. If not, say so and stop — the mapping assumes the template's shape.
2. `git status` clean. Create/switch to `go-migration`.
3. Toolchain: `go version` ≥ 1.22, `uv`, `psql` or a Docker Postgres you can reach (needed to prove the baseline), Redis reachable if the app uses it. Missing Go → tell the user how to install, stop.
4. Read the root `CLAUDE.md`, `README.md`, `Procfile` / `start.sh`, `Makefile`, `.github/workflows/*`, `tests/conftest.py`, `.env.example`. These say how the app is actually run and deployed; grown projects differ from the template here.
5. Load `go-webapp-template:go-webapp-template` (Skill tool) and read `references/go-files.md`, `config-files.md`, `html-templates.md` from it. Module path = the kebab-case app name from `pyproject.toml` unless the user says otherwise.

## Phase 1 — Inventory

```
mkdir -p .planning
python3 ${CLAUDE_PLUGIN_ROOT}/skills/fastapi-go-migration/scripts/inventory.py . --json > .planning/inventory.json
python3 ${CLAUDE_PLUGIN_ROOT}/skills/fastapi-go-migration/scripts/inventory.py . --md   > .planning/inventory.md
```

Read `inventory.md`. It is the map for every later step: routes per router, models with Python-side defaults flagged, every Jinja construct and custom filter in use, env vars, grown features, how tests start the server, where migrations run in deploy. Later sessions read this file, not the Python source wholesale — that is what keeps a big repo inside the context window. Check `warnings[]`; anything the script could not parse you must read by hand now and add to the md.

## Phase 2 — Baseline migration (Python still alive)

```
mkdir -p migrations
uv run python ${CLAUDE_PLUGIN_ROOT}/skills/fastapi-go-migration/scripts/baseline_ddl.py \
    --models app.db.models [--exclude-schema auth] > migrations/00001_baseline.sql
```

Pass `--exclude-schema` for every schema `alembic/env.py`'s `include_object` skips (the template skips `auth`). Prove the file: create a scratch database, `psql -v ON_ERROR_STOP=1 -f migrations/00001_baseline.sql` **twice** — the second run must succeed with only "already exists, skipping" notices. If a copy of the production schema is available, run it there too (no-op expected) or `pg_dump --schema-only` both and diff. Also grep `alembic/versions` for `INSERT` — seed data from data migrations must be appended to the baseline.

The `Down` section is deliberately empty. Leave it that way.

## Phase 3 — Mapping plan

Spawn a Plan subagent with: `.planning/inventory.md`, `references/mapping.md`, `references/templates.md`, `references/grown-features.md`, and the instruction to load `go-webapp-template:go-webapp-template`. It writes `.planning/SPEC.md` containing:

- the Go module path and the stack slice (no `internal/ai` if no AI, no `internal/cache` if no Redis — `go mod tidy` drops the dependency with the file);
- the FuncMap list (every custom Jinja filter → Go func) and the `view()` globals list;
- the cookie-signer finding: is `app/utils.py` identical to the template's? If not, what changed;
- per Python unit-test file: port or delete;
- every **ask** item from `grown-features.md` found in the inventory, with the options;
- the session list: session 1 is always the Go skeleton; then one session per router group (its db functions → handlers → templates), then one per cross-cutting feature (AI, jobs, email, webhooks, MCP…), then template residue, then gates, then cutover. Each session names its routes, so parity can be checked per session.

Resolve all **ask** items with the user in **one** AskUserQuestion, write the answers into SPEC.md, then:
- ≤ 3 routers and no grown features → one implementing subagent runs the sessions in order.
- Otherwise → `/plan-tools:split-plan` on SPEC.md, then `/plan-tools:plan-split-implment`. If the `plan-tools` plugin is not installed (`/plan-tools:split-plan` is not in the skill list), tell the user to install it (`/plugin install plan-tools@wovemind`) and wait. Progress lives in `.planning/progress.md` and in the repo itself (which Go files exist, what `--go-routes` reports), so any later session can resume from the diff.

## Session rules (every implementing session)

1. Load `go-webapp-template:go-webapp-template`; read only the reference file this session needs (`mapping.md` for handlers/db, `templates.md` for pages, `grown-features.md` for a feature).
2. Order inside a session: `internal/db/<table>.go` (struct + `cols` const + only the queries the handlers call) → `internal/server/<router>.go` handlers + routes in `server.New` → the templates those handlers render, with their partials.
3. Keep names and paths identical to the Python routes. Keep status codes (422 for form validation, 303 vs 307 as the Python code had them). Set headers and cookies before rendering.
4. Session 1 additionally: the four `render.go` additions from `templates.md`, `internal/auth/cookies_test.go` with a vector from `uv run python -c "from app.utils import _sign; print(_sign('abc'))"`, `writeJSON` helper if the inventory has JSON routes, `import _ "time/tzdata"` if it has timezones, and `go build ./...` green with `GET /` rendering `index.html`.
5. End of every session:
   ```
   gofmt -l . && go vet ./... && go test ./... && \
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/fastapi-go-migration/scripts/inventory.py . --go-routes
   ```
   `--go-routes` prints Python routes still missing in Go; the session's own routes must not be among them. Then commit (semantic message, pre-approved for the branch only if the user said so; otherwise stop and ask once for the whole branch).
6. Run the Python app on one port and the Go app on another while porting; `curl -i` the same URL on both when in doubt about a status code or header.

## Gates (all must pass before cutover)

| Gate | Command / proof |
|---|---|
| Build, vet, tests | `gofmt -l .` prints nothing; `go vet ./...`; `go test ./...` |
| Route parity | `inventory.py . --go-routes` exits 0 |
| Cookies | `cookies_test.go` vector passes; a browser with a Python-era cookie is still logged in on the Go server |
| Templates | `render_test.go` renders every page with `missingkey=error`; no `ZgotmplZ` / `<no value>` in any output; `grep -rn 'x-data="{{' templates/` empty |
| Baseline | applied twice to a scratch DB; no-op on a prod-schema copy; `./out migrate status` shows it |
| Python-side defaults | every column flagged `python_default` is supplied in the Go `INSERT`/`UPDATE` |
| e2e | `tests/conftest.py` already rewritten (cutover.md §1); `uv run pytest tests` green against the Go binary; `--collect-only` count unchanged |
| Grown features | each **ask** answer implemented as recorded in SPEC.md; arq/queue drained if applicable |
| Manual smoke | `make dev`; log in, hit each top-level page, one HTMX fragment, one form post |

Write the results into `.planning/progress.md`. A failed gate is not a reason to skip it — fix and re-run.

## Cutover

Follow `references/cutover.md` top to bottom: conftest, tests-only `pyproject.toml` (or delete), `railpack.json`, `Procfile`, no `railway.json` (the user sets pre-deploy `./out migrate up` in the dashboard, checklist §7), Python deletion, Makefile/.gitignore, CI, README, project CLAUDE.md. Finish by printing the deploy checklist from cutover.md §7 for the user — the skill does not deploy, and does not run `migrate up` against production itself (the first deploy does, via the pre-deploy command).

## Stop and ask (never decide alone)

- Any **ask** row in `grown-features.md` present in the inventory (numpy/pandas, websockets, i18n, HEIC/WebP encoding, MCP OAuth server, long-lived arq jobs).
- `app/utils.py` signer differs from the template and the project has live users — confirm the port before touching sessions.
- `itsdangerous` timed links in flight (email verification, unsubscribe): replicate the format or invalidate.
- Commit on the branch, and anything that touches the production DB or Railway.

## Pitfalls that cost the most (details in `pitfalls.md`)

- Railpack picks Python when `pyproject.toml` is at the root, and its default Go build compiles the non-main root package (`embed.go`) → `railpack.json` with `"provider": "golang"` and an explicit `go build ... -o out ./cmd/server` build command, always.
- `tojson` in a double-quoted attribute → `json` inside single quotes.
- `missingkey=error` off → blank spots in pages instead of failing tests.
- Python-side `uuid4`/`utcnow` defaults are not in the DDL → NOT NULL violations at the first INSERT.
- `RowToStructByPos` field order ≠ column order → silently swapped values.
- Cookie signer changed in the project → every user logged out at deploy.
- `alembic upgrade head` was in `start.sh`/CI, not the Procfile → first deploy runs a stale schema.
- conftest still spawns uvicorn → e2e suite collects nothing after Python is gone.
