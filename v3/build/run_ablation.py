"""Prompt-length ablation for p7.3.

p7.3 reached five sentences by accretion - every clause was added because removing it
caused a specific failure. That is a reasonable way to arrive at a prompt and a bad
reason to believe the result is minimal. This strips it back and measures what each
layer is still buying.

  L1  one sentence: mannequin, colour, white ground, extent. Nothing else.
  L2  L1 + the person is gone.
  L3  L2 + copy each piece exactly.
  L4  full p7.3 - adds the completeness clause and the no-addition guard.

Each level is a strict superset of the one before, so the difference between adjacent
columns is exactly one clause. Same 8 references, same seed, colour and extent from the
same CPU readers - only the prompt length varies.
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
import skin_tone as S        # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
QWEN = "fal-ai/qwen-image-edit-2511"
SEED = 46

GONE = (" The person themself is gone - no face, no skin, no hair.")
COPY = (" Copy each piece exactly - the same colour, print, texture and cut.")
EVERY = (" The mannequin wears every piece the person is actually wearing, exactly as "
         "they wear it, keeping its shape and drape.")
GUARD = (" The mannequin wears only what the person is wearing and nothing else: if "
         "they are not carrying a bag, there is no bag.")


def levels(colour, extent):
    one = (f"Show this person's outfit on a {colour} mannequin against pure white."
           f"{extent}")
    return {
        "L1": one,
        "L2": one + GONE,
        "L3": one + GONE + COPY,
        "L4": one + GONE + COPY + EVERY + GUARD,
    }


def main():
    F._load_env()
    rows = [r for r in csv.DictReader(open(os.path.join(
        REPO, "v3/testsets/v30_matrix_b.csv"))) if r["garment"] in P.PROBE]
    log, jobs = {}, []
    for r in rows:
        g, person = r["garment"], r["person"]
        gp = os.path.join(RUN, "inputs", f"{g}.jpg")
        t = S.tone(cv2.imread(os.path.join(RUN, "inputs", f"{person}.jpg")))
        colour = t["name"] if t else "beige skin"
        fr = S.framing(cv2.imread(gp))
        extent = P.FRAME_SENTENCE[fr["framing"]]
        for tag, prompt in levels(colour, extent).items():
            log[f"{g}|abl.{tag}"] = {"prompt": prompt, "words": len(prompt.split()),
                                     "colour": colour, "framing": fr["framing"]}
            jobs.append((f"{g}|abl.{tag}", prompt, gp))
    json.dump(log, open(os.path.join(RUN, "_ablation_prompts.json"), "w"), indent=1)
    todo = [(k, p, gp) for k, p, gp in jobs
            if not os.path.exists(os.path.join(RUN, "refs", f"{k.replace('|', '__')}.jpg"))]
    w = {k.split("|")[1]: v["words"] for k, v in log.items()}
    print("word counts: " + " · ".join(f"{k} {v}" for k, v in sorted(w.items())))
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
