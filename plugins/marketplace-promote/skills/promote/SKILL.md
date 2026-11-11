---
name: promote
description: Use when the user wants to list, submit or promote a Claude Code plugin marketplace in plugin directories and awesome lists, or to check which directories already list it, what blocks a submission and what is pending. Runs pre-flight checks, opens PRs and issues through gh, drives web submission forms up to the final submit, and publishes a status report.
argument-hint: "[repo path] [--check]"
---

# Promote a plugin marketplace

Gets the marketplace repository at `[repo path]` (default: the current directory) listed in plugin directories. With `--check`, run pre-flight only: create nothing anywhere, publish the report and stop.

Rules for the whole run:
- Never put tokens, cookies or passwords in a command, log, state file or report. The owner signs in to websites themselves in the headed browser.
- Never submit anything that is in the state file or already open (`pending`). Skip `listed`, `pending`, `closed`, `blocked` and `not-yet-eligible` directories, but show them in the report.
- Rules per directory live in `${CLAUDE_PLUGIN_ROOT}/skills/promote/directories.json`. Do not hard-code any owner, repo or plugin name in commands.
- Write all report text in normal English, whatever style the chat uses.

## 1. Pre-flight

```bash
STATE="${CLAUDE_PLUGIN_DATA}/<owner>-<repo>.json"
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/promote/scripts/preflight.py" "<repo path>" --state "$STATE" --json
```

`<owner>-<repo>` comes from the `repo` object in the output (run once without `--state` if you need it first). If `CLAUDE_PLUGIN_DATA` is empty, use a scratch directory and tell the owner the state will not survive.

Output: `repo` {owner, repo, url, created_at, stars, problems[]}, `directories[]` {id, name, channel, target, status, problems[], links[], eligible_from?}, `plugins[]` {name, path, problems[]}. A problem is {plugin, file, rule, fix}. Status is one of `listed`, `pending`, `ready`, `blocked`, `closed`, `not-yet-eligible`.

For per-plugin directories (`aitmpl`, `anthropic`) a `ready` status can still carry problems: those plugins are named in `problems[].plugin`. Skip exactly those plugins for that directory and report each problem with its fix.

State file shape: `{"submissions": {"<directory id>": [{"url": "...", "plugin": "..."}]}, "artifact_url": "..."}`. Create or update it with a small `python3 -I -c` snippet. Write it right after each PR or issue is created and after each confirmed web submit, so an interrupted run never duplicates.

If `--check` was given, go to step 6.

## 2. Pick what to submit

Directories with status `ready`, by channel: `pr` (composio, aitmpl), `issue+pr` (tonsofskills), `web` (anthropic, claudemarketplaces, claudepluginhub), `human-link` (awesome-claude-code, only when eligible).

## 3. Draft PRs and issues

Entry text comes from `.claude-plugin/marketplace.json` (marketplace description, each plugin's description), trimmed to the directory's limits. Fork each target repository with `gh repo fork --clone` into a scratch directory, never into the owner's repo.

- composio: one link line in the best-fit category section of `README.md`. Read the file, choose the category by the plugins' descriptions, copy the style of the neighbouring lines.
- aitmpl: one PR per plugin (`one_component_per_pr`). Create `cli-tool/components/plugins/<category>/<name>/source.json` with `repo`, `path`, `commit`, `license`, `author` (see `directories.json`). `commit` is the 40-character `git rev-parse HEAD` of the pushed default branch (check `git status` and `git log origin/HEAD..` first; if the work is not pushed, stop and say so). `license` must match the LICENSE at that commit. Never commit `docs/components.json` or `dashboard/public/`.
- tonsofskills: first an issue from template `plugin-submission.yml`, then a PR adding one entry to `sources.yaml` that references the issue. State in both that the submission was prepared with AI assistance.

Ask the owner once with AskUserQuestion, all in one round:
1. Approve or edit all drafts (show them in full).
2. Which aitmpl plugins to submit (suggest 3; later runs offer the rest).
3. Which Anthropic directory plugins to submit (at most 10 per 24 hours, only ones not already in the state file).

Then for each approved item: branch, commit, `gh pr create` or `gh issue create`, and record the URL in the state file immediately.

## 4. Web forms

Follow `references/web-forms.md` for each `web` directory with `playwright-cli` (headed, its own profile, one session per directory, run from a scratch directory so `.playwright-cli/` stays out of the repo). If the page shows a sign-in screen, tell the owner to sign in inside that browser and wait; never type credentials. For claudemarketplaces.com choose the free option only and never touch payment fields.

Fill the form, then stop before the final submit and take a snapshot. Ask the owner with AskUserQuestion, one question per form (per plugin for the Anthropic portal), whether to submit. On "submit", click the final control, check the success signal listed in the reference, and record the result in the state file. On anything else, close the form without submitting.

## 5. awesome-claude-code

This list bans bots, so never use `gh` or browser automation against it. If the directory status is `ready` (the repo is eligible), build a prefilled link and show it in the report for the owner to open and submit by hand:

```
https://github.com/hesreallyhim/awesome-claude-code/issues/new?template=recommend-resource.yml&display_name=<name>&category=Lists%20%26%20Collections&link=<repo url>&author_name=<author>&author_link=<author url>&description=<10-500 chars>
```

Use `display_name`, `link`, `author_name`, `author_link` and `description` from the repository and marketplace.json, URL-encoded. Tell the owner the checklist boxes cannot be prefilled and they must read and tick them themselves. If the status is `not-yet-eligible`, report "eligible from <eligible_from>, re-run then" and give no link.

## 6. Report

Load the `artifact-design` skill, then build one HTML page and publish it as a private Artifact (`Artifact` tool, `icon: list`). One row per directory: name, status, link (PR, issue, listing or prefilled link), problems with their fixes, and the next action. Add a short summary line (how many listed or pending out of how many) and a section for repository-level problems. The page must work in light and dark and at phone width.

Keep the returned URL as `artifact_url` in the state file. On the next run read it from the state and publish to it (`url` = that URL, same `file_path`) instead of making a new Artifact. Artifacts are private by default: tell the owner the page is visible only to them until they share it.
