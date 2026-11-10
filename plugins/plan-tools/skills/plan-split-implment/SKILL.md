---
name: plan-split-implment
description: Orchestrate execution of a session-split implementation plan (produced by split-plan) by delegating each incomplete session to its own subagent, sequentially. Use when .planning/ (or sessions/ and progress.md) exists and the user wants to run through the remaining sessions.
argument-hint: "[--branch <name>]"
---

You are the orchestrator for a session-split implementation plan. NEVER implement anything yourself — only delegate to subagents and monitor.

## Setup

1. Read `.planning/progress.md` and `.planning/sessions/` (default location — if missing, check the project root, then ask the user).
2. Check the current git branch. If on `main` or `master`, create an implementation branch first (e.g. `plan/<feature-name>`) and work there — every session ends with a commit, and those incremental commits belong on a branch, not on main.
   - With `--branch <name>` in `$ARGUMENTS`, use that name instead of `plan/<feature-name>`.

## Blocker check

Before spawning any subagent, read through every remaining session file (not just the next one) looking for blockers — steps the plan depends on that no subagent can complete on its own, because they require the user's own credentials, accounts, or access. Typical examples: signing up for or logging into a third-party service, creating an API key or OAuth app, granting a permission or dashboard access, buying a domain, or any manual action in a UI the subagent has no path to.

- If you find any, respond with **only** a numbered checklist of the blockers — no heading, no preamble, no explanation, no summary after. Be concise: one line per blocker, just enough for the user to act on it. Then stop and wait — do not spawn any subagent yet. Once the user confirms they're done, re-check anything ambiguous rather than assuming, then proceed.
- If you find none, say so in one line and go straight into the execution loop — don't wait for a go-ahead.

## Execution loop

Run sessions strictly sequentially — each depends on the previous. NEVER run sessions in parallel.

For each incomplete session, use the Task tool to spawn one subagent instructed to:
1. Read `.planning/CLAUDE.md` (plan conventions), then its session file.
2. Execute the session's tasks exactly.
3. Update the project's root CLAUDE.md with what changed this session (conventions, stack, structure introduced/changed). If it doesn't exist yet (new project), create it from scratch.
4. Commit the work (including the CLAUDE.md update).
5. Update `.planning/progress.md` (mark its session complete, next session active).
6. Exit.

If a subagent ends its run with a question for the user instead of finishing (its session's implementation rules tell it to, rather than guess), ask the user with AskUserQuestion in plain English, then send the answer to that same subagent with SendMessage so it continues with its context intact.

Do not start the next subagent until the previous one has finished AND `.planning/progress.md` confirms completion. If a session fails or ends in a broken state, stop and report to the user — do not skip ahead.

## After all sessions complete

Polish the root CLAUDE.md, now that every session has appended to it piecemeal:

1. If the `claude-md-management` plugin is installed (`/claude-md-management:claude-md-improver` is in the skill list), run `/claude-md-management:claude-md-improver` on it; otherwise skip this step and say so in the report.
2. If the `caveman` plugin is installed (`/caveman:caveman-compress` is in the skill list), run `/caveman:caveman-compress claude.md` on it; otherwise skip this step and say so in the report.
3. Commit the result.
4. If `user-flows.md` exists at the project root, invoke `/user-flows:update-user-flows` to sync it with everything implemented across all sessions, then commit the result. Skip this step if the file doesn't exist.

Archive the plan files into a feature-named subdirectory so the plan location stays clean for the next plan:

```bash
mkdir <plan_location>/<feature_name>
mv <plan_location>/*.md <plan_location>/sessions <plan_location>/<feature_name>/
```

Do NOT commit the move — the plan location is almost always gitignored.
