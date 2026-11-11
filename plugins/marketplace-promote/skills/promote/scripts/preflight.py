#!/usr/bin/env python3
"""Pre-flight for promoting a plugin marketplace in directories.

Usage:
  preflight.py <repo-path> [--state <file>] [--json]
  preflight.py --selftest

Output (--json): {"repo": {...}, "directories": [{id, name, channel, target, status, problems[], links[],
eligible_from?}], "plugins": [{name, path, problems[]}]}. A problem is {plugin, file, rule, fix}.
Status: listed | pending | ready | blocked | closed | not-yet-eligible. Only `gh` read calls and anonymous
GETs are made. owner/repo come from `git remote get-url origin`. Python 3 stdlib only.
"""
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(HERE, "..", "directories.json")
RESERVED_PREFIX = ("claude-", "anthropic-", "anthropics-", "cc-plugin-")
RESERVED_NAMES = {"claude", "anthropic", "anthropics", "claude-code", "claude-mods"}
PRUNE = {".git", "node_modules"}
PIN = re.compile(r"(@|==)\d+\.\d+\.\d+([-+][\w.]+)?$")


# ---- network seams (stubbed in the selftest) ----
def gh_json(args):
    try:
        r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=60)
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


def http_get(url):
    """(status, text); (0, "") on network error. Anything but 200 means "not listed"."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 marketplace-promote"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read(5_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def run_validate(path):
    """(ok, detail); ok None when `claude` is missing."""
    if not shutil.which("claude"):
        return None, "claude CLI not on PATH"
    try:
        r = subprocess.run(["claude", "plugin", "validate", "."], cwd=path, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return False, "claude plugin validate timed out after 300s"
    return r.returncode == 0, (r.stdout + r.stderr).strip()[-500:]


# ---- helpers ----
def prob(rule, fix, plugin=None, file=None):
    return {"plugin": plugin, "file": file, "rule": rule, "fix": fix}


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def origin(path):
    r = subprocess.run(["git", "remote", "get-url", "origin"], cwd=path, capture_output=True, text=True)
    m = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(\.git)?/?\s*$", r.stdout)
    if not m:
        sys.exit("preflight: no github.com `origin` remote in " + path)
    return m.group(1), m.group(2)


def words_outside_code(text):
    return len(re.sub(r"```.*?(```|\Z)", "", text, flags=re.S).split())


def walk(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in PRUNE]
        yield d, dirs, files


def mcp_servers(pdir, pjson):
    m = read_json(os.path.join(pdir, ".mcp.json")) or {}
    servers = {**m.get("mcpServers", m), **(pjson.get("mcpServers") if isinstance(pjson.get("mcpServers"), dict) else {})}
    return {k: v for k, v in servers.items() if isinstance(v, dict)}


# ---- checks ----
def check_plugin(root, entry):
    name = entry.get("name", "?")
    src = entry.get("source")
    if not isinstance(src, str) or not src.startswith("./"):
        return None  # external source: not checkable locally
    pdir = os.path.join(root, src)
    rel = lambda p: os.path.relpath(p, root)
    pj_path = os.path.join(pdir, ".claude-plugin", "plugin.json")
    pj = read_json(pj_path) or {}
    P = []
    readme = next((os.path.join(pdir, f) for f in os.listdir(pdir) if f.lower() == "readme.md"), None) if os.path.isdir(pdir) else None
    n = words_outside_code(open(readme, encoding="utf-8", errors="replace").read()) if readme else 0
    if n < 40:
        P.append(prob("plugin.readme_words", f"README has {n} words outside code blocks; write at least 40.", name, rel(readme or os.path.join(pdir, "README.md"))))
    has_license = pj.get("license") or any(f.upper().startswith("LICENSE") for f in os.listdir(pdir)) if os.path.isdir(pdir) else False
    if not has_license:
        P.append(prob("plugin.license", "Add a LICENSE file in the plugin folder or a `license` field in plugin.json.", name, rel(pj_path)))
    for d, dirs, files in walk(pdir):
        for f in files:
            if f == ".DS_Store":
                P.append(prob("plugin.ds_store", "Delete the file and add .DS_Store to .gitignore.", name, rel(os.path.join(d, f))))
        for f in files + dirs:
            if os.path.islink(os.path.join(d, f)):
                P.append(prob("plugin.symlinks", "Replace the symlink with a real file or directory.", name, rel(os.path.join(d, f))))
    for sname, s in mcp_servers(pdir, pj).items():
        args = [str(a) for a in s.get("args", [])]
        if s.get("command") in ("npx", "uvx"):
            pkg = next((a for a in args if not a.startswith("-")), "")
            if not PIN.search(pkg):
                P.append(prob("plugin.npx_pinned", f"MCP server '{sname}' runs `{pkg or s['command']}`; pin an exact version (pkg@1.2.3 / pkg==1.2.3).", name, rel(os.path.join(pdir, ".mcp.json"))))
    pname = pj.get("name", name)
    if pname.startswith(RESERVED_PREFIX) or pname in RESERVED_NAMES or ("official" in pname and re.search(r"claude|anthropic", pname)):
        P.append(prob("plugin.name_reserved", f"'{pname}' is a reserved plugin name; rename it.", name, rel(pj_path)))
    if pname != os.path.basename(os.path.normpath(pdir)) or pname != name:
        P.append(prob("plugin.name_matches_folder", f"plugin.json name '{pname}', marketplace entry '{name}', folder '{os.path.basename(os.path.normpath(pdir))}' must be identical.", name, rel(pj_path)))
    return P


def check_repo(root, owner, repo, info):
    P = []
    if info is None or info.get("private"):
        P.append(prob("repo.public", f"{owner}/{repo} is private or unreachable via gh; make it public.", file=None))
    if not any(f.upper().startswith("LICENSE") for f in os.listdir(root)):
        P.append(prob("repo.license", "Add a LICENSE file at the repo root.", file="LICENSE"))
    ok, detail = run_validate(root)
    if ok is None:
        P.append(prob("repo.validate", "Cannot validate: " + detail + ". Install Claude Code and re-run.", file=".claude-plugin/marketplace.json"))
    elif not ok:
        P.append(prob("repo.validate", "`claude plugin validate .` fails: " + detail, file=".claude-plugin/marketplace.json"))
    return P


def subst(s, o, r):
    return s.replace("{repo_url}", f"https://github.com/{o}/{r}").replace("{owner}", o).replace("{repo}", r)


def listed_links(d, o, r):
    out = []
    for c in d.get("listed_check", []):
        url = subst(c["url"], o, r)
        status, text = http_get(url)
        needle = subst(c.get("contains", ""), o, r)
        # whole-token match so acme/mp does not match acme/mp-extra or other-acme/mp
        if status == 200 and re.search(r"(?<![\w.-])" + re.escape(needle) + r"(?![\w.-])", text, re.I):
            out.append(url)
    return out


def pending_links(d, o, r, state):
    links = [e["url"] for e in (state.get("submissions", {}).get(d["id"]) or []) if e.get("url")]
    if d["channel"] in ("pr", "issue+pr") and d.get("bots_allowed", True):
        for kind in ("prs", "issues"):
            found = gh_json(["search", kind, "--author", "@me", "--repo", d["target"], f"https://github.com/{o}/{r}",
                             "--state", "open", "--json", "url"]) or []
            links += [x["url"] for x in found]
    return list(dict.fromkeys(links))


def directory_status(d, o, r, info, problems, plugin_problems, plugin_count, state, now):
    out = {"id": d["id"], "name": d["name"], "channel": d["channel"], "target": d["target"], "problems": [], "links": []}
    links = listed_links(d, o, r)
    if links:
        return {**out, "status": "listed", "links": links}
    links = pending_links(d, o, r, state)
    if links:
        return {**out, "status": "pending", "links": links}
    if d["channel"] in ("pr", "issue+pr"):
        t = gh_json(["api", f"repos/{d['target']}"]) or {}
        if t and (not t.get("has_pull_requests", True) or (d["channel"] == "issue+pr" and not t.get("has_issues", True))):
            return {**out, "status": "closed", "problems": [prob("directory.accepts", f"{d['target']} has pull requests/issues disabled; re-check on the next run.")]}
    lim = d.get("limits", {})
    if "min_age_days" in lim and info and info.get("created_at"):
        created = dt.date.fromisoformat(info["created_at"][:10])
        eligible = created + dt.timedelta(days=lim["min_age_days"])
        if now < eligible and info.get("stargazers_count", 0) < lim.get("or_min_stars", 1 << 30):
            return {**out, "status": "not-yet-eligible", "eligible_from": eligible.isoformat()}
    reqs = set(d.get("requirements", []))
    repo_p = [p for p in problems if p["rule"] in reqs]
    plug_p = [p for p in plugin_problems if p["rule"] in reqs]
    bad = {p["plugin"] for p in plug_p}
    # per-plugin directories only lose the failing plugins; the rest can still go
    blocked = bool(repo_p) or (plug_p and (not d.get("per_plugin") or len(bad) >= plugin_count))
    return {**out, "status": "blocked" if blocked else "ready", "problems": repo_p + plug_p}


def run(root, state_file=None, now=None):
    root = os.path.abspath(root)
    o, r = origin(root)
    state = (read_json(state_file) if state_file else None) or {}
    now = now or dt.date.today()
    info = gh_json(["api", f"repos/{o}/{r}"])
    mp = read_json(os.path.join(root, ".claude-plugin", "marketplace.json")) or {}
    entries = mp.get("plugins", [])
    names = [e.get("name") for e in entries]
    repo_p = check_repo(root, o, r, info)
    plugins, plugin_p = [], []
    for e in entries:
        P = check_plugin(root, e)
        if P is None:
            continue
        if names.count(e.get("name")) > 1:
            P.append(prob("plugin.name_unique", f"Plugin name '{e.get('name')}' appears more than once in marketplace.json.", e.get("name"), ".claude-plugin/marketplace.json"))
        plugins.append({"name": e.get("name"), "path": e["source"], "problems": P})
        plugin_p += P
    dirs = json.load(open(RULES, encoding="utf-8"))["directories"]
    res = [directory_status(d, o, r, info, repo_p, plugin_p, len(plugins), state, now) for d in dirs]
    return {"repo": {"owner": o, "repo": r, "url": f"https://github.com/{o}/{r}",
                     "created_at": (info or {}).get("created_at"), "stars": (info or {}).get("stargazers_count"),
                     "problems": repo_p},
            "directories": res, "plugins": plugins}


# ---- selftest ----
def selftest():
    global gh_json, http_get, run_validate
    tmp = tempfile.mkdtemp()
    try:
        def w(rel, text="x"):
            p = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w").write(text)
        good = "word " * 50
        plugins = {"good": {}, "short": {}, "dsstore": {}, "link": {}, "npx": {}, "mism": {}, "nolic": {}}
        entries = []
        for n in plugins:
            lic = n != "nolic"
            code = "```\n" + "code " * 100 + "\n```\n"
            w(f"plugins/{n}/.claude-plugin/plugin.json", json.dumps({"name": "other" if n == "mism" else n, **({"license": "MIT"} if lic else {})}))
            w(f"plugins/{n}/README.md", (("few words\n" + code) if n == "short" else good))
            entries.append({"name": n, "source": f"./plugins/{n}"})
        w("plugins/dsstore/.DS_Store")
        os.symlink(os.path.join(tmp, "plugins/good/README.md"), os.path.join(tmp, "plugins/link/ln"))
        w("plugins/npx/.mcp.json", json.dumps({"mcpServers": {"a": {"command": "npx", "args": ["-y", "pkg"]}, "b": {"command": "npx", "args": ["-y", "pkg@1.2.3"]}}}))
        w("plugins/good/.mcp.json", json.dumps({"mcpServers": {"a": {"command": "uvx", "args": ["pkg==1.2.3"]}}}))
        w(".claude-plugin/marketplace.json", json.dumps({"name": "m", "plugins": entries}))
        w("LICENSE")
        subprocess.run(["git", "init", "-q"], cwd=tmp)
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/acme/mp.git"], cwd=tmp)
        repo_info = {"private": False, "created_at": "2026-11-11T00:00:00Z", "stargazers_count": 0}
        closed = {"has_pull_requests": False, "has_issues": False}
        gh_json = lambda a: closed if a[:2] == ["api", "repos/ccplugins/awesome-claude-code-plugins"] else (
            repo_info if a[0] == "api" and a[1] == "repos/acme/mp" else ({"has_pull_requests": True, "has_issues": True} if a[0] == "api" else []))
        http_get = lambda u: (404, "")
        run_validate = lambda p: (True, "")
        out = run(tmp, now=dt.date(2026, 11, 20))
        by = {p["name"]: {x["rule"] for x in p["problems"]} for p in out["plugins"]}
        want = {"short": "plugin.readme_words", "dsstore": "plugin.ds_store", "link": "plugin.symlinks",
                "npx": "plugin.npx_pinned", "mism": "plugin.name_matches_folder", "nolic": "plugin.license"}
        for n, rule in want.items():
            assert rule in by[n], (n, by[n])
        assert not by["good"], by["good"]
        for n in ("npx",):
            assert sum(p["rule"] == "plugin.npx_pinned" for q in out["plugins"] if q["name"] == n for p in q["problems"]) == 1
        assert all(p["file"] and p["fix"] for q in out["plugins"] for p in q["problems"])
        d = {x["id"]: x for x in out["directories"]}
        assert d["awesome-claude-code"]["status"] == "not-yet-eligible" and d["awesome-claude-code"]["eligible_from"] == "2026-11-25", d["awesome-claude-code"]
        assert d["ccplugins"]["status"] == "closed", d["ccplugins"]
        assert d["composio"]["status"] == "ready" and d["aitmpl"]["status"] == "ready" and d["aitmpl"]["problems"], d["aitmpl"]
        out = run(tmp, now=dt.date(2026, 11, 26))
        assert {x["id"]: x for x in out["directories"]}["awesome-claude-code"]["status"] == "ready"
        http_get = lambda u: (200, "see https://github.com/acme/mp-extra") if "composio" in u else (404, "")
        out = run(tmp)
        assert {x["id"]: x for x in out["directories"]}["composio"]["status"] == "ready"
        http_get = lambda u: (200, "see https://github.com/acme/mp") if "composio" in u else (404, "")
        out = run(tmp)
        assert {x["id"]: x for x in out["directories"]}["composio"]["status"] == "listed"
        st = os.path.join(tmp, "state.json")
        w("state.json", json.dumps({"submissions": {"anthropic": [{"url": "https://x/1"}]}}))
        out = run(tmp, st)
        assert {x["id"]: x for x in out["directories"]}["anthropic"]["status"] == "pending"
    finally:
        shutil.rmtree(tmp)
    print("preflight selftest ok")


def main(argv):
    if "--selftest" in argv:
        return selftest()
    args = [a for a in argv if not a.startswith("--")]
    state = argv[argv.index("--state") + 1] if "--state" in argv else None
    if state in args:
        args.remove(state)
    if not args:
        sys.exit(__doc__)
    out = run(args[0], state)
    if "--json" in argv:
        print(json.dumps(out, indent=2))
    else:
        for d in out["directories"]:
            print(f"{d['status']:17} {d['id']}" + (f"  (from {d['eligible_from']})" if d.get("eligible_from") else ""))
            for p in d["problems"]:
                print(f"    {p['rule']} [{p['plugin'] or 'repo'}] {p['file'] or ''}: {p['fix']}")


if __name__ == "__main__":
    main(sys.argv[1:])
