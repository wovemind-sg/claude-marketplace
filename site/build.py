#!/usr/bin/env python3
"""Build the wovemind marketplace site into _site/.

Usage:
    python3 site/build.py [--out DIR]
    python3 site/build.py --selftest

Reads .claude-plugin/marketplace.json, each plugin's .claude-plugin/plugin.json,
the frontmatter of skills/*/SKILL.md and commands/*.md, and the how-to specs in
site/specs/<plugin>/<item>.json. Each spec is rendered with help-me-understand's
build_page.py and wrapped in the site shell. Writes:

    index.html                      catalog home
    plugins/<plugin>/index.html     plugin page
    plugins/<plugin>/<item>/index.html   how-to page for one skill, command or mod

Every link is relative, so the site works under any sub-path. The build fails
(exit 1) when a skill or command has no spec, a spec belongs to no plugin, a
spec does not render, an internal link does not resolve, a name is not
path-safe, or a manifest URL is not http(s). A plugin hosted outside this repo
gets a card and plugin page only. It still writes
everything it could, then lists every problem at once.

Standard library only; runs on Python 3.8+.
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from html import escape, unescape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD_PAGE = os.path.join("plugins", "help-me-understand", "skills", "help-me-understand", "scripts", "build_page.py")
REPO_URL = "https://github.com/wovemind-sg/claude-marketplace"
MARKETPLACE_REPO = "wovemind-sg/claude-marketplace"
FEATURED = ("plan-tools", "ui-audit", "compliance-audit")
KIND_ORDER = {"skill": 0, "command": 1, "mod": 2}
KIND_LABEL = {"skill": "Skill", "command": "Command", "mod": "Mod command"}
KIND_GROUP = {"skill": "Skills", "command": "Commands", "mod": "Mod commands"}
CATEGORY_LABEL = {"ui-quality": "UI quality"}

# Category glyphs: 24-unit stroke icons, drawn in the category colour on its tinted tile.
GLYPHS = {
    "scaffolding": '<path d="M12 3 3 7.5l9 4.5 9-4.5z"/><path d="m3 12 9 4.5 9-4.5"/><path d="m3 16.5 9 4.5 9-4.5"/>',
    "workflow": '<circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="12" r="2.5"/><circle cx="6" cy="18" r="2.5"/>'
                '<path d="M8.5 6h3a4 4 0 0 1 4 4v0M8.5 18h3a4 4 0 0 0 4-4v0"/>',
    "notifications": '<path d="M6 16v-5a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
    "ui-quality": '<rect x="3" y="4" width="18" height="15" rx="2.5"/><path d="M3 8.5h18"/>'
                  '<circle cx="11" cy="13.5" r="2.6"/><path d="m13 15.5 2.5 2.5"/>',
    "libraries": '<path d="M5 4.5A1.5 1.5 0 0 1 6.5 3H19v15H6.5A1.5 1.5 0 0 0 5 19.5z"/><path d="M5 19.5A1.5 1.5 0 0 0 6.5 21H19"/>'
                 '<path d="M9 7.5h6M9 11h4"/>',
    "media": '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="m10 9 5 3-5 3z"/>',
    "compliance": '<path d="M12 3 4.5 6v5.5c0 4.6 3.2 8.4 7.5 9.5 4.3-1.1 7.5-4.9 7.5-9.5V6z"/><path d="m9 12 2.2 2.2L15.5 10"/>',
}
DEFAULT_GLYPH = '<rect x="4" y="4" width="16" height="16" rx="4"/><path d="M9 12h6M12 9v6"/>'
BRAND_SVG = ('<svg class="w-brand-mark" viewBox="0 0 28 28" aria-hidden="true"><rect x="1" y="1" width="26" height="26" rx="8"/>'
             '<path d="M7 9.5c2.5 0 3.5 9 7 9s4.5-9 7-9"/><path d="M7 18.5c2.5 0 3.5-9 7-9s4.5 9 7 9" opacity=".55"/></svg>')
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 28 28'%3E%3Crect width='28' height='28' rx='8' "
           "fill='%2317684f'/%3E%3Cpath d='M7 9.5c2.5 0 3.5 9 7 9s4.5-9 7-9' fill='none' stroke='white' stroke-width='2.4' "
           "stroke-linecap='round'/%3E%3C/svg%3E")


# ---------------------------------------------------------------- reading the repo

def unquote(value):
    """Strip one pair of matching outer YAML quotes, keeping the raw text otherwise (so `[a] [b]` stays a string)."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        inner = value[1:-1]
        return inner.replace('\\"', '"') if value[0] == '"' else inner.replace("''", "'")
    return value


def parse_frontmatter(text):
    """Top-level `key: value` pairs of a Markdown file's `---` frontmatter.

    Handles quoted values, unquoted values that YAML would read as lists, folded
    (`>`) and literal (`|`) blocks, and plain values continued on indented lines.
    shortcut: not a YAML parser; nested mappings and lists come back as raw text, upgrade if a field ever needs them.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out, key, style, buf = {}, None, None, []

    def finish():
        if key is not None:
            out[key] = ("\n".join(buf) if style == "|" else " ".join(x for x in buf if x)).strip()

    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z0-9_-]+):(?:\s+(.*))?$", line)
        if m and not line[:1].isspace():
            finish()
            key, value = m.group(1), (m.group(2) or "").strip()
            if value[:1] in (">", "|") and re.match(r"^[>|][+-]?$", value):
                style, buf = value[0], []
            else:
                style, buf = None, [unquote(value)]
        elif key is not None and (line[:1].isspace() or not line.strip()):
            buf.append(line.strip())
    finish()
    return out


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def discover(root, errors):
    """Plugins from the marketplace manifest, each with its skills and commands from the filesystem."""
    market = read_json(os.path.join(root, ".claude-plugin", "marketplace.json"))
    plugins = []
    for entry in market.get("plugins", []):
        name, source = entry.get("name", "?"), entry.get("source")
        if not valid_name(name):
            errors.append("marketplace.json: plugin name %r must match %s" % (name, NAME_RE.pattern))
            continue
        if not isinstance(source, str) or not source.startswith("./"):
            # Hosted outside this repo (github, git URL, npm...): a card and plugin page from the entry, no how-to pages.
            check_urls(name, "marketplace.json", entry, errors)
            plugins.append({"name": name, "dir": None, "entry": entry, "manifest": {}, "items": [], "external": True})
            continue
        pdir = os.path.normpath(os.path.join(root, source))
        try:
            manifest = read_json(os.path.join(pdir, ".claude-plugin", "plugin.json"))
        except (OSError, ValueError) as exc:
            errors.append("%s: cannot read plugin.json: %s" % (source, exc))
            continue
        check_urls(name, "marketplace.json", entry, errors)
        check_urls(name, "plugin.json", manifest, errors)
        items = []
        skills = os.path.join(pdir, "skills")
        for sub in sorted(os.listdir(skills)) if os.path.isdir(skills) else []:
            md = os.path.join(skills, sub, "SKILL.md")
            if os.path.isfile(md) and named_ok("%s/skills/%s" % (source, sub), sub, errors):
                items.append(make_item("skill", sub, parse_frontmatter(read_text(md))))
        commands = os.path.join(pdir, "commands")
        for fn in sorted(os.listdir(commands)) if os.path.isdir(commands) else []:
            if fn.endswith(".md") and named_ok("%s/commands/%s" % (source, fn), fn[:-3], errors):
                items.append(make_item("command", fn[:-3], parse_frontmatter(read_text(os.path.join(commands, fn)))))
        plugins.append({"name": name, "dir": pdir, "entry": entry, "manifest": manifest, "items": items})
    return market, plugins


# Names become output path segments; every plugin, skill, command and spec name in the repo fits this.
NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")


def valid_name(name):
    return isinstance(name, str) and NAME_RE.fullmatch(name) is not None


def named_ok(where, name, errors):
    if valid_name(name):
        return True
    errors.append("%s: name %r must match %s" % (where, name, NAME_RE.pattern))
    return False


def check_urls(name, where, data, errors):
    """Manifest URLs rendered as links must be http(s); a bad one is reported and dropped so it never reaches a page."""
    for field in ("homepage", "repository"):
        url = data.get(field)
        if url is not None and not (isinstance(url, str) and re.match(r"^https?://", url)):
            errors.append("%s: plugin %s field %s must be an http:// or https:// URL, got %r" % (where, name, field, url))
            data.pop(field)


def make_item(kind, name, fm):
    return {"kind": kind, "name": name, "hint": fm.get("argument-hint", ""), "description": fm.get("description", "")}


def attach_specs(root, plugins, errors):
    """Pair each spec file with its item; a spec that is neither a skill nor a command is a mod command."""
    spec_root = os.path.join(root, "site", "specs")
    by_name = {p["name"]: p for p in plugins}
    for d in sorted(os.listdir(spec_root)) if os.path.isdir(spec_root) else []:
        ddir = os.path.join(spec_root, d)
        if d.startswith("."):
            continue
        if not os.path.isdir(ddir):
            errors.append("site/specs/%s: specs go in site/specs/<plugin>/<item>.json" % d)
            continue
        plugin = by_name.get(d)
        if plugin is None:
            errors.append("site/specs/%s/: no plugin named %s in marketplace.json" % (d, d))
            continue
        if plugin.get("external"):
            errors.append("site/specs/%s/: %s is hosted outside this repo, so it has no how-to pages" % (d, d))
            continue
        for fn in sorted(os.listdir(ddir)):
            if not fn.endswith(".json"):
                continue
            stem, rel = fn[:-5], "site/specs/%s/%s" % (d, fn)
            if not named_ok(rel, stem, errors):
                continue
            item = next((i for i in plugin["items"] if i["name"] == stem), None)
            if item is None:
                readme = os.path.join(plugin["dir"], "README.md")
                if not re.search(r"`/%s(?![\w-])" % re.escape(stem), read_text(readme) if os.path.isfile(readme) else ""):
                    errors.append("%s: %s has no skill or command %s, and its README never mentions `/%s`" % (rel, d, stem, stem))
                    continue
                item = {"kind": "mod", "name": stem, "hint": "", "description": ""}
                plugin["items"].append(item)
            item["spec_path"] = os.path.join(ddir, fn)
            try:
                item["spec"] = read_json(item["spec_path"])
            except (OSError, ValueError) as exc:
                errors.append("%s: invalid JSON: %s" % (rel, exc))
    for p in plugins:
        p["items"].sort(key=lambda i: (KIND_ORDER[i["kind"]], i["name"]))
        for i in p["items"]:
            if "spec_path" not in i:
                errors.append("missing spec: site/specs/%s/%s.json (%s %s)" % (p["name"], i["name"], i["kind"], invocation(p, i)))


# ---------------------------------------------------------------- small helpers

def _load_build_page():
    spec = importlib.util.spec_from_file_location("build_page", os.path.join(ROOT, BUILD_PAGE))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def inline(text):
    """Escape spec text and apply its two inline marks, `code` and **bold**, exactly as the how-to page does."""
    return _build_page.inline(text or "")


_build_page = _load_build_page()


def plain(text):
    return re.sub(r"[`*]", "", text or "")


def invocation(plugin, item):
    return "/" + item["name"] if item["kind"] == "mod" else "/%s:%s" % (plugin["name"], item["name"])


def category_label(cat):
    return CATEGORY_LABEL.get(cat, cat.replace("-", " ").capitalize())


def glyph(cat, cls="w-glyph"):
    return ('<span class="%s w-cat-%s" aria-hidden="true"><svg viewBox="0 0 24 24">%s</svg></span>'
            % (cls, escape(cat), GLYPHS.get(cat, DEFAULT_GLYPH)))


def counts_label(items):
    n = {}
    for i in items:
        n[i["kind"]] = n.get(i["kind"], 0) + 1
    parts = []
    for kind, one, many in (("skill", "skill", "skills"), ("command", "command", "commands"), ("mod", "mod command", "mod commands")):
        if n.get(kind):
            parts.append("%d %s" % (n[kind], one if n[kind] == 1 else many))
    return ", ".join(parts) or "no skills"


def version(plugin):
    """plugin.json wins over the marketplace entry, as in Claude Code; either may hold it."""
    return plugin["manifest"].get("version") or plugin["entry"].get("version") or "?"


def rendered(plugin):
    return [i for i in plugin["items"] if i.get("page")]


def copy_button(cmd):
    return ('<button type="button" class="w-copy" data-copy="%s" aria-label="Copy %s">'
            '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="12" height="12" rx="2.5"/>'
            '<path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></svg><span>Copy</span></button>'
            % (escape(cmd), escape(cmd)))


def cmd_line(cmd, shown=None):
    return '<div class="w-cmd"><code>%s</code>%s</div>' % (shown or escape(cmd), copy_button(cmd))


_tab_ids = [0]


def install_block(plugin_name, compact=False):
    """Two numbered steps, in a Terminal tab and an Inside Claude Code tab. Without JavaScript both panels show."""
    _tab_ids[0] += 1
    uid = "w-tabs-%d" % _tab_ids[0]
    target = plugin_name or "<plugin>"
    panels = (
        ("term", "Terminal", "In your terminal", "claude plugin marketplace add %s" % MARKETPLACE_REPO,
         "claude plugin install %s@wovemind" % target),
        ("cc", "Inside Claude Code", "Inside a Claude Code session", "/plugin marketplace add %s" % MARKETPLACE_REPO,
         "/plugin install %s@wovemind" % target),
    )
    tabs, bodies = [], []
    for n, (key, tab, where, add, inst) in enumerate(panels):
        sel = n == 0
        tabs.append('<button type="button" role="tab" id="%s-%s-tab" aria-controls="%s-%s" aria-selected="%s" tabindex="%d">%s</button>'
                    % (uid, key, uid, key, "true" if sel else "false", 0 if sel else -1, tab))
        bodies.append(
            '<div class="w-panel" role="tabpanel" id="%s-%s" aria-labelledby="%s-%s-tab">'
            '<p class="w-where">%s</p><ol class="w-steplist">'
            '<li><span class="w-stepn" aria-hidden="true">1</span><div><p>Add the wovemind marketplace (once)</p>%s</div></li>'
            '<li><span class="w-stepn" aria-hidden="true">2</span><div><p>Install the plugin</p>%s</div></li></ol></div>'
            % (uid, key, uid, key, where, cmd_line(add), cmd_line(inst)))
    return ('<div class="w-install%s" data-tabs><div class="w-tablist" role="tablist" aria-label="Where you type it">%s</div>%s</div>'
            % (" w-install-compact" if compact else "", "".join(tabs), "".join(bodies)))


def page(rel, title, description, body, body_class="w-site"):
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<title>%s</title>
<meta name="description" content="%s">
<link rel="icon" href="%s">
<link rel="stylesheet" href="%sassets/site.css">
<script>document.documentElement.classList.add("w-js")</script>
</head>
<body class="w %s">
<a class="w-skip" href="#content">Skip to content</a>
%s
%s
%s
<div class="w-live w-sr" aria-live="polite" id="w-live"></div>
<script src="%sassets/site.js" defer></script>
</body>
</html>
""" % (escape(title), escape(description), FAVICON, rel, body_class, header(rel), body, footer(rel), rel)


def header(rel):
    home = rel or "./"
    return ('<header class="w-head"><div class="w-wrap w-head-in">'
            '<a class="w-brand" href="%s">%s<span>wovemind</span><span class="w-brand-sub">plugins</span></a>'
            '<nav class="w-nav" aria-label="Site"><a href="%s#plugins">Plugins</a><a href="%s#how">How it works</a>'
            '<a href="%s">GitHub</a></nav></div></header>' % (home, BRAND_SVG, home, home, REPO_URL))


def footer(rel):
    return ('<footer class="w-foot"><div class="w-wrap w-foot-in"><p>%s Open-source Claude Code plugins by Wovemind.</p>'
            '<nav aria-label="Footer"><a href="%s">Source on GitHub</a><a href="%s/blob/main/CONTRIBUTING.md">Contributing</a>'
            '<a href="%s/blob/main/LICENSE">MIT licence</a></nav></div></footer>'
            % (BRAND_SVG, REPO_URL, REPO_URL, REPO_URL))


def crumbs(rel, trail):
    parts = ['<li><a href="%s">Plugins</a></li>' % (rel or "./")]
    for label, href in trail:
        parts.append('<li><a href="%s">%s</a></li>' % (href, escape(label)) if href
                     else '<li><span aria-current="page">%s</span></li>' % escape(label))
    return '<nav class="w-crumbs" aria-label="Breadcrumb"><ol>%s</ol></nav>' % "".join(parts)


# ---------------------------------------------------------------- pages

def plugin_card(p, rel, featured=False):
    entry, items = p["entry"], p["items"]
    cat = entry.get("category", "other")
    words = " ".join([p["name"], entry.get("description", ""), cat, category_label(cat)] + entry.get("tags", [])
                     + [i["name"] for i in items] + [plain(i.get("spec", {}).get("title", "")) for i in items])
    extra = ""
    if featured:
        extra = '<ul class="w-feat-items">%s</ul>' % "".join(
            "<li><code>%s</code></li>" % escape(invocation(p, i)) for i in items[:3])
    return ('<li class="w-card%s w-reveal" data-cat="%s" data-search="%s"><a href="%splugins/%s/">'
            '<div class="w-card-top">%s<span class="w-badge w-cat-%s">%s</span></div>'
            '<h3 class="w-card-name">%s</h3><p class="w-card-desc">%s</p>%s'
            '<p class="w-card-meta"><span>%s</span><span>v%s</span></p></a></li>'
            % (" w-card-feat" if featured else "", escape(cat), escape(words.lower()), rel, escape(p["name"]),
               glyph(cat), escape(cat), escape(category_label(cat)), escape(p["name"]), escape(entry.get("description", "")),
               extra, "hosted elsewhere" if p.get("external") else counts_label(items), escape(version(p))))


def render_index(plugins, market):
    total = sum(len(p["items"]) for p in plugins)
    cats = {}
    for p in plugins:
        c = p["entry"].get("category", "other")
        cats[c] = cats.get(c, 0) + 1
    chips = ['<button type="button" class="w-chip" data-cat="" aria-pressed="true">All <span>%d</span></button>' % len(plugins)]
    for c, n in sorted(cats.items(), key=lambda kv: (-kv[1], kv[0])):
        chips.append('<button type="button" class="w-chip" data-cat="%s" aria-pressed="false">%s <span>%d</span></button>'
                     % (escape(c), escape(category_label(c)), n))
    by_name = {p["name"]: p for p in plugins}
    featured = "".join(plugin_card(by_name[n], "", True) for n in FEATURED if n in by_name)
    cards = "".join(plugin_card(p, "") for p in sorted(plugins, key=lambda p: p["name"]))
    licences = sorted({p["manifest"].get("license") or p["entry"].get("license") or "unlicensed" for p in plugins})
    add_cmd = "claude plugin marketplace add %s" % MARKETPLACE_REPO
    term_lines = [
        ("cmt", "# 1. add the wovemind marketplace"), ("cmd", add_cmd),
        ("cmt", "# 2. install a plugin"), ("cmd", "claude plugin install plan-tools@wovemind"),
        ("cmt", "# 3. in Claude Code, run one of its skills"), ("cc", "/plan-tools:split-plan"),
    ]
    term = "".join('<span class="w-t w-t-%s">%s</span>' % (k, escape(t)) for k, t in term_lines)
    steps = [
        ("Add the marketplace", "Once, in your terminal or inside Claude Code. It lists every plugin here.",
         '<path d="m4 7 4 4-4 4"/><path d="M11 16h9"/>', add_cmd),
        ("Install a plugin", "Pick one below. Its skills and commands load into Claude Code.",
         '<path d="M12 3 4 7v10l8 4 8-4V7z"/><path d="m4 7 8 4 8-4M12 11v10"/>', "claude plugin install <plugin>@wovemind"),
        ("Run a skill", "Type its slash command, or just ask: skills also start when your request matches them.",
         '<path d="M15 4 9 20"/>', "/<plugin>:<skill>"),
    ]
    how = "".join(
        '<li class="w-how-step w-reveal"><svg class="w-how-ic" viewBox="0 0 24 24" aria-hidden="true">%s</svg>'
        '<span class="w-how-n" aria-hidden="true">%d</span><h3>%s</h3><p>%s</p><code>%s</code></li>'
        % (ic, n + 1, t, d, escape(c)) for n, (t, d, ic, c) in enumerate(steps))
    faq = [
        ("Where do I type these commands?",
         "<p>Commands that start with <code>claude plugin</code> go in your terminal. The same commands with a slash, "
         "like <code>/plugin install</code>, go inside a running Claude Code session. Each plugin page shows both.</p>"),
        ("How do I run a skill once it is installed?",
         "<p>Type its slash command in Claude Code, for example <code>/plan-tools:split-plan</code>. Skills also start on their own "
         "when what you ask matches what they do. Every skill and command here has a how-to page with its exact command.</p>"),
        ("How do I get updates?",
         "<p>Refresh the marketplace, then update each plugin you installed:</p>%s%s"
         "<p>Inside a session, run <code>/reload-plugins</code> afterwards.</p>"
         % (cmd_line("claude plugin marketplace update wovemind"), cmd_line("claude plugin update <plugin>@wovemind"))),
        ("Is it free, and can I contribute?",
         '<p>Yes. Every plugin is open source (%s) and lives in <a href="%s">the GitHub repository</a>. '
         'To add or change one, read <a href="%s/blob/main/CONTRIBUTING.md">CONTRIBUTING.md</a>.</p>'
         % (escape(", ".join(licences)), REPO_URL, REPO_URL)),
    ]
    faq_html = "".join('<details class="w-faq-q"><summary>%s</summary><div>%s</div></details>' % (q, a) for q, a in faq)
    body = """<main id="content">
<section class="w-hero"><div class="w-wrap w-hero-in">
  <div class="w-hero-copy">
    <h1>Plugins that make Claude Code plan, check and ship with you.</h1>
    <p class="w-lede">%s</p>
    <p class="w-count"><strong>%d plugins</strong>, <strong>%d skills and commands</strong>, each with a how-to page.</p>
    <div class="w-hero-install"><p class="w-where">Add the marketplace in your terminal</p>%s</div>
    <p class="w-hero-links"><a class="w-btn" href="#plugins">Browse plugins</a><a class="w-btn w-btn-quiet" href="#how">How it works</a></p>
  </div>
  <div class="w-term" aria-hidden="true"><div class="w-term-bar"><i></i><i></i><i></i><span>terminal</span></div><pre class="w-term-body">%s</pre></div>
</div></section>
<section class="w-section" aria-labelledby="feat-h"><div class="w-wrap">
  <div class="w-section-head"><p class="w-eyebrow">Start here</p><h2 id="feat-h">Featured</h2></div>
  <ul class="w-grid w-grid-feat">%s</ul>
</div></section>
<section class="w-section" id="plugins" aria-labelledby="all-h"><div class="w-wrap">
  <div class="w-section-head"><p class="w-eyebrow">Catalog</p><h2 id="all-h">All plugins</h2></div>
  <div class="w-filter">
    <div class="w-search"><label class="w-sr" for="w-q">Search plugins</label>
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/></svg>
      <input id="w-q" type="search" placeholder="Search plugins, skills and tags" autocomplete="off" spellcheck="false">
      <kbd aria-hidden="true">/</kbd></div>
    <div class="w-chips" role="group" aria-label="Filter by category">%s</div>
  </div>
  <p class="w-results" id="w-results" aria-live="polite">Showing all %d plugins</p>
  <ul class="w-grid" id="w-grid">%s</ul>
  <div class="w-empty" id="w-empty" hidden><p>No plugin matches that search.</p><button type="button" class="w-btn w-btn-quiet" id="w-clear">Clear search and filters</button></div>
</div></section>
<section class="w-section" id="how" aria-labelledby="how-h"><div class="w-wrap">
  <div class="w-section-head"><p class="w-eyebrow">Three steps</p><h2 id="how-h">How it works</h2></div>
  <ol class="w-how">%s</ol>
</div></section>
<section class="w-section" aria-labelledby="faq-h"><div class="w-wrap w-faq">
  <div class="w-section-head"><p class="w-eyebrow">Questions</p><h2 id="faq-h">FAQ</h2></div>
  <div>%s</div>
</div></section>
</main>""" % (escape(market.get("description", "")), len(plugins), total, cmd_line(add_cmd), term, featured,
              "".join(chips), len(plugins), cards, how, faq_html)
    title = "wovemind: Claude Code plugins"
    return page("", title, market.get("description", ""), body, "w-site w-home")


def item_row(p, i, rel):
    spec = i.get("spec", {})
    title = inline(spec.get("title") or i["name"])
    inv = '<code class="w-inv">%s%s</code>' % (escape(invocation(p, i)), (' <span class="w-hint">%s</span>' % escape(i["hint"])) if i["hint"] else "")
    desc = '<p class="w-item-desc">%s</p>' % inline(spec.get("bottom_line", "")) if spec.get("bottom_line") else ""
    if i.get("page"):
        return ('<li><a class="w-item" href="%s%s/">'
                '<span class="w-item-title">%s</span>%s%s<span class="w-item-go" aria-hidden="true">&rarr;</span></a></li>'
                % (rel, escape(i["name"]), title, inv, desc))
    return '<li><div class="w-item w-item-off"><span class="w-item-title">%s</span>%s<p class="w-item-desc">How-to page not built yet.</p></div></li>' % (title, inv)


def render_plugin(p, plugins):
    entry, m = p["entry"], p["manifest"]
    cat = entry.get("category", "other")
    rel = "../../"
    groups = []
    for kind in ("skill", "command", "mod"):
        its = [i for i in p["items"] if i["kind"] == kind]
        if its:
            groups.append('<h3 class="w-group">%s <span>%d</span></h3><ul class="w-items">%s</ul>'
                          % (KIND_GROUP[kind], len(its), "".join(item_row(p, i, "") for i in its)))
    if p.get("external"):
        groups = ['<p class="w-muted">Skill pages are not available here because this plugin is hosted outside this repo.</p>']
    elif not groups:
        groups.append('<p class="w-muted">This plugin has no skills or commands; it works through hooks.</p>')
    facts = [("Version", escape(version(p))), ("Category", escape(category_label(cat))),
             ("Licence", escape(m.get("license") or entry.get("license") or "?"))]
    if p.get("external"):
        source = entry.get("repository") or ""
        facts.append(("Source", '<a href="%s">%s</a>' % (escape(source), escape(re.sub(r"^https?://|/$", "", source)))
                      if source else "Hosted outside this repo"))
    else:
        source = "%s/tree/main/%s" % (REPO_URL, entry["source"][2:].rstrip("/"))
        facts += [("Includes", counts_label(p["items"])), ("Source", '<a href="%s">GitHub</a>' % escape(source))]
    home = m.get("homepage") or entry.get("homepage") or ""
    if home and not (source and home.startswith(source)):
        facts.append(("Homepage", '<a href="%s">%s</a>' % (escape(home), escape(re.sub(r"^https?://|/$", "", home)))))
    facts_html = "".join("<div><dt>%s</dt><dd>%s</dd></div>" % kv for kv in facts)
    names = {x["name"] for x in plugins}
    req = []
    deps = m.get("dependencies") or []
    if deps:
        req.append('<p class="w-side-label">Installed along with it</p><ul class="w-deps">%s</ul>' % "".join(
            '<li><a href="../%s/">%s</a></li>' % (escape(d), escape(d)) if d in names else "<li>%s</li>" % escape(d) for d in deps))
    conf = m.get("userConfig") or {}
    if conf:
        rows = []
        for key, c in conf.items():
            default = c.get("default")
            rows.append('<li><strong>%s</strong> <code>%s</code><p>%s%s</p></li>'
                        % (escape(c.get("title", key)), escape(key), escape(c.get("description", "")),
                           (" Default: <code>%s</code>." % escape(json.dumps(default) if not isinstance(default, str) else default))
                           if default not in (None, "") else ""))
        req.append('<p class="w-side-label">Settings</p><ul class="w-conf">%s</ul>' % "".join(rows))
    req_html = ('<div class="w-side-box"><h2 class="w-side-h">Requirements</h2>%s</div>' % "".join(req)) if req else ""
    related = [x for x in plugins if x is not p and x["entry"].get("category") == cat]
    related_html = ""
    if related:
        related_html = ('<section class="w-section w-related" aria-labelledby="rel-h"><div class="w-wrap"><div class="w-section-head">'
                        '<p class="w-eyebrow">Also in %s</p><h2 id="rel-h">Related plugins</h2></div><ul class="w-grid">%s</ul></div></section>'
                        % (escape(category_label(cat)), "".join(plugin_card(x, rel) for x in related)))
    body = """<main id="content">
<div class="w-wrap">%s
<div class="w-phead">%s<div><h1>%s</h1><p class="w-lede">%s</p>
<p class="w-pills"><span class="w-badge w-cat-%s">%s</span><span class="w-pill">v%s</span><span class="w-pill">%s</span></p></div></div>
<div class="w-cols">
  <div class="w-included"><h2>What&rsquo;s included</h2>%s</div>
  <aside class="w-side" aria-label="Install and details">
    <div class="w-side-box"><h2 class="w-side-h">Install</h2>%s</div>
    <div class="w-side-box"><h2 class="w-side-h">Details</h2><dl class="w-facts">%s</dl></div>
    %s
  </aside>
</div></div>
%s
</main>""" % (crumbs(rel, [(p["name"], None)]), glyph(cat, "w-glyph w-glyph-lg"), escape(p["name"]),
              escape(m.get("description") or entry.get("description", "")), escape(cat), escape(category_label(cat)),
              escape(version(p)), escape(m.get("license") or entry.get("license") or ""), "".join(groups),
              install_block(p["name"]), facts_html, req_html, related_html)
    return page(rel, "%s: Claude Code plugin" % p["name"], entry.get("description", ""), body, "w-site w-plugin")


def split_fragment(html):
    """build_page.py output: pull the <title> out for <head>, drop the claude: meta, keep style, main and script as written."""
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    title = m.group(1).strip() if m else ""
    rest = re.sub(r"<title>.*?</title>\s*", "", html, count=1, flags=re.S)
    rest = re.sub(r'<meta name="claude:[^"]*"[^>]*>\s*', "", rest)
    return title, rest


def render_howto(root, p, i, prev_i, next_i, errors):
    rel = "../../../"
    fd, tmp = tempfile.mkstemp(suffix=".html")
    os.close(fd)
    try:
        proc = subprocess.run([sys.executable, os.path.join(root, BUILD_PAGE), i["spec_path"], tmp],
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, universal_newlines=True)
        if proc.returncode != 0:
            msg = (proc.stderr.strip().splitlines() or ["exit %d" % proc.returncode])[-1]
            errors.append("site/specs/%s/%s.json: does not render: %s" % (p["name"], i["name"], msg))
            return None
        title_esc, fragment = split_fragment(read_text(tmp))
    finally:
        os.unlink(tmp)
    inv = invocation(p, i)
    shown = escape(inv) + ((' <span class="w-hint">%s</span>' % escape(i["hint"])) if i["hint"] else "")
    pager = []
    for label, cls, other in (("Previous", "w-prev", prev_i), ("Next", "w-next", next_i)):
        if other:
            pager.append('<a class="%s" href="../%s/"><span>%s</span><strong>%s</strong></a>'
                         % (cls, escape(other["name"]), label, inline(other.get("spec", {}).get("title") or other["name"])))
    body = """<div class="w-wrap w-narrow w-intro">%s
<div class="w-runbox"><p class="w-where"><span class="w-kind">%s</span> Type this in Claude Code</p>%s
<details class="w-need"><summary><span>Not installed yet? Install <strong>%s</strong> first</span></summary>%s</details></div>
</div>
<div class="w-frag" id="content">%s</div>
<nav class="w-wrap w-narrow w-pager" aria-label="More in %s">%s<a class="w-up" href="../"><span>All of</span><strong>%s</strong></a></nav>""" % (
        crumbs(rel, [(p["name"], "../"), (plain(i.get("spec", {}).get("title") or i["name"]), None)]),
        KIND_LABEL[i["kind"]], cmd_line(inv, shown), escape(p["name"]), install_block(p["name"], compact=True),
        fragment, escape(p["name"]), "".join(pager), escape(p["name"]))
    desc = plain(i.get("spec", {}).get("bottom_line") or i["description"])
    return page(rel, "%s · %s · wovemind" % (unescape(title_esc), p["name"]), desc, body, "w-site w-howto")


# ---------------------------------------------------------------- checks and build

LINK_RE = re.compile(r"""\s(?:href|src)\s*=\s*["']([^"']*)["']""")


def check_links(out):
    """Every href and src in the built site is external, a same-page anchor, or a relative path to a file that exists."""
    errs, out = [], os.path.abspath(out)
    for dirpath, _, files in os.walk(out):
        for fn in sorted(files):
            if not fn.endswith(".html"):
                continue
            path = os.path.join(dirpath, fn)
            relpath = os.path.relpath(path, out)
            for url in LINK_RE.findall(read_text(path)):
                if re.match(r"^(https?:|mailto:|data:|#)", url):
                    continue
                if url.startswith("/") or re.match(r"^[a-z][a-z0-9+.-]*:", url, re.I):
                    errs.append("%s: link %s must be relative" % (relpath, url))
                    continue
                target = url.split("#", 1)[0].split("?", 1)[0]
                full = os.path.normpath(os.path.join(dirpath, target))
                if target.endswith("/") or os.path.isdir(full):
                    full = os.path.join(full, "index.html")
                if not (full + os.sep).startswith(out + os.sep) or not os.path.isfile(full):
                    errs.append("%s: broken link %s" % (relpath, url))
    return errs


def build(root, out):
    """Build the site into `out`. Returns (errors, page count); writes whatever it can even when there are errors."""
    root, out = os.path.abspath(root), os.path.abspath(out)
    if (root + os.sep).startswith(out + os.sep):
        raise SystemExit("refusing to build into %s: it contains the repository" % out)
    errors = []
    if os.path.exists(out):
        # Only wipe an empty dir or a previous build, so a mistyped --out (site, plugins, ~) never deletes sources.
        if os.listdir(out) and not os.path.isfile(os.path.join(out, "assets", "site.js")):
            raise SystemExit("refusing to replace %s: it is not empty and not a previous site build" % out)
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "assets"))
    for fn in ("site.css", "site.js"):
        shutil.copy(os.path.join(root, "site", "assets", fn), os.path.join(out, "assets", fn))
    market, plugins = discover(root, errors)
    attach_specs(root, plugins, errors)
    pages = 0
    for p in plugins:
        with_spec = [i for i in p["items"] if "spec" in i]
        for n, i in enumerate(with_spec):
            html = render_howto(root, p, i, with_spec[n - 1] if n else None,
                                with_spec[n + 1] if n + 1 < len(with_spec) else None, errors)
            if html is not None:
                i["page"] = True
                write(os.path.join(out, "plugins", p["name"], i["name"], "index.html"), html)
                pages += 1
    for p in plugins:
        write(os.path.join(out, "plugins", p["name"], "index.html"), render_plugin(p, plugins))
        pages += 1
    write(os.path.join(out, "index.html"), render_index(plugins, market))
    errors.extend(check_links(out))
    return errors, pages + 1


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# ---------------------------------------------------------------- self-test

def selftest():
    # Frontmatter: the shapes the repo's SKILL.md and command files actually use.
    fm = parse_frontmatter('---\nname: x\ndescription: >\n  Folded line one\n  and two.\nargument-hint: "[a | b] <c>"\n---\nbody\n')
    assert fm == {"name": "x", "description": "Folded line one and two.", "argument-hint": "[a | b] <c>"}, fm
    assert parse_frontmatter("---\nargument-hint: [optional one-line app idea]\n---\n")["argument-hint"] == "[optional one-line app idea]"
    assert parse_frontmatter("---\nargument-hint: <pr> (defaults to the current PR)\n---\n")["argument-hint"] == "<pr> (defaults to the current PR)"
    assert parse_frontmatter("---\na: 'it''s'\nb: |\n  one\n  two\n---\n") == {"a": "it's", "b": "one\ntwo"}
    assert parse_frontmatter("no frontmatter\n") == {}
    assert inline("run `a<b>` **now**") == "run <code>a&lt;b&gt;</code> <strong>now</strong>"
    assert inline("`f(**kw**)`") == "<code>f(**kw**)</code>"

    tmp = tempfile.mkdtemp()
    try:
        # Missing-spec and orphan detection on a tiny fake repo.
        fake = os.path.join(tmp, "repo")
        write(os.path.join(fake, ".claude-plugin", "marketplace.json"),
              json.dumps({"plugins": [{"name": "demo", "source": "./plugins/demo", "category": "workflow"}]}))
        write(os.path.join(fake, "plugins", "demo", ".claude-plugin", "plugin.json"), json.dumps({"name": "demo", "version": "1.0.0"}))
        write(os.path.join(fake, "plugins", "demo", "README.md"), "Run `/pane` to open it.\n")
        write(os.path.join(fake, "plugins", "demo", "skills", "has-spec", "SKILL.md"), "---\nname: has-spec\n---\n")
        write(os.path.join(fake, "plugins", "demo", "skills", "no-spec", "SKILL.md"), "---\nname: no-spec\nargument-hint: <x>\n---\n")
        write(os.path.join(fake, "plugins", "demo", "commands", "cmd.md"), "---\ndescription: c\n---\n")
        for rel in ("demo/has-spec.json", "demo/cmd.json", "demo/pane.json", "demo/pan.json", "ghost/x.json"):
            write(os.path.join(fake, "site", "specs", rel), "{}")
        errs = []
        _, plugins = discover(fake, errs)
        attach_specs(fake, plugins, errs)
        kinds = {i["name"]: i["kind"] for i in plugins[0]["items"]}
        assert kinds == {"has-spec": "skill", "no-spec": "skill", "cmd": "command", "pane": "mod"}, kinds
        assert [i["name"] for i in plugins[0]["items"]] == ["has-spec", "no-spec", "cmd", "pane"]
        assert any(e.startswith("missing spec: site/specs/demo/no-spec.json") and "/demo:no-spec" in e for e in errs), errs
        assert any("pan.json" in e for e in errs) and any("ghost" in e for e in errs), errs  # `/pane` does not cover pan
        assert len(errs) == 3, errs
        assert invocation(plugins[0], plugins[0]["items"][3]) == "/pane"

        # External sources, URL schemes and path-safe names.
        fake2 = os.path.join(tmp, "repo2")
        write(os.path.join(fake2, ".claude-plugin", "marketplace.json"), json.dumps({"plugins": [
            {"name": "ext", "source": {"source": "github", "repo": "o/ext"}, "description": "d", "category": "media",
             "tags": ["t"], "homepage": "https://ext.dev/", "repository": "https://github.com/o/ext"},
            {"name": "evil", "source": "npm-pkg", "homepage": "javascript:alert(1)"},
            {"name": "../up", "source": "./plugins/up"},
            {"name": "loc", "source": "./plugins/loc"}]}))
        write(os.path.join(fake2, "plugins", "loc", ".claude-plugin", "plugin.json"), json.dumps({"repository": "ftp://x"}))
        write(os.path.join(fake2, "plugins", "loc", "skills", "Bad.Name", "SKILL.md"), "---\nname: b\n---\n")
        write(os.path.join(fake2, "plugins", "loc", "commands", ".hidden.md"), "---\n---\n")
        write(os.path.join(fake2, "site", "specs", "loc", "..x.json"), "{}")
        write(os.path.join(fake2, "site", "specs", "ext", "a.json"), "{}")
        errs = []
        _, plugins = discover(fake2, errs)
        attach_specs(fake2, plugins, errs)
        assert [p["name"] for p in plugins] == ["ext", "evil", "loc"] and plugins[2]["items"] == [], plugins
        assert sum("must match" in e for e in errs) == 4, errs  # ../up, Bad.Name, .hidden, ..x
        assert any("evil field homepage" in e for e in errs) and any("loc field repository" in e for e in errs), errs
        assert any("site/specs/ext/" in e and "outside this repo" in e for e in errs) and len(errs) == 7, errs
        assert "homepage" not in plugins[1]["entry"]  # dropped, never rendered
        html = render_plugin(plugins[0], plugins)
        assert "hosted outside this repo" in html and 'href="https://ext.dev/"' in html and 'href="https://github.com/o/ext"' in html
        assert "plugin install ext@wovemind" in html and "hosted elsewhere" in plugin_card(plugins[0], "")
        assert "Hosted outside this repo" in render_plugin(plugins[1], plugins)

        # Link check: relative links that resolve pass; missing targets and root-absolute links fail.
        site = os.path.join(tmp, "site")
        write(os.path.join(site, "index.html"), '<a href="a/">x</a><a href="#top">t</a><a href="https://e.com/">e</a>'
                                                 '<link href="assets/s.css"><a href="b/">gone</a><a href="/a/">abs</a>')
        write(os.path.join(site, "a", "index.html"), '<a href="../">up</a><a href="../index.html#x">up</a>')
        write(os.path.join(site, "assets", "s.css"), "")
        errs = check_links(site)
        assert len(errs) == 2 and "broken link b/" in errs[0] and "/a/ must be relative" in errs[1], errs

        # --out never wipes a non-empty directory that is not a previous build.
        try:
            build(ROOT, fake)
            raise AssertionError("build wiped a non-build directory")
        except SystemExit:
            pass
        assert os.path.isfile(os.path.join(fake, "plugins", "demo", "README.md"))

        # The real site: every skill and command has a spec, every spec renders, every link resolves.
        errors, pages = build(ROOT, os.path.join(tmp, "out"))
        if errors:
            print("site/build.py selftest: the real build has %d problem(s):" % len(errors))
            for e in errors:
                print("  " + e)
            return 1
        assert os.path.isfile(os.path.join(tmp, "out", "index.html")) and pages > 20
    finally:
        shutil.rmtree(tmp)
    print("site/build.py selftest: OK")
    return 0


def main(argv):
    if argv[1:] == ["--selftest"]:
        return selftest()
    out = os.path.join(ROOT, "_site")
    if len(argv) == 3 and argv[1] == "--out":
        out = argv[2]
    elif len(argv) != 1:
        sys.stderr.write("usage: build.py [--out DIR] | --selftest\n")
        return 2
    errors, pages = build(ROOT, out)
    print("built %d pages into %s" % (pages, out))
    if errors:
        print("%d problem(s):" % len(errors))
        for e in errors:
            print("  " + e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
