"""v3.3 phase 2: the version on the CROP. A4 crop -> klein -> bbox re-crop.

Template (every arm): head swap + PERSON_CLAUSE[framing], no colour word, seed 46.
  link 3  pose variants   P0 baseline, P1 feet, P2 hips, P3 "no ..." - legs and feet
  link 4  region variants M1 neck-up, M2 face-only, M3 skin kept (positive), M4 "no ..."

Each added sentence is itself keyed on the framing read (never name a part the crop
excludes); a cell whose prompt equals P0's is not re-run - same prompt, same seed.
Outputs refs/{g}__p2_{arm}raw.jpg and refs/{g}__p2_{arm}.jpg; _v33_p2_prompts.json.
"""
import csv
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import v3lib as L  # noqa: E402
from run_v33_pose import PERSON_CLAUSE  # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
META = os.path.join(RUN, "_v33_p2_prompts.json")

SWAP = ("Replace this person's head with a smooth, featureless mannequin head of the same "
        "size, in the same position and facing the same way - no face, no hair.")
KEEP = " Keep the clothing, the body, the hands and the background exactly as they are."

FEET = {"full_body": " Both feet flat on the ground, side by side, toes pointing straight "
                     "at the camera.",
        "knee_up": " Both legs straight, knees pointing at the camera."}
HIPS = {k: " Hips square to the camera, weight even on both legs, legs straight."
        for k in ("full_body", "knee_up", "waist_up")}
NOPOSE = {"full_body": " No turned feet, no bent knee, no twist in the hips."}

REGION = {
    "M1_neckup": ("Replace this person's head, from the neck up, with a smooth, featureless "
                  "mannequin head of the same size, in the same position and facing the "
                  "same way - no face, no hair."),
    "M2_faceonly": ("Replace only this person's face with a smooth, featureless mannequin "
                    "face, and remove the hair; the neck is unchanged."),
    "M3_skinkept": SWAP + (" The skin of the neck, the arms and the hands stays exactly as "
                           "photographed - the same colour and texture."),
    "M4_no": SWAP + " No mannequin material on the neck, the arms or the hands.",
}
ARMS = ["P0", "P1_feet", "P2_hips", "P3_no", "M1_neckup", "M2_faceonly", "M3_skinkept", "M4_no"]


def build(arm, fr):
    pose = PERSON_CLAUSE[fr]
    if arm == "P0":
        return SWAP + KEEP + pose
    if arm == "P1_feet":
        return SWAP + KEEP + pose + FEET.get(fr, "")
    if arm == "P2_hips":
        return SWAP + KEEP + pose + HIPS.get(fr, "")
    if arm == "P3_no":
        return SWAP + KEEP + pose + NOPOSE.get(fr, "")
    return REGION[arm] + KEEP + pose


def recrop(bgr, pad=0.04, thr=245):
    """bbox of the non-white region on the white ground the A4 crop supplies. 40 ms, no matte."""
    m = (bgr < thr).any(axis=2)
    ys, xs = np.where(m)
    if len(ys) < 20:
        return bgr
    h, w = bgr.shape[:2]
    py, px = int(h * pad), int(w * pad)
    return bgr[max(0, ys.min() - py):min(h, ys.max() + py),
               max(0, xs.min() - px):min(w, xs.max() + px)]


def load_env():
    for line in open(os.path.join(REPO, ".env")):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main():
    load_env()
    L.MODEL_DIR = os.path.join(REPO, "v2", "runs", ".models")
    paths = L.fetch_models(verbose=False)
    rows = list(csv.DictReader(open(os.path.join(REPO, "v3/testsets/v30_matrix_b.csv"))))
    meta = json.load(open(META)) if os.path.exists(META) else {}
    jobs, skipped = [], 0
    for r in rows:
        g = r["garment"]
        crop = cv2.imread(os.path.join(RUN, "inputs", f"{g}__A4.jpg"))
        fr = L.framing(crop, paths)["framing"]
        p0 = build("P0", fr)
        for arm in ARMS:
            prompt = build(arm, fr)
            same = arm != "P0" and prompt == p0
            meta[f"{g}|{arm}"] = {"prompt": prompt, "framing": fr, "same_as_P0": same,
                                  "endpoint": L.KLEIN, "seed": L.SEED}
            if same:
                skipped += 1
                continue
            out = os.path.join(RUN, "refs", f"{g}__p2_{arm}raw.jpg")
            if os.path.exists(out):
                continue
            jobs.append((out, (lambda b=crop, q=prompt: L.call(
                L.KLEIN, {"image_urls": [L.b64(b)], "prompt": q, "seed": L.SEED}))))
    json.dump(meta, open(META, "w"), indent=1)
    print(f"{len(rows)} refs x {len(ARMS)} arms, {len(jobs)} klein calls, "
          f"{skipped} cells identical to P0 not re-run", flush=True)
    with ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(fn): out for out, fn in jobs}
        for f in as_completed(futs):
            try:
                cv2.imwrite(futs[f], f.result(), [cv2.IMWRITE_JPEG_QUALITY, 95])
                print("  ok  ", os.path.basename(futs[f]), flush=True)
            except Exception as e:
                print("  FAIL", os.path.basename(futs[f]), str(e)[:100], flush=True)
                if "balance" in str(e).lower():
                    break
    n = 0
    for r in rows:
        for arm in ARMS:
            g = r["garment"]
            raw = os.path.join(RUN, "refs", f"{g}__p2_{arm}raw.jpg")
            out = os.path.join(RUN, "refs", f"{g}__p2_{arm}.jpg")
            if os.path.exists(raw) and not os.path.exists(out):
                cv2.imwrite(out, recrop(cv2.imread(raw)), [cv2.IMWRITE_JPEG_QUALITY, 95])
                n += 1
    print(f"re-cropped {n}\ndone")


if __name__ == "__main__":
    main()
