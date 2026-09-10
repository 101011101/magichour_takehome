"""v3.5 probe — does one klein call re-pose AND bald the wearer?

The gap this tests: `BC` bald-passes the raw photograph before it crops, because hair
falling on the shoulders and chest cannot be told from garment by any matte. `VEi` gets the
same effect for free — the mannequin sentence replaces the head and its hair together. The
re-pose arm `M1q` does neither: it keeps the wearer's own head, so cropping it leaves
whatever hair spilled onto the garment. On a long-haired wearer that is hair baked into the
reference, and no downstream stage removes it.

So: three call-1 arms on the same A4 crop, one klein call each, seed 46, on fal.

  M0    Q3 — the mannequin sentence (reused from link A, same backend and seed: free)
  M1q   Q3 with the mannequin sentence deleted — the approved re-pose arm, hair kept
  M1qb  M1q + a bald clause taken from v3lib.BALD_PROMPT, so the wording is the record's

The set is the five garments with the most **garment lost to hair removal**, measured off
V2's own crop pair: `c32_no_face_keep_hair` minus `c3_no_face`, which is exactly the
quantity V2's `hair_threshold = 0.14` gates BC_klein on. Four of the five are over it.

  python3 v3/build/run_v35_bald_probe.py [--dry]
"""
import argparse
import csv
import json
import os
import sys
import time

import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
import v3lib as L                 # noqa: E402
import run_ironman as R           # noqa: E402

SRC = os.path.join(REPO, "v3", "runs", "v34", "ironman2")
LINKA = os.path.join(REPO, "v3", "runs", "v35", "linkA")
OUT = os.path.join(REPO, "v3", "runs", "v35", "bald_probe")
ENDPOINT = "fal-ai/flux-2/klein/4b/distilled/edit"
USD_PER_CALL = 0.015

# ranked by garment lost to hair removal (v2/runs/crop_screen alphas); V2 gates BC_klein
# at 0.14, so the first four are over its own threshold
GARMENTS = [("p021", 0.195), ("dualuse_woman_top_denim_skirt_nonceleb", 0.170),
            ("p023", 0.169), ("dualuse_zendaya_white_blazer_skirt", 0.144),
            ("p012", 0.140)]

# lifted from v3lib.BALD_PROMPT's first two sentences so the wording is the record's, not a
# new invention; the third sentence is dropped because KEEP and PERSON_CLAUSE already say it
BALD = (" The person is completely bald: remove all hair from the head and any hair falling "
        "over the shoulders, chest or back, and show the scalp.")


def m1q(framing):
    return R.KEEP.lstrip() + R.PERSON_CLAUSE[framing] + R.HOLD


def m1qb(framing):
    return R.KEEP.lstrip() + BALD + R.PERSON_CLAUSE[framing] + R.HOLD


ARMS = {"M1q": m1q, "M1qb": m1qb}


def canvas(bgr, maxpix=1_048_576):
    h, w = bgr.shape[:2]
    k = min(1.0, (maxpix / (h * w)) ** 0.5)
    return max(16, int(h * k) // 16 * 16), max(16, int(w * k) // 16 * 16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=46)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    framings = {k.split("|")[0]: v["framing"] for k, v in
                json.load(open(os.path.join(SRC, "meta", "prompts.json"))).items()
                if k.endswith("|VEi")}
    os.makedirs(os.path.join(OUT, "refs"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "meta"), exist_ok=True)

    jobs = [(g, hs, arm) for g, hs in GARMENTS for arm in ARMS]
    todo = [j for j in jobs if not os.path.exists(os.path.join(OUT, "refs", f"{j[0]}__{j[2]}.jpg"))]
    print(f"{len(GARMENTS)} garments x {len(ARMS)} arms = {len(jobs)} refs; "
          f"{len(todo)} to call = ${len(todo) * USD_PER_CALL:.2f} on fal")
    if a.dry:
        g, hs = GARMENTS[0]
        for arm, fn in ARMS.items():
            print(f"\n[{arm}] {g} (hair share {hs:.3f}, framing {framings[g]})\n  {fn(framings[g])}")
        return

    _load_env()
    rows, t0 = [], time.time()
    for g, hs, arm in todo:
        crop = cv2.imread(os.path.join(SRC, "inputs", f"{g}__A4.jpg"))
        h, w = canvas(crop)
        prompt = ARMS[arm](framings[g])
        t1 = time.time()
        im = L.call(ENDPOINT, {"image_urls": [L.b64(crop)], "prompt": prompt,
                               "seed": a.seed, "image_size": {"width": w, "height": h}})
        im = R.recrop(im)
        cv2.imwrite(os.path.join(OUT, "refs", f"{g}__{arm}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 95])
        rows.append({"garment": g, "hair_share": hs, "arm": arm, "framing": framings[g],
                     "seconds": round(time.time() - t1, 2), "prompt": prompt})
        print(f"  {len(rows)}/{len(todo)} {arm} {g} {rows[-1]['seconds']}s", flush=True)
        with open(os.path.join(OUT, "meta", "probe.csv"), "w", newline="") as f:
            w_ = csv.DictWriter(f, fieldnames=list(rows[0])); w_.writeheader(); w_.writerows(rows)
    json.dump({"endpoint": ENDPOINT, "seed": a.seed, "garments": GARMENTS,
               "bald_clause": BALD, "calls": len(rows),
               "usd": round(len(rows) * USD_PER_CALL, 2),
               "hair_metric": "garment lost to hair removal: (c32_no_face_keep_hair - "
                              "c3_no_face) alpha area, v2/runs/crop_screen; V2 gates "
                              "BC_klein at hair_threshold=0.14",
               "M0_from": "v3/runs/v35/linkA/refs (same backend, same seed 46)",
               "wall_seconds": round(time.time() - t0, 1)},
              open(os.path.join(OUT, "meta", "run.json"), "w"), indent=1)
    print(f"{len(rows)} calls, ${len(rows) * USD_PER_CALL:.2f}")


def _load_env():
    for line in open(os.path.join(REPO, ".env"), encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


if __name__ == "__main__":
    main()
