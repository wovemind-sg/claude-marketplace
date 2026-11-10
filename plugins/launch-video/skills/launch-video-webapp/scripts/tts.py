#!/usr/bin/env python3
"""
Generate voice-over audio for every beat with ElevenLabs, including word timings
(used later for caption placement).

Usage:  python3 tts.py [video_dir] [--force] [--only beat-02]

Needs ELEVENLABS_API_KEY in the environment or in ~/.launch-video/env
(a plain text file with a line like  ELEVENLABS_API_KEY=sk_...).

Outputs, per beat:
    video/voice/beat-NN.mp3    the audio
    video/voice/beat-NN.json   character-level timings from ElevenLabs
For avatar beats, also writes video/avatar/PASTE-beat-NN.txt with the text to paste
into the avatar tool (in case the user prefers typing the script instead of uploading audio).
"""
import base64
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

args = [a for a in sys.argv[1:] if not a.startswith("--")]
root = pathlib.Path(args[0]) if args else pathlib.Path("video")
force = "--force" in sys.argv
only = None
if "--only" in sys.argv:
    only = sys.argv[sys.argv.index("--only") + 1]


def load_key():
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key:
        return key.strip()
    env_file = pathlib.Path.home() / ".launch-video" / "env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip().startswith("ELEVENLABS_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


API_KEY = load_key()
if not API_KEY:
    sys.exit(
        "ERROR: no ElevenLabs API key. Put it in ~/.launch-video/env as\n"
        "  ELEVENLABS_API_KEY=your_key_here\n(the launch-video-setup skill walks through this)"
    )


def api(path, data=None):
    req = urllib.request.Request(
        "https://api.elevenlabs.io" + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"xi-api-key": API_KEY, "Content-Type": "application/json"},
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.exit(f"ERROR: ElevenLabs returned {e.code}: {body[:500]}")


beats_path = root / "beats.json"
if not beats_path.exists():
    sys.exit("ERROR: beats.json missing — run parse_script.py first")
data = json.loads(beats_path.read_text())
meta, beats = data["meta"], data["beats"]

# Resolve voice name -> id
voices = api("/v1/voices")["voices"]
wanted = (meta.get("voice") or "").strip()
voice = None
for v in voices:
    if wanted and (v["voice_id"] == wanted or v["name"].lower() == wanted.lower()):
        voice = v
        break
if voice is None:
    if wanted:
        print(f"WARNING: voice '{wanted}' not found in your account. Available voices:")
    else:
        print("No 'Voice:' set in script.md. Available voices:")
    for v in voices:
        labels = v.get("labels") or {}
        print(f"  - {v['name']:<20} {labels.get('gender', ''):<8} {labels.get('accent', '')}")
    sys.exit(1)
print(f"Using voice: {voice['name']}")

(root / "voice").mkdir(parents=True, exist_ok=True)
(root / "avatar").mkdir(parents=True, exist_ok=True)

lang = (meta.get("language") or "en").lower()
model = "eleven_multilingual_v2"

for b in beats:
    if only and b["id"] != only:
        continue
    mp3 = root / "voice" / f"{b['id']}.mp3"
    js = root / "voice" / f"{b['id']}.json"
    if b["type"] == "avatar":
        (root / "avatar" / f"PASTE-{b['id']}.txt").write_text(b["text"] + "\n")
    if mp3.exists() and js.exists() and not force:
        print(f"  {b['id']}  already done (use --force to regenerate)")
        continue
    resp = api(
        f"/v1/text-to-speech/{voice['voice_id']}/with-timestamps",
        {
            "text": b["text"],
            "model_id": model,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.2},
        },
    )
    mp3.write_bytes(base64.b64decode(resp["audio_base64"]))
    js.write_text(json.dumps(resp.get("alignment") or {}, ensure_ascii=False))
    al = resp.get("alignment") or {}
    ends = al.get("character_end_times_seconds") or [0]
    print(f"  {b['id']}  {b['type']:6}  {ends[-1]:5.1f}s  -> {mp3}")

print("Done. Audio is in", root / "voice")
