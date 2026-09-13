"""Write `v3/colab/v312_set.csv` - the ten product shots against two full-body people.

The question is Runbo's: if a user uploads a flat-lay or ghost-mannequin garment and asks for
`upper`, what happens. v3.11 answered only half of it, and only about the detector: Pose reports
a hip on 6 of these 10 person-free photographs. It never generated a try-on from one, so
"6 of 10" has never been joined to an outcome. This set joins it.

The garments are the ten `test_set1` product shots the v3.11 inquiry used, so the hip reads are
comparable to the ones already on record. The people are full-body and already clean in the
v3.10 count, taken from `v311_set.csv` so nothing new about the person side enters here.

  python3 v3/build/make_v312_set.py
"""
import csv
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V311 = os.path.join(REPO, "v3", "colab", "v311_set.csv")
OUT = os.path.join(REPO, "v3", "colab", "v312_set.csv")
SEED = 46
# the ten product-only garments of `test_set1`, as the v3.11 inquiry used them
GARMENTS = ("g001", "g002", "g008", "g010", "g016", "g017", "g021", "g023", "g026", "g028")
N_PEOPLE = 2


def main():
    rows = list(csv.DictReader(open(V311)))
    # people only: a v3.11 row's `garment` can also appear as someone's `person`, and a garment
    # stem standing in as a person would muddle a set about garments
    people = [r for r in rows if r["person"].startswith("p")]
    seen, picked = set(), []
    for r in sorted(people, key=lambda r: r["person"]):
        if r["person"] in seen:
            continue
        seen.add(r["person"])
        picked.append(r)
        if len(picked) == N_PEOPLE:
            break
    if len(picked) < N_PEOPLE:
        raise SystemExit(f"only {len(picked)} full-body people in {V311}")
    for r in picked:
        assert r["person_framing"] == "full_body", f"{r['person']} is not full_body"

    out = []
    for g in GARMENTS:
        for p in picked:
            out.append({"set_id": f"{p['person']}+{g}", "person": p["person"], "garment": g,
                        "seed": SEED, "person_framing": p["person_framing"],
                        "garment_kind": "product"})
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"{os.path.relpath(OUT, REPO)}  ({len(out)} cells · {len(GARMENTS)} product garments "
          f"· people {[p['person'] for p in picked]} · seed {SEED})")


if __name__ == "__main__":
    main()
