#!/usr/bin/env python3
"""Fast change check for Anthropic's model guide.

Fetches the guide, reduces it to visible text, hashes it and compares the hash
with the lock file next to the stored copy (pick-model/references/guide.lock.json).

  guide_hash.py                 print {status, sha256, text_file}; status is
                                "unchanged" or "changed"
  guide_hash.py --write-hash    save the live hash and today's date to the lock
  guide_hash.py --selftest      run the built-in tests

Exit codes: 0 ok, 2 the guide could not be fetched (JSON has "error").
"""
import argparse, hashlib, json, re, sys, tempfile, urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

URL = "https://claude.dev/blog/which-claude-model-should-you-build-with/"
LOCK = Path(__file__).resolve().parents[2] / "pick-model/references/guide.lock.json"
SKIP = {"script", "style", "nav", "header", "footer", "noscript", "svg", "head"}
BREAK = {"p", "h1", "h2", "h3", "h4", "li", "br", "div", "tr", "table"}
# Everything from here on is the site's related-posts feed, which changes weekly.
CUT = "Related posts"


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth, self.out = 0, []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.depth += 1
        if tag in BREAK:
            self.out.append("\n")
        if tag in ("td", "th"):
            self.out.append(" | ")

    def handle_endtag(self, tag):
        if tag in SKIP and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth:
            self.out.append(data)


def extract(html: str) -> str:
    """Visible page text, one item per line, whitespace-collapsed."""
    p = _Text()
    p.feed(html)
    text = "".join(p.out).split(CUT)[0]
    lines = (re.sub(r"[ \t\xa0]+", " ", ln).strip() for ln in text.splitlines())
    return "\n".join(ln for ln in lines if ln)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "model-picker-check-guide"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def old_hash(lock: Path):
    """Stored hash, or None when the lock is missing or corrupt (reads as "changed")."""
    try:
        return json.loads(lock.read_text()).get("sha256")
    except (OSError, ValueError, AttributeError):
        return None


def selftest() -> None:
    a = "<html><head><title>x</title></head><body><nav>menu</nav><h1>T</h1><p>a  b</p><script>var x=1</script><table><tr><td>m</td><td>n</td></tr></table><footer>f</footer>Related posts<p>feed</p></body></html>"
    b = a.replace("a  b", "a b").replace("menu", "other menu").replace("feed", "other feed")
    assert extract(a) == "T\na b\n| m | n", repr(extract(a))
    assert digest(extract(a)) == digest(extract(b)), "nav/feed/whitespace must not change the hash"
    assert digest(extract(a)) != digest(extract(a.replace("a  b", "a c"))), "content change must change the hash"
    with tempfile.TemporaryDirectory() as d:
        lock = Path(d) / "l.json"
        assert old_hash(lock) is None, "missing lock"
        lock.write_text("{bad")
        assert old_hash(lock) is None, "corrupt lock"
        lock.write_text("[]")
        assert old_hash(lock) is None, "non-object lock"
        lock.write_text('{"sha256": "x"}')
        assert old_hash(lock) == "x"
    print("selftest ok")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lock", type=Path, default=LOCK)
    ap.add_argument("--url", default=URL)
    ap.add_argument("--write-hash", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    try:
        text = extract(fetch(a.url))
    except Exception as e:  # network, DNS, HTTP
        print(json.dumps({"status": "error", "error": str(e)}))
        return 2
    if len(text) < 2000:
        print(json.dumps({"status": "error", "error": "page text too short, layout may have changed"}))
        return 2
    sha = digest(text)
    if a.write_hash:
        a.lock.write_text(json.dumps({"url": a.url, "sha256": sha, "checked": date.today().isoformat()}, indent=2) + "\n")
        print(json.dumps({"status": "written", "sha256": sha}))
        return 0
    old = old_hash(a.lock)
    f = tempfile.NamedTemporaryFile("w", suffix=".txt", prefix="model-guide-", delete=False)
    f.write(text)
    f.close()
    print(json.dumps({"status": "unchanged" if sha == old else "changed", "sha256": sha, "text_file": f.name}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
