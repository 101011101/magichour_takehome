"""v3.3 link 1: the v3.1 extraction call, sent to klein instead of Qwen.

Everything else is the locked v3.1 arm, imported from the Colab library so the prompt
string is the one v3.1 locked (the repo-side run_mq.py predates dynamic prompting):

  input    the A4 crop already on disk from v3.1 link 10
  prompt   v3lib.mq_prompt() - colour from the PAIRED person's face, extent + pose
           from the crop's framing, one table
  call 1   fal-ai/flux-2/klein/4b/distilled/edit   <- the only change
  seed     46

Outputs: v3/runs/v3.0b/refs/{garment}__MK__{person}.jpg and _v33_prompts.json.
Resumable: an output on disk is skipped.
"""
import csv
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
import v3lib as L  # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
MATRIX = os.path.join(REPO, "v3", "testsets", "v30_matrix_b.csv")
META = os.path.join(RUN, "_v33_prompts.json")


def load_env():
    for line in open(os.path.join(REPO, ".env")):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main(limit=None):
    load_env()
    L.MODEL_DIR = os.path.join(REPO, "v2", "runs", ".models")   # already there; no copy
    paths = L.fetch_models(verbose=False)
    rows = list(csv.DictReader(open(MATRIX)))[: int(limit) if limit else None]
    meta = json.load(open(META)) if os.path.exists(META) else {}
    jobs = []
    for r in rows:
        g, p = r["garment"], r["person"]
        out = os.path.join(RUN, "refs", f"{g}__MK__{p}.jpg")
        crop = cv2.imread(os.path.join(RUN, "inputs", f"{g}__A4.jpg"))
        person = cv2.imread(os.path.join(RUN, "inputs", f"{p}.jpg"))
        prompt, colour, fr = L.mq_prompt(person, crop, paths)
        meta[f"{g}|{p}"] = {"prompt": prompt, "colour": colour, "framing": fr,
                            "endpoint": L.KLEIN, "seed": L.SEED}
        if os.path.exists(out):
            continue
        jobs.append((out, (lambda c=crop, q=prompt: L.call(
            L.KLEIN, {"image_urls": [L.b64(c)], "prompt": q, "seed": L.SEED}))))
    json.dump(meta, open(META, "w"), indent=1)
    print(f"{len(rows)} pairs, {len(jobs)} calls to make", flush=True)
    fails = []
    with ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(fn): out for out, fn in jobs}
        for f in as_completed(futs):
            out = futs[f]
            try:
                cv2.imwrite(out, f.result(), [cv2.IMWRITE_JPEG_QUALITY, 95])
                print("  ok  ", os.path.basename(out), flush=True)
            except Exception as e:
                fails.append(out)
                print("  FAIL", os.path.basename(out), str(e)[:100], flush=True)
                if "balance" in str(e).lower():
                    break
    print(f"done: {len(jobs)-len(fails)} made, {len(fails)} failed")


if __name__ == "__main__":
    main(*sys.argv[1:])
