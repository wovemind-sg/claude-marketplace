#!/usr/bin/env python3
"""Capture every web screen/state in one pass: one playwright-cli session per side x viewport x theme, in parallel.

Each session runs one `run-code` call that loops over its jobs: fresh goto of the route, dark setup, freeze CSS,
fonts and network idle, steps, full-page screenshot (the routine in references/web.md). Writes
<work>/<side>/<screen>/<viewport>/<state>[--dark].png plus <state>[--dark].txt (page text) and prints JSON:
written, failed [{session, screen, state, key, error}], redirects [{screen, route, to}], not_found [{side, screen, route}]
(route answered 404, no shot, not a failure), final_urls {<side>/<screen>/<viewport>/<state>: url},
truncated (shots cut at 16000 px). Exit 1 when anything failed.
--only takes output stems (<screen>/<viewport>/<state>[--dark]), the same form as failed entries' keys.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

try:
    from PIL import Image
except ImportError:
    print("Pillow is required: pip install pillow", file=sys.stderr)
    sys.exit(2)

SINGLE_STEPS = ("goto", "click", "hover", "press", "wait_for", "scroll_to")
IPHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
EMULATION_KEYS = ("is_mobile", "has_touch", "device_scale_factor", "user_agent")

# One function expression: run-code wraps the file as `await (<file>)(page)`. __DATA__ is replaced with JSON.
SESSION_JS = r"""async page => {
  const C = __DATA__;
  const out = [];
  const FREEZE = '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important;scroll-behavior:auto!important}';
  const vp = C.viewport;
  let cdp = null;
  // setViewportSize (the full-page routine, resize) drops the CDP override, so it is re-applied per job and per resize.
  const emulate = async height => {
    if (!vp.emulate) return;
    cdp = cdp || await page.context().newCDPSession(page);
    await cdp.send('Emulation.setDeviceMetricsOverride', {width: vp.width, height, deviceScaleFactor: vp.dpr, mobile: vp.mobile});
    await cdp.send('Emulation.setTouchEmulationEnabled', {enabled: vp.touch});
    if (vp.ua) await cdp.send('Emulation.setUserAgentOverride', {userAgent: vp.ua});
  };
  const settle = async () => {
    const d = C.dark;
    if (d && d.method === 'class') await page.evaluate(c => document.documentElement.classList.add(c), d.class || 'dark');
    if (d && d.method === 'attribute') await page.evaluate(([a, v]) => document.documentElement.setAttribute(a, v), [d.attribute || 'data-theme', d.value || 'dark']);
    await page.addStyleTag({content: FREEZE + (C.freeze_css || '')});
    await page.evaluate(() => document.fonts.ready);
    await page.waitForLoadState('networkidle');
  };
  const step = async s => {
    if ('goto' in s) { await page.goto(C.base + s.goto); await settle(); }
    else if ('click' in s) await page.click(s.click);
    else if ('hover' in s) await page.hover(s.hover);
    else if ('fill' in s) await page.fill(s.fill, s.value);
    else if ('press' in s) await page.keyboard.press(s.press);
    else if ('wait_for' in s) await page.waitForSelector(s.wait_for);
    else if ('scroll_to' in s) await page.locator(s.scroll_to).scrollIntoViewIfNeeded();
  };
  const fullPage = async path => {
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
    let extra = 0, cut = false;
    for (let i = 0; i < 5; i++) {
      const want = orig.height + extra + await need();
      const total = Math.min(want, MAX);
      cut = want > MAX;
      if (total <= orig.height + extra) break; // stopped growing
      extra = total - orig.height;
      await page.setViewportSize({width: orig.width, height: total});
      await emulate(total);
      await page.waitForTimeout(300);
    }
    // fullPage alone shoots the whole document, so the cap needs a clip
    await page.screenshot({path, fullPage: true, ...(cut ? {clip: {x: 0, y: 0, width: orig.width, height: MAX}} : {})});
    await page.setViewportSize(orig);
    return cut;
  };
  try {
    const d = C.dark;
    if (d && d.method === 'media') await page.emulateMedia({colorScheme: 'dark'});
    if (d && d.storage) await page.addInitScript(([k, v]) => localStorage.setItem(k, v), [d.storage.key, d.storage.value]);
  } catch (e) {
    return JSON.stringify(C.jobs.map(j => ({key: j.key, error: 'dark setup: ' + String(e.message || e).split('\n')[0]})));
  }
  for (const j of C.jobs) {
    const r = {key: j.key};
    try {
      // a job that threw mid full-page leaves the viewport stretched; reset so it cannot leak into this one
      await page.setViewportSize({width: vp.width, height: vp.height});
      await emulate(vp.height);
      const resp = await page.goto(C.base + j.route);
      if (resp && resp.status() === 404) { r.not_found = true; out.push(r); continue; }
      await settle();
      r.url = await page.evaluate(() => location.href);
      r.width = await page.evaluate(() => innerWidth);
      // html bg, body bg, body text color: many apps keep body transparent and theme the root or the text
      r.bg = await page.evaluate(() => [document.documentElement, document.body].map(e => getComputedStyle(e).backgroundColor)
        .concat(getComputedStyle(document.body).color));
      for (const s of j.steps) await step(s);
      r.text = await page.evaluate(() => document.body.innerText);
      if (j.full_page) r.truncated = await fullPage(j.out);
      else await page.screenshot({path: j.out});
    } catch (e) {
      r.error = String(e.message || e).split('\n')[0];
    }
    out.push(r);
  }
  return JSON.stringify(out);
}
"""


def step_error(s):
    if isinstance(s, dict) and ((len(s) == 1 and next(iter(s)) in SINGLE_STEPS) or set(s) == {"fill", "value"}):
        return None
    return (f"unknown step shape {json.dumps(s)}; accepted: "
            + ", ".join(f'{{"{k}": ...}}' for k in SINGLE_STEPS) + ', {"fill": selector, "value": text}')


def viewport_info(v):
    emu = any(k in v for k in EMULATION_KEYS)
    return {"width": v["width"], "height": v["height"], "emulate": emu, "dpr": v.get("device_scale_factor", 1),
            "mobile": bool(v.get("is_mobile")), "touch": bool(v.get("has_touch")),
            "ua": v.get("user_agent") or (IPHONE_UA if v.get("is_mobile") else None)}


def safe_name(kind, n):
    """Config/manifest names become path parts under --work; the repo is untrusted, so no '/', '..' or absolute paths."""
    if not (isinstance(n, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", n) and ".." not in n):
        raise ValueError(f"{kind} name {json.dumps(n)} must be letters, digits, '-', '_' or '.', no '..'")
    return n


def build_plan(config, manifest, sides, work, screens=None, themes="light", only=None):
    """Sessions {name: {side, base, viewport, viewport_name, dark, jobs}}; job key = <screen>/<viewport>/<state>[--dark]."""
    cfg_screens = config.get("screens", [])
    for s in cfg_screens:
        safe_name("screen", s["name"])
        for st in s.get("states", []):
            safe_name("state", st["name"])
    for v in config["viewports"]:
        safe_name("viewport", v)
    for e in (manifest.get("screens") or {}).values():
        for n in (e.get("recipes") or {}):
            safe_name("recipe", n)
    names = [s["name"] for s in cfg_screens]
    unknown = sorted(set(screens or []) - set(names))
    if unknown:
        raise ValueError(f"--screens names not in config: {', '.join(unknown)}")
    selected = [s for s in cfg_screens if not screens or s["name"] in screens]
    recipes = {n: (e.get("recipes") or {}) for n, e in (manifest.get("screens") or {}).items()}
    dark_cfg = config.get("dark_mode") if isinstance(config.get("dark_mode"), dict) else None
    want_dark = dark_cfg is not None and themes == "light+dark"
    sessions = {}
    for side, base in sides:
        for vname, v in config["viewports"].items():
            for dark in ([False, True] if want_dark else [False]):
                jobs = []
                for s in selected:
                    if dark and s.get("dark") is False:
                        continue
                    states = {st["name"]: st for st in s.get("states", [{"name": "default"}])}
                    rec = recipes.get(s["name"], {})
                    for name in list(states) + [n for n in rec if n not in states]:
                        st = states.get(name, {})
                        if st.get("viewports") and vname not in st["viewports"]:
                            continue
                        if dark and "dark" not in st.get("themes", ["light", "dark"]):
                            continue
                        stem = name + ("--dark" if dark else "")
                        key = f"{s['name']}/{vname}/{stem}"
                        if only and key not in only:
                            continue
                        steps = list(s.get("nav_steps", [])) + list(rec.get(name, st.get("steps", [])))
                        job = {"key": key, "screen": s["name"], "state": stem, "route": s.get("route") or "/",
                               "steps": steps, "full_page": s.get("full_page", True),
                               "out": os.path.join(work, side, s["name"], vname, stem + ".png")}
                        errs = [e for e in map(step_error, steps) if e]
                        if errs:
                            job["error"] = errs[0]
                        jobs.append(job)
                if jobs:
                    sessions[f"{side}-{vname}" + ("-dark" if dark else "")] = {
                        "side": side, "base": base.rstrip("/"), "viewport_name": vname,
                        "viewport": viewport_info(v), "dark": dark_cfg if dark else None, "jobs": jobs}
    return sessions


def parse_result(stdout):
    """run-code prints the returned string JSON-encoded on the line after '### Result'."""
    lines = stdout.splitlines()
    if "### Result" not in lines:
        raise ValueError("no result from run-code: " + stdout.strip()[-500:])
    return json.loads(json.loads(lines[lines.index("### Result") + 1]))


def redirect_target(final_url, own_screen, routes):
    """Screen whose route (path + query) the page ended on, other than its own; None if none."""
    def norm(u):
        p = urlsplit(u)
        return (p.path or "/") + ("?" + p.query if p.query else "")
    at = norm(final_url)
    if own_screen in routes and norm(routes[own_screen]) == at:
        return None  # stayed on its own route, even if another screen shares it
    return next((n for n, r in routes.items() if n != own_screen and norm(r) == at), None)


def collect(sessions, results, routes):
    """Check and record each session's job results; results[name] is a list of job results or an error string."""
    rep = {"written": [], "failed": [], "redirects": [], "not_found": [], "final_urls": {}, "truncated": []}
    by_key = {}
    for name, sess in sessions.items():
        res = results.get(name)
        got = {r["key"]: r for r in res} if isinstance(res, list) else {}
        for j in sess["jobs"]:
            by_key[(name, j["key"])] = j.get("error") and {"error": j["error"]} or got.get(
                j["key"], {"error": res if isinstance(res, str) else "no result for this job"})
    # A dark method that changes nothing on any side is wrong; one side matching (a base without dark CSS) is fine.
    verdicts = {}
    for name, sess in sessions.items():
        if not sess["dark"]:
            continue
        light = name[:-len("-dark")]
        pairs = [(by_key[(name, j["key"])].get("bg"), by_key.get((light, j["key"][:-len("--dark")]), {}).get("bg"))
                 for j in sess["jobs"]]
        pairs = [p for p in pairs if p[0] and p[1]]
        verdicts.setdefault(sess["viewport_name"], []).append(
            (sess["side"], bool(pairs) and all(a == b for a, b in pairs)))
    # a base-only call (head+base-related) cannot judge: the base may predate dark mode
    bad_dark = {v for v, vs in verdicts.items() if all(b for _, b in vs) and any(s != "base" for s, _ in vs)}
    for name, sess in sessions.items():
        for j in sess["jobs"]:
            r = by_key[(name, j["key"])]

            def fail(msg):
                rep["failed"].append({"session": name, "screen": j["screen"], "state": j["state"], "key": j["key"],
                                      "error": msg})
                # diff_images.py walks the tree, so a failed item's shot (or one left from an earlier run) must go
                for p in (j["out"], j["out"][:-4] + ".txt"):
                    if os.path.exists(p):
                        os.remove(p)
            if r.get("error"):
                fail(r["error"])
                continue
            if r.get("not_found"):
                nf = {"side": sess["side"], "screen": j["screen"], "route": j["route"]}
                if nf not in rep["not_found"]:
                    rep["not_found"].append(nf)
                continue
            png, width = j["out"], sess["viewport"]["width"]
            if r["width"] != width:
                fail(f"innerWidth {r['width']}, expected {width}: viewport or emulation did not apply")
                continue
            if sess["dark"] and sess["viewport_name"] in bad_dark:
                fail(f"dark_mode {json.dumps(sess['dark'])} left the page background and text color unchanged on "
                     "every side: wrong method")
                continue
            if j["state"].removesuffix("--dark") == "default" and j["screen"] in routes:
                rep["final_urls"][f"{sess['side']}/{j['key']}"] = r["url"]
                to = redirect_target(r["url"], j["screen"], routes)
                if to:
                    red = {"screen": j["screen"], "route": j["route"], "to": to}
                    if red not in rep["redirects"]:
                        rep["redirects"].append(red)
                    if os.path.exists(png):
                        os.remove(png)
                    continue
            if not os.path.exists(png):
                fail("screenshot missing")
                continue
            with Image.open(png) as im:
                got_w = im.size[0]
            if got_w != width:
                fail(f"screenshot is {got_w} px wide, expected {width}")
                continue
            with open(png[:-4] + ".txt", "w") as f:
                f.write(r.get("text") or "")
            rep["written"].append(png)
            if r.get("truncated"):
                rep["truncated"].append(png)
    return rep


def cli(work, sess, *args):
    for attempt in range(2):
        p = subprocess.run(["playwright-cli", f"-s={sess}", *args], cwd=work, capture_output=True, text=True)
        if not (p.returncode and "is not open" in p.stdout + p.stderr) or attempt:
            break
        time.sleep(1)  # `open` can answer "not open" on the very next command
    # line match: page text inside a run-code result may contain "### Error"; stdout last so the
    # error is not cut off behind stderr's update banner
    if p.returncode or "### Error" in p.stdout.splitlines():
        raise RuntimeError(f"playwright-cli {args[0]}: " + (p.stderr + p.stdout).strip()[-500:])
    return p.stdout


def run_session(work, name, sess, storage_state):
    jobs = [j for j in sess["jobs"] if not j.get("error")]
    if not jobs:
        return []
    data = {"base": sess["base"], "viewport": sess["viewport"], "dark": sess["dark"],
            "freeze_css": sess.get("freeze_css"), "jobs": jobs}
    js = os.path.join(work, name + ".js")
    for j in jobs:
        os.makedirs(os.path.dirname(j["out"]), exist_ok=True)
    try:
        cli(work, name, "open")
        if storage_state:
            cli(work, name, "state-load", storage_state)
        cli(work, name, "resize", str(sess["viewport"]["width"]), str(sess["viewport"]["height"]))
        with open(js, "w") as f:
            f.write(SESSION_JS.replace("__DATA__", json.dumps(data)))
        return parse_result(cli(work, name, "run-code", f"--filename={js}"))
    except Exception as e:
        return f"session {name}: {e}"
    finally:
        subprocess.run(["playwright-cli", f"-s={name}", "close"], cwd=work, capture_output=True)


def selftest():
    config = {
        "viewports": {"desktop": {"width": 1440, "height": 900},
                      "mobile": {"width": 390, "height": 844, "device_scale_factor": 3, "is_mobile": True, "has_touch": True}},
        "dark_mode": {"method": "media"},
        "screens": [
            {"name": "home", "route": "/index.html", "states": [
                {"name": "default"},
                {"name": "menu", "steps": [{"click": ".m"}], "viewports": ["desktop"]},
                {"name": "light-only", "themes": ["light"]}]},
            {"name": "login", "route": "/login.html", "states": [{"name": "default"}]},
            {"name": "plain", "route": "/p", "dark": False, "full_page": False, "states": [{"name": "default"}]},
            {"name": "old", "route": "/old.html", "states": [{"name": "default"}]},
        ]}
    manifest = {"screens": {"login": {"recipes": {
        "default": [], "err": [{"fill": "#c", "value": "x"}, {"click": "button"}, {"wait_for": "#err"}],
        "bad": [{"tap": "#c"}]}}, "home": {"recipes": {"menu": [{"click": ".menu"}]}}}}
    with tempfile.TemporaryDirectory() as w:
        sides = [("head", "http://h:1/"), ("base", "http://b:2")]
        s = build_plan(config, manifest, sides, w, screens=["home", "login", "plain", "old"], themes="light+dark")
        assert sorted(s) == sorted(f"{a}-{v}{d}" for a in ("head", "base") for v in ("desktop", "mobile")
                                   for d in ("", "-dark")), sorted(s)
        keys = lambda n: [j["key"] for j in s[n]["jobs"]]
        assert keys("head-desktop") == ["home/desktop/default", "home/desktop/menu", "home/desktop/light-only",
                                        "login/desktop/default", "login/desktop/err", "login/desktop/bad",
                                        "plain/desktop/default", "old/desktop/default"], keys("head-desktop")
        assert "home/mobile/menu" not in keys("head-mobile")  # viewport filter
        assert keys("head-mobile-dark") == ["home/mobile/default--dark", "login/mobile/default--dark",
                                            "login/mobile/err--dark", "login/mobile/bad--dark",
                                            "old/mobile/default--dark"], keys("head-mobile-dark")
        jd = {j["key"]: j for j in s["head-desktop"]["jobs"]}
        assert jd["home/desktop/menu"]["steps"] == [{"click": ".menu"}]  # manifest recipe wins
        assert jd["login/desktop/err"]["steps"][0] == {"fill": "#c", "value": "x"} and "error" not in jd["login/desktop/err"]
        assert "unknown step shape" in jd["login/desktop/bad"]["error"]
        assert jd["plain/desktop/default"]["full_page"] is False
        assert s["head-desktop"]["base"] == "http://h:1" and s["head-mobile"]["viewport"]["emulate"]
        assert s["head-mobile"]["viewport"]["dpr"] == 3 and not s["head-desktop"]["viewport"]["emulate"]
        assert s["base-desktop-dark"]["jobs"][0]["out"] == os.path.join(w, "base/home/desktop/default--dark.png")
        assert sorted(build_plan(config, manifest, sides, w, themes="light")) == sorted(
            f"{a}-{v}" for a in ("head", "base") for v in ("desktop", "mobile"))
        assert list(build_plan(dict(config, dark_mode=False), manifest, sides[:1], w, themes="light+dark")) == [
            "head-desktop", "head-mobile"]
        only = build_plan(config, manifest, sides, w, themes="light+dark", only={"login/mobile/err--dark"})
        assert list(only) == ["head-mobile-dark", "base-mobile-dark"], list(only)
        try:
            build_plan(config, manifest, sides, w, screens=["nope"])
            raise AssertionError("unknown screen accepted")
        except ValueError:
            pass
        for bad in ({"screens": [{"name": "../x"}]}, {"screens": [{"name": "/etc"}]},
                    {"screens": [{"name": "x", "states": [{"name": "a/../../b"}]}]}, {"viewports": {"..": {}}}):
            try:
                build_plan(dict(config, **bad), manifest, sides, w)
                raise AssertionError(f"path name accepted: {bad}")
            except ValueError:
                pass
        try:
            build_plan(config, {"screens": {"home": {"recipes": {"../../evil": []}}}}, sides, w)
            raise AssertionError("path recipe name accepted")
        except ValueError:
            pass

        out ='banner\n### Result\n"[{\\"key\\":\\"a\\",\\"text\\":\\"x\\\\ny\\"}]"\n### Ran Playwright code\n'
        assert parse_result(out) == [{"key": "a", "text": "x\ny"}]
        routes = {"verify": "/verify.html", "sched": "/schedule.html?token=abc", "old": "/old.html"}
        assert redirect_target("http://h:1/verify.html", "old", routes) == "verify"
        assert redirect_target("http://h:1/old.html", "old", routes) is None
        assert redirect_target("http://h:1/schedule.html?token=abc", "old", routes) == "sched"
        assert redirect_target("http://h:1/schedule.html", "old", routes) is None
        assert redirect_target("http://h:1/old.html", "old", dict(routes, alias="/old.html")) is None  # shared route
        bare = build_plan({"viewports": {"d": {"width": 9, "height": 9}}, "screens": [{"name": "x", "route": "/x"}]},
                          {}, sides[:1], w)
        assert [j["key"] for j in bare["head-d"]["jobs"]] == ["x/d/default"]  # no states: default only

        # collect: fake a run of the head and base desktop sessions (light + dark)
        sel = {n: s[n] for n in ("head-desktop", "head-desktop-dark", "base-desktop", "base-desktop-dark")}
        results = {}
        for n, sess in sel.items():
            rs = []
            for j in sess["jobs"]:
                if j.get("error"):
                    continue
                dark_bg = n == "head-desktop-dark"
                r = {"key": j["key"], "url": "http://h:1" + j["route"], "width": 1440, "text": "t " + j["key"],
                     "bg": "rgb(17, 17, 17)" if dark_bg else "rgb(255, 255, 255)"}
                if j["screen"] == "old" and n.startswith("head"):
                    r["url"] = "http://h:1/verify.html"
                if j["key"] == "home/desktop/menu":
                    r = {"key": j["key"], "error": "Timeout 30000ms exceeded"}
                if j["screen"] == "login" and n.startswith("base"):
                    r = {"key": j["key"], "not_found": True}
                if "error" not in r and "not_found" not in r:
                    os.makedirs(os.path.dirname(j["out"]), exist_ok=True)
                    Image.new("RGB", (1440 if j["screen"] != "plain" else 1000, 50)).save(j["out"])
                rs.append(r)
            results[n] = rs
        rep = collect(sel, results, routes)
        failed = {(f["session"], f["key"]): f["error"] for f in rep["failed"]}
        assert "unknown step shape" in failed[("head-desktop", "login/desktop/bad")]
        assert failed[("head-desktop", "home/desktop/menu")].startswith("Timeout")
        assert "1000 px wide" in failed[("head-desktop", "plain/desktop/default")]
        assert not os.path.exists(os.path.join(w, "head/plain/desktop/default.png"))  # failed shot removed
        assert not any("dark_mode" in e for e in failed.values()), failed  # base matching light is fine
        assert rep["redirects"] == [{"screen": "old", "route": "/old.html", "to": "verify"}], rep["redirects"]
        assert not os.path.exists(os.path.join(w, "head/old/desktop/default.png"))
        assert not os.path.exists(os.path.join(w, "head/old/desktop/default--dark.png"))
        assert os.path.exists(os.path.join(w, "base/old/desktop/default.png"))
        assert rep["not_found"] == [{"side": "base", "screen": "login", "route": "/login.html"}], rep["not_found"]
        hp = os.path.join(w, "head/home/desktop/default.png")
        assert hp in rep["written"] and open(hp[:-4] + ".txt").read() == "t home/desktop/default"
        assert rep["final_urls"]["head/old/desktop/default"] == "http://h:1/verify.html"
        # same background in dark and light on every side: the dark method is wrong
        for r in results["head-desktop-dark"]:
            r["bg"] = "rgb(255, 255, 255)"
        rep = collect(sel, results, routes)
        assert any("wrong method" in f["error"] for f in rep["failed"] if f["session"] == "head-desktop-dark")
        rep = collect({n: sel[n] for n in ("base-desktop", "base-desktop-dark")}, results, routes)
        assert not any("wrong method" in f["error"] for f in rep["failed"])  # base-only call cannot judge
        rep = collect({"head-desktop": s["head-desktop"]}, {"head-desktop": "session head-desktop: boom"}, routes)
        assert len(rep["failed"]) == len(s["head-desktop"]["jobs"]) and not rep["written"]
    print(json.dumps({"selftest": "ok"}))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config"); ap.add_argument("--manifest"); ap.add_argument("--work")
    ap.add_argument("--side", action="append", default=[], help="name=base_url, e.g. head=http://localhost:8123")
    ap.add_argument("--screens", help="comma-separated screen names (default: every config screen)")
    ap.add_argument("--themes", choices=["light", "light+dark"], default="light")
    ap.add_argument("--only", nargs="+", help="output stems <screen>/<viewport>/<state>[--dark] to (re)capture")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.config and a.work and a.side):
        ap.error("--config, --work and at least one --side are required")
    config = json.load(open(a.config))
    manifest = json.load(open(a.manifest)) if a.manifest and os.path.exists(a.manifest) else {}
    sides = [tuple(s.split("=", 1)) for s in a.side]
    if any(len(s) != 2 for s in sides):
        ap.error("--side takes name=base_url")
    work = os.path.abspath(a.work)
    os.makedirs(work, exist_ok=True)
    screens = a.screens.split(",") if a.screens else None
    try:
        sessions = build_plan(config, manifest, sides, work, screens, a.themes, set(a.only) if a.only else None)
    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    web = config.get("web") or {}
    storage = os.path.abspath(web["storage_state"]) if web.get("storage_state") else None
    for sess in sessions.values():
        sess["freeze_css"] = web.get("freeze_css")
    with ThreadPoolExecutor(max_workers=max(len(sessions), 1)) as ex:
        futs = {n: ex.submit(run_session, work, n, sess, storage) for n, sess in sessions.items()}
        results = {n: f.result() for n, f in futs.items()}
    routes = {s["name"]: s["route"] for s in config.get("screens", [])
              if s.get("route") and (not screens or s["name"] in screens)}
    rep = collect(sessions, results, routes)
    print(json.dumps(rep, indent=2))
    sys.exit(1 if rep["failed"] else 0)


if __name__ == "__main__":
    main()
