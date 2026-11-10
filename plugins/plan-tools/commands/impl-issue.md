---
description: Spawn a subagent to implement a GitHub issue labeled `ai` — a specific issue number, or the oldest open one if none given
argument-hint: [issue number] [model override, e.g. "opus"] [--label <name>]
---

## Task

Implement one pending residual work item, tracked as a GitHub issue labeled `ai`, then raise a PR for it.

## Steps

Labels: if `$ARGUMENTS` contains `--label <name>`, remove it from `$ARGUMENTS` before step 1 parses them and use `<name>` in place of `ai` in the issue query and pass `--label <name>` on to `finalize-pr.md` in step 3, so its follow-up issues get the same label. Without it, the label is `ai`.

1. Parse `$ARGUMENTS` for an optional issue number (bare digits or `#123`) and an optional model override (`sonnet`, `opus`, `haiku`, `fable`), in either order. Default model: `sonnet`.
2. Resolve which issue to work on:
   - If an issue number was given, use it directly — skip the query below.
   - Otherwise run: `gh issue list -R "$(gh repo view --json nameWithOwner -q .nameWithOwner)" --label ai --author "@me" --state open --json number,title,body,createdAt --limit 100 -q 'sort_by(.[], .createdAt)[0]'`. Always pass `-R` explicitly — without it, `gh issue list` can silently no-op (empty result, no error) when the repo isn't auto-detected from cwd, which reads as a false "no issues" instead of a failure.
   - MUST stop and tell the user if no issue was found — do not fall back to picking a different issue.
3. Spawn one subagent (`subagent_type: general-purpose`, `model:` as resolved in step 1) with a prompt containing exactly this scope and sequence:
   - Fetch the full issue with `gh issue view <number>` and read it in full before writing any code.
   - Branch from the latest remote default branch: `git fetch origin`, detect the default branch (`gh repo view --json defaultBranchRef -q .defaultBranchRef.name` — MUST NOT assume `main`), then `git checkout -b <branch-name> origin/<default-branch>`.
   - Judge whether the issue is trivial — a small, mechanically obvious change (a few-line fix, a single well-scoped edit where the approach is unambiguous) — or not. If it's not trivial (spans multiple files/components, involves a design or sequencing decision, or the approach isn't obvious just from reading the issue), spawn a `Plan` subagent with the issue's full contents and have it produce a step-by-step implementation plan before writing any code, then implement that plan.
   - Implement exactly what the issue describes. MUST NOT add features, refactors, or files beyond what the issue asks for.
   - Verify the work (tests/build pass, as applicable to this repo) before committing. Only commit once the implementation is complete — never commit partial work.
   - Include `Closes #<number>` as a trailer in the commit message — this is what binds the eventual PR to the issue so merging it auto-closes the issue.
   - Read and follow `${CLAUDE_PLUGIN_ROOT}/commands/finalize-pr.md` to review, test, log residual work, and raise the PR. Read that file for instructions — do not invoke `/finalize-pr` as a slash command.
   - Stop and report back without pushing or opening a PR if any verification step fails.
   - Report back: a summary of what changed, the issue number closed, and the PR link.
4. Relay the subagent's summary to the user as-is — do not add extra commentary or next steps it didn't report.
