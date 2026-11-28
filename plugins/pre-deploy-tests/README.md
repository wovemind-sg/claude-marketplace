# pre-deploy-tests

Tests an app before it is deployed. The plan skill writes a test plan for the app's logic and its UI on every platform, screen size, orientation and browser it supports, and splits it into test sessions, each with the model that suits it. The run skill executes the sessions, records every bug without fixing it, and publishes a bug review page. The fix skill fixes the bugs you marked Fix on that page, one pull request per bug.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install pre-deploy-tests@wovemind
```

## Commands

| Command | What it does |
|---|---|
| `/pre-deploy-tests:plan [--full]` | Detects the app type (web, Capacitor, native iOS / Android), confirms it with you along with device sizes, orientations, browsers, the test target and the highest model, then writes `.pre-deploy-tests/SPEC.md` and splits it into test sessions with `/plan-tools:split-plan`, each with a model from `/model-picker:pick-model`. Uses `user-flows.md` when present. A later run plans only what changed since the last plan; `--full` plans everything again. Commits only `.pre-deploy-tests/record.json` (after asking) and publishes a `pre-deploy-tests` commit status. |
| `/pre-deploy-tests:run` | Runs the sessions in order, one test agent per platform copy (Chromium, WebKit, Firefox, iOS Simulator, Android emulator) side by side, each on its own worktree, app and database; on an integration environment, one at a time. Checks tools and credentials first and suggests a lane count from the machine's cores and free RAM. Agents change no code: each bug is reproduced 3 times and recorded with steps, a screenshot or recording, the reproduction script and a fix prompt in `.pre-deploy-tests/bugs/`. Publishes a private bug review page with a ready / not-ready verdict and a Fix / Skip choice per bug. Resumes an interrupted run. |
| `/pre-deploy-tests:fix [artifact url]` | Fixes the bugs marked Fix on the bug review page, one at a time, by severity: each in its own subagent with a model from `/model-picker:pick-model`, which reproduces the bug, fixes it, re-runs the reproduction and takes an "after" capture for UI bugs, then finalizes with `/plan-tools:finalize-pr`. Each PR is squash auto-merged and watched with `/plan-tools:monitor-pr`; the next bug starts after the merge. Asks about undecided bugs and the highest model first. Updates each card with its status, PR link and "after" capture. A bug that does not reproduce, or a PR that gets stuck, is marked on its card and the run goes on. |

## Example

```
/pre-deploy-tests:plan
```

1. Answer the questions: app type, device sizes, orientations, Firefox, the test target (default branch locally, or an integration environment URL), the highest model.
2. Read the coverage summary (areas, platforms, sizes, sessions with their models) and say go.
3. The sessions are in `.pre-deploy-tests/sessions/` and the record is committed.

```
/pre-deploy-tests:run
```

4. Fix what the preflight lists, or continue without it; accept the suggested lane count.
5. Open the bug review page, read the verdict and mark each bug Fix or Skip.

```
/pre-deploy-tests:fix
```

6. Say whether to fix the undecided bugs too, and pick the highest model.
7. Each bug marked Fix becomes a merged PR; its card shows "Fixed" with the PR link and the "after" capture, or "Could not reproduce" / "Needs attention" with the reason.

## Requirements

- Plugins `plan-tools`, `model-picker` and `user-flows` (installed with this plugin).
- `git`, and `gh` signed in for the commit status (optional: a failed status is reported, not fatal). The fix skill needs `gh` signed in, and auto-merge allowed in the repository.
- For the run, per platform copy: `playwright-cli` (Chromium, WebKit, Firefox); macOS with Xcode (iOS Simulator); the Android SDK with `adb` and an emulator (Android); `ffmpeg` optional, to convert iOS recordings. The run lists what is missing before it starts.

## Environment variables and settings

None. Test credentials are named by environment variables in `.pre-deploy-tests/record.json`; secrets are never stored.

## Opinionated defaults

| Default | Change it with |
|---|---|
| Chromium and WebKit are tested; Firefox only when you say you support it. | the Firefox question |
| Sizes: desktop 1440x900, tablet 820x1180, phone 390x844, small phone 360x640, in every orientation you choose (desktop has no landscape variant). | the device-class and orientation questions |
| The highest model a session gets is Opus; a pick above it gets Opus with one more effort level. | the highest-model question, asked every run |
| Only `.pre-deploy-tests/record.json` is committed; everything else in `.pre-deploy-tests/` stays local. | the `.gitignore` question on the first run |
| A later plan tests only what changed since the last plan; if most of the change is shared code, it plans everything. | `--full` |
| Fix takes only bugs marked Fix; undecided bugs are skipped unless you say otherwise when asked. | the Fix / Skip switch on the page, or the undecided-bugs question |
| The highest model a fix gets is Opus; a pick above it gets Opus with one more effort level. | the highest-model question, asked every fix run |
| One PR per bug, squash auto-merged; the next bug starts only after the merge. | none |
