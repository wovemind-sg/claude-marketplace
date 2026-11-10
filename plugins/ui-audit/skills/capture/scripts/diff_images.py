#!/usr/bin/env python3
"""Pixel-diff two trees of screenshots (<screen>/<viewport>/<state>.png).

Prints JSON: added, removed, changed (with changed_pct, bbox, overlay), unchanged.
--mask is a JSON file path or inline JSON: {"<screen>": [[x, y, w, h], ...]} of regions to ignore.
"""
import argparse
import json
import os
import sys
import tempfile

try:
    import numpy as np
    from PIL import Image
except ImportError:
    print("Pillow and numpy are required: pip install pillow numpy", file=sys.stderr)
    sys.exit(2)


def list_pngs(root):
    out = set()
    for dp, _, fs in os.walk(root):
        for f in fs:
            if f.lower().endswith(".png"):
                out.add(os.path.relpath(os.path.join(dp, f), root))
    return out


def load(p):
    return np.asarray(Image.open(p).convert("RGBA"), dtype=np.int16)


def compare(b_path, h_path, regions, threshold, overlay_path):
    b, h = load(b_path), load(h_path)
    mismatch = None
    if b.shape != h.shape:
        # Pad to the max size, top-left anchored; padding (transparent) counts as changed.
        mismatch = [list(b.shape[1::-1]), list(h.shape[1::-1])]
        H, W = max(b.shape[0], h.shape[0]), max(b.shape[1], h.shape[1])

        def pad(a):
            out = np.full((H, W, 4), -255, dtype=np.int16)  # differs from any pixel by >255 per channel
            out[:a.shape[0], :a.shape[1]] = a
            return out
        b, h = pad(b), pad(h)
    diff = (np.abs(b - h) > threshold * 255).any(axis=2)
    for x, y, w, hh in regions:
        diff[max(y, 0):y + hh, max(x, 0):x + w] = False
    pct = 100.0 * diff.sum() / diff.size
    res = {"changed_pct": round(float(pct), 4), "bbox": None, "overlay": None}
    if mismatch:
        res["size_mismatch"] = mismatch
    if diff.any():
        ys, xs = np.where(diff)
        res["bbox"] = [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)]
        ov = (np.clip(h[..., :3], 0, 255) * 0.35 + 255 * 0.65).astype(np.uint8)  # faded head image
        ov[diff] = (255, 0, 0)
        os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
        Image.fromarray(ov).save(overlay_path)
        res["overlay"] = overlay_path
    return res


def run(base, head, out, threshold=0.1, min_pct=0.01, masks=None):
    masks = masks or {}
    bs, hs = list_pngs(base), list_pngs(head)
    rep = {"added": sorted(hs - bs), "removed": sorted(bs - hs), "changed": [], "unchanged": []}
    for rel in sorted(bs & hs):
        screen = rel.split(os.sep)[0]
        r = compare(os.path.join(base, rel), os.path.join(head, rel), masks.get(screen, []),
                    threshold, os.path.join(out, rel))
        r["path"] = rel
        if r["changed_pct"] > min_pct:
            rep["changed"].append(r)
        else:
            if r["overlay"]:
                os.remove(r["overlay"])
            rep["unchanged"].append(rel)
    return rep


def selftest():
    with tempfile.TemporaryDirectory() as d:
        def save(side, rel, color, size=(100, 80), box=None):
            im = Image.new("RGB", size, color)
            if box:
                im.paste((0, 0, 0), box)
            p = os.path.join(d, side, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            im.save(p)
        for side in ("base", "head"):
            save(side, "same/desktop/default.png", "white")
        save("base", "chg/desktop/default.png", "white")
        save("head", "chg/desktop/default.png", "white", box=(10, 10, 30, 20))
        save("base", "masked/desktop/default.png", "white")
        save("head", "masked/desktop/default.png", "white", box=(10, 10, 30, 20))
        save("base", "size/desktop/default.png", "white")
        save("head", "size/desktop/default.png", "white", size=(100, 90))
        save("base", "noise/desktop/default.png", "white")
        save("head", "noise/desktop/default.png", (250, 250, 250))
        save("base", "gone/desktop/default.png", "white")
        save("head", "new/desktop/default.png", "white")
        r = run(os.path.join(d, "base"), os.path.join(d, "head"), os.path.join(d, "out"),
                masks={"masked": [[0, 0, 100, 80]]})
        ch = {c["path"]: c for c in r["changed"]}
        assert set(ch) == {os.path.join(s, "desktop/default.png") for s in ("chg", "size")}, r
        c = ch["chg/desktop/default.png"]
        assert c["bbox"] == [10, 10, 20, 10] and os.path.exists(c["overlay"]), c
        sz = ch["size/desktop/default.png"]
        assert sz["size_mismatch"] == [[100, 80], [100, 90]] and sz["bbox"] == [0, 80, 100, 10], sz
        assert 0 < sz["changed_pct"] < 100 and os.path.exists(sz["overlay"]), sz
        assert len(r["unchanged"]) == 3, r
        assert r["added"] == ["new/desktop/default.png"] and r["removed"] == ["gone/desktop/default.png"], r
    print(json.dumps({"selftest": "ok"}))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base"); ap.add_argument("--head"); ap.add_argument("--out")
    ap.add_argument("--threshold", type=float, default=0.1, help="per-channel tolerance, 0-1 (default 0.1)")
    ap.add_argument("--min-changed-pct", type=float, default=0.01, help="percent of pixels (default 0.01)")
    ap.add_argument("--mask"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.base and a.head and a.out):
        ap.error("--base, --head and --out are required")
    masks = {}
    if a.mask:
        masks = json.loads(a.mask) if a.mask.lstrip().startswith("{") else json.load(open(a.mask))
    for p in (a.base, a.head):
        if not os.path.isdir(p):
            print(json.dumps({"error": f"not a directory: {p}"}), file=sys.stderr)
            sys.exit(1)
    print(json.dumps(run(a.base, a.head, a.out, a.threshold, a.min_changed_pct, masks), indent=2))


if __name__ == "__main__":
    main()
