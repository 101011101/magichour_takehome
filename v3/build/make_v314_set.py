"""The v3.14 set: worn garments to compare references on, product shots to test the waist.

Ground truth is the manifest's own `photo_style`, not anyone's reading of the picture:
on_model is worn, flat_lay and ghost_mannequin are product.

  python3 v3/build/make_v314_set.py   ->  v3/colab/v314_set.csv
"""
import csv
import os
import subprocess

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v3", "colab", "v314_set.csv")
MANIFEST = os.path.join(REPO, "test_set1", "manifest.csv")
MATRIX = os.path.join(REPO, "v3", "colab", "matrix.csv")
# the canonical directories - never the 340px report copies
DIRS = ("test_set1/garments", "test_set1/people", "test_set2/clothes", "test_set2/people",
        "test_set3/people", "test_set2/garments")
PRODUCT_STYLES = ("flat_lay", "ghost_mannequin")


def tracked():
    return set(subprocess.run(["git", "-C", REPO, "ls-files"],
                              capture_output=True, text=True).stdout.split())


def locate(fname, files):
    for d in DIRS:
        p = f"{d}/{fname}"
        if p in files:
            return p
    return None


def main():
    files = tracked()
    mx = list(csv.DictReader(open(MATRIX)))
    name = {r["garment"]: r["garment_file"] for r in mx}
    name.update({r["person"]: r["person_file"] for r in mx})
    rows = []
    for r in csv.DictReader(open(MANIFEST)):
        if r["kind"] != "garment":
            continue
        kind = "product" if r["photo_style"] in PRODUCT_STYLES else "worn"
        fname = name.get(r["id"], r["id"] + ".jpg")
        path = locate(fname, files)
        if path is None:
            print(f"  skip {r['id']}: {fname} not tracked")
            continue
        rows.append({"stem": r["id"], "kind": kind, "path": path,
                     "photo_style": r["photo_style"], "category": r["category"]})
    # a handful of fold garments the manifest does not carry, so the worn side is not all
    # of one test set; they are the dress-heavy ones candidate B is expected to struggle on
    for stem in ("p003", "p021", "dualuse_queen_latifah_gown_stage"):
        if any(x["stem"] == stem for x in rows):
            continue
        fname = name.get(stem)
        path = locate(fname, files) if fname else None
        if path:
            rows.append({"stem": stem, "kind": "worn", "path": path,
                         "photo_style": "on_model", "category": "fold"})
    rows.sort(key=lambda r: (r["kind"], r["stem"]))
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["stem", "kind", "path", "photo_style", "category"])
        w.writeheader()
        w.writerows(rows)
    worn = sum(1 for r in rows if r["kind"] == "worn")
    print(f"{OUT}  ({len(rows)} garments: {worn} worn, {len(rows) - worn} product)")


if __name__ == "__main__":
    main()
