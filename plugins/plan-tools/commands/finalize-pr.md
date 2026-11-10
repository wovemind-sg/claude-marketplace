---
description: Ask every question up front, then run code review with fixes, a security review when the diff is security-relevant, a test plan, residual work and the PR, unattended
argument-hint: [optional extra context for the review/PR, e.g. target branch]
---

Finalize the current branch's work into a PR-ready state, then open the PR.

Steps:

0. **Find the last finalized commit.** If a PR already exists for this branch, look for the newest commit on it that a previous run marked (step 7):
   ```bash
   BASE=""
   if gh pr view --json number >/dev/null 2>&1; then
     git fetch -q origin
     for sha in $(git rev-list "origin/$(gh pr view --json baseRefName -q .baseRefName)..HEAD"); do
       if gh api "repos/{owner}/{repo}/commits/$sha/statuses" \
            -q '.[] | select(.context=="finalize-pr" and .state=="success") | .id' | grep -q .; then
         BASE=$sha; break
       fi
     done
   fi
   ```
   `git rev-list` only walks commits in HEAD's history, so a marked commit dropped by a rebase/force-push is never picked. If `BASE` equals `HEAD`, nothing changed since the last run — tell the user and stop. If `BASE` is set, this is an **incremental run**: steps 1, 1b, 2 and 5 cover only `git diff $BASE..HEAD` (step 6 picks its own scope). If `BASE` is empty, do a full run.

0b. **Ask everything up front.** Why: after this step the run must reach the PR without stopping. Use one `AskUserQuestion` call, plus a second only for custom audit settings. Skip any question the caller, `$ARGUMENTS` or this session already answered. When `AskUserQuestion` is unavailable (unattended, e.g. `drain-issues`), ask nothing, skip the UI audit, and treat push/PR permission as the caller's.
   - **Push/PR go-ahead**: show the branch and base; this replaces the confirm in step 5. A "No" (from the user, or passed by the caller) means: run everything up to and including step 4 (commits stay local), skip steps 5–7, and go to step 8, reporting that the branch is ready but not pushed.
   - **UI audit**: ask only if the `ui-audit` plugin is installed (`/ui-audit:capture` is in the skill list) and the diff touches UI files. Detect UI by looking at the files changed since the last audited commit, using the same order `/ui-audit:capture` uses for its scope: the newest PR commit with a successful `ui-audit` commit status, else `last_audited_sha` in `.ui-audit/manifest.json` if it is an ancestor of HEAD, else the merge-base with the base branch. Before the PR exists, the base is the one named in `$ARGUMENTS` (`BASE_ARG`), else the repo default branch:
   ```bash
   git fetch -q origin
   PR_BASE=$(gh pr view --json baseRefName -q .baseRefName 2>/dev/null || echo "${BASE_ARG:-$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)}")
   AUDIT_BASE=""
   for sha in $(git rev-list "origin/$PR_BASE..HEAD"); do
     if gh api "repos/{owner}/{repo}/commits/$sha/statuses" \
          -q '.[] | select(.context=="ui-audit" and .state=="success") | .id' | grep -q .; then
       AUDIT_BASE=$sha; break
     fi
   done
   if [ -z "$AUDIT_BASE" ] && [ -f .ui-audit/manifest.json ]; then
     M=$(python3 -c "import json;print(json.load(open('.ui-audit/manifest.json')).get('last_audited_sha') or '')")
     [ -n "$M" ] && git merge-base --is-ancestor "$M" HEAD 2>/dev/null && AUDIT_BASE=$M
   fi
   [ -z "$AUDIT_BASE" ] && AUDIT_BASE=$(git merge-base HEAD "origin/$PR_BASE")
   git diff --name-only "$AUDIT_BASE..HEAD"
   ```
     UI files are templates, components, screens, stylesheets, design tokens, front-end JS/TS, and native UI (SwiftUI/UIKit, Compose, Flutter, React Native screens). If `AUDIT_BASE` equals `HEAD`, or none of the changed files is a UI file, skip the question. Otherwise ask "Run the UI audit after the PR is raised? It captures screenshots and publishes as a Claude artifact or to Cloudflare Pages." Options: `Yes, config defaults` (Recommended) / `Yes, choose settings` / `No`. If `.ui-audit/config.json` is missing, say in the option text that the first run builds the config from defaults and captures every screen.
   - **Choose settings** opens the second call: baseline mode (`base+head`, `head-only`, `head+base-related`), publish target (`artifact`, `cloudflare`), platforms (only if more than one is enabled in the config) and themes (`light`, `light+dark`; only if the config has a `dark_mode` object). Keep the answers for step 6.

1. **Review + fix.** Spawn an agent (subagent_type: general-purpose, model: sonnet) with a prompt that:
   - Instructs it to run `/code-review high --fix` (invoke the `code-review` skill with the level `high` first, then the `--fix` flag) on the current diff/branch — or, on an incremental run, only on `git diff $BASE..HEAD` (it may read whole files for context, but reports and fixes only findings in that diff).
   - Instructs it to apply all findings it fixes, and to report back: what was fixed, and any findings it did NOT fix (with reason — e.g. out of scope, needs a design decision, low confidence).
   - Pass along "$ARGUMENTS" as extra context if provided. If "$ARGUMENTS" names a review level (`low|medium|high|xhigh|max`), use that level instead of `high`. Always pass a level explicitly — never rely on the code-review skill's remembered last level.

1b. **Security review.** Run when the diff (`$BASE..HEAD` on an incremental run) touches auth, sessions or permissions; request input (forms, params, bodies, uploads); DB queries; shell or subprocess calls; file paths; outbound HTTP, webhooks or redirects; templates that render user data; crypto, tokens or secrets; CORS, CSP or cookie config; or dependency manifests. `$ARGUMENTS` containing "security" forces it. Skip with a one-line note for docs-, tests- or styles-only diffs. It runs after step 1 so it reviews the final code, and before step 2 so its fixes get tested. Spawn an agent (subagent_type: general-purpose, model: sonnet) with a prompt that:
   - Instructs it to invoke `/security-review` on the diff (on an incremental run, only `git diff $BASE..HEAD`; also include uncommitted working-tree changes from step 1 via `git diff HEAD`; it may read whole files for context).
   - Instructs it to fix every high-confidence finding, commit the fixes, and report back: what it fixed, and any findings it did NOT fix (with reason — e.g. low confidence, needs a design decision).

2. **Test plan.** Once step 1b finishes (or is skipped), spawn an agent (subagent_type: general-purpose, model: sonnet) with a prompt that:
   - Points it at the current diff/branch (on an incremental run, `git diff $BASE..HEAD`) and the fixes applied in steps 1 and 1b.
   - Instructs it to write a concrete test plan covering the changed behavior (happy path + edge cases), execute it (run existing tests, add missing ones, exercise the feature per project conventions — e.g. via the `run` skill if this is a UI/app change), and fix anything it finds broken.
   - Instructs it to report back: the test plan, results, what it fixed, and anything it found but did NOT fix (with reason).

3. **Update user flows.** If `user-flows.md` exists at the repository root, invoke `/user-flows:update-user-flows` to sync it with the changes made in steps 1–2, then commit the result. Skip this step if the file doesn't exist.

3b. **Repo steps.** If `.claude/finalize-pr.md` exists at the repository root (`git rev-parse --show-toplevel`) and is not empty, spawn an agent (subagent_type: general-purpose, model: sonnet) with a prompt that:
   - Includes the file's contents verbatim and instructs it to carry out every step in it, in order, on the current branch.
   - On an incremental run, tells it the range `git diff $BASE..HEAD` changed since the last finalize; each repo step decides whether to scope to that range or run in full.
   - Instructs it to commit any fixes it makes, and report back what each step did, what it fixed, and anything it found but did NOT fix (with reason).

   The PR does not exist yet on a first run, so repo steps must not depend on it. Skip this step if the file doesn't exist or is empty.

4. **Residual work.** Collect the unresolved items reported by steps 1, 1b, 2 and 3b (findings not fixed, test-plan gaps not addressed) and size each distinct action item:
   - **Small–medium** (a contained fix: a few files, no open design decision, roughly under half a day): fix it. Spawn one agent per item (subagent_type: general-purpose, model: sonnet), **sequentially** since they share the working tree, instructing it to implement the fix, run the relevant tests, commit, and report back what it changed — or why it couldn't, in which case treat the item as big.
   - **Big** (needs a design decision, spans several subsystems, or is substantial new work well beyond this PR's scope): invoke `/plan-tools:write-issue <description>` once — one GitHub issue (labeled `ai`) per item.

   If there are no unresolved items, skip this step.

5. **Raise the PR.** Skip steps 5–7 if the push/PR answer in 0b is "No". First, if the plugin setting `designer_ui_review` (`${user_config.designer_ui_review}`) is `true` and the `ui-change-guard` plugin is installed, invoke `/ui-change-guard:review-ui-change` (on an incremental run, scoped to the changes since `$BASE`) and resolve what it flags before continuing. If its final verdict is still UNSAFE or NEEDS ENGINEER REVIEW, run `gh pr edit <number> --add-label ui-risky` once the PR exists. On an incremental run the PR already exists: push the new commits and update its body with `gh pr edit` (add new follow-ups) instead of creating it. Otherwise confirm the working tree is clean (everything committed) and the branch is pushed, then open a pull request (`gh pr create`) with a title and body summarizing the change. List any issues opened in step 4 under a "Follow-ups" section in the PR body (e.g. `Follow-up: #<number>`) so they're visible to reviewers. If this branch's commits close an `ai` issue (a `Closes #<number>` trailer from `/plan-tools:impl-issue`), make sure that line is carried into the PR body so GitHub links and auto-closes it on merge. This pushes to a shared remote and creates a visible artifact, so confirm branch/base and get the user's go-ahead only if step 0b did not already settle it.

6. **UI audit.** Skip with a one-line note if the UI-audit answer is `No` or absent. The answer is the 0b answer or one the caller passed (e.g. `plan-implement-complete`, whose `Yes` counts even though 0b asked nothing); it is absent when the plugin is missing, the run is unattended with no caller answer, or 0b found no UI files and the caller gave none. Don't ask again: use that answer. Re-run the step 0b detection block as is now that the PR exists (`gh pr view` gives the real base). If it finds no UI files at HEAD, skip with a one-line note. If an answer was collected (0b or the caller, `Yes`), run the audit whenever UI files are found, regardless of when they appeared (fixes included). If no answer was ever collected and UI files appear now, skip and suggest `/ui-audit:capture` in the report. Otherwise the PR exists at this point (step 5), so invoke `/ui-audit:capture --pr <number> --unattended`, plus `--baseline`, `--publish`, `--platforms` and `--themes` for each setting chosen under "Choose settings"; it does its own scope selection, so do not pass `$BASE`. Keep the returned audit URL, its password if it gave one (private-repo Cloudflare audit), and its counts (changed, unintended, needs review). Then:
   - Commit any `.ui-audit/` config/manifest changes the skill left in the working tree (never images), push, and if the skill recorded a `ui-audit` commit status re-record it on the new HEAD with `gh api repos/{owner}/{repo}/statuses/$(git rev-parse HEAD) -f state=success -f context=ui-audit -f description="<description>" -f target_url=<audit url>`, copying the existing status's `description` verbatim (it may carry the password) and its `target_url` (the next audit finds the earlier audit through it).
   - Add or replace an "UI audit" section in the PR body with `gh pr edit`: the latest audit link, a `Password: \`<password>\`` line when there is one, and counts, followed by a "History" list with one line per audited commit (`- <short sha>: <url> (N changed, M unintended)`). On an incremental run keep the existing history lines and add the new one at the top.
   - If the audit was declined or could not publish (neither target could publish), say so in the section only when it produced a local `report.md`; otherwise leave the body unchanged and mention it in the report.

7. **Mark the PR as finalized.** Once the PR is raised, the test plan has fully run, and no fixes remain to apply, add a commit status recording that this skill ran:
   ```bash
   gh api repos/{owner}/{repo}/statuses/$(git rev-parse HEAD) \
     -f state=success -f context=finalize-pr -f description="finalize-pr ran"
   ```

8. **Report back.** Summarize to the user in one pass:
   - What `/code-review --fix` fixed, and what it left (with reasons).
   - The security review: what it fixed and deferred, or why it was skipped.
   - The test plan, what passed, what was fixed.
   - Whether user flows were synced.
   - What the repo steps (`.claude/finalize-pr.md`) did, or that none exist.
   - Which residual items were fixed in step 4, and which follow-up issues were opened (URLs).
   - The UI audit URL, its password if any, and counts (or why it was skipped).
   - The PR URL, or that the branch is ready but not pushed (push/PR answer "No").
