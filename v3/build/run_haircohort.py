"""The high-hair-damage cohort, through cropping and Qwen extraction.

These six references are the ones V2 measured as worst for hair falling over the garment
- the cohort BC_klein's whole bald pass exists to handle. They have never been through
the regeneration path, because run B's fold put them on the person side or left them out.

  hair_over_garment, from V2:  p021 19.5%  p023 16.9%  zendaya 14.4%
                               p019 13.5%  p028 11.9%  p009 7.2%

Three inputs per reference, prompt held at p7.3.1 (the adopted minimum):

  raw     the photograph, as everything so far has been given
  CROPB   background removed, head kept
  CROPH   background AND head removed - the PHEAD-style cut

CROPH is the direct question. On a subtractive consumer the head cut is what produces
the jagged boundary klein copies. On a regenerative consumer it may simply remove the
hair problem at no cost. Nobody has run it.
"""
import csv
import json
import os
import sys

import cv2
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v2", "build"))
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import garment_crop as G      # noqa: E402
import phase3_fal as F        # noqa: E402
import phase3_variants as PV  # noqa: E402
import run_phase3 as R3       # noqa: E402
import skin_tone as S         # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
QWEN = "fal-ai/qwen-image-edit-2511"
SEED = 46
MAXPIX = 1_150_000

# (garment reference, V2 hair_over_garment, paired person for the colour read)
COHORT = [("p021", "19.5%", "p001"),
          ("p023", "16.9%", "p002"),
          ("dualuse_zendaya_white_blazer_skirt", "14.4%", "p004"),
          ("p019", "13.5%", "p005"),
          ("p028", "11.9%", "p007"),
          ("p009", "7.2%", "p008")]


def norm_in(stem):
    """Bring a test_set3 image into the run at the same 1 MP normalisation."""
    dst = os.path.join(RUN, "inputs", f"{stem}.jpg")
    if os.path.exists(dst):
        return dst
    src = None
    for r in csv.DictReader(open(os.path.join(REPO, "test_set3", "manifest.csv"))):
        if r["id"] == stem:
            src = os.path.join(REPO, r["path"])
    if not src:
        raise SystemExit(f"{stem} not in test_set3")
    im = cv2.imread(src)
    h, w = im.shape[:2]
    if h * w > MAXPIX:
        k = (MAXPIX / (h * w)) ** 0.5
        im = cv2.resize(im, (int(w * k), int(h * k)), interpolation=cv2.INTER_AREA)
    G.write_rgb(dst, im)
    return dst


def crops(stem):
    outb = os.path.join(RUN, "inputs", f"{stem}__CROPB.jpg")
    outh = os.path.join(RUN, "inputs", f"{stem}__CROPH.jpg")
    if os.path.exists(outb) and os.path.exists(outh):
        return
    img = cv2.imread(os.path.join(RUN, "inputs", f"{stem}.jpg"))
    M = PV.masks(img, f"v30_{stem}", cranium=False)
    x0, y0, x1, y1 = G.bbox_of((M["subject"] > 0.5).astype(np.uint8), img.shape[:2])
    G.write_rgb(outb, PV.flatten(img[y0:y1, x0:x1], M["subject"][y0:y1, x0:x1], PV.WHITE))
    G.write_rgb(outh, PV.flatten(img[y0:y1, x0:x1], M["noface"][y0:y1, x0:x1], PV.WHITE))
    print(f"  crop {stem}", flush=True)


def main():
    F._load_env()
    for stem, _, person in COHORT:
        norm_in(stem)
        norm_in(person)
        crops(stem)
    if "--crops-only" in sys.argv:
        return

    log, jobs = {}, []
    for stem, hair, person in COHORT:
        t = S.tone(cv2.imread(os.path.join(RUN, "inputs", f"{person}.jpg")))
        colour = t["name"] if t else "beige skin"
        for tag, suffix in (("raw", ""), ("CROPB", "__CROPB"), ("CROPH", "__CROPH")):
            src = os.path.join(RUN, "inputs", f"{stem}{suffix}.jpg")
            fr = S.framing(cv2.imread(src))["framing"]
            prompt = (f"This person's outfit on a {colour} mannequin, "
                      f"{R3.EXTENT_WORD[fr]}, on a plain white background.")
            key = f"{stem}|hc.{tag}"
            log[key] = {"prompt": prompt, "colour": colour, "framing": fr,
                        "hair": hair, "person": person, "input": tag}
            if not os.path.exists(os.path.join(RUN, "refs", f"{stem}__hc.{tag}.jpg")):
                jobs.append((key, prompt, src))
    json.dump(log, open(os.path.join(RUN, "_haircohort_prompts.json"), "w"), indent=1)
    print(f"{len(COHORT)} references x 3 inputs, {len(jobs)} to run")
    if "--dry" in sys.argv or not jobs:
        return
    res = F.run([(k, (lambda pr=p, gp=gp: F.call(
        QWEN, {"image_urls": [F._b64(cv2.imread(gp))], "prompt": pr, "seed": SEED})))
        for k, p, gp in jobs], 6)
    for k, v in res.items():
        if v is not None:
            G.write_rgb(os.path.join(RUN, "refs", f"{k.replace('|', '__')}.jpg"), v)
    print(f"\n{sum(1 for v in res.values() if v is not None)}/{len(jobs)} written")


if __name__ == "__main__":
    main()
