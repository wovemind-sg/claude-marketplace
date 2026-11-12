# Publishing the audit: Claude artifact or Cloudflare Pages

The audit is published either as a private Claude artifact (`Artifact` tool) or to Cloudflare Pages behind a password. Nothing is pushed to the repo or any branch, so no confirmation is needed. Build into a scratchpad dir (`AUDIT_DIR`), not the repo (artifact sources must be under the working directory or the scratchpad). `build_report.py` prints JSON with `index`, `report`, `items`, `runs` and `stale_media` (media paths, relative to `AUDIT_DIR`, of items the run replaced or removed).

`N` is the PR number, `REPO` the repo root.

## 1. Choosing the target
In order: `--publish artifact|cloudflare` flag, the answer to the SKILL.md step 2 question, `hosting.target` in `.ui-audit/config.json`, `artifact`. Unattended runs skip the question. Call the choice `TARGET`.

## 2. Previous audit
Skip this on the first audit of a PR. Otherwise `OLD_URL` is the `target_url` of the newest `success` `ui-audit` commit status on the PR's commits, else the `Latest:` URL of the PR body's "UI audit" section (covers audits whose status was never written). Host `claude.ai` means the old target was `artifact`, `*.pages.dev` means `cloudflare`. If neither exists (audit from before publishing, or `BASE` came from the manifest), treat it as a first audit and say earlier items are not carried over.

`OLD_PW` (old target Cloudflare, private repo only) is the password in that status description (`ui-audit ran; password: <pw>`) or the PR body `Password:` line. Never derive it from the sha of the commit carrying the status: finalize-pr re-records the status on a later commit.

## 3. Restore earlier items
All or nothing: if any step here fails, do not publish; use the fallback (section 6), saying earlier items could not be restored.
- Always, before `build_report.py`: have the old `history.json` in `AUDIT_DIR/history.json` (SKILL step 1 already fetched it; reuse that file, do not fetch twice). Without it the new page lists only the re-captured items. Artifact: `Artifact` action `read` with `url`, `path: history.json`, `out_dir: AUDIT_DIR`. Cloudflare: `curl -fsS [-u "ui-audit:$OLD_PW"] $OLD_URL/history.json --create-dirs -o AUDIT_DIR/history.json` (no `-u` for a public repo).
- Old and new target both `artifact`: no media download. Publish only new media and `null` the stale ones (section 4); files left out stay published.
- New target `cloudflare`, or old `cloudflare` and new `artifact`: after the build, download the media of kept items that is missing under `AUDIT_DIR`, i.e. every media path (`base_img`, `head_img`, `diff_img`, `clips`, `stills`) of the items in the merged `AUDIT_DIR/history.json`. Artifact source: `Artifact` action `read` with `paths` (at most 256 per call) and `out_dir: AUDIT_DIR`. Cloudflare source: `curl -fsS [-u "ui-audit:$OLD_PW"] $OLD_URL/<path> --create-dirs -o AUDIT_DIR/<path>`. Why: a Pages deploy is a full snapshot, and a new artifact starts empty. Replaced items are no longer referenced, so they are not downloaded.

## 4. Publish to artifact
Build: `python3 -I "${CLAUDE_SKILL_DIR}/scripts/build_report.py" --spec audit.json --out AUDIT_DIR --repo REPO`. Exit 1 means the self-check failed (SKILL.md step 6): do not publish.

First publish for a PR (also when switching from Cloudflare: pass all restored media). Call `Artifact` with:
- `file_path`: `AUDIT_DIR/index.html`
- `files`: `{published_path: local_source}` for every `media/...` file plus `history.json` and `report.md`. The published path is the path relative to `AUDIT_DIR`, which is what `index.html` references.
- `icon`: `image`. The artifact title is the page's `<title>`, `UI audit - <project> - PR <n>`, set by `build_report.py` from `meta.project` and `meta.pr`.

Keep the returned URL. Artifacts are private by default: reviewers see the audit only after the user shares it from claude.ai. Say so in the final answer.

Later publish for the same PR (old target `artifact`, `OLD_URL` is its URL):
1. `Artifact` action `list`, `scope: files`, with `OLD_URL`. Why: the publish is refused for any path it replaces or removes (`report.md`, `index.html`, `stale_media`) that this session has not read or listed.
2. Build, then `Artifact` publish with `url` set to `OLD_URL` and `file_path` `AUDIT_DIR/index.html`. In `files` pass only the new media, `history.json` and `report.md`, and `null` for each path in `stale_media`. Files you leave out stay published, so kept items still load. Why: a version holds at most 511 files, stale media would fill it.

Limits: at most 255 files per publish, 511 per version. Above 255, split the media across several publishes to the same URL (each publish needs `file_path`: pass `AUDIT_DIR/index.html` every time, the last publish carries the final one).

## 5. Publish to Cloudflare
Deploys with `npx --yes wrangler@4 pages deploy` (needs only Node; no global install, no `cf` CLI). One Pages project per repo, one branch alias per PR. Pages has no built-in password: `build_report.py --password PW` writes `_worker.js` into the audit dir, which checks Basic Auth (any username, the password) in front of the static files. Only the SHA-256 of the password is embedded.

`PROJECT` is `hosting.cloudflare_pages_project` from the config. If it is missing when Cloudflare is chosen, ask (default `<repo-name>-ui-audit`, lowercase letters, digits and hyphens, at most 58 characters) and save it to the config; unattended, use the default and say so.

Pre-check (non-interactive, never `wrangler login`). Publish only if all hold, otherwise use the fallback:
- Node (`npx`) is available.
- `CLOUDFLARE_API_TOKEN` is set (scope Account > Cloudflare Pages > Edit) or `npx --yes wrangler@4 whoami` prints an account. `whoami` exits 0 even when not logged in ("You are not authenticated"), so read its output, not the exit code. Ignore its hint about `wrangler deploy --temporary`: that is for Workers. If not authenticated, tell the user to run `! npx wrangler login` themselves: login opens a browser and hangs an unattended run. If the token reaches more than one account, `CLOUDFLARE_ACCOUNT_ID` must be set too (non-interactive wrangler errors instead of asking).

Password: `gh repo view --json isPrivate -q .isPrivate` (if it fails or prints anything but `false`, treat the repo as private; never fail open). Private repo: `PW=$(git -C REPO rev-parse HEAD | cut -c1-12)`, the first 12 characters of the audited HEAD sha (not `--short=12`, which can return more). It changes every audit. Public repo: no password, no `_worker.js` (the audit is as public as the repo).

Steps, in this order:
1. Build, with `--password "$PW"` on a private repo: `python3 -I "${CLAUDE_SKILL_DIR}/scripts/build_report.py" --spec audit.json --out AUDIT_DIR --repo REPO --password "$PW"`.
2. Download kept media (section 3).
3. Delete each `stale_media` path under `AUDIT_DIR` (`rm -f`), so replaced screenshots are not re-uploaded.
4. Deploy from the scratchpad dir (outside the repo, so wrangler does not pick up the repo's `functions/` or `wrangler.toml`): `SHA=$(git -C REPO rev-parse HEAD)`, then `cd` to the scratchpad and `npx --yes wrangler@4 pages deploy AUDIT_DIR --project-name PROJECT --branch pr-N --commit-hash $SHA`. If it says the project does not exist (first use): `npx --yes wrangler@4 pages project create PROJECT --production-branch <default branch> --force`, then deploy again. `--force` is needed: without it current wrangler hands `project create` to Workers, which fails on `_worker.js` and leaves a `wrangler.jsonc` and `.wrangler/` in the cwd that break the next `pages deploy`; delete those if they appear.
5. wrangler prints `Take a peek over at <deploy url>` (immutable per-deploy URL, used for the "Earlier audits" lines) and `Deployment alias URL: <alias>` (the stable per-PR URL, the `target_url`). Use the printed URLs; do not build them from `PROJECT`, since Cloudflare adds a random suffix when the name is taken.

Each deploy replaces the alias's `_worker.js`, so the alias password is always the latest audit's sha. Each older per-deploy URL keeps the sha of its own commit as its password.

A new alias can take a minute or two to resolve (curl exit 000); retry before calling the deploy broken. `/_worker.js` is never served: with the password it returns the audit page, which is expected.

Limits: 20,000 files per deploy, 25 MiB per file. A clip over 25 MiB fails the deploy: drop or shorten it.

Privacy: anyone with the link and the password sees the screenshots. The password sits in the commit status and the PR body, so it is only as private as the repo. Say so in the final answer.

## 6. Fallback
If the target is Cloudflare and it cannot publish (no Node or credentials, a failed restore, deploy or project create): when someone can be asked, ask "publish as a Claude artifact instead, or keep the audit local"; unattended, keep it local. Keeping it local leaves `AUDIT_DIR/index.html` and returns `report.md` as the PR comment; so does an unavailable `Artifact` tool. Never record a `success` `ui-audit` status without a published URL.

## Retention
None automatic. Delete an artifact, Pages project or deployment only when the user asks.

## 7. Link format for the PR body
One line per audited commit, newest on top. Artifact (same URL on every line):

```markdown
## UI audit
Latest: <artifact url>  (N changed screens, M unintended)

Earlier audits:
- <short-sha> - <artifact url> - <one-line summary>
```

Cloudflare, private repo: add a `Password:` line, replaced every run, and give each earlier line the 12-character sha, which is the password of that deploy URL:

```markdown
## UI audit
Latest: <alias url>  (N changed screens, M unintended)
Password: `<sha12>` (username: anything)

Earlier audits:
- <short-sha> - <deploy url> - password `<sha12>` - <one-line summary>
```

Public Cloudflare repo: no `Password:` line. If publishing was not possible, include the `report.md` summary in the PR comment instead of a link.
