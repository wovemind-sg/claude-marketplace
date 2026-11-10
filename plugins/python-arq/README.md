# python-arq

Claude Code skill: full reference for [arq](https://arq-docs.helpmanual.io/) (v0.28) — job queues, Python, asyncio + Redis.

## What it does

Gives Claude accurate, source-verified knowledge of full arq public API. Write, review, debug client code:

- Enqueueing jobs (`create_pool`, `ArqRedis.enqueue_job`, deferral, uniqueness via `_job_id`)
- Job handles (`Job.result/status/info/result_info/abort`) + exact error flows
- Workers (`WorkerSettings`, `arq` CLI, all `Worker` params + defaults)
- Retry semantics (`Retry`, `max_tries`, at-least-once execution, idempotency)
- Cron jobs, custom serialization, health checks, testing patterns, Redis key layout

## Usage

Triggers auto: working w/ arq code, or building background/task queues in async Python apps backed by Redis. No args, no env vars.

Structure:

- `skills/python-arq/SKILL.md` — core usage, error map, gotchas
- `skills/python-arq/references/api-reference.md` — exhaustive signatures, defaults, Redis keys, execution lifecycle

## Example

> "Add background job to my FastAPI app, retries failed webhook deliveries w/ backoff"

Claude uses skill → correct `WorkerSettings`, `enqueue_job` call w/ string function name, `Retry(defer=ctx['job_try'] * 5)` backoff. No API guessing.

## Install

```bash
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install python-arq@wovemind
```

## Requirements

None for the skill itself. The code it writes needs Python with `asyncio`, the `arq` package (version 0.28) and a Redis server for the queue.

## Environment variables

None. The skill reads no environment variables. The code it writes connects to Redis on `localhost:6379` unless you pass your own settings, for example `RedisSettings.from_dsn(...)` with a URL from your own configuration.