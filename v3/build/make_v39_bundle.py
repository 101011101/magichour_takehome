"""Pack what the v3.9 notebook needs into `v39_bundle.zip` at the repo root.

Both klein calls and the V2 cropper, so unlike v36's call-2-only bundle this one carries the
cropper modules verbatim (garment_crop, phase3_variants, ironman_bc_crop - no rewrites, the
BCA4 lesson). The notebook fetches it from GitHub raw, which means **the zip has to be
committed and pushed before the notebook is run**.

  python3 v3/build/make_v39_bundle.py
"""
import os
import zipfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v39_bundle.zip")
FILES = [("v3/colab/lib/klein_local.py", "lib/klein_local.py"),
         ("v3/colab/lib/v3lib.py", "lib/v3lib.py"),
         ("v3/colab/lib/run_v36.py", "lib/run_v36.py"),
         ("v3/colab/lib/run_v39.py", "lib/run_v39.py"),
         ("v3/build/ironman_bc_crop.py", "lib/ironman_bc_crop.py"),
         ("v2/build/garment_crop.py", "lib/garment_crop.py"),
         ("v2/build/phase3_variants.py", "lib/phase3_variants.py"),
         ("v3/colab/v39_set.csv", "v39_set.csv")]


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
