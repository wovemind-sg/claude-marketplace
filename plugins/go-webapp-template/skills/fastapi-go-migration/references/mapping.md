# Python → Go mapping

Every row maps a construct from a `fastapi-template` project to its `go-webapp-template` counterpart. The Go side names refer to the files in the go-webapp-template skill's `references/go-files.md` (`config.go`, `cookies.go`, `db.go`, `cache.go`, `ai.go`, `server.go`, `middleware.go`, `errors.go`, `render.go`). Read that file once; this table tells you which part of it each Python thing lands in.

The two templates were designed as mirrors — same env var names, same cookie signing, same error/redirect/logging semantics, same frontend — so most skeleton rows are "already done by the Go skeleton". The work is in the rows below the skeleton: routes, models, templates, and whatever the project grew.

## Skeleton (`app/__init__.py`, `main.py`, `dependencies.py`, `utils.py`)

| Python | Go |
|---|---|
| `_assert_env("X")` in `app/__init__.py`; `if not X: raise RuntimeError` in `ai.py` | `config.MustEnv("X")` at the top of `run()` in `cmd/server/main.go`. One line per required var. |
| `os.getenv("X", "d")`, `int(os.getenv(...))` | `config.Env("X", "d")`, `config.EnvInt("X", d)` |
| `DEV_MODE = os.getenv("DEV_MODE") == "ON"` | `config.DevMode` (set by `config.Load()`) |
| loguru setup | `setupLogging()` in main.go — already in the skeleton |
| `lifespan`: Redis ping, `FastAPICache.init`, `DB_ENGINE.dispose()` | `run()`: `db.Connect`, `cache.Connect`, `defer pool.Close()` / `defer c.Close()`, `signal.NotifyContext` + `srv.Shutdown`. Already in the skeleton. Extra lifespan steps (workers, schedulers, warmups) → goroutines started in `run()` bound to `ctx`; see `grown-features.md`. |
| `log_requests` middleware | `logRequests` — already equivalent (same log line format, same dev `Cache-Control: no-store` on `/static`) |
| `http_exception_handler` (401 → 303 `/`, 5xx error, 4xx warn) | `handle()` in `errors.go` — already equivalent |
| extra `@app.middleware("http")` / `app.add_middleware(CORSMiddleware, ...)` / `GZipMiddleware` | hand-written `func(next http.Handler) http.Handler` in `middleware.go`, chained in `server.New`. CORS: set the three headers + handle `OPTIONS`. Gzip: skip unless measured (Railway's edge compresses). |
| `@app.exception_handler(CustomError)` | an `errors.As(err, &custom)` branch inside `handle()` before the `*HTTPError` check |
| `app.mount("/static", StaticFiles(...))` | `http.FileServerFS` on `fs.Sub(assets, "static")` — in the skeleton. Other mounts (`/media`, uploads dir on disk) → `http.FileServer(http.Dir(path))`. |
| `DB_ENGINE` pool sizing per gunicorn worker, `WEB_CONCURRENCY` | `db.Connect` sizes one pool (`MaxConns=20`) for the single process. `WEB_CONCURRENCY` becomes meaningless — unset it in Railway. |
| `get_db_session` ping-retry, `get_redis` ping-retry | The `wakeDeps` middleware (wraps the whole mux) wakes `Pool` and `Cache` before every non-static request via `wake.Waker`; `db.Connect` / `cache.Connect` / `migrate` use `wake.Ping` (`DB_PING_*`, `REDIS_PING_*` honoured). Nothing per-route to port. |

## Routing (`app/routers/*.py`)

| Python | Go |
|---|---|
| `router = APIRouter(prefix="/items")` | No sub-router. Register full paths in `server.New`: `mux.HandleFunc("GET /items", s.handle(s.listItems))`. One file per router: `internal/server/items.go`. |
| `APIRouter(dependencies=[Depends(require_auth)])` | wrap each route: `mux.Handle("GET /account", d.Cookies.RequireAuth(s.handle(s.account)))`. Many routes → a 3-line `func (s *Server) authed(h handlerFunc) http.Handler`. |
| `@router.get("")` with prefix `/items` | `"GET /items"`; an empty-path route on a prefixed router is the prefix itself |
| `@home_router.get("/")` | `"GET /{$}"` — without `{$}` the Go pattern `/` matches every path |
| `@router.get("/{item_id}")` | `"GET /items/{item_id}"`, read with `r.PathValue("item_id")` |
| `@router.get("/files/{path:path}")` | `"GET /files/{path...}"` |
| path param typed `int` | `strconv.Atoi(r.PathValue("id"))`, error → `return server.Err(http.StatusNotFound, "")` (FastAPI gives 422; 404 is friendlier and nothing depends on it unless tests assert 422 — check the inventory's `tests`) |
| path param typed `UUID` | keep as `string`; DB columns are selected as `id::text` |
| `q: str = Query(None)` / plain `q: str = ""` | `r.URL.Query().Get("q")` |
| `name: str = Form(...)` (`python-multipart`) | `r.ParseForm()` (or `r.ParseMultipartForm(32 << 20)` when a file is involved) then `r.FormValue("name")`. A required field missing → `return server.Err(422, "name is required")` — keep 422 because HTMX forms and e2e tests may expect it. |
| pydantic `BaseModel` in `app/schemas/` used as `Body` or `Form` | plain Go struct + explicit validation returning `server.Err(422, msg)`. `app/schemas` disappears. Validation that was implicit in pydantic types (int parsing, email format, min length) must be written out — list each field. |
| `payload: X = Body(...)` / JSON body | `var in X; json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20)).Decode(&in)` with `json:"..."` tags |
| `file: UploadFile = File(...)` | `f, hdr, err := r.FormFile("file")`; `hdr.Filename`, `hdr.Header.Get("Content-Type")`, `io.ReadAll(f)` |
| `request.headers.get("HX-Request")` | `r.Header.Get("HX-Request")` |
| `response.headers["HX-Trigger"] = "x"` | `w.Header().Set("HX-Trigger", "x")` **before** `Render`/`Write` |

## Responses

| Python | Go |
|---|---|
| `templates.TemplateResponse(request=request, name="x.html", context={...})` | `return s.tmpl.Render(w, "x.html", data)`. `request` is never passed to templates — copy what the template reads (`request.url.path`, query values, cookie values) into `data` explicitly. |
| `templates.TemplateResponse("partials/row.html", ...)` (HTMX fragment) | `return s.tmpl.RenderPartial(w, "items.html", "item-row", data)` — the partial is a `{{define "item-row"}}` block parsed into every page (see `templates.md`) |
| `templates.get_template("email.html").render(...)` (not an HTTP response) | a separate `template.ParseFS(assets, "templates/emails/*.html")` set in the package that sends the email; do not route it through `base.html` |
| `HTMLResponse("")` / `Response(status_code=200)` | `w.WriteHeader(http.StatusOK); return nil` |
| `JSONResponse(content, status_code=...)` / returning a dict from a route | add `internal/server/json.go`: `func writeJSON(w http.ResponseWriter, code int, v any) error` (set `Content-Type: application/json`, `WriteHeader(code)`, `json.NewEncoder(w).Encode(v)`) |
| `RedirectResponse(url, status_code=303)` | `http.Redirect(w, r, url, http.StatusSeeOther); return nil` |
| `RedirectResponse(url)` with no status | FastAPI's default is **307**. Preserve it (`http.StatusTemporaryRedirect`) unless you confirm nothing depends on it; 307 re-sends a POST body, 303 does not. |
| `raise HTTPException(status_code=404, detail="x")` | `return server.Err(http.StatusNotFound, "x")` |
| `raise HTTPException(401)` (auth) | `return server.Err(http.StatusUnauthorized, "")` → `handle` redirects 303 to `/` |
| `StreamingResponse(gen(), media_type="text/event-stream")` | `w.Header().Set("Content-Type", "text/event-stream")`; write `data: ...\n\n` per event and call `w.(http.Flusher).Flush()`; stop when `<-r.Context().Done()` |
| `FileResponse(path)` | `http.ServeFile(w, r, path)` or `http.ServeContent` for in-memory bytes |

## Dependencies (`Depends`)

| Python | Go |
|---|---|
| `DBSessionDependency` | `s.Pool` (field of `server.Deps`); pass `r.Context()` to every query |
| `RedisDependency` | `s.Cache.Client` |
| `RequireAuthDependency` / `dependencies=[Depends(require_auth)]` | `d.Cookies.RequireAuth(...)` middleware per route |
| `IsAuthenticatedDependency` | `s.Cookies.IsAuthenticated(r)` in the handler, put into `data["Authenticated"]` |
| other `Depends(fn)` that returns a value (current user, admin flag, locale) | an ordinary method `func (s *Server) currentUser(r *http.Request) (User, error)` called at the top of each handler that needs it |
| a dependency that sets `request.state.x` read by **templates** | middleware that computes it once and stores it with `context.WithValue(r.Context(), ctxKey{}, v)`; `s.view(r, data)` copies it into every render (see `templates.md`) |
| `Depends` chains (A depends on B) | plain function calls; Go has no injection — keep the call order explicit |

## Cookies / auth (`app/utils.py`)

| Python | Go |
|---|---|
| `get_cookie(request, name)` | `s.Cookies.Get(r, name)` returns `(value, ok)` |
| `set_cookie(response, name, value, ...)` | `s.Cookies.Set(w, name, value)` — **call before writing the body**; headers freeze on the first byte |
| `response.delete_cookie(name)` | `s.Cookies.Clear(w, name)` |
| `_sign` / `_verify` | `cookies.go` `sign`/`verify`. The template formats are byte-identical (`value + "." + hex(hmac_sha256(secret, value))`, split on the last `.`, 30 days, Lax, HttpOnly, Secure outside dev) so existing sessions survive — **only if `utils.py` is unmodified**. Grown projects change the MAC input (e.g. MAC over `f"{name}\0{value}"`) or the separator. Diff the project's `utils.py` against the template; port whatever it actually does; then write `internal/auth/cookies_test.go` with a vector generated by `uv run python -c "from app.utils import _sign; print(_sign('abc'))"` and assert `verify` accepts it. |
| cookie values with spaces/quotes/semicolons | Python quotes them, Go's `http.SetCookie` drops invalid bytes silently. Values in these apps are UUIDs or opaque ids — confirm in the inventory; if not, base64url-encode in both directions. |

## Background work, HTTP clients, logging, caching

| Python | Go |
|---|---|
| `background_tasks.add_task(fn, *args)` | `go func() { defer func(){ if rec := recover(); rec != nil { slog.Error("background task panic", "err", rec) } }(); fn(context.WithoutCancel(r.Context()), args) }()` — same fire-and-forget, lost-on-crash semantics as FastAPI; anything that must survive a crash needs a queue (see `grown-features.md`) |
| `httpx.Client()` / `requests.get` per call | one package-level `var httpClient = &http.Client{Timeout: 30 * time.Second}` in the package that owns the integration; `http.NewRequestWithContext(ctx, ...)`; treat `resp.StatusCode >= 300` as an error with the body in the message (as `ai.send` does) |
| `logger.info(f"a {x}")` | `slog.Info("a", "x", x)` — structured, not interpolated |
| `logger.exception("x")` | `slog.Error("x", "err", err)` (Go has no stack unless you add `debug.Stack()`) |
| `logger.bind(user=u)` | `log := slog.With("user", u)` |
| `logger.debug` | `slog.Debug` (only visible with `DEV_MODE=ON`) |
| `@cache(namespace="x", expire=60)` on `async def f(a, b)` | inside the Go function: `return cache.Cached(ctx, s.Cache, "x", keyOf(a, b), 60*time.Second, func() (T, error) {...})` where `keyOf` is `sha256` of the JSON of the arguments. `T` must be JSON round-trippable. |
| `@cache(namespace="ai-model")` on `invoke_ai_model` | already done inside `ai.Invoke` |
| `FastAPICache.clear(namespace="x")` | add `func (c *Cache) ClearNamespace(ctx, ns string) error` using `Client.Scan(ctx, 0, c.key(ns, "*"), 100)` + `Del` — only if the project calls `clear` |
| raw `redis.get/set/incr/expire/setnx` (OTP codes, rate limits, locks) | `s.Cache.Client.Get(ctx, key)` etc. Use the **exact same key strings** the Python code used (no prefix) so live data (an OTP in flight, a rate-limit window) survives the cutover. |

## AI (`app/ai.py`)

| Python | Go |
|---|---|
| `render_prompt("name", **ctx)` | `s.AI.RenderPrompt("name", data)` — `data` is a struct or `map[string]any`; prompt files become `text/template` (see `templates.md`, same table minus escaping) |
| `invoke_ai_model(*messages, system_prompt_name=, prompt_context=, model=, temperature=, **extra)` | `s.AI.Invoke(ctx, []ai.Message{...}, ai.Options{SystemPromptName:, PromptContext:, Model:, Temperature:, Extra: map[string]any{...}})` |
| `get_ai_response(...)` → `str` | `s.AI.GetResponse(ctx, msgs, opts)` |
| `get_ai_json_response(...)` → `dict` | `s.AI.GetJSONResponse(ctx, msgs, opts)` → `map[string]any`; decode into a typed struct afterwards if the handler reads specific keys |
| `dict(role="user", content=x)` | `ai.Message{Role: "user", Content: x}` |
| the dict-vs-object branch in `get_ai_response` | gone — the Go cache decodes straight into `*ai.Response` |

## Database (`app/db/models.py`, `crud.py`, `alembic/`)

| Python | Go |
|---|---|
| `class Item(SQLModel, table=True)` with `__tablename__` | (1) a table in `migrations/00001_baseline.sql` (generated by `scripts/baseline_ddl.py`); (2) `internal/db/items.go`: `type Item struct`, `const itemCols = "id::text, name, ..."`, and the query functions the handlers actually call (List/Get/Create/Update/Delete as needed — not all five by reflex) |
| `id: UUID` | `ID string`; always `SELECT id::text`, so no uuid package |
| `Optional[str]` / `str | None` | `*string`; pgx scans NULL into nil |
| `int` / `float` / `bool` | `int` / `float64` / `bool` |
| `datetime` | `time.Time`. Plain `datetime` fields are `TIMESTAMP WITHOUT TIME ZONE`; `sa_column=Column(DateTime(timezone=True))` gives `WITH TIME ZONE` — the baseline shows which. Always store `.UTC()`. |
| `date` | `time.Time` (pgx maps `date` to `time.Time`) |
| `dict` via `sa_column=Column(JSON)` / `JSONB` | `json.RawMessage` or a typed struct — pgx decodes `json`/`jsonb` columns directly into either |
| `bytes` / `LargeBinary` | `[]byte` |
| `str` Enum (`class Status(str, Enum)`) | `type Status string` + `const (StatusNew Status = "new" ...)`; the DDL keeps the PG enum type if one existed |
| `default_factory=uuid4` / `default_factory=utcnow` / `default=0` (Python-side defaults) | the DDL has **no** default for these — every `INSERT` supplies them: `gen_random_uuid()`, `now()`, literal. The inventory flags every such column as `python_default: true`. |
| `sa_column_kwargs={"onupdate": utcnow}` | every `UPDATE ... SET updated_at = now()` — nothing automatic |
| `Field(foreign_key="items.id", index=True)` | in the DDL; in Go, a JOIN or a second query — there is no ORM graph |
| `Relationship(back_populates=...)` lazy loads | explicit JOIN producing a flat struct, or two queries. Decide per template: what does the page actually show? |
| `session.exec(select(Item).where(Item.x == v)).all()` | `rows, _ := pool.Query(ctx, "SELECT "+itemCols+" FROM items WHERE x = $1", v); return pgx.CollectRows(rows, pgx.RowToStructByPos[Item])` |
| `session.get(Item, id)` | `pgx.CollectOneRow(...)`; `errors.Is(err, pgx.ErrNoRows)` → `server.Err(404, "")` |
| `session.add(obj); session.commit(); session.refresh(obj)` | `INSERT ... RETURNING `+itemCols → `CollectOneRow` |
| `crud.update_db_element(db, obj, patch)` | explicit `UPDATE items SET a = $2, b = $3 WHERE id = $1` — write the column list; there is no generic setattr loop |
| `crud.delete_db_element` | `DELETE FROM items WHERE id = $1` |
| `with session.begin():` / multiple writes that must be atomic | `tx, err := pool.Begin(ctx); defer tx.Rollback(ctx); ...; return tx.Commit(ctx)` |
| `RowToStructByPos` | struct field order **must** equal the column order in the `cols` const. Keep them adjacent. For wide tables (>8 columns) use `pgx.RowToStructByName` with `db:"col"` tags instead. |
| `alembic revision --autogenerate` / `alembic upgrade head` / `make alembic-*` | `make migrate-create name=x` → hand-written SQL; `make migrate-up`; in Railway the dashboard pre-deploy command `./out migrate up` runs it on every deploy |
| `alembic/versions/*` history | replaced wholesale by the single idempotent baseline. Data migrations (`op.execute("UPDATE ...")`) have already run in prod and a fresh DB has no rows to migrate, so they are not carried over. |

## Deployment and tooling

| Python | Go |
|---|---|
| `Procfile`: `web: gunicorn app.main:app ...` (or a `start.sh`) | `web: ./out` |
| `alembic upgrade head` run from `start.sh` or a CI job before deploy | Railway: dashboard pre-deploy command `./out migrate up`; CI: `./out migrate up` in the same job |
| `pyproject.toml` with app deps | `go.mod` (`go mod tidy` fills it). `pyproject.toml` survives only in the tests-only form from `cutover.md`, or is deleted. |
| `.python-version`, `uv.lock` | deleted (`uv.lock` regenerated from the tests-only pyproject if tests stay) |
| `make dev` / `make server` / `make format` | same target names in the Go Makefile (`go run`, `./out`, `gofmt`) |
| `itsdangerous` in `pyproject.toml` | the skeleton lists it but never imports it. If the project uses `URLSafeTimedSerializer` (email verification links, unsubscribe links): either replicate its exact format (base64url payload `.` timestamp `.` HMAC-SHA1 by default — fiddly) or accept that links issued before cutover stop working. Ask the user; usually the second. |
