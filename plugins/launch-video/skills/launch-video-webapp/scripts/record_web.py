#!/usr/bin/env python3
"""
Record the whole demo as one continuous take.

Usage:  python3 scripts/record_web.py [video_dir] [--url http://localhost:8000] [--desktop]

Every demo beat has its own flow at  video/flows/<beat-id>.py, each defining:

    def run(page, base_url):
        page.goto(base_url + "/login")
        pause(page, 1.2)          # unhurried pauses look natural in a demo
        page.click("text=Continue")
        pause(page, 2)

Flows run back-to-back in ONE browser page, in beat order from video/beats.json —
so beat 2 starts exactly where beat 1 left off, and a splash screen or login only
really happens once. `pause(page, seconds)` is injected for convenience. Keep
flows slow — a viewer must be able to follow each tap.

Does NOT split the take into beat clips — run review.py next to have the client
mark trims/notes on the full take, then split_beats.py once they mark it ready.

Output:
    video/recordings/full.mp4   the whole take
    video/marks.json            each beat's start time in the take, for split_beats.py
"""
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("ERROR: playwright not installed. Run:  python3 -m pip install playwright && python3 -m playwright install chromium")

argv = sys.argv[1:]
base_url = None
if "--url" in argv:
    i = argv.index("--url")
    base_url = argv[i + 1]
    del argv[i:i + 2]
desktop = "--desktop" in argv
if desktop:
    argv.remove("--desktop")
root = pathlib.Path(argv[0]) if argv else pathlib.Path("video")

meta_path = root / "beats.json"
if not meta_path.exists():
    sys.exit(f"ERROR: {meta_path} not found — run parse_script.py first")
data = json.loads(meta_path.read_text())
if not base_url:
    base_url = data["meta"].get("base_url")
if not base_url:
    sys.exit("ERROR: no base URL. Add 'Base URL: http://...' to script.md or pass --url")
base_url = base_url.rstrip("/")

beats = [b["id"] for b in data["beats"] if b["type"] == "demo"]
if not beats:
    sys.exit("ERROR: no demo beats in beats.json")
if not shutil.which("ffmpeg"):
    sys.exit("ERROR: ffmpeg not found (run the launch-video-setup skill)")


def pause(page, seconds):
    page.wait_for_timeout(int(seconds * 1000))


flows = {}
for beat in beats:
    flow_path = root / "flows" / f"{beat}.py"
    if not flow_path.exists():
        sys.exit(f"ERROR: flow file {flow_path} does not exist")
    spec = importlib.util.spec_from_file_location(f"flow_{beat}", flow_path)
    flow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(flow)
    if not hasattr(flow, "run"):
        sys.exit(f"ERROR: {flow_path} must define run(page, base_url)")
    flow.pause = pause
    flows[beat] = flow

(root / "recordings").mkdir(parents=True, exist_ok=True)
HOLD = 1.5
status = 0
marks = {}

with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
    # Playwright only scales recordings *down*, so to get a sharp 3x phone recording the
    # browser itself must render at 3x — hence --force-device-scale-factor.
    dsf = 1 if desktop else 3
    browser = p.chromium.launch(headless=True, args=[f"--force-device-scale-factor={dsf}"])
    if desktop:
        ctx_args = dict(viewport={"width": 1440, "height": 900}, device_scale_factor=1,
                        record_video_size={"width": 1440, "height": 900})
    else:
        ctx_args = dict(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True,
                        has_touch=True, record_video_size={"width": 1170, "height": 2532},
                        user_agent=("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
                                    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"))
    context = browser.new_context(record_video_dir=tmp, **ctx_args)
    page = context.new_page()
    print(f"Recording the whole take ({', '.join(beats)}) against {base_url} ...")
    t0 = time.time()
    for beat in beats:
        marks[beat] = time.time() - t0
        try:
            flows[beat].run(page, base_url)
        except Exception as e:  # keep going so later beats still get recorded
            print(f"WARNING: {beat}'s flow raised an error: {e}")
            status = 1
            try:
                page.screenshot(path=str(root / "recordings" / f"{beat}-error.png"))
                print(f"   screenshot of the failure: {root / 'recordings' / f'{beat}-error.png'}")
            except Exception:
                pass
    pause(page, HOLD)
    video = page.video
    context.close()
    webm = pathlib.Path(video.path())
    browser.close()
    full = root / "recordings" / "full.mp4"
    # Playwright's webm sometimes has a variable frame rate; normalise it.
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(webm), "-r", "30",
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-an", str(full)], check=True)

full_dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(full)], capture_output=True, text=True).stdout.strip())

(root / "marks.json").write_text(json.dumps({"full_duration": full_dur, "marks": marks}, indent=2))
print(f"Saved {full}  ({full_dur:.1f}s) and {root / 'marks.json'}")

sys.exit(status)
