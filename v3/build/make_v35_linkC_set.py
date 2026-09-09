"""The link C set: every pair either the v3.4 lock or v3.3 failed, with its provenance.

Two failure records exist for the 200-pair matrix and they disagree about what is hard:

  v34_im2_truth.json      the v3.4 lock's own failures - the reviewer's per-cell verdict
                          on arm VEi, 600 cells, CLEAN/MID/FAIL          -> 31 pairs
  v3/testsets/v34_failures.csv
                          v3.3's failures, cut from v33_ironman_votes_bca4.csv under the
                          reviewer's rule (BC klein better, or both failed, not nudged
                          acceptable), with the F1-F4 class                -> 31 pairs

They overlap on only 11 pairs, so the union is 51 - the v3.3 set carries hard pairs the
lock happens to pass and the F-class taxonomy, the v3.4 set carries the lock's own current
failures. Both are selected on failure; neither transfers to the fold.

On "BC klein failures": there is NO per-cell pass/fail record for a correctly built BC on
this matrix. The reviewer judged the VEi arm only (im2_pass_audit + im2_failure_audit ->
v34_im2_truth.json); the four-way page's best_arm column defaults to VEi and was actively
marked on 3 cells of 600. The nearest thing is v3.3's `fail` verdict - both arms failed -
and that BC was BCA4-class, the build where head subtraction never ran (v3.4 RESULTS 10).
Those cells are already inside v34_failures.csv by construction, so the union below is the
best available BC-failure coverage. The four named BC_klein failures of v3.0 are on a
different fold (`HD_p023` and friends) and are not in this matrix at all.

  python3 v3/build/make_v35_linkC_set.py   ->  v3/testsets/v35_linkC.csv
"""
import collections
import csv
import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TRUTH = os.path.join(REPO, "v34_im2_truth.json")
V33SET = os.path.join(REPO, "v3", "testsets", "v34_failures.csv")
MATRIX = os.path.join(REPO, "v3", "colab", "matrix.csv")
OUT = os.path.join(REPO, "v3", "testsets", "v35_linkC.csv")
FIELDS = ["set_id", "person", "person_file", "garment", "garment_file", "person_framing",
          "source", "class", "lock46", "lock47", "lock48", "lock_seed_stable",
          "v33_46", "v33_47", "v33_48", "v33_class_seed_stable"]


def main():
    lock = collections.defaultdict(dict)
    for k, v in json.load(open(TRUTH)).items():
        sid, seed = k.split("|")
        lock[sid][seed] = v
    lock_fail = {s: ss for s, ss in lock.items() if any(v == "FAIL" for v in ss.values())}
    v33 = {r["set_id"]: r for r in csv.DictReader(open(V33SET))}
    mx = {r["set_id"]: r for r in csv.DictReader(open(MATRIX))}

    rows = []
    for sid in sorted(set(lock_fail) | set(v33)):
        assert sid in mx, f"{sid} is not in the 200-pair matrix"
        r, ss, t = mx[sid], lock.get(sid, {}), v33.get(sid)
        src = ("both" if sid in lock_fail and t else "v34_lock" if sid in lock_fail else "v33")
        rows.append({
            "set_id": sid, "person": r["person"], "person_file": r["person_file"],
            "garment": r["garment"], "garment_file": r["garment_file"],
            "person_framing": r["person_framing"], "source": src,
            "class": (t or {}).get("class", ""),
            "lock46": ss.get("46", ""), "lock47": ss.get("47", ""), "lock48": ss.get("48", ""),
            "lock_seed_stable": ("yes" if ss and all(v == "FAIL" for v in ss.values())
                                 else "no" if sid in lock_fail else ""),
            "v33_46": (t or {}).get("v46", ""), "v33_47": (t or {}).get("v47", ""),
            "v33_48": (t or {}).get("v48", ""),
            "v33_class_seed_stable": (t or {}).get("seed_stable", "")})

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    c = collections.Counter(r["source"] for r in rows)
    print(f"{OUT}: {len(rows)} pairs · v3.4 lock only {c['v34_lock']} · v3.3 only {c['v33']} "
          f"· both {c['both']} · {len({r['garment'] for r in rows})} garments")


if __name__ == "__main__":
    main()
