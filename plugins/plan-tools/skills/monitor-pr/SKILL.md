---
name: monitor-pr
description: Babysit an open GitHub pull request until it is merged — poll its status in the background, fix and push when CI checks fail, and merge the base branch in (resolving conflicts) and push when the base branch moves. Use whenever the user wants a PR to land, says "watch this PR", "monitor PR #123", "babysit the PR", "keep the PR green", "make sure this merges", "get this PR over the line", or asks to be told when a PR merges — even if they don't say "monitor".
argument-hint: <pr-number-or-url> (defaults to the current branch's PR)
---

Drive one pull request to merged. You watch it, and whenever it needs a hand — a failing check, or a base branch that moved on — you fix that, push, and go back to watching. You never merge it yourself and never force-push: the goal is to land the PR the reviewers approved, not a rewritten one.

## 1. Set up

1. Resolve the PR: `$ARGUMENTS` if given, else `gh pr view --json number`. Read `gh pr view <pr> --json number,url,headRefName,baseRefName,isCrossRepository,autoMergeRequest,reviewDecision,state`.
   - Already `MERGED` → say so and stop. `CLOSED` → **Stuck**.
   - `isCrossRepository: true` (a fork) → you likely cannot push to its branch; **Stuck** unless `gh pr checkout` + a dry-run push proves otherwise.
2. The working tree must be clean (`git status --porcelain` empty). If it isn't, it is the user's work — don't stash or discard it; **Stuck**.
3. `gh pr checkout <pr>`, then `git pull --ff-only` so you start from the pushed head.
4. If `autoMergeRequest` is null, nothing will merge the PR once it goes green, and polling would just run out the clock. Tell the user and ask whether to enable it (`gh pr merge <pr> --auto` with the repo's usual method — `--squash`/`--merge`/`--rebase`; check `gh repo view --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed` and ask if more than one is allowed) or whether they will merge by hand. Either answer is fine — keep monitoring.
5. Check whether the base branch requires the `finalize-pr` status (set by `/plan-tools:finalize-pr`):
   ```bash
   gh api "repos/{owner}/{repo}/rules/branches/<base>" \
     -q '[.[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context] | index("finalize-pr")'
   gh api "repos/{owner}/{repo}/branches/<base>/protection/required_status_checks" -q '.contexts | index("finalize-pr")' 2>/dev/null
   ```
   Either printing a number means it's required: pass `finalize-pr` as the poller's 4th argument below. Otherwise omit it.

## 2. Poll

Run the poller **in the background** (it sleeps between polls; you get re-invoked when it exits):

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/monitor-pr/scripts/wait_pr.sh <pr> 60 6 [finalize-pr]
```

| Exit | Meaning | Action |
|---|---|---|
| 0 | merged | **Done** |
| 10 | `BEHIND` or `DIRTY` — base branch moved on | **Sync with base** |
| 30 | a check failed (names on stdout) | **Fix the check** |
| 50 | head commit has no successful `finalize-pr` status | **Run finalize-pr** |
| 20 | closed without merging | **Stuck** |
| 40 | still open after 6 h — usually waiting on a review | Tell the user what it's waiting on (`reviewDecision`, pending checks), then rerun the poller |

After every push, rerun the poller. Expect several rounds on a busy repo.

## 3. Sync with base

Merge, don't rebase: a merge keeps the pushed history intact, so no force-push and no invalidated review comments.

1. `git fetch origin <base> && git merge origin/<base>` (on the PR branch).
2. No conflicts → run the project's fast checks (lint/typecheck/unit tests, whatever CI runs that is cheap locally) so you don't push a merge that is semantically broken, then `git push`.
3. Conflicts → resolve them so **both sides' intent survives**. Read each conflicting hunk with the commits that produced it on each side (`git log origin/<base> -- <file>`, the PR's own diff) — a resolution that silently drops the base branch's change is the worst outcome here, because it reverts someone else's merged work under a "merge" commit nobody reviews closely. For big or multi-file conflicts, delegate to a subagent with that same instruction. If a conflict needs a product decision (both sides changed the same behavior in incompatible ways), `git merge --abort` and go **Stuck** — describe both sides.
4. Commit the merge with git's default message, run the fast checks, push.

## 4. Fix the check

1. Find the failing run: `gh pr checks <pr>` and `gh run view <run-id> --log-failed` (trim to the decisive lines).
2. Decide what kind of failure it is:
   - **Caused by the PR or the merged base** → fix the root cause in code. Don't skip, mark `xfail`, loosen assertions or disable the check to make it pass — that lands a PR that only *looks* green.
   - **Flaky / infrastructure** (network timeout, runner died, cancelled, unrelated test that passes locally) → `gh run rerun <run-id> --failed` once instead of changing code.
   - **Needs a secret, permission or config you can't change** → **Stuck**.
3. Reproduce locally where possible, fix, run the same check locally, commit (`fix: <what>`, semantic format), push. Spawn a subagent for non-trivial fixes so this session's context stays on monitoring.
4. Count attempts per check. The **third** failure of the same check → **Stuck**; you're likely going in circles.

## 5. Run finalize-pr

The PR is waiting on the `finalize-pr` status — typically because new commits (yours or someone else's) landed after the last finalize run.

1. Make sure you're on the PR branch with a clean tree, then `git pull --ff-only`.
2. Invoke `/plan-tools:finalize-pr`. The PR already exists, so it does an incremental run over the commits since the last finalized one and pushes any fixes to this PR. Pushing to this PR's branch is already established by monitoring it — don't re-ask.
3. When it finishes, verify the status is on the **pushed** head:
   ```bash
   git fetch -q origin && [ "$(git rev-parse HEAD)" = "$(git rev-parse @{u})" ] && \
   gh api "repos/{owner}/{repo}/commits/$(git rev-parse HEAD)/statuses" \
     -q '[.[] | select(.context=="finalize-pr" and .state=="success")] | length'
   ```
   - `0` and finalize-pr completed its steps (review, test plan, residual work, PR updated) → set it yourself: `gh api repos/{owner}/{repo}/statuses/$(git rev-parse HEAD) -f state=success -f context=finalize-pr -f description="finalize-pr ran"`.
   - finalize-pr stopped short (unresolved failure, needed a decision) → **Stuck**; don't set the status by hand.
4. Count runs per head SHA. finalize-pr exiting without leaving the status twice on the same head → **Stuck**.

## 6. Stuck

You can't make progress without the user: PR closed, fork you can't push to, dirty tree, a conflict needing a product decision, a check failing three times, missing credentials or permissions, `gh` erroring repeatedly. Tell the user in one short block: what's blocked, what you tried, what you need. Then wait. If the user asked to be notified (or `ntfy`/`desktop-notify` skills are what they normally use), invoke that too.

## 7. Done

When the poller exits 0, report in a few lines: PR URL, merged, and what you did along the way (base merges, check fixes with commit SHAs, reruns, finalize-pr runs). Then offer to switch back to the base branch and pull — don't do it unasked.
