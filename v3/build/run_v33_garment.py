"""v3.3 link 1.1: klein extraction WITHOUT the mannequin - the whole outfit, no body.

Reviewer verdict on link 1: the klein mannequins are poor. Hypothesis: a 4B distilled
model has not the capacity to render a plausible body AND hold the garment, so ask it
for only the garment. Four wordings, one probe cohort, same A4 crop, same seed.

  k1 ghost    the outfit as worn by an invisible body (ghost-mannequin product shot)
  k2 flat     every piece laid flat, arranged as worn
  k3 minimal  the p7.3.1-style irreducible prompt, ~25 words
  k4 qx       v3.1's QX prompt verbatim - the control against refs/{g}__QX.jpg (Qwen)
  k5 form     an INVISIBLE mannequin form - body context kept, no body rendered. Carries
              the v3.1 pose clause too, since a form has a pose
  k1_noext    k1 with NO extent sentence - the ablation for the framing reader

k2 and k3 failed on the 8-reference probe and are not run further; k1, k4, k5 and
k1_noext run on all 28 references of the run-B fold.

Extent is still read from the crop: a garment-only prompt against a waist-up crop can
invent trousers just as a mannequin one can (v3.1 link 3 B), so each variant carries one
grounded sentence naming what the photograph shows. Never name a piece the crop excludes.
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
META = os.path.join(RUN, "_v33_garment_prompts.json")

COHORT = ["dualuse_queen_latifah_gown_stage",
          "dualuse_scarlett_johansson_black_dress_backview_night",
          "dualuse_lp_beige_long_coat_menswear", "g015", "g030",          # link 1 failures
          "g027", "g018", "dualuse_gal_gadot_blue_dress_redcarpet"]        # link 1 parity

EXTENT = {
    "full_body": " The photograph shows the person from head to feet, so every piece "
                 "including footwear is shown.",
    "knee_up": " The photograph shows the person from the head to the knee only; show "
               "only the pieces visible in it, ending where it ends.",
    "waist_up": " The photograph shows the person from the head to the hip only; show "
                "only the pieces visible in it, ending where it ends.",
    "chest_up": " The photograph shows the person from the head to the chest only; show "
                "only the pieces visible in it, ending where it ends.",
    "unknown": " Show only the pieces the photograph shows.",
}

PROMPTS = {
    "k1_ghost": ("Show only this person's clothes, against pure white, as if worn by an "
                 "invisible body: every piece keeps the shape, drape and position it has "
                 "on the person, and the person themself is gone - no face, no skin, no "
                 "hair. Copy each piece exactly - the same colour, print, texture and cut. "
                 "Only what the person is actually wearing: if they are not carrying a "
                 "bag, there is no bag."),
    "k2_flat": ("Lay every piece of this person's outfit flat on pure white, arranged as "
                "it is worn - top above bottom, each piece whole and separate, nothing "
                "overlapping. The person is gone. Copy each piece exactly - the same "
                "colour, print, texture and cut. Only the pieces the person is actually "
                "wearing."),
    "k3_minimal": ("This person's whole outfit on pure white, no person. Every piece "
                   "exactly as photographed: same colour, print, texture and cut."),
    "k4_qx": L.QX_PROMPT,
    "k5_form": ("Show this person's outfit worn by an invisible mannequin against pure "
                "white: the clothes hold the shape of a body - shoulders, chest, waist, "
                "hips - but the mannequin itself cannot be seen, so the collar, cuffs "
                "and hem open onto nothing. The person is gone - no face, no skin, no "
                "hair. Every piece the person is actually wearing, exactly as they wear "
                "it, keeping its shape and drape; copy each piece exactly - the same "
                "colour, print, texture and cut. Only what the person is wearing: if "
                "they are not carrying a bag, there is no bag."),
    "k1_noext": None,   # k1 wording, no extent sentence
    # k6: k1's drape wording plus the body's absence stated CONCRETELY, the way the bag
    # guard is - k1 leaked exposed limbs on 9/28 (legs under dresses, hands) and k4,
    # which says "remove the person entirely", leaked none.
    "k6_ghost2": ("Show only this person's clothes, against pure white, as if worn by an "
                  "invisible body: every piece keeps the shape and drape it has on the "
                  "person. The body is entirely invisible - where a sleeve ends there is "
                  "no hand, where a hem ends there is no leg and no foot, at the collar "
                  "there is no neck, no face and no hair; where the clothes end there is "
                  "only white. Copy each piece exactly - the same colour, print, texture "
                  "and cut. Only what the person is actually wearing: if they are not "
                  "carrying a bag, there is no bag."),
}
PROMPTS["k1_noext"] = PROMPTS["k1_ghost"]
# k5 has a form with a pose, so it takes v3.1's own dynamic clause (extent + pose
# from one table) with the noun swapped - the same rule: never name a part the crop
# excludes.
FORM_CLAUSE = {k: v.replace("mannequin", "form") for k, v in L.FRAME_CLAUSE.items()}
PROBE_ONLY = {"k2_flat", "k3_minimal"}


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
    meta = json.load(open(META)) if os.path.exists(META) else {}
    jobs = []
    allg = sorted({r["garment"] for r in csv.DictReader(open(
        os.path.join(REPO, "v3/testsets/v30_matrix_b.csv")))})
    for g in allg:
        crop = cv2.imread(os.path.join(RUN, "inputs", f"{g}__A4.jpg"))
        fr = L.framing(crop, paths)["framing"]
        for k, base in PROMPTS.items():
            if k in PROBE_ONLY and g not in COHORT:
                continue
            tail = ("" if k in ("k4_qx", "k1_noext") else
                    FORM_CLAUSE[fr] if k == "k5_form" else EXTENT[fr])
            prompt = base + tail
            meta[f"{g}|{k}"] = {"prompt": prompt, "framing": fr, "endpoint": L.KLEIN,
                                "seed": L.SEED}
            out = os.path.join(RUN, "refs", f"{g}__{k}.jpg")
            if os.path.exists(out):
                continue
            jobs.append((out, (lambda c=crop, q=prompt: L.call(
                L.KLEIN, {"image_urls": [L.b64(c)], "prompt": q, "seed": L.SEED}))))
    json.dump(meta, open(META, "w"), indent=1)
    print(f"{len(allg)} refs, {len(jobs)} calls", flush=True)
    fails = 0
    with ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(fn): out for out, fn in jobs}
        for f in as_completed(futs):
            try:
                cv2.imwrite(futs[f], f.result(), [cv2.IMWRITE_JPEG_QUALITY, 95])
                print("  ok  ", os.path.basename(futs[f]), flush=True)
            except Exception as e:
                fails += 1
                print("  FAIL", os.path.basename(futs[f]), str(e)[:100], flush=True)
                if "balance" in str(e).lower():
                    break
    print(f"done: {len(jobs)-fails} made, {fails} failed")


if __name__ == "__main__":
    main()
