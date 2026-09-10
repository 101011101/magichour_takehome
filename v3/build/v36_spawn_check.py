"""Does naming a limb that is not in frame make klein draw it?

The question v2's rule assumes the answer to - *never name a body part the crop excludes* -
and which nothing in v3 has ever measured. It is measurable without a human: take the cells
where the **pose read finds no feet in image 1**, run the same read over each arm's
**output**, and count how often feet appear that the photograph never had.

The read is the one that built the prompt (`run_v36.limbs`, MediaPipe Pose landmark
visibility plus an in-frame coordinate), so the measurement and the instruction agree by
construction on what "in frame" means.

  python3 v3/build/v36_spawn_check.py    ->  v3/runs/v36/a100/meta/spawned_feet.csv
"""
import collections
import csv
import json
import os
import sys

import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
import run_v36 as V                   # noqa: E402
import v3lib as L                     # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v36", "a100")
ARMS = ("E0", "ER", "ERD", "ERS")
OUT = os.path.join(RUN, "meta", "spawned_feet.csv")


def main():
    rows = list(csv.DictReader(open(os.path.join(RUN, "v36_editset.csv"))))
    seen = json.load(open(os.path.join(RUN, "meta", "prompts_v36.json")))
    frame = {k.split("|")[0]: tuple(v["in_frame"]) for k, v in seen.items()}
    paths = L.fetch_models(verbose=False)

    nofeet = [r for r in rows if "feet" not in frame.get(r["set_id"], ())]
    tally, out = collections.Counter(), []
    for r in nofeet:
        rec = {"set_id": r["set_id"], "seed": r["seed"], "bc": r["bc"]}
        for a in ARMS:
            p = os.path.join(RUN, "gen", f"{r['set_id']}__{a}__s{r['seed']}.jpg")
            spawned = "feet" in V.limbs(cv2.imread(p), paths)
            rec[a] = int(spawned)
            tally[a] += spawned
        out.append(rec)

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)

    print(f"{len(nofeet)} cells where image 1 has no feet in frame\n"
          "feet found in the output:")
    for a in ARMS:
        print(f"  {a:4s} {tally[a]:2d}/{len(nofeet)}  ({100 * tally[a] / len(nofeet):.0f}%)")
    print(f"\n-> {os.path.relpath(OUT, REPO)}")


if __name__ == "__main__":
    main()
