"""BC references for the iron-man run, made with the V2 cropper of record:
bald frame -> BiRefNet subject matte x class labels -> head SUBTRACTED (cranium path) -> white.
This is run_v30.crop_ref(..., cranium=True), i.e. BC_klein as prd/v2/ARCHITECTURE.md defines it.

  python3 v3/build/ironman_bc_crop.py <dir with refs/{g}__bald.jpg>   -> refs/{g}__BC.jpg + refs/bc_crop.json
"""
import json, os, sys, time
import cv2, numpy as np
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v2", "build")); sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import garment_crop as G          # noqa: E402
import phase3_variants as P       # noqa: E402


def crop_bc(img, stem):
    M = P.masks(img, stem, cranium=True)
    x0, y0, x1, y1 = G.bbox_of((M["subject"] > 0.5).astype(np.uint8), img.shape[:2])
    return P.flatten(img[y0:y1, x0:x1], M["noface"][y0:y1, x0:x1], P.WHITE), bool(M["cranium_used"])


def main(run):
    refs = os.path.join(run, "refs"); rec = {}
    balds = sorted(f for f in os.listdir(refs) if f.endswith("__bald.jpg"))
    print(f"{len(balds)} bald frames")
    for f in balds:
        g = f[:-len("__bald.jpg")]; out = os.path.join(refs, f"{g}__BC.jpg")
        if os.path.exists(out): continue
        t0 = time.time()
        im, cr = crop_bc(cv2.imread(os.path.join(refs, f)), f"im_{g}")
        G.write_rgb(out, im)
        rec[g] = {"cranium_used": cr, "seconds": round(time.time() - t0, 1), "size": [im.shape[1], im.shape[0]]}
        print(f"  {g}: {im.shape[1]}x{im.shape[0]} cranium={cr} {rec[g]['seconds']}s", flush=True)
    json.dump({"cropper": "v2 phase3_variants.masks(cranium=True) -> noface, run_v30.crop_ref", "refs": rec},
              open(os.path.join(refs, "bc_crop.json"), "w"), indent=1)
    print("done")


if __name__ == "__main__":
    main(sys.argv[1])
