#!/usr/bin/env python3
"""List dependency licenses for a repo and flag copyleft / unknown ones.

Usage:
  license_scan.py <repo> [--json]
  license_scan.py --selftest

Per ecosystem, the first tool that works wins; otherwise a stdlib fallback reads manifests:
  python: pip-licenses --python <repo>/.venv/bin/python (PATH, then uvx) -> .venv site-packages METADATA
          -> names from requirements*.txt / pyproject.toml / uv.lock / poetry.lock (license "unknown")
  go:     go-licenses report ./... -> go.mod require lines (license "unknown", install go-licenses)
  node:   npx --yes license-checker --json (only when node_modules exists) -> node_modules/*/package.json
          -> package-lock.json names (license "unknown")
Never installs anything into the audited repo. Python 3 stdlib only.

Output: {"ecosystems", "packages":[{"name","version","license","class","via"}],
         "flags":{"strong_copyleft","weak_copyleft","unknown"}, "tool_used":{eco: tool}, "notes":[...]}
"""
import csv
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
from importlib import metadata

TIMEOUT = 60
WEAK = re.compile(r"\b(LGPL|MPL|EPL|CDDL|EUPL|CPL)|Lesser General Public|Mozilla Public|Eclipse Public", re.I)
STRONG = re.compile(r"\b(A?GPL|SSPL)|\bOSL\b|General Public License|Affero|Server Side Public", re.I)
PERMISSIVE = re.compile(r"\b(MIT|BSD|Apache|ISC|Unlicense|CC0|0BSD|Zlib|PSF|Python-2\.0|WTFPL|BlueOak|HPND|BSL-1\.0|Boost|X11|Artistic|PostgreSQL|CC-BY(?!-NC|-SA))\b|Python Software Foundation|Public Domain", re.I)
RANK = {"permissive": 0, "weak_copyleft": 1, "strong_copyleft": 2, "unknown": 3}


def classify_one(lic):
    if WEAK.search(lic):  # before STRONG: "LGPL" contains "GPL"
        return "weak_copyleft"
    if STRONG.search(lic):
        return "strong_copyleft"
    if PERMISSIVE.search(lic):
        return "permissive"
    return "unknown"


def classify(lic):
    """SPDX-ish string -> class. 'A OR B' takes the least restrictive option; 'A AND B' the most."""
    lic = (lic or "").strip().strip("()")
    if not lic or lic.upper() in ("UNKNOWN", "UNLICENSED", "NONE", "SEE LICENSE IN LICENSE"):
        return "unknown"
    best = None
    for alt in re.split(r"\s+OR\s+|\s*/\s*|\s*;\s*", lic, flags=re.I):
        worst = max((classify_one(p) for p in re.split(r"\s+AND\s+", alt, flags=re.I)), key=RANK.get)
        best = worst if best is None or RANK[worst] < RANK[best] else best
    return best


def run(cmd, cwd):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT)
        return r.stdout if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def pkg(name, version, lic, via):
    return {"name": name, "version": version or "", "license": lic or "unknown", "class": classify(lic), "via": via}


# ---------- python ----------
def py_names(repo):
    names = set()
    for f in glob.glob(os.path.join(repo, "requirements*.txt")):
        for line in open(f, errors="ignore"):
            m = re.match(r"\s*([A-Za-z0-9][\w.-]*)", line)
            if m and not line.lstrip().startswith(("#", "-")):
                names.add(m.group(1))
    for lock in ("uv.lock", "poetry.lock"):
        p = os.path.join(repo, lock)
        if os.path.exists(p):
            names |= set(re.findall(r'^name = "([^"]+)"', open(p, errors="ignore").read(), re.M))
    p = os.path.join(repo, "pyproject.toml")
    if os.path.exists(p) and not names:
        body = open(p, errors="ignore").read()
        m = re.search(r"^dependencies\s*=\s*\[(.*?)\]", body, re.M | re.S)
        if m:
            names |= set(re.findall(r'"\s*([A-Za-z0-9][\w.-]*)', m.group(1)))
    return names


def scan_python(repo, notes):
    vpy = os.path.join(repo, ".venv", "bin", "python")
    if os.path.exists(vpy):
        for tool, cmd in (("pip-licenses", ["pip-licenses"]), ("uvx pip-licenses", ["uvx", "pip-licenses"])):
            if not shutil.which(cmd[0]):
                continue
            out = run(cmd + ["--format=json", "--python", vpy], repo)
            if out:
                try:
                    return tool, [pkg(d["Name"], d["Version"], d["License"], tool) for d in json.loads(out)]
                except (ValueError, KeyError):
                    pass
        sp = glob.glob(os.path.join(repo, ".venv", "lib", "python*", "site-packages"))
        if sp:
            out = []
            for d in metadata.distributions(path=sp):
                m = d.metadata
                lic = m.get("License-Expression") or ""
                if not lic or len(lic) > 80:
                    lic = m.get("License") or ""
                if not lic or len(lic) > 80:  # full license text pasted in -> use classifiers
                    cls = [c.split("::")[-1].strip() for c in (m.get_all("Classifier") or []) if c.startswith("License ::")]
                    lic = " OR ".join(cls) or "unknown"
                out.append(pkg(m["Name"], d.version, lic, "site-packages METADATA"))
            return "importlib.metadata (.venv)", out
    names = py_names(repo)
    if names:
        notes.append("python: no .venv found; licenses unknown. Run `uv sync` then `uvx pip-licenses --python .venv/bin/python`.")
    return "manifest names only", [pkg(n, "", "unknown", "manifest") for n in sorted(names)]


# ---------- go ----------
def scan_go(repo, notes):
    if shutil.which("go-licenses"):
        out = run(["go-licenses", "report", "./..."], repo)
        if out:
            rows = [r for r in csv.reader(io.StringIO(out)) if len(r) >= 3]
            return "go-licenses", [pkg(r[0], "", r[2], "go-licenses") for r in rows]
    body = open(os.path.join(repo, "go.mod"), errors="ignore").read()
    reqs = re.findall(r"^\s*(?:require\s+)?([\w.-]+\.[\w./-]+)\s+(v[\w.+-]+)", body, re.M)
    notes.append("go: go-licenses not available; licenses unknown. Install: go install github.com/google/go-licenses@latest")
    return "go.mod only", [pkg(n, v, "unknown", "go.mod") for n, v in reqs]


# ---------- node ----------
def node_roots(repo):
    roots = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in {"node_modules", ".git", ".venv", "Pods", "build", "dist", ".claude"}]
        if "package.json" in files:
            roots.append(root)
    return roots


def scan_node(root, eco, notes):
    nm = os.path.join(root, "node_modules")
    if os.path.isdir(nm):
        if shutil.which("npx"):
            out = run(["npx", "--yes", "license-checker", "--json", "--start", root], root)
            if out:
                try:
                    data = json.loads(out)
                    res = []
                    for key, v in data.items():
                        name, _, ver = key.rpartition("@")
                        lic = v.get("licenses", "unknown")
                        res.append(pkg(name, ver, " OR ".join(lic) if isinstance(lic, list) else lic, "license-checker"))
                    return "license-checker", res
                except ValueError:
                    pass
        res = []
        for pj in glob.glob(os.path.join(nm, "*", "package.json")) + glob.glob(os.path.join(nm, "@*", "*", "package.json")):
            try:
                d = json.load(open(pj, errors="ignore"))
            except ValueError:
                continue
            lic = d.get("license")
            if isinstance(lic, dict):
                lic = lic.get("type")
            res.append(pkg(d.get("name", os.path.basename(os.path.dirname(pj))), d.get("version"), lic, "node_modules package.json"))
        return "node_modules package.json", res
    lock = os.path.join(root, "package-lock.json")
    names = []
    if os.path.exists(lock):
        try:
            names = [k.split("node_modules/")[-1] for k in json.load(open(lock)).get("packages", {}) if k]
        except ValueError:
            pass
    if not names:
        names = list(json.load(open(os.path.join(root, "package.json"))).get("dependencies", {}))
    notes.append(f"{eco}: no node_modules; licenses unknown. Run `npm ci` then `npx license-checker --json`.")
    return "package-lock names only", [pkg(n, "", "unknown", "package-lock") for n in sorted(set(names))]


def scan(repo):
    notes, packages, tools, ecos = [], [], {}, []
    if any(os.path.exists(os.path.join(repo, f)) for f in ("pyproject.toml", "uv.lock", "poetry.lock")) or glob.glob(os.path.join(repo, "requirements*.txt")):
        ecos.append("python")
        tools["python"], got = scan_python(repo, notes)
        packages += got
    if os.path.exists(os.path.join(repo, "go.mod")):
        ecos.append("go")
        tools["go"], got = scan_go(repo, notes)
        packages += got
    for root in node_roots(repo):
        eco = "node" if root == repo else "node:" + os.path.relpath(root, repo)
        ecos.append(eco)
        tools[eco], got = scan_node(root, eco, notes)
        packages += got
    flags = {c: sorted({f"{p['name']} ({p['license']})" for p in packages if p["class"] == c})
             for c in ("strong_copyleft", "weak_copyleft", "unknown")}
    return {"ecosystems": ecos, "packages": packages, "flags": flags, "tool_used": tools, "notes": notes}


def selftest():
    cases = {"MIT": "permissive", "Apache-2.0": "permissive", "BSD-3-Clause": "permissive",
             "GPL-3.0-only": "strong_copyleft", "AGPL-3.0": "strong_copyleft", "SSPL-1.0": "strong_copyleft",
             "LGPL-2.1-or-later": "weak_copyleft", "MPL-2.0": "weak_copyleft", "GPL-2.0 OR MIT": "permissive",
             "MIT AND GPL-3.0": "strong_copyleft", "UNKNOWN": "unknown", "": "unknown", "GPLv3": "strong_copyleft", "LGPLv3+": "weak_copyleft",
             "GNU Lesser General Public License v3 (LGPLv3)": "weak_copyleft"}
    fails = [(k, v, classify(k)) for k, v in cases.items() if classify(k) != v]
    for f in fails:
        print("FAIL: %r expected %s got %s" % f)
    print("selftest", "FAILED" if fails else "ok", f"({len(cases)} cases)")
    return 1 if fails else 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1 or not os.path.isdir(args[0]):
        print(__doc__)
        return 2
    rep = scan(os.path.abspath(args[0]))
    if "--json" in argv:
        print(json.dumps(rep, indent=2))
        return 0
    print("ecosystems:", ", ".join(f"{e} [{rep['tool_used'][e]}]" for e in rep["ecosystems"]) or "none detected")
    counts = {}
    for p in rep["packages"]:
        counts[p["class"]] = counts.get(p["class"], 0) + 1
    print("packages:", len(rep["packages"]), counts)
    for c in ("strong_copyleft", "weak_copyleft"):
        for item in rep["flags"][c]:
            print(f"  {c}: {item}")
    print("unknown:", len(rep["flags"]["unknown"]))
    for n in rep["notes"]:
        print("note:", n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
