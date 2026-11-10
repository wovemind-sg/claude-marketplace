---
name: plan-implement-complete
description: Take the current implementation plan all the way to a PR — implement it with subagents (via plan-split-implment when the plan was split into .planning/ sessions), fold any related problems found along the way into the plan instead of filing follow-up issues, run finalize-pr once, open the PR, and optionally monitor it until it auto-merges. Use whenever the user says "implement the plan end to end", "implement and raise a PR", "finish this plan", "take the plan to a PR", "implement it all and merge", or otherwise wants a plan implemented and shipped in one go rather than session by session.
argument-hint: [optional path to the plan file] [--branch <name>]
---

Ship the current plan end to end: implement → finalize → PR → (optionally) merge. You orchestrate; subagents do the implementation work so this session's context stays free for coordination.

## 1. Find the plan

- `.planning/progress.md` + `.planning/sessions/` exist (output of `/plan-tools:split-plan`) → **split plan**.
- Otherwise the plan is `$ARGUMENTS` if given, else the plan in this conversation (e.g. just approved from plan mode), else the most recent file in `~/.claude/plans/`. Confirm the file with the user if you had to guess → **single plan**.
- No plan found → tell the user and stop.
- `--branch <name>` in `$ARGUMENTS` is a flag for step 3, not the plan path; remove it before looking for a path.

## 2. Ask everything up front

The run is long and unattended, so collect every decision now (the first `AskUserQuestion` call holds the 4-question maximum), then don't interrupt the user again except for real blockers:

1. **Implementer model** — model for implementation subagents. Options: Sonnet (Recommended), Opus, Haiku.
2. **Finalize model** — model for `finalize-pr`'s review and test-plan subagents. Options: Sonnet (Recommended), Opus, Haiku.
3. **Git permission** — "Do you give permission in advance for the commits, the push and opening the PR?" Options: Yes (Recommended), No — stop before pushing.
4. **Auto-merge** — "Should the PR be auto-merged once checks pass?" Options: Yes — monitor until merged, No — stop at the open PR.
5. **UI audit** — only when the `ui-audit` plugin is installed (`/ui-audit:capture` is in the skill list); ask it in a second `AskUserQuestion` call. "If the implementation changes UI, run the UI audit?" Options: Yes, config defaults (Recommended), No.

If git permission is **No**, still implement and commit locally (commits stay on the branch, nothing leaves the machine) but stop before the push (finalize-pr's step 5, run from step 4 below) and hand back to the user. Auto-merge is moot then.

## 3. Implement

Make sure you're on a feature branch first; if on `main`/`master`, create one (`plan/<feature-name>`).
With `--branch <name>`, use that name instead, and pass `--branch <name>` to `/plan-tools:plan-split-implment`.

Every implementing subagent gets the chosen model and this instruction block verbatim in its prompt — it is what keeps the plan self-contained:

> **Problems you discover along the way.** For related problems, this overrides any rule in the plan (such as its `## Implementation rules`) that says to change only what the plan lists. If you hit a bug, gap or loose end that is related to this plan, fix it as part of the plan — do not open a GitHub issue for follow-up and do not leave a TODO for later. If it is too big to fit in your session without crowding your context, add a new session for it instead of cramming it in: write `.planning/sessions/session-<NN>-<slug>.md` in the same format as the others (including the plan's `## Implementation rules` block and the Decisions and requirement-map rows that apply, if the other session files have them) and add it to `.planning/progress.md` right after the current session. Problems unrelated to this plan: leave them alone and mention them in your final report. Do not create, comment on, edit or close any pre-existing GitHub issue.

- **Split plan** → invoke `/plan-tools:plan-split-implment` and follow it, with two additions: pass the chosen model to every session subagent, and append the instruction block above to each session subagent's prompt. Re-read `progress.md` after each session — sessions added mid-run are picked up by its loop like any other.
- **Single plan** → spawn one subagent (chosen model) with the plan file, the instruction block, and: implement the whole plan, commit as it goes (semantic commit messages), report what it did. If the plan is clearly too big for one context, run `/plan-tools:split-plan` on it first and treat it as a split plan instead. If the subagent ends with a question for the user instead of finishing, ask the user with AskUserQuestion in plain English, then send the answer to that same subagent with SendMessage so it continues.

If implementation stops in a broken state, stop and report — don't push a half-implemented plan.

## 4. Finalize

Invoke `/plan-tools:finalize-pr` and follow it, with these overrides (tell its subagents too):

- Use the chosen finalize model for its subagents.
- **Run the test plan once.** Don't offer to re-run it, e.g. in a headed browser — one pass, fix what it finds, move on.
- **No follow-up issues.** Its residual-work step would file issues; instead hand each unresolved item that relates to this plan to a subagent (implementer model) with the instruction block above, commit the fixes, and only then open the PR. Unrelated items go into the PR body under "Notes", not into issues.
- Its push/PR confirmation and UI-audit question are already answered by step 2 — pass both answers (git permission, UI audit yes/no with config defaults) so its step 0b asks nothing. Always state the git permission explicitly, Yes or No; on No, finalize-pr stops after its step 4 and does not push or open the PR.

## 5. Merge (if auto-merge = Yes and git permission = Yes)

Skip this step when git permission is No: no PR exists.

1. Enable auto-merge: `gh pr merge <pr> --auto` with the repo's allowed method (`gh repo view --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed`; prefer squash if allowed).
2. Invoke `/plan-tools:monitor-pr <pr>` and follow it until the PR merges. Auto-merge is already on, so skip its auto-merge question.

## 6. Report

A few lines: PR URL and state (merged / open), sessions run (and any added mid-run), what finalize-pr fixed, anything unrelated noted in the PR body.
