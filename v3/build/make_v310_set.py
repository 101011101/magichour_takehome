"""The v3.10 set: the whole fold, every cell `BC`'s and `ER`'s blind counts were made on.

600 cells - 200 pairs x seeds 46/47/48, `v3/colab/v36_ironman_er.csv` unsampled. v3.9 asked
the same question on 93 cells chosen for being interesting; this asks it on everything, because
what v3.9 could not settle is the *cost on cells that already pass*, and it had 31 of them.

Per cell it computes both call-2 canvases FROM THE 1 MP-BOUNDED PERSON PHOTO (run_v310.MAXPIX
= 2^20, the bound the candidate rule implies), so the cells where the two rules agree - NOSCALE
no-ops, not generated, nothing to compare - are known before anything runs. It also carries
each cell's prior verdict from the two blind sweeps, so the marking can be split by "did this
cell already pass", which is the split the whole run exists to resolve.

  python3 v3/build/make_v310_set.py   ->  v3/colab/v310_set.csv
"""
import csv
import os
import sys

import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
import run_v310 as V                   # noqa: E402  the bound and both canvas rules, as the run applies them

COLAB = os.path.join(REPO, "v3", "colab")
T = os.path.join(REPO, "v3", "testsets")
INPUTS = os.path.join(REPO, "v3", "runs", "v36", "ironman_er", "inputs")
FOLD = os.path.join(COLAB, "v36_ironman_er.csv")
OUT = os.path.join(COLAB, "v310_set.csv")
FIELDS = ["set_id", "person", "garment", "seed", "prior", "bc2", "er",
          "person_wh_1mp", "canvas_SCALE", "canvas_NOSCALE", "noscale_noop"]


def verdicts(name):
    return {(r["set_id"], r["seed"]): r["bc_failed"] == "fail"
            for r in csv.DictReader(open(os.path.join(T, name)))}


def main():
    bc2, er = verdicts("bc2_count.csv"), verdicts("er_count.csv")
    fold = list(csv.DictReader(open(FOLD)))

    sizes = {}
    for p in sorted({r["person"] for r in fold}):
        im = cv2.imread(os.path.join(INPUTS, f"{p}.jpg"))
        if im is None:
            raise SystemExit(f"no normalised photo for {p} under {INPUTS}")
        b = V.normalise(im)                          # the bound the candidate rule implies
        sizes[p] = (b, V.CANVAS["SCALE"](b), V.CANVAS["NOSCALE"](b))

    rows = []
    for r in fold:
        c = (r["set_id"], r["seed"])
        b, sc, ns = sizes[r["person"]]
        rows.append({"set_id": r["set_id"], "person": r["person"], "garment": r["garment"],
                     "seed": r["seed"],
                     "prior": "fail" if (bc2.get(c) or er.get(c)) else "clean",
                     "bc2": "fail" if bc2.get(c) else "", "er": "fail" if er.get(c) else "",
                     "person_wh_1mp": f"{b.shape[1]}x{b.shape[0]}",
                     "canvas_SCALE": f"{sc[1]}x{sc[0]}", "canvas_NOSCALE": f"{ns[1]}x{ns[0]}",
                     "noscale_noop": "1" if sc == ns else ""})

    assert len(rows) == 600, f"the fold is 600 cells, got {len(rows)}"
    assert len({(r["set_id"], r["seed"]) for r in rows}) == 600, "duplicate cells"

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader(); w.writerows(rows)

    noop = sum(r["noscale_noop"] == "1" for r in rows)
    cards = {g: sum(1 for r in rows if r["prior"] == g and r["noscale_noop"] != "1")
             for g in ("fail", "clean")}
    ratio = []
    for r in rows:
        if r["noscale_noop"] == "1":
            continue
        (a, b), (c, e) = (map(int, r["canvas_NOSCALE"].split("x")),
                          map(int, r["canvas_SCALE"].split("x")))
        ratio.append(a * b / (c * e))
    mp = [int(a) * int(b) / 2 ** 20 for a, b in (r["person_wh_1mp"].split("x") for r in rows)]
    print(f"{len(rows)} cells -> {os.path.relpath(OUT, REPO)}")
    print(f"  {len({r['set_id'] for r in rows})} pairs · {len({r['person'] for r in rows})} persons · "
          f"{len({r['garment'] for r in rows})} garments")
    print(f"  prior verdict: fail {sum(r['prior'] == 'fail' for r in rows)}, "
          f"clean {sum(r['prior'] == 'clean' for r in rows)}")
    print(f"  person photos under the 1 MP bound: {min(mp):.3f}-{max(mp):.3f} MP (2^20)")
    print(f"  NOSCALE no-ops (canvas identical to SCALE's): {noop}; generated: {len(rows) - noop}")
    print(f"  call-2 generations: SCALE {len(rows)} + NOSCALE {len(rows) - noop} = {2 * len(rows) - noop}")
    print(f"  cards to mark: {sum(cards.values())} (prior fail {cards['fail']}, prior clean {cards['clean']})")
    print(f"  on the {len(ratio)} that differ, NOSCALE/SCALE canvas area {min(ratio):.2f}-{max(ratio):.2f}, "
          f"mean {sum(ratio) / len(ratio):.3f}")


if __name__ == "__main__":
    main()
