---
description: One-off migration — convert old-format .planning/residual/*.md files into `ai`-labeled GitHub issues, then delete the files
---

Migrate residual work from the old file-based format (`.planning/residual/<N>_*.md`) to the new GitHub-issue format used by `/plan-tools:write-issue` and `/plan-tools:impl-issue`.

Steps:

1. List `.planning/residual/*.md`. If none exist, tell the user and stop.
2. Ensure the `ai` label exists: `gh label list --json name -q '.[].name'`; if `ai` isn't in the list, create it (`gh label create ai --color ededed --description "Queued for autonomous implementation"`).
3. For each file, oldest (`<N>_*.md`) first:
   - Read its full contents.
   - Derive a title from the filename or the file's first line (e.g. `fix-null-check-auth-middleware` → `Fix null check in auth middleware`).
   - Create the issue: `gh issue create --title "<title>" --body "<file contents>" --label ai`.
   - Delete the file once the issue is created successfully.
4. Report to the user: how many issues were created (with URLs), and confirm `.planning/residual/` is now empty (remove the directory if empty).
