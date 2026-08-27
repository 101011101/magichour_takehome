"""p7.2b+ : the wider skin ladder.

p7.2b established that naming the colour as skin keeps it on the mannequin where a bare
adjective leaked. p7.2b+ asks how fine the ladder can usefully be: ten steps instead of
four, every one an ordinary phrase.

Two things are run:

  ladder   all ten words on four references, so the ladder itself can be looked at
  matched  the CPU reader's own pick for the PAIRED PERSON, on all eight references,
           which is the arm that would actually ship

Same slot, same sentence as p7.2b: PREFIX + <word> + SUFFIX. No framing clause - p7.2b+
varies colour only, exactly as p7.1 varies framing only. The two are combined later and
only after each has a winner.
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
# Four references: a light garment that bled, a dark garment that bled, a multi-piece
# that survived, and a dark full-body control.
LADDER_REFS = ["p029", "dualuse_emma_watson_black_blazer_armscrossed",
               "g024", "dualuse_man_black_suit_studio_nonceleb"]


def slug(w):
    return w.replace(" skin", "").replace(" ", "-")


def main():
    F._load_env()
    rows = [r for r in csv.DictReader(open(os.path.join(
        REPO, "v3/testsets/v30_matrix_b.csv"))) if r["garment"] in P.PROBE]
    log, jobs = {}, []

    for r in rows:
        g, person = r["garment"], r["person"]
        gpath = os.path.join(RUN, "inputs", f"{g}.jpg")

        if g in LADDER_REFS:
            for word, _, hexv in S.TONES:
                tag = f"p7.2b+.{slug(word)}"
                prompt = P.PREFIX + word + " " + P.SUFFIX
                log[f"{g}|{tag}"] = {"prompt": prompt, "colour": word, "hex": hexv,
                                     "arm": "ladder"}
                jobs.append((f"{g}|{tag}", prompt, gpath))

        t = S.tone(cv2.imread(os.path.join(RUN, "inputs", f"{person}.jpg")))
        word = t["name"] if t else "beige skin"
        prompt = P.PREFIX + word + " " + P.SUFFIX
        log[f"{g}|p7.2b+.matched"] = {"prompt": prompt, "colour": word,
                                      "arm": "matched", "person": person,
                                      "ITA": t["ITA"] if t else None,
                                      "L": t["L"] if t else None,
                                      "measured_hex": t["measured_hex"] if t else None}
        jobs.append((f"{g}|p7.2b+.matched", prompt, gpath))

    json.dump(log, open(os.path.join(RUN, "_p72bplus_prompts.json"), "w"), indent=1)
    todo = [(k, p, gp) for k, p, gp in jobs
            if not os.path.exists(os.path.join(RUN, "refs", f"{k.replace('|', '__')}.jpg"))]
    print(f"{len(jobs)} arms ({len(S.TONES)} ladder x {len(LADDER_REFS)} refs "
          f"+ matched x {len(rows)}), {len(todo)} to run")
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
