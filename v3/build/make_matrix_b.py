"""Build the v3.0 run-B matrix: test_set3 folded in half.

56 on-model images, every one of which can take either side of a pairing. The list
is folded at the midpoint: item i is the person, item i + 28 is the garment source.
28 pairs, every image used exactly once, nothing left over.

Order is manifest order, which is build order and therefore fixed:
test_set1 people (30) -> test_set2 people (8) -> test_set2 on-model (5) ->
test_set1 on-model garments (13). The fold falls so that the plain person set lands
mostly on the person side and the editorial and on-model garment shots land on the
garment side, which is the useful orientation and is a consequence of the order
rather than a thumb on the scale. It is recorded here so it is not mistaken for one.

Emits v3/testsets/v30_matrix_b.csv. TEST.md renders from that file.
"""
import csv
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SET = os.path.join(REPO, "test_set3")
OUT = os.path.join(REPO, "v3", "testsets", "v30_matrix_b.csv")
NOHAIR = 0.0005


def build():
    rows = list(csv.DictReader(open(os.path.join(SET, "manifest.csv"))))
    n = len(rows)
    if n % 2:
        raise SystemExit(f"{n} images: an odd pool cannot be folded cleanly")
    half = n // 2
    out = []
    for i in range(half):
        p, g = rows[i], rows[i + half]
        hf = float(g["hair_frac"]) if g["hair_frac"] else None
        out.append({
            "pair": i + 1,
            "set_id": f"{p['id']}+{g['id']}",
            "person": p["id"],
            "person_path": p["path"],
            "person_src": p["source_set"],
            "person_pose": p["pose"],
            "person_tone": p["skin_tone"],
            "person_gender": p["gender"],
            "person_framing": p["framing"],
            "garment": g["id"],
            "garment_path": g["path"],
            "garment_src": g["source_set"],
            "garment_category": g["category"],
            "garment_hard_case": g["hard_case"],
            "garment_hair_frac": g["hair_frac"],
            # the variable that decides whether BC_klein's bald pass has work to do
            "bald_pass_useful": "" if hf is None else ("no" if hf < NOHAIR else "yes"),
        })
    return out


def main():
    rows = build()
    missing = [r for r in rows
               if not os.path.exists(os.path.join(REPO, r["person_path"]))
               or not os.path.exists(os.path.join(REPO, r["garment_path"]))]
    if missing:
        raise SystemExit(f"missing files: {[m['set_id'] for m in missing]}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    nb = sum(1 for r in rows if r["bald_pass_useful"] == "no")
    print(f"{OUT}  {len(rows)} pairs, {len(rows) * 2} images used once each, "
          f"{nb} garment refs with no hair (bald pass is a no-op there)")


if __name__ == "__main__":
    main()
