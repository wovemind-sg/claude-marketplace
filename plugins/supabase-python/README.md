# supabase-python

Teaches Claude a FastAPI project layout that uses [Supabase](https://supabase.com/) for authentication, storage and realtime, and SQLModel or SQLAlchemy for database queries. The rule it follows is simple: database reads and writes go through SQLModel or SQLAlchemy with an async driver, and the Supabase client is used only for auth, storage and realtime.

The skill covers the project structure, settings loaded from `.env`, the async database session, SQLModel models, the Supabase client, an auth dependency that validates the user's token, example API routes, Alembic migrations, file storage, realtime subscriptions, tests and running the app.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install supabase-python@wovemind
```

## Requirements

None for the skill itself. The code it writes needs:

- Python with `fastapi`, `uvicorn`, `supabase`, `python-dotenv`, `sqlmodel`, `asyncpg`, `alembic` and `pydantic-settings`.
- A Supabase project, either hosted or running locally with the Supabase CLI (`supabase start`).

## Environment variables

The skill reads none. The app it writes reads these from the environment or a `.env` file:

| Variable | Meaning |
|---|---|
| `SUPABASE_URL` | URL of your Supabase project (for a local project, `http://localhost:54321`). |
| `SUPABASE_ANON_KEY` | The project's public anon key. |
| `SUPABASE_SERVICE_ROLE_KEY` | The project's service role key. It bypasses row-level security, so keep it on the server and never commit it. |
| `DATABASE_URL` | Postgres connection string for SQLAlchemy, using the async driver, for example `postgresql+asyncpg://postgres:postgres@localhost:54322/postgres`. |

For a local project, `supabase start` prints both keys.

## Usage

The skill triggers when you work on a FastAPI and Supabase project or ask about SQLModel or SQLAlchemy with Supabase. You can also invoke it directly with `/supabase-python:supabase-python`.

## Example

Ask Claude:

> "Add a posts API to my FastAPI app where only signed-in users can create posts."

Claude adds a `Post` SQLModel model and an Alembic migration for it, then a router whose create endpoint depends on the auth dependency. That dependency reads the bearer token from the request, asks Supabase Auth who the user is, and rejects the request if the token is missing or invalid. The endpoint then saves the post through the async SQLModel session, with the user's id as the author, rather than through the Supabase client.
