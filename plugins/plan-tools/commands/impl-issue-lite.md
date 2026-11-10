---
description: Spawn a subagent to implement a small GitHub issue labeled `ai` — a specific issue number, or the oldest open one if none given — skipping the full review/test-plan cycle
argument-hint: [issue number] [model override, e.g. "opus"]
---

## Task

Implement one small, mechanically obvious residual work item, tracked as a GitHub issue labeled `ai`, then raise a PR for it — without the full `finalize-pr` review/test-plan/residual-issue cycle. Use this instead of `/plan-tools:impl-issue` when the issue is small enough that a separate review pass and formal test plan would be overkill (a few-line fix, a single well-scoped change, no design decision to make).

If the issue turns out not to be trivial once read in full — spans multiple files/components, involves a design or sequencing decision, or the approach isn't obvious — stop and tell the user to use `/plan-tools:impl-issue` instead rather than pushing ahead with the lite path.

## Steps

1. Parse `$ARGUMENTS` for an optional issue number (bare digits or `#123`) and an optional model override (`sonnet`, `opus`, `haiku`, `fable`), in either order. Default model: `sonnet`.
2. Resolve which issue to work on:
   - If an issue number was given, use it directly — skip the query below.
   - Otherwise run: `gh issue list -R "$(gh repo view --json nameWithOwner -q .nameWithOwner)" --label ai --author "@me" --state open --json number,title,body,createdAt --limit 100 -q 'sort_by(.[], .createdAt)[0]'`. Always pass `-R` explicitly — without it, `gh issue list` can silently no-op (empty result, no error) when the repo isn't auto-detected from cwd, which reads as a false "no issues" instead of a failure.
   - MUST stop and tell the user if no issue was found — do not fall back to picking a different issue.
3. Spawn one subagent (`subagent_type: general-purpose`, `model:` as resolved in step 1) with a prompt containing exactly this scope and sequence:
   - Fetch the full issue with `gh issue view <number>` and read it in full before writing any code.
   - Confirm it's actually trivial (small, mechanically obvious change). If not, stop and report back that this issue needs `/plan-tools:impl-issue` instead — do not implement it on the lite path.
   - Branch from the latest remote default branch: `git fetch origin`, detect the default branch (`gh repo view --json defaultBranchRef -q .defaultBranchRef.name` — MUST NOT assume `main`), then `git checkout -b <branch-name> origin/<default-branch>`.
   - Implement exactly what the issue describes. MUST NOT add features, refactors, or files beyond what the issue asks for.
   - Verify the work (existing tests/build pass, as applicable to this repo) before committing. Only commit once the implementation is complete — never commit partial work.
   - Include `Closes #<number>` as a trailer in the commit message — this is what binds the eventual PR to the issue so merging it auto-closes the issue.
   - Push the branch and open a PR (`gh pr create`) with a title and body summarizing the change, carrying the `Closes #<number>` line into the PR body. Follow standard PR-safety practice: this pushes to a shared remote and creates a visible artifact, so confirm branch/base and get the user's go-ahead before pushing/creating if it hasn't been established this session.
   - Stop and report back without pushing or opening a PR if any verification step fails, or if step confirms the issue isn't trivial.
   - Report back: a summary of what changed, the issue number closed, and the PR link.
4. Relay the subagent's summary to the user as-is — do not add extra commentary or next steps it didn't report.
