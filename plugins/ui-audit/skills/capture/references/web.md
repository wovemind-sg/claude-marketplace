# Web capture with playwright-cli

Use the `playwright-cli` skill for the browser. Commands below were verified against the fixture. Read its `references/running-code.md` (run-code), `video-recording.md` (screencast) and `storage-state.md` (login) when you need more than what is shown.

## Layout of captures

```
$WORK/base/<screen>/<viewport>/<state>.png
$WORK/head/<screen>/<viewport>/<state>.png
```

Run `playwright-cli` from `$WORK` (it creates a `.playwright-cli/` dir in the current directory; do not let it land in the repo). `$WORK` is a scratch dir (for example `ui-audit-workspace/run-<sha>`). This exact layout is what `diff_images.py --base $WORK/base --head $WORK/head` expects and what `build_report.py` items point to. Use one playwright session per side and per viewport (`-s=head-mobile`) so emulation settings do not leak.

## Serve base and head

- Head: the working tree, started with `web.launch`.
- Base: `git worktree add "$WORK/base-src" <base_sha>` (detached), then run the same `web.launch` from there on another port. Run `web.seed` in both so data is identical. Remove the worktree afterwards (`git worktree remove --force`).
- Wait for `ready_url` (poll with `curl -sf`) before capturing. Start servers so you hold the real PID, for example `python3 -m http.server PORT >/dev/null 2>&1 & SRV=$!` in the same shell as the later `kill $SRV` (a `( ... &)` subshell loses the PID). `playwright-cli open` can answer "browser not open" on the next command; wait a second and retry.

## Viewports

Desktop: `playwright-cli -s=head-desktop open` then `resize 1440 900`.

Mobile is browser emulation, not a different browser: viewport, device scale factor, touch and mobile UA. Chromium is the default browser of `open` (the `--browser` flag only accepts `chrome`, `firefox`, `webkit`, `msedge`). `open --mobile` or `open --device "iphone 15"` give a ready-made emulation; use the CDP call below when the config needs exact values. The CDP call was verified against the fixture (innerWidth 390, touch points 1, mobile UA). It applies to the page's session and must be repeated in each new session:

```bash
playwright-cli -s=head-mobile open "$BASE_URL"
playwright-cli -s=head-mobile resize 390 844   # required: the CDP override alone left screenshots at 1280x720 with desktop media queries
playwright-cli -s=head-mobile run-code "async page => {
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Emulation.setDeviceMetricsOverride', {width: 390, height: 844, deviceScaleFactor: 3, mobile: true});
  await cdp.send('Emulation.setTouchEmulationEnabled', {enabled: true});
  await cdp.send('Emulation.setUserAgentOverride', {userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'});
}"
```

After emulating, check `playwright-cli -s=head-mobile eval innerWidth` (the value is under `### Result`) prints 390 and that the first screenshot is the expected width; a wrong size means every mobile diff is silently wrong. If the CDP route is unavailable (non-Chromium), fall back to `resize 390 844` alone and tell the user the mobile capture is viewport-only. Screenshots at DPR 3 are large; for diffing use DPR 1 unless config demands otherwise (set `deviceScaleFactor` from config, default to 1 for speed and consistent diffs). Use identical settings for base and head.

Fallback that always works (used in the fixture): `playwright-cli -s=NAME resize 390 844`. It takes two separate args. Ignore the update banner on stderr.

## Stable stills

Before each screenshot:
1. `goto` the route, wait for network idle or for a known selector (`wait_for` in the recipe).
2. Freeze motion: inject CSS and wait for fonts and images.
```bash
playwright-cli -s=head-desktop run-code "async page => {
  await page.addStyleTag({content: '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important;scroll-behavior:auto!important}'});
  await page.evaluate(() => document.fonts.ready);
  await page.waitForLoadState('networkidle');
}"
```
   Add `web.freeze_css` from config to the injected style. Never freeze when the item is a motion capture (see below).
   After each default `goto`, record where the page ended up and what it says: `playwright-cli -s=S eval "location.href"` (the value is under `### Result`) for redirect detection, and `eval "document.body.innerText"` saved to `<state>.txt` next to the PNG, used for reasons in step 5.
3. Dynamic regions: masks are applied at diff time from config, not by editing the page. If a region is hard to mask (random content), stub it first (`page.route`, fixed clock via `page.clock.install({time: ...})`, fixed `Math.random`).
4. Full-page screenshot (the default, base and head alike). Changes at the bottom of a page or inside a scrolling sheet are invisible in a viewport shot, and `screenshot` has no full-page flag, so use `run-code`. It grows the viewport by the document's hidden height plus the hidden overflow of every `overflow:auto|scroll` element (a fixed modal sheet scrolls on its own, so `fullPage` alone would miss it). It re-measures after each resize (up to 5 passes, so `vh`-sized elements and nested scrollers are covered), caps the height at 16000 CSS px, shoots, and restores the viewport:
```bash
playwright-cli -s=head-desktop run-code --filename="$WORK/fullpage.js"   # with the absolute out path substituted
```
```js
async page => {
  const MAX = 16000; // CSS px cap
  const orig = page.viewportSize() || await page.evaluate(() => ({width: innerWidth, height: innerHeight}));
  const need = () => page.evaluate(() => {
    let h = document.documentElement.scrollHeight - innerHeight;
    for (const e of document.querySelectorAll('*')) {
      const o = getComputedStyle(e).overflowY;
      if ((o === 'auto' || o === 'scroll') && e.scrollHeight > e.clientHeight) h += e.scrollHeight - e.clientHeight;
    }
    return Math.max(h, 0);
  });
  let extra = 0;
  for (let i = 0; i < 5; i++) {
    const total = Math.min(orig.height + extra + await need(), MAX);
    if (total <= orig.height + extra) break; // stopped growing
    extra = total - orig.height;
    await page.setViewportSize({width: orig.width, height: total});
    await page.waitForTimeout(300);
  }
  await page.screenshot({path: '/abs/path/<screen>/<viewport>/<state>.png', fullPage: true});
  await page.setViewportSize(orig);
}
```
   Pages taller than the cap are cut off at 16000px: say so in the report for that screen.
   Verified on a 3040px document (3040px image) and on a fixed modal (`max-height:90vh`) holding a 2000px scroller (bottom content captured, viewport back to 800x600). Base and head use the same snippet, so heights may differ; the diff pads to the larger size and reports `size_mismatch`. Set `full_page: false` on a screen in config to opt out and take a plain viewport shot with `playwright-cli -s=head-desktop screenshot --filename=...`.

## Dark mode

Only when config `dark_mode` is an object (absent or `false` means light only). Capture each chosen state a second time as `<state>--dark.png` in the same viewport folder, on base and head alike, in its own session (`-s=head-desktop-dark`) so the theme does not leak into light captures. Set the theme before `goto` where possible, then reload once if the app reads it at load:

```bash
# method "media": prefers-color-scheme
playwright-cli -s=head-desktop-dark run-code "async page => { await page.emulateMedia({colorScheme: 'dark'}); }"
# method "class" / "attribute": run after each goto (and again after a reload)
playwright-cli -s=head-desktop-dark run-code "async page => { await page.evaluate(() => document.documentElement.classList.add('dark')); }"
playwright-cli -s=head-desktop-dark run-code "async page => { await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'dark')); }"
# config dark_mode.storage: write before goto, via an init script
playwright-cli -s=head-desktop-dark run-code "async page => { await page.addInitScript(() => localStorage.setItem('theme', 'dark')); }"
```

Use the class, attribute and key names from config. Verify once per session: `playwright-cli -s=NAME eval "getComputedStyle(document.body).backgroundColor"` should differ from the light session's value; if equal, the method is wrong and every dark diff is meaningless. Freeze, full-page and state recipes work unchanged. Dark does not apply to motion clips unless the diff is dark-specific.

## States

For each screen, loop its `states`. `default` is the page after load. Other states replay the recipe steps (manifest `recipes`, else config `steps`) before screenshotting:

- Recipes start from a page (the screen's route or a starting page named in the recipe) and use `fill`/`click` through the real UI, so a state reached by a form is captured by submitting that form.
- hover: `playwright-cli -s=S hover <ref-or-selector>` (skipped on touch viewports, use tap/click there)
- open menu/modal: click the trigger and `wait_for` the panel selector
- error: trigger via the recipe (invalid input submit) or `page.route` returning an error
- empty: use the seed variant or intercept the list endpoint with an empty array

Reload the route between states so one state's changes do not leak into the next. If a recipe fails on a screen, take a snapshot (`playwright-cli snapshot`) to find the new selector, fix the recipe in the manifest, and mention it in the report.

## Motion

Stills are always produced for motion items: name them `<state>-start.png`, `<state>-mid.png`, `<state>-end.png` (for example `menu-open-mid.png`) at the same viewport, taken at 0 ms, about half the transition duration and after the duration. Do not inject the freeze CSS for these; instead trigger the interaction and call `page.waitForTimeout`.

Record a clip only when at least one holds: the diff touches `transition`, `animation`, `@keyframes`, `transform` timing, gesture handlers or animation libraries in a screen's deps; ripple reasoning flagged it; the manifest `motion` list has an entry for a changed file's screen. Keep clips short (under 5 seconds, 1 viewport, one interaction).

Write one script per interaction and replay the same script on base and head so timing matches:

```js
// $WORK/motion-menu.js  (run with: playwright-cli -s=S run-code --filename=$WORK/motion-menu.js; verified on the fixture, produces a webm)
async page => {
  await page.screencast.start({ path: '/abs/path/to/clip.webm', size: { width: 1280, height: 720 } });
  await page.hover('nav .menu-toggle'); // use the screen's real selector from the recipe
  await page.waitForTimeout(1200);
  await page.screencast.stop();
}
```

Use an absolute output path and generate the file with the path substituted for each side. If the selector does not match, the script times out after 30 s without stopping the screencast; close the session and rerun. Save clips as `$WORK/<side>/<screen>/<viewport>/<state>-<side>.webm` (the side in the file name keeps base and head clips from overwriting each other) and pass base and head clips to `build_report.py` as `clips` (head first, base second when both exist) along with the three stills. If the motion change has no still difference (like the fixture's c3 dropdown timing), the item is classified from the clip and the reason says that stills are identical.

## Cleanup
`playwright-cli -s=NAME close` for every session, `kill` the servers you started, remove the base worktree. Keep `$WORK` until the report is built (media gets copied into the audit dir).
