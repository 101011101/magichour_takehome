"""Did dropping the hold clause move anything the clause was protecting?

A reviewer's "held" is a judgement about two things at once - identity and scene - and it is
easy to answer holistically without meaning to. This measures the scene half instead, which
is the half a machine can settle: take BiRefNet's matte of the person photograph, and compare
each arm's output against that photograph **on the background pixels only**, where no arm is
supposed to have changed anything.

The garment is excluded by construction, so a difference here is the hold failing and nothing
else. BC and ER carry the clause; ER2 does not. If ER2's background error sits with theirs,
the clause was not what was holding the background.

  python3 v3/build/v36_hold_check.py   ->  v3/runs/v36/er2/meta/hold_check.csv
"""
import csv
import os
import statistics as stat
import sys

import cv2
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
import v3lib as L                     # noqa: E402  the matte of record

RUN = os.path.join(REPO, "v3", "runs", "v36", "er2")
BCRUN = os.path.join(REPO, "v3", "runs", "v34", "ironman2_bc")
ARMS = ("BC", "ER", "ER2")
DILATE = 25          # px, keeps the garment's own edge out of the "background"


def bg_error(person, out, mask):
    """Mean absolute difference on background pixels, 0-255. Output is resized to the
    photograph's canvas first - every arm renders on its own, and the comparison is of
    content, not of size."""
    o = cv2.resize(out, (person.shape[1], person.shape[0]), interpolation=cv2.INTER_AREA)
    d = np.abs(person.astype(np.float32) - o.astype(np.float32)).mean(axis=2)
    return float(d[mask].mean()) if mask.any() else float("nan")


def main():
    paths = L.fetch_models(verbose=False)
    rows = list(csv.DictReader(open(os.path.join(RUN, "v36_er2_set.csv"))))
    masks, out = {}, []
    for i, r in enumerate(rows, 1):
        p = r["person"]
        person = cv2.imread(os.path.join(RUN, "inputs", f"{p}.jpg"))
        if p not in masks:
            m = L.matte(person, paths) > 0.5
            k = np.ones((DILATE, DILATE), np.uint8)
            masks[p] = cv2.dilate(m.astype(np.uint8), k).astype(bool) == False   # noqa: E712
        rec = {"set_id": r["set_id"], "seed": r["seed"], "person": p}
        for a in ARMS:
            q = (os.path.join(BCRUN, "gen", f"{r['set_id']}__BC__s{r['seed']}.jpg") if a == "BC"
                 else os.path.join(RUN, "gen", f"{r['set_id']}__{a}__s{r['seed']}.jpg"))
            rec[a] = round(bg_error(person, cv2.imread(q), masks[p]), 2)
        out.append(rec)
        if i % 10 == 0:
            print(f"  {i}/{len(rows)}", flush=True)

    with open(os.path.join(RUN, "meta", "hold_check.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)

    print(f"\nbackground error against the person photograph, {len(out)} cells "
          f"(0 = pixel-identical outside the subject)")
    for a in ARMS:
        v = [r[a] for r in out]
        print(f"  {a:4s} median {stat.median(v):6.2f}   mean {sum(v) / len(v):6.2f}   "
              f"worst {max(v):6.2f}")
    worse = sum(1 for r in out if r["ER2"] > r["ER"])
    print(f"\nER2 worse than ER on {worse}/{len(out)} cells; "
          f"median delta {stat.median([r['ER2'] - r['ER'] for r in out]):+.2f}")
    big = [r for r in out if r["ER2"] - r["ER"] > 2.0]
    print(f"cells where ER2's background error exceeds ER's by more than 2: {len(big)}")
    for r in sorted(big, key=lambda x: x["ER"] - x["ER2"])[:8]:
        print(f"   {r['set_id']} s{r['seed']}  BC {r['BC']}  ER {r['ER']}  ER2 {r['ER2']}")


if __name__ == "__main__":
    main()
