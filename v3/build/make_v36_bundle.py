"""Pack what the v3.6 notebook needs into `v36_bundle.zip` at the repo root.

Call 2 only: no cropper, no BiRefNet, no parser, no mediapipe - so the bundle is three
library files and the set. The notebook fetches it from GitHub raw, which means **the zip
has to be committed and pushed before the notebook is run**; it prints the branch it
expects.

  python3 v3/build/make_v36_bundle.py
"""
import os
import zipfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v36_bundle.zip")
FILES = [("v3/colab/lib/klein_local.py", "lib/klein_local.py"),
         ("v3/colab/lib/v3lib.py", "lib/v3lib.py"),
         ("v3/colab/lib/run_v36.py", "lib/run_v36.py"),
         ("v3/colab/v36_editset.csv", "v36_editset.csv"),
         ("v3/colab/v36_ironman_er.csv", "v36_ironman_er.csv"),
         ("v3/colab/v36_er2_set.csv", "v36_er2_set.csv")]


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
