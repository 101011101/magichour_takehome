"""v3.3 link 1.4: can klein re-pose the person inside the head-swap edit?

Four arms on the raw normalised photograph, each followed by the A4 crop:

  MH_pose    head swap + a CONSTANT pose sentence (names feet regardless of the crop)
  MH_posefr  head swap + pose AND extent from one table keyed on the framing read -
             v3.1's FRAME_CLAUSE rewritten for a person; never name a part the crop excludes
  MH_fr      head swap + the extent sentence only, no pose word
  MH_col     head swap alone, the head given the tone reader's colour for the paired person

Outputs refs/{g}__{arm}raw.jpg (klein) and refs/{g}__{arm}.jpg (A4 crop).
Prompts as sent: _v33_pose_prompts.json. Resumable.
"""
import csv
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
import v3lib as L  # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
META = os.path.join(RUN, "_v33_pose_prompts.json")

HEAD = ("Replace this person's head with a smooth, featureless {head} of the same size, "
        "in the same position and facing the same way - no face, no hair.")
KEEP_ALL = " Keep the clothing, the body, the hands, the pose and the background exactly as they are."
KEEP_NOPOSE = " Keep the clothing, the body, the hands and the background exactly as they are."

POSE_CONST = (" Change the pose: the person stands upright in a neutral pose, facing forward, "
              "arms relaxed at the sides, feet together.")
# pose + extent from ONE read. Never name a body part the crop excludes.
PERSON_CLAUSE = {
    "full_body": (" Change the pose: the person stands upright in a neutral pose, facing "
                  "forward, arms relaxed at the sides, feet together. The photograph shows "
                  "them from head to feet; keep that framing."),
    "knee_up": (" Change the pose: the person stands upright in a neutral pose, facing "
                "forward, arms relaxed at the sides, legs together. The photograph shows "
                "them from the head to the knee only; keep exactly that framing, cut off "
                "below the knee."),
    "waist_up": (" Change the pose: the person stands upright and square to the camera, "
                 "shoulders level, arms relaxed at the sides. The photograph shows them "
                 "from the head to the hip only; keep exactly that framing, cut off below "
                 "the hip."),
    # phase 7 (2026-08-29): "arms down" added - the only row that said nothing about the
    # arms, and p030's raised arms stayed raised under it.
    "chest_up": (" Change the pose: the person faces the camera squarely, shoulders level, "
                 "arms down, relaxed at the sides. The photograph shows them from the head "
                 "to the chest only; keep exactly that framing, cut off below the chest."),
    "unknown": (" Change the pose: the person stands upright and square to the camera. "
                "Keep exactly the framing the photograph has."),
}
EXTENT = {
    "full_body": " The photograph shows the person from head to feet; keep that framing.",
    "knee_up": " The photograph shows the person from the head to the knee only; keep exactly that framing, cut off below the knee.",
    "waist_up": " The photograph shows the person from the head to the hip only; keep exactly that framing, cut off below the hip.",
    "chest_up": " The photograph shows the person from the head to the chest only; keep exactly that framing, cut off below the chest.",
    "unknown": " Keep exactly the framing the photograph has.",
}
ARMS = ["MH_pose", "MH_posefr", "MH_fr", "MH_col"]


def build(arm, fr, colour):
    if arm == "MH_pose":
        return HEAD.format(head="mannequin head") + KEEP_NOPOSE + POSE_CONST
    if arm == "MH_posefr":
        return HEAD.format(head="mannequin head") + KEEP_NOPOSE + PERSON_CLAUSE[fr]
    if arm == "MH_fr":
        return HEAD.format(head="mannequin head") + KEEP_ALL + EXTENT[fr]
    if arm == "MH_col":
        return HEAD.format(head=f"{colour} mannequin head") + KEEP_ALL
    raise KeyError(arm)


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
    jobs = []
    for r in rows:
        g, p = r["garment"], r["person"]
        img = cv2.imread(os.path.join(RUN, "inputs", f"{g}.jpg"))
        fr = L.framing(img, paths)["framing"]
        t = L.tone(cv2.imread(os.path.join(RUN, "inputs", f"{p}.jpg")), paths)
        colour = t["name"] if t else "beige skin"
        for arm in ARMS:
            prompt = build(arm, fr, colour)
            meta[f"{g}|{arm}"] = {"prompt": prompt, "framing": fr, "colour": colour,
                                  "person": p, "endpoint": L.KLEIN, "seed": L.SEED}
            out = os.path.join(RUN, "refs", f"{g}__{arm}raw.jpg")
            if os.path.exists(out):
                continue
            jobs.append((out, (lambda b=img, q=prompt: L.call(
                L.KLEIN, {"image_urls": [L.b64(b)], "prompt": q, "seed": L.SEED}))))
    json.dump(meta, open(META, "w"), indent=1)
    print(f"{len(rows)} refs x {len(ARMS)} arms, {len(jobs)} klein calls", flush=True)
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
    for r in rows:
        for arm in ARMS:
            g = r["garment"]
            out = os.path.join(RUN, "refs", f"{g}__{arm}.jpg")
            raw = os.path.join(RUN, "refs", f"{g}__{arm}raw.jpg")
            if os.path.exists(out) or not os.path.exists(raw):
                continue
            cv2.imwrite(out, L.crop_a4(cv2.imread(raw), paths), [cv2.IMWRITE_JPEG_QUALITY, 95])
            print("  crop", g, arm, flush=True)
    print("done")


if __name__ == "__main__":
    main()
