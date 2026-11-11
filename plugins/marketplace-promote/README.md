# marketplace-promote

Gets a Claude Code plugin marketplace listed in plugin directories and awesome lists with as little manual work as possible. It checks each directory's rules first, opens pull requests and issues through `gh`, fills web submission forms up to the final submit, and publishes a status report. It works for any marketplace repository, not only this one, and it is safe to re-run: it never submits anything twice.

## Install

```
/plugin install marketplace-promote --marketplace wovemind-sg/claude-marketplace
```

## Requirements

- `gh`, authenticated (`gh auth status`).
- `playwright-cli` for the web forms.
- Python 3 (standard library only).
- A paid Claude plan and GitHub push access for the Anthropic plugin directory.
- A public GitHub repository with a `.claude-plugin/marketplace.json`, pushed to its default branch.

## Usage

```
/marketplace-promote:promote [repo path] [--check]
```

`repo path` defaults to the current directory. `--check` runs the pre-flight checks only, publishes the report and submits nothing.

A normal run does this: pre-flight, one review of all drafted PRs and issues (you approve or edit them and pick which aitmpl and Anthropic plugins to submit), then the web forms, then the report. Run it again after adding or changing plugins; directories that already list the repository or have a submission pending are skipped.

## What is automated and what is yours

- Automated: pre-flight checks, forks, branches, commits, PRs and issues once you approve them, filling web forms, and the report.
- Yours: approving the drafts, choosing plugins, signing in to websites in the browser the skill opens, answering "submit" before each web form is sent, and submitting the awesome-claude-code issue by hand (that list bans bots, so you get a prefilled link once the repository is eligible).

## State and report

Run state is stored in `${CLAUDE_PLUGIN_DATA}/<owner>-<repo>.json`: submission URLs and the report URL. Nothing is written to your repository. The report is a private Artifact page, republished to the same URL on every run; share it from claude.ai if others should see it. Credentials are never stored or printed.

## Directories

- composio-community/awesome-claude-plugins: PR with one link line.
- aitmpl.com: one PR per plugin, pinned to the pushed commit.
- Anthropic plugin directory: web form, one plugin per submission, at most 10 per day.
- claudemarketplaces.com: web form, free option only.
- claudepluginhub.com: web form.
- tonsofskills.com: an issue, then a PR; both say AI assistance was used.
- awesome-claude-code: prefilled link only, once the repository is 14 days old or has 100 stars.
- ccplugins/awesome-claude-code-plugins: closed to PRs and issues; reported as closed and re-checked each run.
- claude-plugins.dev and awesomeclaudeplugins.com: index repositories on their own; the report shows whether yours is listed.

Directory rules are in `skills/promote/directories.json`; form details are in `skills/promote/references/web-forms.md`.
