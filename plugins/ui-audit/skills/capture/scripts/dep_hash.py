#!/usr/bin/env python3
"""Find which audited screens are affected by changes between two commits.

Reads a ui-audit manifest (screens -> deps/hash/last_audited_sha, shared -> screens),
diffs --since..--head in --repo, and prints a JSON report on stdout.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile

UI_EXT = {".html", ".htm", ".css", ".scss", ".sass", ".less", ".js", ".jsx", ".ts", ".tsx",
          ".vue", ".svelte", ".jinja", ".j2", ".njk", ".erb", ".hbs", ".swift", ".kt", ".xml",
          ".dart", ".storyboard", ".xib", ".svg"}


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.decode().strip()}")
    return r


def dep_hash(repo, head, deps, missing=None):
    """sha256 over deps at head; paths absent at head are appended to `missing` when given."""
    h = hashlib.sha256()
    for p in sorted(deps):
        r = git(repo, "show", f"{head}:{p}", check=False)
        if r.returncode and missing is not None:
            missing.append(p)
        h.update(p.encode() + b"\0")
        h.update(r.stdout if r.returncode == 0 else b"<missing>")
        h.update(b"\0")
    return h.hexdigest()


def analyze(manifest, repo, since, head="HEAD"):
    screens = manifest.get("screens", {})
    shared = manifest.get("shared", {})
    changed = [f for f in git(repo, "diff", "--name-only", "--no-renames", f"{since}..{head}").stdout.decode().splitlines() if f]
    cset = set(changed)
    affected = sorted(n for n, s in screens.items() if cset & set(s.get("deps", [])))
    shared_changed = [{"file": f, "dependents": sorted(shared[f]), "needs_ripple_review": True}
                      for f in sorted(shared) if f in cset]
    known = set(shared) | {d for s in screens.values() for d in s.get("deps", [])}
    unmapped = sorted(f for f in changed
                      if f not in known and os.path.splitext(f)[1].lower() in UI_EXT)
    new_hashes, missing_deps = {}, {}
    for n, s in screens.items():
        miss = []
        new_hashes[n] = dep_hash(repo, head, s.get("deps", []), miss)
        if miss:
            missing_deps[n] = miss
    # a screen is deleted when all its own (non-shared) deps are missing; surviving shared css/js must not hide it
    def own(n):
        return [d for d in screens[n]["deps"] if d not in shared] or screens[n]["deps"]
    all_missing = sorted(n for n in missing_deps if all(d in missing_deps[n] for d in own(n)))
    return {"since": since, "head": head, "changed_files": changed, "affected_screens": affected,
            "shared_changed": shared_changed, "unmapped_changed_files": unmapped,
            "new_hashes": new_hashes, "missing_deps": missing_deps, "all_deps_missing": all_missing}


def selftest():
    with tempfile.TemporaryDirectory() as d:
        def run(*a):
            subprocess.run(["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@t", *a],
                           check=True, capture_output=True)

        def write(p, t):
            os.makedirs(os.path.dirname(os.path.join(d, p)) or d, exist_ok=True)
            open(os.path.join(d, p), "w").write(t)
        run("init", "-q")
        for p in ("a.html", "b.html", "style.css", "c.html", "x.txt"):
            write(p, p)
        run("add", "."); run("commit", "-qm", "c0")
        base = git(d, "rev-parse", "HEAD").stdout.decode().strip()
        m = {"screens": {"a": {"deps": ["a.html", "style.css"]}, "b": {"deps": ["b.html", "style.css"]}},
             "shared": {"style.css": ["a", "b"]}}
        h0 = analyze(m, d, base, base)["new_hashes"]
        write("a.html", "changed"); write("c.html", "new"); write("x.txt", "n")
        run("commit", "-qam", "c1")
        r = analyze(m, d, base)
        assert r["affected_screens"] == ["a"], r
        assert r["shared_changed"] == [], r
        assert r["unmapped_changed_files"] == ["c.html"], r
        assert r["new_hashes"]["a"] != h0["a"] and r["new_hashes"]["b"] == h0["b"]
        run("mv", "b.html", "b2.html"); run("commit", "-qam", "rename")
        assert "b.html" in analyze(m, d, base)["changed_files"]
        write("style.css", "x"); run("commit", "-qam", "c2")
        r = analyze(m, d, base)
        assert r["affected_screens"] == ["a", "b"], r
        assert r["shared_changed"] == [{"file": "style.css", "dependents": ["a", "b"], "needs_ripple_review": True}], r
        write("gone.html", "g"); run("add", "."); run("commit", "-qm", "g")
        m["screens"]["gone"] = {"deps": ["gone.html"]}
        m["screens"]["part"] = {"deps": ["a.html", "gone.html"]}
        run("rm", "-q", "gone.html"); run("commit", "-qm", "rm")
        r = analyze(m, d, base)
        assert r["missing_deps"] == {"gone": ["gone.html"], "part": ["gone.html"], "b": ["b.html"]}, r
        assert r["all_deps_missing"] == ["b", "gone"], r  # b: own page renamed away, shared css remains
        write("p.html", "p"); run("add", "."); run("commit", "-qm", "p")
        m["screens"]["pg"] = {"deps": ["p.html", "style.css"]}
        assert "pg" not in analyze(m, d, base)["all_deps_missing"]
        run("rm", "-q", "p.html"); run("commit", "-qm", "rmp")
        assert "pg" in analyze(m, d, base)["all_deps_missing"]
    print(json.dumps({"selftest": "ok"}))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest"); ap.add_argument("--repo", default=".")
    ap.add_argument("--since"); ap.add_argument("--head", default="HEAD")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.manifest and a.since):
        ap.error("--manifest and --since are required")
    try:
        with open(a.manifest) as f:
            m = json.load(f)
        print(json.dumps(analyze(m, a.repo, a.since, a.head), indent=2))
    except (RuntimeError, OSError, ValueError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
