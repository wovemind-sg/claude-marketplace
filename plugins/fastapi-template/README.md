# fastapi-template

Scaffolds a complete FastAPI web application skeleton, drawn from production apps.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install fastapi-template@wovemind
```

`plan-tools` installs this plugin for you, and its `create-webapp` skill uses it to start a full app.

## Stack

- **Server**: FastAPI + Jinja2 (server-side rendering)
- **Client**: HTMX 2.x + Alpine.js 3.x
- **Database**: PostgreSQL via SQLModel + Alembic
- **AI**: OpenRouter + Jinja2 prompt templates + Redis caching
- **Cache**: Redis via fastapi-cache2
- **Auth/session state**: HMAC-signed cookies (`app/utils.py`), no SessionMiddleware
- **Runtime**: uv
- **Deploy**: Railway (Procfile) by default; with `--host generic`, no Procfile and no Railway-specific code, so you deploy to any host that runs a Python web server

## Usage

Invoke the skill by asking Claude to scaffold a new web app:

```
/fastapi-template:fastapi-template create a new app called my-app
/fastapi-template:fastapi-template [--host railway|generic] [--ai-model <openrouter model id>]   # defaults railway, openai/gpt-4o-mini
```

Or just describe what you want:

> "Scaffold a new FastAPI project for a task management app"

## Requirements

To run the generated app:

- [`uv`](https://docs.astral.sh/uv/) and Python 3.11 or newer (the project pins 3.11 in `.python-version`).
- `make` for the `make dev`, `make server` and Alembic targets.
- A PostgreSQL database and a Redis server, when those parts are included.
- An OpenRouter API key, when the AI part is included.
- For deploying with the default host, a Railway account; the generated app has a `Procfile` Railway runs.

## Opinionated defaults

| Default | Change it with |
|---|---|
| Deploy to Railway: a `Procfile`, and database/Redis pings retried while a sleeping Railway service wakes up | `--host generic` |
| AI calls go to OpenRouter with the model `openai/gpt-4o-mini` | `--ai-model <openrouter model id>` |
| Dev server on port 8000 | `PORT` in the environment or `make dev PORT=<port>` |
| Production server is gunicorn with 8 uvicorn workers | edit the `server` target in the generated `Makefile` |
| Python 3.11, managed by `uv` | edit `.python-version` and `pyproject.toml` |
| Database included; AI asked about; Redis included when AI is | the skill asks which features to include |

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
├── Procfile              # only with --host railway (the default)
├── .env.example
└── .gitignore
```

## Environment variables

The plugin itself needs none and has no plugin settings. The generated app reads these from `.env`:

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

## Example

```
/fastapi-template:fastapi-template create a new app called recipe-box --host generic --ai-model anthropic/claude-haiku-5-5
```

This generates `recipe-box/` without a `Procfile`, with `invoke_ai_model` defaulting to that OpenRouter model. Then follow the Quick Start above.
