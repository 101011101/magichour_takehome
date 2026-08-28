"""Dynamic prompting: extent and pose emitted together from one framing read.

The two clauses were written separately and contradicted each other - a fixed pose
sentence naming "feet together" told the model feet were in frame while the extent clause
told it to cut above them, and the pose clause won. They now come from one table keyed on
the framing category, under one rule: NEVER NAME A BODY PART THE CROP EXCLUDES.

Eight references chosen to cover every framing category the reader produces, so the
schema is exercised rather than sampled.
"""
import csv
import json
import os
import sys

import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v2", "build"))
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import garment_crop as G   # noqa: E402
import phase3_fal as F     # noqa: E402
import run_p7n as P        # noqa: E402
import run_v30 as V        # noqa: E402
import skin_tone as S      # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
QWEN = "fal-ai/qwen-image-edit-2511"
KLEIN = "fal-ai/flux-2/klein/4b/distilled/edit"
SEED = 46
REFS = ["p029", "dualuse_emma_watson_black_blazer_armscrossed", "g018",   # waist_up
        "p030",                                                           # chest_up
        "dualuse_queen_latifah_gown_stage",                               # knee_up
        "g013", "g014", "dualuse_man_black_suit_studio_nonceleb"]         # full_body


def main():
    F._load_env()
    rows = {r["garment"]: r for r in csv.DictReader(open(os.path.join(
        REPO, "v3/testsets/v30_matrix_b.csv")))}
    log, qjobs = {}, []
    for g in REFS:
        r = rows[g]
        src = os.path.join(RUN, "inputs", f"{g}__A4.jpg")
        t = S.tone(cv2.imread(os.path.join(RUN, "inputs", f"{r['person']}.jpg")))
        colour = t["name"] if t else "beige skin"
        fr = S.framing(cv2.imread(src))["framing"]
        prompt = P.PREFIX + colour + " " + P.SUFFIX + S.FRAME_CLAUSE[fr]
        log[g] = {"prompt": prompt, "colour": colour, "framing": fr,
                  "clause": S.FRAME_CLAUSE[fr].strip(), "set_id": r["set_id"],
                  "person": r["person"]}
        if not os.path.exists(os.path.join(RUN, "refs", f"{g}__dyn.jpg")):
            qjobs.append((g, prompt, src))
    json.dump(log, open(os.path.join(RUN, "_dyn_prompts.json"), "w"), indent=1)
    print(f"extract: {len(qjobs)} qwen calls")
    if "--dry" in sys.argv:
        for g in REFS:
            print(f"  {g[:34]:36} {log[g]['framing']:10} {log[g]['clause'][:78]}")
        return
    if qjobs:
        res = F.run([(k, (lambda p=pr, s=src: F.call(
            QWEN, {"image_urls": [F._b64(cv2.imread(s))], "prompt": p, "seed": SEED})))
            for k, pr, src in qjobs], 6)
        for k, v in res.items():
            if v is not None:
                G.write_rgb(os.path.join(RUN, "refs", f"{k}__dyn.jpg"), v)
    kjobs = []
    for g in REFS:
        ref = os.path.join(RUN, "refs", f"{g}__dyn.jpg")
        out = os.path.join(RUN, "gen", f"{log[g]['set_id']}__dyn.jpg")
        if os.path.exists(out) or not os.path.exists(ref):
            continue
        kjobs.append((log[g]["set_id"], (
            lambda p=os.path.join(RUN, "inputs", f"{log[g]['person']}.jpg"), rp=ref:
            F.call(KLEIN, {"image_urls": [F._b64(cv2.imread(p)), F._b64(cv2.imread(rp))],
                           "prompt": V.PROMPT, "seed": SEED}))))
    print(f"edit: {len(kjobs)} klein calls")
    if kjobs:
        res = F.run(kjobs, 6)
        for k, v in res.items():
            if v is not None:
                G.write_rgb(os.path.join(RUN, "gen", f"{k}__dyn.jpg"), v)
    print("done")


if __name__ == "__main__":
    main()
