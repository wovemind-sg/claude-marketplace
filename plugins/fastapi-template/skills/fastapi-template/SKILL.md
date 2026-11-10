---
name: fastapi-template
description: Scaffolds a complete FastAPI web application skeleton with server-side rendering, database, AI, and Redis. Always use this skill when the user wants to create a new web app, start a new FastAPI project, scaffold a Python web application, set up a new project structure, or bootstrap a full-stack app. Invoke whenever the user says "create a new project", "scaffold a web app", "start a FastAPI app", "set up a project skeleton", "new web app", or anything about bootstrapping a Python web application from scratch.
---

## Stack

Drawn from production apps:

- **Server**: FastAPI + Jinja2 (server-side rendering)
- **Client**: HTMX 2.x (server-driven updates) + Alpine.js 3.x (local state)
- **Database**: PostgreSQL via SQLModel (ORM) + Alembic (migrations)
- **AI**: OpenRouter via `openrouter` package, prompts as Jinja2 `.txt` templates
- **Cache**: Redis via `fastapi-cache2`
- **Auth/session state**: HMAC-signed cookies (`app/utils.py`, keyed by `SESSION_SECRET`) — no Starlette `SessionMiddleware`
- **Config**: `python-dotenv` + `.env.example`
- **Runtime**: `uv` (package management and execution)
- **Logging**: `loguru`
- **Deploy**: Railway via `Procfile`

## Generation Process

1. Ask for **app name** (kebab-case) if not provided
2. Confirm which optional features to include:
   - Database/Alembic (default: yes)
   - AI/OpenRouter (default: ask)
   - Redis caching (default: yes if AI included, otherwise ask)
3. Ask for target directory (default: current directory)
4. Read the three reference files below, then generate all files

Read these reference files before generating:
- `references/python-files.md` — all Python source templates
- `references/config-files.md` — pyproject.toml, Makefile, Procfile, alembic.ini, alembic/env.py, .env.example, .gitignore
- `references/html-templates.md` — base.html, index.html, prompt template, static files

## Project Structure

```
<app-name>/
├── app/
│   ├── __init__.py           # Jinja2Templates, load_dotenv, _assert_env
│   ├── main.py               # FastAPI app, lifespan, middleware, routers
│   ├── dependencies.py       # DBSessionDependency, RedisDependency, auth
│   ├── utils.py              # Cookie helpers and shared utilities
│   ├── ai.py                 # render_prompt, @cache invoke_ai_model, helpers
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py         # SQLModel tables (UUID PKs, __tablename__)
│   │   └── crud.py           # update_db_element, delete_db_element
│   ├── routers/
│   │   ├── __init__.py
│   │   └── home.py           # home_router: GET /
│   └── schemas/
│       └── __init__.py
├── templates/
│   ├── base.html             # HTMX + Alpine.js CDNs, static CSS/JS blocks
│   ├── index.html            # extends base.html
│   └── prompts/              # Jinja2 .txt templates for AI prompts
│       └── example.txt
├── static/
│   ├── css/app.css
│   └── js/app.js
├── alembic/
│   ├── env.py                # load_dotenv, SQLModel metadata, include_object
│   ├── README
│   ├── script.py.mako
│   └── versions/
├── alembic.ini               # Timestamp filename template
├── pyproject.toml
├── Makefile
├── Procfile                  # Railway-compatible gunicorn
├── .env.example
├── .env                      # local only (gitignored)
├── .python-version           # 3.11
└── .gitignore
```

## Critical Patterns (always follow these)

**Env validation** — in `app/__init__.py`, call `_assert_env(name)` for every required env var. Fail at import time, not request time.

**DEV_MODE** — `DEV_MODE = os.getenv("DEV_MODE", "OFF") == "ON"`. Wire it to loguru level, the `secure` flag of `set_cookie` in `utils.py`, and cache prefix suffix (`-dev`).

**Loguru** — remove default handler, add one stdout handler:
```
format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{line} | {message}"
```
DEBUG in DEV_MODE, INFO in prod.

**Lifespan** — connect Redis in `@asynccontextmanager async def lifespan`. Call `FastAPICache.init(RedisBackend(redis), prefix=...)`. Ping Redis and log the result. Close Redis on exit.

**Request logging middleware** — always include `log_requests` that logs method, path, status, duration_ms.

**HTTP exception handler** — redirect 401 → `/` (status 303). Log 5xx as error, 4xx as warning. Call `_default_http_handler` for all others.

**hx-boost, always** — put `hx-boost="true"` on `<body>` in `base.html` so every link and form navigates via HTMX's AJAX swap instead of a full-page browser navigation. This matters most when the app is wrapped with Capacitor: a full-page reload/redirect flashes white and breaks the native app feel in a WKWebView, while a boosted swap doesn't. Never introduce plain `<a href>` full-page navigation as the primary nav path, and don't add JS `window.location` redirects where an hx-boosted link or form would do.

**Signed cookies, never `SessionMiddleware`** — all per-user state that must survive requests (login, OAuth `state`/PKCE, preferences) goes through `get_cookie`/`set_cookie` in `app/utils.py`, which HMAC-sign values with `SESSION_SECRET`. `require_auth`/`is_authenticated` read the `user_id` cookie this way. Do not add Starlette `SessionMiddleware` or use `request.session`. Set cookies on the response the route returns (or from middleware) — a cookie set on a dependency-injected `Response` is silently dropped when the route returns a `TemplateResponse`.

**DB session dependency** — `with Session(DB_ENGINE) as session: yield session`, typed as `DBSessionDependency = Annotated[Session, Depends(get_db_session)]`.

**AI caching** — `@cache(namespace="ai-model")` on `invoke_ai_model`. The cached value comes back as a `dict` (deserialized from Redis) — handle both dict and object in `get_ai_response`.

**SQLModel models** — UUID PKs with `default_factory=uuid4`, always set `__tablename__` explicitly.

**Prompt templates** — Jinja2 `.txt` files under `templates/prompts/`. Render with a module-level `_prompt_env = Environment(loader=FileSystemLoader(...))`.

**HTMX loading** — `<script src="https://unpkg.com/htmx.org@2.0.4" integrity="sha384-HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+" crossorigin="anonymous"></script>` in `<head>`.

**Alpine.js loading** — `<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js"></script>` at end of `<body>`, after `app.js`.

## Customization Checklist

After generating, remind the user to:
- Replace all `<app-name>` placeholders with their actual app name
- Fill in real values in `.env` (DATABASE_URL, REDIS_CONNECTION_STRING, etc.)
- Delete the example `Item` model in `db/models.py` and define their own
- Replace the example `prompts/example.txt` with real prompt templates
- Run `make alembic-upgrade` after adding models
- Run `make dev` to start the dev server
