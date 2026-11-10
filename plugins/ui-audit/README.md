# ui-audit

Visual UI-change audit for pull requests. Reviewers cannot see UI changes from a diff, and shared CSS or components change screens nobody meant to touch. `ui-audit` captures before/after screenshots (and short clips for motion) of every screen that really changed, tags each as intentional, unintended or needs review, and publishes one audit page, either as a private Claude artifact or on Cloudflare Pages behind a password, that you link from the PR.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install ui-audit@wovemind
```

## Usage

```
/ui-audit:capture [--platforms web,ios,android] [--baseline base+head|head-only|head+base-related] [--full] [--pr N] [--publish artifact|cloudflare] [--themes light|light+dark] [--unattended] [--model <name>]   # --model: helper subagent model, default haiku
```

The skill also triggers when you ask for screenshots of UI changes, a visual audit or before/after images. `/plan-tools:finalize-pr` offers to run it when a PR touches UI files, then calls it with `--unattended`, which asks nothing and uses the passed flags, the config and the defaults (no dark-mode offer; a failed base falls back to `head-only`).

Each run:
0. Requires a clean working tree (ignoring `.ui-audit/`); if not, offers to commit your changes, otherwise stops.
1. Loads `.ui-audit/config.json` (first run: interviews you, discovers screens, writes config and manifest).
2. Finds the last audited commit (a `ui-audit` commit status on the PR, else `last_audited_sha` in the manifest, else the merge-base) and stops if nothing changed since.
3. Asks which platforms (if several are enabled) and which baseline mode and where to publish (`hosting.target` in the config is the default, `--publish` skips the question). Baseline modes: `base+head` (default; shows only screens that really changed, with diff overlay), `head-only` (fast, no diff, everything needs review) or `head+base-related` (base captured only for screens whose own files changed).
4. Picks screens from file hashes plus model reasoning about ripples from shared files, captures base (git worktree) and head under identical conditions, diffs, classifies, and builds the audit page.
5. Publishes the audit and returns the URL (and the password, if any), ready for the PR body:
   - `artifact` (default): a Claude artifact, private until you share it from claude.ai.
   - `cloudflare`: Cloudflare Pages (`https://pr-<n>.<project>.pages.dev`). On a private repo it sits behind a password, the first 12 characters of the audited commit sha, kept in the `ui-audit` commit status and the PR body. A public repo gets no password. Anyone with the link and password sees the screenshots.

Changing the target for a PR that already has an audit carries the earlier items over to the new target.

Never pushes, and commits only your uncommitted work in step 0 when you say yes. `.ui-audit/` changes are left in the working tree for you or finalize-pr to commit. Images are never committed.

## Dark mode

Web apps with a dark theme (detected from `prefers-color-scheme`, `.dark`/`[data-theme]` selectors or Tailwind `darkMode`) can opt in via a `dark_mode` object in `.ui-audit/config.json` (`false` = none or declined, not asked again). Each run then also captures every chosen state in dark (`<state>--dark`), diffs base vs head, and cross-checks light and dark: a screen that changed in one theme but not the other is flagged `needs_review` (hardcoded color or missing dark variant). Choose `light` only at the per-run question for quicker runs.

## Requirements

- `gh` CLI, authenticated (PR lookup and the `ui-audit` commit status).
- To publish as an artifact: the Claude Code `Artifact` tool. Artifacts are private: reviewers see the audit after you share it from claude.ai.
- To publish to Cloudflare Pages: Node (`npx`, already needed for the Playwright CLI) to run `npx wrangler@4 pages deploy`; nothing to install. Credentials: `CLOUDFLARE_API_TOKEN` (scope Account > Cloudflare Pages > Edit) plus `CLOUDFLARE_ACCOUNT_ID` if the token reaches several accounts, or run `! npx wrangler login` once. The skill never logs in itself.
- If the chosen target cannot publish, the skill offers the artifact instead or keeps a local `index.html` and a `report.md` for the PR comment.
- Python 3 with `pip install pillow numpy` (image diffing).
- Web: the Playwright CLI (`playwright-cli`, via the `playwright-cli` skill).
- Native (optional, untested on real apps): Xcode with iOS simulators (`xcrun simctl`), or the Android SDK with an emulator and `adb`; optionally `ffmpeg` to convert recordings.

## Environment variables

None are needed to publish as a Claude artifact. To publish to Cloudflare Pages, set `CLOUDFLARE_API_TOKEN` (scope Account > Cloudflare Pages > Edit), plus `CLOUDFLARE_ACCOUNT_ID` when the token reaches more than one account, or run `! npx wrangler login` once instead. The plugin has no plugin settings; per-repo choices live in `.ui-audit/config.json`.

## Opinionated defaults

| Default | Change it with |
|---|---|
| Publish as a private Claude artifact | `--publish cloudflare`, or `hosting.target` in `.ui-audit/config.json` |
| Compare base and head (`base+head`), showing only screens that really changed | `--baseline head-only` or `--baseline head+base-related` |
| Capture desktop 1440x900 and mobile 390x844 | viewports in `.ui-audit/config.json` |
| Light theme only; dark is captured too once the repo opts in with a `dark_mode` object in `.ui-audit/config.json` | `--themes light` for a quick run |
| Helper subagents run on the `haiku` model | `--model <name>` |
| Audit only what changed since the last audited commit | `--full` |
| Record a `ui-audit` commit status on the PR head | fixed; `finalize-pr` relies on it |

## Repo metadata

Committed in the target repo under `.ui-audit/`:
- `config.json`: platforms, launch command and base URL, login and seed data, hosting target and Cloudflare Pages project name (`hosting`), viewports (default desktop 1440x900 and mobile 390x844 with touch, via browser emulation), screens and states, masked regions, diff thresholds, default baseline mode, native device settings. Platform ids: `web`, `capacitor-ios`, `capacitor-android`, `expo-ios`, `expo-android`.
- `manifest.json`: maintained by the skill. Per screen its dependency files, hash, last audited sha, interaction recipes and motion entries; shared files and the screens they affect; ripple notes. This is what makes repeat runs cheap: only screens whose hash changed are re-captured and the model reasons only about new screens and shared-file ripples.

Full schemas: `skills/capture/references/config-schema.md`.

## Worked example

A PR changes a button on the home page and also `style.css`, which every page uses.

```
/ui-audit:capture
```

The skill detects `style.css` as a shared file, reasons about which pages it reaches, captures base and head for home, about and settings at desktop and mobile, and finds that only `home` (the new button, intentional) and `about` (card padding changed, unintended) differ. The audit page lists `about` first with the diff overlay and a one-line reason, and the PR body gets:

```markdown
## UI audit
Latest: https://claude.ai/artifact/<id>  (2 changed screens, 1 unintended)
```

Or, on Cloudflare Pages with a private repo:

```markdown
## UI audit
Latest: https://pr-12.my-repo-ui-audit.pages.dev  (2 changed screens, 1 unintended)
Password: `3f9c1a7be204` (username: anything)
```

A later commit that only touches `about.html` re-captures `about` alone.

## Files

- `skills/capture/SKILL.md`: the workflow.
- `skills/capture/references/`: `config-schema.md`, `web.md`, `native.md`, `ripple-reasoning.md`, `hosting.md`.
- `skills/capture/scripts/`: `dep_hash.py`, `diff_images.py`, `build_report.py` (each has `--help` and `--selftest`).

Native capture (Capacitor, Expo/React Native) follows the documented simulator and emulator commands but has not been tried on a real app yet.
