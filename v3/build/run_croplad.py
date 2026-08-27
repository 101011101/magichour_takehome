"""Phase 4: the crop-quality ladder.

Six preparations of the same six references, monotone in CPU cost, one prompt held
fixed at the full p7.3. The question is where quality stops improving - and in
particular whether BiRefNet at 1024, which is 48.9 of the crop's 49 seconds, earns its
place when the consumer regenerates rather than subtracts.

  A0 raw          the photograph                                        0
  A1 bbox         subject bounding box from pose, background KEPT       ~40 ms
  A2 mask256      bbox + background removed, Selfie Multiclass 256      ~150 ms
  A4 biref1024    bbox + background removed, BiRefNet at 1024           measured
  A5 biref1024h   as A4 plus head removed                               measured

A3 was to have been BiRefNet at 512 - the same model at a quarter of the pixels, as the
interpolation point between 151 ms and 49 s. It cannot be run: BiRefNet_lite.onnx is
exported with STATIC 1024x1024 input dimensions and onnxruntime rejects any other shape.
There is no resolution knob without re-exporting the model from the PyTorch weights, so
the ladder has no middle rung and the choice really is 151 ms or 49 s.

A1 is the arm that separates cropping from background removal. They have always been
done together; they are different operations at very different prices.

Timings and an edge-roughness figure against A4 are recorded for every arm, so a null
result can be read as "the difference is real and does not matter" rather than "there
was no difference".
"""
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
import run_haircohort as HC   # noqa: E402
import run_phase3 as R3       # noqa: E402
import skin_tone as S         # noqa: E402

RUN = os.path.join(REPO, "v3", "runs", "v3.0b")
QWEN = "fal-ai/qwen-image-edit-2511"
SEED = 46
ARMS = ["A0raw", "A1bbox", "A2mask256", "A4biref1024", "A5biref1024h"]
PAD = 0.04


def _bbox(mask, shape):
    ys, xs = np.where(mask > 0.5)
    if len(ys) < 20:
        return 0, 0, shape[1], shape[0]
    py, px = int(shape[0] * PAD), int(shape[1] * PAD)
    return (max(0, xs.min() - px), max(0, ys.min() - py),
            min(shape[1], xs.max() + px), min(shape[0], ys.max() + py))


def prep(stem, timings):
    """Build every arm's input for one reference. Returns {arm: path}."""
    img = cv2.imread(os.path.join(RUN, "inputs", f"{stem}.jpg"))
    h, w = img.shape[:2]
    out = {"A0raw": os.path.join(RUN, "inputs", f"{stem}.jpg")}

    def save(arm, im):
        p = os.path.join(RUN, "inputs", f"{stem}__{arm}.jpg")
        G.write_rgb(p, im)
        out[arm] = p

    # A1 - pose bbox, background kept
    t = time.time()
    res = S._poser().detect(S._mp_image(img))
    if res.pose_landmarks:
        lms = res.pose_landmarks[0]
        xs = [l.x for l in lms if l.visibility > 0.3]
        ys = [l.y for l in lms if l.visibility > 0.3]
        x0, x1 = max(0, min(xs) - PAD), min(1, max(xs) + PAD)
        y0, y1 = max(0, min(ys) - PAD * 2), min(1, max(ys) + PAD)
        box = (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))
    else:
        box = (0, 0, w, h)
    timings.setdefault("A1bbox", []).append(time.time() - t)
    save("A1bbox", img[box[1]:box[3], box[0]:box[2]])

    # A2 - selfie multiclass 256, background removed
    t = time.time()
    seg = S._segmenter().segment(S._mp_image(img))
    ch = [cv2.resize(m.numpy_view(), (w, h), interpolation=cv2.INTER_LINEAR)
          for m in seg.confidence_masks]
    subj = np.clip(1.0 - ch[0], 0, 1)          # channel 0 is background
    b = _bbox(subj, (h, w))
    timings.setdefault("A2mask256", []).append(time.time() - t)
    save("A2mask256", PV.flatten(img[b[1]:b[3], b[0]:b[2]],
                                 subj[b[1]:b[3], b[0]:b[2]], PV.WHITE))

    # A4 - BiRefNet at its only supported resolution
    t = time.time()
    prob, _ = G.biref_matte(img, f"cl_{stem}_1024", True)
    timings.setdefault("A4biref1024", []).append(time.time() - t)
    subj = G.drop_specks(prob)
    b = _bbox(subj, (h, w))
    save("A4biref1024", PV.flatten(img[b[1]:b[3], b[0]:b[2]],
                                   subj[b[1]:b[3], b[0]:b[2]], PV.WHITE))

    # A5 - the full stack with the head removed
    t = time.time()
    M = PV.masks(img, f"cl_{stem}_full", cranium=False)
    b = _bbox(M["subject"], (h, w))
    timings.setdefault("A5biref1024h", []).append(time.time() - t)
    save("A5biref1024h", PV.flatten(img[b[1]:b[3], b[0]:b[2]],
                                    M["noface"][b[1]:b[3], b[0]:b[2]], PV.WHITE))
    return out


def roughness(path):
    """Edge roughness of the subject silhouette: contour perimeter over the perimeter
    of its own convex hull. A clean outline approaches 1; a staircase exceeds it."""
    a = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if a is None:
        return None
    m = (a < 244).astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return None
    c = max(cs, key=cv2.contourArea)
    hull = cv2.convexHull(c)
    ph = cv2.arcLength(hull, True)
    return round(cv2.arcLength(c, True) / ph, 3) if ph > 0 else None


def main():
    F._load_env()
    timings, inputs = {}, {}
    for stem, hair, person in HC.COHORT:
        inputs[stem] = prep(stem, timings)
        print(f"  prepared {stem}", flush=True)
    stats = {a: round(float(np.mean(v)), 3) for a, v in timings.items()}
    rough = {stem: {a: roughness(p) for a, p in d.items()} for stem, d in inputs.items()}
    json.dump({"seconds": stats, "roughness": rough},
              open(os.path.join(RUN, "_croplad_prep.json"), "w"), indent=1)
    print("seconds per reference: " + " · ".join(f"{k} {v}" for k, v in stats.items()))
    if "--prep-only" in sys.argv:
        return

    log, jobs = {}, []
    for stem, hair, person in HC.COHORT:
        t = S.tone(cv2.imread(os.path.join(RUN, "inputs", f"{person}.jpg")))
        colour = t["name"] if t else "beige skin"
        for arm in ARMS:
            src = inputs[stem][arm]
            fr = S.framing(cv2.imread(src))["framing"]
            # full p7.3, held fixed on every arm
            import run_p7n as P
            prompt = P.PREFIX + colour + " " + P.SUFFIX + P.FRAME_SENTENCE[fr]
            key = f"{stem}|cl.{arm}"
            log[key] = {"prompt": prompt, "colour": colour, "framing": fr,
                        "hair": hair, "arm": arm, "input": os.path.relpath(src, REPO)}
            if not os.path.exists(os.path.join(RUN, "refs", f"{stem}__cl.{arm}.jpg")):
                jobs.append((key, prompt, src))
    json.dump(log, open(os.path.join(RUN, "_croplad_prompts.json"), "w"), indent=1)
    print(f"{len(HC.COHORT)} references x {len(ARMS)} arms, {len(jobs)} to run")
    if "--dry" in sys.argv or not jobs:
        return
    res = F.run([(k, (lambda pr=p, gp=gp: F.call(
        QWEN, {"image_urls": [F._b64(cv2.imread(gp))], "prompt": pr, "seed": SEED})))
        for k, p, gp in jobs], 6)
    for k, v in res.items():
        if v is not None:
            G.write_rgb(os.path.join(RUN, "refs", f"{k.replace('|', '__')}.jpg"), v)
    print(f"\n{sum(1 for v in res.values() if v is not None)}/{len(jobs)} written")


if __name__ == "__main__":
    main()
