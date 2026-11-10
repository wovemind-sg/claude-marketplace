---
name: apply
description: Implement the fixes from a published compliance-audit Artifact report, card by card, end to end — reads every card not marked Done or Won't fix plus the planning answers saved on the page, orders the cards by dependency (legal documents last), then for each card plans with an Opus subagent, splits the plan, implements with Sonnet subagents, finalizes and raises a PR against the base branch, sets squash auto-merge and waits for the merge before starting the next card. Use whenever the user wants to apply, implement, fix, execute or work through the compliance audit findings, cards or report — "apply the audit", "fix the compliance cards", "implement the legal changes", "I answered the questions, go" — even if they do not say "apply". Not for running the audit itself (use audit).
argument-hint: "[artifact url] [--planner opus] [--implementer sonnet] [--base <branch>]"
---

Implement every open card of a compliance-audit report, one card per PR, in dependency order, without supervision.

The user has already answered the planning questions on the report page. Your job is to turn each card into a merged PR. You are the orchestrator: subagents plan and write code; you sequence, ask, ship and wait. Work autonomously. The only things you bring to the user are (a) planning questions their saved answers do not cover, and (b) being stuck (see **Stuck**).

## Arguments

Parse `$ARGUMENTS`:

| Argument | Default | Meaning |
|---|---|---|
| artifact URL | found via Artifact `action: "list"`: the newest "… Compliance Audit" artifact whose `data-repo` matches this repo; ask if none or several match | the report to apply |
| `--planner <model>` | `opus` | model for planning subagents |
| `--implementer <model>` | `sonnet` | model for implementing, review, test and merge-conflict subagents |
| `--base <branch>` | the plugin setting `default_base_branch` (`${user_config.default_base_branch}`); when that is empty or still contains the text `user_config`, the repository's default branch (`gh repo view --json defaultBranchRef -q .defaultBranchRef.name`) | PR base branch; every card branches from it and merges into it |

Run from the root of the audited repo. All paths below are relative to `${CLAUDE_PLUGIN_ROOT}/skills/apply/`.

## Standing permissions and overrides

The user who invokes this skill grants, for its whole run: creating branches, committing, pushing, opening PRs against `--base`, editing PR bodies, enabling auto-merge, merging `--base` into the card branch, and updating card statuses on the report. Do not stop to confirm these, even where a called skill (e.g. `finalize-pr` step 5) would normally ask.

Two rules override the skills you call:

1. **No follow-up issues.** Anything unresolved that a review, test plan or implementer surfaces about this card's change gets fixed on this card's branch — spawn another implementer subagent, add sessions if needed. Never run `write-issue`, never open a GitHub issue, never leave a "Follow-ups" section.
2. **Leave pre-existing issues alone.** Do not implement, close, comment on, or reference (`Closes #…`) any GitHub issue that existed before this run, even if related. Problems that predate this card and are not caused or touched by it stay out of the PR.

## Step 1 — Load the cards

1. Read the artifact (`Artifact action: "read"`). Save the HTML to your scratchpad and run:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/apply/scripts/parse_cards.py <scratch>/report.html > <scratch>/cards.json
   ```
   Each card has `id` (the #N shown on the page), `sid` (title slug, the db key), `severity`, `risk`, `title`, `sections` (Rule, What the rule says, What we found, What to do, Owner) and `questions`.
2. Read the page's shared state with `ArtifactData` (load it via ToolSearch if deferred): `list` the `status` collection (doc id = `sid`, field `s`: `prog` / `done` / `wont`) and the `answers` collection (doc id = `<sid>--<question index>`, field `t`).
3. Keep every card whose status is not `done` or `wont`. Attach each card's answers to its questions by index; a question with no answer is **open**.
4. Cards already `prog`: check for an existing branch or PR named `compliance/<id>-*` (`gh pr list --head …`, `git branch -a`). If a PR is open, resume that card at Step 3.7; if merged, mark it `done` and drop it; otherwise restart it from Step 3.1.

## Step 2 — Order the cards

Build a dependency graph and topologically sort it. A card depends on another when its fix needs the other's result to exist or to be described truthfully. Typical edges:

- **Legal documents last.** Privacy policy, terms/EULA, cookie policy, DPA, sub-processor list, imprint, accessibility statement and store privacy labels describe what the product does, so they depend on every card that changes data collection, retention, consent, deletion, vendors, AI or payments.
- Data-model, auth and security foundations before features built on them (e.g. account-deletion backend before the in-app delete button, consent storage before gating analytics on consent).
- Store-console and registration cards (owner founder only) after the code they declare.

Ties break by risk (high first), then card id. Owner-only cards whose fix lies entirely outside the repo (a console setting, a registration, a lawyer review) cannot be implemented — set them aside for the final report; do not plan or mark them. Cards with a mixed owner: implement the repo part, list the rest in the PR body.

Print the order as one line per card (`#id title — depends on #x, #y`), then start without waiting.

## Step 3 — For each card, in order

Before each card: working tree clean (if not and the changes are not yours, that is **Stuck**), then
```bash
git fetch origin <base> && git switch -c compliance/<id>-<sid> origin/<base>
```
Set the card's status to `prog` (ArtifactData `set`, collection `status`, doc `sid`, data `{"s":"prog"}`).

### 3.1 Plan — `--planner` subagent

Spawn one Agent (`model: <planner>`, general-purpose). You decide nothing about the fix yourself; the planner reads the code and writes the plan; the user's answers decide every choice. Give the planner:

- the full card (all sections), the answered questions with their answers, and the open questions;
- the repo path and base branch;
- this instruction: *"Write a concrete implementation plan for this compliance fix in this repo: files to change, data/migration steps, UI copy, tests, and how to verify. Base every decision on the card and the user's answers. Do not decide anything the answers do not settle — product choices, legal wording, retention periods, vendor choices, UX, who is affected, anything with more than one reasonable answer. List each such decision as a question with 2–4 concrete options instead. Return: the plan (with placeholders where a question is pending) and the list of questions."*

If questions come back (plus any open card questions the plan actually depends on), ask the user with AskUserQuestion — up to 4 per call, concrete options, recommended option first only when the code or answers point to it. Send the answers back to the same planner (SendMessage) and repeat until it returns a plan with no open questions. Never fill a gap with your own judgment to keep moving; waiting for the user here is expected.

Write the final plan to `.planning/SPEC.md`. Check that `.planning/` is gitignored; if not, keep it out of commits (`git add` explicit paths only).

### 3.2 Split — `/plan-tools:split-plan`

Invoke `plan-tools:split-plan` on `.planning/SPEC.md`. Do not wait for the user to review the session list. If it reports the plan fits one session, it writes no session files — go to 3.3 single-session.

### 3.3 Implement — `--implementer` subagents

- **Split:** invoke `plan-tools:plan-split-implment`, telling it to use `model: <implementer>` for each session subagent and that the branch already exists. If its blocker check returns a checklist that needs the user's own credentials or console access, that is **Stuck**.
- **Single session:** spawn one Agent (`model: <implementer>`) with the plan: implement it exactly, run the relevant tests, commit, and report what it did and anything unresolved.

### 3.4 Absorb discovered work

Whatever the implementers report as unresolved, broken, or "should also be fixed" for this change: fix it now on this branch with another implementer subagent (append a session to `.planning/sessions/` if the plan was split). This is rule 1 — nothing becomes a follow-up. Pre-existing, unrelated issues stay untouched (rule 2).

### 3.5 Finalize and raise the PR — `/plan-tools:finalize-pr`

Invoke `plan-tools:finalize-pr` with args: `base: <base>; use model <implementer> for subagents; no follow-up issues — fix every residual item on this branch (skip step 4, loop back to an implementer instead); permission to push and create the PR is already granted; PR body must include the test plan and its results`.

- The test plan runs **once**, inside finalize-pr. Do not run it again later (not after residual fixes, not after base merges).
- After the PR exists, make sure its body has a **Test plan** section listing each check and its result (pass / fixed / not run + why). If finalize-pr's body lacks it, add it with `gh pr edit <pr> --body-file <file>`. Also include: `Compliance audit card #<id>: <title>`, the rule, and any part of the card left to the founder or lawyer.
- PR base must be `<base>` (`gh pr create --base <base>`); fix with `gh pr edit --base <base>` if wrong.

### 3.6 Auto-merge

```bash
gh pr merge <pr> --auto --squash
```
If the repo does not allow auto-merge, that is **Stuck**.

### 3.7 Wait for the merge

Run the bundled poller in the background (Bash `run_in_background: true`) and act on its exit code when it finishes:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/apply/scripts/wait_pr.sh <pr> 60 6
```

| Exit | Meaning | Action |
|---|---|---|
| 0 | merged | go to 3.8 |
| 10 | `BEHIND` or `DIRTY` — other collaborators moved `<base>` | `git fetch origin <base> && git merge origin/<base>`; on conflicts spawn an implementer subagent to resolve them keeping both sides' intent; push; rerun the poller. Expect this several times per PR. |
| 30 | a check failed | read the failing job log (`gh run view --log-failed`), spawn an implementer subagent to fix, push, rerun the poller. Third failure on the same check → **Stuck**. |
| 20 | closed without merging | **Stuck** |
| 40 | still open after 6 h (usually a required review) | **Stuck**; keep polling after notifying |

### 3.8 Close out the card

Set the card's status to `done` (`{"s":"done"}`), archive `.planning/` as plan-split-implment describes (if it did not already), `git switch <base> && git pull`, delete the local card branch, and continue with the next card in the order.

## Stuck

Stuck means you cannot make progress without the user and it is not a planning question: auto-merge disabled, PR closed, the same check failing three times, a conflict you cannot resolve without a product decision, credentials or console access needed, a dirty working tree that is not yours, a tool erroring repeatedly. Then:

1. Invoke `ntfy:notify-me` with `now — compliance apply stuck on card #<id>: <one-line reason> (priority 4)`.
2. Tell the user in chat what is blocked and what you need, and wait. Do not skip ahead to the next card — later cards may depend on this one.

## Final report

When every card is merged (or set aside), reply with:

- merged cards: `#id title — PR url`;
- cards set aside because their fix is outside the repo, each with the owner and the exact action left (from "What to do");
- parts of merged cards left to the founder or lawyer.
