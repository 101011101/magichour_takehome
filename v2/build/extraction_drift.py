# Triage signal for AC-A extraction drift. NOT a verdict.
#
# AC-A regenerates the whole garment, so it can return a beautiful crop of the wrong
# clothes. Section 2b of EXPERIMENT.md established that neither instrument we have
# catches that: garment_sim scored 0.78 and the VLM scored 4/5 on an output that
# transferred no garment at all. Both reward a PLAUSIBLE garment over the CORRECT
# one, so no embedding metric belongs here.
#
# What this does instead is deliberately dumb and therefore hard to fool: compare
# simple, direct statistics of the garment pixels against the control crop.
#   dL, dC   median lightness and chroma shift in LAB -- catches colour drift
#   dHue     circular hue shift -- catches a recoloured garment
#   dEdge    edge density ratio -- catches a pattern being smoothed away or invented
# Gross drift shows up here. Subtle invention (a changed collar, a moved seam) does
# NOT, and cannot -- that is what the reviewer's eye is for. Use this only to rank
# which references deserve the hardest look.
import csv
import glob
import os
import sys

import cv2
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUN = os.path.join(REPO, "v2", "runs", "acab")


NORM_H = 900   # every image is rescaled so the GARMENT is this tall before Canny


def garment_stats(bgr, white_thresh=244):
    """Statistics over the garment pixels only -- the white ground is excluded, so
    a change in how much white surrounds the garment cannot move these numbers.

    SCALE NORMALISATION IS LOAD-BEARING. A first version compared edge density on
    the images as-is, and the control crops are ~376x897 while the extractions come
    back at 672x1024 or larger. Canny finds more edges per pixel at higher
    resolution, so the "pattern lost" signal was partly measuring resolution. Both
    images are now rescaled so the garment's bounding box is the same height before
    any edge measurement. The colour statistics are scale-free and were never
    affected."""
    g0 = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    s0 = g0 < white_thresh
    ys = np.where(s0.any(axis=1))[0]
    if len(ys) > 20:
        gh = int(ys[-1] - ys[0]) or 1
        k = NORM_H / gh
        if 0.05 < k < 20:
            bgr = cv2.resize(bgr, (max(8, int(bgr.shape[1] * k)), max(8, int(bgr.shape[0] * k))),
                             interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC)
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    sel = g < white_thresh
    if sel.sum() < 400:
        return None
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    L, a, b = lab[..., 0][sel], lab[..., 1][sel] - 128, lab[..., 2][sel] - 128
    chroma = np.sqrt(a * a + b * b)
    hue = np.arctan2(b, a)
    # circular mean, since hue wraps
    hx, hy = float(np.mean(np.cos(hue))), float(np.mean(np.sin(hue)))
    edges = cv2.Canny(bgr, 60, 160) > 0
    return {"L": float(np.median(L)), "C": float(np.median(chroma)),
            "hx": hx, "hy": hy,
            "edge": float(edges[sel].mean()), "area": int(sel.sum())}


def compare(ctrl, out):
    c, o = garment_stats(ctrl), garment_stats(out)
    if c is None or o is None:
        return None
    dhue = np.degrees(np.arctan2(
        o["hy"] * c["hx"] - o["hx"] * c["hy"], o["hx"] * c["hx"] + o["hy"] * c["hy"]))
    return {"dL": o["L"] - c["L"], "dC": o["C"] - c["C"], "dHue": float(abs(dhue)),
            "dEdge": (o["edge"] + 1e-6) / (c["edge"] + 1e-6)}


def verdict(d):
    """Deliberately coarse. Anything not flagged still needs looking at."""
    if d is None:
        return "no garment found"
    f = []
    if abs(d["dL"]) > 12:
        f.append(f"lightness {d['dL']:+.0f}")
    if abs(d["dC"]) > 10:
        f.append(f"chroma {d['dC']:+.0f}")
    if d["dHue"] > 25:
        f.append(f"hue {d['dHue']:.0f}deg")
    if d["dEdge"] > 1.9 or d["dEdge"] < 0.5:
        f.append(f"pattern x{d['dEdge']:.2f}")
    return "DRIFT: " + ", ".join(f) if f else "no gross drift"


def run(tags=None):
    stems = sorted({os.path.basename(p).split("__")[0]
                    for p in glob.glob(os.path.join(RUN, "*__CTRL.jpg"))})
    tags = tags or ["QX_qwen_p1", "QX_qwen_p2", "QX_qwen_p3",
                    "QX_plus_p1", "QX_plus_p3", "QX_kleind", "QX_kleinb"]
    notes, agg = {}, {t: [] for t in tags}
    for s in stems:
        ctrl = cv2.imread(os.path.join(RUN, f"{s}__CTRL.jpg"))
        for t in tags:
            f = os.path.join(RUN, f"{s}__{t}.jpg")
            if not os.path.exists(f):
                continue
            d = compare(ctrl, cv2.imread(f))
            notes[f"{s}|{t}"] = verdict(d)
            if d:
                agg[t].append(d)
    return notes, agg


if __name__ == "__main__":
    notes, agg = run()
    print(f"{'arm':14} {'n':>3} {'|dL|':>6} {'|dC|':>6} {'dHue':>6} {'dEdge':>7} {'flagged':>8}")
    for t, ds in agg.items():
        if not ds:
            continue
        n = len(ds)
        fl = sum(1 for d in ds if verdict(d).startswith("DRIFT"))
        print(f"{t:14} {n:3d} {np.mean([abs(d['dL']) for d in ds]):6.1f} "
              f"{np.mean([abs(d['dC']) for d in ds]):6.1f} "
              f"{np.mean([d['dHue'] for d in ds]):6.1f} "
              f"{np.mean([d['dEdge'] for d in ds]):7.2f} {fl:5d}/{n}")
    print("\nper-reference flags:")
    for k in sorted(notes):
        if notes[k].startswith("DRIFT"):
            print(f"  {k:44} {notes[k]}")
