#!/usr/bin/env python3
"""Build a self-contained UI audit page (index.html) and a short report.md.

Usage: build_report.py --spec audit.json --out DIR [--password PW]   |   build_report.py --selftest
--password also writes OUT/_worker.js, a Cloudflare Pages worker that answers 401 unless the request carries
Basic Auth (any username) with that password. Only the SHA-256 of the password is embedded, never the plaintext.

Spec JSON (paths are absolute or relative to the spec file):
{
  "meta": {"pr": 12, "head_sha": "...", "base_sha": "...", "baseline_mode": "base+head" | "head-only",
           "project": "repo name", "incremental_from": "<sha>|null", "reused_screens": ["name", ...],
           "dep_hashes": {"<screen>": "<dep_hash.py new_hashes value>"}, "summary": "short PR description"},
  "items": [{"screen", "platform", "viewport", "state", "classification": "intentional|unintended|needs_review",
             "reason": "one line", "route": "/path", "head_hash": "<diff_images.py hashes value>",
             "captured_sha": "defaults to meta.head_sha", "dep_hash": "<screen's dep hash when captured>",
             "base_img", "head_img", "diff_img", "changed_pct",
             "clips": ["a.webm"], "stills": {"start": "p.png", "mid": "p.png", "end": "p.png"}}],
  "redirects": [{"screen": "old", "route": "/old", "to": "target-screen"}]
}
base_img/diff_img/changed_pct are omitted for head-only items. Media is copied into OUT/media/.
If OUT/history.json exists, a new item replaces only the old item with the same (screen, platform,
viewport, state). An old item is kept (marked "reused": true) only if its screen is in meta.reused_screens, its
stored dep_hash equals meta.dep_hashes[screen] and its key is not re-captured; every other old item is dropped
and its media listed in stale_media. The run is appended to the history list.
Dedupe: new items with the same (platform, viewport, head_hash, changed_pct) become one card (the first in sort
order); the others' route (or screen) goes in its "also_at", and each redirect adds "<route> (redirects to <to>)"
to the target screen's cards.
Self-check (exit 1, nothing written, all problems on stderr): a card whose captured_sha != meta.head_sha that is
not a valid reuse.
Prints JSON {index, report, items, runs, stale_media} on stdout;
stale_media lists the media paths (relative to OUT) of dropped old items, for the publisher to delete.
"""
import argparse
import hashlib
import html
import json
import os
import re
import shutil
import sys
import tempfile

ORDER = {"unintended": 0, "needs_review": 1, "intentional": 2}
CLASSES = list(ORDER)


def slug(s):
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(s)).strip("-") or "x"


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def copy_media(item, idx, spec_dir, out):
    """Copy every media path of item into OUT/media/<idx>-.../ and rewrite to relative paths."""
    d = os.path.join("media", f"{idx}-{slug(item['screen'])}-{slug(item['viewport'])}-{slug(item.get('state', 'default'))}")

    used = {}  # dst_rel -> src, so clips/stills sharing a basename (base vs head) are not overwritten

    def cp(p):
        if not p:
            return None
        src = p if os.path.isabs(p) else os.path.join(spec_dir, p)
        if not os.path.isfile(src):
            fail(f"media file not found: {src}")
        dst_rel = os.path.join(d, os.path.basename(src))
        n = 1
        while used.get(dst_rel, src) != src:
            n += 1
            stem, ext = os.path.splitext(os.path.basename(src))
            dst_rel = os.path.join(d, f"{stem}-{n}{ext}")
        used[dst_rel] = src
        dst = os.path.join(out, dst_rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.abspath(src) != os.path.abspath(dst):
            shutil.copyfile(src, dst)
        return dst_rel.replace(os.sep, "/")

    for k in ("base_img", "head_img", "diff_img"):
        item[k] = cp(item.get(k))
    item["clips"] = [cp(c) for c in item.get("clips") or []]
    item["stills"] = {k: cp(v) for k, v in (item.get("stills") or {}).items()}


def validate(spec):
    if not isinstance(spec, dict) or "items" not in spec or "meta" not in spec:
        fail("spec needs 'meta' and 'items'")
    for i in spec["items"]:
        for k in ("screen", "platform", "viewport", "classification", "head_img"):
            if not i.get(k):
                fail(f"item missing '{k}': {i}")
        if i["classification"] not in ORDER:
            fail(f"bad classification '{i['classification']}'")
        i.setdefault("state", "default")
        i.setdefault("captured_sha", spec["meta"].get("head_sha"))


def _key(i):
    return (i["screen"], i["platform"], i["viewport"], i.get("state") or "default")


def media_of(i):
    return [p for p in (i.get("base_img"), i.get("head_img"), i.get("diff_img"), *(i.get("clips") or []), *(i.get("stills") or {}).values()) if p]


def merge_history(prev, new_items, meta):
    """Keep an old item (reused: true) only if its screen is reused, its dep_hash still matches and its key is
    not re-captured. Returns (items, runs, stale_media) where stale_media are the media paths of dropped old items."""
    redone = {i["screen"] for i in new_items}
    keys = {_key(i) for i in new_items}
    reused, hashes = meta.get("reused_screens") or [], meta.get("dep_hashes") or {}
    kept, stale = [], []
    for i in prev.get("items", []):
        if i["screen"] in reused and i.get("dep_hash") and i["dep_hash"] == hashes.get(i["screen"]) and _key(i) not in keys:
            kept.append({**i, "reused": True})
        else:
            stale += media_of(i)
    runs = prev.get("runs", []) + [{k: meta.get(k) for k in ("head_sha", "base_sha", "baseline_mode", "incremental_from")}
                                   | {"recaptured": sorted(redone), "reused": reused}]
    return kept + new_items, runs, sorted(set(stale))


def dedupe(items):
    """Merge items with identical pixels (platform, viewport, head_hash, changed_pct); returns the kept items."""
    first, out = {}, []
    for i in items:
        k = (i["platform"], i["viewport"], i.get("head_hash"), i.get("changed_pct"))
        if not i.get("head_hash") or k not in first:
            first[k] = i
            out.append(i)
        else:
            f = first[k]
            f["also_at"] = f.get("also_at", []) + [i.get("route") or i["screen"], *i.get("also_at", [])]
    return out


def add_redirects(items, redirects):
    for r in redirects:
        txt = f"{r['route']} (redirects to {r['to']})"
        for i in items:
            if i["screen"] == r["to"] and txt not in i.get("also_at", []):
                i["also_at"] = i.get("also_at", []) + [txt]


def self_check(items, meta):
    """List of problems; build refuses to write anything when non-empty."""
    return [f"{i['screen']}/{i['viewport']}/{i['state']} captured at {str(i['captured_sha'])[:8]}, not head {str(meta.get('head_sha'))[:8]}"
            for i in items if not i.get("reused") and i["captured_sha"] != meta.get("head_sha")]


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#fff;--fg:#1a1a1a;--muted:#666;--line:#ddd;--card:#f6f6f7;--unintended:#c62828;--needs_review:#b26a00;--intentional:#2e7d32}
@media (prefers-color-scheme:dark){:root{--bg:#141415;--fg:#eee;--muted:#999;--line:#333;--card:#1e1e20;--unintended:#ef5350;--needs_review:#ffb74d;--intentional:#66bb6a}}
*{box-sizing:border-box}body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:16px/1.4 system-ui,sans-serif;max-width:1200px;margin-inline:auto}
h1{font-size:1.4rem;margin:.2em 0}.meta{color:var(--muted);font-size:.9rem}
.bar{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}select,button{font:inherit;font-size:16px;padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}
button[aria-pressed=true]{outline:2px solid var(--fg)}
.item{border:1px solid var(--line);border-radius:8px;padding:12px;margin:14px 0;background:var(--card)}
.item h2{font-size:1.05rem;margin:0 0 4px}.tag{font-size:.75rem;font-weight:600;padding:2px 8px;border-radius:99px;border:1px solid currentColor;margin-left:6px}
.tag.unintended{color:var(--unintended)}.tag.needs_review{color:var(--needs_review)}.tag.intentional{color:var(--intentional)}
.modes{display:flex;gap:6px;margin:8px 0;flex-wrap:wrap}
.view img,video{max-width:100%;height:auto;display:block}.view img{width:auto;max-height:calc(var(--fit,95vh) * var(--z,1))}
.zoom{display:flex;gap:6px;margin-left:auto}
.slider{display:grid;position:relative;width:fit-content;max-width:100%;touch-action:pan-y}
.slider>img,.slider>.wm,.slider .top{grid-area:1/1}.slider .top{overflow:hidden;position:relative}
.wm{position:absolute;top:0;left:0;margin:8px;padding:2px 8px;border-radius:4px;background:rgba(0,0,0,.55);color:#fff;font-size:.8rem;font-weight:600;pointer-events:none}.top .wm{left:auto;right:0}.slider .top img{width:100%;max-width:none}
.slider input{grid-row:2;width:0;min-width:100%;margin:6px 0 0}
.side{display:flex;gap:10px}.side figure{margin:0;flex:1 1 0;min-width:0}figcaption{font-size:.8rem;color:var(--muted)}
.stills{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}.stills img{max-width:30%}
.empty{color:var(--muted)}#summary{overflow-wrap:anywhere;max-height:30vh;overflow-y:auto;white-space:pre-line}ul{padding-left:1.2em}
</style></head><body>
<h1>UI audit</h1><div class="meta" id="meta"></div><p id="summary" hidden></p>
<div class="bar"><select id="fp" aria-label="Platform"></select><select id="fv" aria-label="Viewport"></select><select id="fc" aria-label="Classification"></select></div>
<div id="items"></div>
<h2>Run history</h2><ul id="runs"></ul>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent),$=s=>document.querySelector(s);
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const m=D.meta,headOnly=m.baseline_mode==='head-only';
$('#meta').textContent=`PR ${m.pr??'-'} · head ${(m.head_sha||'').slice(0,8)} · base ${(m.base_sha||'-').slice(0,8)} · mode ${m.baseline_mode}`+(m.incremental_from?` · incremental from ${m.incremental_from.slice(0,8)}`:'')+(m.reused_screens&&m.reused_screens.length?` · reused: ${m.reused_screens.join(', ')}`:'');
if(m.summary){$('#summary').textContent=m.summary;$('#summary').hidden=false}
function fill(id,label,key){const v=[...new Set(D.items.map(i=>i[key]))];$(id).innerHTML=`<option value="">${label}: all</option>`+v.map(x=>`<option>${E(x)}</option>`).join('')}
fill('#fp','Platform','platform');fill('#fv','Viewport','viewport');fill('#fc','Classification','classification');
['#fp','#fv','#fc'].forEach(s=>$(s).onchange=render);
const img=(p,a)=>`<img src="${E(p)}" alt="${E(a)}" loading="lazy">`;
function body(i,mode){
 if(headOnly||!i.base_img)return `<p class="meta">Head only: no baseline captured, nothing to compare.</p>${img(i.head_img,'head')}`;
 if(mode==='side')return `<div class="side"><figure>${img(i.base_img,'before')}<figcaption>Before</figcaption></figure><figure>${img(i.head_img,'after')}<figcaption>After</figcaption></figure></div>`;
 if(mode==='diff')return i.diff_img?`${img(i.diff_img,'diff overlay')}<div class="meta">Diff overlay</div>`:'<p class="empty">No diff overlay for this item.</p>';
 return `<div class="slider">${img(i.base_img,'before')}<span class="wm">Before</span><div class="top" style="clip-path:inset(0 0 0 50%)">${img(i.head_img,'after')}<span class="wm">After</span></div><input type="range" min="0" max="100" value="50" aria-label="Before/after slider"></div>`}
function motion(i){let h='';if(i.clips&&i.clips.length)h+=i.clips.map(c=>`<video controls muted loop playsinline src="${E(c)}"></video>`).join('');
 const s=i.stills||{};if(Object.keys(s).length)h+=`<div class="stills">`+['start','mid','end'].filter(k=>s[k]).map(k=>`<figure style="margin:0">${img(s[k],k)}<figcaption>${k}</figcaption></figure>`).join('')+`</div>`;return h?`<h3>Motion</h3>${h}`:''}
function render(){
 const f={platform:$('#fp').value,viewport:$('#fv').value,classification:$('#fc').value};
 const list=D.items.filter(i=>Object.keys(f).every(k=>!f[k]||i[k]===f[k]));
 $('#items').innerHTML=list.length?'':'<p class="empty">No items match.</p>';
 list.forEach(i=>{const d=document.createElement('section');d.className='item';let mode='slider';
  const pct=i.changed_pct!=null?` · ${(+i.changed_pct).toFixed(2)}% changed`:'';
  d.innerHTML=`<h2>${E(i.screen)} <span class="tag ${i.classification}">${i.classification.replace('_',' ')}</span></h2><div class="meta">${E(i.platform)} · ${E(i.viewport)} · ${E(i.state)}${pct}</div><div class="meta">Captured at ${E((i.captured_sha||'').slice(0,8))}${i.reused?' · reused, files unchanged':''}</div>${(i.also_at||[]).length?`<div class="meta">Also at: ${i.also_at.map(E).join(', ')}</div>`:''}<p>${E(i.reason)}</p>`+
  `<div class="modes">${headOnly||!i.base_img?'':[['slider','Slider'],['side','Side by side'],['diff','Diff overlay']].map(([k,l])=>`<button data-m="${k}" aria-pressed="${k===mode}">${l}</button>`).join('')}<div class="zoom"><button data-z="-1" aria-label="Decrease image height">−</button><button data-z="0">Fit to screen</button><button data-z="1" aria-label="Increase image height">+</button></div></div><div class="view"></div>`+motion(i);
  const v=d.querySelector('.view');const draw=()=>{v.innerHTML=body(i,mode);const r=v.querySelector('input');if(r)r.oninput=()=>v.querySelector('.top').style.clipPath=`inset(0 0 0 ${r.value}%)`};
  d.querySelectorAll('[data-m]').forEach(b=>b.onclick=()=>{mode=b.dataset.m;d.querySelectorAll('[data-m]').forEach(x=>x.setAttribute('aria-pressed',x===b));draw()});
  // Fit: card header + image + slider/caption row (~40px) + card padding fits the window height.
  d.fit=()=>d.style.setProperty('--fit',Math.max(120,innerHeight-(v.getBoundingClientRect().top-d.getBoundingClientRect().top)-60)+'px');
  let z=1;d.querySelectorAll('[data-z]').forEach(b=>b.onclick=()=>{const k=+b.dataset.z;z=k?Math.max(.25,z*(k>0?1.25:.8)):1;d.style.setProperty('--z',z)});
  draw();$('#items').appendChild(d);d.fit()})}
addEventListener('resize',()=>document.querySelectorAll('.item').forEach(d=>d.fit()));
render();
$('#runs').innerHTML=(D.runs||[]).slice().reverse().map(r=>`<li>${E((r.head_sha||'').slice(0,8))} (${E(r.baseline_mode)})${r.incremental_from?` from ${E(r.incremental_from.slice(0,8))}`:''}: re-captured ${E((r.recaptured||[]).join(', ')||'none')}${(r.reused||[]).length?`; reused ${E(r.reused.join(', '))}`:''}</li>`).join('');
</script></body></html>"""


def report_md(meta, items, runs):
    counts = {c: sum(i["classification"] == c for i in items) for c in CLASSES}
    L = [f"UI audit for PR {meta.get('pr', '-')} (head `{(meta.get('head_sha') or '')[:8]}`, mode {meta.get('baseline_mode')})", ""]
    if meta.get("summary"):
        L += [meta["summary"], ""]
    L += [f"{len(items)} item(s): {counts['unintended']} unintended, {counts['needs_review']} needs review, {counts['intentional']} intentional."]
    if meta.get("reused_screens"):
        L.append(f"Reused from earlier audit: {', '.join(meta['reused_screens'])}.")
    L.append("")
    for i in items:
        pct = f", {float(i['changed_pct']):.2f}% changed" if i.get("changed_pct") is not None else ""
        L.append(f"- **{i['classification']}** {i['screen']} ({i['platform']}/{i['viewport']}/{i['state']}{pct}): {i.get('reason', '')}")
        L.append(f"  Captured at {str(i['captured_sha'])[:8]}" + (" · reused, files unchanged" if i.get("reused") else ""))
        if i.get("also_at"):
            L.append(f"  Also at: {', '.join(i['also_at'])}")
    if len(runs) > 1:
        L += ["", f"Run history: {len(runs)} audits."]
    return "\n".join(L) + "\n"


def build(spec_path, out, password=None):
    spec = json.load(open(spec_path))
    validate(spec)
    spec_dir = os.path.dirname(os.path.abspath(spec_path))
    meta = spec["meta"]
    hist_p = os.path.join(out, "history.json")
    prev = json.load(open(hist_p)) if os.path.isfile(hist_p) else {}
    key = lambda i: (ORDER[i["classification"]], i["screen"], i["viewport"])
    new = dedupe(sorted(spec["items"], key=key))
    items, runs, stale = merge_history(prev, new, meta)
    add_redirects(items, spec.get("redirects") or [])
    problems = self_check(items, meta)
    if problems:
        fail("report refused:\n" + "\n".join(problems))
    os.makedirs(out, exist_ok=True)
    # Prefix new media dirs with the run number so they never collide with kept items.
    run_no = len(prev.get("runs", [])) + 1
    for n, i in enumerate(new):
        copy_media(i, f"r{run_no}-{n}", spec_dir, out)
    items.sort(key=key)
    json.dump({"meta": meta, "items": items, "runs": runs}, open(hist_p, "w"), indent=1)
    data = json.dumps({"meta": meta, "items": items, "runs": runs}).replace("</", "<\\/")
    title = " - ".join(["UI audit", *([meta["project"]] if meta.get("project") else []), f"PR {meta['pr']}" if meta.get("pr") else "PR -"])
    subs = {"__TITLE__": html.escape(title), "__DATA__": data}  # one pass: a project/summary containing a placeholder must not be re-substituted
    open(os.path.join(out, "index.html"), "w").write(re.sub("__TITLE__|__DATA__", lambda m: subs[m.group()], PAGE))
    open(os.path.join(out, "report.md"), "w").write(report_md(meta, items, runs))
    if password:
        open(os.path.join(out, "_worker.js"), "w").write(WORKER.replace("__HASH__", hashlib.sha256(password.encode()).hexdigest()))
    elif os.path.exists(os.path.join(out, "_worker.js")):
        os.remove(os.path.join(out, "_worker.js"))  # a reused out dir must not keep an old gate (or a stale hash)
    return {"index": os.path.join(out, "index.html"), "report": os.path.join(out, "report.md"), "items": len(items), "runs": len(runs), "stale_media": stale}


WORKER = r"""export default {
  async fetch(req, env) {
    let pw = "";
    try {
      const a = req.headers.get("Authorization") || "";
      if (a.startsWith("Basic ")) pw = atob(a.slice(6)).split(":").slice(1).join(":");
    } catch (e) {}
    const h = [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(pw)))].map(b => b.toString(16).padStart(2, "0")).join("");
    if (h === "__HASH__") return env.ASSETS.fetch(req);
    return new Response("Authentication required", {status: 401, headers: {"WWW-Authenticate": 'Basic realm="ui-audit"'}});
  }
};
"""


def selftest():
    from PIL import Image  # selftest needs Pillow only to make images
    with tempfile.TemporaryDirectory() as t:
        for n in ("b.png", "h.png", "d.png"):
            Image.new("RGB", (40, 30), "white").save(os.path.join(t, n))
        open(os.path.join(t, "c.webm"), "wb").write(b"x")

        def spec(items, redirects=(), **m):
            p = os.path.join(t, "spec.json")
            meta = {"pr": 1, "head_sha": "abcdef123456", "base_sha": "111111aaaaaa", "baseline_mode": "base+head", "dep_hashes": {"about": "dh", "home": "dh"}, **m}
            json.dump({"meta": meta, "items": items, "redirects": list(redirects)}, open(p, "w"))
            return p
        full = lambda s, c: dict(screen=s, platform="web", viewport="desktop", state="default", classification=c, reason="r", base_img="b.png", head_img="h.png", diff_img="d.png", changed_pct=1.5, dep_hash="dh")
        out = os.path.join(t, "out")
        build(spec([full("about", "unintended"), {**full("home", "intentional"), "clips": ["c.webm"], "stills": {"start": "h.png"}}]), out)
        h = open(os.path.join(out, "index.html")).read()
        assert 'id="summary"' in h and 'data-z=' in h
        build(spec([full("about", "unintended")], summary="Sums it up."), os.path.join(t, "outs"))
        assert "Sums it up." in open(os.path.join(t, "outs", "report.md")).read()
        assert "overflow-wrap:anywhere" in h and "Sums it up." not in open(os.path.join(out, "report.md")).read()  # long-summary wrap; no summary -> absent
        assert "<title>UI audit - PR 1</title>" in h
        build(spec([full("about", "unintended")], project="__DATA__", summary="__TITLE__"), os.path.join(t, "outq"))
        assert "<title>UI audit - __DATA__ - PR 1</title>" in open(os.path.join(t, "outq", "index.html")).read()
        build(spec([full("about", "unintended")], project="my<app>"), os.path.join(t, "outp"))
        assert "<title>UI audit - my&lt;app&gt; - PR 1</title>" in open(os.path.join(t, "outp", "index.html")).read()
        assert 'id="data"' in h and "prefers-color-scheme:dark" in h and "<script src" not in h
        d = json.load(open(os.path.join(out, "history.json")))
        assert [i["screen"] for i in d["items"]] == ["about", "home"], "unintended first"
        assert os.path.isfile(os.path.join(out, d["items"][1]["clips"][0]))
        assert "unintended" in open(os.path.join(out, "report.md")).read()
        # incremental: about re-captured as intentional, home reused
        build(spec([full("about", "intentional")], incremental_from="abcdef123456", reused_screens=["home"]), out)
        d = json.load(open(os.path.join(out, "history.json")))
        assert len(d["runs"]) == 2 and {i["screen"] for i in d["items"]} == {"about", "home"}
        assert next(i for i in d["items"] if i["screen"] == "about")["classification"] == "intentional"
        # partial re-capture: only about/desktop/default replaced; about/mobile and home kept as reused
        R = ["about", "home"]
        mob = {**full("about", "needs_review"), "viewport": "mobile"}
        build(spec([mob], reused_screens=R), out)
        build(spec([full("about", "unintended")], reused_screens=R), out)
        d = json.load(open(os.path.join(out, "history.json")))
        got = {(i["screen"], i["viewport"]): i["classification"] for i in d["items"]}
        assert got == {("about", "desktop"): "unintended", ("about", "mobile"): "needs_review", ("home", "desktop"): "intentional"}, got
        assert {i["screen"] for i in d["items"] if i.get("reused")} == {"about", "home"} and not next(i for i in d["items"] if i["viewport"] == "desktop" and i["screen"] == "about").get("reused")
        hx = open(os.path.join(out, "index.html")).read()
        assert "Captured at" in hx and "reused, files unchanged" in hx and "Captured at abcdef12 · reused" in open(os.path.join(out, "report.md")).read()
        # renamed/deleted screen: not in the new run -> old cards gone, media stale
        about_media = [m for i in d["items"] if i["screen"] == "about" for m in media_of(i)]
        r = build(spec([full("home", "intentional")], reused_screens=[]), out)
        d = json.load(open(os.path.join(out, "history.json")))
        assert {i["screen"] for i in d["items"]} == {"home"} and not any(i.get("reused") for i in d["items"])
        assert set(about_media) <= set(r["stale_media"]), r
        # reuse dropped when the dep hash differs
        o3 = os.path.join(t, "o3")
        build(spec([full("about", "unintended"), full("home", "intentional")]), o3)
        r = build(spec([full("about", "unintended")], reused_screens=["home"], dep_hashes={"about": "dh", "home": "changed"}), o3)
        d = json.load(open(os.path.join(o3, "history.json")))
        assert {i["screen"] for i in d["items"]} == {"about"} and r["stale_media"], r
        # commit mismatch: exit 1, nothing written
        o4 = os.path.join(t, "o4")
        try:
            build(spec([{**full("about", "unintended"), "captured_sha": "deadbeef0000"}]), o4)
            raise AssertionError("expected SystemExit")
        except SystemExit as e:
            assert e.code == 1 and not os.path.exists(o4)
        # identical pixels on two screens: one card with also_at; same route, different pixels: two cards
        o5 = os.path.join(t, "o5")
        a = {**full("about", "intentional"), "route": "/about", "head_hash": "H"}
        build(spec([a, {**full("home", "intentional"), "route": "/home", "head_hash": "H"}]), o5)
        d = json.load(open(os.path.join(o5, "history.json")))
        assert [(i["screen"], i.get("also_at")) for i in d["items"]] == [("about", ["/home"])], d["items"]
        o6 = os.path.join(t, "o6")
        build(spec([{**a, "state": "a", "head_hash": "H1"}, {**a, "state": "b", "head_hash": "H2"}]), o6)
        assert json.load(open(os.path.join(o6, "history.json")))["items"].__len__() == 2
        # redirect lands in also_at of the target's cards
        o7 = os.path.join(t, "o7")
        build(spec([a], redirects=[{"screen": "old", "route": "/old", "to": "about"}]), o7)
        d = json.load(open(os.path.join(o7, "history.json")))
        assert d["items"][0]["also_at"] == ["/old (redirects to about)"] and "Also at: /old" in open(os.path.join(o7, "report.md")).read()
        assert 'position:absolute' not in h.split('.slider .top{')[1].split('}')[0] and 'grid-area:1/1' in h
        # stale media: re-capturing home lists the old home files
        old = next(i for i in json.load(open(os.path.join(out, "history.json")))["items"] if i["screen"] == "home")
        stale = build(spec([full("home", "intentional")]), out)["stale_media"]
        assert old["head_img"] in stale and old["base_img"] in stale, stale
        # password gate: hash only, never the plaintext; absent without the flag
        assert not os.path.exists(os.path.join(out, "_worker.js"))
        build(spec([full("home", "intentional")]), out, password="s3cret-pw")
        w = open(os.path.join(out, "_worker.js")).read()
        assert hashlib.sha256(b"s3cret-pw").hexdigest() in w and "s3cret-pw" not in w and "__HASH__" not in w
        build(spec([full("home", "intentional")]), out)
        assert not os.path.exists(os.path.join(out, "_worker.js"))
        # head-only
        out2 = os.path.join(t, "out2")
        build(spec([dict(screen="home", platform="web", viewport="mobile", classification="needs_review", reason="r", head_img="h.png")], baseline_mode="head-only"), out2)
        assert "head-only" in open(os.path.join(out2, "index.html")).read()
    print("selftest ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec")
    ap.add_argument("--out")
    ap.add_argument("--password")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.spec and a.out:
        print(json.dumps(build(a.spec, a.out, a.password)))
    else:
        ap.error("need --spec and --out (or --selftest)")
