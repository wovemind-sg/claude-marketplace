# Config File Templates

Replace `<app-name>` with the actual app name throughout.

---

## `go.mod`

```
module <app-name>

go 1.26
```

Write only these two lines, then run `go mod tidy` in the project root: it adds the `require` block with current versions of the four dependencies the sources import (never hand-pin versions — they go stale) and may raise the `go` line to the minimum the dependencies declare — keep whatever tidy writes:

- `github.com/jackc/pgx/v5` — PostgreSQL driver + pool (Database)
- `github.com/pressly/goose/v3` — migrations (Database)
- `github.com/redis/go-redis/v9` — Redis (Cache)
- `github.com/joho/godotenv` — `.env` loading

`go mod tidy` only pulls what is imported, so dropping a feature's Go files drops its dependency automatically. Railpack reads the Go version from this file.

---

## `Makefile`

```makefile
PORT ?= 8000

.PHONY: tidy kill_server dev build server format test migrate-up migrate-down migrate-status migrate-create

tidy:
	go mod tidy

kill_server:
	@(lsof -t -i:$(PORT) && kill -9 $(shell lsof -t -i:$(PORT))) || echo "Server is not running"

dev: kill_server
	PORT=$(PORT) go run ./cmd/server

build:
	go build -o out ./cmd/server

server: build kill_server
	PORT=$(PORT) ./out

format:
	gofmt -w . && go vet ./...

test:
	go test ./...

migrate-up:
	go run ./cmd/server migrate up

migrate-down:
	go run ./cmd/server migrate down

migrate-status:
	go run ./cmd/server migrate status

migrate-create:
	go run ./cmd/server migrate create $(name)
```

Note: Makefile targets must use actual tab characters for indentation (not spaces). When writing the file, ensure the command lines use tabs.

`DEV_MODE=ON` comes from `.env`, so `make dev` runs in dev mode and `./out` in Railway runs in prod mode without any Makefile branching. Usage: `make migrate-create name=add_users`.

**If no database**: drop the four `migrate-*` targets.

---

## `Procfile`

Only when host is `railway`; with `--host generic`, do not create it (nor `railpack.json` below).

```
web: ./out
```

`railpack.json` (below) builds `cmd/server` to `out`, and the Procfile starts it.

Migrations run on every deploy through the pre-deploy command the user sets in the Railway dashboard (service → Settings → Deploy → Pre-deploy Command: `./out migrate up`). It runs in the built image with the service's variables, before the new deployment goes live; a non-zero exit fails the deploy and the previous version keeps serving. Do not add `railway.json` or `railway.toml`: config-as-code overrides the dashboard settings. To run migrations by hand on the deployed service:

```
railway ssh --service "<service name>" -- ./out migrate up
```

The deploy image contains only the binary — no `make`, no goose CLI — which is why migrations are embedded and run through the server binary.

---

## `railpack.json`

Only when host is `railway`.

```json
{
  "$schema": "https://schema.railpack.com",
  "provider": "golang",
  "steps": {
    "build": { "commands": ["go build -ldflags=\"-w -s\" -o out ./cmd/server"] }
  }
}
```

Required: the root `embed.go` (`package app`, non-main) makes Railpack's default `go build -o out` build the root package, which writes a package archive instead of an executable — the build succeeds but the container fails with `./out: Permission denied`. Extra build steps (e.g. `npm ci --omit=dev`) go after this command in the same `commands` array; never rely on the default build command.

---

## `migrations/00001_create_items.sql`

```sql
-- +goose Up
CREATE TABLE items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    description text
);

-- +goose Down
DROP TABLE items;
```

Every migration needs both markers. `make migrate-create name=<slug>` generates a timestamped `YYYYMMDDHHMMSS_<slug>.sql` with the markers in place. Use `-- +goose StatementBegin` / `-- +goose StatementEnd` around multi-statement bodies such as `CREATE FUNCTION`.

---

## `.env.example`

```
DEV_MODE=ON
PORT=8000

# Database
ENGINE_URL=postgresql://postgres:password@localhost:5432/<app-name>

# Redis
REDIS_CONNECTION_STRING=redis://localhost:6379

# Signed cookies (internal/auth)
SESSION_SECRET=change-me-to-a-random-secret-in-production

# AI
OPENROUTER_API_KEY=sk-or-...
```

Optional tuning (only when host is `railway`; defaults shown): `DB_PING_RETRIES=5`, `DB_PING_INTERVAL=2`, `REDIS_PING_RETRIES=5`, `REDIS_PING_INTERVAL=2` (seconds); they apply at startup, to `migrate`, and to each request (bounding how long one request waits on a sleeping DB before a 500, after which requests fail fast for 10s; Redis failures only log and continue). `DOT_ENV_PATH` overrides the `.env` location.

---

## `.gitignore`

```gitignore
# Build output
out
/bin/

# Environment
.env
.prod.env

# IDE
.vscode/
.idea/

# OS
.DS_Store
```
