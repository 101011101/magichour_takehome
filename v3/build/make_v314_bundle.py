"""v314_bundle.zip - the runner, the set, and the crop modules the notebook imports.

  python3 v3/build/make_v314_bundle.py
"""
import os
import zipfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v314_bundle.zip")
FILES = {
    "lib/klein_local.py": "v3/colab/lib/klein_local.py",
    "lib/v3lib.py": "v3/colab/lib/v3lib.py",
    "lib/run_v314.py": "v3/colab/lib/run_v314.py",
    "lib/garment_crop.py": "v2/build/garment_crop.py",
    "lib/phase3_variants.py": "v2/build/phase3_variants.py",
    "lib/ironman_bc_crop.py": "v3/build/ironman_bc_crop.py",
    "v314_set.csv": "v3/colab/v314_set.csv",
}


def main():
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, src in FILES.items():
            p = os.path.join(REPO, src)
            if not os.path.exists(p):
                raise SystemExit(f"missing {src}")
            z.write(p, arc)
    print(f"{OUT}  ({os.path.getsize(OUT) // 1024} KB)")
    for n in zipfile.ZipFile(OUT).namelist():
        print("  ", n)
    print("\ncommit and push it before running the notebook - it is fetched from GitHub")


if __name__ == "__main__":
    main()
