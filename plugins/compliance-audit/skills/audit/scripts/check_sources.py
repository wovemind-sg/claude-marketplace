#!/usr/bin/env python3
"""Maintainer tool: check every source URL in the reference modules still resolves.

Usage: check_sources.py [references_dir]   (default: ../references next to this script)
Parses `last-reviewed:` and the `sources:` bullet list of every *.md, HEADs each URL (GET fallback),
prints `status  last-modified  url`, then lists 4xx and cross-host redirects. Exit 1 on any 4xx.
"""
import glob
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compliance-audit check_sources)"}


def fetch(url):
    for method in ("HEAD", "GET"):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method=method, headers=UA), timeout=10) as r:
                return r.status, r.headers.get("Last-Modified", "-"), r.geturl()
        except urllib.error.HTTPError as e:
            if method == "GET":
                return e.code, "-", url
        except Exception as e:  # DNS, timeout, TLS: report, do not crash the sweep
            if method == "GET":
                return f"ERR {type(e).__name__}", "-", url
    return "ERR", "-", url


def parse(path):
    text = open(path, encoding="utf-8").read()
    reviewed = (re.search(r"^last-reviewed:\s*(\S+)", text, re.M) or [None, "?"])[1]
    block = re.search(r"^sources:\s*\n((?:\s*-\s*\S.*\n?)+)", text, re.M)
    urls = re.findall(r"https?://\S+", block.group(1)) if block else []
    return reviewed, [u.rstrip(").,>") for u in urls]


def main(argv):
    ref = argv[0] if argv else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references")
    bad, moved = [], []
    for path in sorted(glob.glob(os.path.join(ref, "*.md"))):
        reviewed, urls = parse(path)
        print(f"== {os.path.basename(path)}  last-reviewed {reviewed}  ({len(urls)} sources)")
        for url in urls:
            status, lm, final = fetch(url)
            print(f"{status}  {lm}  {url}")
            if isinstance(status, int) and 400 <= status < 500:
                bad.append(url)
            if urllib.parse.urlparse(final).netloc != urllib.parse.urlparse(url).netloc:
                moved.append(f"{url} -> {final}")
    print(f"\n4xx: {len(bad)}", *bad, sep="\n  ")
    print(f"cross-host redirects: {len(moved)}", *moved, sep="\n  ")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
