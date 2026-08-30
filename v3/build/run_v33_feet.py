"""v3.3 phase 5: feet out of the reference. Four placements of the cut, then the edit.
  R1 ankle-after   CPU cut on the Q3 reference at the ankles
  R2 hem-after     as R1, but never through a hem: cut at the lowest non-white row above the ankles if higher
  R3 ankle-before  A4 crop cut at the ankles -> klein (M1 + clause on the new read + hold) -> re-crop
  R4 prompt        Q3 prompt + "The frame ends at the ankles; the feet are outside it."
Usage: run_v33_feet.py [garment ...]   (default: the probe pair g013 g012)
"""
import csv, json, os, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2, numpy as np
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib")); sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import v3lib as L
from run_v33_phase2 import recrop, load_env
from run_v33_phase3 import build
RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
META = os.path.join(RUN, "_v33_p5_prompts.json")
FEET_OUT = " The frame ends at the ankles; the feet are outside it."
ARMS = ["R1_ankleafter", "R2_hemafter", "R3_anklebefore", "R4_prompt"]
MARGIN = 0.03


def ankle_y(bgr, paths):
    res = L._poser(paths).detect(L._mp_image(bgr))
    if not res.pose_landmarks: return None
    lm = res.pose_landmarks[0]
    ys = [lm[i].y for i in (27, 28) if lm[i].visibility >= 0.5]
    return int(min(ys) * bgr.shape[0]) if ys else None


FALLBACK = {}   # garment -> ankle ratio measured on the A4 crop, used when the reader fails on the reference


def cut_ankle(bgr, paths, g=None):
    y = ankle_y(bgr, paths)
    if y is None and g in FALLBACK: y = int(FALLBACK[g] * bgr.shape[0])
    if y is None: return bgr, None
    y = max(1, int(y - MARGIN * bgr.shape[0]))
    return bgr[:y], y


def cut_hem(bgr, paths, g=None):
    y = ankle_y(bgr, paths)
    if y is None and g in FALLBACK: y = int(FALLBACK[g] * bgr.shape[0])
    if y is None: return bgr, None
    ya = max(1, int(y - MARGIN * bgr.shape[0]))
    # lowest row above the ankle line whose centre third is non-white (the hem)
    w = bgr.shape[1]; band = bgr[:ya, w // 3: 2 * w // 3]
    rows = np.where((band < 245).any(axis=2).any(axis=1))[0]
    yh = int(rows.max()) + 1 if len(rows) else ya
    return bgr[:min(ya, yh)], min(ya, yh)


def main(garments):
    load_env(); L.MODEL_DIR = os.path.join(REPO, "v2", "runs", ".models"); paths = L.fetch_models(verbose=False)
    rows = [r for r in csv.DictReader(open(os.path.join(REPO, "v3/testsets/v30_matrix_b.csv"))) if r["garment"] in garments]
    meta = json.load(open(META)) if os.path.exists(META) else {}
    gen_jobs, ref_jobs = [], []
    for r in rows:
        g, p, sid = r["garment"], r["person"], r["set_id"]
        q3 = cv2.imread(os.path.join(RUN, "refs", f"{g}__p3_Q3_garment.jpg"))
        a4 = cv2.imread(os.path.join(RUN, "inputs", f"{g}__A4.jpg"))
        ya4 = ankle_y(a4, paths)
        if ya4 is not None: FALLBACK[g] = ya4 / a4.shape[0]
        # R1 / R2: CPU cuts on the finished Q3 reference
        for arm, fn in (("R1_ankleafter", cut_ankle), ("R2_hemafter", cut_hem)):
            out = os.path.join(RUN, "refs", f"{g}__p5_{arm}.jpg")
            im, y = fn(q3, paths, g); cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
            meta[f"{g}|{arm}"] = {"cut_row": y, "of": q3.shape[0], "source": "p3_Q3_garment", "prompt": None,
                                  "reader_on_reference": ankle_y(q3, paths) is not None}
        # R3: cut the crop, re-read framing, klein
        cut, y = cut_ankle(a4, paths); fr = L.framing(cut, paths)["framing"]
        pr3 = build("Q3_garment", fr)
        meta[f"{g}|R3_anklebefore"] = {"cut_row": y, "of": a4.shape[0], "framing_after_cut": fr, "prompt": pr3, "seed": L.SEED}
        out3 = os.path.join(RUN, "refs", f"{g}__p5_R3_anklebefore.jpg")
        if not os.path.exists(out3):
            ref_jobs.append((out3, (lambda b=cut, q=pr3: L.call(L.KLEIN, {"image_urls": [L.b64(b)], "prompt": q, "seed": L.SEED}))))
        # R4: prompt only, on the uncut crop
        fr4 = L.framing(a4, paths)["framing"]; pr4 = build("Q3_garment", fr4) + FEET_OUT
        meta[f"{g}|R4_prompt"] = {"framing": fr4, "prompt": pr4, "seed": L.SEED}
        out4 = os.path.join(RUN, "refs", f"{g}__p5_R4_prompt.jpg")
        if not os.path.exists(out4):
            ref_jobs.append((out4, (lambda b=a4, q=pr4: L.call(L.KLEIN, {"image_urls": [L.b64(b)], "prompt": q, "seed": L.SEED}))))
    json.dump(meta, open(META, "w"), indent=1)
    print(f"{len(rows)} refs; {len(ref_jobs)} klein reference calls", flush=True)
    with ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(fn): out for out, fn in ref_jobs}
        for f in as_completed(futs):
            try:
                im = f.result(); cv2.imwrite(futs[f], recrop(im), [cv2.IMWRITE_JPEG_QUALITY, 95]); print("  ref ", os.path.basename(futs[f]), "BLACK" if im.mean() < 5 else "", flush=True)
            except Exception as e: print("  FAIL", os.path.basename(futs[f]), str(e)[:100], flush=True)
    for r in rows:
        g, p, sid = r["garment"], r["person"], r["set_id"]
        person = cv2.imread(os.path.join(RUN, "inputs", f"{p}.jpg"))
        for arm in ARMS:
            out = os.path.join(RUN, "gen", f"{sid}__{arm}.jpg"); ref = os.path.join(RUN, "refs", f"{g}__p5_{arm}.jpg")
            if os.path.exists(out) or not os.path.exists(ref): continue
            gen_jobs.append((out, (lambda a=person, b=cv2.imread(ref): L.call(L.KLEIN, {"image_urls": [L.b64(a), L.b64(b)], "prompt": L.EDIT_PROMPT, "seed": L.SEED}))))
    print(f"{len(gen_jobs)} edits", flush=True)
    with ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(fn): out for out, fn in gen_jobs}
        for f in as_completed(futs):
            try:
                im = f.result(); cv2.imwrite(futs[f], im, [cv2.IMWRITE_JPEG_QUALITY, 95]); print("  edit", os.path.basename(futs[f]), "BLACK" if im.mean() < 5 else "", flush=True)
            except Exception as e: print("  FAIL", os.path.basename(futs[f]), str(e)[:100], flush=True)
    print("done")


if __name__ == "__main__":
    main(sys.argv[1:] or ["g013", "g012"])
