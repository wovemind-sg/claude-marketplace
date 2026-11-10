---
name: hook-finalize-pr
description: Help the user create or edit this repo's `.claude/finalize-pr.md` — the per-repo steps that `/plan-tools:finalize-pr` runs (step 3b). Use when the user wants to configure, add, change, or review repo-specific finalize-pr checks such as lint, migrations, version bumps, or changelog, or says "set up the finalize-pr hook".
argument-hint: [optional description of the steps to add]
---

Configure `.claude/finalize-pr.md` for the current repo. This file is read verbatim by a Sonnet subagent in `/plan-tools:finalize-pr` step 3b, so write it as plain instructions that agent can follow with no other context.

## How the file is used

- Location: `$(git rev-parse --show-toplevel)/.claude/finalize-pr.md`. Empty or missing = step skipped.
- Runs after the test plan and user-flows sync, before residual work and the PR.
- The PR does not exist yet on a first run: steps must not use `gh pr ...`.
- On an incremental run the agent is told the `$BASE..HEAD` range changed since the last finalize; each step says whether to scope to it or run in full.
- The agent commits its own fixes and reports what it fixed and what it found but did not fix (those become residual work).

## Procedure

1. Read the existing file if present. If it has content, show it and ask whether to add, change, or replace; never overwrite without confirmation.
2. If `$ARGUMENTS` describes the steps, use that. Otherwise inspect the repo (`Makefile`, `package.json` scripts, `pyproject.toml`, CI workflows, `migrations/`, `CHANGELOG*`, version files) and propose at most 5 candidate steps; ask which to keep.
3. Write each step as a numbered, imperative instruction with:
   - the exact command to run (verified to exist in the repo),
   - when it applies (e.g. "if `migrations/` changed in the diff"),
   - what to do on failure (fix and commit, or report only).
4. Keep steps non-interactive and idempotent. No steps that push, open or edit the PR, or need secrets.
5. Write the file (create `.claude/` if needed) and show the final content. Do not commit unless the user asks.

## Example

```markdown
1. Run `make lint` and fix what it reports. Scope to files in `git diff --name-only $BASE..HEAD` when a range is given.
2. If `migrations/` changed, check every new migration has a downgrade; fix and commit if missing.
3. If `src/` changed, bump the patch version in `pyproject.toml` once per branch (skip if already bumped vs. the base branch).
```
