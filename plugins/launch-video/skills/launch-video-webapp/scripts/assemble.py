#!/usr/bin/env python3
"""
Assemble the final launch video from:
    video/beats.json                 (from parse_script.py)
    video/voice/beat-NN.mp3 + .json  (from tts.py)
    video/recordings/beat-NN.mp4     (screen recordings, demo beats)
    video/avatar/beat-NN.mp4         (avatar clips, avatar beats)

Usage:
    python3 assemble.py [video_dir] [--no-captions] [--only beat-02] [--preview]

  --only beat-02   build just that one segment (video/work/seg-beat-02.mp4) for a quick look
  --preview        half resolution, fast encode, for checking timing
  --no-captions    skip burned-in captions

Output: video/out/launch.mp4
"""
import json
import pathlib
import shutil
import subprocess
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("ERROR: Pillow not installed. Run:  python3 -m pip install pillow")

args = [a for a in sys.argv[1:] if not a.startswith("--")]
root = pathlib.Path(args[0]) if args else pathlib.Path("video")
CAPTIONS = "--no-captions" not in sys.argv
PREVIEW = "--preview" in sys.argv
ONLY = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None

if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
    sys.exit("ERROR: ffmpeg/ffprobe not found on PATH (run the launch-video-setup skill)")

data = json.loads((root / "beats.json").read_text())
meta, beats = data["meta"], data["beats"]
if meta.get("format", "vertical") == "landscape":
    W, H = 1920, 1080
else:
    W, H = 1080, 1920
if PREVIEW:
    W, H = W // 2, H // 2
FPS = 30
XFADE = 0.4
CAPTION_ZONE = 0.16                               # bottom share of screen kept free for captions

# dark, darker, glow accent — used when script.md sets no Background of its own
DEFAULT_BG = ((13, 15, 26), (27, 22, 58), (110, 90, 220))


def parse_hex(h):
    h = h.strip().lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


bg_meta = (meta.get("background") or "").strip()
if bg_meta:
    try:
        BG_TOP, BG_BOTTOM, BG_GLOW = [parse_hex(c) for c in bg_meta.split(",")]
    except Exception:
        print(f"  WARNING: Background '{bg_meta}' not understood, using the default")
        BG_TOP, BG_BOTTOM, BG_GLOW = DEFAULT_BG
else:
    BG_TOP, BG_BOTTOM, BG_GLOW = DEFAULT_BG

work = root / "work"
out_dir = root / "out"
work.mkdir(exist_ok=True)
out_dir.mkdir(exist_ok=True)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(" ".join(map(str, cmd)))
        print(r.stderr[-3000:])
        sys.exit(f"ffmpeg failed while building {cmd[-1]}")


def probe(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        sys.exit(f"ffprobe failed on {path}: {r.stderr}")
    info = json.loads(r.stdout)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"].get("duration") or 0)
    return {"w": int(v["width"]) if v else 0, "h": int(v["height"]) if v else 0, "dur": dur, "audio": a is not None}


# ---------------------------------------------------------------- captions (.ass)
def ass_time(t):
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def words_from_alignment(al, text):
    """ElevenLabs gives per-character times; regroup into (word, start, end)."""
    chars = al.get("characters") or []
    starts = al.get("character_start_times_seconds") or []
    ends = al.get("character_end_times_seconds") or []
    words, cur, cs = [], "", None
    for ch, s, e in zip(chars, starts, ends):
        if ch.isspace():
            if cur:
                words.append((cur, cs, e))
                cur, cs = "", None
        else:
            if cs is None:
                cs = s
            cur += ch
            last_end = e
    if cur:
        words.append((cur, cs, last_end))
    return words


def words_estimated(text, duration):
    """No timings available: spread words proportionally to their length."""
    toks = text.split()
    total = sum(len(t) + 1 for t in toks) or 1
    t, out = 0.0, []
    for tok in toks:
        d = duration * (len(tok) + 1) / total
        out.append((tok, t, t + d))
        t += d
    return out


def chunk_words(words, max_chars=28, max_words=5):
    lines, cur = [], []
    for w in words:
        trial = " ".join(x[0] for x in cur + [w])
        if cur and (len(trial) > max_chars or len(cur) >= max_words):
            lines.append(cur)
            cur = []
        cur.append(w)
        if w[0][-1] in ".!?":
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    return [(" ".join(x[0] for x in ln), ln[0][1], ln[-1][2]) for ln in lines]


def write_ass(path, cues, font_size):
    margin_v = int(H * 0.05)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Arial,{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{max(2, font_size // 14)},{max(1, font_size // 20)},2,{int(W*0.06)},{int(W*0.06)},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for text, s, e in cues:
        e = max(e, s + 0.3)
        lines.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{text}\n")
    path.write_text("".join(lines), encoding="utf-8")


def captions_for(beat, duration):
    js = root / "voice" / f"{beat['id']}.json"
    words = []
    if js.exists():
        try:
            words = words_from_alignment(json.loads(js.read_text()), beat["text"])
        except Exception:
            words = []
    if not words:
        words = words_estimated(beat["text"], duration)
    return chunk_words(words)


# ---------------------------------------------------------------- phone frame
def phone_geometry(rec_w, rec_h):
    """Where the phone screen sits on the canvas."""
    avail_h = H * (1 - CAPTION_ZONE) - H * 0.05
    sh = int(avail_h)
    sw = int(sh * rec_w / rec_h)
    max_w = int(W * 0.86)
    if sw > max_w:
        sw = max_w
        sh = int(sw * rec_h / rec_w)
    sw -= sw % 2
    sh -= sh % 2
    x = (W - sw) // 2
    y = int(H * 0.05) + (int(avail_h) - sh) // 2
    return sw, sh, x, y


def make_background_and_mask(sw, sh, x, y, bezel):
    from PIL import ImageFilter
    tag = f"{sw}x{sh}_{x}_{y}_{BG_TOP}{BG_BOTTOM}{BG_GLOW}".replace(" ", "")
    bg_path = work / f"bg_{abs(hash(tag))}.png"
    mask_path = work / f"mask_{sw}x{sh}.png"
    r = int(sw * 0.11)
    if not bg_path.exists():
        # diagonal gradient (top-left -> bottom-right) reads less flat than a straight
        # vertical one at this size
        img = Image.new("RGB", (W, H))
        px = img.load()
        for yy in range(H):
            ty = yy / (H - 1)
            for xx in range(W):
                t = (xx / (W - 1) + ty) / 2
                px[xx, yy] = tuple(int(BG_TOP[i] * (1 - t) + BG_BOTTOM[i] * t) for i in range(3))
        img = img.convert("RGBA")

        # soft glow behind the phone, tinted with the app's own accent color
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gw, gh = int(sw * 1.6), int(sh * 1.3)
        gx, gy = x + sw // 2 - gw // 2, y + sh // 2 - gh // 2
        ImageDraw.Draw(glow).ellipse((gx, gy, gx + gw, gy + gh), fill=(*BG_GLOW, 100))
        glow = glow.filter(ImageFilter.GaussianBlur(int(sw * 0.18)))
        img = Image.alpha_composite(img, glow)

        # drop shadow under the phone
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            (x - bezel, y - bezel + 18, x + sw + bezel, y + sh + bezel + 18), r + bezel, fill=(0, 0, 0, 130))
        shadow = shadow.filter(ImageFilter.GaussianBlur(28))
        img = Image.alpha_composite(img, shadow)

        # vignette: keep the corners quieter than the center so the phone stays the focus
        vignette = Image.new("L", (W, H), 0)
        ImageDraw.Draw(vignette).ellipse((-W * 0.3, -H * 0.2, W * 1.3, H * 1.2), fill=255)
        vignette = vignette.filter(ImageFilter.GaussianBlur(int(W * 0.25)))
        darkened = Image.alpha_composite(img, Image.new("RGBA", (W, H), (0, 0, 0, 140)))
        img = Image.composite(img, darkened, vignette).convert("RGB")

        d = ImageDraw.Draw(img)
        d.rounded_rectangle((x - bezel, y - bezel, x + sw + bezel, y + sh + bezel), r + bezel, fill=(12, 12, 16))
        d.rounded_rectangle((x, y, x + sw, y + sh), r, fill=(0, 0, 0))
        img.save(bg_path)
    if not mask_path.exists():
        m = Image.new("L", (sw, sh), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, sw - 1, sh - 1), r, fill=255)
        m.save(mask_path)
    return bg_path, mask_path


def zoom_filter(zoom, sw, sh):
    """Return an ffmpeg crop expression for a zoom preset or 'x,y,w,h' fractions."""
    # Presets magnify 1.5x while keeping the screen's aspect ratio, anchored top/center/bottom.
    # That 1.5x means every preset crops (1 - 1/1.5) ~= 17% off each edge: top/center/bottom
    # only move the vertical window, the horizontal crop is always centered — so a preset
    # always slices off full-width content (a header, a bottom bar) regardless of which one
    # is picked. There's no preset that avoids this on an edge-to-edge screen; use "none".
    z = 1 / 1.5
    presets = {"top": ((1 - z) / 2, 0, z, z), "center": ((1 - z) / 2, (1 - z) / 2, z, z),
               "bottom": ((1 - z) / 2, 1 - z, z, z)}
    if zoom in presets:
        fx, fy, fw, fh = presets[zoom]
    else:
        try:
            fx, fy, fw, fh = [float(v) for v in zoom.split(",")]
        except Exception:
            print(f"  WARNING: zoom '{zoom}' not understood, ignoring")
            return ""
    return f"crop=iw*{fw}:ih*{fh}:iw*{fx}:ih*{fy},"


# ---------------------------------------------------------------- segments
def enc_args():
    if PREVIEW:
        return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p"]


AUDIO = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]


def build_avatar(beat):
    src = root / "avatar" / f"{beat['id']}.mp4"
    if not src.exists():
        sys.exit(f"MISSING: {src}  (the avatar clip for '{beat['title']}')")
    info = probe(src)
    if not info["audio"]:
        sys.exit(f"{src} has no audio track — re-download it from the avatar tool with sound")
    seg = work / f"seg-{beat['id']}.mp4"
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x121422,fps={FPS},format=yuv420p")
    if CAPTIONS:
        ass = work / f"{beat['id']}.ass"
        write_ass(ass, captions_for(beat, info["dur"]), font_size=int(H * 0.030))
        vf += f",subtitles='{ass.as_posix()}'"
    run(["ffmpeg", "-y", "-i", str(src), "-vf", vf, "-af", "aresample=48000", *enc_args(), *AUDIO, str(seg)])
    return seg, probe(seg)["dur"]


def build_demo(beat):
    rec = root / "recordings" / f"{beat['id']}.mp4"
    voice = root / "voice" / f"{beat['id']}.mp3"
    if not rec.exists():
        sys.exit(f"MISSING: {rec}  (the screen recording for '{beat['title']}')")
    if not voice.exists():
        sys.exit(f"MISSING: {voice}  (the voice-over for '{beat['title']}' — run tts.py)")
    ri, ai = probe(rec), probe(voice)
    target = max(ri["dur"], ai["dur"] + beat.get("hold", 1.0))
    sw, sh, x, y = phone_geometry(ri["w"], ri["h"])
    bezel = max(6, int(sw * 0.02))
    bg, mask = make_background_and_mask(sw, sh, x, y, bezel)
    zoom = zoom_filter(beat["zoom"], sw, sh) if beat.get("zoom") else ""
    if zoom:
        scale = f"scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh}"
    else:
        scale = f"scale={sw}:{sh}"
    pad = max(0.0, target - ri["dur"])
    fc = (
        f"[1:v]{zoom}{scale},fps={FPS},tpad=stop_mode=clone:stop_duration={pad:.3f}[rec];"
        f"[2:v]format=gray[m];[rec][m]alphamerge[recm];"
        f"[0:v][recm]overlay={x}:{y}:shortest=1,format=yuv420p[v0];"
        f"[3:a]apad=whole_dur={target:.3f}[a]"
    )
    if CAPTIONS:
        ass = work / f"{beat['id']}.ass"
        write_ass(ass, captions_for(beat, ai["dur"]), font_size=int(H * 0.030))
        fc = fc.replace("[v0];", f"[v1];[v1]subtitles='{ass.as_posix()}'[v0];")
    seg = work / f"seg-{beat['id']}.mp4"
    run([
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(FPS), "-i", str(bg),
        "-i", str(rec),
        "-loop", "1", "-framerate", str(FPS), "-i", str(mask),
        "-i", str(voice),
        "-filter_complex", fc, "-map", "[v0]", "-map", "[a]",
        "-t", f"{target:.3f}", *enc_args(), *AUDIO, str(seg),
    ])
    return seg, probe(seg)["dur"]


segments = []
for b in beats:
    if ONLY and b["id"] != ONLY:
        continue
    print(f"Building {b['id']} ({b['type']}: {b['title']}) ...")
    seg, dur = build_avatar(b) if b["type"] == "avatar" else build_demo(b)
    segments.append((seg, dur))
    print(f"   -> {seg.name}  {dur:.1f}s")

if ONLY:
    print(f"\nSegment ready: {segments[0][0]}")
    sys.exit(0)

# ---------------------------------------------------------------- concatenate with crossfades
final = out_dir / ("launch-preview.mp4" if PREVIEW else "launch.mp4")
if len(segments) == 1:
    shutil.copy(segments[0][0], final)
else:
    inputs = []
    for seg, _ in segments:
        inputs += ["-i", str(seg)]
    fc, offset, vprev, aprev = [], 0.0, "[0:v]", "[0:a]"
    for i in range(1, len(segments)):
        offset += segments[i - 1][1] - XFADE
        vout = f"[v{i}]" if i < len(segments) - 1 else "[vout]"
        aout = f"[a{i}]" if i < len(segments) - 1 else "[aout]"
        fc.append(f"{vprev}[{i}:v]xfade=transition=fade:duration={XFADE}:offset={offset:.3f}{vout}")
        fc.append(f"{aprev}[{i}:a]acrossfade=d={XFADE}{aout}")
        vprev, aprev = vout, aout
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
         *enc_args(), "-movflags", "+faststart", *AUDIO, str(final)])

total = probe(final)["dur"]
print(f"\nDONE  {final}   ({total:.1f}s, {W}x{H})")
