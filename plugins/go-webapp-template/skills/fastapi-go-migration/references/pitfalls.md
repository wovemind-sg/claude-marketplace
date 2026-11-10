# Pitfalls and the check that catches each

Each entry: what goes wrong, why, and the concrete check that proves it did not. Run the checks; do not reason about them.

## Templates

**Contextual autoescaping is not Jinja's.** `html/template` escapes by context (text, attribute, URL, JS, CSS); Jinja escapes HTML only. Symptoms: `#ZgotmplZ` in `href`, double-quoted strings inside `<script>`, CSS values mangled, `<no value>` in output. Full list in `templates.md` → "Autoescaping differences". *Check:* the render-all-pages test (`render_test.go`) with `missingkey=error`, plus grepping the rendered output of each page for `ZgotmplZ` and `<no value>`.

**`tojson` inside a double-quoted attribute.** The JSON's own double quotes terminate the attribute and Alpine silently gets a broken expression. Jinja projects already have this bug lurking (the inventory counts `tojson_double_quoted_attrs`). In Go, `json` returns `template.JS` and the attribute must be single-quoted. *Check:* `grep -rn 'x-data="{{' templates/` returns nothing; every `json` call sits inside `'...'`.

**Prefix functions and operators.** `{{if .A and .B}}` is a parse error; it is `{{if and .A .B}}`. `and`/`or` short-circuit only since Go 1.18 (the template requires 1.22+, fine). `eq` on mismatched kinds (`int` vs `int64`, `string` vs `*string`) is a runtime error. *Check:* `go test ./internal/server/` — parse errors surface at `ParseTemplates`, runtime ones in the render test.

**`{{template}}` takes exactly one argument.** Macro calls with several arguments need `dict`. *Check:* parse error if wrong.

**`range` over a map is key-sorted.** Jinja preserved dict insertion order. A nav built from a dict renders in a different order. *Check:* compare the page with the Python one for any map-driven list.

**Partial define-name collisions.** All partials are parsed into every page, so two files both defining `"row"` silently take the last one. *Check:* `grep -rhn '{{define "' templates/partials | sort | uniq -d` returns nothing.

## Database

**goose and Alembic coexist.** `alembic_version` and `goose_db_version` both live in the DB. The baseline is a no-op on prod (every `CREATE ... IF NOT EXISTS` finds the object) and records version 1. Never run `alembic` after cutover. Drop `alembic_version` only in a later migration once rollback is no longer a concern. *Check:* `./out migrate status` shows the baseline applied; `psql -c '\dt'` still shows every table with the same row counts as before.

**`include_object` exclusions.** If `alembic/env.py` excluded a schema (the template skips `auth`), pass the same `--exclude-schema` to `baseline_ddl.py` or the baseline will try to create tables Alembic never owned. *Check:* read `alembic/env.py`; compare the baseline's table list to `alembic/versions/*`.

**Baseline `Down` is a no-op on purpose.** A `Down` that drops the production tables is one typo away from data loss. *Check:* the file ends with the no-op comment block, not `DROP TABLE`.

**Python-side defaults are not in the DDL.** `default_factory=uuid4`, `default_factory=utcnow`, `default=0`, `onupdate=utcnow` lived in Python; the DDL does not have them. Every Go `INSERT` must supply `gen_random_uuid()`, `now()`, the literal; every `UPDATE` must set `updated_at = now()`. The inventory flags these columns (`python_default: true`). *Check:* for each flagged column, grep the Go `INSERT`/`UPDATE` for that column name; a NOT NULL violation in the handler test if you missed one.

**`RowToStructByPos` order.** Struct field order must equal the column order in the `cols` const or values land in the wrong fields with no error when the types coincide (two `string` columns swapped). *Check:* keep the const immediately above the struct; one test per table that inserts a row and reads it back comparing every field. Wide tables: switch to `RowToStructByName` + `db:"..."` tags.

**Timestamps.** Plain `datetime` fields are `timestamp without time zone` (pgx returns them as `time.Time` in UTC); `DateTime(timezone=True)` columns are `timestamptz`. The baseline SQL shows which. Store `.UTC()` always. *Check:* the round-trip test above includes a timestamp and compares with `.Equal`, and the rendered page shows the same wall-clock time the Python app showed.

**Data migrations are gone.** `op.execute("UPDATE ...")` steps in Alembic history already ran in prod and a fresh DB has no rows to fix. If one of them seeded reference data (`INSERT INTO plans ...`), that seed must move into the baseline or a second goose migration. *Check:* grep `alembic/versions` for `INSERT`.

## Cookies and cache

**Cookie compatibility is per repo.** The template signers are byte-identical, so sessions survive — but only if `app/utils.py` was never modified. Grown projects changed the MAC input (`name\0value`), the separator, the max-age, or added a version prefix. *Check:* `uv run python -c "from app.utils import _sign; print(_sign('abc'))"` before Python is deleted, paste the output into `internal/auth/cookies_test.go`, assert `verify` returns `("abc", true)`. Then log in on the Go server with a browser that still has the Python cookie.

**Cookie value charset.** Python's `set_cookie` quotes values with spaces/semicolons; Go's `http.SetCookie` silently drops invalid bytes. *Check:* the inventory's cookie values are UUIDs/opaque ids. If not, base64url them.

**Cache keys change.** `fastapi-cache2` keys are `prefix:namespace:md5(module+func+args)`; the Go helper uses `prefix:namespace:sha256(json)`. Nothing matches after cutover → a cold cache, which is fine. Keys the app wrote itself with raw Redis calls (OTP codes, rate limits, locks) must keep their exact names or in-flight OTPs break at the moment of deploy. *Check:* grep the Python for `redis.` calls with literal keys; grep the Go for the same literals.

**arq queue.** Jobs are pickled Python; Go cannot read them. *Check:* `redis-cli LLEN arq:queue` is 0 before cutover (or whatever queue name `WorkerSettings` used).

## Routing and HTTP

**Status-code parity.** FastAPI: 422 on validation failure, 307 for a trailing-slash redirect, 307 for `RedirectResponse` without an explicit code, 405 vs 404 distinctions. e2e tests and HTMX `hx-target-4xx` handlers may depend on these. Go 1.22 mux: `/items/` is a subtree pattern (matches `/items/anything`), `/items/{$}` is exact, `/items` does not match `/items/`. *Check:* `inventory.py --go-routes` for presence; the e2e suite for codes; a `curl -i` pass over every GET route comparing status with the Python server (run both on different ports during the migration).

**Headers after body.** `w.Header().Set` and `Cookies.Set` after `Render` wrote bytes are silently ignored (Go logs `superfluous response.WriteHeader` at best). *Check:* `go vet` does not catch it; the e2e login test does.

**`FileServer` lists directories.** `/static/` with no `index.html` renders a directory listing. Harmless for `/static/` (public assets) but do not mount a directory containing anything private. *Check:* `curl /static/` and look.

## Deployment

**Railpack picks Python if `pyproject.toml` or `requirements.txt` is at the root.** `.python-version` and `uv.lock` alone do not trigger it, but the tests-only `pyproject.toml` from `cutover.md` does, and provider precedence is undocumented. Always add `railpack.json` at the root (content in `cutover.md` §3).

**Railpack's default Go build compiles the wrong package.** It runs `go build -ldflags="-w -s" -o out` at the root; the root `embed.go` is `package app` (non-main), so `out` is a package archive, not an executable. The build succeeds and `./out` exists, but the container fails with `/bin/bash: line 1: ./out: Permission denied`. `railpack.json` must set `"provider": "golang"` and `steps.build.commands` to `go build -ldflags="-w -s" -o out ./cmd/server` — a bare `{"provider": "golang"}` keeps the broken default. *Check:* the Railway build log names the Go provider and shows `go build ... -o out ./cmd/server`; "build succeeded and `./out` exists" is not enough — this bug passes both.

**Static binary, no tzdata.** The deploy image is minimal; `time.LoadLocation("Asia/Singapore")` fails there and works locally. *Check:* `import _ "time/tzdata"` in `main.go` if the inventory lists `timezones`.

**Where did `alembic upgrade head` run?** Grown projects run it in `start.sh`, a Railway pre-deploy command, or a CI job — not in the template's Procfile. Remove it from wherever it was and let the Railway dashboard pre-deploy command (`./out migrate up`, set by the user, see `cutover.md` §7) own it; CI keeps its own `./out migrate up` against the CI database. A leftover `alembic upgrade head` pre-deploy command fails every deploy (no Python in the image). *Check:* inventory `deploy` section; grep `.github/workflows`, `start.sh`, `railway.json`/`railway.toml`.

**`WEB_CONCURRENCY` and friends.** Meaningless for one Go process; the pgx pool is 20 connections per replica. With N Railway replicas that is 20N against Postgres `max_connections`. *Check:* Railway variables; lower `MaxConns` in `db.Connect` if N×20 is near the limit.

**e2e tests silently testing nothing.** `tests/conftest.py` spawned `uvicorn app.main:app`. After Python is deleted that line fails at collection — unless pytest is configured to skip on error, in which case the suite passes with zero tests. *Check:* rewrite the conftest per `cutover.md` **before** deleting `app/`; `pytest --collect-only` lists the same test count as before.
