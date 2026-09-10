"""The v3.6 evaluation set: 150 cells of iron man 2, both sides of BC's own record.

A prompt tested only on failures cannot be adopted. The rescue rate says what a longer
call-2 prompt buys; the **regression rate on cells that already work** says what it costs,
and the second number is the one that decides whether it ships. So the set is:

  29 cells the reviewer marked FAIL for BC   (all of them - v3/testsets/bc_count.csv)
 121 cells the reviewer left unmarked        (a fixed-seed sample of the other 571)
 ---
 150 cells, each a (set_id, seed) pair that already carries a BC verdict

The sample is drawn with `random.Random(46)` over the sorted unmarked rows, so re-running
this script reproduces the set exactly.

  python3 v3/build/make_v36_editset.py    ->  v3/colab/v36_editset.csv
"""
import csv
import os
import random

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COUNT = os.path.join(REPO, "v3", "testsets", "bc_count.csv")
MATRIX = os.path.join(REPO, "v3", "colab", "matrix.csv")
OUT = os.path.join(REPO, "v3", "colab", "v36_editset.csv")
N_OK = 121
SEED = 46


def main():
    marks = list(csv.DictReader(open(COUNT)))
    pairs = {r["set_id"]: r for r in csv.DictReader(open(MATRIX))}
    fail = [r for r in marks if r["bc_failed"] == "fail"]
    ok = sorted([r for r in marks if r["bc_failed"] != "fail"],
                key=lambda r: (r["set_id"], r["seed"]))
    keep = fail + random.Random(SEED).sample(ok, N_OK)
    keep.sort(key=lambda r: (r["bc_failed"] != "fail", r["set_id"], r["seed"]))

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["set_id", "person", "garment", "seed", "bc"])
        w.writeheader()
        for r in keep:
            p = pairs[r["set_id"]]
            w.writerow({"set_id": r["set_id"], "person": p["person"],
                        "garment": p["garment"], "seed": r["seed"],
                        "bc": "fail" if r["bc_failed"] == "fail" else "ok"})
    print(f"{len(keep)} cells ({len(fail)} fail + {N_OK} ok) -> "
          f"{os.path.relpath(OUT, REPO)}")


if __name__ == "__main__":
    main()
