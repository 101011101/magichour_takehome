"""Build the 200-pair full-run matrix from test_set3.

56 on-model images give 3,080 ordered pairs; 200 is a selection and the selection is
the design. Two rules:

  1  EVERY image appears on both sides. Each of the 56 is a person input at least 3
     times and a garment source at least 3 times, so no result can be an artefact of
     one image never being asked to do one job.
  2  Deterministic, no randomness. Person i takes garments (i+k) mod 56 for k in a
     fixed offset list, skipping self-pairs. Offsets are coprime-ish with 56 so the
     pairings spread rather than clustering.

No stratification by garment type or framing: the fold already showed the framing
distribution is uneven (19 full-body, 9 cropped of 28) and forcing balance would
misrepresent what the set actually contains.
"""
import csv
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v3", "testsets", "v3_full_matrix.csv")
TARGET = 200
OFFSETS = [1, 5, 13, 23, 31, 41]      # spread, none sharing a factor with 56 except 1


def main():
    rows = list(csv.DictReader(open(os.path.join(REPO, "test_set3", "manifest.csv"))))
    ids = [r["id"] for r in rows]
    meta = {r["id"]: r for r in rows}
    n = len(ids)
    pairs, seen = [], set()
    for off in OFFSETS:
        for i in range(n):
            if len(pairs) >= TARGET:
                break
            p, g = ids[i], ids[(i + off) % n]
            if p == g or (p, g) in seen:
                continue
            seen.add((p, g))
            pairs.append((p, g))
        if len(pairs) >= TARGET:
            break

    out = []
    for k, (p, g) in enumerate(pairs, 1):
        mp, mg = meta[p], meta[g]
        out.append({
            "pair": k, "set_id": f"{p}+{g}",
            "person": p, "person_file": os.path.basename(mp["path"]),
            "person_pose": mp["pose"], "person_tone": mp["skin_tone"],
            "person_gender": mp["gender"], "person_framing": mp["framing"],
            "garment": g, "garment_file": os.path.basename(mg["path"]),
            "garment_category": mg["category"], "garment_hard_case": mg["hard_case"],
            "garment_src": mg["source_set"],
        })
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)

    import collections
    cp = collections.Counter(r["person"] for r in out)
    cg = collections.Counter(r["garment"] for r in out)
    print(f"{OUT}\n  {len(out)} pairs, {len(cp)} distinct persons, "
          f"{len(cg)} distinct garments")
    print(f"  as person : min {min(cp.values())}  max {max(cp.values())}")
    print(f"  as garment: min {min(cg.values())}  max {max(cg.values())}")
    print(f"  images never used as person : {n - len(cp)}")
    print(f"  images never used as garment: {n - len(cg)}")


if __name__ == "__main__":
    main()
