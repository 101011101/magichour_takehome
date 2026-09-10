"""The iron-man set for `ER`: the same 600 cells `BC` was counted on.

`BC`'s rate of record is a blind sweep of **200 pairs x seeds 46/47/48** on the iron-man-2
matrix (`v3/testsets/bc_count.csv`, 29 failures, 4.8%). A rate for `ER` is comparable to it
only if it is the same 600 cells, the same reference, the same canvas, the same eye and the
same page - so the set is not sampled and not filtered. It is the matrix, expanded.

  python3 v3/build/make_v36_ironman_set.py    ->  v3/colab/v36_ironman_er.csv
"""
import csv
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MATRIX = os.path.join(REPO, "v3", "colab", "matrix.csv")
OUT = os.path.join(REPO, "v3", "colab", "v36_ironman_er.csv")
SEEDS = (46, 47, 48)


def main():
    rows = list(csv.DictReader(open(MATRIX)))
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["set_id", "person", "garment", "seed"])
        w.writeheader()
        for r in rows:
            for s in SEEDS:
                w.writerow({"set_id": r["set_id"], "person": r["person"],
                            "garment": r["garment"], "seed": s})
    print(f"{len(rows) * len(SEEDS)} cells ({len(rows)} pairs x {len(SEEDS)} seeds) -> "
          f"{os.path.relpath(OUT, REPO)}")


if __name__ == "__main__":
    main()
