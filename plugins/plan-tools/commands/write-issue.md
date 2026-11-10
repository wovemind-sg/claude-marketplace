---
description: Open a GitHub issue labeled `ai` for deferred work (e.g. a bug found during review but out of scope for the current PR)
argument-hint: <description of the work to do later> [--label <name>]
---

Record deferred work as a GitHub issue so it can be picked up and executed later.

Labels: if `$ARGUMENTS` contains `--label <name>`, remove it from `$ARGUMENTS` before anything else reads them and use `<name>` wherever this command says `ai` as a label (the label check, the label creation and `--label` on the issue). Without it, the label is `ai`.

Steps:

1. Ensure the `ai` label exists: `gh label list --json name -q '.[].name'`; if `ai` isn't in the list, create it (`gh label create ai --color ededed --description "Queued for autonomous implementation"`).
2. Derive a short title from "$ARGUMENTS" (e.g. "fix null check in auth middleware" → `Fix null check in auth middleware`).
3. Write a clear, self-contained issue body describing the work: what's wrong/needed, where (file/line if known), and any context from the current conversation that a future session would need to act on it without re-deriving it.
4. Create the issue: `gh issue create --title "<title>" --body-file - --label ai`, with the body on stdin through a quoted heredoc (`<<'EOF'`), so backticks and `$` in it are not run as shell.
5. Confirm the issue URL to the user.

Do not implement the work now — this command only records it for later.
