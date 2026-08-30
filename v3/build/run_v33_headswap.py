"""v3.3 link 1.3: MH - klein replaces the HEAD with a mannequin head, nothing else, and
the result goes through the A4 crop. A subtraction, which is what klein is good at; no
garment pixel is regenerated.

  call 1  klein on the normalised photograph, HEAD_PROMPT, seed 46 -> refs/{g}__MHraw.jpg
  crop    BiRefNet A4 on that                                       -> refs/{g}__MH.jpg
"""
import csv
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
import v3lib as L  # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
HEAD_PROMPT = ("Replace this person's head with a smooth, featureless mannequin head of "
               "the same size, in the same position and facing the same way - no face, "
               "no hair. Keep the clothing, the body, the hands, the pose and the "
               "background exactly as they are.")


def load_env():
    for line in open(os.path.join(REPO, ".env")):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main():
    load_env()
    L.MODEL_DIR = os.path.join(REPO, "v2", "runs", ".models")
    paths = L.fetch_models(verbose=False)
    gs = sorted({r["garment"] for r in csv.DictReader(
        open(os.path.join(REPO, "v3/testsets/v30_matrix_b.csv")))})
    jobs = []
    for g in gs:
        out = os.path.join(RUN, "refs", f"{g}__MHraw.jpg")
        if os.path.exists(out):
            continue
        img = cv2.imread(os.path.join(RUN, "inputs", f"{g}.jpg"))
        jobs.append((out, (lambda b=img: L.call(
            L.KLEIN, {"image_urls": [L.b64(b)], "prompt": HEAD_PROMPT, "seed": L.SEED}))))
    print(f"{len(gs)} refs, {len(jobs)} klein calls", flush=True)
    with ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(fn): out for out, fn in jobs}
        for f in as_completed(futs):
            try:
                cv2.imwrite(futs[f], f.result(), [cv2.IMWRITE_JPEG_QUALITY, 95])
                print("  ok  ", os.path.basename(futs[f]), flush=True)
            except Exception as e:
                print("  FAIL", os.path.basename(futs[f]), str(e)[:100], flush=True)
                if "balance" in str(e).lower():
                    break
    for g in gs:
        out = os.path.join(RUN, "refs", f"{g}__MH.jpg")
        raw = os.path.join(RUN, "refs", f"{g}__MHraw.jpg")
        if os.path.exists(out) or not os.path.exists(raw):
            continue
        cv2.imwrite(out, L.crop_a4(cv2.imread(raw), paths), [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("  crop", g, flush=True)
    print("done")


if __name__ == "__main__":
    main()
