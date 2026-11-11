# Repo metadata: `.ui-audit/config.json` and `.ui-audit/manifest.json`

Both files are committed in the target repo under `.ui-audit/`. No images are ever committed (they live in the published audit). The config is human-owned (created once by interview, edited by the user). The manifest is skill-owned (rebuilt incrementally, never hand-edited unless fixing a mistake). The scripts `dep_hash.py` reads only the manifest fields `screens.<name>.deps` and `shared`; `diff_images.py` takes masks from the config.

## config.json

```json
{
  "version": 1,
  "platforms": ["web"],
  "default_baseline_mode": "base+head",
  "web": {
    "launch": "python3 -m http.server 8123",
    "cwd": ".",
    "base_url": "http://localhost:8123",
    "ready_url": "http://localhost:8123/index.html",
    "storage_state": null,
    "login_steps": [],
    "seed": "make seed-fixtures",
    "feature_flags": {"new_nav": true},
    "freeze_css": null
  },
  "viewports": {
    "desktop": {"width": 1440, "height": 900},
    "mobile": {"width": 390, "height": 844, "device_scale_factor": 3, "is_mobile": true, "has_touch": true,
               "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"}
  },
  "screens": [
    {"name": "home", "route": "/index.html", "full_page": true, "states": [{"name": "default"}]},
    {"name": "about", "route": "/about.html", "states": [{"name": "default"}]},
    {"name": "settings", "route": "/settings.html", "states": [
      {"name": "default"},
      {"name": "menu-open", "steps": [{"click": "nav .menu-toggle"}], "viewports": ["desktop"]}
    ]}
  ],
  "masks": {
    "home": [[10, 10, 200, 40]],
    "*": []
  },
  "dark_mode": {"method": "media"},
  "diff": {"threshold": 0.1, "min_changed_pct": 0.01},
  "hosting": {"target": "artifact", "cloudflare_pages_project": "my-repo-ui-audit"},
  "native": {}
}
```

Field notes:
- `platforms`: enabled platforms, any of `web`, `capacitor-ios`, `capacitor-android`, `expo-ios`, `expo-android`. If more than one is enabled the skill asks which to capture on each run.
- `default_baseline_mode`: `base+head`, `head-only` or `head+base-related`. Only a suggestion; the skill still asks each run unless the user passed a mode.
- `web.launch`: command that serves the app; `cwd` is relative to the repo root. For the base capture the same command is run inside the base worktree on a different port (replace the port in `launch`, `base_url`, `ready_url`; if the app cannot change port, run base and head one after the other instead of in parallel).
- `web.storage_state`: path to a Playwright storage-state file (gitignored) for logged-in screens, or `null`. `login_steps` is an alternative: a list of `{goto|fill|click|press}` steps that produce a session, after which the skill runs `state-save` to create the file.
- `web.seed`: command that makes the data deterministic. It must run in both worktrees against the same dataset.
- `web.freeze_css`: extra CSS injected for stills besides the built-in animation freeze (see `web.md`).
- `viewports`: names are free-form but `desktop` and `mobile` are the defaults. A viewport with `is_mobile`/`has_touch`/`device_scale_factor`/`user_agent` is captured through browser emulation (see `web.md`). Remember `dep_hash`/`diff_images` paths use the viewport name.
- `screens[].full_page`: default `true`; set `false` for a viewport-only screenshot of that screen (`references/web.md` step 4).
- `screens[].route`: URL path (web) or deep link (native). Instead of a route, a screen can have `nav_steps` (list of steps replayed from the base URL), same step vocabulary as states.
- `screens[].states[]`: `name` (file name, kebab-case), optional `steps` (`click`, `hover`, `fill`, `press`, `wait_for`, `scroll_to`), optional `viewports` to limit where it applies. State `default` is always the page right after load and settle.
- `masks`: per screen name (or `*` for every screen), a list of `[x, y, w, h]` rectangles in screenshot pixels, passed to `diff_images.py --mask`. Use for clocks, avatars, ads, randomized content. Prefer fixing the data (seed) over masking.
- `dark_mode`: omit until dark mode has been offered; `false` records that the app has no dark theme or the user declined, so it is not asked again. `method` is how dark is switched on, see `web.md` "Dark mode": `media` (`prefers-color-scheme`, also what Tailwind's default `darkMode: 'media'` uses), `class` (add `class`, default `dark`, to `<html>`) or `attribute` (set `attribute`, default `data-theme`, to `value`, default `dark`); optional `storage` `{"key": "theme", "value": "dark"}` is written to localStorage first for apps that read the preference on load. Optional `screens[].dark: false` skips dark for a screen, `states[].themes: ["light"]` for a state.
- `hosting.target`: `artifact` (default; absent also means artifact) or `cloudflare`. Preselected in the per-run publish question; `--publish` overrides it. See `hosting.md`.
- `hosting.cloudflare_pages_project`: Cloudflare Pages project audits are deployed to (one per repo, a branch alias per PR). Lowercase letters, digits and hyphens, at most 58 characters. Needed only for `cloudflare`; asked and saved when missing. No secrets in the config: credentials come from `CLOUDFLARE_API_TOKEN` or `wrangler login`, and the password is the first 12 characters of the audited commit sha.
- `report.default_view`: `slider` (default), `side` or `diff`: the comparison view the audit page opens with. The page has a picker that remembers the viewer's choice.
- `diff`: defaults for `diff_images.py` `--threshold` (per-channel tolerance, fraction of 255) and `--min-changed-pct` (percent of pixels).
- `native`: filled in by `references/native.md` (simulator/emulator names, app ids, build commands).

## manifest.json

```json
{
  "version": 1,
  "last_audited_sha": "9f2c1ab...",
  "screens": {
    "home": {
      "deps": ["index.html", "style.css"],
      "hash": "sha256 of the dep contents at last_audited_sha (written by dep_hash.py new_hashes)",
      "last_audited_sha": "9f2c1ab...",
      "recipes": {
        "default": [],
        "menu-open": [{"click": "nav .menu-toggle"}, {"wait_for": "nav .menu-list"}]
      },
      "motion": [
        {"selector": "nav .menu", "trigger": "menu-open", "kind": "transition", "note": "dropdown slides in"}
      ]
    }
  },
  "shared": {
    "style.css": ["home", "about", "settings"]
  },
  "ripple_notes": [
    {"file": "style.css", "reason": "global stylesheet, every page", "added": "9f2c1ab", "widen": "all-screens"}
  ]
}
```

Field notes:
- `screens.<name>.deps`: repo-relative paths whose change can alter the screen (template/component, its styles, route handler or view model, i18n strings that the screen renders). Globs are not supported; list files. A file listed in more than one screen's deps and that is a global/layout/token file also belongs in `shared`.
- `screens.<name>.hash` and `last_audited_sha`: the last audited state. Written from `dep_hash.py` output `new_hashes` plus the head sha, only after a successful audit of that screen at all its viewports.
- `screens.<name>.recipes`: interaction steps per state, copied from config or discovered while exploring. A recipe may name a state that is not in config (added for a PR's visible changes, SKILL.md step 2b): the capture loop covers config states plus manifest recipe states. Replay these; do not re-explore with snapshots on later runs.
- `screens.<name>.motion`: motion-bearing selectors found so far (transition, animation, gesture). A change to a file in that screen's deps triggers a clip for the listed trigger when the diff touches transition/animation properties.
- `shared`: map of shared file to the screens it affects. `dep_hash.py` marks screens as affected and flags `needs_ripple_review`.
- `ripple_notes`: why the model added or widened something, so the next run does not redo the reasoning. `widen` is `all-screens`, `listed` or `none`.
- Top-level `last_audited_sha`: the newest head sha of a completed audit. Mirrored by the `ui-audit` commit status on the PR commit (see SKILL.md step 1).

Schema decisions beyond the plan's SPEC: `recipes`/`motion` live per screen; the manifest also records `ripple_notes`; `config.screens[].states[]` is the source of recipes on first build.

## First-run interview

Ask with AskUserQuestion, a few questions at a time, offer discovered defaults so the user mostly confirms:
1. Which platforms does this repo ship (web, Capacitor, Expo/React Native)? Which should be enabled for audits?
2. How do I start the app locally (command, port, working directory)? How do I know it is ready?
3. Does the app need login? Provide a test account or storage-state, or should I use an existing dev-login route?
4. Is there seed/fixture data so screens look the same on every run? If not, which regions are dynamic (clocks, avatars, random content) and should be masked?
5. Feature flags or env vars that need to be on for the screens to render?
6. Viewports: keep desktop 1440x900 and mobile 390x844 (touch, DPR 3), or different?
7. Default baseline mode (base+head recommended).
8. Publish target: Claude artifact (default) or Cloudflare Pages; only if Cloudflare, the Pages project name (default `<repo-name>-ui-audit`). Write `hosting.target` (and the project).
9. Only if dark mode was detected: capture dark too? Confirm the detected `dark_mode` method.

### Discovering screens
1. Find the routing source: framework router file (Next/Remix/React Router/Vue Router/Expo Router file tree, Flask/FastAPI/Django URL conf plus templates, static `*.html`), or for native the navigator/deep-link config.
2. List route -> view file candidates with `rg`/`ls`, not by crawling the running app.
3. Propose the screen list (name, route, notable states such as empty, error, modal, open menu) and have the user confirm, merge or drop entries. Skip admin/internal screens unless the user wants them.
4. For each confirmed screen derive `deps` by reading its view file's imports, template includes/extends, linked stylesheets and route handler. Put global CSS, layout templates, design tokens and the root component in `shared`.
5. Write config, build the manifest, run `dep_hash.py` once with `--since` set to the current HEAD to seed `new_hashes`.

### Detecting dark mode
Search the styles and config with `rg`, not the running app: `prefers-color-scheme: dark`; `.dark`, `[data-theme=dark]`, `[data-theme="dark"]` or `.theme-dark` selectors; `darkMode` in `tailwind.config.*` (`'class'`/`'selector'` means class method, `'media'` or unset means media); `dark:` utility classes; theme toggles (`localStorage` reads of `theme`, `next-themes`, `useColorScheme`). No hits means write `"dark_mode": false`. Pick the method from what the code reads, and verify it once in step 4 by checking the screenshot actually turns dark (a wrong method silently produces a duplicate of the light capture).

### Keeping token cost low
- Hashing and diffing are scripts; never read screenshots to decide whether something changed. Look at images only for the changed items you must classify, and at no more than the diff overlay plus head image.
- Re-derive `deps` only for screens whose files changed or that are new; reuse manifest entries for the rest.
- Replay `recipes` by script. Explore with snapshots only for new or failing screens, then store the recipe.
- Spend model reasoning on: new/ambiguous screens, changed shared files (ripple review), and classifying changed items.
