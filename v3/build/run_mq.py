"""The v3.1 mannequin arm end to end, over the whole run-B fold.

Everything v3.1 established, assembled and run on all 28 pairs so it can be compared
against BC_klein and QX on identical inputs:

  1  crop      A4 - BiRefNet_lite @1024, background removed, head KEPT, cropped to the
                    subject bbox. CPU. Chosen over the cheap matte because that one
                    removes garment, and over the head-cut because that one loses the
                    context the hair needs.
  2  read      pose -> extent clause          (36 ms)
               skin -> colour phrase from the PAIRED PERSON, quantised to the ladder
  3  extract   Qwen-Image-Edit-2511, full p7.3                       call 1
  4  edit      klein, the V2 AMT prompt, seed 46                     call 2

Two calls, which is the production budget. Everything before step 3 is CPU.
Outputs land as gen/{set_id}__MQ.jpg, beside BC and QX from the same fold.
"""
import csv
import json
import os
import sys
import time

import cv2
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v2", "build"))
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import garment_crop as G      # noqa: E402
import phase3_fal as F        # noqa: E402
import phase3_variants as PV  # noqa: E402
import run_p7n as P           # noqa: E402
import run_v30 as V           # noqa: E402
import skin_tone as S         # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
QWEN = "fal-ai/qwen-image-edit-2511"
KLEIN = "fal-ai/flux-2/klein/4b/distilled/edit"
SEED = 46
PAD = 0.04


def crop_a4(stem):
    """A4: BiRefNet @1024, background white, head kept, cropped to subject bbox."""
    out = os.path.join(RUN, "inputs", f"{stem}__A4.jpg")
    if os.path.exists(out):
        return out
    img = cv2.imread(os.path.join(RUN, "inputs", f"{stem}.jpg"))
    h, w = img.shape[:2]
    t = time.time()
    prob, _ = G.biref_matte(img, f"mq_{stem}", False)
    subj = G.drop_specks(prob)
    ys, xs = np.where(subj > 0.5)
    if len(ys) < 20:
        b = (0, 0, w, h)
    else:
        py, px = int(h * PAD), int(w * PAD)
        b = (max(0, xs.min() - px), max(0, ys.min() - py),
             min(w, xs.max() + px), min(h, ys.max() + py))
    G.write_rgb(out, PV.flatten(img[b[1]:b[3], b[0]:b[2]],
                                subj[b[1]:b[3], b[0]:b[2]], PV.WHITE))
    print(f"  crop {stem}  {time.time()-t:.0f}s", flush=True)
    return out


def main():
    F._load_env()
    rows = list(csv.DictReader(open(os.path.join(REPO, "v3/testsets/v30_matrix_b.csv"))))
    stage = sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "all"

    if stage in ("crop", "all"):
        for r in rows:
            crop_a4(r["garment"])
        if stage == "crop":
            return

    log = {}
    if stage in ("extract", "all"):
        jobs = []
        for r in rows:
            g, person = r["garment"], r["person"]
            src = os.path.join(RUN, "inputs", f"{g}__A4.jpg")
            if not os.path.exists(src):
                print(f"  skip {g}: no A4 crop")
                continue
            t = S.tone(cv2.imread(os.path.join(RUN, "inputs", f"{person}.jpg")))
            colour = t["name"] if t else "beige skin"
            fr = S.framing(cv2.imread(src))["framing"]
            prompt = P.PREFIX + colour + " " + P.SUFFIX + P.FRAME_SENTENCE[fr]
            log[g] = {"prompt": prompt, "colour": colour, "framing": fr,
                      "person": person, "crop": os.path.relpath(src, REPO)}
            if not os.path.exists(os.path.join(RUN, "refs", f"{g}__MQ.jpg")):
                jobs.append((g, prompt, src))
        json.dump(log, open(os.path.join(RUN, "_mq_prompts.json"), "w"), indent=1)
        print(f"extract: {len(jobs)} qwen calls")
        if jobs and "--dry" not in sys.argv:
            res = F.run([(k, (lambda pr=p, gp=gp: F.call(
                QWEN, {"image_urls": [F._b64(cv2.imread(gp))], "prompt": pr,
                       "seed": SEED}))) for k, p, gp in jobs], 6)
            for k, v in res.items():
                if v is not None:
                    G.write_rgb(os.path.join(RUN, "refs", f"{k}__MQ.jpg"), v)
        if stage == "extract":
            return

    if stage in ("edit", "all"):
        jobs = []
        for r in rows:
            ref = os.path.join(RUN, "refs", f"{r['garment']}__MQ.jpg")
            out = os.path.join(RUN, "gen", f"{r['set_id']}__MQ.jpg")
            if os.path.exists(out) or not os.path.exists(ref):
                continue
            jobs.append((r["set_id"], (
                lambda p=os.path.join(RUN, "inputs", f"{r['person']}.jpg"), rp=ref:
                F.call(KLEIN, {"image_urls": [F._b64(cv2.imread(p)), F._b64(cv2.imread(rp))],
                               "prompt": V.PROMPT, "seed": SEED}))))
        print(f"edit: {len(jobs)} klein calls (~${len(jobs)*0.015:.2f})")
        if jobs and "--dry" not in sys.argv:
            res = F.run(jobs, 6)
            for k, v in res.items():
                if v is not None:
                    G.write_rgb(os.path.join(RUN, "gen", f"{k}__MQ.jpg"), v)

    n = len([1 for r in rows
             if os.path.exists(os.path.join(RUN, "gen", f"{r['set_id']}__MQ.jpg"))])
    print(f"\n{n}/{len(rows)} MQ outputs on disk")


if __name__ == "__main__":
    main()
