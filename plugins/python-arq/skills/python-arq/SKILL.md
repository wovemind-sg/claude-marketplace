---
name: python-arq
description: Complete reference for arq (v0.28), the Python asyncio + Redis job queue library by the pydantic author. Use whenever writing, reviewing, or debugging Python code that imports arq, enqueues background jobs with enqueue_job, defines a WorkerSettings class, runs the `arq` CLI worker, schedules cron jobs, or handles job results/retries/aborts. Also trigger when the user asks for "background tasks", "task queue", "job queue", or "deferred/scheduled jobs" in an async Python (FastAPI, aiohttp, etc.) app backed by Redis, even if they don't name arq.
---
# arq — asyncio + Redis job queue

arq = small (~1k lines) job-queue lib. Two halves: **client** enqueue jobs into Redis sorted set; **worker process** (start via `arq` CLI) poll set, run registered coroutines. Jobs + results pickle-serialized by default. Current version 0.28.0. Deps: `redis[hiredis]>=4.2,<6`, `click`. Install: `pip install arq`.

Public API (all importable from `arq`): `create_pool`, `ArqRedis`, `Worker`, `func`, `run_worker`, `check_health`, `cron`, `Retry`. Plus `arq.connections.RedisSettings`, `arq.jobs.Job / JobStatus / JobDef / JobResult / ResultNotFound / SerializationError / DeserializationError`, `arq.worker.FailedJobs / JobExecutionFailed`.

Exact signatures: read `references/api-reference.md` in this skill for full param lists, defaults, Redis key layout.

## Canonical example (both halves)

```python
# tasks.py
from httpx import AsyncClient
from arq import create_pool
from arq.connections import RedisSettings

REDIS = RedisSettings()  # localhost:6379 db 0; or RedisSettings.from_dsn('redis://host:6379/1')

async def download_content(ctx, url):          # ctx dict is ALWAYS first arg
    r = await ctx['session'].get(url)
    return len(r.text)                          # return value stored as job result (must serialize)

async def startup(ctx):
    ctx['session'] = AsyncClient()              # share resources via ctx

async def shutdown(ctx):
    await ctx['session'].aclose()

class WorkerSettings:                           # plain class, read by `arq` CLI
    functions = [download_content]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = REDIS

# client side
async def main():
    redis = await create_pool(REDIS)            # returns ArqRedis (subclass of redis.asyncio.Redis)
    job = await redis.enqueue_job('download_content', 'https://example.com')
```

Run worker: `arq tasks.WorkerSettings`. CLI flags: `--burst/--no-burst` (exit when queue empty), `--check` (health check, exit code 0/1), `--watch <dir>` (auto-reload, need `watchfiles`), `-v`, `--custom-log-dict <import.path>`.

## Enqueueing

```python
await redis.enqueue_job(
    'function_name',            # STRING name (Function.name / coroutine __qualname__), not the function object
    *args,
    _job_id=None,               # set → enforces uniqueness (see below)
    _queue_name=None,           # default 'arq:queue'
    _defer_until=None,          # datetime to run at  ┐ both set → RuntimeError
    _defer_by=None,             # int/float secs or timedelta ┘
    _expires=None,              # don't run after this delay; default 24h + defer time
    _job_try=None,              # override try counter (re-enqueue from inside a job)
    **kwargs,
) -> Job | None
```

- Returns `Job` handle, or **`None`** when job w/ `_job_id` already exists — either still queued/running **or result still stored**. Uniqueness lasts til result key expires (`keep_result`). Always handle `None` case.
- Deferred jobs: score in sorted set = run timestamp; status `deferred` til then.
- Job passing `_expires` before worker picks it up → fails w/ `JobExecutionFailed('job expired')`.

## Job handle

```python
job.job_id
await job.status()       # JobStatus: deferred | queued | in_progress | complete | not_found
await job.info()         # JobDef | None — function, args, kwargs, job_try, enqueue_time, score; no wait
await job.result_info()  # JobResult | None — adds success, result, start/finish_time; NEVER raises job's exception
await job.result(timeout=None, poll_delay=0.5)  # waits; returns result OR re-raises job's exception
await job.abort(timeout=None)                   # True if aborted; needs allow_abort_jobs=True on worker
```

`job.result()` error flows:
- job raised → that exception re-raised in caller
- `timeout` exceeded → `asyncio.TimeoutError`
- job not in queue, no result stored (e.g. `keep_result=0`, or result expired) → `ResultNotFound`
- stored failure not exception instance (custom serializer lost it) → `SerializationError`

`abort()`: cancels queued/running job (raises `asyncio.CancelledError` inside it). Returns `False` if job already finished or outcome unknown. Aborted job's stored result = `CancelledError`; counts as failed. Worker needs `allow_abort_jobs=True`, else abort request ignored.

## Job functions, ctx, per-function config

Every job coroutine: `async def fn(ctx, *args, **kwargs)`. Worker injects into ctx: `ctx['redis']` (the ArqRedis pool — enqueue follow-up jobs w/ it), `ctx['job_id']`, `ctx['job_try']` (1-based), `ctx['enqueue_time']` (datetime), `ctx['score']`; plus whatever `on_startup` added. Worker-level `ctx=` dict merges in too.

Per-function overrides via `arq.func()` wrapper in `functions` list:

```python
from arq import func
class WorkerSettings:
    functions = [func(download_content, name=None, timeout=60, keep_result=3600,
                      keep_result_forever=None, max_tries=3)]
```

`func()` also accepts import string `'module.fn'`. Non-coroutine → `RuntimeError`. `keep_result=0` → result not stored (and `job.result()` will raise `ResultNotFound`).

## Retry semantics

- Raise `Retry(defer=secs_or_timedelta)` inside job → re-queued after `defer` (same job_id; `ctx['job_try']` increments). Classic backoff: `raise Retry(defer=ctx['job_try'] * 5)`.
- `max_tries` (worker default 5, per-function override) exceeded → job fails w/ `JobExecutionFailed('max N retries exceeded')`.
- Worker shutdown / `asyncio.CancelledError` mid-job → job re-queued, re-run (counts as retry, not failure) — **jobs run at-least-once; make idempotent** (idempotency keys, upserts, transactions).
- `retry_jobs=False` on worker → Retry/cancellation become failures instead.
- Any other exception → job failed, exception pickled as result, re-raised by `job.result()`. No auto-retry on ordinary exceptions — only `Retry`, cancellation, or worker death re-run job.

## Worker settings (most used; full list in reference)

```python
class WorkerSettings:
    functions = [...]                  # required (or cron_jobs); raw coroutines or func(...)
    cron_jobs = [...]
    redis_settings = RedisSettings()   # or redis_pool = existing ArqRedis
    queue_name = 'arq:queue'
    max_jobs = 10                      # concurrent jobs (asyncio tasks, one process)
    job_timeout = 300                  # secs; exceeded → asyncio.TimeoutError, job fails
    keep_result = 3600                 # secs to keep results; 0 = don't store
    max_tries = 5
    poll_delay = 0.5
    on_startup / on_shutdown / on_job_start / on_job_end = async fn(ctx)
    after_job_end = async fn(ctx)      # runs after result recorded
    allow_abort_jobs = False
    retry_jobs = True
    handle_signals = True              # False when embedding in another framework
    job_completion_wait = 0            # secs; graceful k8s shutdown: stop picking, wait, then cancel
    health_check_interval = 3600
    timezone = None                    # tzinfo for cron; default system tz
    job_serializer / job_deserializer  # must MATCH the client pool's
```

Programmatic: `arq.worker.create_worker(WorkerSettings, **overrides)` / `run_worker(...)` (blocking) / `await worker.async_run()` (no signal handling teardown, testing) / `await worker.run_check()` (burst-style; raises `FailedJobs(count, job_results)` if any failed, else returns completed count).

## Cron

```python
from arq import cron
class WorkerSettings:
    cron_jobs = [cron(report, hour={9, 17}, minute=30)]  # 09:30 & 17:30 daily
```

`cron(coroutine, *, name, month, day, weekday, hour, minute, second=0, microsecond=123456, run_at_startup=False, unique=True, job_id=None, timeout, keep_result=0, keep_result_forever=False, max_tries=1)`. Time fields: int, set of ints, or None=every; weekday also `'mon'…'sun'`. Field left None matches every value — `cron(f)` w/ all None runs **every second**; always pin fields above wanted granularity. `unique=True` dedupes across multiple workers (job_id derived from scheduled time). Cron defaults differ from normal jobs: `keep_result=0`, `max_tries=1`. Worker `timezone` governs schedule eval; `ARQ_TIMEZONE` env var affects timestamp decode.

## Serialization

Default pickle → args, kwargs, return values, raised exceptions must all be picklable; client + worker must share codebase (same import paths). Custom: pass `job_serializer=msgpack.packb, job_deserializer=lambda b: msgpack.unpackb(b, raw=False)` to BOTH `create_pool()` and WorkerSettings — mismatch = `DeserializationError`/garbage. Serialization failure on enqueue → `SerializationError`. Result that fails to serialize → stored as failed w/ string `'unable to serialize result'`.

## Error/exception map

| Exception | Where raised | Meaning |
|---|---|---|
| `Retry` | you raise in job | re-queue job (respects max_tries) |
| `ResultNotFound` | `job.result()` | no result stored + job gone; usually `keep_result=0` or expired |
| `asyncio.TimeoutError` | `job.result(timeout=)` caller; also fails job when `job_timeout` exceeded | wait/run too long |
| `SerializationError` / `DeserializationError` | enqueue / decode | pickle (or custom serializer) failed |
| `JobExecutionFailed` | stored as result | expired, max retries exceeded, or function name not registered on worker |
| `FailedJobs(count, job_results)` | `worker.run_check()` | ≥1 job failed in burst run |
| `RuntimeError` | `enqueue_job` w/ both defer args; `func()`/`cron()` on non-coroutine; `create_pool` sentinel misconfig | config error |

## Gotchas

- **At-least-once, not exactly-once.** Worker crash mid-job → job re-runs once `arq:in-progress:{id}` key (TTL = max job timeout + 10s) expires. Design idempotent.
- Function referenced by **string** at enqueue time; typo/unregistered name → job fails at execution ('function not found'), not at enqueue.
- `enqueue_job` returning `None` = silent dedup, not error. Want re-run same `_job_id`? Delete old result first or lower `keep_result`.
- One worker process = `max_jobs` concurrent asyncio tasks. CPU-bound/blocking sync work: wrap w/ `loop.run_in_executor` + `ProcessPoolExecutor` stored in ctx at startup; or run more worker processes (safe — queue ops transactional).
- Results poll every `poll_delay` (0.5s) — `job.result()` adds up to that latency.
- Queue depth: `await redis.zcard('arq:queue')`. All queued jobs: `await redis.queued_jobs()`. All results: `await redis.all_job_results()` (KEYS scan — dev/test only).
- Health check: worker writes `arq:queue:health-check` key; verify w/ `arq --check tasks.WorkerSettings`.
- Testing pattern: `Worker(functions=[...], redis_pool=pool, burst=True, poll_delay=0)` then `await worker.run_check()`; or CLI `--burst`.
- FastAPI/aiohttp integration: `create_pool()` once at app startup, stash on app state, `enqueue_job` from handlers; worker = **separate process** (`arq tasks.WorkerSettings`), never started inside web app.
- Redis keys used (don't collide): `arq:queue` (sorted set), `arq:job:{id}`, `arq:in-progress:{id}`, `arq:retry:{id}`, `arq:result:{id}`, `arq:abort` — flushing these resets queue.