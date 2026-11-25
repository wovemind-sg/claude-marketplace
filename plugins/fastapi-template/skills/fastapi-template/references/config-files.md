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
PORT ?= $(or $(shell sed -n 's/^PORT=//p' .env 2>/dev/null),8000)
VENV_NAME ?= .venv

$(VENV_NAME):
	uv sync

.PHONY: requirements kill_server server dev format alembic-generate alembic-upgrade alembic-downgrade worktree-env worktree-reap

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

worktree-env:
	uv run python scripts/worktree_env.py

worktree-reap:
	uv run python scripts/worktree_env.py --reap
```

Without the database feature, drop the `worktree-reap` target (and its `.PHONY` entry). The `PORT` line reads the worktree's own `.env`, so each worktree's `make dev` uses its own port.

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

## `scripts/worktree_env.py`

Gives each `claude --worktree` checkout its own port, Postgres DB and Redis db. Replace `<app-name>` (kebab-case); the DB name uses it with `-` turned into `_`.

Feature gating: delete every line or block tagged `# [db]` when the database feature is off, and every one tagged `# [redis]` when Redis is off. Port isolation always stays. Without the database feature there is nothing to reap, so also delete `reap` and the `--reap` branch, and use the setup-only hook command in `.claude/settings.json`.

```python
"""Per-worktree isolation: own port, Postgres DB and Redis db via a worktree-local `.env`.

`python scripts/worktree_env.py`         create `.env` + DB for this linked worktree (no-op in main / if `.env` exists)
`python scripts/worktree_env.py --reap`  drop DBs / flush Redis dbs of slots no live worktree claims
Never touches the main DB or Redis db 0.
"""

import fcntl
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit  # [redis]

import redis  # [redis]
from dotenv import dotenv_values
from sqlalchemy import create_engine, text  # [db]
from sqlalchemy.engine import make_url  # [db]

APP = "<app-name>"
DB_PREFIX = APP.replace("-", "_") + "_wt"  # [db]
BASE_PORT = 8000
SLOTS = range(1, 10)
DEFAULT_REDIS = "redis://localhost:6379"  # [redis]
OVERRIDDEN = {
    "WT_SLOT",
    "ENGINE_URL",
    "REDIS_CONNECTION_STRING",
    "PORT",
    "PUBLIC_BASE_URL",
    "TEST_PORT_OFFSET",
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def main_env_path() -> Path:
    return (
        Path(git("rev-parse", "--path-format=absolute", "--git-common-dir")).parent
        / ".env"
    )


@contextmanager
def slot_lock():
    """Exclusive lock so concurrent setup/reap never pick the same slot or drop a half-claimed one."""
    common = git("rev-parse", "--path-format=absolute", "--git-common-dir")
    with open(Path(common) / f"{APP}-worktree.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def claimed_slots() -> set[int]:
    slots = set()
    for line in git("worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            env = Path(line[9:]) / ".env"
            if env.is_file() and (
                m := re.fullmatch(r"\d", dotenv_values(env).get("WT_SLOT") or "")
            ):
                slots.add(int(m.group()))
    return slots


def redis_url(base: str, slot: int) -> str:  # [redis]
    """`base` (main's REDIS_CONNECTION_STRING: host/auth kept) with its db swapped for `slot`."""  # [redis]
    return urlsplit(base)._replace(path=f"/{slot}").geturl()  # [redis]


def admin_engine(main_url: str):  # [db]
    return create_engine(  # [db]
        make_url(main_url).set(database="postgres"), isolation_level="AUTOCOMMIT"  # [db]
    )  # [db]


def reap(vals: dict) -> None:  # [db]
    with slot_lock(), admin_engine(vals["ENGINE_URL"]).connect() as c:  # [db]
        keep = claimed_slots()  # [db]
        for (name,) in c.execute(  # [db]
            text("select datname from pg_database where datname ~ :pat"),  # [db]
            {"pat": f"^{DB_PREFIX}[0-9]$"},  # [db]
        ).all():  # [db]
            slot = int(name[-1])  # [db]
            if slot not in keep:  # [db]
                c.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))  # [db]
                base = vals.get("REDIS_CONNECTION_STRING") or DEFAULT_REDIS  # [redis]
                redis.Redis.from_url(redis_url(base, slot)).flushdb()  # [redis]
                print(f"reaped slot {slot}")  # [db]


def setup(main_env: Path) -> None:
    with slot_lock():
        _setup(main_env)


def _setup(main_env: Path) -> None:
    env = Path(".env")
    if (
        git("rev-parse", "--git-dir") == git("rev-parse", "--git-common-dir")
        or env.exists()
    ):
        return
    vals = dotenv_values(main_env)
    used = claimed_slots()
    slot = next(s for s in SLOTS if s not in used)
    port = BASE_PORT + slot
    url = make_url(vals["ENGINE_URL"]).set(database=f"{DB_PREFIX}{slot}")  # [db]
    redis_base = vals.get("REDIS_CONNECTION_STRING") or DEFAULT_REDIS  # [redis]
    lines = [
        l
        for l in main_env.read_text().splitlines()
        if l.split("=", 1)[0].strip() not in OVERRIDDEN
    ]
    lines += [
        f"WT_SLOT={slot}",
        f"ENGINE_URL={url.render_as_string(hide_password=False)}",  # [db]
        f"REDIS_CONNECTION_STRING={redis_url(redis_base, slot)}",  # [redis]
        f"PORT={port}",
        f"PUBLIC_BASE_URL=http://localhost:{port}",
        f"TEST_PORT_OFFSET={1000 * slot}",
    ]
    # Claim the slot (.env) before creating the DB so a concurrent --reap never drops it;
    # undo the claim on failure so the next session retries instead of keeping a half-built slot.
    env.write_text("\n".join(lines) + "\n")
    try:
        with admin_engine(vals["ENGINE_URL"]).connect() as c:  # [db]
            # No live owner claims this slot, so any existing DB / Redis db is stale: start clean.
            c.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))  # [db]
            c.execute(text(f'CREATE DATABASE "{url.database}"'))  # [db]
        redis.Redis.from_url(redis_url(redis_base, slot)).flushdb()  # [redis]
        # load_dotenv never overrides the shell, so pin ENGINE_URL too: migrate this slot's DB, never one inherited from the shell
        subprocess.run(  # [db]
            ["uv", "run", "alembic", "upgrade", "head"],  # [db]
            check=True,  # [db]
            env={  # [db]
                **os.environ,  # [db]
                "DOT_ENV_PATH": str(env.resolve()),  # [db]
                "ENGINE_URL": url.render_as_string(hide_password=False),  # [db]
            },  # [db]
        )  # [db]
    except BaseException:
        env.unlink(missing_ok=True)
        raise
    print(f"worktree slot {slot}: port {port}")


if __name__ == "__main__":
    try:
        main_env = main_env_path()
        if "--reap" in sys.argv:
            reap(dotenv_values(main_env))  # [db]
        else:
            setup(main_env)
    except Exception as e:  # hooks must never fail a session (Postgres/Redis down, no .env)
        print(f"worktree_env: skipped ({type(e).__name__})", file=sys.stderr)
```

---

## `.claude/settings.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "(uv run python scripts/worktree_env.py --reap; uv run python scripts/worktree_env.py) >/dev/null 2>&1 || true"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run python scripts/worktree_env.py --reap >/dev/null 2>&1 || true"
          }
        ]
      }
    ]
  }
}
```

Without the database feature: the SessionStart command is `uv run python scripts/worktree_env.py >/dev/null 2>&1 || true` and there is no `SessionEnd` entry. Commit this file; it carries no secrets.

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
