---
description: Drive open `ai`-labeled GitHub issues to zero — loop branch → implement → finalize PR → merge → reset for every issue until none remain
argument-hint: [optional model override, e.g. "opus" — defaults to sonnet]
---

Empty out open GitHub issues labeled `ai` one at a time, each through a full branch → implement → finalize → merge → reset cycle, looping until none remain.

Resolve model: parse "$ARGUMENTS" for a model override (`sonnet`, `opus`, `haiku`, `fable`). Default: `sonnet`.

Determine the main branch (`git symbolic-ref refs/remotes/origin/HEAD`, or ask if ambiguous) once, up front.

A subagent cannot itself spawn further subagents — so each cycle below runs as ONE subagent that does everything inline. Rather than restating `/impl-issue`'s, `/finalize-pr`'s, and `/write-issue`'s steps here, point the subagent at those command files directly (`${CLAUDE_PLUGIN_ROOT}/commands/impl-issue.md`, `finalize-pr.md`, `write-issue.md`) and tell it to read and follow each one — skipping only their own "spawn an agent" sub-step, since it must do that work itself instead of delegating further. This keeps the three commands as the single source of truth; this file just wires them together. Spawning one subagent per cycle also gives each cycle a clean context, standing in for the `/clear` the user originally asked for — there's no tool that can trigger `/clear` from inside a running command.

Loop:

1. **Check for work.** Run `gh issue list -R "$(gh repo view --json nameWithOwner -q .nameWithOwner)" --label ai --state open --json number --limit 1`. Always pass `-R` explicitly — without it, `gh issue list` can silently no-op (empty result, no error) if the repo isn't auto-detected from cwd, which reads as a false "no issues left" rather than a failure. If empty, invoke the `ntfy:ntfy` skill to send "No issues left — no open ai-labeled issues" with title "drain-issues" and priority 4, and stop.

2. **Spawn one subagent for the full cycle** (subagent_type: general-purpose, model: as resolved above, run_in_background: true). Its prompt should instruct it to:
   a. Read `${CLAUDE_PLUGIN_ROOT}/commands/impl-issue.md` and follow it for the oldest open `ai`-labeled issue — creating a branch off `<main branch>` first, then implementing and committing with a `Closes #<number>` trailer per that command's steps, except its "spawn an agent" step (do the implementation itself).
   b. Read `${CLAUDE_PLUGIN_ROOT}/commands/finalize-pr.md` and follow it against the resulting diff — running code review with fixes, writing and executing a test plan, and logging unresolved items via `${CLAUDE_PLUGIN_ROOT}/commands/write-issue.md`'s issue-creation steps — again doing each step itself instead of spawning further agents.
   c. Push the branch and open the PR (`gh pr create`), carrying the `Closes #<number>` line into the PR body so the issue auto-closes on merge, and listing any new follow-up issues under a "Follow-ups" section.
   d. Poll the PR's checks every 5 minutes (`gh pr checks`): once all pass, merge it (`gh pr merge`); if any fail, fix the break, commit, push, and resume polling.
   e. If it hits something hard, significant, or needing a decision only the user can make, invoke the `ntfy:ntfy` skill to send a notification describing the blocker and stop rather than guessing.
   f. Report back: branch name, PR URL, issue number closed, final status (merged / stopped-for-decision / stuck), and any follow-up issues it opened.

3. **Watch for a dead agent.** While the subagent runs, check back every 20 minutes (ScheduleWakeup) that it's still alive (TaskList/TaskGet) — this is only a safety net for a silently-died agent, not a substitute for the completion notification. If it's gone with no completion notification, invoke the `ntfy:ntfy` skill to send a notification describing that the cycle died mid-run and stop the loop.

4. **On completion**, per the subagent's final report:
   - Stopped for a user decision → its own notify-me already fired; stop the loop and wait for the user.
   - PR merged → run `git checkout <main branch> && git fetch && git reset --hard origin/<main branch>`, then go back to step 1.
   - Stuck / unresolved failure → invoke the `ntfy:ntfy` skill to send a notification describing what's stuck and stop the loop.

Repeat until step 1 finds no open `ai`-labeled issues left.

Note: this command auto-commits, auto-pushes, and auto-merges without per-step confirmation by design — that's its entire purpose. Confirm with the user before the first run that this is what they want for this repo/branch.
