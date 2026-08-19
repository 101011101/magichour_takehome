# Build every garment reference for the Attention Modulation Test.
#
# Ten arms, four mechanisms for controlling what klein attends to in the reference:
#   remove the person       control, QX (AC-A)
#   remove only the head    BC, BALD_raw (AC-B)
#   remove nothing, destroy identity   D1h/D2/D3 on both bases (AC-C)
#   remove nothing at all   BALD_raw
#
# The /O arms need no generative step and are built for every source. The /B arms
# need a bald frame first, so they are built only where one exists.
import csv
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acc_destroy as D           # noqa: E402
import garment_crop as G          # noqa: E402
import phase3_variants as P       # noqa: E402

OUT = os.path.join(P.REPO, "v2", "runs", "amt")
BLUR = dict(k=0.34, passes=3, pad=0.18)      # HEAVY tier


def build(src, meta, files):
    """All arms available for one garment source. Returns what was written."""
    raw = cv2.imread(meta[src])
    M = P.masks(raw, src)
    x0, y0, x1, y1 = G.bbox_of((M["subject"] > 0.5).astype(np.uint8), raw.shape[:2])

    def save(tag, px, alpha, box):
        a, b, c, d = box
        G.write_rgb(os.path.join(OUT, f"{src}__{tag}.jpg"),
                    P.flatten(px[b:d, a:c], alpha[b:d, a:c], P.WHITE))
        files[f"{src}|{tag}"] = f"{src}__{tag}.jpg"

    box = (x0, y0, x1, y1)
    save("control", raw, M["noface"], box)
    # /O: hair kept, nothing cut, identity destroyed in place
    full, face = M["subject"], M["face"]
    save("D1hO", D.blur(raw, face, **BLUR), full, box)
    save("D2O", D.twirl(raw, face), full, box)
    save("D3O", D.pixelate(raw, face), full, box)

    bald_p = os.path.join(P.REPO, "v2", "runs", "phase3", f"{src}__PRE2raw.jpg")
    if os.path.exists(bald_p):
        bald = cv2.imread(bald_p)
        MB = P.masks(bald, src + "__PRE2", cranium=True)
        bb = G.bbox_of((MB["subject"] > 0.5).astype(np.uint8), bald.shape[:2])
        bbox = (bb[0], bb[1], bb[2], bb[3])
        save("BC_klein", bald, MB["noface"], bbox)
        # BALD_raw is the control that asks whether cropping earns its place at all:
        # the bald photograph, uncropped, nothing removed
        G.write_rgb(os.path.join(OUT, f"{src}__BALD_raw.jpg"), bald)
        files[f"{src}|BALD_raw"] = f"{src}__BALD_raw.jpg"
        head = MB["head"]
        save("D1hB", D.blur(bald, head, **BLUR), MB["subject"], bbox)
        save("D2B", D.twirl(bald, head), MB["subject"], bbox)
        save("D3B", D.pixelate(bald, head), MB["subject"], bbox)


def main():
    meta = {r["stem"]: r["src_path"] for r in
            csv.DictReader(open(os.path.join(P.REPO, "v2", "runs", "crop_screen", "crop_log.csv")))}
    pj = json.load(open(os.path.join(OUT, "_pairs.json")))
    files = {}
    for s in pj["srcs"]:
        build(s, meta, files)
        print(f"  {s}")
    # QX extraction already exists for the cohort; carry it across where present
    for s in pj["srcs"]:
        q = os.path.join(P.REPO, "v2", "runs", "acab", f"{s}__QX_qwen_p1.jpg")
        if os.path.exists(q):
            files[f"{s}|QX_qwen_p1"] = os.path.relpath(q, OUT)
    json.dump({"files": files, **pj}, open(os.path.join(OUT, "_refs.json"), "w"), indent=1)
    have = {}
    for k in files:
        have[k.split("|")[1]] = have.get(k.split("|")[1], 0) + 1
    print("\narm coverage over "f"{len(pj['srcs'])} sources:")
    for k, v in sorted(have.items()):
        print(f"  {k:12} {v:2d}")


if __name__ == "__main__":
    main()
