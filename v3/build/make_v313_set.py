"""Write `v3/colab/v313_set.csv` - every photograph whose person-or-not answer is known.

Ground truth is `test_set1/manifest.csv`, never a judgement of the picture: a garment shot
flat_lay or ghost_mannequin has no person in it; a garment shot on_model does, and so does
every photograph the fold uses as a garment source.

The on_model garments are a SUBSET of the fold's stems - 13 of the 56 - so adding the two
lists without dropping duplicates counts those 13 twice and inflates the denominator. They are
de-duplicated here, which is why the set is 73 images and not 86.

  python3 v3/build/make_v313_set.py
"""
import csv
import glob
import os
import subprocess

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v3", "colab", "v313_set.csv")
FOLD = os.path.join(REPO, "v3", "runs", "v310", "a100", "in1mp", "*.jpg")
DIRS = ("test_set1/people", "test_set1/garments", "test_set2/people", "test_set2/clothes",
        "test_set3/people", "test_set2/garments")


def main():
    tracked = set(subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                                 cwd=REPO).stdout.split())
    man = {r["id"]: r for r in csv.DictReader(open(os.path.join(REPO, "test_set1/manifest.csv")))}
    mx = list(csv.DictReader(open(os.path.join(REPO, "v3/colab/matrix.csv"))))
    files = {r["person"]: r["person_file"] for r in mx}
    files.update({r["garment"]: r["garment_file"] for r in mx})

    def resolve(stem):
        f = files.get(stem) or f"{stem}.jpg"
        for d in DIRS:
            if f"{d}/{f}" in tracked:
                return f"{d}/{f}"
        return None

    rows, seen = [], set()
    for p in sorted(glob.glob(FOLD)):
        stem = os.path.splitext(os.path.basename(p))[0]
        path = resolve(stem)
        if not path:
            raise SystemExit(f"{stem} is not a tracked file - Colab could not fetch it")
        rows.append({"stem": stem, "path": path, "truth": "person",
                     "why": man.get(stem, {}).get("photo_style") or "worn, fold garment"})
        seen.add(stem)
    for i, r in man.items():
        if r["kind"] == "garment" and r["photo_style"] in ("flat_lay", "ghost_mannequin"):
            if i in seen:
                raise SystemExit(f"{i} is both a fold garment and a person-free shot")
            path = resolve(i)
            if not path:
                raise SystemExit(f"{i} is not a tracked file")
            rows.append({"stem": i, "path": path, "truth": "no_person", "why": r["photo_style"]})
            seen.add(i)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["stem", "path", "truth", "why"])
        w.writeheader()
        w.writerows(rows)
    n_p = sum(1 for r in rows if r["truth"] == "person")
    print(f"{os.path.relpath(OUT, REPO)}  {len(rows)} images: {n_p} with a person, "
          f"{len(rows) - n_p} without")


if __name__ == "__main__":
    main()
