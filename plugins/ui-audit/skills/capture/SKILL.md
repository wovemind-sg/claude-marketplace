---
name: capture
description: Capture before/after screenshots and short clips of the UI changes in a branch or PR, flag unintended visual changes, and publish a reviewable audit page as a Claude artifact or on Cloudflare Pages. Use whenever the user wants screenshots of UI changes, a visual audit, a visual regression check, a UI diff for a PR, before/after images, or to "show reviewers what the UI looks like", whenever templates, components, styles, screens or front-end code changed and reviewers need to see the result, and when /plan-tools:finalize-pr asks for a UI audit. Works for web (Playwright, desktop and mobile emulation) and, for Capacitor/Expo apps, simulators and emulators. Also use it to set up, refresh or inspect the `.ui-audit/` config and manifest in a repo.
argument-hint: "[--platforms web,ios,android] [--baseline base+head|head-only|head+base-related] [--full] [--pr N] [--publish artifact|cloudflare] [--themes light|light+dark] [--unattended]"
---

# UI audit capture

Reviewers cannot see UI changes from a diff, and shared CSS or components change screens nobody meant to touch. This skill captures what the UI really looks like before and after a change, keeps only screens that visibly changed, tags each as intentional or unintended, builds one audit page, publishes it and links it from the PR. Repo metadata in `.ui-audit/` plus helper scripts keep repeat runs cheap: scripts hash and diff, you only reason about new screens, ripple effects and classification.

Scripts live in `${CLAUDE_SKILL_DIR}/scripts/` (if that variable is not set, they are next to this file under `scripts/`). Run any Python that reads untrusted files with `python3 -I`. Pillow and numpy are required for diffing; if missing, tell the user to `pip install pillow numpy` and stop.

| Script | Purpose |
|---|---|
| `scripts/dep_hash.py` | which screens changed since a sha, shared-file ripple flags, new hashes |
| `scripts/diff_images.py` | pixel diff base vs head with masks, overlay images, changed % |
| `scripts/build_report.py` | audit `index.html`, `report.md`, `history.json` from a spec |

References, read only when the step says so:
- `references/config-schema.md`: config and manifest schemas, first-run interview, screen discovery, token-saving rules (step 0 and whenever you edit them).
- `references/web.md`: playwright-cli capture flow, viewports and mobile emulation, stable stills, states, motion clips (step 4 for web).
- `references/native.md`: Capacitor/Expo simulator and emulator capture (step 4 when a native platform is selected).
- `references/ripple-reasoning.md`: finding screens the dependency graph misses (step 3).
- `references/hosting.md`: choosing the target, publishing as a Claude artifact or to Cloudflare Pages, history migration, fallback, PR link format (step 6).

Never commit or push anything yourself, with one exception: step 0 may commit the user's uncommitted work, only after they say yes. Files changed in the repo (`.ui-audit/`) are left in the working tree for the caller or user to commit. Never commit images.

## Delegate to Haiku subagents when the work is mechanical

Capture runs are long and mostly repetitive, and every screenshot, snapshot and shell output lands in context. Spawn subagents with `model: haiku` for the mechanical parts so the main session keeps only the results. Haiku is reliable when the task is a fixed recipe with a checkable output; it is not reliable at open-ended judgment, so keep that yourself (or use Sonnet).

Use Haiku (one subagent per platform, or per batch of screens) for:
- Replaying recorded recipes from the manifest in step 4: start the app, set viewport and emulation, visit each screen/state, save PNGs to the agreed layout, record clips for flagged motion items.
- Native boot/install/launch/screenshot loops from `references/native.md`.
- Checking that every expected file exists with the expected viewport width.
- Running the scripts in steps 3 and 5 when you only need their JSON, and assembling the spec from `diff_images.py` output for items you have already classified.

Keep on the main model (or Sonnet), never Haiku:
- First-run setup, screen discovery, and writing or refreshing recipes (step 0, and a recipe step that no longer matches).
- Ripple reasoning and choosing extra screens (step 3), deciding motion clips, and classifying changes as intentional / unintended / needs_review with reasons (step 5).
- Anything involving user confirmation (step 2) or publishing (step 6).

How to delegate safely: give the subagent the exact commands or recipe, the output directory and the layout, and ask it to report only the list of files written plus any step that failed. Check its output yourself before the diff (files exist, widths match the viewport, no blank images); a failed or suspicious Haiku run is retried once by Sonnet instead of being trusted. Subagents never write the manifest or config and never publish.

## Workflow

### 0. Load config, or run first-run setup
Why: every later step depends on knowing how to start the app and what the screens are.
- Require a clean working tree, ignoring `.ui-audit/`: `git status --porcelain -- . ':!.ui-audit'`. The audit is recorded against HEAD, so captures must match it. If it lists files, show them and offer to commit them (commit only on the user's yes, with a semantic message). If they decline, or the run is unattended, stop. An unpushed HEAD is fine.
- Read `.ui-audit/config.json` and `.ui-audit/manifest.json` at the repo root. Their schemas are in `references/config-schema.md`.
- The run is unattended when AskUserQuestion is unavailable or `--unattended` is passed (the caller already asked everything). Then take every answer from the user's prompt and otherwise use the defaults in `references/config-schema.md`; write the config and manifest yourself and say which defaults you chose.
- Dark mode is web-only and opt-in through `dark_mode` in the config. On first run, and when `dark_mode` is absent (`false` means the user declined: do not ask again), check whether the project has it (detection in `references/config-schema.md`) and offer to enable it (with `--unattended`, do not offer; leave `dark_mode` absent).
- If the config is missing, run the first-run interview from that file with AskUserQuestion (with `--unattended`, skip the interview and the screen-list confirmation and use the defaults), discover screens from the router/templates, confirm the list with the user, write the config, then build the manifest (deps and shared files per screen) and run `dep_hash.py` once to seed hashes. The first run is a full sweep: every screen is captured (step 3 `--full`).
- If only the manifest is missing or stale, rebuild entries incrementally (new or changed files only).

### 1. Determine scope
Why: incremental runs should only look at what changed since the last audit.
- `BASE` is the last audited sha. In order: the newest commit on the PR branch with a successful `ui-audit` commit status (same pattern as finalize-pr step 0, context `ui-audit`), then the top-level `last_audited_sha` in the manifest if that commit is an ancestor of HEAD (`git merge-base --is-ancestor`), then `git merge-base HEAD origin/<pr base branch>`.
- If `BASE` equals `HEAD` and a previous audit exists (status, manifest `last_audited_sha`), nothing changed since the last audit. Tell the user and stop. On a first run with no previous audit, an equal merge-base is not "no changes": the base is the commit the user names (the PR's first parent, or the prompt's base), so ask for it if it is not given (with `--unattended`, use the PR's base branch).
- Record `BASE`, `HEAD`, and whether this is incremental. Also determine the PR number (`gh pr view --json number`, or from `--pr`); it is needed to publish.

### 2. Ask the per-run questions
Why: the user knows which platforms and comparison they care about; the cost differs a lot. Skip a question only when the argument already answers it (`--platforms`, `--baseline`, `--publish`, `--themes`). Use AskUserQuestion. With `--unattended`, ask nothing: use the arguments, else the config and the defaults in `references/config-schema.md`, and do not offer dark mode (`dark_mode` stays absent, so a later attended run offers it).
- **Platforms**, only if more than one is enabled in config: which to capture this run (for example web, iOS simulator, Android emulator). Native captures are slower, so let the user pick.
- **Baseline mode**, always (default `base+head`):
  - `base+head`: capture the old version and the new version of every affected screen, then show only screens that really changed, side by side with a diff overlay. This is the default because reviewers see exactly what moved, and it is the only mode that can find unintended changes.
  - `head-only`: capture only the new version. Fastest and cheapest, no diff and no way to tell what changed. Everything is tagged `needs_review`. Use for brand new UIs or when the base cannot run.
  - `head+base-related`: capture the new version of all affected screens but the old version only for screens whose own files changed. Faster than the default on large apps, but unintended ripples on other screens are shown without a before image, so they are tagged `needs_review`.
- **Viewports**: confirm the configured ones (default desktop and mobile). Mobile is browser emulation on web.
- **Publish target**, unless `--publish` is given or the run is unattended: `Claude artifact` (private until shared from claude.ai) or `Cloudflare Pages` (behind a password on a private repo), with the config's `hosting.target` (default `artifact`) preselected. Details in `references/hosting.md`.
- **Themes**, unless `--themes` is given, only if config has a `dark_mode` object (web only): `light+dark` (default) or `light` only. Dark doubles the captures, so offer `light` for quick runs.

### 3. Choose screens
Why: capturing everything is slow and noisy; capturing too little hides ripples.
1. `python3 -I scripts/dep_hash.py --manifest .ui-audit/manifest.json --repo . --since $BASE --head $HEAD` gives `affected_screens`, `shared_changed`, `unmapped_changed_files` and `new_hashes`. `dep_hash.py` has no full-sweep flag: for a full sweep select every screen in the manifest yourself. Do that when this is the first audit, the user passed `--full`, or `references/ripple-reasoning.md` says to widen.
2. Read `references/ripple-reasoning.md`. For each `shared_changed` entry (`needs_ripple_review`) and each unmapped UI file, reason about extra screens the graph misses. Add them with a one-line reason and record it in the manifest `ripple_notes`; add new files to `shared`/`deps` so the next run needs no reasoning.
3. Unaffected screens keep their previous capture; they are not re-captured. Mark which are "intentionally touched" (their own deps changed) versus "ripple" (reached only through shared files or your reasoning): this drives classification in step 5.
4. The history merge replaces only the exact (screen, platform, viewport, state) items you re-capture; other kept items stay. Capture only what you need, but a state that no longer exists must be listed in the spec's `removed` array.
5. Decide motion: if the diff touches transitions, animations, keyframes, gestures or ripple reasoning flags it, plan a clip for the affected interaction (details in `references/web.md`).

### 4. Capture
Why: pixels are the evidence. Base and head must be captured under identical conditions or the diff is noise.
- Delegate the replay to Haiku subagents as described above; capture new or broken recipes yourself.
- Web: follow `references/web.md` (base from a git worktree at `BASE`, head from the working tree, same seed and storage state, desktop and mobile, states from the manifest recipes, motion rules).
- Native (Capacitor, Expo/React Native): follow `references/native.md`. Tell the user it is untested on real apps.
- Always capture base fresh. In `head-only` mode skip base entirely.
- Layout everywhere: `<side>/<screen>/<viewport>/<state>.png`. Dark captures are the same states with a `--dark` suffix (`default--dark.png`), so the scripts, history and audit page need no theme support: a dark item is just a state. How to switch themes is in `references/web.md`.
- Sources of flakiness (animations, fonts, clocks, random data) are handled in `references/web.md`. If a screen cannot be made stable, mask it in config rather than ignoring noisy diffs.

### 5. Compare and classify
Why: reviewers only want screens that changed, with the surprising ones first.
- `python3 -I scripts/diff_images.py --base BASE_DIR --head HEAD_DIR --out DIFF_DIR [--mask config masks JSON] [--threshold ...] [--min-changed-pct ...]`. Drop `unchanged`. `added` (no base image) and `removed` need a decision: new screens/states are `intentional` if their files were touched; items with no base image in `head-only` or related-only mode are `needs_review`.
- Classify each `changed` item: `intentional` if the screen was touched by the diff itself and the visual change is plausible given the diff; `unintended` if the screen was only reached through shared files or ripple and nobody meant to change it, or the change contradicts the diff; `needs_review` when you cannot tell. Look at the diff overlay and head image only for changed items. Write a one-line reason for each (what changed, and why you think so).
- Dark pairs (skip screens or states that have no `--dark` capture, e.g. opted out with `dark: false`): when a screen's light capture changed, compare it with its `--dark` item. Light changed but dark identical (or the reverse) usually means a hardcoded color or a missing dark variant: classify both `needs_review` and say so in the reason, unless the diff clearly explains it. A change that appears only in dark on a screen nobody touched is `unintended`.
- `size_mismatch` means base and head differ in size (common with full-page captures). The diff pads both to the larger size, so the extra area counts as changed and the overlay shows it; judge it like any other change (e.g. new content at the bottom is plausibly `intentional`).
- Write the audit spec JSON (the spec schema is in the `build_report.py` docstring, shown by `--help`). Map `diff_images.py` output directly: `path` is `<screen>/<viewport>/<state>.png`, `overlay` becomes `diff_img`, `changed_pct` carries over. Add `clips` and `stills` for motion items.
- Meta fields: `project` (repo name, from `gh repo view --json name -q .name`, else `basename "$(git rev-parse --show-toplevel)"` (in a git worktree that is the worktree folder, not the repo); becomes the page and artifact title `UI audit - <project> - PR <n>`), `pr`, `head_sha`, `base_sha`, `baseline_mode`, `incremental_from`, `reused_screens`, `summary`. `summary` is one or two plain sentences on what the PR changes and why, shown under the PR line at the top of the page: draft it from the PR title and body (`gh pr view --json title,body`) or, without a PR, from the branch commits, then, if `/humanizer:humanizer` is installed, run it through that before putting it in the spec. Media paths in the spec are resolved relative to the spec file, not the working directory: use absolute paths. In `head-only` mode set `base_sha` to `BASE` anyway (it is the point the audit would have compared against).
- In an incremental run the history merge replaces only re-captured (screen, platform, viewport, state) items; list vanished ones in the spec's `removed: [{screen, platform, viewport, state}]`. Compare it against `BASE` (the last audited sha, whose head images you may reuse from the earlier run's captures), and if the earlier finding still matters, say so in the item's `reason` so it is not lost.

### 6. Build and publish
Why: the audit is only useful if reviewers can open it. Both targets are private (artifact until shared, Cloudflare behind a password), so publishing needs no confirmation.
Read `references/hosting.md` and follow it: it covers choosing the target, fetching the previous `history.json`, building, publishing, and the fallback (local `index.html` plus `report.md`).

### 7. Record and report
- A first `head-only` run also sets the manifest top-level `last_audited_sha` to HEAD, so the next run with no new commits stops at step 1.
- Update `.ui-audit/manifest.json`: for each screen successfully audited at all its viewports set `hash` from `new_hashes` and `last_audited_sha` to HEAD; set the top-level `last_audited_sha`; save new recipes and motion entries. Leave the files in the working tree and tell the caller they need committing; do not commit.
- If a PR exists and the audit was published, always record it (it is only commit metadata, not a push; without it the next run cannot find the earlier audit and publishes a second one): `gh api repos/{owner}/{repo}/statuses/$(git rev-parse HEAD) -f state=success -f context=ui-audit -f description="<description>" -f target_url=<url>`. `<description>` is `ui-audit ran` for an artifact or a public-repo Cloudflare audit, and `ui-audit ran; password: <sha12>` for a private-repo Cloudflare audit (the next run reads the password from it). `<url>` is the artifact URL or the Cloudflare alias URL. Step 1 reads the status next time, and `target_url` is how the next run finds the earlier audit. If the status write fails (for example HEAD is not pushed), say so and move on: the PR body section is the durable record.
- Return to the user (and to finalize-pr, which puts it in the PR body): the audit URL and the password, if any, counts of changed/unintended/needs-review screens, the list of unintended items with reasons, which screens were reused, which were skipped and why, and the `report.md` text as a ready PR comment if hosting was unavailable.

## Edge cases
- No UI changes in the diff and nothing shared changed: report "no UI changes since BASE", build nothing, but still update `last_audited_sha`.
- App fails to start on base: say so, fall back to `head-only` for the affected platform after asking the user (with `--unattended`, fall back without asking and note it in the report).
- A recipe step no longer matches: refresh it with a snapshot, update the manifest recipe, mention it in the report.
- Everything differs by a few pixels: likely font/animation instability; fix stability (see `references/web.md`) instead of reporting hundreds of changes.
