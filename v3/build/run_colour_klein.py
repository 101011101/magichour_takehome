"""Does the mannequin's colour change the try-on, or only the reference?

Every colour experiment so far - p7.2, p7.2b, p7.2b+ - compared REFERENCES. 120 colour
variants exist on disk and not one has been through an edit. So the question the colour
reader was built to answer has never actually been asked: does the mannequin's colour
change the OUTPUT.

Five colours per reference, each taken all the way through both calls:

  matched   the CPU skin reader on the paired person - what ships today
  white     the p7 default, and the low-amplitude case when the garment is pale
  grey      achromatic and person-independent - needs no reader at all
  black     the other achromatic extreme
  opposite  the ladder step furthest in lightness from `matched` - a principled wrong
            answer rather than an arbitrary one, so a null result means "colour does not
            matter" rather than "these two colours happened to be close"

Six pairs chosen to span the cases that failed and the cases that did not.
"""
import csv
import json
import os
import sys

import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v2", "build"))
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import garment_crop as G     # noqa: E402
import phase3_fal as F       # noqa: E402
import run_p7n as P          # noqa: E402
import run_v30 as V          # noqa: E402
import skin_tone as S        # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
QWEN = "fal-ai/qwen-image-edit-2511"
KLEIN = "fal-ai/flux-2/klein/4b/distilled/edit"
SEED = 46

# garment -> why it is here
PAIRS = {
    "g011": "the colour failure: beige coat on the wearer, dark mannequin, textures merged",
    "g013": "the other MQ failure, and a patterned garment",
    "dualuse_zendaya_white_blazer_skirt": "white garment - the white-on-white case",
    "dualuse_man_black_suit_studio_nonceleb": "black garment - the black-on-black case",
    "g014": "plain blue dress, MQ perfect - the control",
    "g030": "gold sequin, MQ perfect - a high-chroma garment",
}


def opposite(word):
    """Furthest ladder step by L*, so the wrong answer is wrong by construction."""
    lo = dict((n, l) for n, l, _ in S.TONES)[word]
    return max(S.TONES, key=lambda t: abs(t[1] - lo))[0]


def main():
    F._load_env()
    rows = [r for r in csv.DictReader(open(os.path.join(
        REPO, "v3/testsets/v30_matrix_b.csv"))) if r["garment"] in PAIRS]
    stage = sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "all"
    log = {}

    plan = []
    for r in rows:
        g, person = r["garment"], r["person"]
        src = os.path.join(RUN, "inputs", f"{g}__A4.jpg")
        t = S.tone(cv2.imread(os.path.join(RUN, "inputs", f"{person}.jpg")))
        matched = t["name"] if t else "beige skin"
        fr = S.framing(cv2.imread(src))["framing"]
        for arm, word in (("matched", matched), ("white", "white skin"),
                          ("grey", "grey"), ("black", "black skin"),
                          ("opposite", opposite(matched))):
            prompt = P.PREFIX + word + " " + P.SUFFIX + P.FRAME_SENTENCE[fr]
            log[f"{g}|{arm}"] = {"prompt": prompt, "colour": word, "arm": arm,
                                 "person": person, "set_id": r["set_id"],
                                 "matched": matched, "why": PAIRS[g]}
            plan.append((g, arm, prompt, src, r))
    json.dump(log, open(os.path.join(RUN, "_ck_prompts.json"), "w"), indent=1)

    if stage in ("extract", "all"):
        jobs = [(f"{g}|{a}", pr, src) for g, a, pr, src, _ in plan
                if not os.path.exists(os.path.join(RUN, "refs", f"{g}__ck.{a}.jpg"))]
        print(f"extract: {len(jobs)} qwen calls")
        if jobs and "--dry" not in sys.argv:
            res = F.run([(k, (lambda p=pr, s=src: F.call(
                QWEN, {"image_urls": [F._b64(cv2.imread(s))], "prompt": p, "seed": SEED})))
                for k, pr, src in jobs], 6)
            for k, v in res.items():
                if v is not None:
                    g, a = k.split("|")
                    G.write_rgb(os.path.join(RUN, "refs", f"{g}__ck.{a}.jpg"), v)
        if stage == "extract":
            return

    if stage in ("edit", "all"):
        jobs = []
        for g, a, pr, src, r in plan:
            ref = os.path.join(RUN, "refs", f"{g}__ck.{a}.jpg")
            out = os.path.join(RUN, "gen", f"{r['set_id']}__ck.{a}.jpg")
            if os.path.exists(out) or not os.path.exists(ref):
                continue
            jobs.append((f"{r['set_id']}|{a}", (
                lambda p=os.path.join(RUN, "inputs", f"{r['person']}.jpg"), rp=ref:
                F.call(KLEIN, {"image_urls": [F._b64(cv2.imread(p)), F._b64(cv2.imread(rp))],
                               "prompt": V.PROMPT, "seed": SEED}))))
        print(f"edit: {len(jobs)} klein calls (~${len(jobs)*0.015:.2f})")
        if jobs and "--dry" not in sys.argv:
            res = F.run(jobs, 6)
            for k, v in res.items():
                if v is not None:
                    sid, a = k.split("|")
                    G.write_rgb(os.path.join(RUN, "gen", f"{sid}__ck.{a}.jpg"), v)
    n = len([1 for f in os.listdir(os.path.join(RUN, "gen")) if "__ck." in f])
    print(f"\n{n}/{len(plan)} colour-through-klein outputs on disk")


if __name__ == "__main__":
    main()
