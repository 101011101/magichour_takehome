"""The v3.11 set: a few garments x two full-body people, on cells that already work.

Runbo's case is "a full body image, but just wants to swap the top", so the people are chosen by
the framing read - `v3lib.framing` on the person photo, ankle in frame => full_body - and the
pairs are drawn ONLY from cells marked clean in the v3.10 count (`v310_count.csv`, NOSCALE,
fail=0). A selector failing on a pair that was already broken would tell us nothing; starting
from cells that work makes a failure here attributable to the selector.

The garments are chosen by a measurement too: the hip line is read off the archived bald frames -
the same read `run_v311.hip_line` will make - and only garments whose hip sits between HIP_LO and
HIP_HI of frame height are eligible, so both halves are substantial. A garment whose hip sits at
the bottom of the frame is a waist-up photograph: its `lower` band would be a sliver and would
fall back to `full`, which is correct behaviour but tests nothing in a six-garment trial.

No product shots here, unlike the first draft of this set: Runbo's case is a person photograph,
and the flat-lay behaviour is already measured and written up in EXPERIMENT link 1 (Pose reports
a hip on 6 of 10 flat-lays, which contain no person at all).

  python3 v3/build/make_v311_set.py   ->  v3/colab/v311_set.csv

Needs mediapipe, the v3.10 count, and the archived photos and bald frames under v3/runs/ - all
gitignored, which is why the selection it produces is committed as the CSV.
"""
import collections
import csv
import glob
import os
import sys

import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
sys.path.insert(0, os.path.join(REPO, "v2", "build"))
import v3lib as L                      # noqa: E402  the framing read
import run_v311 as V                   # noqa: E402  the same hip read the run will make

COLAB = os.path.join(REPO, "v3", "colab")
OUT = os.path.join(COLAB, "v311_set.csv")
COUNT = os.path.join(REPO, "v310_count.csv")
INPUTS = os.path.join(REPO, "v3", "runs", "v310", "a100", "in1mp")
WORN_BALD = os.path.join(REPO, "v3", "runs", "v34", "ironman2", "refs", "*__bald.jpg")
POSE = os.path.join(REPO, "v2", "runs", ".models", "pose_landmarker_lite.task")
SEED = 46
HIP_LO, HIP_HI = 0.35, 0.80
N_GARMENT, N_PERSON = 6, 2
FIELDS = ["set_id", "person", "garment", "seed", "person_framing", "hip_frac_archive"]


def main():
    clean = {tuple(r["set_id"].split("+", 1)) for r in csv.DictReader(open(COUNT))
             if r["arm"] == "NOSCALE" and r["fail"] == "0"}
    if not clean:
        raise SystemExit(f"no clean NOSCALE cells in {COUNT}")

    hip = {}
    for f in sorted(glob.glob(WORN_BALD)):
        g = os.path.basename(f).replace("__bald.jpg", "")
        im = cv2.imread(f)
        if im is None:
            continue
        y, _ = V.hip_line(im)
        hip[g] = None if y is None else round(y / im.shape[0], 3)
    eligible = {g for g, f in hip.items() if f is not None and HIP_LO <= f <= HIP_HI}

    paths = {"pose": POSE}
    framing = {}
    for p in sorted({p for p, g in clean if g in eligible}):
        f = os.path.join(INPUTS, f"{p}.jpg")
        if os.path.exists(f):
            framing[p] = L.framing(cv2.imread(f), paths)["framing"]

    # the fold pairs each person with only a few garments, so the same two people cannot cover
    # six garments: the people are chosen PER GARMENT from that garment's own clean pairs
    by_garment = collections.defaultdict(list)
    for p, g in sorted(clean):
        if g in eligible and framing.get(p) == "full_body":
            by_garment[g].append(p)
    ranked = sorted(by_garment.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    garments = [g for g, ps in ranked if len(ps) >= N_PERSON][:N_GARMENT]
    if len(garments) < N_GARMENT:
        raise SystemExit(f"only {len(garments)} garments have {N_PERSON} clean full-body "
                         f"partners; lower N_PERSON or widen HIP_LO/HIP_HI")

    rows = [{"set_id": f"{p}+{g}", "person": p, "garment": g, "seed": SEED,
             "person_framing": framing[p], "hip_frac_archive": hip[g]}
            for g in garments for p in by_garment[g][:N_PERSON]]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader(); w.writerows(rows)

    balds = len({V.bald_key(a, r) for a, r in V.PLAN})
    edits = len(rows) * len(V.PLAN)
    print(f"{len(rows)} cells -> {os.path.relpath(OUT, REPO)}")
    print(f"  {len(garments)} garments x {N_PERSON} people each x {len(V.PLAN)} "
          f"(arm, region) pairs = {edits} try-ons")
    print(f"  klein calls: {len(garments) * balds} call 1 + {edits} call 2 = "
          f"{len(garments) * balds + edits}; crops: {len(garments) * balds}")
    print(f"  every pair is clean in the v3.10 count ({len(clean)} clean cells to draw from)")
    print(f"  every person reads full_body on the framing read")
    print(f"  garments, hip at {HIP_LO}-{HIP_HI} of frame height, with their clean partners:")
    for g in garments:
        print(f"    {g[:48]:48s} hip {hip[g]}  {', '.join(by_garment[g][:N_PERSON])}")
    print(f"  eligible by hip: {len(eligible)}/{len(hip)} · with {N_PERSON} clean full-body "
          f"partners: {sum(1 for _, ps in ranked if len(ps) >= N_PERSON)} · taken: {len(garments)}")


if __name__ == "__main__":
    main()
