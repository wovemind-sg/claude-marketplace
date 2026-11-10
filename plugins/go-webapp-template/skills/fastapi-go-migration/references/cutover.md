# Cutover: removing Python and switching deploy

Only start this after every gate in SKILL.md passed. Everything here is on the `go-migration` branch; nothing is committed without the user's ok, and nothing is deployed by the skill — the last step is instructions for the user.

## 1. Rewrite `tests/conftest.py` (if `tests/` stays)

The Python conftest spawned uvicorn and often imported `app.` for fixtures. Replace the server fixture with one that builds and runs the Go binary:

```python
import os, socket, subprocess, time
import pytest

PORT = 8765

def _wait(port, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.2)
    raise RuntimeError(f"server on :{port} did not start")

@pytest.fixture(scope="session")
def base_url():
    subprocess.run(["go", "build", "-o", "out", "./cmd/server"], check=True)
    env = {**os.environ, "PORT": str(PORT)}
    proc = subprocess.Popen(["./out"], env=env)
    try:
        _wait(PORT)
        yield f"http://127.0.0.1:{PORT}"
    finally:
        proc.terminate()
        proc.wait(timeout=10)
```

Keep whatever the old conftest did beyond starting the server (seeding, Playwright options), but anything that imported `app.` must become HTTP calls against the server or raw SQL through `psycopg2`. Then `uv run pytest --collect-only -q` must list the same tests as before.

## 2. Minimal `pyproject.toml`

```toml
[project]
name = "<app-name>-tests"
version = "0.0.0"
requires-python = ">=3.11"
dependencies = []

[dependency-groups]
test = [
    "pytest>=8.3",
    "pytest-playwright>=0.6",
    # keep only what tests/ imports: httpx, psycopg2-binary, pytest-xdist ...
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Run `uv lock` to regenerate `uv.lock` from it. If there is no `tests/` directory, delete `pyproject.toml` and `uv.lock` instead.

## 3. Deploy files

- `railpack.json` at the repo root — required for two reasons: the tests-only `pyproject.toml` would otherwise let Railpack pick Python, and the root `embed.go` (`package app`, non-main) makes Railpack's default `go build -o out` build the root package into a non-executable archive (`./out: Permission denied` at start):
  ```json
  {
    "$schema": "https://schema.railpack.com",
    "provider": "golang",
    "steps": {
      "build": { "commands": ["go build -ldflags=\"-w -s\" -o out ./cmd/server"] }
    }
  }
  ```
  Extra build steps (e.g. `npm ci --omit=dev`) go after this command in the same `commands` array. A bare `{"provider": "golang"}` is not enough.
- `Procfile` → exactly `web: ./out` (replace any gunicorn line or `start.sh` reference).
- No `railway.json` / `railway.toml`: config-as-code overrides the dashboard. If the project has one, remove its `preDeployCommand`, `startCommand` and build settings, then delete the file if nothing else remains; if anything else remains in it, stop and ask the user (moving those settings to the dashboard is their call). Migrations run through the pre-deploy command the user sets in the dashboard (§7).
- Delete `start.sh` / `entrypoint.sh` if they existed; whatever they did (`alembic upgrade head`) is replaced by the dashboard pre-deploy command (§7).
- `.env.example`: same keys as before minus `WEB_CONCURRENCY` / worker-count variables; add `PORT=8000`.

## 4. Delete Python

```
git rm -r app alembic alembic.ini .python-version
git rm -f start.sh requirements.txt base_requirements.txt   # whichever exist
find . -name __pycache__ -type d -prune -exec rm -rf {} +
```

Leave `tests/` (if kept), `templates/`, `static/`, `mobile/`. Then `grep -rn --include='*.py' . -l` must list only files under `tests/`.

## 5. Makefile, .gitignore

Makefile = the go-webapp-template one (`references/config-files.md`) plus, if tests stay:

```makefile
test-e2e:
	uv run --group test pytest tests
```

(tab-indented). `.gitignore` = the template's plus `.venv/` and `.pytest_cache/` when tests stay.

## 6. CI, docs

- `.github/workflows/*.yml`: replace `uv sync` / `alembic upgrade head` / `pytest` steps with `go build ./... && go vet ./... && go test ./...`, `./out migrate up` against the CI database, then `make test-e2e` if tests stay. Use `actions/setup-go` with the version from `go.mod`.
- `README.md`: stack, `make dev`, `make migrate-up`, migrations run via the pre-deploy command set in the Railway dashboard (manual: `railway ssh --service <svc> -- ./out migrate up`).
- Project `CLAUDE.md`: load `claude-md-management:claude-md-improver` if the `claude-md-management` plugin is installed (otherwise skip it, edit the file directly and say so in the report) and update — stack, layout (`cmd/`, `internal/`), the Go commands, the signed-cookie rule, the goose migration rule, and the fact that `tests/` is Python Playwright run with `uv`.
- Delete `.planning/` from the migration unless the project already used it for other work.

## 7. Hand the deploy to the user

Print this checklist; do not run it:

1. Railway → service → Settings → Deploy → Pre-deploy Command: set it to `./out migrate up` (replacing `alembic upgrade head` if that is there). Do this before merging; a leftover alembic command fails every deploy (no Python in the image), an empty one deploys without migrations.
2. Railway → service variables: remove `WEB_CONCURRENCY`, `*_WORKERS` overrides if any; keep everything else, including `DB_PING_*` / `REDIS_PING_*` (names are unchanged).
3. Merge `go-migration` → deploy. Watch the build log: first lines must name the Go provider and show `go build ... -o out ./cmd/server`; the start command is `./out`.
4. The pre-deploy log shows `./out migrate up` applying `00001_baseline.sql` (a no-op on the data); `railway ssh --service "<service name>" -- ./out migrate status` shows it applied.
5. Open the app with a browser that still holds a session cookie from the Python app — you should still be logged in.
6. Watch logs for 10 minutes: every request line is `METHOD /path -> status (Nms)`; no 500s.
7. Later, once rollback to Python is off the table: `make migrate-create name=drop_alembic_version` with `DROP TABLE IF EXISTS alembic_version;` in `Up` and a no-op `Down`.

Rollback before step 7: restore the previous Pre-deploy Command in the dashboard (the Python commit has no `./out`, so `./out migrate up` would fail its deploy), then redeploy the previous commit; the schema is untouched (the baseline created nothing), and `goose_db_version` is an extra table Alembic ignores.
