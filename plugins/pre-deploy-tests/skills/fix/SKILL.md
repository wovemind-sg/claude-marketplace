---
name: fix
description: Fix the bugs marked Fix on the pre-deploy bug review page published by /pre-deploy-tests:run, one bug at a time, each in its own subagent and its own pull request — reproduce, fix, re-run the reproduction, take an "after" capture for UI bugs, finalize with /plan-tools:finalize-pr, squash auto-merge and wait for the merge with /plan-tools:monitor-pr before the next bug — and update each card's status on the page. Use whenever the user wants to fix, apply or work through the pre-deploy test bugs, "fix the bugs I marked", "go fix them", "I chose what to fix", even if they do not say "fix". Not for planning or running the tests (use /pre-deploy-tests:plan or /pre-deploy-tests:run).
argument-hint: "[artifact url]"
---

# Fix the pre-deploy bugs

Turn every bug the user marked **Fix** on the bug review page into a merged pull request, one bug per PR, in series. You are the orchestrator: subagents reproduce and fix; you choose the order, ship, wait for the merge and keep the page up to date. People decided on the page what to fix, so do not second-guess a choice; ask only where the page leaves a gap (undecided bugs, the model cap).

All paths below are relative to the repository root (`git rev-parse --show-toplevel`). Run git commands from there.

## 1. Guards and the page

- If the `plan-tools` plugin is not installed (`/plan-tools:finalize-pr` is not in the skill list), tell the user to install it (`/plugin install plan-tools@wovemind`) and wait.
- If the `model-picker` plugin is not installed (`/model-picker:pick-model` is not in the skill list), tell the user to install it (`/plugin install model-picker@wovemind`) and wait.
- **The page:** the artifact URL in `$ARGUMENTS`; else `url` in `.pre-deploy-tests/page.json`; else run Artifact `action: "list"` and take the newest artifact titled "… Pre-deploy Tests" whose `<main data-repo>` matches this repo (`gh repo view --json nameWithOwner -q .nameWithOwner`). Ask if none or several match.
- Read the page (Artifact `action: "read"`, `url`) and save its HTML as `index.html` in a scratchpad folder (`PAGE_DIR`): you republish from it in step 5. Each bug is an `<article class="bug" data-id="BUG-NNN" data-sev="...">`.
- Read the shared state with Artifact `read_db`, `db_op: "list"`, following `next_cursor` to the end: collection `choice` (doc id = bug id, `{"choice": "fix" | "skip"}`; no doc = undecided) and collection `status` (doc id = bug id, `{"status": "fixing" | "fixed" | "norepro" | "attention", "pr", "note"}`).
- **Bug records:** `.pre-deploy-tests/bugs/BUG-NNN/bug.md` (format in `${CLAUDE_PLUGIN_ROOT}/skills/run/references/bug-record.md`), its `captures/` and `repro.*`. When the folder is missing (the run happened on another machine), save the card's text from the page as `bug.md` in the same layout and fetch its script with Artifact `read_file` (`BUG-NNN/repro.<ext>`) into that folder.
- Read `.pre-deploy-tests/record.json` (`target`, `launch`, `profile.template`) and `.pre-deploy-tests/CLAUDE.md` when they exist: the subagents start the app the way they say.

## 2. Choose the bugs and the model cap

1. **Status first.** A bug with status `fixed` is done. A bug with status `fixing` was interrupted: check `gh pr list --head fix/BUG-NNN- --state all` and `git branch -a --list '*fix/BUG-NNN-*'`. An open PR resumes at step 4; a merged one is set to `fixed` with its PR link; anything else restarts at step 3.
2. **To fix:** every bug with choice `fix` and no `fixed` status. Bugs marked `norepro` or `attention` by an earlier run are tried again.
3. **Undecided** (no choice doc, not `fixed`): list them, one line each (`BUG-NNN severity title`), and ask once (AskUserQuestion): "Skip the undecided bugs" (Recommended) / "Fix them too" / "Let me choose" (then ask per bug, up to four per call). Bugs added this way get `choice: fix` written to the page so the page shows what was done.
4. **Skip:** every bug with choice `skip`. Never touch them.
5. **Model cap:** ask (AskUserQuestion) for the highest model a fix may use: Opus (Recommended), Fable, Sonnet, Haiku. Ask every run.
6. **Base branch:** `target.branch` in the record when the target was local; otherwise the repository's default branch (`gh repo view --json defaultBranchRef -q .defaultBranchRef.name`).

**Order:** severity (Blocker, Major, Minor, Cosmetic), then bug number. Print one line per bug (`BUG-NNN severity title`) and start without waiting. Nothing to fix: say so and stop.

**Launch for a fix:** a fix is proven on a local app, never on the integration environment (the fix is not deployed there). When the record's `launch` is null and the project is not a template project (no `worktree-env` target in its `Makefile`), ask once, in plain words, for the commands that start the app on a given port and database, create and migrate that database, the URL that answers when it is ready, and how a test account is made (environment variable names only), with `{port}` and `{db}` where the values go. Add the answer to `.pre-deploy-tests/CLAUDE.md`.

## Standing permissions and overrides

The user who invokes this skill grants, for its whole run: creating branches, committing, pushing, opening PRs against the base branch, editing PR bodies, enabling auto-merge, merging the base branch into a fix branch, writing `choice` and `status` on the page, and republishing the page. Do not stop to confirm these, even where a skill you call (finalize-pr's push/PR question, monitor-pr's auto-merge question or its offer to switch branches) would normally ask.

Two rules override the skills you call:

1. **No follow-up issues.** Anything a review, test plan or the fixing agent finds unresolved about this bug's change is fixed on this bug's branch. Never open a GitHub issue, never leave a "Follow-ups" section.
2. **Leave pre-existing issues alone.** Do not close, comment on or reference any GitHub issue that existed before this run.

## 3. Per bug, in order

1. **Clean tree:** `git status --porcelain` shows nothing outside `.pre-deploy-tests/`. Changes that are not yours: tell the user and wait; do not stash or discard them.
2. **Branch:** `git fetch origin <base> && git switch -c fix/BUG-NNN-<slug> origin/<base>` (`<slug>`: the title in lowercase kebab-case, at most five words).
3. **Status:** Artifact `write_db`, `db_op: "set"`, collection `status`, doc `BUG-NNN`, `{"status": "fixing", "pr": "", "note": ""}`.
4. **Model:** invoke `/model-picker:pick-model` with the bug's fix prompt (from `bug.md`) as the job. Turn the answer into the lowercase family word (haiku, sonnet, opus, fable). Model order: Haiku < Sonnet < Opus < Fable. Above the cap: the cap model with the effort one level higher (low, medium, high, xhigh, max; max stays max). Print `BUG-NNN: <model> <effort>` (add "capped from <model>" when capped).
5. **Spawn one subagent** (general-purpose, that `model` and `effort`) with this prompt, absolute paths filled in:

   ```
   You fix one bug found by pre-deploy tests, end to end, on branch fix/BUG-NNN-<slug> (already checked out, from origin/<base>).

   Bug record: <abs>/.pre-deploy-tests/bugs/BUG-NNN/bug.md. Read it in full; its "Fix prompt" section is your task. Captures and the reproduction script are in the same folder.
   Record format: ${CLAUDE_PLUGIN_ROOT}/skills/run/references/bug-record.md.
   Run the app locally, never against an integration environment: <the launch commands from .pre-deploy-tests/CLAUDE.md, with port 8199 and database pdt_fix; or "make worktree-env" for a template project; plus launch.native_build for an ios or android bug>. Test credentials are in the environment variables <names>; never print or write their values.

   1. Reproduce first, before changing any code: follow the Steps (or run the reproduction script) at the places the record lists, up to 3 times. If it does not happen even once, stop: change no code, commit nothing, and end with "NOREPRO: <what you did and saw>".
   2. Fix the root cause. Change only what this bug needs.
   3. Re-run the same reproduction at every place the record lists and confirm the Expected result. Run the project's tests that cover the changed code.
   4. UI bug (the record has captures): take an "after" capture at the same copy, size and orientation as each "before" capture, the same kind (screenshot or recording), named like it, into <abs>/.pre-deploy-tests/bugs/BUG-NNN/after/. How: the section "One screenshot or one recording outside a comparison" of ${CLAUDE_PLUGIN_ROOT}/skills/run/references/web.md (add --browser <copy> for webkit and firefox), or "iOS simulator" / "Android emulator" and "Rotation and tablets" in ${CLAUDE_PLUGIN_ROOT}/skills/run/references/native.md. Run playwright-cli from <abs scratch dir>, never the repo root.
   5. Stop the app you started. Commit with "fix: <what was wrong, in plain words>", staging explicit paths only; never add .pre-deploy-tests/.
   6. Invoke /plan-tools:finalize-pr with: "base: <base>; push and PR creation are already approved; no follow-up issues: fix every residual item on this branch; PR body includes the test plan and its results, 'Fixes BUG-NNN from the pre-deploy tests' with the bug's title and the page link <url>". Do each of its steps yourself instead of spawning agents.
   Do not merge the PR. End with one line: "PR: <url>", or "NOREPRO: <reason>", or "STUCK: <what failed>".
   ```

6. **Act on the last line:**
   - `PR: <url>` → step 4.
   - `NOREPRO: <reason>` → status `{"status": "norepro", "pr": "", "note": "<reason>"}`; `git switch <base>`, delete the branch; next bug.
   - `STUCK: <reason>`, or no such line → status `attention` with the reason; `git switch <base>`, keep the branch; next bug.

## 4. Merge

1. `gh pr merge <pr> --auto --squash`. If the repository does not allow auto-merge, status `attention` ("auto-merge is off") with the PR link, and go to step 6.
2. Invoke `/plan-tools:monitor-pr <pr>` and follow it until the PR merges. Where monitor-pr would stop and wait for the user (the same check failing three times, the PR closed, a conflict needing a product decision, still open after six hours because a review never came), do not wait: set status `attention` with that reason and the PR link, and go to step 6. Leave the PR open.
3. Merged → step 5. The next bug starts only after this merge, so its branch contains this fix.

## 5. Close out the bug

1. Status `{"status": "fixed", "pr": "<url>", "note": ""}`.
2. **"After" captures** (UI bugs with files in `.pre-deploy-tests/bugs/BUG-NNN/after/`): in `PAGE_DIR/index.html`, inside that bug's `<section class="blk after" hidden><div class="media">`, add one `<figure>` per file, as the card's "before" figures are written: `<img src="BUG-NNN/after/<file>" alt="..." loading="lazy">` for a screenshot, `<video src="BUG-NNN/after/<file>" controls muted playsinline preload="metadata"></video>` for a recording, and a `<figcaption>` (copy, size, orientation: what it shows now). Leave `hidden` as it is: the page shows the section once it holds a figure. Escape `&`, `<` and `>` in text.
3. Republish: run Artifact `action: "list_files"` with the page `url` first, then publish `file_path` `PAGE_DIR/index.html` to that `url`, `icon` `bug`, `files` mapping each `BUG-NNN/after/<file>` to its local file, and the same capabilities the run skill published:

   ```json
   {"db":{"rules":[{"path":"choice","read":"view","write":"admin"},{"path":"status","read":"view","write":"admin"}]},"user":{}}
   ```

   Files left out of the map stay published, and the shared choices and statuses stay. If the publish is refused because the page changed since you read it, merge your figures into the version it returns and publish that.
4. Go back to base: `git switch <base> && git pull`, and delete the local fix branch.

## 6. After a stuck bug

Back to base (`git switch <base>`) and go on with the next bug. A bug left in `attention` keeps its branch and PR; the next run tries it again.

## 7. Report

End with:

- fixed: `BUG-NNN title: PR url`;
- not reproduced: `BUG-NNN title: reason`;
- needs attention: `BUG-NNN title: reason, PR url if any`;
- skipped: the bugs marked Skip, and undecided ones left out;
- the page link.

Say that a new `/pre-deploy-tests:plan` re-tests the fixed bugs.
