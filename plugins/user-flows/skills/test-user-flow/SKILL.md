---
name: test-user-flow
description: Generate and maintain Python Playwright (pytest-playwright, run via uv) end-to-end tests from the user-flows.md inventory at the project root — create tests for new flows, update tests whose flow changed, and delete tests whose flow was removed. Supports local mode (against a dev server, with Redis/Postgres available for setup and assertions) and remote mode (against a real deployment, restricted to Playwright and HTTP). Use whenever the user asks to generate, write, sync, or update tests for their user flows, E2E tests, or flow coverage — including after user-flows.md changes ("sync the flow tests", "cover the new flows") or when they want flow tests run against a deployed/staging/production environment. Requires a user-flows.md produced by extract-user-flows.
argument-hint: "[--mode local|remote] [optional area filter, e.g. 'checkout']"
---

Keep the project's Playwright E2E suite (Python, `pytest-playwright`, run via `uv`) in sync with `user-flows.md` at the project root: one test per flow, no test without a flow, no flow silently uncovered.

If `user-flows.md` does not exist, **stop** and tell the user to run `/user-flows:extract-user-flows` first — do not invent flows from the codebase yourself; the inventory is the contract this skill implements.

Read the sibling skill at `${CLAUDE_PLUGIN_ROOT}/skills/extract-user-flows/SKILL.md` for the flow entry format (`### UF-NNN`, Actor/Precondition/Steps/Expected/Source). Each field maps directly onto a test: Precondition → setup, Steps → actions, Expected → assertions, Source → where to look when a selector or route is unclear.

## Local mode vs remote mode

The suite must support two modes, since where it points changes what's reachable for setup and assertions:

- **Local mode** — runs against a dev server the suite starts (or an already-running one). It's your own environment, so tests may reach into Redis and Postgres directly (fixtures, seed scripts, DB-level assertions) whenever that's a better fit than driving the UI — e.g. seeding a precondition row, or asserting a record landed correctly without relying on it also being rendered.
- **Remote mode** — runs against a real deployment of the app. There's no direct line to its Redis/Postgres, so tests may only use Playwright (UI actions and assertions) and plain HTTP calls to the app's own endpoints (its API, webhooks it exposes, etc.) — never a direct database or cache connection, even if credentials happen to be available; a real deployment's data isn't yours to touch out-of-band.

If the user names a mode (`--mode local`/`--mode remote`, or says things like "test against the deployed app" / "test against my dev server"), use it. Otherwise infer from context — an existing `<tests-dir>/conftest.py` or `pyproject.toml` `--base-url` pointing at a deployed URL means remote; a localhost/127.0.0.1 base URL or no config yet means local. If it's genuinely ambiguous (first run, no clues), ask.

Record the resolved mode for the run in the report, and keep test file layout mode-agnostic — the same `test_<area_slug>.py` files serve both; what changes is which fixtures/assertions a test is allowed to use, and the `--base-url`/app-lifecycle config below.

## How sync works

Every generated test carries a marker comment on the line above it:

```
# user-flow: UF-001 hash: a1b2c3d4e5f6
```

The hash is a truncated sha256 of the flow's normalized entry in `user-flows.md`. This makes change detection cheap and exact: a flow whose hash matches its marker needs nothing — you never re-read or re-judge it. Never compute or edit these hashes by hand; always take them from the script below, otherwise the stored hash drifts from what the script computes and every future sync misclassifies the flow as updated.

Run the diff first, before reading any test file:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/test-user-flow/scripts/flow_sync.py" user-flows.md <tests-dir>
```

It prints JSON with four buckets — `new` (flow has no test), `updated` (marker hash ≠ flow hash; includes the current flow block and the test's file/line), `deleted` (marker's flow no longer exists), `unchanged` — plus `conflicts` (e.g. one flow ID marked in two files). Resolve conflicts before anything else; a conflicted ID must not be auto-modified.

If the user gave an area filter, act only on flows/tests under that area heading and say so in the report.

`<tests-dir>` is where the flow tests live: find an existing directory containing `user-flow:` markers first (search the repo), then fall back to the project's Playwright test dir, then default to `tests/user_flows/`.

## First run: Playwright setup

If the project has no Python Playwright (`pytest-playwright` not among the dependencies):

1. `uv add --dev pytest-playwright` (if the project isn't a uv project yet, `uv init` first — but check for another Python setup to respect before assuming), then `uv run playwright install chromium`.
2. Configure the base URL so tests don't hardcode it: add `--base-url=<app url>` to `addopts` under `[tool.pytest.ini_options]` in `pyproject.toml`, and use relative paths in `page.goto()`. In local mode, work out the dev server's URL and start command from the repo (package/framework scripts, Dockerfile, framework defaults). In remote mode, use the deployment's real URL — ask the user for it if it isn't already in the repo's config/env.
3. App lifecycle differs by mode:
   - **Local**: tests need the app running. If the repo has a clean start command, add a session-scoped autouse fixture in `<tests-dir>/conftest.py` that starts the app when the base URL isn't already responding and tears it down after; if starting the app is genuinely not derivable, skip the fixture and state in the report that the app must be running before the tests.
   - **Remote**: never start or stop the app — it's a real deployment, not yours to manage. Skip the autouse fixture entirely; tests just assume the base URL is already serving.

If Python Playwright is already configured, use the existing config, browser set, and conventions — don't add a parallel setup.

Regardless of whether setup was needed, ensure these three project pieces exist (idempotent — check first, add only what's missing):

1. **Excluded-by-default marker.** User-flow tests are slow E2E tests that need a browser and a running app — they must not break or drag the project's normal test run. Register a `user_flow` pytest marker in `pyproject.toml` (`markers = ["user_flow: E2E user-flow tests, excluded from the default run"]` under `[tool.pytest.ini_options]`) and add `-m "not user_flow"` to `addopts`, so a plain `pytest` deselects them; an explicit `-m user_flow` on the command line overrides it. Every area file gets `pytestmark = pytest.mark.user_flow` at module level so new tests are covered automatically. If the project excludes by a different existing mechanism (its own marker scheme, `testpaths` that already omit the dir), follow that convention instead of stacking a second one.
2. **Makefile target.** Add to the project's `Makefile` (create it if there is none, respect its existing style and `.PHONY` conventions if there is):

   ```makefile
   .PHONY: test-user-flows
   test-user-flows:
   	uv run pytest -m user_flow <tests-dir>
   ```

3. **CLAUDE.md note.** Add (or refresh) a short section in the project's `CLAUDE.md` — create the file with just this section if it doesn't exist — saying: user-flow E2E tests live in `<tests-dir>`, are generated from `user-flows.md` by `/user-flows:test-user-flow`, are excluded from the default pytest run by the `user_flow` marker, and run via `make test-user-flows`; the `# user-flow: UF-NNN hash: ...` comments are sync markers that must not be edited by hand — resync via the skill instead.

## Writing a test (new and updated flows)

Layout: one file per area, `<tests-dir>/test_<area_slug>.py`, one test function per flow inside it. Name the function after the flow ID and name — `def test_uf_001_login_with_valid_credentials(page: Page):` — and put the exact flow title in its docstring (`"""UF-001: Login with valid credentials"""`) so failures trace straight back to the inventory.

Directly above each test function (above its decorators, if any), place its marker comment with the `hash` value from the script output.

Test quality rules — these decide whether the suite survives contact with reality:

- Assert exactly what **Expected** says is observable (URL, visible text, created record via UI evidence) — a test that asserts less than the flow promises is a false safety net.
- Use Playwright's user-facing locators (`page.get_by_role`, `page.get_by_label`, `page.get_by_text`) and web-first assertions (`expect(...).to_be_visible()` from `playwright.sync_api`); no `wait_for_timeout`, no CSS/XPath chains unless the DOM offers nothing better. Read the actual templates/components from the flow's **Source** to get real names and labels — never guess selectors.
- Implement **Precondition** as real setup: in local mode, a pytest fixture, a direct Redis/Postgres seed, an API call, or UI steps — pick whichever is most reliable. In remote mode, only UI steps or HTTP calls to the app's own endpoints are available — there's no DB to seed directly. When a precondition can't be satisfied from the test (needs prod data, a paid account, a third-party callback, or — in remote mode — DB-level state with no endpoint to reach it), still write the test body but mark it `@pytest.mark.skip(reason="...")` with a one-line reason — a visible gap beats a fake green.
- Assertions follow the same split: local mode may assert directly against Redis/Postgres when that's the more precise check (e.g. a row's exact field value); remote mode asserts only through the UI (Playwright) or HTTP responses from the app's own API — never a direct datastore connection.
- Extract setup shared by several flows in an area (e.g. "logged in as admin") into a pytest fixture in `conftest.py` (or the area file, if only that area uses it), not copy-paste per test.

For **updated** flows, edit the existing test in place: reread the current flow block (the script gives it to you), adjust setup/actions/assertions to match, keep any manual improvements in the test that don't contradict the new flow (better selectors, extra assertions), and replace the marker's hash with the new one. Don't regenerate the whole file — untouched tests stay byte-for-byte identical.

## Deleting tests (removed flows)

For each `deleted` entry, remove that test block (marker comment through the end of the function body) from its file. Delete the area file itself only when no tests remain in it. Never touch a test that has no `user-flow:` marker — hand-written tests in the same directory are not yours to manage. List every deleted test ID and file in the report; if a deletion looks suspicious (the flow's feature clearly still exists in the code), flag it instead of deleting — the likelier fault is a stale user-flows.md, and the fix is `/user-flows:update-user-flows`, not losing coverage.

## Verify

1. Rerun `flow_sync.py` — it must report every flow as `unchanged` (empty `new`/`updated`/`deleted`, no conflicts). This proves the markers you wrote are correct.
2. `uv run pytest --collect-only -m user_flow <tests-dir>` — catches syntax/collection errors in every file (the explicit `-m user_flow` is required: the default `addopts` deselects these tests).
3. Run the new and updated tests (`uv run pytest -m user_flow <changed files>`). If the app can't be started in this environment, say so explicitly rather than skipping silently. Fix failures caused by the test (wrong selector, missing wait); a test that fails because the app genuinely doesn't do what the flow says is a finding — report it, don't bend the test until it passes.
4. Confirm a plain `uv run pytest --collect-only` still deselects the user-flow tests and collects the rest of the suite — proof the default test run is unaffected.

## Report

Summarize: mode used (local/remote, and how it was resolved), tests created (IDs), updated (IDs + what changed), deleted (IDs + files), skipped (IDs + reason), unchanged count, project files touched outside `<tests-dir>` (`pyproject.toml`, `Makefile`, `CLAUDE.md`), and the verification outcome (collected / ran / couldn't run and why). Remind the user the suite runs via `make test-user-flows`. Do not paste whole test files into the conversation.
