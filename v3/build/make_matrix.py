"""Build the v3.0 evaluation matrix from test_set2.

Garment-driven by design: failure is a property of the garment reference, so the
matrix is 12 references x 3 person inputs rather than 36 arbitrary pairs. The
person rotation is a fixed modular walk over a fixed list, so the same matrix is
produced on every run. Emits v3/testsets/v30_matrix.csv; TEST.md is written from
this file and must not be edited independently.
"""
import csv
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TS2 = os.path.join(REPO, "test_set2")
OUT = os.path.join(REPO, "v3", "testsets", "v30_matrix.csv")

# (stem, folder, kind, stress axis, why this reference is in the set)
GARMENTS = [
    ("dualuse_lp_floral_kimono_set", "clothes", "worn", "BC",
     "dense floral on a loose editorial drape; the V2 kimono reference"),
    ("dualuse_navy_peacoat_onmodel", "clothes", "worn", "BC",
     "high stand collar - the head cut lands on the garment itself"),
    ("dualuse_lp_plaid_overcoat_brown_suit", "clothes", "worn", "both",
     "plaid and a collar together: BC cut-line and QX smoothing in one reference"),
    ("dualuse_lp_beige_long_coat_menswear", "clothes", "worn", "BC",
     "beige against skin - the low-amplitude boundary case"),
    ("dualuse_zendaya_white_blazer_skirt", "people", "worn", "BC",
     "long hair over a white garment on a light ground"),
    ("dualuse_queen_latifah_gown_stage", "people", "worn", "BC",
     "long hair, stage lighting, gown drape"),
    ("dualuse_scarlett_johansson_black_dress_backview_night", "people", "worn", "QX",
     "back view - view-dependent information a regenerated front cannot hold"),
    ("clothesonly_ts1g010_plain_tee_ghost", "clothes", "product", "QX",
     "plain: nothing to extract and everything to invent"),
    ("clothesonly_ts1g026_metallica_text_tee_flat", "clothes", "product", "QX",
     "heavy text - regeneration mangles glyphs"),
    ("clothesonly_ts1g028_fine_stripe_shirt_ghost", "clothes", "product", "QX",
     "fine stripes - the smoothing case"),
    ("clothesonly_ts1g001_graphic_logo_tee", "clothes", "product", "QX",
     "a logo mark: destroyed or invented"),
    ("clothesonly_ts1g008_plaid_flannel", "clothes", "product", "QX",
     "dense plaid without a wearer, so the crop is not a variable"),
]

# Fixed order. The walk below takes three at a time, skipping self-pairs.
PEOPLE = [
    ("dualuse_emma_watson_black_blazer_armscrossed", "long", "light", "frontal"),
    ("dualuse_hugh_jackman_grey_suit_outdoor", "short", "light", "frontal"),
    ("dualuse_woman_top_denim_skirt_nonceleb", "long", "light", "frontal"),
    ("dualuse_queen_latifah_gown_stage", "long", "deep", "frontal"),
    ("dualuse_man_black_suit_studio_nonceleb", "short", "medium", "frontal"),
    ("dualuse_zendaya_white_blazer_skirt", "long", "medium", "frontal"),
    ("dualuse_gal_gadot_blue_dress_redcarpet", "long", "light", "frontal"),
    ("dualuse_scarlett_johansson_black_dress_backview_night", "long", "light", "back"),
]

# In test_set2 but deliberately out of the matrix, with the reason.
EXCLUDED = [
    ("dualuse_lp_navy_quarterzip_knit_LOWRES.avif", "690x966, below the set's own resolution bar"),
    ("clothesonly_ts1g021_blue_jeans_flat.jpg", "lower body only - a different failure axis, held in reserve"),
    ("clothesonly_ts1g023_plaid_mini_skirt_flat.jpg", "lower body only - same reason"),
    ("rejected/", "failed quality check upstream"),
    ("superseded/", "a higher-resolution replacement exists"),
]


def find(stem, folder):
    d = os.path.join(TS2, folder)
    for f in sorted(os.listdir(d)):
        if os.path.splitext(f)[0] == stem:
            return os.path.relpath(os.path.join(d, f), REPO)
    return None


def build():
    ppl = {p[0]: p for p in PEOPLE}
    where = {g[0]: g[1] for g in GARMENTS}
    for p in PEOPLE:
        where.setdefault(p[0], "people")

    rows, i = [], 0
    for g, gfolder, kind, stress, why in GARMENTS:
        picked = []
        while len(picked) < 3:
            cand = PEOPLE[i % len(PEOPLE)][0]
            i += 1
            if cand != g and cand not in picked:
                picked.append(cand)
        for person in picked:
            hair, tone, view = ppl[person][1:]
            rows.append({
                "set_id": f"{person}+{g}",
                "person": person,
                "person_path": find(person, where[person]),
                "person_hair": hair,
                "person_tone": tone,
                "person_view": view,
                "garment": g,
                "garment_path": find(g, gfolder),
                "garment_kind": kind,
                "stress": stress,
                "why": why,
            })
    return rows


def main():
    rows = build()
    missing = [r for r in rows if not r["person_path"] or not r["garment_path"]]
    if missing:
        raise SystemExit(f"missing files: {[(m['person'], m['garment']) for m in missing]}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{OUT}  {len(rows)} pairs, "
          f"{len({r['garment'] for r in rows})} garments, "
          f"{len({r['person'] for r in rows})} people")


if __name__ == "__main__":
    main()
