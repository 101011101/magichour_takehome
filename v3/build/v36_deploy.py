"""Stage the v3.6 report for deployment: two pages and the images they use, nothing else.

`v3/report/` is 2.3 GB, nearly all of it the marking tools' image directories. The submission
is two pages and one image folder, so the deploy directory is built rather than uploaded
wholesale.

  python3 v3/build/v36_deploy.py     ->  v3/report_v36/
  npx vercel deploy v3/report_v36 --prod
"""
import os
import shutil

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(REPO, "v3", "report")
OUT = os.path.join(REPO, "v3", "report_v36")
PAGES = ["v36_report.html", "v36_findings.html"]
IMGDIR = "img_v36r"

INDEX = """<title>ER - v3.6</title>
<meta http-equiv='refresh' content='0; url=v36_report.html'>
<link rel='canonical' href='v36_report.html'>
<p><a href='v36_report.html'>v3.6 &mdash; ER</a></p>
"""


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    for p in PAGES:
        shutil.copy(os.path.join(SRC, p), os.path.join(OUT, p))
    # only the sizes the pages actually reference: the @full originals are the click-through,
    # and they are what makes the directory large, so they come too - but nothing else does
    shutil.copytree(os.path.join(SRC, IMGDIR), os.path.join(OUT, IMGDIR))
    open(os.path.join(OUT, "index.html"), "w").write(INDEX)
    n = sum(len(f) for _, _, f in os.walk(OUT))
    size = sum(os.path.getsize(os.path.join(r, f))
               for r, _, fs in os.walk(OUT) for f in fs) / 1e6
    print(f"{os.path.relpath(OUT, REPO)}  {n} files, {size:.0f} MB")
    print("  npx vercel deploy v3/report_v36 --prod")


if __name__ == "__main__":
    main()
