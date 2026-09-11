"""The set for the transformer swap: cells whose `ER` verdict is already known.

A quantised transformer can only be judged against outcomes that exist, so the set is drawn
from the bank's classification rather than sampled at random:

  every cell `ER` failed              - does the swap fail them too, or reach some?
  every cell `ER` repaired over `BC`  - does the swap keep the wins?
  a fixed-seed sample of both-clean   - does the swap break what works? the one that decides

  python3 v3/build/make_v36_fp8_set.py   ->  v3/colab/v36_fp8_set.csv
"""
import csv
import os
import random

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
T = os.path.join(REPO, "v3", "testsets")
OUT = os.path.join(REPO, "v3", "colab", "v36_fp8_set.csv")
N_CLEAN = 40
SEED = 46


def main():
    L = lambda p: {(r["set_id"], r["seed"]): r["bc_failed"] == "fail"          # noqa: E731
                   for r in csv.DictReader(open(os.path.join(T, p)))}
    bc2, er = L("bc2_count.csv"), L("er_count.csv")
    bf = {(r["set_id"], r["seed"]): (r["block"], r["er_verdict"])
          for r in csv.DictReader(open(os.path.join(T, "v36_bcfail.csv")))}
    matrix = {r["set_id"]: r for r in csv.DictReader(
        open(os.path.join(REPO, "v3", "colab", "matrix.csv")))}

    er_fail = sorted(c for c in er if er[c])
    repaired = sorted(c for c, (blk, v) in bf.items() if blk == "bcfail" and v == "clean")
    clean = sorted(c for c in bc2 if not bc2[c] and not er.get(c)
                   and c not in set(er_fail) | set(repaired))
    pick = random.Random(SEED).sample(clean, N_CLEAN)

    rows, seen = [], set()
    for cells, tag in ((er_fail, "er_fail"), (repaired, "er_repaired"), (pick, "both_clean")):
        for sid, sd in cells:
            if (sid, sd) in seen:
                continue
            seen.add((sid, sd))
            m = matrix[sid]
            rows.append({"set_id": sid, "person": m["person"], "garment": m["garment"],
                         "seed": sd, "er_status": tag})

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["set_id", "person", "garment", "seed", "er_status"])
        w.writeheader(); w.writerows(rows)
    n = {t: sum(1 for r in rows if r["er_status"] == t) for t in
         ("er_fail", "er_repaired", "both_clean")}
    print(f"{len(rows)} cells -> {os.path.relpath(OUT, REPO)}   {n}")


if __name__ == "__main__":
    main()
