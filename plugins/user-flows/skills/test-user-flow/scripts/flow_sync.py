#!/usr/bin/env python3
"""Diff user-flows.md against the user-flow test suite.

Usage:
    python3 flow_sync.py <path-to-user-flows.md> <tests-dir>

Parses every flow entry (### UF-NNN: ...) from user-flows.md and hashes its
normalized content. Scans <tests-dir> for marker comments of the form

    user-flow: UF-001 hash: a1b2c3d4e5f6

(valid inside any comment syntax). Prints a JSON report to stdout:

    {
      "new":       [{id, name, area, hash, block}],   # flow exists, no test
      "updated":   [{id, name, area, hash, block, old_hash, file, line}],
      "deleted":   [{id, old_hash, file, line}],       # test exists, no flow
      "unchanged": [{id, file}],
      "conflicts": ["human-readable problem", ...]     # duplicate markers etc.
    }

Exit code 0 on success, 1 on unreadable input.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

FLOW_HEADING = re.compile(r"^### (UF-\d+):\s*(.*)$")
AREA_HEADING = re.compile(r"^## (?!#)(.*)$")
MARKER = re.compile(r"user-flow:\s*(UF-\d+)\s+hash:\s*([0-9a-f]{6,64})")
TEST_FILE_SUFFIXES = (".ts", ".tsx", ".js", ".mjs", ".cjs", ".py")


def flow_hash(block_lines):
    """Hash the normalized flow block: trailing whitespace stripped,
    blank lines dropped, joined with \\n. First 12 hex chars of sha256."""
    normalized = "\n".join(
        line.rstrip() for line in block_lines if line.strip()
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def parse_flows(md_path):
    flows = {}
    conflicts = []
    area = None
    current = None  # (id, name, area, [lines])

    def close(current):
        if current is None:
            return
        fid, name, farea, lines = current
        if fid in flows:
            conflicts.append(f"duplicate flow id {fid} in {md_path}")
        flows[fid] = {
            "id": fid,
            "name": name,
            "area": farea,
            "hash": flow_hash(lines),
            "block": "\n".join(lines).rstrip(),
        }

    for line in md_path.read_text(encoding="utf-8").splitlines():
        m = FLOW_HEADING.match(line)
        if m:
            close(current)
            current = (m.group(1), m.group(2).strip(), area, [line])
            continue
        m = AREA_HEADING.match(line)
        if m:
            close(current)
            current = None
            area = m.group(1).strip()
            continue
        if current is not None:
            current[3].append(line)
    close(current)
    return flows, conflicts


def scan_tests(tests_dir):
    markers = {}
    conflicts = []
    if not tests_dir.is_dir():
        return markers, conflicts
    for path in sorted(tests_dir.rglob("*")):
        if not path.is_file() or path.suffix not in TEST_FILE_SUFFIXES:
            continue
        if "node_modules" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            m = MARKER.search(line)
            if not m:
                continue
            fid, fhash = m.group(1), m.group(2)
            if fid in markers:
                prev = markers[fid]
                conflicts.append(
                    f"{fid} marked in both {prev['file']}:{prev['line']} "
                    f"and {path}:{lineno} — remove one before syncing"
                )
                continue
            markers[fid] = {"file": str(path), "line": lineno, "hash": fhash}
    return markers, conflicts


def main():
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 1
    md_path = Path(sys.argv[1])
    tests_dir = Path(sys.argv[2])
    if not md_path.is_file():
        print(f"error: {md_path} not found", file=sys.stderr)
        return 1

    flows, flow_conflicts = parse_flows(md_path)
    markers, marker_conflicts = scan_tests(tests_dir)

    report = {
        "new": [],
        "updated": [],
        "deleted": [],
        "unchanged": [],
        "conflicts": flow_conflicts + marker_conflicts,
    }

    for fid, flow in sorted(flows.items()):
        marker = markers.get(fid)
        if marker is None:
            report["new"].append(flow)
        elif marker["hash"] != flow["hash"]:
            report["updated"].append(
                {**flow, "old_hash": marker["hash"],
                 "file": marker["file"], "line": marker["line"]}
            )
        else:
            report["unchanged"].append({"id": fid, "file": marker["file"]})

    for fid, marker in sorted(markers.items()):
        if fid not in flows:
            report["deleted"].append(
                {"id": fid, "old_hash": marker["hash"],
                 "file": marker["file"], "line": marker["line"]}
            )

    json.dump(report, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
