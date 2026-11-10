# Go File Templates

Replace `<app-name>` with the actual app name throughout. It is the Go module path, so every internal import is `<app-name>/internal/...` and the root package is imported as `app "<app-name>"`.

**Host `generic`** (`--host generic`): do not create `internal/wake/`, and make these edits where the files below use it — remove each `"<app-name>/internal/wake"` import, then:
- `internal/db/db.go`: `if err := pool.Ping(ctx); err != nil {` instead of `wake.Ping(ctx, "DB", pool.Ping)`.
- `internal/db/migrate.go`: `if err := sqlDB.PingContext(ctx); err != nil {` instead of `wake.Ping(ctx, "DB", sqlDB.PingContext)`.
- `internal/cache/cache.go`: `if err := c.Ping(ctx); err != nil {` instead of `wake.Ping(ctx, "REDIS", c.Ping)`.
- `internal/server/server.go`: drop the `dbWake, rdsWake` field, the two `wake.New` blocks and `h = s.wakeDeps(h)`; the `New` comment becomes `mux → recoverPanics → logRequests`.
- `internal/server/middleware.go`: drop `wakeDeps`.
- Drop the comments that mention a sleeping Railway DB/Redis or the Railway pre-deploy command.

---

## `embed.go` (project root)

```go
// Package app embeds the non-Go assets so the deployed binary is self-contained.
package app

import "embed"

// Assets holds templates/ and static/. In DEV_MODE main swaps this for os.DirFS(".")
// so edits show up without a rebuild.
//
//go:embed templates static
var Assets embed.FS

// Migrations holds goose SQL migrations; db.Migrate runs them from the binary itself.
//
//go:embed migrations/*.sql
var Migrations embed.FS
```

**If no database**: remove the `Migrations` var and its directive (an embed pattern that matches no files fails the build).

---

## `cmd/server/main.go`

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"io/fs"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	app "<app-name>"
	"<app-name>/internal/ai"
	"<app-name>/internal/auth"
	"<app-name>/internal/cache"
	"<app-name>/internal/config"
	"<app-name>/internal/db"
	"<app-name>/internal/server"
)

const appName = "<app-name>"

func main() {
	config.Load()
	setupLogging()

	if len(os.Args) > 1 && os.Args[1] == "migrate" {
		migrations, err := fs.Sub(app.Migrations, "migrations")
		if err != nil {
			slog.Error("migrations fs", "err", err)
			os.Exit(1)
		}
		if err := db.Migrate(context.Background(), config.MustEnv("ENGINE_URL"), migrations, os.Args[2:]); err != nil {
			slog.Error("migrate failed", "err", err)
			os.Exit(1)
		}
		return
	}

	if err := run(); err != nil {
		slog.Error("server exited", "err", err)
		os.Exit(1)
	}
}

func setupLogging() {
	level := slog.LevelInfo
	if config.DevMode {
		level = slog.LevelDebug
	}
	handler := slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{
		Level:     level,
		AddSource: true,
		ReplaceAttr: func(_ []string, a slog.Attr) slog.Attr {
			switch a.Key {
			case slog.TimeKey:
				return slog.String(a.Key, a.Value.Time().Format("2006-01-02 15:04:05"))
			case slog.SourceKey:
				if src, ok := a.Value.Any().(*slog.Source); ok {
					return slog.String(a.Key, fmt.Sprintf("%s:%d", filepath.Base(src.File), src.Line))
				}
			}
			return a
		},
	})
	slog.SetDefault(slog.New(handler))
}

func run() error {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	slog.Info("starting", "app", appName, "dev_mode", config.DevMode)

	// Required config — fail here, not on the first request.
	engineURL := config.MustEnv("ENGINE_URL")
	redisURL := config.MustEnv("REDIS_CONNECTION_STRING")
	sessionSecret := config.MustEnv("SESSION_SECRET")
	openRouterKey := config.MustEnv("OPENROUTER_API_KEY")

	var assets fs.FS = app.Assets
	if config.DevMode {
		assets = os.DirFS(".")
	}

	pool, err := db.Connect(ctx, engineURL)
	if err != nil {
		return fmt.Errorf("db: %w", err)
	}
	defer pool.Close()
	slog.Info("DB connected")

	cachePrefix := appName
	if config.DevMode {
		cachePrefix += "-dev"
	}
	c, err := cache.Connect(ctx, redisURL, cachePrefix)
	if err != nil {
		return fmt.Errorf("redis: %w", err)
	}
	defer c.Close()
	slog.Info("Redis connected")

	aiClient, err := ai.New(openRouterKey, assets, c)
	if err != nil {
		return fmt.Errorf("ai: %w", err)
	}

	handler, err := server.New(server.Deps{
		Dev:     config.DevMode,
		Assets:  assets,
		Cookies: auth.New(sessionSecret, !config.DevMode),
		Pool:    pool,
		Cache:   c,
		AI:      aiClient,
	})
	if err != nil {
		return err
	}

	srv := &http.Server{
		Addr:              ":" + config.Env("PORT", "8000"),
		Handler:           handler,
		ReadHeaderTimeout: 10 * time.Second,
	}
	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := srv.Shutdown(shutdownCtx); err != nil {
			slog.Warn("shutdown", "err", err)
		}
	}()

	slog.Info("listening", "addr", srv.Addr)
	if err := srv.ListenAndServe(); !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	slog.Info("stopped")
	return nil
}
```

**If no database**: drop the `migrate` branch, `db.Connect`, `Pool:` and the `db`/`app.Migrations` imports.
**If no Redis**: drop `cache.Connect`, `Cache:`, `cachePrefix`, and pass `nil` as the cache to `ai.New` (the cache helper tolerates a nil cache).
**If no AI**: drop `ai.New`, `AI:`, and `OPENROUTER_API_KEY`.

---

## `internal/config/config.go`

```go
// Package config loads .env and exposes typed environment helpers.
package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/joho/godotenv"
)

// DevMode is true when DEV_MODE=ON. Set by Load.
var DevMode bool

// Load reads .env (or DOT_ENV_PATH). A missing file is fine: production uses real env vars.
func Load() {
	path := os.Getenv("DOT_ENV_PATH")
	if path == "" {
		path = ".env"
	}
	_ = godotenv.Load(path)
	DevMode = strings.ToUpper(os.Getenv("DEV_MODE")) == "ON"
}

// MustEnv returns the variable or exits the process. Call it at startup so a
// misconfigured deploy dies immediately instead of on the first request.
func MustEnv(name string) string {
	v := os.Getenv(name)
	if v == "" {
		fmt.Fprintf(os.Stderr, "Configuration missing: %s\n", name)
		os.Exit(1)
	}
	return v
}

// Env returns the variable or def when unset/empty.
func Env(name, def string) string {
	if v := os.Getenv(name); v != "" {
		return v
	}
	return def
}

// EnvInt returns the variable parsed as int, or def when unset or unparsable.
func EnvInt(name string, def int) int {
	if n, err := strconv.Atoi(os.Getenv(name)); err == nil {
		return n
	}
	return def
}
```

---

## `internal/wake/wake.go`

Only when host is `railway`.

```go
// Package wake pings a dependency with retries before it is used, so a Railway
// Postgres/Redis that went to sleep has time to wake up instead of failing the call.
package wake

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	"<app-name>/internal/config"
)

// Ping calls ping until it succeeds, up to <name>_PING_RETRIES attempts (default 5)
// spaced <name>_PING_INTERVAL seconds apart (default 2). name is "DB" or "REDIS".
func Ping(ctx context.Context, name string, ping func(context.Context) error) error {
	retries := config.EnvInt(name+"_PING_RETRIES", 5)
	interval := time.Duration(config.EnvInt(name+"_PING_INTERVAL", 2)) * time.Second
	for attempt := 1; ; attempt++ {
		err := ping(ctx)
		if err == nil || attempt >= retries {
			return err
		}
		slog.Warn(name+" ping failed, retrying", "attempt", attempt, "retries", retries, "err", err)
		select {
		case <-time.After(interval):
		case <-ctx.Done():
			return fmt.Errorf("%w (last ping error: %v)", ctx.Err(), err)
		}
	}
}

// fresh is how long a ping result is trusted, success or failure. Railway sleeps a service
// only after minutes without traffic, so one that answered seconds ago is still awake; one
// whose retry loop just gave up fails fast instead of making every request wait it out again.
const fresh = 10 * time.Second

// Waker is Ping for hot paths: it skips the ping while the last result (success or
// failure) is fresh, and concurrent callers share one retry loop instead of each running their own.
type Waker struct {
	name   string
	ping   func(context.Context) error
	sem    chan struct{} // 1-slot lock that a cancelled caller can give up waiting on
	lastOK time.Time     // guarded by sem
	failAt time.Time     // guarded by sem: when the last retry loop gave up
	err    error         // guarded by sem: why it gave up
}

func New(name string, ping func(context.Context) error) *Waker {
	return &Waker{name: name, ping: ping, sem: make(chan struct{}, 1)}
}

func (w *Waker) Wake(ctx context.Context) error {
	select {
	case w.sem <- struct{}{}:
	case <-ctx.Done():
		return ctx.Err()
	}
	defer func() { <-w.sem }()
	if time.Since(w.lastOK) < fresh {
		return nil
	}
	if time.Since(w.failAt) < fresh { // a loop recently gave up (maybe while we waited): don't run another
		return w.err
	}
	if err := Ping(ctx, w.name, w.ping); err != nil {
		if ctx.Err() == nil { // our own caller giving up says nothing about the service: don't hand it to the others
			w.failAt, w.err = time.Now(), err
		}
		return err
	}
	w.lastOK = time.Now()
	return nil
}
```

`Ping` runs at startup (`db.Connect`, `cache.Connect`) and in `migrate` before goose touches the DB. `Waker` runs in the server's `wakeDeps` middleware before every non-static request, and in any background worker before each job or tick. Railway can put a service to sleep long after the app started, so a startup-only ping is not enough.

---

## `internal/wake/wake_test.go`

Only when host is `railway`.

```go
package wake

import (
	"context"
	"errors"
	"sync/atomic"
	"testing"
)

func TestPing(t *testing.T) {
	t.Setenv("DB_PING_RETRIES", "3")
	t.Setenv("DB_PING_INTERVAL", "0")
	calls := 0
	asleepTwice := func(context.Context) error {
		if calls++; calls < 3 {
			return errors.New("asleep")
		}
		return nil
	}
	if err := Ping(context.Background(), "DB", asleepTwice); err != nil || calls != 3 {
		t.Fatalf("woke: err=%v calls=%d, want nil 3", err, calls)
	}
	calls = 0
	down := func(context.Context) error { calls++; return errors.New("down") }
	if err := Ping(context.Background(), "DB", down); err == nil || calls != 3 {
		t.Fatalf("down: err=%v calls=%d, want error 3", err, calls)
	}
}

func TestWakerSkipsWhileFresh(t *testing.T) {
	calls := 0
	w := New("DB", func(context.Context) error { calls++; return nil })
	for range 3 {
		if err := w.Wake(context.Background()); err != nil {
			t.Fatal(err)
		}
	}
	if calls != 1 {
		t.Fatalf("calls=%d, want 1 (later wakes within the fresh window skip the ping)", calls)
	}
}

func TestWakerCancelledLoopIsNotShared(t *testing.T) {
	t.Setenv("DB_PING_RETRIES", "3")
	t.Setenv("DB_PING_INTERVAL", "0")
	w := New("DB", func(ctx context.Context) error { return ctx.Err() })
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if err := w.Wake(ctx); !errors.Is(err, context.Canceled) {
		t.Fatalf("err=%v, want context.Canceled", err)
	}
	w.ping = func(context.Context) error { return nil }
	if err := w.Wake(context.Background()); err != nil {
		t.Fatalf("a live caller inherited the cancelled caller's error: %v", err)
	}
}

func TestWakerSharesFailedLoop(t *testing.T) {
	t.Setenv("DB_PING_RETRIES", "3")
	t.Setenv("DB_PING_INTERVAL", "0")
	var calls atomic.Int32
	w := New("DB", func(context.Context) error { calls.Add(1); return errors.New("down") })
	errs := make(chan error, 5)
	for range 5 {
		go func() { errs <- w.Wake(context.Background()) }()
	}
	for range 5 {
		if err := <-errs; err == nil {
			t.Fatal("want error from a down DB")
		}
	}
	if n := calls.Load(); n != 3 {
		t.Fatalf("pings=%d, want 3 (one shared retry loop, not one per caller)", n)
	}
}

func TestWakerFailsFastAfterFailedLoop(t *testing.T) {
	t.Setenv("DB_PING_RETRIES", "2")
	t.Setenv("DB_PING_INTERVAL", "0")
	calls := 0
	w := New("DB", func(context.Context) error { calls++; return errors.New("down") })
	first := w.Wake(context.Background())
	second := w.Wake(context.Background())
	if first == nil || second != first || calls != 2 {
		t.Fatalf("first=%v second=%v calls=%d, want the same error and 2 pings (no second loop)", first, second, calls)
	}
}
```

---

## `internal/auth/cookies.go`

```go
// Package auth implements HMAC-signed cookies — the only per-user state mechanism.
package auth

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"net/http"
	"strings"
)

const maxAge = 30 * 24 * 3600 // 30 days

// Cookies signs and verifies cookie values with SESSION_SECRET.
type Cookies struct {
	secret []byte
	secure bool
}

// New returns a signer. Pass secure=false in DEV_MODE so cookies work over http://localhost.
func New(secret string, secure bool) *Cookies {
	return &Cookies{secret: []byte(secret), secure: secure}
}

func (c *Cookies) mac(value string) string {
	m := hmac.New(sha256.New, c.secret)
	m.Write([]byte(value))
	return hex.EncodeToString(m.Sum(nil))
}

func (c *Cookies) sign(value string) string {
	return value + "." + c.mac(value)
}

func (c *Cookies) verify(signed string) (string, bool) {
	i := strings.LastIndexByte(signed, '.')
	if i < 0 {
		return "", false
	}
	value, sig := signed[:i], signed[i+1:]
	if !hmac.Equal([]byte(sig), []byte(c.mac(value))) {
		return "", false
	}
	return value, true
}

// Get returns the verified value of a signed cookie.
func (c *Cookies) Get(r *http.Request, name string) (string, bool) {
	ck, err := r.Cookie(name)
	if err != nil {
		return "", false
	}
	return c.verify(ck.Value)
}

// Set writes a signed cookie. Call before writing the response body.
func (c *Cookies) Set(w http.ResponseWriter, name, value string) {
	http.SetCookie(w, &http.Cookie{
		Name:     name,
		Value:    c.sign(value),
		Path:     "/",
		HttpOnly: true,
		Secure:   c.secure,
		SameSite: http.SameSiteLaxMode,
		MaxAge:   maxAge,
	})
}

// Clear deletes a cookie.
func (c *Cookies) Clear(w http.ResponseWriter, name string) {
	http.SetCookie(w, &http.Cookie{Name: name, Value: "", Path: "/", MaxAge: -1})
}

// IsAuthenticated reports whether a valid user_id cookie is present.
func (c *Cookies) IsAuthenticated(r *http.Request) bool {
	_, ok := c.Get(r, "user_id")
	return ok
}

// UserID returns the authenticated user id, or "" when not logged in.
func (c *Cookies) UserID(r *http.Request) string {
	id, _ := c.Get(r, "user_id")
	return id
}

// RequireAuth is middleware that bounces anonymous requests to / (303), matching
// the 401-redirect behaviour of server.handle.
func (c *Cookies) RequireAuth(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !c.IsAuthenticated(r) {
			http.Redirect(w, r, "/", http.StatusSeeOther)
			return
		}
		next.ServeHTTP(w, r)
	})
}
```

---

## `internal/db/db.go`

```go
// Package db owns the PostgreSQL pool, migrations and queries.
package db

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"<app-name>/internal/wake"
)

// Connect opens a pool and pings it, retrying so a sleeping Railway DB can wake up.
func Connect(ctx context.Context, url string) (*pgxpool.Pool, error) {
	cfg, err := pgxpool.ParseConfig(url)
	if err != nil {
		return nil, err
	}
	// One process serves every request, so size the pool once (no per-worker split).
	cfg.MaxConns = 20
	cfg.MinConns = 1
	cfg.MaxConnLifetime = 5 * time.Minute
	cfg.HealthCheckPeriod = 30 * time.Second

	pool, err := pgxpool.NewWithConfig(ctx, cfg)
	if err != nil {
		return nil, err
	}

	if err := wake.Ping(ctx, "DB", pool.Ping); err != nil {
		pool.Close()
		return nil, err
	}
	return pool, nil
}
```

---

## `internal/db/migrate.go`

```go
package db

import (
	"context"
	"database/sql"
	"fmt"
	"io/fs"

	_ "github.com/jackc/pgx/v5/stdlib" // registers the "pgx" database/sql driver goose needs
	"github.com/pressly/goose/v3"

	"<app-name>/internal/wake"
)

// Migrate implements `server migrate up|down|status|create <name>` over the embedded
// migrations. The same binary runs in Railway, so nothing extra is installed there:
// Railway's pre-deploy command (set in the dashboard) runs `./out migrate up` on every deploy.
func Migrate(ctx context.Context, url string, migrations fs.FS, args []string) error {
	if len(args) == 0 {
		return fmt.Errorf("usage: migrate up|down|status|create <name>")
	}
	sqlDB, err := sql.Open("pgx", url) // lazy: no connection until first use
	if err != nil {
		return err
	}
	defer sqlDB.Close()

	if args[0] == "create" {
		if len(args) < 2 {
			return fmt.Errorf("usage: migrate create <name>")
		}
		// create writes to the OS filesystem (embedded FS is read-only); timestamped filename.
		return goose.Create(sqlDB, "migrations", args[1], "sql")
	}

	// The pre-deploy command is often the first thing to hit a sleeping Railway Postgres.
	if err := wake.Ping(ctx, "DB", sqlDB.PingContext); err != nil {
		return fmt.Errorf("db: %w", err)
	}

	p, err := goose.NewProvider(goose.DialectPostgres, sqlDB, migrations)
	if err != nil {
		return err
	}
	switch args[0] {
	case "up":
		results, err := p.Up(ctx)
		for _, r := range results {
			fmt.Println("applied", r.Source.Path)
		}
		return err
	case "down":
		r, err := p.Down(ctx)
		if r != nil {
			fmt.Println("rolled back", r.Source.Path)
		}
		return err
	case "status":
		statuses, err := p.Status(ctx)
		for _, s := range statuses {
			fmt.Printf("%-8s %s\n", s.State, s.Source.Path)
		}
		return err
	}
	return fmt.Errorf("unknown migrate command %q", args[0])
}
```

---

## `internal/db/items.go`

```go
package db

import (
	"context"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// Item is the example model. Replace with your actual domain models.
// Column order in every SELECT must match the struct field order (RowToStructByPos).
type Item struct {
	ID          string
	Name        string
	Description *string
}

const itemCols = `id::text, name, description`

func ListItems(ctx context.Context, pool *pgxpool.Pool) ([]Item, error) {
	rows, _ := pool.Query(ctx, `SELECT `+itemCols+` FROM items ORDER BY name`)
	return pgx.CollectRows(rows, pgx.RowToStructByPos[Item])
}

// GetItem returns pgx.ErrNoRows when the id does not exist.
func GetItem(ctx context.Context, pool *pgxpool.Pool, id string) (Item, error) {
	rows, _ := pool.Query(ctx, `SELECT `+itemCols+` FROM items WHERE id = $1`, id)
	return pgx.CollectOneRow(rows, pgx.RowToStructByPos[Item])
}

func CreateItem(ctx context.Context, pool *pgxpool.Pool, name string, description *string) (Item, error) {
	rows, _ := pool.Query(ctx,
		`INSERT INTO items (name, description) VALUES ($1, $2) RETURNING `+itemCols,
		name, description)
	return pgx.CollectOneRow(rows, pgx.RowToStructByPos[Item])
}

func UpdateItem(ctx context.Context, pool *pgxpool.Pool, it Item) error {
	_, err := pool.Exec(ctx,
		`UPDATE items SET name = $2, description = $3 WHERE id = $1`,
		it.ID, it.Name, it.Description)
	return err
}

func DeleteItem(ctx context.Context, pool *pgxpool.Pool, id string) error {
	_, err := pool.Exec(ctx, `DELETE FROM items WHERE id = $1`, id)
	return err
}
```

`rows, _ := pool.Query(...)` followed by `CollectRows` is the documented pgx pattern: a Query error is surfaced again by `rows.Err()`, which `CollectRows` returns.

---

## `internal/cache/cache.go`

```go
// Package cache wraps Redis with a generic JSON memoization helper.
package cache

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"time"

	"github.com/redis/go-redis/v9"

	"<app-name>/internal/wake"
)

// Cache is a Redis client with a key prefix ("<app-name>" or "<app-name>-dev").
type Cache struct {
	Client *redis.Client
	prefix string
}

// Connect parses a redis:// URL, pings with retry (sleeping Railway Redis) and returns the cache.
func Connect(ctx context.Context, url, prefix string) (*Cache, error) {
	opt, err := redis.ParseURL(url)
	if err != nil {
		return nil, err
	}
	c := &Cache{Client: redis.NewClient(opt), prefix: prefix}
	if err := wake.Ping(ctx, "REDIS", c.Ping); err != nil {
		_ = c.Close()
		return nil, err
	}
	return c, nil
}

func (c *Cache) Ping(ctx context.Context) error { return c.Client.Ping(ctx).Err() }

func (c *Cache) Close() error { return c.Client.Close() }

func (c *Cache) key(namespace, key string) string {
	return c.prefix + ":" + namespace + ":" + key
}

// Cached returns the JSON-cached value for namespace+key, or runs compute, stores the
// result (ttl 0 = no expiry) and returns it. A nil *Cache disables caching, which keeps
// tests and no-Redis builds simple. Cache failures are logged, never fatal.
func Cached[T any](ctx context.Context, c *Cache, namespace, key string, ttl time.Duration, compute func() (T, error)) (T, error) {
	var v T
	if c == nil {
		return compute()
	}
	full := c.key(namespace, key)
	raw, err := c.Client.Get(ctx, full).Bytes()
	switch {
	case err == nil:
		if err := json.Unmarshal(raw, &v); err == nil {
			return v, nil
		}
		slog.Warn("cache decode failed, recomputing", "key", full)
	case !errors.Is(err, redis.Nil):
		slog.Warn("cache get failed", "key", full, "err", err)
	}

	v, err = compute()
	if err != nil {
		return v, err
	}
	if raw, err := json.Marshal(v); err == nil {
		if err := c.Client.Set(ctx, full, raw, ttl).Err(); err != nil {
			slog.Warn("cache set failed", "key", full, "err", err)
		}
	}
	return v, nil
}
```

---

## `internal/ai/ai.go`

```go
// Package ai calls OpenRouter's chat completions API with prompt templates and caching.
package ai

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"io/fs"
	"log/slog"
	"net/http"
	"strings"
	"text/template"
	"time"

	"<app-name>/internal/cache"
)

const (
	endpoint     = "https://openrouter.ai/api/v1/chat/completions"
	DefaultModel = "openai/gpt-4o-mini"
)

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// Options mirrors the keyword arguments of the Python invoke_ai_model.
type Options struct {
	Model            string
	Temperature      float64
	SystemPromptName string         // rendered from templates/prompts/<name>.txt and prepended
	PromptContext    any            // data for that template
	Extra            map[string]any // forwarded verbatim into the request body (top_p, max_tokens, ...)
}

type Response struct {
	Choices []struct {
		Message Message `json:"message"`
	} `json:"choices"`
	Usage map[string]any `json:"usage"`
}

type Client struct {
	apiKey  string
	prompts *template.Template
	cache   *cache.Cache
	http    *http.Client
}

// New parses templates/prompts/*.txt from assets. cache may be nil (no caching).
func New(apiKey string, assets fs.FS, c *cache.Cache) (*Client, error) {
	prompts, err := template.ParseFS(assets, "templates/prompts/*.txt")
	if err != nil {
		return nil, fmt.Errorf("prompt templates: %w", err)
	}
	return &Client{
		apiKey:  apiKey,
		prompts: prompts,
		cache:   c,
		http:    &http.Client{Timeout: 60 * time.Second},
	}, nil
}

// RenderPrompt renders templates/prompts/<name>.txt with data.
func (c *Client) RenderPrompt(name string, data any) (string, error) {
	var b strings.Builder
	if err := c.prompts.ExecuteTemplate(&b, name+".txt", data); err != nil {
		return "", err
	}
	return strings.TrimSpace(b.String()), nil
}

// Invoke sends a chat completion, memoized in Redis under namespace "ai-model" keyed by
// the sha256 of the exact request body (no TTL).
func (c *Client) Invoke(ctx context.Context, messages []Message, opts Options) (*Response, error) {
	if opts.Model == "" {
		opts.Model = DefaultModel
	}
	if opts.SystemPromptName != "" {
		system, err := c.RenderPrompt(opts.SystemPromptName, opts.PromptContext)
		if err != nil {
			return nil, err
		}
		slog.Debug("system prompt", "text", system)
		messages = append([]Message{{Role: "system", Content: system}}, messages...)
	}
	body := map[string]any{
		"model":       opts.Model,
		"messages":    messages,
		"temperature": opts.Temperature,
	}
	for k, v := range opts.Extra {
		body[k] = v
	}
	raw, err := json.Marshal(body)
	if err != nil {
		return nil, err
	}
	sum := sha256.Sum256(raw)
	return cache.Cached(ctx, c.cache, "ai-model", hex.EncodeToString(sum[:]), 0, func() (*Response, error) {
		slog.Debug("calling AI model", "model", opts.Model)
		return c.send(ctx, raw)
	})
}

func (c *Client) send(ctx context.Context, raw []byte) (*Response, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(raw))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+c.apiKey)
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.http.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("openrouter %d: %s", resp.StatusCode, data)
	}
	var out Response
	if err := json.Unmarshal(data, &out); err != nil {
		return nil, err
	}
	slog.Debug("AI response usage", "usage", out.Usage)
	return &out, nil
}

// GetResponse returns the first choice's trimmed content.
func (c *Client) GetResponse(ctx context.Context, messages []Message, opts Options) (string, error) {
	resp, err := c.Invoke(ctx, messages, opts)
	if err != nil {
		return "", err
	}
	if len(resp.Choices) == 0 {
		return "", fmt.Errorf("openrouter: empty choices")
	}
	content := strings.TrimSpace(resp.Choices[0].Message.Content)
	slog.Debug("AI response", "content", truncate(content, 300))
	return content, nil
}

// GetJSONResponse extracts the outermost {...} from the reply and decodes it.
func (c *Client) GetJSONResponse(ctx context.Context, messages []Message, opts Options) (map[string]any, error) {
	if opts.Extra == nil {
		opts.Extra = map[string]any{}
	}
	opts.Extra["top_p"] = 1
	content, err := c.GetResponse(ctx, messages, opts)
	if err != nil {
		return nil, err
	}
	if start, end := strings.Index(content, "{"), strings.LastIndex(content, "}"); start != -1 && end > start {
		content = content[start : end+1]
	}
	var out map[string]any
	if err := json.Unmarshal([]byte(content), &out); err != nil {
		return nil, fmt.Errorf("ai json: %w", err)
	}
	return out, nil
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "…"
}
```

Write the `--ai-model` value as `DefaultModel` (`openai/gpt-4o-mini` when the flag is not given).

---

## `internal/server/server.go`

```go
// Package server wires routes, templates and middleware into an http.Handler.
package server

import (
	"io/fs"
	"net/http"

	"github.com/jackc/pgx/v5/pgxpool"

	"<app-name>/internal/ai"
	"<app-name>/internal/auth"
	"<app-name>/internal/cache"
	"<app-name>/internal/wake"
)

// Deps is everything handlers need. Nil Pool/Cache/AI are allowed for features not scaffolded.
type Deps struct {
	Dev     bool
	Assets  fs.FS // templates/ and static/ (embedded in prod, os.DirFS(".") in dev)
	Cookies *auth.Cookies
	Pool    *pgxpool.Pool
	Cache   *cache.Cache
	AI      *ai.Client
}

type Server struct {
	Deps
	tmpl            *Templates
	dbWake, rdsWake *wake.Waker // nil when Pool/Cache is nil
}

// New builds the handler: mux → wakeDeps → recoverPanics → logRequests.
func New(d Deps) (http.Handler, error) {
	tmpl, err := ParseTemplates(d.Assets, d.Dev)
	if err != nil {
		return nil, err
	}
	s := &Server{Deps: d, tmpl: tmpl}
	if d.Pool != nil {
		s.dbWake = wake.New("DB", d.Pool.Ping)
	}
	if d.Cache != nil {
		s.rdsWake = wake.New("REDIS", d.Cache.Ping)
	}

	mux := http.NewServeMux()
	static, err := fs.Sub(d.Assets, "static")
	if err != nil {
		return nil, err
	}
	mux.Handle("GET /static/", http.StripPrefix("/static/", http.FileServerFS(static)))
	mux.HandleFunc("GET /{$}", s.handle(s.home))
	// Add more routes here, e.g.:
	// mux.Handle("GET /items", d.Cookies.RequireAuth(s.handle(s.listItems)))

	var h http.Handler = mux
	h = s.wakeDeps(h)
	h = recoverPanics(h)
	h = logRequests(d.Dev, h)
	return h, nil
}
```

---

## `internal/server/middleware.go`

```go
package server

import (
	"fmt"
	"log/slog"
	"net/http"
	"runtime/debug"
	"strings"
	"time"
)

type statusWriter struct {
	http.ResponseWriter
	status int
}

func (w *statusWriter) WriteHeader(code int) {
	w.status = code
	w.ResponseWriter.WriteHeader(code)
}

// logRequests logs "METHOD /path -> status (Nms)" for every request. In dev it also
// disables caching of /static/ so CSS/JS edits show immediately.
func logRequests(dev bool, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		if dev && strings.HasPrefix(r.URL.Path, "/static/") {
			w.Header().Set("Cache-Control", "no-store")
		}
		sw := &statusWriter{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(sw, r)
		slog.Info(fmt.Sprintf("%s %s -> %d (%dms)",
			r.Method, r.URL.Path, sw.status, time.Since(start).Milliseconds()))
	})
}

// wakeDeps makes sure a Railway Postgres/Redis that went to sleep is awake before any
// route (or route middleware) runs, by pinging with retry when the last ping is stale.
func (s *Server) wakeDeps(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !strings.HasPrefix(r.URL.Path, "/static/") {
			if s.dbWake != nil {
				if err := s.dbWake.Wake(r.Context()); err != nil {
					if r.Context().Err() == nil { // not when the client is gone or the request deadline passed
						slog.Error("DB not awake", "method", r.Method, "path", r.URL.Path, "err", err)
						http.Error(w, http.StatusText(http.StatusInternalServerError), http.StatusInternalServerError)
					}
					return
				}
			}
			// Redis is an optimisation (cache.Cached tolerates failures), so a down Redis must not 500 every route.
			if s.rdsWake != nil {
				if err := s.rdsWake.Wake(r.Context()); err != nil {
					slog.Warn("Redis not awake, continuing without cache", "err", err)
				}
			}
		}
		next.ServeHTTP(w, r)
	})
}

// recoverPanics turns a handler panic into a logged 500 instead of a dropped connection.
func recoverPanics(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if rec := recover(); rec != nil {
				slog.Error("panic", "method", r.Method, "path", r.URL.Path, "err", rec, "stack", string(debug.Stack()))
				http.Error(w, http.StatusText(http.StatusInternalServerError), http.StatusInternalServerError)
			}
		}()
		next.ServeHTTP(w, r)
	})
}
```

---

## `internal/server/errors.go`

```go
package server

import (
	"errors"
	"log/slog"
	"net/http"
)

// HTTPError is returned by handlers to produce a specific status code.
type HTTPError struct {
	Code    int
	Message string
}

func (e *HTTPError) Error() string { return e.Message }

// Err builds an HTTPError; an empty msg uses the standard status text.
func Err(code int, msg string) *HTTPError {
	if msg == "" {
		msg = http.StatusText(code)
	}
	return &HTTPError{Code: code, Message: msg}
}

type handlerFunc func(w http.ResponseWriter, r *http.Request) error

// handle adapts error-returning handlers: 401 → 303 redirect to /, 5xx logged as error,
// 4xx as warning, anything that is not an *HTTPError becomes a logged 500.
func (s *Server) handle(h handlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		err := h(w, r)
		if err == nil || r.Context().Err() != nil { // client gone or request deadline passed
			return
		}
		var he *HTTPError
		if !errors.As(err, &he) {
			he = Err(http.StatusInternalServerError, "")
			slog.Error("unhandled error", "method", r.Method, "path", r.URL.Path, "err", err)
		} else if he.Code >= 500 {
			slog.Error("HTTP error", "status", he.Code, "method", r.Method, "path", r.URL.Path, "detail", he.Message)
		} else {
			slog.Warn("HTTP error", "status", he.Code, "method", r.Method, "path", r.URL.Path, "detail", he.Message)
		}
		if he.Code == http.StatusUnauthorized {
			http.Redirect(w, r, "/", http.StatusSeeOther)
			return
		}
		http.Error(w, he.Message, he.Code)
	}
}
```

---

## `internal/server/render.go`

```go
package server

import (
	"bytes"
	"encoding/json"
	"fmt"
	"html/template"
	"io/fs"
	"net/http"
	"path"
)

// funcs are available in every template. `json` marks the value safe for use inside
// single-quoted attributes: x-data='{{ json .State }}'.
var funcs = template.FuncMap{
	"json": func(v any) (template.JS, error) {
		b, err := json.Marshal(v)
		return template.JS(b), err
	},
}

// Templates holds one parsed set per page: base.html + templates/partials/*.html + the page,
// so each page can fill base's blocks and reuse partials for HTMX fragments.
type Templates struct {
	assets fs.FS
	dev    bool
	pages  map[string]*template.Template
}

func ParseTemplates(assets fs.FS, dev bool) (*Templates, error) {
	t := &Templates{assets: assets, dev: dev}
	if err := t.parse(); err != nil {
		return nil, err
	}
	return t, nil
}

func (t *Templates) parse() error {
	pageFiles, err := fs.Glob(t.assets, "templates/*.html")
	if err != nil {
		return err
	}
	partials, _ := fs.Glob(t.assets, "templates/partials/*.html")
	pages := map[string]*template.Template{}
	for _, file := range pageFiles {
		name := path.Base(file)
		if name == "base.html" {
			continue
		}
		files := append([]string{"templates/base.html"}, partials...)
		files = append(files, file)
		tmpl, err := template.New("").Funcs(funcs).ParseFS(t.assets, files...)
		if err != nil {
			return fmt.Errorf("parse %s: %w", file, err)
		}
		pages[name] = tmpl
	}
	t.pages = pages
	return nil
}

// Render executes page `name` inside base.html. The output is buffered so a template
// error produces a clean 500 instead of a half-written page.
func (t *Templates) Render(w http.ResponseWriter, name string, data any) error {
	if t.dev { // re-parse on every request so edits show without restart
		if err := t.parse(); err != nil {
			return err
		}
	}
	tmpl, ok := t.pages[name]
	if !ok {
		return fmt.Errorf("template %q not found", name)
	}
	var buf bytes.Buffer
	if err := tmpl.ExecuteTemplate(&buf, "base.html", data); err != nil {
		return err
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_, err := buf.WriteTo(w)
	return err
}

// RenderPartial executes a single named template (a partial) — for HTMX fragment responses.
func (t *Templates) RenderPartial(w http.ResponseWriter, page, partial string, data any) error {
	tmpl, ok := t.pages[page]
	if !ok {
		return fmt.Errorf("template %q not found", page)
	}
	var buf bytes.Buffer
	if err := tmpl.ExecuteTemplate(&buf, partial, data); err != nil {
		return err
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_, err := buf.WriteTo(w)
	return err
}
```

---

## `internal/server/home.go`

```go
package server

import "net/http"

func (s *Server) home(w http.ResponseWriter, r *http.Request) error {
	return s.tmpl.Render(w, "index.html", map[string]any{
		"Authenticated": s.Cookies.IsAuthenticated(r),
	})
}
```

---

## `internal/server/server_test.go`

```go
package server

import (
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	"<app-name>/internal/auth"
)

func TestHome(t *testing.T) {
	h, err := New(Deps{
		Assets:  os.DirFS("../.."), // project root: templates/ and static/
		Cookies: auth.New("test-secret", false),
	})
	if err != nil {
		t.Fatal(err)
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/", nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("GET / = %d, want 200", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), `hx-boost="true"`) {
		t.Fatal("base.html not rendered: hx-boost missing")
	}
}
```
