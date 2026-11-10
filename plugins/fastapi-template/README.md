# fastapi-template

Scaffolds a complete FastAPI web application skeleton, drawn from production apps.

## Stack

- **Server**: FastAPI + Jinja2 (server-side rendering)
- **Client**: HTMX 2.x + Alpine.js 3.x
- **Database**: PostgreSQL via SQLModel + Alembic
- **AI**: OpenRouter + Jinja2 prompt templates + Redis caching
- **Cache**: Redis via fastapi-cache2
- **Auth/session state**: HMAC-signed cookies (`app/utils.py`), no SessionMiddleware
- **Runtime**: uv
- **Deploy**: Railway (Procfile)

## Usage

Invoke the skill by asking Claude to scaffold a new web app:

```
/fastapi-template:fastapi-template create a new app called my-app
/fastapi-template:fastapi-template [--host railway|generic] [--ai-model <openrouter model id>]   # defaults railway, openai/gpt-4o-mini
```

Or just describe what you want:

> "Scaffold a new FastAPI project for a task management app"

## Generated Structure

```
<app-name>/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── dependencies.py
│   ├── utils.py
│   ├── ai.py
│   ├── db/
│   │   ├── models.py
│   │   └── crud.py
│   ├── routers/
│   │   └── home.py
│   └── schemas/
├── templates/
│   ├── base.html
│   ├── index.html
│   └── prompts/
├── static/
├── alembic/
├── alembic.ini
├── pyproject.toml
├── Makefile
├── Procfile
├── .env.example
└── .gitignore
```

## Required Environment Variables

| Variable | Description |
|---|---|
| `ENGINE_URL` | PostgreSQL connection string |
| `REDIS_CONNECTION_STRING` | Redis URL |
| `SESSION_SECRET` | Random secret for HMAC-signing cookies (`app/utils.py`) |
| `OPENROUTER_API_KEY` | OpenRouter API key (if using AI) |
| `DEV_MODE` | Set to `ON` for development |

## Quick Start

After scaffolding:

```bash
cd <app-name>
cp .env.example .env
# edit .env with real values
make alembic-upgrade  # run initial migration
make dev              # start dev server at localhost:8000
```
