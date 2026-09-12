"""The v3.9 set: every cell a blind sweep failed, plus a fixed sample of cells both sweeps
passed - so each arm is judged on what it rescues and on what it breaks.

  fail   v3/colab/v36_er2_set.csv - the union of BC pass 2's failures and the ER sweep's
  clean  the both_clean cells of v3/colab/v36_fp8_set.csv - clean in bc2_count and
         er_count, sampled random.Random(46) by make_v36_fp8_set.py; reused so these cells
         also carry the ERq (Photoroom transformer) record

Per cell it computes both call-2 canvases FROM THE 1 MP-BOUNDED PERSON PHOTO, the bound this
test runs under (run_v39.MAXPIX = 2^20, not v3lib's 1,150,000), so the cells where the two
rules agree - NOSCALE no-ops, not generated - are known before anything runs.

  python3 v3/build/make_v39_set.py   ->  v3/colab/v39_set.csv
"""
import csv
import os
import sys

import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
import run_v39 as V                    # noqa: E402  the bound and both canvas rules, as the run applies them

COLAB = os.path.join(REPO, "v3", "colab")
T = os.path.join(REPO, "v3", "testsets")
INPUTS = os.path.join(REPO, "v3", "runs", "v36", "ironman_er", "inputs")
OUT = os.path.join(COLAB, "v39_set.csv")
FIELDS = ["set_id", "person", "garment", "seed", "group", "bc2", "er",
          "person_wh_1mp", "canvas_SCALE", "canvas_NOSCALE", "noscale_noop"]


def verdicts(name):
    return {(r["set_id"], r["seed"]): r["bc_failed"] == "fail"
            for r in csv.DictReader(open(os.path.join(T, name)))}


def main():
    bc2, er = verdicts("bc2_count.csv"), verdicts("er_count.csv")
    fail = list(csv.DictReader(open(os.path.join(COLAB, "v36_er2_set.csv"))))
    clean = [r for r in csv.DictReader(open(os.path.join(COLAB, "v36_fp8_set.csv")))
             if r["er_status"] == "both_clean"]

    rows, seen = [], set()
    for group, src in (("fail", fail), ("clean", clean)):
        for r in src:
            c = (r["set_id"], r["seed"])
            if c in seen:
                continue
            seen.add(c)
            p = cv2.imread(os.path.join(INPUTS, f"{r['person']}.jpg"))
            if p is None:
                raise SystemExit(f"no normalised photo for {r['person']} under {INPUTS}")
            p = V.normalise(p)                      # the bound this test runs under
            sc, ns = V.CANVAS["SCALE"](p), V.CANVAS["NOSCALE"](p)
            rows.append({"set_id": r["set_id"], "person": r["person"], "garment": r["garment"],
                         "seed": r["seed"], "group": group,
                         "bc2": "fail" if bc2.get(c) else "", "er": "fail" if er.get(c) else "",
                         "person_wh_1mp": f"{p.shape[1]}x{p.shape[0]}",
                         "canvas_SCALE": f"{sc[1]}x{sc[0]}", "canvas_NOSCALE": f"{ns[1]}x{ns[0]}",
                         "noscale_noop": "1" if sc == ns else ""})

    for r in rows:
        if r["group"] == "fail":
            assert r["bc2"] or r["er"], f"{r['set_id']}@{r['seed']} is in the fail group but no sweep failed it"
        else:
            assert not r["bc2"] and not r["er"], f"{r['set_id']}@{r['seed']} is not clean"

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader(); w.writerows(rows)

    mp = [int(a) * int(b) / 2 ** 20 for a, b in (r["person_wh_1mp"].split("x") for r in rows)]
    ratio = []
    for r in rows:
        (a, b), (c, e) = (map(int, r["canvas_NOSCALE"].split("x")), map(int, r["canvas_SCALE"].split("x")))
        ratio.append(a * b / (c * e))
    noop = sum(r["noscale_noop"] == "1" for r in rows)
    diff = [x for x, r in zip(ratio, rows) if r["noscale_noop"] != "1"]
    n = {g: sum(r["group"] == g for r in rows) for g in ("fail", "clean")}
    print(f"{len(rows)} cells -> {os.path.relpath(OUT, REPO)}   {n}")
    print(f"  {len({r['set_id'] for r in rows})} pairs · {len({r['garment'] for r in rows})} garments · "
          f"{len({r['person'] for r in rows})} persons")
    print(f"  person photos under the 1 MP bound: {min(mp):.3f}-{max(mp):.3f} MP (2^20)")
    print(f"  NOSCALE no-ops (same canvas as SCALE): {noop}; generated: {len(rows) - noop}")
    print(f"  on the {len(diff)} that differ, NOSCALE/SCALE canvas area {min(diff):.2f}-{max(diff):.2f}")


if __name__ == "__main__":
    main()
