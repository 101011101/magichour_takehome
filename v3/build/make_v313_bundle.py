"""Pack what the v3.13 notebook needs into `v313_bundle.zip` at the repo root.

Small, because this run generates nothing: the candidate definitions and the set. The models
are fetched by pinned URL in the notebook and checked by sha256 there.

  python3 v3/build/make_v313_bundle.py
"""
import os
import zipfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v313_bundle.zip")
FILES = [("v3/colab/lib/run_v313.py", "lib/run_v313.py"),
         ("v3/colab/v313_set.csv", "v313_set.csv")]


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
