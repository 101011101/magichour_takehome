"""Pack what the v3.11 notebook needs into `v311_bundle.zip` at the repo root.

Carries the cropper modules, because unlike v3.10 this run builds references: the bald pass and
the head-subtracting crop both run, and the region band is computed inside the crop.

  python3 v3/build/make_v311_bundle.py
"""
import os
import zipfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v311_bundle.zip")
FILES = [("v3/colab/lib/klein_local.py", "lib/klein_local.py"),
         ("v3/colab/lib/v3lib.py", "lib/v3lib.py"),
         ("v3/colab/lib/run_v36.py", "lib/run_v36.py"),
         ("v3/colab/lib/run_v311.py", "lib/run_v311.py"),
         ("v3/build/ironman_bc_crop.py", "lib/ironman_bc_crop.py"),
         ("v2/build/garment_crop.py", "lib/garment_crop.py"),
         ("v2/build/phase3_variants.py", "lib/phase3_variants.py"),
         ("v3/colab/v311_set.csv", "v311_set.csv")]


def main():
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for src, dst in FILES:
            p = os.path.join(REPO, src)
            if not os.path.exists(p):
                raise SystemExit(f"missing {src}")
            z.write(p, dst)
    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None
        names = z.namelist()
    print(f"{os.path.relpath(OUT, REPO)}  ({os.path.getsize(OUT) / 1024:.0f} KB)")
    for n in names:
        print("  ", n)
    print("\ncommit and push it before running the notebook - it is fetched from GitHub raw")


if __name__ == "__main__":
    main()
