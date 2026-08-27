"""Run the p7.1 (framing) and p7.2 (colour) probes.

Prompts are built by concatenation, which is the whole point of the design:

    PREFIX + <one word> + SUFFIX

so the only thing that changes between arms of p7.2 is a single colour word, and the
only thing that changes between arms of p7.1 is one sentence about extent. Nothing else
in the wording moves, so a difference between arms is attributable to that word.

p7.1  framing   .1 self-limiting sentence, no CPU
                .2 mirror-the-crop sentence, no CPU
                .3 CPU pose reader injects the extent term
p7.2  colour    .white .grey  fixed, no CPU
                .matched      CPU skin reader on the PAIRED PERSON
                .contrast     furthest of the eight tone words from the garment

Probe cohort is 8 references chosen because they carry the defects, not at random.
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
import garment_crop as G          # noqa: E402
import phase3_fal as F            # noqa: E402
import skin_tone as S             # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
QWEN = "fal-ai/qwen-image-edit-2511"
SEED = 46

# p7 split at the one word that p7.2 varies.
PREFIX = "Show this person's outfit on a "
# The colour word is optional. Concatenating "" into the slot leaves "on a mannequin";
# concatenating "tan" leaves "on a tan mannequin". The first version of this file passed
# the literal word "mannequin" into the slot for the p7.1 arms and produced
# "on a mannequin mannequin" in all 24 of them - see RESULTS 3c.5.
SUFFIX = ("mannequin against pure white. The mannequin wears every piece the person is "
          "actually wearing, exactly as they wear it, keeping its shape and drape - and "
          "the person themself is gone, no face, no skin, no hair. Copy each piece "
          "exactly - the same colour, print, texture and cut. The mannequin wears only "
          "what the person is wearing and nothing else: if they are not carrying a bag, "
          "there is no bag.")

FRAME_EXTRA = {
    "p7.1.1": (" Show only the part of the body that the photograph shows. If the "
               "photograph stops at the waist, the mannequin stops at the waist. Do not "
               "continue the body below where the photograph ends."),
    "p7.1.2": (" Frame the mannequin exactly as the person is framed in the photograph - "
               "the same crop, the same part of the body, nothing beyond it."),
    # .3 is the same shape of sentence as .1 and .2, but the extent word comes from the
    # CPU pose reader instead of being left to the model. Injected as a trailing clause,
    # not into the noun slot - putting it in the noun slot produced "a mannequin shown
    # from the head to the chest ... mannequin against pure white".
    "p7.1.3": None,
}
FRAME_SENTENCE = {
    "full_body": " Show the whole mannequin, head to feet.",
    "knee_up": " Show the mannequin from the head to the knee only, cut off below the knee.",
    "waist_up": " Show the mannequin from the head to the hip only, cut off below the hip.",
    "chest_up": " Show the mannequin from the head to the chest only, cut off below the chest.",
    "unknown": " Show only the part of the body that the photograph shows.",
}

PROBE = ["p029", "p030", "dualuse_emma_watson_black_blazer_armscrossed",
         "g013", "g015", "g029", "dualuse_man_black_suit_studio_nonceleb", "g024"]


def tone_of(path):
    t = S.tone(cv2.imread(path))
    return t["name"] if t else None


def contrast_word(garment_bgr):
    """Furthest tone word from the garment's own median lightness."""
    g = cv2.cvtColor(garment_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    m = cv2.cvtColor(garment_bgr, cv2.COLOR_BGR2GRAY) < 244
    if m.sum() < 200:
        return "grey"
    L = float(np.median(g[..., 0][m])) * 100.0 / 255.0
    return max(S.TONES, key=lambda t: abs(t[1] - L))[0]


def build(rows):
    jobs, log = [], {}
    for r in rows:
        g, person = r["garment"], r["person"]
        gpath = os.path.join(RUN, "inputs", f"{g}.jpg")
        ppath = os.path.join(RUN, "inputs", f"{person}.jpg")

        # ---- p7.1: framing --------------------------------------------
        fr = S.framing(cv2.imread(gpath))
        for tag, extra in FRAME_EXTRA.items():
            if extra is None:
                extra = FRAME_SENTENCE[fr["framing"]]
            prompt = PREFIX + SUFFIX + extra
            log[f"{g}|{tag}"] = {"prompt": prompt, "framing_read": fr}
            jobs.append((f"{g}|{tag}", prompt, gpath))

        # ---- p7.2a: bare colour adjective ------------------------------
        # Run first. "tan" turned a white shirt into a tan polo - the model reads the
        # adjective as applying to the picture, not to the mannequin. Kept for the
        # comparison; see RESULTS 3c.3.
        matched = tone_of(ppath) or "grey"
        contrast = contrast_word(cv2.imread(gpath))
        for tag, word in (("p7.2.white", "white"), ("p7.2.grey", "grey"),
                          ("p7.2.matched", matched), ("p7.2.contrast", contrast)):
            prompt = PREFIX + word + " " + SUFFIX
            log[f"{g}|{tag}"] = {"prompt": prompt, "colour": word, "phrasing": "bare",
                                 "person": person, "matched_from": matched,
                                 "contrast_pick": contrast}
            jobs.append((f"{g}|{tag}", prompt, gpath))

        # ---- p7.2b: the colour qualified as SKIN ------------------------
        # The binding test. If "tan" leaks because the adjective is loose, then naming
        # what the colour belongs to - the mannequin's skin - should keep it there.
        # "grey" stays bare: a grey mannequin is a material, not a complexion.
        for word in ("white skin", "beige skin", "tan skin", "black skin", "grey"):
            tag = "p7.2b." + word.split()[0]
            prompt = PREFIX + word + " " + SUFFIX
            log[f"{g}|{tag}"] = {"prompt": prompt, "colour": word,
                                 "phrasing": "skin-qualified", "person": person}
            jobs.append((f"{g}|{tag}", prompt, gpath))
    return jobs, log


def main():
    F._load_env()
    rows = [r for r in csv.DictReader(open(os.path.join(
        REPO, "v3/testsets/v30_matrix_b.csv"))) if r["garment"] in PROBE]
    jobs, log = build(rows)
    todo = [(k, p, g) for k, p, g in jobs
            if not os.path.exists(os.path.join(RUN, "refs", f"{k.replace('|', '__')}.jpg"))]
    print(f"{len(rows)} references x {len(jobs)//len(rows)} arms = {len(jobs)} total, "
          f"{len(todo)} to run")
    json.dump(log, open(os.path.join(RUN, "_p7n_prompts.json"), "w"), indent=1)
    if "--dry" in sys.argv or not todo:
        return
    res = F.run([(k, (lambda pr=p, gp=g: F.call(
        QWEN, {"image_urls": [F._b64(cv2.imread(gp))], "prompt": pr, "seed": SEED})))
        for k, p, g in todo], 6)
    for k, v in res.items():
        if v is not None:
            G.write_rgb(os.path.join(RUN, "refs", f"{k.replace('|', '__')}.jpg"), v)
    print(f"\n{sum(1 for v in res.values() if v is not None)}/{len(todo)} written")


if __name__ == "__main__":
    main()
