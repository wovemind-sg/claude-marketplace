#!/usr/bin/env bash
# Record the whole demo as one continuous take.
#
# Usage:  scripts/record_app.sh [video_dir]
#   e.g.  scripts/record_app.sh
#
# Runs every demo beat's video/flows/<beat-id>.yaml with Maestro back-to-back
# while a single `adb shell screenrecord` captures the whole session — so beat 2
# starts exactly where beat 1 left off, and a splash screen only really appears
# once. The status bar is switched to Android "demo mode" (full battery, clean
# clock, no notification icons) so recordings look tidy.
#
# Does NOT split the take into beat clips — run review.py next to have the
# client mark trims/notes on the full take, then split_beats.py once approved.
#
# Output: video/recordings/full.mp4, video/marks.json (each beat's start time).
set -euo pipefail

ROOT="${1:-video}"
HOLD="${HOLD:-1.5}"          # seconds to keep recording after the last beat finishes

command -v adb >/dev/null || { echo "ERROR: adb not found (run the launch-video-setup skill)"; exit 1; }
command -v maestro >/dev/null || { echo "ERROR: maestro not found (run the launch-video-setup skill)"; exit 1; }
[ -f "$ROOT/beats.json" ] || { echo "ERROR: $ROOT/beats.json not found — run parse_script.py first"; exit 1; }

BEATS=$(python3 -c "
import json
d = json.load(open('$ROOT/beats.json'))
print(' '.join(b['id'] for b in d['beats'] if b['type'] == 'demo'))
")
[ -n "$BEATS" ] || { echo "ERROR: no demo beats in $ROOT/beats.json"; exit 1; }
for BEAT in $BEATS; do
  [ -f "$ROOT/flows/$BEAT.yaml" ] || { echo "ERROR: flow file $ROOT/flows/$BEAT.yaml does not exist"; exit 1; }
done

DEVICES=$(adb devices | awk 'NR>1 && $2=="device"{print $1}')
if [ -z "$DEVICES" ]; then
  echo "ERROR: no Android device or emulator is connected."
  echo "Start the emulator first, e.g.:  emulator -avd launch-video &"
  exit 1
fi
if [ "$(echo "$DEVICES" | wc -l)" -gt 1 ] && [ -z "${ANDROID_SERIAL:-}" ]; then
  echo "ERROR: several devices connected. Set ANDROID_SERIAL=<id> to pick one:"; adb devices; exit 1
fi

mkdir -p "$ROOT/recordings"

# Clean status bar (demo mode). Harmless if unsupported.
adb shell settings put global sysui_demo_allowed 1 >/dev/null 2>&1 || true
adb shell am broadcast -a com.android.systemui.demo -e command enter >/dev/null 2>&1 || true
adb shell am broadcast -a com.android.systemui.demo -e command clock -e hhmm 0900 >/dev/null 2>&1 || true
adb shell am broadcast -a com.android.systemui.demo -e command battery -e level 100 -e plugged false >/dev/null 2>&1 || true
adb shell am broadcast -a com.android.systemui.demo -e command network -e wifi show -e level 4 >/dev/null 2>&1 || true
adb shell am broadcast -a com.android.systemui.demo -e command notifications -e visible false >/dev/null 2>&1 || true

REMOTE="/sdcard/launch-video-full.mp4"
adb shell rm -f "$REMOTE" >/dev/null 2>&1 || true

echo "Recording the whole take ($BEATS) ..."
# screenrecord has a 3 minute cap by default; --time-limit raises to the maximum allowed.
adb shell screenrecord --bit-rate 12000000 --time-limit 180 "$REMOTE" &
REC_PID=$!
sleep 1.5
# `date +%s.%N` doesn't work on macOS (BSD date has no %N) — python3 is already required.
now_s() { python3 -c 'import time; print(time.time())'; }
T0=$(now_s)

MARKS_FILE="$ROOT/recordings/marks.txt"
: > "$MARKS_FILE"
STATUS=0
for BEAT in $BEATS; do
  NOW=$(now_s)
  awk -v t0="$T0" -v now="$NOW" -v beat="$BEAT" 'BEGIN{printf "%s %.3f\n", beat, now-t0}' >> "$MARKS_FILE"
  set +e
  maestro test "$ROOT/flows/$BEAT.yaml"
  if [ $? -ne 0 ]; then
    echo "WARNING: $BEAT's flow reported an error — the take continues anyway."
    STATUS=1
  fi
  set -e
done

sleep "$HOLD"
# SIGINT makes screenrecord finish the file cleanly.
adb shell pkill -INT screenrecord >/dev/null 2>&1 || adb shell killall -INT screenrecord >/dev/null 2>&1 || true
wait $REC_PID 2>/dev/null || true
sleep 1.5

adb shell am broadcast -a com.android.systemui.demo -e command exit >/dev/null 2>&1 || true

FULL="$ROOT/recordings/full.mp4"
adb pull "$REMOTE" "$FULL" >/dev/null
adb shell rm -f "$REMOTE" >/dev/null 2>&1 || true

python3 - "$FULL" "$MARKS_FILE" "$ROOT/marks.json" <<'PYEOF'
import json
import pathlib
import subprocess
import sys

full, marks_file, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
marks = [line.split() for line in pathlib.Path(marks_file).read_text().splitlines() if line.strip()]
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", full], capture_output=True, text=True).stdout.strip())
pathlib.Path(out_path).write_text(json.dumps(
    {"full_duration": dur, "marks": {beat: float(t) for beat, t in marks}}, indent=2))
PYEOF

if [ $STATUS -ne 0 ]; then
  echo "WARNING: one or more flows reported an error (see above) — check the take before trusting it."
fi
echo "Saved $ROOT/recordings/full.mp4 and $ROOT/marks.json"
exit $STATUS
