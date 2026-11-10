#!/usr/bin/env python3
"""Extract finding cards from a published compliance-audit report HTML.

Usage: parse_cards.py <report.html>   -> JSON list of cards on stdout
       parse_cards.py --selftest

Mirrors the report's own script: cards are `.f` divs numbered #1.. in page
order, and `sid` is the title slug the page uses as the db key for
`status/<sid>` and `answers/<sid>--<question index>`.
"""
import json
import re
import sys
from html.parser import HTMLParser

SEV = {"b": "Blocker", "r": "Required", "c": "Recommended"}


def slug(title):
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", title.lower()))[:60]


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


class Cards(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards, self.card, self.depth = [], None, 0
        self.field, self.buf, self.in_k, self.k = None, [], False, ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if self.card is None:
            if tag == "div" and "f" in cls:
                sev = next((SEV[c] for c in cls if c in SEV), "")
                self.card = {"severity": sev, "risk": int(a.get("data-risk") or 0),
                             "title": "", "sections": {}, "questions": []}
                self.depth = 1
            return
        if tag == "div":
            self.depth += 1
        if tag == "h3":
            self.field, self.buf = "title", []
        elif tag == "li" and self.field == "pq":
            self.buf = []
        elif tag == "ol" and "pq" in cls:
            self.field = "pq"
        elif (tag == "p" or (tag == "div" and "says" in cls)) and self.field is None:
            self.field, self.buf, self.k = "sec", [], ""
        elif tag == "span" and "k" in cls and self.field == "sec":
            self.in_k = True

    def handle_endtag(self, tag):
        if self.card is None:
            return
        if self.in_k and tag == "span":
            self.in_k = False
            return
        if tag == "h3" and self.field == "title":
            self.card["title"] = re.sub(r"^\d+\.\s*", "", clean("".join(self.buf)))
            self.field = None
        elif tag == "li" and self.field == "pq":
            self.card["questions"].append(clean("".join(self.buf)))
        elif tag == "ol" and self.field == "pq":
            self.field = None
        elif self.field == "sec" and (tag == "p" or (tag == "div" and self.depth == 2)):
            text = clean("".join(self.buf))
            m = re.match(r"(Rule|Owner):\s*(.*)", text)
            if self.k:
                self.card["sections"][self.k] = text
            elif m:
                self.card["sections"][m.group(1)] = m.group(2)
            self.field = None
        if tag == "div":
            self.depth -= 1
            if self.depth == 0:
                self.cards.append(self.card)
                self.card = None

    def handle_data(self, data):
        if self.card is None:
            return
        if self.in_k:
            self.k += data.strip()
        elif self.field:
            self.buf.append(data)


def parse(html):
    p = Cards()
    p.feed(html)
    for i, c in enumerate(p.cards, 1):
        c["id"] = i
        c["sid"] = slug(c["title"])
    return p.cards


def selftest():
    html = """<main><div class="f b" data-risk="9"><span class="tag">Blocker</span><h3>Deleting an account never erases data</h3>
<p class="meta">Rule: <a href="x">GDPR Art. 17</a></p>
<div class="says"><span class="k">What the rule says</span>Users can ask for <b>erasure</b>.</div>
<p><span class="k">What to do</span>Hard-delete rows.</p>
<p class="meta">Owner: engineer</p>
<ol class="pq" hidden><li>Keep invoices?</li><li>Grace period?</li></ol></div>
<div class="f c" data-risk="2"><span class="tag">Recommended</span><h3>Add security.txt</h3></div></main>"""
    cs = parse(html)
    assert len(cs) == 2, cs
    a = cs[0]
    assert a["id"] == 1 and a["severity"] == "Blocker" and a["risk"] == 9, a
    assert a["sid"] == "deleting-an-account-never-erases-data", a
    assert a["sections"]["What the rule says"] == "Users can ask for erasure.", a
    assert a["sections"]["Rule"] == "GDPR Art. 17" and a["sections"]["What to do"] == "Hard-delete rows.", a
    assert a["sections"]["Owner"] == "engineer", a
    assert a["questions"] == ["Keep invoices?", "Grace period?"], a
    assert cs[1]["id"] == 2 and cs[1]["questions"] == [], cs[1]
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    elif len(sys.argv) == 2:
        with open(sys.argv[1], encoding="utf-8") as f:
            json.dump(parse(f.read()), sys.stdout, indent=1)
    else:
        sys.exit(__doc__)
