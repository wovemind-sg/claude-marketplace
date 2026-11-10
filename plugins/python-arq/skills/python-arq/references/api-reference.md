# arq v0.28 — full API reference

Checked against arq source (python-arq/arq, v0.28.0). Defaults shown real.

## Contents

1. [arq.connections.RedisSettings](#redissettings)
2. [arq.connections.create_pool](#create_pool)
3. [arq.connections.ArqRedis](#arqredis)
4. [arq.jobs.Job](#job)
5. [JobStatus / JobDef / JobResult](#jobstatus--jobdef--jobresult)
6. [arq.worker.func / Function](#func--function)
7. [arq.worker.Retry and other exceptions](#exceptions)
8. [arq.worker.Worker](#worker)
9. [Worker helpers & health checks](#worker-helpers)
10. [arq.cron.cron](#cron)
11. [CLI](#cli)
12. [Redis key layout & constants](#redis-key-layout)
13. [Typing protocols](#typing-protocols)
14. [Serialization internals](#serialization-internals)

---

## RedisSettings

`arq.connections.RedisSettings` — dataclass, plain config holder.

```python
RedisSettings(
    host: str | list[tuple[str, int]] = 'localhost',  # list of (host, port) when sentinel=True
    port: int = 6379,
    unix_socket_path: str | None = None,
    database: int = 0,
    username: str | None = None,
    password: str | None = None,
    ssl: bool = False,
    ssl_keyfile: str | None = None,
    ssl_certfile: str | None = None,
    ssl_cert_reqs: str = 'required',
    ssl_ca_certs: str | None = None,
    ssl_ca_data: str | None = None,
    ssl_check_hostname: bool = False,
    conn_timeout: int = 1,          # socket connect timeout, secs
    conn_retries: int = 5,          # create_pool retry attempts
    conn_retry_delay: int = 1,      # secs between retries
    max_connections: int | None = None,
    sentinel: bool = False,
    sentinel_master: str = 'mymaster',
    retry_on_timeout: bool = False,
    retry_on_error: list[type[Exception]] | None = None,
    retry: redis.asyncio.retry.Retry | None = None,   # redis-py Retry, NOT arq.worker.Retry
)
```

`RedisSettings.from_dsn(dsn: str) -> RedisSettings` — takes schemes `redis://`, `rediss://` (ssl=True), `unix://`. DB from path (`redis://h:6379/1`) or query (`?db=1`). Bad scheme → `RuntimeError('invalid DSN scheme')`. Note: from_dsn maps only host/port/ssl/user/password/db/socket-path — timeouts etc set after.

## create_pool

```python
async def create_pool(
    settings_: RedisSettings | None = None,   # None → RedisSettings() defaults
    *,
    retry: int = 0,                            # internal retry counter, leave 0
    job_serializer: Callable[[dict], bytes] | None = None,    # default pickle.dumps
    job_deserializer: Callable[[bytes], dict] | None = None,  # default pickle.loads
    default_queue_name: str = 'arq:queue',
    expires_extra_ms: int = 86_400_000,        # default job expiry margin, 1 day
) -> ArqRedis
```

- Retries connection up to `settings.conn_retries` times, `conn_retry_delay` secs apart, on `ConnectionError | OSError | RedisError | asyncio.TimeoutError`; then re-raises.
- `sentinel=True` w/ `host` as str → `RuntimeError` (needs list of `(host, port)` tuples).
- Confirms alive w/ `ping()` before return.

## ArqRedis

`class ArqRedis(redis.asyncio.Redis)` — full redis-py async client plus:

### enqueue_job

```python
async def enqueue_job(
    function: str,                 # registered function name (Function.name / __qualname__; cron names prefixed 'cron:')
    *args: Any,
    _job_id: str | None = None,    # default uuid4().hex
    _queue_name: str | None = None,  # None → pool's default_queue_name
    _defer_until: datetime | None = None,
    _defer_by: int | float | timedelta | None = None,  # seconds
    _expires: int | float | timedelta | None = None,   # seconds; None → defer + expires_extra_ms
    _job_try: int | None = None,
    **kwargs: Any,
) -> Job | None
```

Mechanics (transactional, WATCH on job key):
1. If `arq:job:{id}` OR `arq:result:{id}` exists → return `None` (dedup).
2. Score = `_defer_until` as unix-ms, or now + `_defer_by`, or now.
3. `PSETEX arq:job:{id}` w/ expiry `_expires` (or `score - now + expires_extra_ms`), payload = serialized `{t, f, a, k, et}`.
4. `ZADD queue {id: score}`.
5. Concurrent dupe enqueue (WatchError) → returns `None`.

Errors: both defer args → `RuntimeError`; unserializable args → `SerializationError`.

### Introspection

```python
async def all_job_results() -> list[JobResult]   # KEYS arq:result:* — O(N), dev/test only; sorted by enqueue_time
async def queued_jobs(*, queue_name: str | None = None) -> list[JobDef]
    # ZRANGE + fetch each job key; raises RuntimeError if a job key expired mid-scan
```

## Job

`arq.jobs.Job(job_id, redis, _queue_name='arq:queue', _deserializer=None)` — handle only, holds no state. Construct manually to re-attach to known job_id.

```python
await job.result(timeout: float | None = None, *, poll_delay: float = 0.5) -> Any
```
Polls `arq:result:{id}` + queue membership each `poll_delay`:
- result exists, success → return `JobResult.result`
- result exists, failure → re-raise stored exception (`Exception` or `CancelledError`); stored value not exception → raise `SerializationError(value)`
- no result AND job_id not in queue → `ResultNotFound` (msg hints: is keep_result configured?)
- `timeout` elapsed → `asyncio.TimeoutError`
(`pole_delay` param = deprecated alias.)

```python
await job.info() -> JobDef | None        # result_info() or decode arq:job:{id}; sets .score from queue
await job.result_info() -> JobResult | None  # decode arq:result:{id}; None if absent; never raises job's exc
await job.status() -> JobStatus
```
Status logic: result key exists → `complete`; in-progress key → `in_progress`; queue score > now → `deferred`; score ≤ now → `queued`; none → `not_found`.

```python
await job.abort(*, timeout: float | None = None, poll_delay: float = 0.5) -> bool
```
- Still deferred: re-scores to run now (cancellation processes fast).
- Adds id to `arq:abort` sorted set; worker (if `allow_abort_jobs=True`) cancels task, or fails job before start.
- Then waits on `result()`: `CancelledError` → `True`; `ResultNotFound` → `False` (unknown); normal result/other exc → `False` (finished anyway).
- Abort entries older than 60s (`abort_job_max_age`) purged — worker must see request within that window.

## JobStatus / JobDef / JobResult

```python
class JobStatus(str, Enum):
    deferred, queued, in_progress, complete, not_found

@dataclass
class JobDef:
    function: str
    args: tuple
    kwargs: dict
    job_try: int
    enqueue_time: datetime
    score: int | None
    job_id: str | None

@dataclass
class JobResult(JobDef):    # adds:
    success: bool
    result: Any             # return value or exception instance
    start_time: datetime
    finish_time: datetime
    queue_name: str
```

`ResultNotFound(RuntimeError)`, `SerializationError(RuntimeError)`, `DeserializationError(SerializationError)` live in `arq.jobs`.

## func / Function

```python
def func(
    coroutine: str | Function | WorkerCoroutine,  # import string allowed
    *,
    name: str | None = None,             # default coroutine.__qualname__
    keep_result: int | float | timedelta | None = None,  # None → worker default; 0 → don't store
    timeout: int | float | timedelta | None = None,      # None → worker job_timeout
    keep_result_forever: bool | None = None,             # wins over keep_result
    max_tries: int | None = None,        # None → worker max_tries; 1 → never retry
) -> Function
```
Non-coroutine target → `RuntimeError`. `Function` = dataclass `(name, coroutine, timeout_s, keep_result_s, keep_result_forever, max_tries)`.

## Exceptions

```python
class Retry(RuntimeError):            # arq.worker
    def __init__(self, defer: int | float | timedelta | None = None)
```
Raise inside job → worker re-queues (score bumped by `defer` from now), increments `jobs_retried`. Guarded by worker `retry_jobs=True` + `max_tries`.

- `JobExecutionFailed(RuntimeError)` — stored as result for: expired jobs (`'job expired'`), unknown function (`"function 'x' not found"`), max retries (`'max N retries exceeded'`). Equal comparison by args.
- `FailedJobs(count, job_results)` — raised by `run_check()`.
- `RetryJob(RuntimeError)` — internal; raising re-queues job w/o counting as failure (like CancelledError path).

## Worker

```python
Worker(
    functions: Sequence[Function | WorkerCoroutine] = (),
    *,
    queue_name: str | None = 'arq:queue',    # None allowed only with redis_pool (inherits its default)
    cron_jobs: Sequence[CronJob] | None = None,
    redis_settings: RedisSettings | None = None,   # ignored if redis_pool given
    redis_pool: ArqRedis | None = None,
    burst: bool = False,
    on_startup: async (ctx) | None = None,
    on_shutdown: async (ctx) | None = None,
    on_job_start: async (ctx) | None = None,   # ctx has job_id/job_try/enqueue_time/score
    on_job_end: async (ctx) | None = None,     # before result written
    after_job_end: async (ctx) | None = None,  # after result written
    handle_signals: bool = True,               # SIGINT/SIGTERM handlers; False inside other frameworks
    job_completion_wait: int = 0,   # >0: on signal stop picking jobs, wait this many secs for running jobs, then cancel
    max_jobs: int = 10,             # concurrent tasks
    job_timeout: SecondsTimedelta = 300,
    keep_result: SecondsTimedelta = 3600,
    keep_result_forever: bool = False,
    poll_delay: SecondsTimedelta = 0.5,
    queue_read_limit: int | None = None,   # default max(max_jobs * 5, 100)
    max_tries: int = 5,
    health_check_interval: SecondsTimedelta = 3600,
    health_check_key: str | None = None,   # default '{queue_name}:health-check'
    ctx: dict | None = None,               # merged into job ctx
    retry_jobs: bool = True,               # False → Retry/CancelledError fail instead of re-queue
    allow_abort_jobs: bool = False,
    max_burst_jobs: int = -1,              # burst mode cap; negative = unlimited
    job_serializer: Callable[[dict], bytes] | None = None,
    job_deserializer: Callable[[bytes], dict] | None = None,
    expires_extra_ms: int = 86_400_000,
    timezone: datetime.timezone | None = None,   # cron schedule tz; default system local
    log_results: bool = True,
)
```

Constructor raises: no functions and no cron_jobs → `RuntimeError`; cron_jobs not CronJob instances → `RuntimeError`; `queue_name=None` w/o redis_pool → `ValueError`.

Run methods:
- `run() -> None` — blocking; creates/uses event loop; closes pool on exit.
- `async_run() -> None` — awaitable, doesn't close connections (testing / embedding).
- `run_check(retry_jobs=None, max_burst_jobs=None) -> int` — runs `async_run()`, then raises `FailedJobs` if `jobs_failed > 0`, else returns `jobs_complete`.
- `close()` — waits for tasks, deletes health key, runs on_shutdown, closes pool.

Execution guarantees / lifecycle per job:
1. Poll: `ZRANGEBYSCORE queue -inf..now` (limit `queue_read_limit`).
2. Claim: transactional check + `PSETEX arq:in-progress:{id}` TTL = (max function timeout or job_timeout) + 10s. Another worker holding key → skip. Worker death → job re-runnable after TTL.
3. Run: `arq:retry:{id}` INCR = try counter (expires 88400s). try > max_tries → fail. `asyncio.wait_for(fn(ctx, *args, **kwargs), timeout)`.
4. Outcomes: success → result stored (if keep_result), job/retry keys deleted, ZREM from queue. `Retry` → ZINCRBY defer, keys kept. CancelledError from abort → failed+stored. CancelledError from shutdown / `RetryJob` → left in queue, re-run. Other exception → failed, exception stored as result.
5. Cron jobs keep in-progress key 60s after finish, stops dupe scheduling across workers.

Worker attrs useful in tests: `jobs_complete`, `jobs_failed`, `jobs_retried`, `tasks` (dict of running run_job tasks), `job_tasks` (actual job coroutine tasks), `pool`.

## Worker helpers

```python
arq.worker.create_worker(settings_cls, **kwargs) -> Worker  # settings_cls: class OR dict; kwargs override
arq.worker.run_worker(settings_cls, **kwargs) -> Worker     # create + blocking run
arq.worker.check_health(settings_cls) -> int                # 0 healthy, 1 not
arq.worker.async_check_health(redis_settings, health_check_key=None, queue_name=None) -> int
```
Settings class → kwargs by intersecting attribute names w/ `Worker.__init__` params — unknown attrs silently ignored (typos in WorkerSettings don't error!).

Health: worker PSETEXes `{queue}:health-check` every `health_check_interval` w/ `Mar-01 17:41:22 j_complete=0 j_failed=0 j_retried=0 j_ongoing=0 queued=0`.

## cron

```python
def cron(
    coroutine: str | WorkerCoroutine,     # import string allowed
    *,
    name: str | None = None,              # default 'cron:{__qualname__}'
    month: int | set[int] | None = None,        # 1-12
    day: int | set[int] | None = None,          # 1-31
    weekday: int | set[int] | str | None = None,  # 0-6 or 'mon','tues','wed','thurs','fri','sat','sun'
    hour: int | set[int] | None = None,         # 0-23
    minute: int | set[int] | None = None,       # 0-59
    second: int | set[int] | None = 0,          # NOTE: defaults to 0, not None
    microsecond: int = 123_456,           # off-peak within the second
    run_at_startup: bool = False,
    unique: bool = True,                  # dedupe across workers via job_id '{name}:{scheduled_unix_ms}'
    job_id: str | None = None,            # fixed id spanning schedules
    timeout: SecondsTimedelta | None = None,
    keep_result: float | None = 0,        # cron default: results NOT kept
    keep_result_forever: bool | None = False,
    max_tries: int | None = 1,            # cron default: no retries
) -> CronJob
```

Scheduling: each heartbeat (every `poll_delay`, cron window clamped ≥0.5s) worker enqueues cron jobs due within next ~2 windows, `_defer_until` exact time. `None` field = wildcard. Registered under name `cron:{qualname}` — enqueue-able manually by that string too. `arq.cron.next_cron(previous_dt, *, month..microsecond)` exposed for computing schedules.

## CLI

```
arq [OPTIONS] WORKER_SETTINGS        # import path, e.g. app.tasks.WorkerSettings
  --burst / --no-burst    exit when queue empty (overrides settings)
  --check                 health check only; exit 0/1
  --watch PATH            reload on changes (requires watchfiles)
  -v, --verbose           debug logging
  --custom-log-dict PATH  import path to logging dictConfig dict
  -V, --version
```
Adds CWD to `sys.path`. Logging: arq configures `arq.*` loggers via dictConfig; in embedded/async_run usage configure logging yourself (`arq.logs.default_log_config(verbose)`).

## Redis key layout

| Key | Type | Purpose |
|---|---|---|
| `arq:queue` (or custom queue_name) | sorted set | job_id → run-at unix-ms score |
| `arq:job:{job_id}` | string | serialized job payload, PSETEX expires |
| `arq:in-progress:{job_id}` | string | claim marker, TTL = max timeout + 10s |
| `arq:retry:{job_id}` | string | try counter, TTL 88400s |
| `arq:result:{job_id}` | string | serialized result, TTL = keep_result (no TTL if forever) |
| `arq:abort` | sorted set | abort requests, entries purged after 60s |
| `{queue_name}:health-check` | string | worker health line |

Constants in `arq.constants`. Timezone for decoding timestamps: env `ARQ_TIMEZONE` / `arq_timezone` / `TIMEZONE` / `timezone`.

## Typing protocols

`arq.typing`: `SecondsTimedelta = int | float | timedelta`; `WorkerCoroutine` = `async (ctx, *args, **kwargs) -> Any`; `StartupShutdown` = `async (ctx) -> Any`; `WorkerSettingsType` = class or dict.

## Serialization internals

Payload dicts (matters when writing custom serializers — receive these dicts, not raw args):
- job: `{'t': job_try, 'f': function_name, 'a': args, 'k': kwargs, 'et': enqueue_time_ms}`
- result: adds `{'s': success, 'r': result, 'st': start_ms, 'ft': finish_ms, 'q': queue_name, 'id': job_id}`

Custom serializer must handle exception instances in `'r'` (failures store exception object). Result serialization fails → arq retries w/ `r='unable to serialize result', s=False`; `job.result()` then raises `SerializationError('unable to serialize result')`.