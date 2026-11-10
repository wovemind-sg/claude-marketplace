# plan-tools

Tools for restructuring implementation plans so large features can be built across multiple Claude Code sessions without blowing the context window.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install plan-tools@wovemind
```

Installing plan-tools also installs the plugins it depends on: `ntfy`, `fastapi-template` and `htmx-vs-alpine`.

## Requirements

- **`git`** and the **GitHub CLI (`gh`)**, signed in (`gh auth login`) with push access to the repository. Every issue, PR and status command goes through `gh`.
- **The `ntfy` plugin** (installed as a dependency) for `drain-issues`, which sends a push notification when it finishes, gets blocked or a cycle stalls. Set its `server` setting first; see the ntfy README.
- **`create-webapp`** uses `fastapi-template` and `htmx-vs-alpine` (dependencies). It also uses `use-railway` when the host is Railway, and the `capacitor-core` and `capacitor-deployment` skills when you want iOS/Android apps; when one of those is not installed it skips that part and says so.
- **`create-app`** checks for Node, Xcode with CocoaPods (iOS), JDK 17 with the Android SDK (Android) and an EAS login (`eas login`) before it plans.
- **`finalize-pr`** uses the built-in `/code-review` and `/security-review` skills, and the optional `ui-audit` and `ui-change-guard` plugins from this marketplace when they are installed.

## Settings and environment variables

No environment variables are needed. The plugin has one setting, which you change with `/plugin configure plan-tools@wovemind`:

| Setting | Default | What it does |
|---|---|---|
| `designer_ui_review` | `false` | When `true` and the `ui-change-guard` plugin is installed, `finalize-pr` runs `/ui-change-guard:review-ui-change` before it raises the PR, and labels the PR `ui-risky` if the review still finds a problem. |

A default only takes effect after you open the settings dialog and save it once. Until then the setting counts as off.

## Opinionated defaults

These are the team conventions the skills assume. Each one can be changed with the argument shown.

| Default | Where | Change it with |
|---|---|---|
| Deferred work goes into GitHub issues labeled `ai` | `write-issue`, `impl-issue`, `impl-issue-lite`, `drain-issues`, `finalize-pr`, `convert-residual` | `--label <name>` |
| Plan work happens on a branch named `plan/<feature-name>` | `plan-split-implment`, `plan-implement-complete` | `--branch <name>` |
| Sub-agents run on the `sonnet` model | `impl-issue`, `impl-issue-lite`, `drain-issues` (model word in the arguments, e.g. `opus`); `finalize-pr` (`--model <name>`); `create-webapp`, `create-app` and `plan-implement-complete` ask you up front | see each skill |
| A finished PR gets a `finalize-pr` commit status, and a UI audit gets a `ui-audit` status | `finalize-pr`, `monitor-pr` | fixed; a branch rule can require `finalize-pr` |
| A PR whose designer review still fails gets the label `ui-risky` | `finalize-pr` | only runs when `designer_ui_review` is on |
| New web apps use FastAPI + Jinja2 + HTMX + Alpine.js, deployed to Railway, with OpenRouter `openai/gpt-4o-mini` | `create-webapp` | `--host generic`, `--ai-model <model id>` |
| New mobile apps use Expo + React Native + expo-router, built and shipped with EAS | `create-app` | fixed |
| Auto-merge uses an allowed merge method: `plan-implement-complete` prefers squash, `monitor-pr` asks when more than one is allowed | `plan-implement-complete`, `monitor-pr` | the repository's merge settings |

## Example

Start a new web app, plan it, and implement it session by session:

```
/plan-tools:create-webapp a recipe box where friends share weekly meal plans
```

Or, in an existing repo where you already have a plan:

```
/plan-tools:split-plan
/plan-tools:plan-split-implment --branch feature/meal-plans
/plan-tools:finalize-pr
/plan-tools:monitor-pr
```

To work through deferred issues labeled `backlog` instead of `ai`:

```
/plan-tools:drain-issues opus --label backlog
```

## Skills

### `/plan-tools:create-webapp`

Bootstraps a brand-new FastAPI + Jinja2 + HTMX + Alpine.js web app end to end. Gathers the feature list, an optional design reference, whether the app also ships as iOS/Android apps (then a Capacitor WebView shell loading the deployed server is planned and built too, per the `capacitor-core` skills), and the planning/implementing models. Decides which parts of the `fastapi-template` stack to scaffold (Postgres/Alembic, Redis, OpenRouter, Google login, arq), collects only the `.env` values those parts need, writes `.env` + `.env.example` and gitignores `.env`, then tests every external dependency (DB, Redis, API keys, toolchain) so the implementer never stalls. Spawns a `Plan` subagent (following `plan-helper`; its open decisions are relayed to the user via `AskUserQuestion` and answered back with `SendMessage`) to write the plan into `.planning/SPEC.md`, runs `split-plan` directly under `.planning/`, and after the user approves per-session commits, hands off to `plan-split-implment` (split) or a single implementing subagent (not split). Client-side choices follow `htmx-vs-alpine`.

Usage:

```
/plan-tools:create-webapp [--host railway|generic] [--ai-model <openrouter model id>] [optional one-line app idea]   # defaults railway, openai/gpt-4o-mini
```

Requires the `fastapi-template` and `htmx-vs-alpine` plugins from this marketplace to be installed; the `capacitor-core` plugin too when mobile apps are wanted.

### `/plan-tools:create-app`

Same end-to-end flow as `create-webapp`, for apps that are **mobile only** (no web UI): Expo SDK 57 + React Native 0.86 + React 19.2 + expo-router + TypeScript 6 + zustand, tested with Jest 29 / jest-expo, built and shipped with EAS Build + Submit (TestFlight, Play alpha). Gathers features, platforms, bundle id, design reference and models; picks only the needed Expo/RN libraries and local Expo Modules (Swift / Kotlin — e.g. an Apple Vision / LiteRT similarity engine, a PHImageManager / BitmapFactory thumbnail cache) from `skills/create-app/references/stack.md`; collects `EXPO_PUBLIC_*` env values and store credentials; checks Node, Xcode/CocoaPods, JDK 17 / Android SDK and EAS login; then plans, splits under `.planning/` and hands off to implementing subagents.

Usage:

```
/plan-tools:create-app [optional one-line app idea]
```

### `/plan-tools:plan-helper`

Runs automatically whenever Claude writes an implementation plan (or invoke it directly). Makes the plan:

- **Ask, not assume** — every decision your request or the code doesn't already dictate becomes an AskUserQuestion round (UX, behavior, naming, edge cases, libraries, structure).
- **No unrequested changes** — each step cites which of your asks it serves (`Serves: A<n>`); anything without one is cut or asked about.
- **Smallest complete change** — each step states why nothing smaller works; real smaller-vs-larger trade-offs are put to you as questions.
- **Cover everything** — a requirement map lists each ask verbatim with its delivering step and verification, and verification includes running the real app/command, not only tests.

The plan carries an `## Implementation rules` block that binds implementers; `split-plan` copies it into every session file.

Usage:

```
/plan-tools:plan-helper
```

### `/plan-tools:split-plan`

Takes an existing implementation plan and splits it into isolated, context-sized sessions.

Usage:

```
/plan-tools:split-plan
```

Claude will ask where the existing plan lives if it doesn't already know, then produce:

- `SPEC.md` — the original plan, preserved as reference
- `progress.md` — session status tracker (Session 1 starts "active")
- `CLAUDE.md` — condensed project conventions (under 60 lines)
- `sessions/session-01.md`, `session-02.md`, ... — one file per session with goal, prerequisites, numbered tasks, files touched, verification steps, and handoff instructions. When the plan came from `plan-helper`, each file also carries the `## Implementation rules` block, the applicable Decisions and the requirement-map rows that session delivers (rows are ticked in `SPEC.md`)

With no plan, the skill drafts one following `plan-helper`.

The skill only plans — it does not implement anything. It ends by showing a one-line summary per session for review before implementation starts.

### `/plan-tools:plan-split-implment`

Executes a session-split plan (as produced by `split-plan`). Reads `sessions/` and `progress.md`, then spawns one subagent per incomplete session, sequentially. Each subagent reads its session file, does the work, commits, updates `progress.md`, and exits. The orchestrator only delegates and monitors — it does not implement anything itself. If a subagent hits a decision its plan does not answer, it ends its run with the question; the orchestrator asks you and sends the answer back to that subagent.

Usage:

```
/plan-tools:plan-split-implment [--branch <name>]   # default branch plan/<feature-name>
```

### `/plan-tools:write-issue`

Records deferred work (e.g. a bug found during review but out of scope now) as a GitHub issue labeled `ai`.

Usage:

```
/plan-tools:write-issue [--label <name>] <description of the work to do later>   # default label ai
```

### `/plan-tools:impl-issue`

Spawns a subagent to implement the oldest open `ai`-labeled GitHub issue, committing with a `Closes #<number>` trailer so the eventual PR auto-closes it on merge.

Usage:

```
/plan-tools:impl-issue [optional model override] [--label <name>]   # default label ai
```

### `/plan-tools:impl-issue-lite`

Same as `impl-issue` for a small, mechanically obvious issue: the subagent implements it and opens a PR without the full `finalize-pr` review and test-plan cycle. If the issue turns out not to be small, it stops and tells you to use `impl-issue`.

Usage:

```
/plan-tools:impl-issue-lite [issue number] [model override] [--label <name>]   # defaults: oldest open issue, sonnet, label ai
```

### `/plan-tools:convert-residual`

One-off migration for repos that used the older file-based residual format: turns each `.planning/residual/*.md` file into a labeled GitHub issue, then deletes the files.

Usage:

```
/plan-tools:convert-residual [--label <name>]   # default label ai
```

### `/plan-tools:finalize-pr`

Asks every question up front (push/PR go-ahead, UI audit), then runs unattended: `/code-review high --fix` (level `high` unless the arguments name another), a `/security-review` pass when the diff touches security-relevant code (high-confidence findings fixed, the rest become residual work), a test plan, logs any remaining loose ends as residual work (one `ai`-labeled issue per item via `write-issue`), then opens a PR, optionally runs a UI audit, and reports back what was fixed, tested, deferred, the audit URL and the PR URL.

Step order: 0 last finalized commit, 0b upfront questions, 1 code review, 1b security review, 2 test plan, 3 user flows, 3b repo steps, 4 residual work, 5 PR, 6 UI audit, 7 mark, 8 report.

When the diff touches UI files, the upfront questions include whether to run `/ui-audit:capture --unattended` (from the optional `ui-audit` plugin in this marketplace) and adds an "UI audit" section with a per-commit history to the PR body. The step is skipped with a note when the plugin is not installed or the diff has no UI changes.

Repos can add their own steps in `.claude/finalize-pr.md` (free-form markdown instructions). They run after the test plan and user-flows sync, before residual work and the PR (so the PR does not exist yet on a first run); findings they could not fix become residual work. On incremental runs the agent is told the `$BASE..HEAD` range and each step decides whether to scope to it. Example:

```markdown
1. Run `make lint` and fix what it reports.
2. If `migrations/` changed, check the new migration has a downgrade.
```

Run `/plan-tools:hook-finalize-pr [description]` to create or edit that file interactively: it inspects the repo, proposes steps, and writes `.claude/finalize-pr.md`.

Usage:

```
/plan-tools:finalize-pr [optional extra context] [--label <name>] [--model <name>]   # defaults: label ai, model sonnet
```

### `/plan-tools:drain-issues`

Drains open `ai`-labeled GitHub issues to zero. Loops: spawns one subagent per issue to run a full branch → implement → `code-review --fix` → test → PR (closing the issue) → merge cycle, watches it for a dead-agent safety net, resets local `<main branch>` after each merge, and repeats. Uses the `ntfy:ntfy` skill (ntfy plugin) to notify on completion, blockers needing a decision, or a stuck/dead cycle.

Usage:

```
/plan-tools:drain-issues [optional model override] [--label <name>]   # default label ai
```

Auto-commits, auto-pushes, and auto-merges without per-step confirmation by design — confirm with the user this is wanted before the first run.

### `/plan-tools:plan-implement-complete`

Ships the current plan end to end. Asks up front for the implementer and finalize models (default Sonnet), advance permission for commits/push/PR, and whether to auto-merge. Implements via `plan-split-implment` for `.planning/` split plans (or one subagent for a single plan file); related problems found along the way are fixed in-plan — adding sessions if needed — never filed as issues, and pre-existing issues are left alone. Then runs `finalize-pr` once (single test-plan pass, residual items fixed instead of filed), opens the PR, and if auto-merge was chosen enables it and runs `monitor-pr` until merged.

Usage:

```
/plan-tools:plan-implement-complete [optional plan file] [--branch <name>]   # default branch plan/<feature-name>
```

### `/plan-tools:monitor-pr`

Babysits an open PR until it merges. Polls in the background; when a check fails it fixes the root cause (or reruns once if flaky) and pushes; when the base branch moves it merges the base in, resolves conflicts keeping both sides' intent, and pushes; when the base branch requires the `finalize-pr` status and the head lacks it, runs `/plan-tools:finalize-pr` and makes sure the status lands on the pushed head. Never force-pushes or merges the PR itself — offers to enable auto-merge if it's off. Stops and asks when stuck (PR closed, fork, dirty tree, same check failing 3 times, conflict needing a product decision).

Usage:

```
/plan-tools:monitor-pr [pr-number-or-url]   # defaults to the current branch's PR
```

Requires `gh` authenticated with push access to the PR branch.
