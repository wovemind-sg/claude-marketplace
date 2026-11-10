#!/usr/bin/env python3
"""
Show the recorded take in a browser so the client can mark trims and leave
timestamped notes before the take is split into beats.

Usage:  python3 scripts/review.py [video_dir]

Opens a local page with video/recordings/full.mp4 on a timeline. The client:
  - drags on the trim lane to mark a window that runs too long, and/or
  - clicks the notes lane to leave a timestamped note for the agent,
  then clicks "Send for edits" (enabled once a trim or note exists) or
  "Mark ready" (enabled only while none do).

Blocks until they submit, then writes video/review.json:
    {"action": "edits"|"ready",
     "crops": [{"start": 3.2, "end": 5.1}, ...],
     "notes": [{"time": 7.0, "text": "..."}]}
and exits 0. Re-run after acting on the feedback to show the new take.
"""
import http.server
import json
import pathlib
import socket
import sys
import threading
import webbrowser

root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("video")
video_path = root / "recordings" / "full.mp4"
if not video_path.exists():
    sys.exit(f"ERROR: {video_path} not found — run the record step first")

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Review the take</title>
<style>
  :root {
    --bg: #0d0e11; --panel: #15171b; --panel-2: #1b1e24; --line: #282b32;
    --text: #e7e8ec; --dim: #8d919c; --trim: #e2a33d; --trim-dim: rgba(226,163,61,.20);
    --note: #5fa8ff; --note-dim: rgba(95,168,255,.20); --radius: 10px;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    padding: 28px 20px 96px;
  }
  .mono { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-variant-numeric: tabular-nums; }
  h1 { font-size: 17px; font-weight: 600; margin: 0 0 4px; }
  .sub { color: var(--dim); font-size: 13px; margin: 0 0 24px; max-width: 60ch; }
  .stage { display: flex; justify-content: center; margin-bottom: 22px; }
  video {
    max-width: min(90vw, 480px); max-height: 56vh; background: #000;
    border-radius: 14px; border: 1px solid var(--line);
    box-shadow: 0 12px 32px rgba(0,0,0,.45);
  }
  .timeline { max-width: 900px; margin: 0 auto; }
  .timelineToolbar { display: flex; align-items: center; justify-content: flex-end; gap: 8px; margin-bottom: 6px; }
  .zoombtn {
    width: 24px; height: 24px; border-radius: 6px; border: 1px solid var(--line); background: var(--panel-2);
    color: var(--text); font-size: 15px; line-height: 1; cursor: pointer;
  }
  .zoombtn:hover { background: var(--panel); }
  .zoombtn:disabled { opacity: .35; cursor: default; }
  .zoomLabel { color: var(--dim); font-size: 12px; width: 3em; text-align: center; }
  .timelineScroll { overflow-x: auto; overflow-y: hidden; border-radius: 8px; }
  .timelineInner { position: relative; min-width: 100%; }
  .ruler { position: relative; height: 22px; border-bottom: 1px solid var(--line); }
  .tick { position: absolute; bottom: 0; font-size: 11px; color: var(--dim); transform: translateX(-50%); }
  .tick::after {
    content: ""; position: absolute; bottom: -1px; left: 50%; width: 1px; height: 5px; background: var(--line);
  }
  .lane {
    position: relative; height: 46px; background: var(--panel);
    border: 1px solid var(--line); border-top: none; cursor: crosshair; overflow: hidden;
  }
  .lane-label {
    position: absolute; left: 8px; top: 50%; transform: translateY(-50%);
    font-size: 11px; color: var(--dim); pointer-events: none; z-index: 1;
  }
  #trimLane { border-radius: 0 0 0 0; }
  #noteLane { border-top: 1px solid var(--line); border-radius: 0 0 8px 8px; }
  .playhead {
    position: absolute; top: 0; bottom: 0; width: 1px; background: #fff; opacity: .65; pointer-events: none; z-index: 3;
  }
  .region {
    position: absolute; top: 4px; bottom: 4px; background: var(--trim-dim);
    border: 1px solid var(--trim); border-radius: 4px;
  }
  .region .x {
    position: absolute; top: -8px; right: -8px; width: 16px; height: 16px; border-radius: 50%;
    background: var(--trim); color: #16130a; font-size: 11px; line-height: 16px; text-align: center;
    cursor: pointer; opacity: 0; transition: opacity .1s;
  }
  .region:hover .x { opacity: 1; }
  .pin {
    position: absolute; top: 50%; width: 12px; height: 12px; margin-left: -6px; margin-top: -6px;
    background: var(--note); border-radius: 50% 50% 50% 0; transform: rotate(45deg); cursor: pointer;
  }
  .popover {
    position: absolute; z-index: 10; background: var(--panel-2); border: 1px solid var(--line);
    border-radius: 8px; padding: 10px; width: 240px; box-shadow: 0 10px 28px rgba(0,0,0,.5);
  }
  .popover textarea {
    width: 100%; min-height: 60px; resize: vertical; background: var(--bg); color: var(--text);
    border: 1px solid var(--line); border-radius: 6px; padding: 6px 8px; font: inherit; margin-bottom: 8px;
  }
  .popover .row { display: flex; justify-content: space-between; gap: 8px; }
  .lists { max-width: 900px; margin: 28px auto 0; display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
  .lists h2 { font-size: 12px; text-transform: none; color: var(--dim); font-weight: 600; margin: 0 0 8px; }
  .chip {
    display: flex; align-items: center; gap: 8px; background: var(--panel); border: 1px solid var(--line);
    border-radius: 7px; padding: 7px 10px; margin-bottom: 6px; font-size: 13px;
  }
  .chip .dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
  .chip.trim .dot { background: var(--trim); }
  .chip.note .dot { background: var(--note); }
  .chip .t { color: var(--dim); flex: none; }
  .chip .txt { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .chip button {
    flex: none; background: none; border: none; color: var(--dim); cursor: pointer; font-size: 15px; line-height: 1;
    padding: 2px 4px;
  }
  .chip button:hover { color: var(--text); }
  .empty { color: var(--dim); font-size: 13px; }
  footer {
    position: fixed; left: 0; right: 0; bottom: 0; background: var(--panel);
    border-top: 1px solid var(--line); padding: 14px 20px; display: flex; align-items: center;
    justify-content: center; gap: 12px;
  }
  footer .status { position: absolute; left: 20px; color: var(--dim); font-size: 13px; }
  button.action {
    font: inherit; font-weight: 600; font-size: 14px; padding: 10px 18px; border-radius: 8px;
    border: 1px solid var(--line); background: var(--panel-2); color: var(--text); cursor: pointer;
  }
  button.action:disabled { opacity: .35; cursor: default; }
  button.action.primary:not(:disabled) { background: var(--note); border-color: var(--note); color: #0a1626; }
  button.action.ready:not(:disabled) { background: #3fb87f; border-color: #3fb87f; color: #06170f; }
  .done { text-align: center; margin-top: 18vh; color: var(--dim); }
</style>
</head>
<body>
  <h1>Review the take</h1>
  <p class="sub">Drag on the amber lane to mark a part that runs too long. Click the blue lane to leave a
    timestamped note for the agent. Then send it back or mark it ready below.</p>

  <div class="stage"><video id="v" src="/video" controls></video></div>

  <div class="timeline">
    <div class="timelineToolbar">
      <button class="zoombtn" id="zoomOut" title="Zoom out">−</button>
      <span class="mono zoomLabel" id="zoomLabel">1×</span>
      <button class="zoombtn" id="zoomIn" title="Zoom in">+</button>
    </div>
    <div class="timelineScroll" id="timelineScroll">
      <div class="timelineInner" id="timelineInner">
        <div class="ruler" id="ruler"></div>
        <div class="lane" id="trimLane"><span class="lane-label">trim</span></div>
        <div class="lane" id="noteLane"><span class="lane-label">notes</span></div>
      </div>
    </div>
  </div>

  <div class="lists">
    <div>
      <h2>Trims</h2>
      <div id="trimList"><div class="empty">None yet — drag on the amber lane.</div></div>
    </div>
    <div>
      <h2>Notes</h2>
      <div id="noteList"><div class="empty">None yet — click the blue lane.</div></div>
    </div>
  </div>

  <footer>
    <span class="status" id="status"></span>
    <button class="action primary" id="sendEdits" disabled>Send for edits</button>
    <button class="action ready" id="markReady">Mark ready</button>
  </footer>

<script>
const v = document.getElementById('v');
const timelineScroll = document.getElementById('timelineScroll');
const timelineInner = document.getElementById('timelineInner');
const trimLane = document.getElementById('trimLane');
const noteLane = document.getElementById('noteLane');
const ruler = document.getElementById('ruler');
const zoomInBtn = document.getElementById('zoomIn');
const zoomOutBtn = document.getElementById('zoomOut');
const zoomLabel = document.getElementById('zoomLabel');
const trimListEl = document.getElementById('trimList');
const noteListEl = document.getElementById('noteList');
const sendBtn = document.getElementById('sendEdits');
const readyBtn = document.getElementById('markReady');
const statusEl = document.getElementById('status');

let dur = 0;
let crops = [];
let notes = [];
let popover = null;

const ZOOM_LEVELS = [1, 2, 4, 8, 16, 32];
let zoomIdx = 0;

function applyZoom(centerTime) {
  const z = ZOOM_LEVELS[zoomIdx];
  const w = Math.round(timelineScroll.clientWidth * z);
  timelineInner.style.width = w + 'px';
  zoomLabel.textContent = z + '×';
  zoomOutBtn.disabled = zoomIdx === 0;
  zoomInBtn.disabled = zoomIdx === ZOOM_LEVELS.length - 1;
  buildRuler();
  renderMarks();
  refreshHeads();
  const t = centerTime == null ? v.currentTime : centerTime;
  timelineScroll.scrollLeft = (t / dur) * w - timelineScroll.clientWidth / 2;
}
zoomInBtn.onclick = () => { zoomIdx = Math.min(ZOOM_LEVELS.length - 1, zoomIdx + 1); applyZoom(); };
zoomOutBtn.onclick = () => { zoomIdx = Math.max(0, zoomIdx - 1); applyZoom(); };

function fmt(t) {
  t = Math.max(0, t);
  const m = Math.floor(t / 60);
  const s = (t % 60).toFixed(1).padStart(4, '0');
  return m + ':' + s;
}

function xToTime(el, clientX) {
  const r = el.getBoundingClientRect();
  const frac = Math.min(1, Math.max(0, (clientX - r.left) / r.width));
  return frac * dur;
}

function timeToX(el, t) {
  const r = el.getBoundingClientRect();
  return (t / dur) * r.width;
}

function buildRuler() {
  ruler.innerHTML = '';
  if (!dur) return;
  const pxPerSec = timelineInner.getBoundingClientRect().width / dur;
  const steps = [0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600];
  let step = steps[steps.length - 1];
  for (const s of steps) { if (s * pxPerSec >= 70) { step = s; break; } }
  for (let t = 0; t <= dur; t += step) {
    const el = document.createElement('span');
    el.className = 'tick mono';
    el.style.left = (t / dur * 100) + '%';
    el.textContent = fmt(t);
    ruler.appendChild(el);
  }
}

function addPlayhead(el) {
  const p = document.createElement('div');
  p.className = 'playhead';
  el.appendChild(p);
  return p;
}
const heads = [];

function refreshHeads() {
  const x = (v.currentTime / dur * 100) + '%';
  heads.forEach(h => h.style.left = x);
}

function renderLists() {
  sendBtn.disabled = crops.length === 0 && notes.length === 0;
  readyBtn.disabled = crops.length > 0 || notes.length > 0;

  trimListEl.innerHTML = '';
  if (!crops.length) trimListEl.innerHTML = '<div class="empty">None yet — drag on the amber lane.</div>';
  crops.forEach((c, i) => {
    const chip = document.createElement('div');
    chip.className = 'chip trim';
    chip.innerHTML = `<span class="dot"></span><span class="t mono">${fmt(c.start)}–${fmt(c.end)}</span>
      <span class="txt">runs long</span><button title="Remove">×</button>`;
    chip.querySelector('button').onclick = () => { crops.splice(i, 1); renderAll(); };
    trimListEl.appendChild(chip);
  });

  noteListEl.innerHTML = '';
  if (!notes.length) noteListEl.innerHTML = '<div class="empty">None yet — click the blue lane.</div>';
  notes.forEach((n, i) => {
    const chip = document.createElement('div');
    chip.className = 'chip note';
    chip.innerHTML = `<span class="dot"></span><span class="t mono">${fmt(n.time)}</span>
      <span class="txt">${n.text.replace(/</g, '&lt;')}</span><button title="Remove">×</button>`;
    chip.querySelector('button').onclick = () => { notes.splice(i, 1); renderAll(); };
    noteListEl.appendChild(chip);
  });
}

function renderMarks() {
  trimLane.querySelectorAll('.region').forEach(e => e.remove());
  crops.forEach((c, i) => {
    const el = document.createElement('div');
    el.className = 'region';
    el.style.left = timeToX(trimLane, c.start) + 'px';
    el.style.width = Math.max(2, timeToX(trimLane, c.end) - timeToX(trimLane, c.start)) + 'px';
    const x = document.createElement('div');
    x.className = 'x';
    x.textContent = '×';
    x.onclick = (e) => { e.stopPropagation(); crops.splice(i, 1); renderAll(); };
    el.appendChild(x);
    trimLane.appendChild(el);
  });
  noteLane.querySelectorAll('.pin').forEach(e => e.remove());
  notes.forEach((n, i) => {
    const el = document.createElement('div');
    el.className = 'pin';
    el.style.left = timeToX(noteLane, n.time) + 'px';
    el.title = n.text;
    el.onclick = (e) => { e.stopPropagation(); openNotePopover(n.time, e.clientX, i); };
    noteLane.appendChild(el);
  });
}

function renderAll() { renderLists(); renderMarks(); closePopover(); }

function closePopover() {
  if (popover) { popover.remove(); popover = null; }
}

function openNotePopover(time, clientX, existingIndex) {
  closePopover();
  const box = document.createElement('div');
  box.className = 'popover';
  const existing = existingIndex != null ? notes[existingIndex] : null;
  box.style.left = Math.min(window.innerWidth - 260, Math.max(10, clientX - 120)) + 'px';
  const laneRect = noteLane.getBoundingClientRect();
  box.style.top = (laneRect.bottom + window.scrollY + 6) + 'px';
  box.innerHTML = `<div class="mono" style="color:var(--dim);font-size:12px;margin-bottom:6px;">@ ${fmt(time)}</div>
    <textarea placeholder="What should the agent do here?">${existing ? existing.text.replace(/</g, '&lt;') : ''}</textarea>
    <div class="row">
      ${existing ? '<button class="action" id="delNote">Delete</button>' : '<span></span>'}
      <button class="action primary" id="saveNote">${existing ? 'Save' : 'Add note'}</button>
    </div>`;
  document.body.appendChild(box);
  popover = box;
  const ta = box.querySelector('textarea');
  ta.focus();
  box.querySelector('#saveNote').onclick = () => {
    const text = ta.value.trim();
    if (!text) { closePopover(); return; }
    if (existing) existing.text = text;
    else notes.push({ time, text });
    renderAll();
  };
  const del = box.querySelector('#delNote');
  if (del) del.onclick = () => { notes.splice(existingIndex, 1); renderAll(); };
}

v.addEventListener('loadedmetadata', () => {
  dur = v.duration;
  heads.push(addPlayhead(ruler), addPlayhead(trimLane), addPlayhead(noteLane));
  applyZoom(0);
  renderAll();
});
v.addEventListener('timeupdate', refreshHeads);
window.addEventListener('resize', () => applyZoom());

ruler.addEventListener('click', (e) => { v.currentTime = xToTime(ruler, e.clientX); });

// trim lane: drag to create a region, previewing both ends in the video as you go
let dragStart = null;
let dragEl = null;
let lastSeek = 0;
function seekPreview(t) {
  const now = performance.now();
  if (now - lastSeek < 40) return;
  lastSeek = now;
  v.currentTime = t;
}
trimLane.addEventListener('mousedown', (e) => {
  if (e.target.closest('.region')) return;
  dragStart = xToTime(trimLane, e.clientX);
  v.pause();
  v.currentTime = dragStart;
  dragEl = document.createElement('div');
  dragEl.className = 'region';
  dragEl.style.left = timeToX(trimLane, dragStart) + 'px';
  dragEl.style.width = '0px';
  trimLane.appendChild(dragEl);
});
window.addEventListener('mousemove', (e) => {
  if (dragStart == null || !dur) return;
  const t = xToTime(trimLane, e.clientX);
  const lo = Math.min(dragStart, t), hi = Math.max(dragStart, t);
  dragEl.style.left = timeToX(trimLane, lo) + 'px';
  dragEl.style.width = Math.max(1, timeToX(trimLane, hi) - timeToX(trimLane, lo)) + 'px';
  seekPreview(t);
});
window.addEventListener('mouseup', (e) => {
  if (dragStart == null) return;
  const t = xToTime(trimLane, e.clientX);
  const lo = Math.min(dragStart, t), hi = Math.max(dragStart, t);
  dragStart = null;
  if (dragEl) { dragEl.remove(); dragEl = null; }
  if (hi - lo >= 0.15) { crops.push({ start: lo, end: hi }); renderAll(); }
  else { v.currentTime = t; }
});

noteLane.addEventListener('click', (e) => {
  if (e.target.closest('.pin')) return;
  openNotePopover(xToTime(noteLane, e.clientX), e.clientX, null);
});

function submit(action) {
  sendBtn.disabled = true; readyBtn.disabled = true;
  statusEl.textContent = 'Sending…';
  fetch('/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, crops, notes }),
  }).then(() => {
    document.body.innerHTML = '<div class="done"><h1 style="font-size:20px">Sent — you can close this tab.</h1></div>';
  }).catch(() => { statusEl.textContent = 'Failed to send — check the terminal.'; sendBtn.disabled = false; readyBtn.disabled = false; });
}
sendBtn.onclick = () => submit('edits');
readyBtn.onclick = () => submit('ready');
</script>
</body>
</html>
"""

result = {}
done = threading.Event()


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/video":
            self._serve_video()
        else:
            self.send_error(404)

    def _serve_video(self):
        # The browser cancels in-flight Range requests constantly while scrubbing —
        # that's a normal disconnect, not an error worth a traceback.
        try:
            size = video_path.stat().st_size
            range_header = self.headers.get("Range")
            if range_header:
                start_s, _, end_s = range_header.replace("bytes=", "").partition("-")
                start = int(start_s or 0)
                end = min(int(end_s), size - 1) if end_s else size - 1
                self.send_response(206)
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                length = end - start + 1
            else:
                start, length = 0, size
                self.send_response(200)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(length))
            self.end_headers()
            with open(video_path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        if self.path != "/submit":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length) or b"{}")
        result["action"] = data.get("action")
        result["crops"] = data.get("crops", [])
        result["notes"] = data.get("notes", [])
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        done.set()


sock = socket.socket()
sock.bind(("127.0.0.1", 0))
port = sock.getsockname()[1]
sock.close()

server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{port}/"
print(f"Review it at {url} (opening your browser) ...")
webbrowser.open(url)
done.wait()
server.shutdown()

out = root / "review.json"
out.write_text(json.dumps(result, indent=2))
n_crops, n_notes = len(result["crops"]), len(result["notes"])
print(f"Saved {out}  (action={result['action']}, {n_crops} trim(s), {n_notes} note(s))")
for note in result["notes"]:
    print(f"  note @ {note['time']:.1f}s: {note['text']}")
for crop in result["crops"]:
    print(f"  trim {crop['start']:.1f}s - {crop['end']:.1f}s")
