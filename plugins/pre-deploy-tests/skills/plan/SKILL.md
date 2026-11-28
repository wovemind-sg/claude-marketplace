---
name: plan
description: Write a pre-deployment test plan for the app in this repo — its logic and its UI on every platform, screen size, orientation and browser it supports — and split it into test sessions with /plan-tools:split-plan, each with a model picked by /model-picker:pick-model. A later run plans only what changed since the last plan. Use whenever the user wants to test the app before a deploy or release, asks "is this safe to deploy", "plan the QA", "what should we test before shipping", "test plan for mobile and tablet", or wants to refresh the test plan after new commits, even if they do not say "plan". Not for running the tests (use /pre-deploy-tests:run).
argument-hint: "[--full]"
---

# Pre-deploy test plan

Write a test plan for the app in the current repository and split it into test sessions that `/pre-deploy-tests:run` executes. This skill plans only: it never runs a test and never changes app code.

Everything the skill writes goes under `.pre-deploy-tests/` at the repository root. Only `.pre-deploy-tests/record.json` is committed; it is what the next plan needs to test only what changed. Everything else (spec, sessions, bugs, captures, worktrees, archive) stays local.

## 1. Guards and arguments

- If the `plan-tools` plugin is not installed (`/plan-tools:split-plan` is not in the skill list), tell the user to install it (`/plugin install plan-tools@wovemind`) and wait.
- If the `model-picker` plugin is not installed (`/model-picker:pick-model` is not in the skill list), tell the user to install it (`/plugin install model-picker@wovemind`) and wait.
- `$ARGUMENTS` may hold `--full`, which forces a full plan even when a record exists. Ignore anything else and say so.
- Run from the repository root (`git rev-parse --show-toplevel`). If the working tree is not a git repository, stop and say the plan needs git.

## 2. Full or incremental

Read `${CLAUDE_SKILL_DIR}/references/record.md` now: it holds the record schema and the incremental selection rules this step and steps 3-9 use.

- No `.pre-deploy-tests/record.json`, or `--full`: **full plan**.
- A record exists: **incremental plan** of `git diff <last_planned_sha>..HEAD`, following "Incremental selection" in `record.md`. If that section says to fall back to a full plan (baseline missing from history, most of the change in shared code), say why in one line and do a full plan.

Then, in this order:

1. Incremental only: collect the bugs to re-test ("Bugs to re-test" in `record.md`) before anything moves, because step 2 moves the bug files.
2. If `.pre-deploy-tests/worktrees/` holds worktrees from an earlier run, remove each with `git worktree remove --force <path>`, then `git worktree prune`.
3. Move every file and folder in `.pre-deploy-tests/` except `record.json` and `archive/` into `.pre-deploy-tests/archive/<YYYY-MM-DD>/` (add `-2`, `-3` if that folder exists). Old sessions and bugs stay readable there and never mix with the new plan.

## 3. App profile and the questions

**Detect the app type** from the repo before asking anything, so the questions only confirm:

| Signal | Means |
|---|---|
| `package.json` depends on `@capacitor/core`, or a `capacitor.config.*` file exists | web + native (Capacitor); `ios/` and `android/` folders show which platforms |
| `package.json` depends on `expo` or `react-native`, or `app.json` has an `expo` key | native (React Native / Expo); Expo with a `web` platform also ships to the web |
| `*.xcodeproj` / `Podfile` without Capacitor or React Native | native iOS |
| `build.gradle` / `build.gradle.kts` / `AndroidManifest.xml` without Capacitor or React Native | native Android |
| A web server or front-end framework (FastAPI, Go `net/http`, Django, Express, Next, Vite, templates, `index.html`) and none of the above | web only |

Also look for: dark mode (`prefers-color-scheme`, a theme toggle, `dark:` classes), right-to-left text (`dir="rtl"`, RTL locales) and translations (locale files, i18n libraries); a project made by `/fastapi-template:fastapi-template` or `/go-webapp-template:go-webapp-template` (a `worktree-env` target in its `Makefile`), which already gives each worktree its own port and database.

**Ask in one round** with AskUserQuestion. It takes up to four questions per call, so send the calls back to back without work in between. Put the detected answer first, marked (Recommended):

1. App type: web only, web + native (Capacitor), or native only; and for native, iOS, Android or both. If the web build of a Capacitor or Expo app is also served on the web, the web counts as a platform too.
2. Device classes (multi-select): desktop 1440x900, tablet 820x1180, phone 390x844, small phone 360x640. Offer only the classes the app type can have; desktop only when it runs in a browser.
3. Orientations: portrait only, or portrait and landscape. Landscape applies to the phone, small phone and tablet sizes; desktop is already landscape.
4. Firefox: do you support it? Chromium and WebKit are always tested when the app runs in a browser; Firefox only on a yes.
5. Only when detected: dark mode, right-to-left text, extra languages — test them, yes or no.
6. Test target: the default branch run locally (each test lane gets its own worktree, app and database), or an integration environment (ask for its URL). Name the default branch from `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`.
7. Highest model a test session may use: Opus (Recommended), Fable, Sonnet, Haiku. It caps what pick-model chooses in step 6.

**Incremental runs** reuse the recorded profile and ask only questions 6 and 7. If the diff shows a new platform (for example an `android/` folder appeared), ask question 1 again too.

From the answers, build the list of **platform copies** — one copy is one environment a test agent drives, and the copies of a session run side by side:

- `chromium`, `webkit`, and `firefox` if supported: when the app runs in a browser.
- `ios` (iOS Simulator) and `android` (Android emulator): for each native platform confirmed.

And the **sizes** each copy is tested at: every chosen device class, in every chosen orientation (no landscape variant of desktop). For `ios` and `android`, phone means a phone simulator or emulator and tablet means an iPad simulator or a tablet emulator; their screen size is the device's own.

## 4. User flows

- `user-flows.md` at the repository root: every `UF-NNN` in it becomes a test item (step 5) that traces to that flow. If the project has a `test-user-flows` target in its `Makefile`, plan one item that runs `make test-user-flows` against the target.
- No `user-flows.md`: offer to create it first with `/user-flows:extract-user-flows` (AskUserQuestion: "Extract user flows first (Recommended)" / "No, plan from the code"). If the `user-flows` plugin is not installed (`/user-flows:extract-user-flows` is not in the skill list), tell the user to install it (`/plugin install user-flows@wovemind`) and wait. On yes, invoke it and continue with its file. On no, build the inventory yourself from the code: every route, page or screen, every form and its handler, every role and permission check, every background job a user can see the result of. Ground each item in a file; never invent a feature.

## 5. Draft the test spec

Read `${CLAUDE_SKILL_DIR}/references/test-areas.md` now and write `.pre-deploy-tests/SPEC.md`:

1. **App profile**: type, platforms, platform copies, sizes and orientations, browsers, dark mode / RTL / languages, user flows present or not.
2. **Target**: local default branch (and its name) or the integration URL.
3. **Launch** (local target only): how each lane starts its own app on its own port and database. A template project (a `worktree-env` target in its `Makefile`) uses that, so ask nothing. Any other project: ask once, in plain words, for the command that starts the app on a given port and database, the command that creates and migrates that database, the URL that answers when the app is ready, and how a test account is made (a seed command, or environment variable names that hold test credentials — never the secrets themselves). Write `{port}` and `{db}` where the values go. Native copies also need the build command for a simulator or emulator.
4. **Coverage matrix**: one row per area from `test-areas.md` that applies to this app type; one column per platform copy; each cell lists the sizes and orientations tested, or "n/a" with the reason.
5. **Test items** `T-001`, `T-002`, … numbered across the whole spec. Each item has: what to test, steps, expected result, platform copies, sizes and orientations, and its trace — a `UF-NNN`, a screen or route, or a source file. An item with no trace does not go in. Take the areas from `test-areas.md` and keep only what this app has (no file upload, no file upload tests).

An incremental plan's spec holds only the selected items plus the bug re-tests from step 2, each re-test tracing to its `BUG-NNN`.

## 6. Sessions, models and review

Break the spec into test sessions by split-plan's rules: one goal per session (an area of the app, or a group of flows), about 120k tokens of work, and each session lists its platform copies and the files and flows it covers. Keep the items that drive the same screens together, so one agent learns a screen once.

For each session, invoke `/model-picker:pick-model` with the session's goal, its test items and its platform copies as the job. Turn the answer into the lowercase family word (haiku, sonnet, opus, fable). Model order: Haiku < Sonnet < Opus < Fable. If the pick is above the cap from question 7, use the cap model with the effort one level higher (low, medium, high, xhigh, max; max stays max), and note "capped from <model>".

Show the coverage summary and wait for the user's go-ahead before writing any session file:

- areas covered and areas left out (with the reason)
- platform copies, sizes and orientations
- one line per session: number, title, model and effort (and "capped from" when capped), platform copies, item count
- for an incremental plan: the base commit, the changed files that caused each session, and the bugs re-tested

Change the plan as the user asks and show the summary again.

## 7. Write the session files with split-plan

Invoke `/plan-tools:split-plan` with no model word and follow it, with these overrides (they win over split-plan's own text):

- The plan is `.pre-deploy-tests/SPEC.md`; it already exists, so skip split-plan's step 1b. Write the output under `.pre-deploy-tests/` (`.pre-deploy-tests/CLAUDE.md`, `.pre-deploy-tests/progress.md`, `.pre-deploy-tests/sessions/session-NN.md`), not `.planning/`.
- Use the sessions the user approved in step 6. Write at least one session file even if the plan is small: the run skill reads sessions.
- Sessions test; they do not build. They do not end in a commit and do not update the project's root `CLAUDE.md`; leave both out of the session files.
- Every session file starts with these lines, exactly as named, right under its title:

  ```
  Model: <haiku|sonnet|opus|fable>
  Effort: <low|medium|high|xhigh|max>
  Platform copies: <comma-separated: chromium, webkit, firefox, ios, android>
  Covers: <T-NNN items>; <UF-NNN flows>; <files or globs>
  ```

  Then: Goal, Sizes and orientations per copy, the test items in full (steps, expected, trace), How to verify (every item reported as pass, fail with a bug, or blocked with the reason), and this block verbatim:

  ```
  ## Test rules
  - Change no app code, configuration, data fixtures or tests in the repository. You test; you never fix.
  - Do not commit, push, open a pull request or change git state.
  - Record every bug in the format of `run/references/bug-record.md` in the pre-deploy-tests plugin.
  - After a bug, carry on with the next test item. A bug never ends the session.
  ```

- `.pre-deploy-tests/progress.md` is one table, every session `not_started`:

  ```
  | Session | Title | Model | Effort | Status |
  |---|---|---|---|---|
  | 01 | <title> | opus | high | not_started |
  ```

- `.pre-deploy-tests/CLAUDE.md` holds the app profile, the target, the launch commands and the platform copies, under 60 lines.

## 8. Record and commit

Write `.pre-deploy-tests/record.json` by the schema in `record.md`: profile and answers, launch commands, per-session coverage, `last_planned_sha` (HEAD when this plan was made), `mode` (`full` or `incremental`) and `base_sha`.

First run in this repo (no `.pre-deploy-tests` lines in `.gitignore`): ask whether to add these lines, so only the record is ever committed:

```
.pre-deploy-tests/*
!.pre-deploy-tests/record.json
```

Then ask whether to commit the record. On yes, commit `record.json` (and `.gitignore` if it changed) with the message `chore: record pre-deploy test plan`, and nothing else. On no, leave it uncommitted and say the next plan can only diff from it once it is committed.

## 9. Publish the commit status

Publish a status on the planned commit (`last_planned_sha`), so the plan is visible on GitHub next to the commit it covers:

```
gh api repos/{owner}/{repo}/statuses/<last_planned_sha> -f state=success -f context=pre-deploy-tests -f description="planned: <N> sessions (full|diff from <base_sha7>)"
```

GitHub only takes a status for a commit it has, so an unpushed commit fails. A failure is reported in one line, never fatal: the record is the baseline, the status is the cross-check.

## 10. Report

End with: full or incremental (and the base commit), the session table (number, title, model, effort, platform copies), what was left out and why, whether the record was committed, the status result, and the next step: `/pre-deploy-tests:run`.
