#!/usr/bin/env python3
"""
Parse video/script.md into video/beats.json.

Usage:  python3 parse_script.py [video_dir]

Script format (see assets/script-template.md):

    # Launch video — My App
    Voice: Rachel
    Format: vertical          (vertical = 9:16, landscape = 16:9)
    Language: en
    Base URL: http://localhost:8000     (web apps only)
    Background: #0B1220, #182447, #6E8CFF   (dark, darker, glow accent — from the app's own palette)

    ## 1. Intro (avatar)
    Spoken text...

    ## 2. Sign in (demo)
    Zoom: none                (none | top | center | bottom | x,y,w,h as fractions)
    Hold: 1.0                 (seconds to keep showing the screen after the voice ends)
    Spoken text...
"""
import json
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("video")
src_path = root / "script.md"
if not src_path.exists():
    sys.exit(f"ERROR: {src_path} not found")

src = src_path.read_text(encoding="utf-8")
meta = {"app_name": "", "voice": "", "format": "vertical", "base_url": "", "language": "en", "background": ""}
beats = []
cur = None
errors = []

for raw in src.splitlines():
    line = raw.strip()
    if cur is None:
        m = re.match(r"^#\s+Launch video\s*[—–-]+\s*(.+)$", line)
        if m:
            meta["app_name"] = m.group(1).strip()
            continue
        m = re.match(r"^(Voice|Format|Base URL|Language|Background)\s*:\s*(.+)$", line, re.I)
        if m:
            meta[m.group(1).lower().replace(" ", "_")] = m.group(2).strip()
            continue
    m = re.match(r"^##\s+(\d+)\.\s*(.+?)\s*\((avatar|demo)\)\s*$", line, re.I)
    if m:
        cur = {
            "n": int(m.group(1)),
            "title": m.group(2).strip(),
            "type": m.group(3).lower(),
            "text": [],
            "zoom": None,
            "hold": 1.0,
        }
        beats.append(cur)
        continue
    if line.startswith("## "):
        errors.append(f"Heading not understood (needs '## N. Title (avatar)' or '(demo)'): {line}")
        continue
    if cur is None or not line or line.startswith("<!--"):
        continue
    m = re.match(r"^Zoom\s*:\s*(.+)$", line, re.I)
    if m:
        v = m.group(1).strip().lower()
        cur["zoom"] = None if v in ("none", "no", "off") else v
        continue
    m = re.match(r"^Hold\s*:\s*([\d.]+)", line, re.I)
    if m:
        cur["hold"] = float(m.group(1))
        continue
    cur["text"].append(line)

for b in beats:
    b["text"] = " ".join(b["text"])
    b["id"] = f"beat-{b['n']:02d}"
    if not b["text"]:
        errors.append(f"{b['id']} ({b['title']}) has no spoken text")

if meta["format"] not in ("vertical", "landscape"):
    errors.append(f"Format must be 'vertical' or 'landscape', got '{meta['format']}'")
if meta["background"]:
    hexes = [c.strip() for c in meta["background"].split(",")]
    if len(hexes) != 3 or not all(re.fullmatch(r"#[0-9a-fA-F]{6}", h) for h in hexes):
        errors.append(f"Background must be 3 '#rrggbb' colors (dark, darker, glow accent), got '{meta['background']}'")
if not beats:
    errors.append("No beats found")

if errors:
    print("Problems in script.md:")
    for e in errors:
        print("  -", e)
    sys.exit(1)

(root / "beats.json").write_text(json.dumps({"meta": meta, "beats": beats}, indent=2, ensure_ascii=False))
words = sum(len(b["text"].split()) for b in beats)
print(f"Parsed {len(beats)} beats -> {root / 'beats.json'}   (~{words} words, ~{words / 2.5:.0f}s of speech)")
for b in beats:
    print(f"  {b['id']}  {b['type']:6}  {b['title']:<30} {len(b['text'].split()):>3} words")
