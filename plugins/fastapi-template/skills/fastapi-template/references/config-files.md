# Config File Templates

Replace `<app-name>` with the actual app name throughout.

---

## `pyproject.toml`

```toml
[project]
name = "<app-name>"
version = "0.1.0"
description = ""
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "gunicorn>=23.0",
    "uvicorn[standard]>=0.34",
    "jinja2>=3.1",
    "python-dotenv>=1.0",
    "python-multipart>=0.0.18",
    "loguru>=0.7",
    "httpx>=0.27",
    "itsdangerous>=2.2",
    # Database
    "sqlmodel>=0.0.38",
    "alembic>=1.18",
    "psycopg[binary]>=3.2",  # SQLAlchemy 2.1+ maps postgresql:// to psycopg 3
    # Redis + caching
    "fastapi-cache2[redis]>=0.2.2",
    "redis>=4.2",  # fastapi-cache2 0.2.2 requires redis<5
    # AI
    "openrouter>=0.9.1",
]

[dependency-groups]
test = [
    "pytest>=8.3",
    "pytest-playwright>=0.6",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Remove groups (Database / Redis / AI) as needed when those features are not included.

---

## `Makefile`

```makefile
PORT ?= 8000
VENV_NAME ?= .venv

$(VENV_NAME):
	uv sync

.PHONY: requirements kill_server server dev format alembic-generate alembic-upgrade alembic-downgrade

requirements: $(VENV_NAME)
	uv sync -q

kill_server:
	@(lsof -t -i:$(PORT) && kill -9 $(shell lsof -t -i:$(PORT))) || echo "Server is not running"

server: requirements kill_server
	uv run gunicorn app.main:app --bind 0.0.0.0:$(PORT) --worker-class uvicorn.workers.UvicornWorker --workers 8

dev: requirements kill_server
	uv run uvicorn app.main:app --host 0.0.0.0 --port $(PORT) --reload

format:
	uv run --with black python -m black app --target-version py311
	uv run --with djlint djlint templates --reformat --quiet

alembic-generate: $(VENV_NAME)
	uv run alembic revision --autogenerate -m "$(name)"

alembic-upgrade: $(VENV_NAME)
	uv run alembic upgrade head

alembic-downgrade: $(VENV_NAME)
	uv run alembic downgrade -1
```

Note: Makefile targets must use actual tab characters for indentation (not spaces). When writing the file, ensure the command lines use tabs.

---

## `Procfile`

Only when host is `railway`; with `--host generic`, do not create it.

```
web: gunicorn app.main:app --bind 0.0.0.0:$PORT --worker-class uvicorn.workers.UvicornWorker --workers ${WEB_CONCURRENCY:-4} --timeout 60 --access-logfile - --error-logfile -
```

---

## `alembic.ini`

```ini
[alembic]
script_location = alembic
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s
prepend_sys_path = .
timezone = UTC
truncate_slug_length = 40
version_locations = %(here)s/alembic/versions
version_path_separator = os
recursive_version_locations = false
output_encoding = utf-8

sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

Note: `alembic.ini`'s `sqlalchemy.url` is overridden in `alembic/env.py` via `ENGINE_URL` env var — the placeholder value is never used.

---

## `alembic/env.py`

```python
import os
import sys
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlmodel import SQLModel
from alembic import context

load_dotenv(dotenv_path=os.getenv("DOT_ENV_PATH", ".env"))

sys.path.append(os.path.join(os.getcwd(), "app"))

from app.db.models import *  # noqa: F401, F403 — registers all models with SQLModel metadata

DB_URL = os.getenv("ENGINE_URL")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def include_object(object, name, type_, reflected, compare_to):
    _ = reflected, compare_to
    if type_ == "table" and getattr(object, "schema", None) == "auth":
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(DB_URL)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

## `alembic/README`

```
Generic single-database configuration.
```

---

## `alembic/script.py.mako`

Use the standard file generated by `uv run alembic init alembic`. If bootstrapping manually:

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

---

## `.env.example`

```
DEV_MODE=ON

# Database
ENGINE_URL=postgresql://postgres:password@localhost:5432/<app-name>

# Redis
REDIS_CONNECTION_STRING=redis://localhost:6379

# Signed cookies (app/utils.py)
SESSION_SECRET=change-me-to-a-random-secret-in-production

# AI
OPENROUTER_API_KEY=sk-or-...
```

---

## `.python-version`

```
3.11
```

---

## `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/

# Virtual envs
.venv/
.dev/

# Environment
.env
.prod.env

# IDE
.vscode/
.idea/

# OS
.DS_Store

# Test
.pytest_cache/
```
