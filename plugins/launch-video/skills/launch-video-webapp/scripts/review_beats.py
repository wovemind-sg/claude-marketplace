#!/usr/bin/env python3
"""
Show the split-out beat clips in a browser so the client can approve them (or
leave a note) before the script is sized to their exact lengths.

Usage:  python3 scripts/review_beats.py [video_dir]

Opens a local page listing every video/recordings/beat-NN.mp4 in order. For
each beat the client can play it, tick "Looks good", or leave a note. Blocks
until they click "Send for edits" (enabled once any note exists, or any beat
isn't ticked) or "All good" (enabled only once every beat is ticked with no
notes), then writes video/beats_review.json:
    {"action": "edits"|"ready",
     "beats": {"beat-01": {"ok": true, "note": ""}, ...}}
and exits 0. Re-run after acting on notes to confirm the fix.
"""
import http.server
import json
import pathlib
import re
import socket
import sys
import threading
import webbrowser

root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("video")
rec_dir = root / "recordings"
beats = sorted(
    (p for p in rec_dir.glob("beat-*.mp4") if re.fullmatch(r"beat-\d+\.mp4", p.name)),
    key=lambda p: p.name,
) if rec_dir.exists() else []
if not beats:
    sys.exit(f"ERROR: no beat-NN.mp4 files in {rec_dir} — run split_beats.py first")

BEAT_IDS = [p.stem for p in beats]

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Review the beats</title>
<style>
  :root {
    --bg: #0d0e11; --panel: #15171b; --panel-2: #1b1e24; --line: #282b32;
    --text: #e7e8ec; --dim: #8d919c; --note: #5fa8ff; --ok: #3fb87f;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    padding: 28px 20px 96px;
  }
  h1 { font-size: 17px; font-weight: 600; margin: 0 0 4px; }
  .sub { color: var(--dim); font-size: 13px; margin: 0 0 24px; max-width: 60ch; }
  .grid {
    max-width: 960px; margin: 0 auto; display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 20px;
  }
  .card {
    background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 14px;
  }
  .card h2 { font-size: 13px; font-weight: 600; margin: 0 0 8px; color: var(--dim); }
  video { width: 100%; border-radius: 8px; background: #000; }
  .row { display: flex; align-items: center; gap: 8px; margin-top: 10px; }
  .row label { font-size: 13px; display: flex; align-items: center; gap: 6px; cursor: pointer; }
  textarea {
    width: 100%; min-height: 50px; resize: vertical; background: var(--bg); color: var(--text);
    border: 1px solid var(--line); border-radius: 6px; padding: 6px 8px; font: inherit; margin-top: 8px;
  }
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
  button.action.ready:not(:disabled) { background: var(--ok); border-color: var(--ok); color: #06170f; }
  .done { text-align: center; margin-top: 18vh; color: var(--dim); }
</style>
</head>
<body>
  <h1>Review the beats</h1>
  <p class="sub">Watch each clip. Tick "Looks good" or leave a note for anything to change. Then send it back or mark them all good below.</p>
  <div class="grid" id="grid"></div>
  <footer>
    <span class="status" id="status"></span>
    <button class="action primary" id="sendEdits" disabled>Send for edits</button>
    <button class="action ready" id="markReady" disabled>All good</button>
  </footer>
<script>
const BEAT_IDS = __BEAT_IDS__;
const grid = document.getElementById('grid');
const state = {};
BEAT_IDS.forEach(id => {
  state[id] = { ok: false, note: '' };
  const card = document.createElement('div');
  card.className = 'card';
  card.innerHTML = `
    <h2>${id}</h2>
    <video src="/video/${id}.mp4" controls></video>
    <div class="row"><label><input type="checkbox" data-id="${id}" class="okbox"> Looks good</label></div>
    <textarea data-id="${id}" placeholder="Note for the agent (leave blank if none)"></textarea>
  `;
  grid.appendChild(card);
});
const sendBtn = document.getElementById('sendEdits');
const readyBtn = document.getElementById('markReady');
const statusEl = document.getElementById('status');

function refresh() {
  const notes = Object.values(state).some(s => s.note.trim());
  const allOk = Object.values(state).every(s => s.ok) && !notes;
  sendBtn.disabled = !notes && Object.values(state).every(s => s.ok);
  readyBtn.disabled = !allOk;
}
grid.querySelectorAll('.okbox').forEach(cb => {
  cb.onchange = () => { state[cb.dataset.id].ok = cb.checked; refresh(); };
});
grid.querySelectorAll('textarea').forEach(ta => {
  ta.oninput = () => { state[ta.dataset.id].note = ta.value; refresh(); };
});
refresh();

function submit(action) {
  sendBtn.disabled = true; readyBtn.disabled = true;
  statusEl.textContent = 'Sending…';
  const beats = {};
  for (const id of BEAT_IDS) beats[id] = { ok: state[id].ok, note: state[id].note.trim() };
  fetch('/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, beats }),
  }).then(() => {
    document.body.innerHTML = '<div class="done"><h1 style="font-size:20px">Sent — you can close this tab.</h1></div>';
  }).catch(() => { statusEl.textContent = 'Failed to send — check the terminal.'; refresh(); });
}
sendBtn.onclick = () => submit('edits');
readyBtn.onclick = () => submit('ready');
</script>
</body>
</html>
""".replace("__BEAT_IDS__", json.dumps(BEAT_IDS))

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
        elif self.path.startswith("/video/"):
            self._serve_video(self.path[len("/video/"):])
        else:
            self.send_error(404)

    def _serve_video(self, name):
        path = rec_dir / name
        if not re.fullmatch(r"beat-\d+\.mp4", name) or not path.exists():
            self.send_error(404)
            return
        try:
            size = path.stat().st_size
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
            with open(path, "rb") as f:
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
        result["beats"] = data.get("beats", {})
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

out = root / "beats_review.json"
out.write_text(json.dumps(result, indent=2))
n_notes = sum(1 for b in result["beats"].values() if b.get("note"))
print(f"Saved {out}  (action={result['action']}, {n_notes} note(s))")
for beat_id, b in result["beats"].items():
    if b.get("note"):
        print(f"  {beat_id}: {b['note']}")
