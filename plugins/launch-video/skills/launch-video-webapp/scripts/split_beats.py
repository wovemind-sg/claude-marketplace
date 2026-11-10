#!/usr/bin/env python3
"""
Split video/recordings/full.mp4 into per-beat clips.

Usage:  python3 scripts/split_beats.py [video_dir]

Run this after the review step (review.py) comes back "ready" — it uses
video/marks.json (written by record_web.py) to know where each beat starts.

Output: video/recordings/<beat-id>.mp4 per demo beat.
"""
import json
import pathlib
import subprocess
import sys

root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("video")
full = root / "recordings" / "full.mp4"
marks_path = root / "marks.json"
if not full.exists():
    sys.exit(f"ERROR: {full} not found — run record_web.py first")
if not marks_path.exists():
    sys.exit(f"ERROR: {marks_path} not found — run record_web.py first")

marks_data = json.loads(marks_path.read_text())
marks = marks_data["marks"]
full_dur = marks_data["full_duration"]
beats = list(marks.keys())

for i, beat in enumerate(beats):
    start = marks[beat]
    end = marks[beats[i + 1]] if i + 1 < len(beats) else full_dur
    out = root / "recordings" / f"{beat}.mp4"
    # -ss after -i (not before) so the cut lands on the exact frame, not the nearest keyframe.
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(full), "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(out)], check=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                         capture_output=True, text=True).stdout.strip()
    print(f"Saved {out}  ({float(dur or 0):.1f}s)")
