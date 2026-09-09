"""v3.5 derived arms — the head cut off a reference, with the incumbent's own cropper.

`M1c` / `M0c` are `M1` / `M0` with the head subtracted. No model call: the reference is
already paid for, so the head-crop idea costs nothing to test.

The subtraction is not a horizontal cut. It is **BC's** mechanism, imported not reinvented:
the V2 cropper's `noface` mask (BiRefNet subject matte x the MediaPipe multiclass parse,
cranium path) flattened to white -- `phase3_variants.masks(bgr, stem, cranium=True)`, the
same call `v3/build/ironman_bc_crop.py` makes for the `BC` references. That is the point of
the experiment: BC's head removal on VEi's re-posed reference.

  python3 v3/build/run_v35_headcrop.py [M1 M0 ...]     -> refs/{g}__{arm}c.jpg
"""
import json
import os
import sys
import time

import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v2", "build"))
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import garment_crop as G          # noqa: E402
import phase3_variants as P       # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v35", "linkA")


def headcrop(img, stem):
    """The BC crop applied to a v3.5 reference: subject bbox, head pixels subtracted."""
    import numpy as np
    M = P.masks(img, stem, cranium=True)
    x0, y0, x1, y1 = G.bbox_of((M["subject"] > 0.5).astype(np.uint8), img.shape[:2])
    return (P.flatten(img[y0:y1, x0:x1], M["noface"][y0:y1, x0:x1], P.WHITE),
            bool(M["cranium_used"]))


def main(arms):
    refs = os.path.join(RUN, "refs")
    rec = {}
    for arm in arms:
        srcs = sorted(f for f in os.listdir(refs) if f.endswith(f"__{arm}.jpg"))
        print(f"{arm}: {len(srcs)} references")
        for f in srcs:
            g = f[:-len(f"__{arm}.jpg")]
            out = os.path.join(refs, f"{g}__{arm}c.jpg")
            if os.path.exists(out):
                continue
            t0 = time.time()
            im, cr = headcrop(cv2.imread(os.path.join(refs, f)), f"v35_{arm}_{g}")
            G.write_rgb(out, im)
            rec[f"{g}|{arm}c"] = {"cranium_used": cr, "seconds": round(time.time() - t0, 1),
                                  "size": [im.shape[1], im.shape[0]]}
            print(f"  {g} {arm}c: {im.shape[1]}x{im.shape[0]} cranium={cr} "
                  f"{rec[f'{g}|{arm}c']['seconds']}s", flush=True)
    p = os.path.join(RUN, "meta", "headcrop.json")
    old = json.load(open(p)) if os.path.exists(p) else {}
    json.dump({"cropper": "v2 phase3_variants.masks(cranium=True) -> noface, as ironman_bc_crop.py",
               "refs": {**old.get("refs", {}), **rec}}, open(p, "w"), indent=1)
    print("done")


if __name__ == "__main__":
    main(sys.argv[1:] or ["M1", "M0"])
