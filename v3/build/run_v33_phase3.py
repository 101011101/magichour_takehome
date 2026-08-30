"""v3.3 phase 3: pose wording on the M1 baseline, garment held through the re-pose.

Template: A4 crop -> klein (M1 head swap + PERSON_CLAUSE[framing] + one sentence) ->
bbox re-crop. Q0 is phase 2's M1 cell (not re-run). Each sentence fires only where the
part it names is in frame; a cell equal to Q0's prompt is not re-run.
"""
import csv
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import v3lib as L  # noqa: E402
from run_v33_pose import PERSON_CLAUSE  # noqa: E402
from run_v33_phase2 import REGION, KEEP, recrop, load_env  # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
META = os.path.join(RUN, "_v33_p3_prompts.json")
M1 = REGION["M1_neckup"]
LOWER = ("full_body", "knee_up")
LEGS = " Legs straight."
GARMENT_HEM = (" Every garment keeps its shape through the change of pose: a dress stays a "
               "dress, a skirt stays a skirt, its hem hanging as one piece.")
GARMENT_ALL = (" The clothing stays exactly the same through the change of pose - the same "
               "pieces, the same shape, the same length.")
FEET = " Feet point towards the camera."
ARMS = ["Q0", "Q1_legs", "Q2_legsgarment", "Q3_garment", "Q4_feet", "Q5_all"]


def build(arm, fr):
    base = M1 + KEEP + PERSON_CLAUSE[fr]
    if arm == "Q1_legs":
        return base + (LEGS if fr in LOWER else "")
    if arm == "Q2_legsgarment":
        return base + (LEGS + GARMENT_HEM if fr in LOWER else "")
    if arm == "Q3_garment":
        return base + GARMENT_ALL
    if arm == "Q4_feet":
        return base + (FEET if fr == "full_body" else "")
    if arm == "Q5_all":
        return base + (LEGS + GARMENT_HEM + (FEET if fr == "full_body" else "")
                       if fr in LOWER else "")
    return base


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
        q0 = build("Q0", fr)
        for arm in ARMS:
            prompt = build(arm, fr)
            same = arm != "Q0" and prompt == q0
            meta[f"{g}|{arm}"] = {"prompt": prompt, "framing": fr, "same_as_Q0": same,
                                  "endpoint": L.KLEIN, "seed": L.SEED}
            if arm == "Q0":
                # phase 2's M1 cell, copied under the phase-3 name so the page is uniform
                for suf in ("raw", ""):
                    src = os.path.join(RUN, "refs", f"{g}__p2_M1_neckup{suf}.jpg")
                    dst = os.path.join(RUN, "refs", f"{g}__p3_Q0{suf}.jpg")
                    if not os.path.exists(dst):
                        cv2.imwrite(dst, cv2.imread(src), [cv2.IMWRITE_JPEG_QUALITY, 95])
                continue
            if same:
                skipped += 1
                continue
            out = os.path.join(RUN, "refs", f"{g}__p3_{arm}raw.jpg")
            if os.path.exists(out):
                continue
            jobs.append((out, (lambda b=crop, q=prompt: L.call(
                L.KLEIN, {"image_urls": [L.b64(b)], "prompt": q, "seed": L.SEED}))))
    json.dump(meta, open(META, "w"), indent=1)
    print(f"{len(rows)} refs x {len(ARMS)} arms, {len(jobs)} klein calls, {skipped} = Q0", flush=True)
    with ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(fn): out for out, fn in jobs}
        for f in as_completed(futs):
            try:
                im = f.result()
                cv2.imwrite(futs[f], im, [cv2.IMWRITE_JPEG_QUALITY, 95])
                print("  ok  ", os.path.basename(futs[f]), "BLACK" if im.mean() < 5 else "", flush=True)
            except Exception as e:
                print("  FAIL", os.path.basename(futs[f]), str(e)[:100], flush=True)
                if "balance" in str(e).lower():
                    break
    n = 0
    for r in rows:
        for arm in ARMS:
            g = r["garment"]
            raw = os.path.join(RUN, "refs", f"{g}__p3_{arm}raw.jpg")
            out = os.path.join(RUN, "refs", f"{g}__p3_{arm}.jpg")
            if os.path.exists(raw) and not os.path.exists(out):
                cv2.imwrite(out, recrop(cv2.imread(raw)), [cv2.IMWRITE_JPEG_QUALITY, 95])
                n += 1
    print(f"re-cropped {n}\ndone")


if __name__ == "__main__":
    main()
