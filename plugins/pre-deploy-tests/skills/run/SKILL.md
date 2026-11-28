---
name: run
description: Run the pre-deployment test sessions written by /pre-deploy-tests:plan — one test agent per platform copy (Chromium, WebKit, Firefox, iOS Simulator, Android emulator), side by side on their own worktree, app and database, or one at a time on an integration environment — record every bug with a reproduction, captures and a fix prompt without changing app code, and publish a private bug review page with a Fix / Skip choice per bug and a ready / not-ready verdict. Use whenever the user wants to run, execute or continue the pre-deploy tests, "test the app now", "run the QA sessions", "is it ready to deploy", or resume an interrupted test run, even if they do not say "run". Not for writing the plan (use /pre-deploy-tests:plan) or fixing the bugs (use /pre-deploy-tests:fix).
---

# Run the pre-deploy tests

Execute the test sessions in `.pre-deploy-tests/sessions/`, record what breaks, and publish the bug review page. Test agents test and record; nobody fixes anything in this run, because a fix made mid-test changes what the other sessions are testing. Fixing is `/pre-deploy-tests:fix`, after people have chosen what to fix on the page.

All paths below are relative to the repository root (`git rev-parse --show-toplevel`). Run git commands from there.

## 1. Read the plan and resume

- If `.pre-deploy-tests/progress.md` or `.pre-deploy-tests/record.json` is missing, tell the user to run `/pre-deploy-tests:plan` first and stop.
- Read `.pre-deploy-tests/record.json` (`platform_copies`, `target`, `launch`, `profile.template`, `sessions`, `last_planned_sha`), `.pre-deploy-tests/CLAUDE.md` and `progress.md`. Each session file starts with `Model:`, `Effort:`, `Platform copies:` and `Covers:` lines.
- Sessions to run: every `not_started` and `active` one, in number order. An `active` session was interrupted: delete its `.pre-deploy-tests/bugs/inbox/<session>-*` folders and run it again from the start. `complete` sessions are never re-run. If any session is `blocked`, ask once whether to retry the blocked ones (their reason is in the table).
- Nothing left to run and `.pre-deploy-tests/page.json` exists: print the verdict line and page link from it, and stop. Nothing left to run and no page: go to step 7.
- Copies in play: the union of the `Platform copies:` lines of the sessions to run.

## 2. Preflight

Check everything the copies in play need before any agent starts, so a missing tool shows up now and not halfway through the run:

| Copy | Check |
|---|---|
| chromium, webkit, firefox | `playwright-cli --version`; webkit and firefox also need `playwright-cli install-browser <name>` once (run it if the first `open --browser <name>` fails) |
| ios | macOS with Xcode: `xcrun simctl list devices available` lists an iPhone (and an iPad when the session sizes include tablet) |
| android | `adb version` and `emulator -list-avds` list a phone (and a tablet AVD when needed) |
| ios, with landscape in its sizes | Accessibility permission for the terminal (rotation sends a keystroke): `osascript -e 'tell application "System Events" to UI elements enabled'` prints `true`; if not, the user grants it in System Settings > Privacy & Security > Accessibility |
| any native recording | `ffmpeg -version` (optional: without it iOS recordings stay `.mov`) |

- **Credentials:** `launch.test_account` (or `.pre-deploy-tests/CLAUDE.md`) names the environment variables that hold test credentials. Check each is set (`[ -n "$VAR" ]`); never print a value.
- **The app answers:** integration target: `curl -sSL -o /dev/null -w '%{http_code}' <target.url>` returns 2xx or 3xx. Local target: step 4 starts each app and waits for `ready_url`.

List what is missing in one short list. Then ask (AskUserQuestion): "I'll fix it, then continue" (Recommended) or "Continue without it". On continue, each copy that cannot run is left out, and every session that needed it ends `blocked` with the reason (step 6). On fix, check again.

## 3. Lanes

A lane is one test agent running at a time.

- **Integration target: one lane**, no question. Agents running side by side against one shared environment would change each other's data.
- **Local target:** read the machine:
  - macOS: cores `sysctl -n hw.ncpu`; free RAM from `vm_stat`: (pages free + inactive + speculative) x the page size in its first line.
  - Linux: cores `nproc`; free RAM is the `available` column of `free -b`.
  - Count the copies in play, each `ios` or `android` copy counting as two (a simulator or emulator is heavy). Suggest `max(1, min(that count, floor(cores / 2), floor((free GB - 4) / 4)))`.
  - Ask (AskUserQuestion) with the suggestion first, marked (Recommended), showing the cores and free RAM it came from; the user can type another number.

A simulator or emulator takes two lanes while it runs. iOS simulator copies of one session run one after another, never side by side, and each keeps one simulator booted at a time (phone, then tablet): iOS rotation sends a keystroke to whichever Simulator window is in front, so two booted simulators can rotate the wrong device. Android emulator and browser copies are unaffected.

## 4. Local target: one worktree, app and database per copy

Skip this step for an integration target: every agent uses `target.url`.

For each copy in play, in `.pre-deploy-tests/worktrees/<copy>/`:

1. `git worktree add --detach .pre-deploy-tests/worktrees/<copy> <last_planned_sha>`: every copy tests the commit the plan covers. If `origin/<target.branch>` has moved past it, say so in one line (the run still tests the planned commit; a new plan picks up the change).
2. Start the app with its own port and database:
   - Template project (`profile.template` set): run `make worktree-env` in the worktree and use the port and database it prints; start the app the way the worktree's own `CLAUDE.md` says.
   - Otherwise use `launch`: pick a free port (`8100 + n`, checked with `lsof -i :<port>`) and the database name `pdt_<copy>`, substitute them for `{port}` and `{db}`, run `db_setup`, then `start` in the background (Bash with `run_in_background`, never `nohup` or `&`), and poll `ready_url` until it answers (up to two minutes). Run the test-account seed command if `test_account` names one.
   - Native copies: build and install onto the copy's simulator or emulator with `launch.native_build`, pointed at that copy's app server (how to point it is in `.pre-deploy-tests/CLAUDE.md`; if it is not, ask the user once and add the answer there).
3. A copy whose app does not start: show the last 20 lines of its output, leave the copy out, and mark its sessions as in step 2.

With fewer lanes than copies, keep at most the lane count of apps running: start a copy's app when its agent starts and stop it when the agent ends (the worktree and database stay).

## 5. Run each session

For each session to run, in order: set it to `active` in `progress.md`, then spawn one subagent per platform copy the session lists (left-out copies excepted), side by side up to the lane count (iOS simulator copies one after another, see step 3); the rest wait for a free lane. Use the session's `Model` as the Agent `model` and its `Effort` as the `effort`. Print one line per agent first: `Session NN <copy>: <model> <effort>`.

The subagent prompt (fill in the absolute paths; `${CLAUDE_SKILL_DIR}` is this skill's folder):

```
You are a test agent for pre-deploy tests. You test; you never fix.

Session file: <abs path to .pre-deploy-tests/sessions/session-NN.md>. Read it first and follow its Test rules block.
Your platform copy: <copy>. App: <URL with this copy's port, or the integration URL>; <simulator or emulator name for ios/android>.
Test every item of the session at every size and orientation the session lists for your copy.
Test credentials are in the environment variables <names>. Never print or write their values.

Bug record format: read ${CLAUDE_SKILL_DIR}/references/bug-record.md and follow it exactly.
Captures: <web copies> read the section "One screenshot or one recording outside a comparison" of ${CLAUDE_SKILL_DIR}/references/web.md (add --browser <copy> for webkit and firefox). <ios/android> read "iOS simulator" or "Android emulator", and "Rotation and tablets", in ${CLAUDE_SKILL_DIR}/references/native.md. A static bug gets a screenshot; a bug with movement gets a recording. Run playwright-cli from <abs scratch dir>, never the repo root.

Write each finding to <abs>/.pre-deploy-tests/bugs/inbox/<NN>-<copy>/<slug>/ (finding.md, captures, scripts). Reproduce each bug 3 times before recording it and write the count. Save every script you used to reach or show a bug next to its finding.
Write <abs>/.pre-deploy-tests/bugs/inbox/<NN>-<copy>/results.md: one line per test item and size: T-NNN, size, orientation, pass | fail <slug> | blocked <reason>.
Change no file outside .pre-deploy-tests/ and do not change git state. Do not ask the user questions: anything you cannot do is "blocked" with the reason.
End with one line: passed, failed and blocked counts.
```

Wait for every agent of the session before step 6. An agent that ends with no `results.md` did not finish: spawn it once more; if it fails again, its copy counts as blocked for this session ("agent did not finish").

## 6. After each session: merge and number

1. Read every `finding.md` in the session's inbox folders, against the format in `${CLAUDE_SKILL_DIR}/references/bug-record.md`.
2. **Duplicates:** findings with the same symptom on the same screen in different copies, sizes or orientations, or plainly the same cause, are one bug that lists every place under `where`. Also compare against the `bugs/BUG-NNN/` folders from earlier sessions of this run: the same bug seen again gets its new places added, not a new number.
3. **Number** each new bug `BUG-NNN`: one more than the highest existing number, three digits. Write `bugs/BUG-NNN/bug.md` (id filled in, also in the "Fix prompt" title and script path; places, reproduction counts and captures combined; the highest severity found), move its captures into `bugs/BUG-NNN/captures/` named `<copy>-<size>-<orientation>[-<n>].<ext>`, and its scripts to `bugs/BUG-NNN/repro.<ext>` (`repro-<copy>.<ext>` when they differ). Check that every UI bug has a capture of the right kind; a moving bug without a recording is incomplete, so say so under Captures.
4. Keep the session's `results.md` files as `bugs/results/<NN>-<copy>.md` and delete the session's inbox folders.
5. In `progress.md` set the session to `complete` when every copy ran every item, else `blocked: <copy>: <reason>` (its bugs still count). Print one line: `Session NN: <n> new bugs, <m> seen again, <blocked copies>`.

## 7. Publish the bug review page

1. **Clean up** (local target): stop every app this run started, `git worktree remove --force` each `.pre-deploy-tests/worktrees/<copy>`, then `git worktree prune`. Databases stay; list their names in the report so the user can drop them.
2. **Verdict:** "Not ready" if any bug is Blocker or Major, or any planned session is not `complete`; otherwise "Ready". Keep the reasons (for example "2 Major; session 04 blocked: android: no emulator").
3. **Fill the page.** Load the `artifact-design` skill once before the first publish. Copy `${CLAUDE_SKILL_DIR}/assets/report-template.html` to `index.html` in a scratchpad folder (`PAGE_DIR`) and fill it by the comments in it: `{{PROJECT}}` is the repository name, `data-repo` is `owner/name` (`gh repo view --json nameWithOwner -q .nameWithOwner`), the verdict and its reasons, the counts, the session table, and one card per bug, by severity then number. Every field of `bug.md` goes on the card; captures and scripts are linked as `BUG-NNN/captures/<file>` and `BUG-NNN/repro.<ext>`. Escape `&`, `<` and `>` in all text taken from a record, and `"` in attribute values.
4. **Publish** as a private Artifact: `file_path` `PAGE_DIR/index.html`, `icon` `bug`, a one-sentence `description` ("Pre-deploy test run of <repo>: Not ready, 1 Blocker, 2 Major, 4 Minor"), `files` mapping each published path `BUG-NNN/captures/<file>` and `BUG-NNN/repro.<ext>` to its file under `.pre-deploy-tests/bugs/`, and exactly these capabilities:

   ```json
   {"db":{"rules":[{"path":"choice","read":"view","write":"admin"},{"path":"status","read":"view","write":"admin"}]},"user":{}}
   ```

   At most 255 files go in one publish: above that, publish the rest in further calls to the returned `url`, each with the same `file_path`. The page title is `<project> Pre-deploy Tests` (the template's `<title>`); the plan and fix skills find the page by that title and its `data-repo`, so keep both.
5. **Published before in this run** (`.pre-deploy-tests/page.json` exists, for example after retrying blocked sessions): run Artifact `action: "list_files"` with its `url` first, then publish to that `url`, so Fix / Skip choices already made stay. A new plan archives `page.json`, so the next plan's run gets a new page and old choices never land on new bug numbers.
6. Write `.pre-deploy-tests/page.json`: `{"url": "<artifact url>", "published_at": "<YYYY-MM-DD>", "verdict": "Ready|Not ready", "reasons": [...]}`.

Shared state on the page (the fix skill reads and writes it with Artifact `read_db` / `write_db`):

- collection `choice`, doc id = bug id (`BUG-007`), `{"choice": "fix" | "skip"}`. Editors set it with the page's Fix / Skip switch; no doc means undecided.
- collection `status`, doc id = bug id, `{"status": "fixing" | "fixed" | "norepro" | "attention", "pr": "<url or empty>", "note": "<reason>"}`.

## 8. Report

End with: the verdict and its reasons, bug counts by severity, blocked sessions with their reasons, databases left behind, and the page link. Say the page is private until the user shares it from claude.ai, and that the next step is to mark each bug Fix or Skip on the page and run `/pre-deploy-tests:fix`.
