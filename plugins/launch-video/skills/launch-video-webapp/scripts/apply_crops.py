#!/usr/bin/env python3
"""
Cut marked windows out of video/recordings/full.mp4 directly, for review.py
trims that don't map to a shortenable pause() in any flow (real page-load,
animation, or network latency that no flow edit can change). Safe to run here
since this happens before voice-over or captions exist — nothing downstream to
fall out of sync.

Usage:  python3 scripts/apply_crops.py [video_dir] [--crops '[{"start":1.2,"end":3.4}]']

Without --crops, reads the crop list from video/review.json. Overwrites
video/recordings/full.mp4 with those windows removed, and shifts
video/marks.json's start times to match, so split_beats.py (and a second run
of this script) stay correct afterward.
"""
import json
import pathlib
import subprocess
import sys

argv = sys.argv[1:]
crops_arg = None
if "--crops" in argv:
    i = argv.index("--crops")
    crops_arg = json.loads(argv[i + 1])
    del argv[i:i + 2]
root = pathlib.Path(argv[0]) if argv else pathlib.Path("video")

full = root / "recordings" / "full.mp4"
marks_path = root / "marks.json"
if not full.exists():
    sys.exit(f"ERROR: {full} not found")
if not marks_path.exists():
    sys.exit(f"ERROR: {marks_path} not found — run the record step first")

if crops_arg is None:
    review_path = root / "review.json"
    if not review_path.exists():
        sys.exit(f"ERROR: no --crops given and {review_path} not found")
    crops_arg = json.loads(review_path.read_text()).get("crops", [])
crops = sorted(({"start": float(c["start"]), "end": float(c["end"])} for c in crops_arg),
               key=lambda c: c["start"])
if not crops:
    sys.exit("Nothing to do: no crops.")

marks_data = json.loads(marks_path.read_text())
full_dur = marks_data["full_duration"]

# The segments to KEEP are the gaps between crops.
keep = []
cursor = 0.0
for c in crops:
    if c["start"] > cursor:
        keep.append((cursor, c["start"]))
    cursor = max(cursor, c["end"])
if cursor < full_dur:
    keep.append((cursor, full_dur))
if not keep:
    sys.exit("ERROR: crops remove the entire take")

filt = []
for i, (s, e) in enumerate(keep):
    filt.append(f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[k{i}]")
filt.append("".join(f"[k{i}]" for i in range(len(keep))) + f"concat=n={len(keep)}:v=1:a=0[outv]")

tmp = root / "recordings" / "full.trimmed.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(full), "-filter_complex", ";".join(filt),
                "-map", "[outv]", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(tmp)], check=True)
tmp.replace(full)


def remap(t):
    """Shift a timestamp past earlier crops by however much was removed before it."""
    removed = 0.0
    for c in crops:
        if c["end"] <= t:
            removed += c["end"] - c["start"]
        elif c["start"] < t:
            removed += t - c["start"]
    return round(t - removed, 3)


marks_data["marks"] = {beat: remap(t) for beat, t in marks_data["marks"].items()}
marks_data["full_duration"] = remap(full_dur)
marks_path.write_text(json.dumps(marks_data, indent=2))

new_dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(full)], capture_output=True, text=True).stdout.strip()
removed_total = sum(c["end"] - c["start"] for c in crops)
print(f"Removed {len(crops)} window(s), {removed_total:.1f}s total.")
print(f"{full} is now {float(new_dur):.1f}s. Updated {marks_path}.")
