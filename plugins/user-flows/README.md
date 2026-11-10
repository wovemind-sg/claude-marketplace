# user-flows

Extract a deduplicated inventory of user flows from an application codebase and write it to `user-flows.md` at the project root. The inventory is formatted for a model to later consume — the intended pipeline is:

```
extract user flows → generate automated tests for the flows → run the tests after big changes
```

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install user-flows@wovemind
```

## Requirements

- Extracting, updating and adding flows needs nothing beyond Claude Code; the skills read the code and write `user-flows.md`.
- `test-user-flow` needs [`uv`](https://docs.astral.sh/uv/) and Python 3. On first run it adds `pytest-playwright` as a dev dependency and installs the Playwright browser; it uses `make` for the generated `make test-user-flows` target. The app must be startable locally, or reachable at a deployed URL.

## Environment variables and settings

None. The plugin has no environment variables and no plugin settings. The base URL the tests use is written to `pyproject.toml` (`--base-url` under `[tool.pytest.ini_options]`).

## Opinionated defaults

| Default | Change it with |
|---|---|
| Extraction is exhaustive (`high`): edge cases, error paths and permission-denied paths included | `low` or `medium` as the first argument |
| Tests are Python Playwright (`pytest-playwright`) run through `uv` | not configurable |
| Tests live in `tests/user_flows/` | an existing folder with `user-flow:` markers, or the project's Playwright test folder, is used instead |
| Tests are marked `user_flow` and left out of the normal `pytest` run | run them with `make test-user-flows` |
| Local mode (tests may seed Redis/Postgres directly) when the base URL is localhost; remote mode (UI and HTTP only) for a deployed URL | say `--mode local` or `--mode remote` to `test-user-flow` |

## Skills

### `/user-flows:extract-user-flows [low|medium|high] [area]`

Both arguments are optional, in any order:

- **Granularity** — how comprehensive the list is. `low` = critical happy paths only, `medium` = happy paths + important variations, `high` (default) = exhaustive, including edge cases, error paths, and permission-denied paths.
- **Area** — free-text filter; restricts extraction to matching features and replaces only that section of an existing `user-flows.md` (other sections and their IDs stay stable).

### `/user-flows:update-user-flows`

Updates an existing `user-flows.md` after code changes in the current session (from the conversation + git diff): adds flows for new features, revises changed ones (IDs kept), removes flows for deleted features (IDs never reused), and reports the removed IDs so downstream tests can be cleaned up. Untouched flows are left byte-for-byte identical. When anything changed, it then invokes `test-user-flow` to sync the test suite.

### `/user-flows:add-user-flow <description>`

Adds one specific new flow from a free-text description (e.g. "let users export their order history as CSV") — for a single flow the client asked for, rather than re-deriving many from a session's changes. Checks for an equivalent existing flow first and stops without changes if found; otherwise grounds the flow in the code, appends it with the next ID, and invokes `test-user-flow` to sync the test suite if one exists. Creates `user-flows.md` if it doesn't exist yet.

### `/user-flows:test-user-flow [area]`

Generates and maintains Python Playwright E2E tests (`pytest-playwright`, run via `uv run pytest`) from `user-flows.md` (stops if the file is missing — run extract first). Each generated test carries a marker comment (`# user-flow: UF-001 hash: <sha256 prefix>`); a bundled script diffs the flow hashes against the markers, so on re-runs the skill creates tests only for new flows, rewrites only tests whose flow changed, deletes tests whose flow was removed, and never touches unchanged or hand-written tests. Sets up `pytest-playwright` via uv (base URL in `pyproject.toml`, app-launch fixture in `conftest.py`) on first run. Tests are marked `user_flow` and excluded from the default pytest run; they run via a generated `make test-user-flows` target, and the skill documents all of this in the project's `CLAUDE.md`. Optional free-text area filter limits the sync to one area.

## Examples

```
/user-flows:extract-user-flows
/user-flows:extract-user-flows medium
/user-flows:extract-user-flows low checkout and payments
/user-flows:extract-user-flows login
/user-flows:test-user-flow
/user-flows:test-user-flow checkout
/user-flows:add-user-flow let users export their order history as CSV
```

## Output

`user-flows.md` at the project root: flows grouped by area, each with a stable ID (`UF-001`, …), actor, precondition, arrow-chain steps, an assertable expected outcome, and source pointers into the code. Extraction also adds a short section to the project's `CLAUDE.md` pointing future sessions at the file and the update/test skills.
