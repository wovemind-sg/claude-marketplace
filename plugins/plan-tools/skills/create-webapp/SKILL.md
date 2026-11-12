---
name: create-webapp
description: End-to-end bootstrap of a brand-new FastAPI + Jinja2 + HTMX + Alpine.js web app — gather features, design reference and whether to ship Capacitor mobile apps, pick only the needed parts of the fastapi-template stack, collect .env values, clear blockers, plan with a subagent, split the plan into .planning/ sessions, then hand off to implementing subagents. Use whenever the user wants to start, bootstrap, kick off, or build a new web app from scratch and wants it planned and implemented end to end, not just scaffolded — even if they only say "new app", "build me an app that…", or "start a project for…".
argument-hint: "[--host railway|generic] [--ai-model <openrouter model id>] [optional one-line app idea]"
---

You are orchestrating the birth of a new web app: from a feature list to a running, committed implementation. You do not write app code yourself — you gather what the subagents need, remove everything that would stall them, then delegate planning and implementation.

Everything downstream is only as good as the inputs collected here. A subagent with a vague feature list, a missing API key, or an unreachable database will either stop and wait or invent something. Spend the effort up front.

## 1. Gather inputs

Two optional flags in `$ARGUMENTS`; remove them before using the rest as the seed:
- `--host railway|generic` (default `railway`). With `generic`, skip every Railway provisioning and deploy step below (the `use-railway` provisioning of the database and the Railway deploy target in section 4, the "Railway via `Procfile`" deploy step in section 5) and tell the user they deploy to their own host; if mobile = yes, ask them for the public HTTPS URL of that host instead.
- `--ai-model <openrouter model id>` (default `openai/gpt-4o-mini`).

Pass both values to `fastapi-template:fastapi-template` wherever this skill or its subagents use it (section 5 step 1, section 7): the template is applied as if run with `--host <host> --ai-model <model>`, and the Plan prompt carries both values verbatim.

Use `$ARGUMENTS` as the seed if given. Ask for everything below in as few rounds as possible (AskUserQuestion, grouping related questions). Skip anything the user already stated.

1. **App name** (kebab-case). Default: current directory name. Confirm the current directory is the intended project root — if it is not empty, stop and ask.
2. **Features** — a list of what the app must do. Push for concrete user-facing behaviour ("users log in with Google, create lists, share a list by link"), not categories ("auth", "CRUD"). Ask about anything ambiguous now; the planner cannot ask the user.
3. **Design reference** (optional) — a URL, a screenshot/image path, an existing app to imitate, or a few words of direction ("minimal, dark, dense tables"). If none, say the planner will pick a sensible default.
4. **Mobile apps?** — should this also ship as iOS/Android apps? Yes/No. If yes, which platforms. Yes means a Capacitor WebView shell is planned and built alongside the web app (see section 2).
5. **Planning model** — default `sonnet`.
6. **Implementing model** — default `sonnet`. Options: `sonnet`, `opus`, `haiku`, `fable`.

## 2. Decide the stack slice

The `fastapi-template:fastapi-template` skill supports more than most apps need. Scaffolding unused parts adds env vars the user must fill, services they must run, and dead code the implementer will trip over. Decide each part from the feature list, then confirm the table with the user in one message:

| Part | Include when |
|---|---|
| PostgreSQL + SQLModel + Alembic | Anything is persisted (almost always yes) |
| Redis (`fastapi-cache2`) | AI is included, or caching/rate-limiting/background jobs are needed |
| OpenRouter AI | Any feature generates, summarises, classifies or converses over text |
| Google login | The feature list needs accounts or per-user data (Authlib OAuth; login state and the OAuth `state`/PKCE values live in signed cookies, see below) |
| Background jobs (`arq`) | Long-running or scheduled work; implies Redis |

**Auth state is always HMAC-signed cookies, never Starlette `SessionMiddleware`.** The template ships `get_cookie`/`set_cookie` in `app/utils.py`, signed with `SESSION_SECRET`, and `require_auth`/`is_authenticated` read the `user_id` cookie through them — that is the only session mechanism. Do not add `SessionMiddleware` or `request.session`, and do not let Authlib keep its OAuth `state`/PKCE in a server session: store them in their own signed cookie (this is also what makes Google's cross-device 2-Step-Verification flow work inside a Capacitor WebView). Set cookies from the route's returned response or from middleware, never via a dependency-injected `Response` — FastAPI silently drops those when the route returns a `TemplateResponse`.

**Client side is fixed**: Jinja2 templates, HTMX for anything the server owns, Alpine.js for ephemeral UI state, `hx-boost="true"` on `<body>`. No SPA, no JSON API for the browser, no custom JS where an HTMX attribute or Alpine directive does the job. The `htmx-vs-alpine:htmx-vs-alpine` skill is the arbiter for each interaction — the planner and implementers must apply it. The plan must also require visible user feedback (UI left to the app) for failed htmx requests, handled app-wide via `htmx:responseError`, `htmx:sendError` and `htmx:timeout`; htmx 2 does not swap 4xx/5xx responses, so otherwise a failed boosted click looks like nothing happened.

**If mobile = yes**, the mobile apps are part of the plan, not a later step. The shape is a **Capacitor shell whose WebView loads the deployed server** (`server.url` in `capacitor.config.ts` pointing at the production URL, `allowNavigation` for the app's own host and `accounts.google.com` if Google login is included) — the FastAPI app stays the single source of UI, no bundled web build to keep in sync. The `capacitor-core:capacitor-best-practices` and `capacitor-core:capacitor-plugins` skills are the reference for project setup, plugin use and native gotchas; the planner and implementers must load them for the Capacitor sessions if the `capacitor-core` plugin is installed; otherwise they skip them and say so in the report.

Because the web app is what the WebView shows, it must be Capacitor-ready from session 1 — retrofitting is painful:
- mobile-first responsive layout, safe-area CSS (`env(safe-area-inset-*)`)
- every text input, textarea and select at `font-size: 16px` minimum (iOS auto-zoom)
- **IMPORTANT: `hx-boost="true"` on `<body>` in `base.html`, on every page, no exceptions.** Without it every link and form does a full-page navigation, and in a Capacitor WebView that means a white blink on every click — the app feels like a website in a box. Boosted navigation swaps the body in place and the blink disappears. No plain full-page `<a href>` as the primary nav path, no `window.location` / JS redirects where a boosted link or form works, and server redirects (303 after POST) are fine only because the boosted form follows them via HTMX.
- Google login goes through a native hop (`ASWebAuthenticationSession` / Custom Tabs) inside the app, gated on `Capacitor.isNativePlatform()` — the plain browser OAuth stays for the web; both flows end by setting the same signed `user_id` cookie
- native features the feature list implies (camera, share, push, haptics) go through Capacitor plugins with denied-permission handling, not `getUserMedia`-style web APIs

## 3. Collect `.env` values and write the file

Derive the required variables from the stack slice — only those, nothing speculative:

| Variable | When | How to get the value |
|---|---|---|
| `DEV_MODE` | always | set `ON` |
| `SESSION_SECRET` | always | generate: `openssl rand -hex 32` — don't ask the user |
| `ENGINE_URL` | Postgres | ask — `postgresql://user:pass@host:5432/db` (local or Railway) |
| `REDIS_CONNECTION_STRING` | Redis | ask — `redis://localhost:6379` or hosted URL |
| `OPENROUTER_API_KEY` | AI | ask |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google login | ask; needs an OAuth client in Google Cloud Console with `http://localhost:8000/auth/callback` as an authorised redirect URI |

Ask for the values in one message, listing each variable with a one-line note on where it comes from. Then:

1. `git init` if the directory is not already a repository.
2. Write `.env` with the collected values. Never echo secret values back into the conversation after this point.
3. Ensure `.gitignore` exists and contains `.env` (and `.prod.env`); create or append as needed. Verify with `git check-ignore .env` — this is the one file that must never be committed.
4. Write `.env.example` with the same keys and placeholder values, so the implementer knows the contract.

## 4. Clear blockers

The implementing subagents run unattended. Anything they cannot do themselves must be done now. Check, don't assume — actually test each one and report pass/fail in a short checklist:

- **Postgres reachable** — `uv run --with psycopg2-binary python -c "import psycopg2,os; from dotenv import load_dotenv; load_dotenv(); psycopg2.connect(os.environ['ENGINE_URL']).close(); print('ok')"` (or `psql "$ENGINE_URL" -c 'select 1'`). If the DB doesn't exist yet, create it or have the user provision it (Railway: `use-railway` skill, if the `railway` plugin is installed; otherwise skip it and say so in the report).
- **Redis reachable** — `redis-cli -u "$REDIS_CONNECTION_STRING" ping` or the python equivalent.
- **OpenRouter key valid** — `curl -s -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/auth/key` returns 200.
- **Google OAuth client** — redirect URI registered; the user confirms, you cannot test this.
- **Toolchain** — `uv --version` works; Python 3.11 available (`uv python list`).
- **Design reference readable** — image path exists / URL fetches.
- **Mobile toolchain** (mobile = yes) — `node --version`, `npm --version`; Xcode + CocoaPods (`xcodebuild -version`, `pod --version`) for iOS; Android Studio / SDK (`ANDROID_HOME` set, `adb version`) for Android. Ask which platforms the user wants and only check those.
- **Deploy target** (mobile = yes) — the WebView needs a public HTTPS URL. Confirm a Railway project (or other host) exists or can be created (`use-railway` skill, if the `railway` plugin is installed; otherwise skip it and say so in the report), and capture the URL for `capacitor.config.ts`.
- **Anything feature-specific** — third-party APIs, webhooks, domains, paid accounts the features imply. Read the feature list once more with this lens.

Present failures as a numbered list, one line each, then wait for the user to fix them. Re-test after they say done. Do not move on with a known-broken dependency — the planner will plan around it and the implementer will hit it in session 1.

## 5. Plan

Spawn one subagent with `subagent_type: Plan` and `model:` the planning model. The Plan agent is read-only, which is what you want here. Its prompt must carry, verbatim, everything gathered above: app name, feature list, design reference, mobile flag, the stack-slice table, the exact env var names present in `.env`, and the blocker results. Then instruct it to:

1. Load the `fastapi-template:fastapi-template` skill (Skill tool) and read its three reference files for the exact file templates and critical patterns — including the signed-cookie helpers in `app/utils.py`, which are the only auth/session mechanism allowed (no `SessionMiddleware`). Do not run its interactive interview — the answers are already in the prompt. Only the parts in the stack slice get scaffolded; the plan must say explicitly which template files/blocks to drop (e.g. "no `app/ai.py`, remove Redis from lifespan").
2. Load the `htmx-vs-alpine:htmx-vs-alpine` skill and, for every interactive element implied by the features, decide HTMX vs Alpine and record the decision in the plan.
   Always, mobile or not, put the failed-htmx-request feedback rule from section 2 into the `.planning/CLAUDE.md` conventions and into the session that builds `base.html` and `app.js`: `htmx:responseError`, `htmx:sendError` and `htmx:timeout` each show visible user feedback app-wide (the UI is the app's choice, never console-only), the listeners are registered once behind a guard flag because `app.js` re-runs on every boosted body swap, and `htmx.config.timeout` is set so `htmx:timeout` can fire.
3. If a design reference was given, look at it (Read for images, WebFetch for URLs) and write a short design brief: palette, typography, spacing, layout skeleton, component look. If none, choose a restrained default and write it down anyway — every session must render the same app.
4. If mobile = yes, load `capacitor-core:capacitor-best-practices` and `capacitor-core:capacitor-plugins` (if the `capacitor-core` plugin is installed; otherwise skip loading them and say so in the report), bake the Capacitor-ready constraints from section 2 into the conventions (call out `hx-boost="true"` on `<body>` explicitly in `.planning/CLAUDE.md` — it is the single most common regression and the implementer of a later session will not know why it matters unless told) and into every task that touches templates/CSS, and add the Capacitor work as its own slice(s) at the end: `npm init` + `@capacitor/core|cli|ios|android` in a `mobile/` directory, `capacitor.config.ts` with `server.url` = the deployed URL (read from an env var or a config constant — never a localhost URL committed for production), `allowNavigation`, iOS/Android platform add, plugin wiring for any native feature, and the native Google-login hop if login is included. This requires the server to be deployed and reachable over HTTPS first, so the plan must include a deploy step (Railway via `Procfile`) before the Capacitor slice.
5. Produce a complete implementation plan: scaffolding first (a runnable `make dev` with the home page is the first milestone), then features as vertical slices, each ending in a working committable state, with Alembic migrations, verification steps, and the CLAUDE.md the project root should end up with. Return the plan as markdown.

Follow `/plan-tools:plan-helper` while planning. The Plan agent cannot ask the user anything itself, so tell it: when it has open decisions, end its run with those questions as its final report (plain English, 2–4 options each, recommendation first) instead of guessing. Ask the user with AskUserQuestion in plain English, then send the answers to that same Plan subagent with SendMessage so it continues with its context intact; repeat until it returns the finished plan.

Save the returned plan to `.planning/SPEC.md` (create `.planning/`). Show the user a one-screen summary and get a go-ahead before splitting — a wrong plan multiplied across sessions is expensive to unwind.

## 6. Split

Invoke `/plan-tools:split-plan` pointing at `.planning/SPEC.md`, with output directly under `.planning/` (its default) — not a subdirectory. Two outcomes:

- **Split** — `.planning/progress.md`, `.planning/CLAUDE.md`, `.planning/sessions/session-NN.md` now exist.
- **Not split** — split-plan judged the whole plan fits one session. `.planning/SPEC.md` stays the single source.

## 7. Implement

First, ask the user one question: **approve committing after every session (or at the end, if not split) without further confirmation?** The implementers commit as they go; without this approval they would stop after every session. Do not start until answered.

Then:

- **If split** — spawn one subagent (`subagent_type: general-purpose`, `model:` the implementing model) whose prompt is: invoke `/plan-tools:plan-split-implment` from this directory, with commit-per-session pre-approved by the user, and report back the final progress state and any session that stopped. That skill handles branching, per-session subagents, CLAUDE.md polish and plan archiving.
- **If not split** — spawn one subagent (`subagent_type: general-purpose`, `model:` the implementing model) instructed to: read `.planning/SPEC.md` in full; load `fastapi-template:fastapi-template` and `htmx-vs-alpine:htmx-vs-alpine` for reference; implement the plan exactly, scaffolding only the stack slice; verify (`make dev` boots, migrations apply, each feature works); write the project root CLAUDE.md; commit (pre-approved) with a semantic message; report back what was built and what, if anything, was left undone. If it ends with a question for the user instead of finishing, ask the user with AskUserQuestion in plain English, then send the answer to that same subagent with SendMessage so it continues.

Relay the implementer's report to the user as-is. Then list the obvious next steps only if they exist: unresolved blockers, deferred items, and — if mobile = yes — store submission (`capacitor-deployment:capacitor-app-store`, if the `capacitor-deployment` plugin is installed; otherwise say it is not installed), which is out of scope here.
