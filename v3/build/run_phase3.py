"""Phase 3: the minimum prompt, and cropping the input before extraction.

Two experiments, deliberately separate:

  p7.3.n   prompt ladder built from first principles. Starts with the three
           irreducible requirements and adds one clause at a time. Negation-free
           except for the control, because every first-party source says to write
           positives and Qwen's own rewriter forbids negation words.

  CROPB    background removed, subject whole, head kept
  CROPH    background removed and head removed - the PHEAD-style cut
           Both hold the prompt fixed, so the input is the only variable.

The crops share one mask computation per reference: BiRefNet at 1024 is the expensive
stage (~60 s) and both variants are derived from the same alpha.
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
import garment_crop as G     # noqa: E402
import phase3_fal as F       # noqa: E402
import phase3_variants as PV  # noqa: E402
import run_p7n as P          # noqa: E402
import skin_tone as S        # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
QWEN = "fal-ai/qwen-image-edit-2511"
SEED = 46


def ladder(colour, extent_word, extent_sentence):
    """Each level is the one before plus one clause, except .6 which is the control.

    extent_word    goes inside the noun phrase   e.g. "waist-up"
    extent_sentence the p7.1.3 clause, used only by the control
    """
    base = (f"This person's outfit on a {colour} mannequin, {extent_word}, "
            "on a plain white background.")
    fid = " Each garment keeps its own colour, print, texture and cut."
    face = " The mannequin is smooth and featureless."
    every = " The mannequin wears every garment the person wears, drawn as they wear it."
    return {
        "p7.3.1": base,
        "p7.3.2": base + fid,
        "p7.3.3": base + fid + face,
        "p7.3.4": base + fid + face + every,
        # .5 - the whole of p7.3, every negation turned positive
        "p7.3.5": (f"This person's outfit on a {colour} mannequin, {extent_word}, on a "
                   "plain white background. The mannequin is smooth and featureless, and "
                   "wears every garment the person wears, drawn as they wear it, keeping "
                   "its shape and drape. Each garment keeps its own colour, print, "
                   "texture and cut. The mannequin wears exactly the garments in the "
                   "photograph."),
        # .6 - current p7.3, unchanged, negations and all
        "p7.3.6": (P.PREFIX + colour + " " + P.SUFFIX + extent_sentence),
    }


EXTENT_WORD = {
    "full_body": "shown full length",
    "knee_up": "shown from the head to the knee",
    "waist_up": "shown from the head to the hip",
    "chest_up": "shown from the head to the chest",
    "unknown": "shown as the photograph frames the person",
}


def crops():
    """CROPB and CROPH from one mask pass per reference. Pure CPU."""
    made = []
    for g in P.PROBE:
        outb = os.path.join(RUN, "inputs", f"{g}__CROPB.jpg")
        outh = os.path.join(RUN, "inputs", f"{g}__CROPH.jpg")
        if os.path.exists(outb) and os.path.exists(outh):
            continue
        img = cv2.imread(os.path.join(RUN, "inputs", f"{g}.jpg"))
        M = PV.masks(img, f"v30_{g}", cranium=False)
        x0, y0, x1, y1 = G.bbox_of((M["subject"] > 0.5).astype(np.uint8), img.shape[:2])
        G.write_rgb(outb, PV.flatten(img[y0:y1, x0:x1],
                                     M["subject"][y0:y1, x0:x1], PV.WHITE))
        G.write_rgb(outh, PV.flatten(img[y0:y1, x0:x1],
                                     M["noface"][y0:y1, x0:x1], PV.WHITE))
        made.append(g)
        print(f"  crop {g}", flush=True)
    return made


def main():
    F._load_env()
    if "--crops-only" in sys.argv:
        crops()
        return
    crops()
    rows = [r for r in csv.DictReader(open(os.path.join(
        REPO, "v3/testsets/v30_matrix_b.csv"))) if r["garment"] in P.PROBE]
    log, jobs = {}, []
    for r in rows:
        g, person = r["garment"], r["person"]
        gp = os.path.join(RUN, "inputs", f"{g}.jpg")
        t = S.tone(cv2.imread(os.path.join(RUN, "inputs", f"{person}.jpg")))
        colour = t["name"] if t else "beige skin"
        fr = S.framing(cv2.imread(gp))["framing"]
        L = ladder(colour, EXTENT_WORD[fr], P.FRAME_SENTENCE[fr])

        for tag, prompt in L.items():
            log[f"{g}|{tag}"] = {"prompt": prompt, "words": len(prompt.split()),
                                 "colour": colour, "framing": fr, "input": "raw"}
            jobs.append((f"{g}|{tag}", prompt, gp))

        # crop arms: prompt held at p7.3, input varies
        for tag, suffix in (("CROPB", "__CROPB"), ("CROPH", "__CROPH")):
            src = os.path.join(RUN, "inputs", f"{g}{suffix}.jpg")
            if not os.path.exists(src):
                continue
            prompt = L["p7.3.6"]
            log[f"{g}|p7.3.{tag}"] = {"prompt": prompt, "words": len(prompt.split()),
                                      "colour": colour, "framing": fr, "input": tag}
            jobs.append((f"{g}|p7.3.{tag}", prompt, src))

    json.dump(log, open(os.path.join(RUN, "_phase3_prompts.json"), "w"), indent=1)
    todo = [(k, p, gp) for k, p, gp in jobs
            if not os.path.exists(os.path.join(RUN, "refs", f"{k.replace('|', '__')}.jpg"))]
    w = sorted({(v["words"], k.split("|")[1]) for k, v in log.items()})
    print("words: " + " · ".join(f"{t} {n}" for n, t in
                                 sorted({(k.split('|')[1], v['words'])
                                         for k, v in log.items()})))
    print(f"{len(jobs)} arms, {len(todo)} to run")
    if "--dry" in sys.argv or not todo:
        return
    res = F.run([(k, (lambda pr=p, gp=gp: F.call(
        QWEN, {"image_urls": [F._b64(cv2.imread(gp))], "prompt": pr, "seed": SEED})))
        for k, p, gp in todo], 6)
    for k, v in res.items():
        if v is not None:
            G.write_rgb(os.path.join(RUN, "refs", f"{k.replace('|', '__')}.jpg"), v)
    print(f"\n{sum(1 for v in res.values() if v is not None)}/{len(todo)} written")


if __name__ == "__main__":
    main()
