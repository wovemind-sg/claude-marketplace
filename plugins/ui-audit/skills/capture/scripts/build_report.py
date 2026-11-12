#!/usr/bin/env python3
"""Build a self-contained UI audit page (index.html) and a short report.md.

Usage: build_report.py --spec audit.json --out DIR [--password PW] [--repo DIR]   |   build_report.py --selftest
--password also writes OUT/_worker.js, a Cloudflare Pages worker that answers 401 unless the request carries
Basic Auth (any username) with that password. Only the SHA-256 of the password is embedded, never the plaintext.

Spec JSON (paths are absolute or relative to the spec file):
{
  "meta": {"pr": 12, "head_sha": "...", "base_sha": "...", "baseline_mode": "base+head" | "head-only",
           "project": "repo name", "incremental_from": "<sha>|null", "reused_screens": ["name", ...],
           "dep_hashes": {"<screen>": "<dep_hash.py new_hashes value>"}, "summary": "short PR description",
           "default_view": "slider|side|diff (default slider)"},
  "items": [{"screen", "platform", "viewport", "state", "classification": "intentional|unintended|needs_review",
             "reason": "one line", "route": "/path", "head_hash": "<diff_images.py hashes value>",
             "captured_sha": "defaults to meta.head_sha", "dep_hash": "<screen's dep hash when captured>",
             "base_img", "head_img", "diff_img", "changed_pct",
             "clips": ["a.webm"], "stills": {"start": "p.png", "mid": "p.png", "end": "p.png"}}],
  "redirects": [{"screen": "old", "route": "/old", "to": "target-screen"}],
  "changes": [{"id": "c1", "text": "what changed in the PR", "items": [{"screen", "viewport", "state"}],
               "not_captured": "why no card (omit when items has cards)"}],
  "config_suggestions": ["merge old-verify into verify", ...]
}
base_img/diff_img/changed_pct are omitted for head-only items. Media is copied into OUT/media/.
If OUT/history.json exists, a new item replaces only the old item with the same (screen, platform,
viewport, state). An old item is kept (marked "reused": true) only if its screen is in meta.reused_screens, its
stored dep_hash equals meta.dep_hashes[screen] and its key is not re-captured; every other old item is dropped
and its media listed in stale_media. The run is appended to the history list.
Item "base_sha" (defaults to meta.base_sha) must equal meta.base_sha for an old item to be reused. Every item gets
"history": [{"run", "head_sha", "changed"}] (one entry per audit; a reused item gets changed false) and "changed_in"
(the run where its head_hash last differed from the same-key card of the previous run, or it was new or had no
head_hash). Each runs entry has "run". Base moved (previous run's base_sha != meta.base_sha) with reused_screens
non-empty: the build refuses, re-capture every screen.
Dedupe: new items with the same (platform, viewport, head_hash, changed_pct) become one card (the first in sort
order); the others' route (or screen) goes in its "also_at", and each redirect adds "<route> (redirects to <to>)"
to the target screen's cards; a redirect whose target has no card is listed with the config suggestions.
redirects and config_suggestions are kept in history.json and merged with the next run's (deduped by (screen, to) /
text); a carried redirect is dropped when its screen is re-captured. A change item also matches a card through its
"merged_screens" (screens deduped into it).
Quote check (new items only): every "straight" or “curly” quoted string in an item's reason must appear in the
screen's manifest deps (<repo>/.ui-audit/manifest.json, --repo default .) at meta.head_sha, or anywhere in the repo at
head (git grep -F) when the screen has no deps or there is no manifest. A missing quote turns an intentional item into
needs_review (unintended stays unintended) and prefixes its reason with 'Needs review: "X" not in current code. '.
Self-check (exit 1, nothing written, all problems on stderr): a card whose captured_sha != meta.head_sha that is
not a valid reuse; a change whose items match no card (screen, plus viewport/state when given) and has no not_captured.
The page and report.md list the changes ("Changes in this PR") and config_suggestions (only when non-empty).
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
import subprocess
import sys
import tempfile

ORDER = {"unintended": 0, "needs_review": 1, "intentional": 2}
CLASSES = list(ORDER)
VIEWS = ("slider", "side", "diff")
QUOTE = re.compile(r'"([^"]+)"|“([^”]+)”')


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
    if spec["meta"].get("default_view") is None:
        spec["meta"]["default_view"] = "slider"
    if spec["meta"]["default_view"] not in VIEWS:
        fail(f"bad default_view '{spec['meta']['default_view']}', use one of {', '.join(VIEWS)}")
    for c in spec.get("changes") or []:
        if not isinstance(c, dict) or not c.get("id") or not c.get("text"):
            fail(f"change needs 'id' and 'text': {c}")
    for i in spec["items"]:
        for k in ("screen", "platform", "viewport", "classification", "head_img"):
            if not i.get(k):
                fail(f"item missing '{k}': {i}")
        if i["classification"] not in ORDER:
            fail(f"bad classification '{i['classification']}'")
        i.setdefault("state", "default")
        i.setdefault("captured_sha", spec["meta"].get("head_sha"))
        i.setdefault("base_sha", spec["meta"].get("base_sha"))


def _key(i):
    return (i["screen"], i["platform"], i["viewport"], i.get("state") or "default")


def media_of(i):
    return [p for p in (i.get("base_img"), i.get("head_img"), i.get("diff_img"), *(i.get("clips") or []), *(i.get("stills") or {}).values()) if p]


def merge_history(prev, new_items, meta):
    """Keep an old item (reused: true) only if its screen is reused, its dep_hash and base_sha still match and its
    key is not re-captured. Every item gets history (one entry per run) and changed_in (the run its pixels last
    changed). Returns (items, runs, stale_media) where stale_media are the media paths of dropped old items."""
    n = len(prev.get("runs", [])) + 1
    old = {(m, *_key(i)[1:]): i for i in prev.get("items", []) for m in i.get("merged_screens", [])}  # deduped-away screens look up their survivor
    old.update({_key(i): i for i in prev.get("items", [])})
    pix = lambda x: x.get("head_hash") or x.get("img_hash")  # img_hash: head image content, for items without head_hash
    for i in new_items:
        o = old.get(_key(i)) or {}
        changed = not o or not pix(i) or pix(o) != pix(i)
        i["history"] = o.get("history", []) + [{"run": n, "head_sha": meta.get("head_sha"), "changed": changed}]
        i["changed_in"] = n if changed else o.get("changed_in", n - 1)
    redone = {i["screen"] for i in new_items}
    keys = {_key(i) for i in new_items}
    reused, hashes = meta.get("reused_screens") or [], meta.get("dep_hashes") or {}
    kept, stale = [], []
    pbase = (prev.get("runs") or [{}])[-1].get("base_sha")  # 4.0 items carry no base_sha: they share the last run's
    for i in prev.get("items", []):
        if i["screen"] in reused and i.get("dep_hash") and i["dep_hash"] == hashes.get(i["screen"]) and i.get("base_sha", pbase) == meta.get("base_sha") and _key(i) not in keys:
            h = i.get("history", [])
            kept.append({**i, "reused": True, "history": h + [{"run": n, "head_sha": meta.get("head_sha"), "changed": False}],
                         "changed_in": i.get("changed_in", h[-1]["run"] if h else n - 1)})
        else:
            stale += media_of(i)
    runs = prev.get("runs", []) + [{k: meta.get(k) for k in ("head_sha", "base_sha", "baseline_mode", "incremental_from")}
                                   | {"run": n, "recaptured": sorted(redone), "reused": reused}]
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
            f["merged_screens"] = f.get("merged_screens", []) + [i["screen"]]
    return out


def add_redirects(items, redirects):
    """Add each redirect to its target's cards; returns the notes for redirects whose target has no card."""
    lost = []
    for r in redirects:
        txt = f"{r['route']} (redirects to {r['to']})"
        hit = [i for i in items if r["to"] in (i["screen"], *i.get("merged_screens", []))]
        for i in hit:
            if txt not in i.get("also_at", []):
                i["also_at"] = i.get("also_at", []) + [txt]
        if not hit:
            lost.append(f"{txt}: no card, the target is unchanged")
    return lost


def carry(prev, spec, redone):
    """Redirects and config suggestions survive incremental runs; a redirect is dropped when its screen is re-captured."""
    new = spec.get("redirects") or []
    seen = {(r["screen"], r["to"]) for r in new}
    reds = [r for r in prev.get("redirects", []) if r["screen"] not in redone and (r["screen"], r["to"]) not in seen] + new
    sugg = list(dict.fromkeys(prev.get("config_suggestions", []) + (spec.get("config_suggestions") or [])))
    return reds, sugg


def quote_check(items, meta, repo):
    """Mark an item needs_review when a quoted string of its reason is not in the code at head."""
    head = meta.get("head_sha")
    mp = os.path.join(repo, ".ui-audit", "manifest.json")
    screens = (json.load(open(mp)) if os.path.isfile(mp) else {}).get("screens", {})
    git = lambda *a: subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, errors="replace")

    def found(q, screen):
        deps = screens.get(screen, {}).get("deps")
        if deps:
            return any(q in git("show", f"{head}:{d}").stdout for d in deps)
        return git("grep", "-qF", "-e", q, head).returncode == 0
    for i in items:
        qs = [a or b for a, b in QUOTE.findall(i.get("reason") or "")]
        missing = [q for q in qs if not found(q, i["screen"])] if head else []
        if missing:
            if i["classification"] == "intentional":  # never lower unintended
                i["classification"] = "needs_review"
            i["reason"] = "".join(f'Needs review: "{q}" not in current code. ' for q in missing) + i["reason"]


def covers(ci, card):
    """A change item matches a card on screen, plus viewport/state when the change item gives them."""
    return ci.get("screen") in (card["screen"], *card.get("merged_screens", [])) and all(ci.get(k) in (None, card[k]) for k in ("viewport", "state"))


def self_check(items, meta, changes=(), prev_runs=()):
    """List of problems; build refuses to write anything when non-empty."""
    p = []
    if meta.get("reused_screens") and prev_runs and prev_runs[-1].get("base_sha") != meta.get("base_sha"):
        p.append(f"base moved from {str(prev_runs[-1].get('base_sha') or 'unknown')[:8]} to {str(meta.get('base_sha'))[:8]}: re-capture every screen (no reuse)")
    p += [f"{i['screen']}/{i['viewport']}/{i['state']} captured at {str(i['captured_sha'])[:8]}, not head {str(meta.get('head_sha'))[:8]}"
         for i in items if not i.get("reused") and i["captured_sha"] != meta.get("head_sha")]
    return p + [f"change {c['id']} ({c['text']}) has no card and no not_captured reason"
                for c in changes if not c.get("not_captured") and not any(covers(ci, i) for ci in c.get("items") or [] for i in items)]


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
.item.reviewed .modes,.item.reviewed .view,.item.reviewed h3,.item.reviewed .stills,.item.reviewed video,.item.reviewed .reason{display:none}
.empty{color:var(--muted)}#summary{overflow-wrap:anywhere;max-height:30vh;overflow-y:auto;white-space:pre-line}ul{padding-left:1.2em}
</style></head><body>
<h1>UI audit</h1><div class="meta" id="meta"></div><p id="summary" hidden></p>
<div id="changes" hidden><h2>Changes in this PR</h2><ul id="chl"></ul></div>
<div class="bar"><select id="fp" aria-label="Platform"></select><select id="fv" aria-label="Viewport"></select><select id="fc" aria-label="Classification"></select><select id="fm" aria-label="Default view"></select></div>
<div id="items"></div>
<div id="sugg" hidden><h2>Config suggestions</h2><ul id="sgl"></ul></div>
<h2>Run history</h2><ul id="runs"></ul>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent),$=s=>document.querySelector(s);
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const m=D.meta,headOnly=m.baseline_mode==='head-only';
$('#meta').textContent=`PR ${m.pr??'-'} · head ${(m.head_sha||'').slice(0,8)} · base ${(m.base_sha||'-').slice(0,8)} (PR base branch) · mode ${m.baseline_mode}`+(m.incremental_from?` · previous audit ${m.incremental_from.slice(0,8)}`:'')+(m.reused_screens&&m.reused_screens.length?` · reused: ${m.reused_screens.join(', ')}`:'');
if(m.summary){$('#summary').textContent=m.summary;$('#summary').hidden=false}
function fill(id,label,key){const v=[...new Set(D.items.map(i=>i[key]))];$(id).innerHTML=`<option value="">${label}: all</option>`+v.map(x=>`<option>${E(x)}</option>`).join('')}
fill('#fp','Platform','platform');fill('#fv','Viewport','viewport');fill('#fc','Classification','classification');
['#fp','#fv','#fc'].forEach(s=>$(s).onchange=render);
const VN={slider:'Slider',side:'Side by side',diff:'Diff overlay'};
$('#fm').innerHTML=Object.entries(VN).map(([k,l])=>`<option value="${k}">Default view: ${l}</option>`).join('');
let stored=null;try{stored=localStorage.getItem('ui-audit-view')}catch(e){}
$('#fm').value=VN[stored]?stored:m.default_view;
$('#fm').onchange=()=>{try{localStorage.setItem('ui-audit-view',$('#fm').value)}catch(e){}render()};
if((D.changes||[]).length){$('#changes').hidden=false;$('#chl').innerHTML=D.changes.map(c=>`<li>${E(c.text)}: ${c.not_captured?`Not captured: ${E(c.not_captured)}`:(c.items||[]).map(x=>E([x.screen,x.viewport,x.state].filter(Boolean).join(' / '))).join('; ')}</li>`).join('')}
if((D.config_suggestions||[]).length){$('#sugg').hidden=false;$('#sgl').innerHTML=D.config_suggestions.map(x=>`<li>${E(x)}</li>`).join('')}
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
 list.forEach(i=>{const d=document.createElement('section');d.className='item';let mode=$('#fm').value;
  const pct=i.changed_pct!=null?` · ${(+i.changed_pct).toFixed(2)}% changed`:'';
  d.innerHTML=`<h2>${E(i.screen)} <span class="tag ${E(i.classification)}">${E(i.classification.replace('_',' '))}</span>${i.changed_in===D.runs.length?'<span class="tag">Changed in this audit</span>':''}</h2><div class="meta">${E(i.platform)} · ${E(i.viewport)} · ${E(i.state)}${pct}</div><div class="meta">Captured at ${E((i.captured_sha||'').slice(0,8))}${i.reused?' · reused, files unchanged':''}</div>${(i.also_at||[]).length?`<div class="meta">Also at: ${i.also_at.map(E).join(', ')}</div>`:''}<div class="meta">Audit history: ${(i.history||[]).map((h,k)=>`#${E(h.run)} ${E((h.head_sha||'').slice(0,8))} ${k?(h.changed?'changed':'unchanged'):'new'}`).join(' · ')}</div><p class="reason">${E(i.reason)}</p><button class="rv"></button> <span class="meta rvn"></span>`+
  `<div class="modes">${headOnly||!i.base_img?'':[['slider','Slider'],['side','Side by side'],['diff','Diff overlay']].map(([k,l])=>`<button data-m="${k}" aria-pressed="${k===mode}">${l}</button>`).join('')}<div class="zoom"><button data-z="-1" aria-label="Decrease image height">−</button><button data-z="0">Fit to screen</button><button data-z="1" aria-label="Increase image height">+</button></div></div><div class="view"></div>`+motion(i);
  const rk=`ui-audit-reviewed:${m.project||''}:${m.pr}:${i.screen}|${i.platform}|${i.viewport}|${i.state}`,rb=d.querySelector('.rv'),cv=String(i.changed_in);
  const isRv=()=>{try{return localStorage.getItem(rk)===cv}catch(e){return false}};
  const showRv=()=>{const r=isRv();d.classList.toggle('reviewed',r);rb.textContent=r?'Reviewed \u2014 unmark':'Mark reviewed'};
  rb.onclick=()=>{try{isRv()?localStorage.removeItem(rk):localStorage.setItem(rk,cv);d.querySelector('.rvn').textContent=''}catch(e){d.querySelector('.rvn').textContent="Can't save: browser storage blocked"}showRv()};showRv();
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


def report_md(meta, items, runs, changes=(), suggestions=()):
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
        k = i.get("changed_in")
        if k:
            L.append(f"  {'changed in' if k == len(runs) else 'unchanged since'} audit #{k}")
        if i.get("also_at"):
            L.append(f"  Also at: {', '.join(i['also_at'])}")
    if changes:
        L += ["", "## Changes in this PR"]
        for c in changes:
            where = f"Not captured: {c['not_captured']}" if c.get("not_captured") else "; ".join("/".join(x for x in (ci.get("screen"), ci.get("viewport"), ci.get("state")) if x) for ci in c.get("items") or [])
            L.append(f"- {c['text']}: {where}")
    if suggestions:
        L += ["", "## Config suggestions"] + [f"- {x}" for x in suggestions]
    if len(runs) > 1:
        L += ["", f"Run history: {len(runs)} audits."]
    return "\n".join(L) + "\n"


def build(spec_path, out, password=None, repo="."):
    spec = json.load(open(spec_path))
    validate(spec)
    spec_dir = os.path.dirname(os.path.abspath(spec_path))
    meta = spec["meta"]
    hist_p = os.path.join(out, "history.json")
    prev = json.load(open(hist_p)) if os.path.isfile(hist_p) else {}
    key = lambda i: (ORDER[i["classification"]], i["screen"], i["viewport"])
    all_new = sorted(spec["items"], key=key)
    quote_check(all_new, meta, repo)
    for i in all_new:
        src = i["head_img"] if os.path.isabs(i["head_img"]) else os.path.join(spec_dir, i["head_img"])
        if not i.get("head_hash") and os.path.isfile(src):
            i["img_hash"] = hashlib.sha256(open(src, "rb").read()).hexdigest()
    merged, runs, stale = merge_history(prev, all_new, meta)
    changes = spec.get("changes") or []
    problems = self_check(merged, meta, changes, prev.get("runs", []))  # before dedupe, so a change pointing at a merged-away card still counts as covered
    if problems:
        fail("report refused:\n" + "\n".join(problems))
    new = dedupe(all_new)
    items = [i for i in merged if i.get("reused")] + new
    reds, sugg = carry(prev, spec, {i["screen"] for i in all_new})
    lost = add_redirects(items, reds)
    os.makedirs(out, exist_ok=True)
    # Prefix new media dirs with the run number so they never collide with kept items.
    run_no = len(prev.get("runs", [])) + 1
    for n, i in enumerate(new):
        copy_media(i, f"r{run_no}-{n}", spec_dir, out)
    items.sort(key=key)
    json.dump({"meta": meta, "items": items, "runs": runs, "redirects": reds, "config_suggestions": sugg}, open(hist_p, "w"), indent=1)
    sugg = sugg + lost  # shown with the suggestions so an unmatched redirect is never silent
    data = json.dumps({"meta": meta, "items": items, "runs": runs, "changes": changes, "config_suggestions": sugg}).replace("</", "<\\/")
    title = " - ".join(["UI audit", *([meta["project"]] if meta.get("project") else []), f"PR {meta['pr']}" if meta.get("pr") else "PR -"])
    subs = {"__TITLE__": html.escape(title), "__DATA__": data}  # one pass: a project/summary containing a placeholder must not be re-substituted
    open(os.path.join(out, "index.html"), "w").write(re.sub("__TITLE__|__DATA__", lambda m: subs[m.group()], PAGE))
    open(os.path.join(out, "report.md"), "w").write(report_md(meta, items, runs, changes, sugg))
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

        def spec(items, redirects=(), config_suggestions=(), **m):
            p = os.path.join(t, "spec.json")
            meta = {"pr": 1, "head_sha": "abcdef123456", "base_sha": "111111aaaaaa", "baseline_mode": "base+head", "dep_hashes": {"about": "dh", "home": "dh"}, **m}
            json.dump({"meta": meta, "items": items, "redirects": list(redirects), "config_suggestions": list(config_suggestions)}, open(p, "w"))
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
        # redirect to a screen that was deduped away lands on the card it merged into
        o7b = os.path.join(t, "o7b")
        build(spec([a, {**full("home", "intentional"), "route": "/home", "head_hash": "H"}], redirects=[{"screen": "old", "route": "/old", "to": "home"}]), o7b)
        assert json.load(open(os.path.join(o7b, "history.json")))["items"][0]["also_at"] == ["/home", "/old (redirects to home)"]
        # unmatched redirect shows in report.md; carried in history; dropped when its screen is re-captured
        o7c = os.path.join(t, "o7c")
        build(spec([a], redirects=[{"screen": "old", "route": "/old", "to": "gone"}], config_suggestions=["s1"]), o7c)
        assert "/old (redirects to gone): no card" in open(os.path.join(o7c, "report.md")).read()
        build(spec([a], config_suggestions=["s2", "s1"], reused_screens=[]), o7c)
        d = json.load(open(os.path.join(o7c, "history.json")))
        assert d["redirects"] == [{"screen": "old", "route": "/old", "to": "gone"}] and d["config_suggestions"] == ["s1", "s2"], d
        build(spec([{**a, "screen": "old"}]), o7c)
        assert json.load(open(os.path.join(o7c, "history.json")))["redirects"] == []
        # a merged-away screen is covered by the surviving card's merged_screens after being reused
        o7d = os.path.join(t, "o7d")
        build(spec([a, {**full("home", "intentional"), "route": "/home", "head_hash": "H"}]), o7d)
        p = spec([], reused_screens=["about", "home"], dep_hashes={"about": "dh", "home": "dh"})
        sp = json.load(open(p)); sp["changes"] = [{"id": "c", "text": "home copy", "items": [{"screen": "home"}]}]; json.dump(sp, open(p, "w"))
        build(p, o7d)
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
        # quote check against a temp git repo with a manifest
        rp = os.path.join(t, "repo")
        os.makedirs(os.path.join(rp, ".ui-audit"))
        open(os.path.join(rp, "about.html"), "w").write("<p>No account found.</p>")
        open(os.path.join(rp, "other.html"), "w").write("<p>Only elsewhere</p>")
        json.dump({"screens": {"about": {"deps": ["about.html"]}}}, open(os.path.join(rp, ".ui-audit", "manifest.json"), "w"))
        g = lambda *a: subprocess.run(["git", "-C", rp, "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True, text=True).stdout.strip()
        g("init", "-q"); g("add", "."); g("commit", "-qm", "x")
        sha = g("rev-parse", "HEAD")

        def qb2(s, c, reason):
            build(spec([{**full(s, c), "reason": reason}], head_sha=sha), os.path.join(t, "oq1"), repo=rp)
            return json.load(open(os.path.join(t, "oq1", "history.json")))["items"][0]

        def qb(s, reason):
            build(spec([{**full(s, "intentional"), "reason": reason}], head_sha=sha), os.path.join(t, "oq1"), repo=rp)
            return json.load(open(os.path.join(t, "oq1", "history.json")))["items"][0]
        assert qb("about", 'Shows "No account found." now')["classification"] == "intentional"
        assert qb("about", 'Shows \u201cNo account found.\u201d now')["classification"] == "intentional"
        i = qb("about", 'Shows "Only elsewhere" now')  # present in repo, but not in about's deps
        assert i["classification"] == "needs_review" and i["reason"].startswith('Needs review: "Only elsewhere" not in current code. Shows')
        assert qb("login", 'Shows "Only elsewhere" now')["classification"] == "intentional"  # no deps: whole repo
        assert qb("login", 'Shows "Nowhere text"')["classification"] == "needs_review"
        assert qb2("about", "unintended", 'Shows "Nowhere text"')["classification"] == "unintended"
        # change coverage
        def chg(changes, **kw):
            p = spec([full("about", "intentional")])
            sp = json.load(open(p)); sp["changes"] = changes; sp.update(kw); json.dump(sp, open(p, "w"))
            return p
        o8 = os.path.join(t, "o8")
        try:
            build(chg([{"id": "c1", "text": "new empty state", "items": [{"screen": "about", "viewport": "mobile", "state": "empty"}]}]), o8)
            raise AssertionError("expected SystemExit")
        except SystemExit as e:
            assert e.code == 1 and not os.path.exists(o8)
        sg = ["merge old into about"]
        build(chg([{"id": "c1", "text": "about copy", "items": [{"screen": "about", "viewport": "desktop", "state": "default"}]},
                   {"id": "c2", "text": "email text", "items": [], "not_captured": "needs real SMTP"}], config_suggestions=sg), o8)
        rm = open(os.path.join(o8, "report.md")).read()
        assert "## Changes in this PR" in rm and "Not captured: needs real SMTP" in rm and "## Config suggestions" in rm and sg[0] in rm
        hp = open(os.path.join(o8, "index.html")).read()
        assert 'id="fm"' in hp and '"default_view": "slider"' in hp and "ui-audit-view" in hp
        assert "## Config suggestions" not in open(os.path.join(out, "report.md")).read()
        # default view: valid value kept, invalid fails
        build(spec([full("about", "intentional")], default_view="diff"), os.path.join(t, "o9"))
        assert '"default_view": "diff"' in open(os.path.join(t, "o9", "index.html")).read()
        try:
            build(spec([full("about", "intentional")], default_view="grid"), os.path.join(t, "o10"))
            raise AssertionError("expected SystemExit")
        except SystemExit as e:
            assert e.code == 1
        # card history: same key over 3 builds with head_hash H1, H1, H2
        oh = os.path.join(t, "oh")
        for hh in ("H1", "H1", "H2"):
            build(spec([{**full("about", "intentional"), "head_hash": hh}]), oh)
        it = json.load(open(os.path.join(oh, "history.json")))["items"][0]
        assert [x["changed"] for x in it["history"]] == [True, False, True] and it["changed_in"] == 3, it
        assert "changed in audit #3" in open(os.path.join(oh, "report.md")).read()
        # reused item: unchanged entry appended, changed_in kept
        orr = os.path.join(t, "orr")
        build(spec([full("about", "intentional"), {**full("home", "intentional"), "head_hash": "H"}]), orr)
        build(spec([full("about", "intentional")], reused_screens=["home"]), orr)
        hm = next(x for x in json.load(open(os.path.join(orr, "history.json")))["items"] if x["screen"] == "home")
        assert hm["reused"] and hm["changed_in"] == 1 and hm["history"][-1] == {"run": 2, "head_sha": "abcdef123456", "changed": False}, hm
        # base moved + reuse: refused, nothing written
        before = open(os.path.join(orr, "history.json")).read()
        try:
            build(spec([full("about", "intentional")], reused_screens=["home"], base_sha="222222bbbbbb"), orr)
            raise AssertionError("expected SystemExit")
        except SystemExit as e:
            assert e.code == 1 and open(os.path.join(orr, "history.json")).read() == before
        # 4.0-format history (no base_sha/history/changed_in): reuse still works, unchanged card is not "changed now"
        o40 = os.path.join(t, "o40")
        build(spec([{**full("about", "intentional"), "head_hash": "A"}, {**full("home", "intentional"), "head_hash": "H"}]), o40)
        d40 = json.load(open(os.path.join(o40, "history.json")))
        for x in d40["items"]:
            for k in ("base_sha", "history", "changed_in"):
                x.pop(k, None)
        json.dump(d40, open(os.path.join(o40, "history.json"), "w"))
        build(spec([{**full("about", "intentional"), "head_hash": "A"}], reused_screens=["home"]), o40)
        d40 = {x["screen"]: x for x in json.load(open(os.path.join(o40, "history.json")))["items"]}
        assert d40["home"]["reused"] and d40["about"]["changed_in"] == 1, d40
        # no head_hash: unchanged head image keeps changed_in; a changed image bumps it
        onh = os.path.join(t, "onh")
        build(spec([full("about", "intentional")]), onh)
        build(spec([full("about", "intentional")]), onh)
        it = json.load(open(os.path.join(onh, "history.json")))["items"][0]
        assert [x["changed"] for x in it["history"]] == [True, False] and it["changed_in"] == 1, it
        Image.new("RGB", (40, 30), "black").save(os.path.join(t, "h.png"))
        build(spec([full("about", "intentional")]), onh)
        assert json.load(open(os.path.join(onh, "history.json")))["items"][0]["changed_in"] == 3
        Image.new("RGB", (40, 30), "white").save(os.path.join(t, "h.png"))
        # a card deduped into another keeps its history: next run is unchanged, not new
        om = os.path.join(t, "om")
        hm2 = {**full("home", "intentional"), "route": "/home", "head_hash": "H"}
        build(spec([a, hm2]), om)
        build(spec([a, hm2]), om)
        it = json.load(open(os.path.join(om, "history.json")))["items"][0]
        assert it["merged_screens"] == ["home"] and it["changed_in"] == 1, it
        # missing previous base_sha prints "unknown", not "None"
        assert "unknown" in self_check([], {"reused_screens": ["x"], "base_sha": "b"}, (), [{}])[0]
        hx = open(os.path.join(orr, "index.html")).read()
        assert "ui-audit-reviewed" in hx and "Audit history" in hx
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
    ap.add_argument("--repo", default=".")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.spec and a.out:
        print(json.dumps(build(a.spec, a.out, a.password, a.repo)))
    else:
        ap.error("need --spec and --out (or --selftest)")
