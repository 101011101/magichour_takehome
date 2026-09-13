"""Pack what the v3.12 notebook needs into `v312_bundle.zip` at the repo root.

v3.11's bundle plus `run_v312.py` and this run's set. The pipeline modules are unchanged -
v3.12 adds no stage, it only points the shipping path at garment-only photographs and draws
the cut line.

  python3 v3/build/make_v312_bundle.py
"""
import os
import zipfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v312_bundle.zip")
FILES = [("v3/colab/lib/klein_local.py", "lib/klein_local.py"),
         ("v3/colab/lib/v3lib.py", "lib/v3lib.py"),
         ("v3/colab/lib/run_v36.py", "lib/run_v36.py"),
         ("v3/colab/lib/run_v311.py", "lib/run_v311.py"),
         ("v3/colab/lib/run_v312.py", "lib/run_v312.py"),
         ("v3/build/ironman_bc_crop.py", "lib/ironman_bc_crop.py"),
         ("v2/build/garment_crop.py", "lib/garment_crop.py"),
         ("v2/build/phase3_variants.py", "lib/phase3_variants.py"),
         ("v3/colab/v312_set.csv", "v312_set.csv")]


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
