"""Cut v3.5's failure set out of the v3.4 lock's own per-cell human verdict.

`v34_im2_truth.json` is the artefact of record for iron man 2: 600 cells (200 pairs x
seeds 46/47/48), every one judged by the reviewer, CLEAN / MID / FAIL
(v3.4 RESULTS 10.5). This takes every pair with at least one FAIL, carries the three
per-seed verdicts and a seed_stable flag, and joins the matrix row for the file names.

It exists because the set was first cut inline and left on disk without a generator - the
mistake v3.4 RESULTS' "Not in the repo" note records for v34_failures.csv.

  python3 v3/build/make_v35_failures.py    ->  v3/testsets/v35_failures.csv
"""
import collections
import csv
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TRUTH = os.path.join(REPO, "v34_im2_truth.json")
MATRIX = os.path.join(REPO, "v3", "colab", "matrix.csv")
OUT = os.path.join(REPO, "v3", "testsets", "v35_failures.csv")
FIELDS = ["set_id", "person", "person_file", "garment", "garment_file", "person_framing",
          "garment_hard_case", "v46", "v47", "v48", "seed_stable"]


def main():
    by = collections.defaultdict(dict)
    for k, v in json.load(open(TRUTH)).items():
        sid, seed = k.split("|")
        by[sid][seed] = v
    mx = {r["set_id"]: r for r in csv.DictReader(open(MATRIX))}
    rows = []
    for sid, ss in sorted(by.items()):
        if not any(v == "FAIL" for v in ss.values()):
            continue
        r = mx[sid]
        rows.append({"set_id": sid, "person": r["person"], "person_file": r["person_file"],
                     "garment": r["garment"], "garment_file": r["garment_file"],
                     "person_framing": r["person_framing"],
                     "garment_hard_case": r["garment_hard_case"],
                     "v46": ss.get("46", ""), "v47": ss.get("47", ""), "v48": ss.get("48", ""),
                     "seed_stable": "yes" if all(v == "FAIL" for v in ss.values()) else "no"})
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    stable = sum(r["seed_stable"] == "yes" for r in rows)
    print(f"{OUT}: {len(rows)} pairs of {len(by)} · {stable} fail at every seed")


if __name__ == "__main__":
    main()
