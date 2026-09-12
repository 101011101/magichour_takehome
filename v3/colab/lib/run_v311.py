"""v3.11 - a garment-type selector: upper, lower, or the whole outfit, and two ways to build it.

Runbo, verbatim: "You didn't include a feature that allows users to choose the garment type,
right, like if the user uploads a full body image but just wants to swap like the top."

So the thing being asked for is a **person-side outcome**: a full-body photograph goes in with
REGION=upper, the top is swapped, and the person's own trousers are still their own trousers
afterwards. The reference is only the means. Two ways to build that reference, and this run puts
them side by side.

  A - crop only.       The bald pass is the one of record, byte for byte. The band is cut on the
                       MASK before the bbox, so call 2 receives half a garment on white.
  B - modify call 1.   The bald pass ALSO neutralises the half the user did not select, replacing
                       it with a plain white garment (Ray: "have the first call replace the upper
                       body with a plain white tshirt for the crop to be easier"). A uniform,
                       unpatterned region is an easier thing for a matte and a parser to cut
                       against, so the reference should come out cleaner. Then the same band.

B DEPARTS FROM THE CALL-1 PROMPT OF RECORD. Every v3.8/v3.10 number was made with BALD_PROMPT
exactly as written; arm B sends a different call-1 prompt (BALD_NEUTRAL below, verbatim in
TEST.md), so no number transfers to it. A is the control precisely because its call 1 is
untouched.

Call 2 is `ER`, byte for byte, in both arms. The only variable is how the reference was built.

REGION=full has nothing unselected to neutralise, so B's call 1 would be BALD_PROMPT and its
reference would be A's: `full` is generated once, under A, and the page says so.

THE BAND. The cut is on the mask, before the bbox - cropping the finished picture would leave
the reference's white ground and framing describing a body that is not there. The hip line is
the mean y of Pose landmarks 23/24, counting only hips that are confident AND inside the frame,
which is the pair of tests v3lib.framing applies to its joints.

THE FALLBACK IS NAMED, NEVER GUESSED. No pose, no in-frame hip, or a band keeping less than
MIN_BAND of the subject falls back to `full` and records why, per garment, in meta. Measured
before this was built: Pose finds a hip on 53 of 56 worn bald frames in the archive - and on 6
of 10 flat-lays, which contain no person at all, so "a landmark exists" is not evidence that a
body does.

THE STUB THIS FILLS. `garment_crop.SELECT_REGION` and `region_band` have sat unimplemented since
V2. Their comment records why the earlier attempt was pulled - a band prior "dragged the jeans in
on the navy peacoat" - but that band picked a GARMENT by proportion; this one picks a BODY REGION
from a detected joint.

Inputs (cell 4 unpacks them): inputs/{stem}.jpg.
Resumable: every stage skips what is on disk. Output: run/{in1mp,refs,gen,meta}.
"""
import csv
import json
import os
import platform
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v3lib as L                      # noqa: E402  BALD_PROMPT, the call-1 prompt of record
import klein_local as K                # noqa: E402  the call, and the canvas rules
import run_v36 as V36                  # noqa: E402  ER's prompt, byte for byte as v3.8 sent it

OUT = "run"
MAXPIX = 2 ** 20                       # the production bound since v3.10
REGIONS = ("full", "upper", "lower")
PLAN = (("A", "full"), ("A", "upper"), ("A", "lower"), ("B", "upper"), ("B", "lower"))
CALL1_SEED = 46
L_HIP, R_HIP = 23, 24                  # MediaPipe Pose; phase3_variants names only the head ones
VIS = 0.5                              # v3lib.framing's confidence bar, unchanged
MARGIN = 0.02                          # and its in-frame margin
MIN_BAND = 0.02                        # a band keeping less than this is a sliver, not a reference
JPG = [cv2.IMWRITE_JPEG_QUALITY, 95]
FAL_PER_CALL = 0.015

# Arm B's call 1. BALD_PROMPT's first two sentences unchanged - the bald pass still has to happen
# - then one sentence naming the replacement, then the hold sentence rewritten to hold the half
# the user DID select. The hold clause of record ("keep the clothing ... exactly as they are")
# cannot stand here: it contradicts the replacement in the sentence before it.
BALD_NEUTRAL = {
    "upper": ("Make this person completely bald. Remove all hair from the head and any hair "
              "falling over the shoulders, chest or back, and show the scalp. Replace everything "
              "they are wearing below the waist with plain white trousers, with no pattern, "
              "print or logo. Keep what they are wearing above the waist, the body, the pose and "
              "the background exactly as they are."),
    "lower": ("Make this person completely bald. Remove all hair from the head and any hair "
              "falling over the shoulders, chest or back, and show the scalp. Replace everything "
              "they are wearing above the waist with a plain white t-shirt, with no pattern, "
              "print or logo. Keep what they are wearing below the waist, the body, the pose and "
              "the background exactly as they are."),
}
_T = []


def d(*p):
    q = os.path.join(OUT, *p)
    os.makedirs(os.path.dirname(q), exist_ok=True)
    return q


def normalise(bgr, maxpix=MAXPIX):
    """v3lib.normalise at the production bound: nothing over 1 MP, INTER_AREA down."""
    h, w = bgr.shape[:2]
    if h * w <= maxpix:
        return bgr
    k = (maxpix / (h * w)) ** 0.5
    return cv2.resize(bgr, (int(w * k), int(h * k)), interpolation=cv2.INTER_AREA)


def size_noscale(bgr, maxpix=MAXPIX):
    """The person's own size, floor 32, never upscaled - the shipped call-2 canvas."""
    h, w = bgr.shape[:2]
    k = min(1.0, (maxpix / (h * w)) ** 0.5)
    return max(32, int(h * k) // 32 * 32), max(32, int(w * k) // 32 * 32)


def _canvas(images, prompt, seed, size_fn):
    """klein_local.edit with the canvas function injected; K.edit resolves _size at call time."""
    orig = K._size
    K._size = size_fn
    try:
        return K.edit(images, prompt, seed, canvas="v33")
    finally:
        K._size = orig


def klein(stage, arm, ident, seed, images, prompt, size_fn):
    im, secs = _canvas(images, prompt, seed, size_fn)
    _T.append({"stage": stage, "arm": arm, "id": ident, "seed": seed, "seconds": secs,
               "klein_call": 1})
    return im


# ---------------------------------------------------------------- the band ----
def hip_line(bgr):
    """y of the hip line in pixels, or (None, why).

    The mean of landmarks 23/24, counting only hips that are BOTH confident and inside the
    frame. A hip the detector has placed outside the picture is a guess about a body part the
    photograph does not show, and a band drawn from it would cut at an invented row.
    """
    import mediapipe as mp
    import phase3_variants as P
    lm = P._pose()
    if lm is None:
        return None, "pose unavailable"
    r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                           data=np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))))
    if not r.pose_landmarks:
        return None, "no pose detected"
    p = r.pose_landmarks[0]
    ys = [p[i].y for i in (L_HIP, R_HIP)
          if p[i].visibility >= VIS and -MARGIN <= p[i].x <= 1 + MARGIN
          and -MARGIN <= p[i].y <= 1 + MARGIN]
    if not ys:
        return None, "no hip in frame"
    return float(sum(ys) / len(ys)) * bgr.shape[0], ""


def references(bald_bgr, stem, regions=REGIONS):
    """The requested references off ONE mask computation. Returns {region: (image, info)}.

    `full` reproduces `ironman_bc_crop.crop_bc` exactly - subject bbox, noface alpha - so the
    control is the production reference and not a near-miss of it.
    """
    import garment_crop as G
    import phase3_variants as P
    M = P.masks(bald_bgr, stem, cranium=True)
    subject, alpha = M["subject"], M["noface"]
    shape = bald_bgr.shape[:2]
    full_area = float((alpha > 0.5).sum())
    y, why = (None, "") if tuple(regions) == ("full",) else hip_line(bald_bgr)
    out = {}
    for region in regions:
        info = {"requested": region, "region": region, "fallback": "",
                "hip_y": None if y is None else round(y, 1),
                "cranium_used": bool(M["cranium_used"])}
        band_alpha = alpha
        if region != "full":
            if y is None:
                info["fallback"] = why
            else:
                band = np.zeros(shape, np.float32)
                row = int(round(max(0, min(shape[0], y))))
                if region == "upper":
                    band[:row] = 1.0
                else:
                    band[row:] = 1.0
                kept = alpha * band
                frac = float((kept > 0.5).sum()) / full_area if full_area else 0.0
                info["kept_fraction"] = round(frac, 4)
                if frac < MIN_BAND:
                    info["fallback"] = f"band keeps {frac:.1%} of the subject"
                else:
                    band_alpha = kept
        if info["fallback"]:
            info["region"] = "full"
        box_mask = (subject > 0.5) if info["region"] == "full" else (band_alpha > 0.5)
        x0, y0, x1, y1 = G.bbox_of(box_mask.astype(np.uint8), shape)
        im = P.flatten(bald_bgr[y0:y1, x0:x1], band_alpha[y0:y1, x0:x1], P.WHITE)
        info["size"] = [im.shape[1], im.shape[0]]
        info["mp"] = round(im.shape[0] * im.shape[1] / 2 ** 20, 3)
        out[region] = (im, info)
    return out


def bald_key(arm, region):
    """Which bald frame a (arm, region) reference is cut from.

    A's call 1 does not depend on the region, so one frame serves all three. B's does - the
    prompt names the half being neutralised - so B needs one per region. B/full does not exist:
    with nothing unselected there is nothing to neutralise, and it would be A's frame.
    """
    return "A" if arm == "A" else f"B_{region}"


def main(matrix="v311_set.csv", plan=PLAN, gpu_usd_per_hour=None, limit=None):
    wall0 = time.time()
    for arm, region in plan:
        if (arm, region) not in PLAN:
            raise SystemExit(f"unknown arm/region {arm}/{region}; one of {PLAN}")
    if not K.info().get("transformer"):
        raise SystemExit("load the production transformer first: K.load(repo=..., "
                         "transformer=(...)) - this runner never falls back to BFL's")
    rows = list(csv.DictReader(open(matrix)))
    if limit:
        rows = rows[:int(limit)]
    garments = sorted({r["garment"] for r in rows})
    stems = sorted({r["person"] for r in rows} | set(garments))
    balds = sorted({bald_key(a, r) for a, r in plan})

    # 0 the production bound
    n = 0
    for s in stems:
        src, out = d("inputs", f"{s}.jpg"), d("in1mp", f"{s}.jpg")
        if not os.path.exists(src):
            raise SystemExit(f"missing {src} - cell 4 unpacks the inputs")
        if os.path.exists(out):
            continue
        cv2.imwrite(out, normalise(cv2.imread(src)), JPG)
        n += 1
    print(f"0 inputs bounded to {MAXPIX} px: {n} written, {len(stems)} total")

    mp_path = d("meta", "v311_meta.json")
    meta = json.load(open(mp_path)) if os.path.exists(mp_path) else {"garments": {}, "cells": {}}
    print(f"{len(rows)} cells · {len(garments)} garments · plan {list(plan)}")

    # 1 call 1 - A's bald pass once per garment; B's once per garment per region it neutralises
    n = 0
    for g in garments:
        for key in balds:
            out = d("refs", f"{g}__bald_{key}.jpg")
            if os.path.exists(out):
                continue
            prompt = L.BALD_PROMPT if key == "A" else BALD_NEUTRAL[key.split("_", 1)[1]]
            src = cv2.imread(d("in1mp", f"{g}.jpg"))
            b = klein("bald", key, g, CALL1_SEED, [src], prompt, K._size)
            b = cv2.resize(b, (src.shape[1], src.shape[0]), interpolation=cv2.INTER_AREA)
            cv2.imwrite(out, b, JPG)
            n += 1
    print(f"1 call 1: {n} bald passes made ({len(balds)} per garment: {balds})")

    # 2 the crops - one mask per bald frame, every region that frame serves cut off it
    want = {}
    for arm, region in plan:
        want.setdefault(bald_key(arm, region), []).append((arm, region))
    for g in garments:
        for key, pairs in sorted(want.items()):
            todo = [(a, r) for a, r in pairs if not os.path.exists(d("refs", f"{g}__{a}_{r}.jpg"))]
            if not todo:
                continue
            t0 = time.time()
            refs = references(cv2.imread(d("refs", f"{g}__bald_{key}.jpg")), f"v311_{key}_{g}",
                              tuple(r for _, r in todo))
            for arm, region in todo:
                im, info = refs[region]
                cv2.imwrite(d("refs", f"{g}__{arm}_{region}.jpg"), im, JPG)
                meta["garments"].setdefault(g, {})[f"{arm}_{region}"] = dict(info, bald=key)
            secs = round(time.time() - t0, 1)
            _T.append({"stage": "crop", "arm": key, "id": g, "seed": 0, "seconds": secs})
            hip = refs[todo[0][1]][1]["hip_y"]
            fb = {f"{a}/{r}": refs[r][1]["fallback"] for a, r in todo if refs[r][1]["fallback"]}
            print(f"    {g[:44]:44s} {key:8s} hip_y={hip} {secs}s"
                  + (f" · fell back: {fb}" if fb else "")
                  + " · " + " ".join(f"{a}/{r}={refs[r][1]['size'][0]}x{refs[r][1]['size'][1]}"
                                     for a, r in todo), flush=True)
            json.dump(meta, open(mp_path, "w"), indent=1)

    # 3 call 2 - ER, byte for byte, on the shipped canvas, for every (arm, region)
    n = 0
    for r in rows:
        sid, seed = r["set_id"], int(r["seed"])
        person = cv2.imread(d("in1mp", f"{r['person']}.jpg"))
        meta["cells"].setdefault(f"{sid}|{seed}", {})["canvas"] = list(size_noscale(person))[::-1]
        for arm, region in plan:
            out = d("gen", f"{sid}__{arm}_{region}__s{seed}.jpg")
            if os.path.exists(out):
                continue
            ref = cv2.imread(d("refs", f"{r['garment']}__{arm}_{region}.jpg"))
            assert ref is not None, f"missing refs/{r['garment']}__{arm}_{region}.jpg"
            im = klein("edit", f"{arm}_{region}", sid, seed, [person, ref], V36.ER, size_noscale)
            cv2.imwrite(out, im, JPG)
            n += 1
            if n % 15 == 0:
                print(f"    {n} edits", flush=True)
                json.dump(meta, open(mp_path, "w"), indent=1)
                _write(rows, plan, wall0, gpu_usd_per_hour)
    json.dump(meta, open(mp_path, "w"), indent=1)
    _write(rows, plan, wall0, gpu_usd_per_hour)
    print(f"3 edits: {n} made")
    fell = {g: {k: i["fallback"] for k, i in v.items() if i.get("fallback")}
            for g, v in meta["garments"].items()}
    fell = {g: v for g, v in fell.items() if v}
    print(f"   references that fell back to full: {len(fell)}" + (f" {fell}" if fell else ""))
    print(f"done in {(time.time() - wall0) / 60:.1f} min")


def _write(rows, plan, wall0, rate):
    with open(d("meta", "timings_v311.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["stage", "arm", "id", "seed", "seconds", "klein_call"])
        w.writeheader()
        for t in _T:
            w.writerow({**{"klein_call": 0}, **t})
    calls = [t for t in _T if t.get("klein_call")]
    wall = time.time() - wall0
    by = {}
    for t in _T:
        by.setdefault((t["stage"], t["arm"]), []).append(t["seconds"])
    json.dump({"cells": len(rows), "plan": [list(p) for p in plan], "klein_calls": len(calls),
               "klein_seconds": round(sum(t["seconds"] for t in calls), 1),
               "wall_minutes": round(wall / 60, 2),
               "cad_gpu": round(wall / 3600 * rate, 3) if rate else None,
               "usd_fal_equivalent": round(len(calls) * FAL_PER_CALL, 2),
               "per_stage_mean_seconds": {f"{s}/{a}": round(sum(v) / len(v), 3)
                                          for (s, a), v in by.items()},
               "prompts": {"call1_A": L.BALD_PROMPT, "call1_B": BALD_NEUTRAL, "edit": V36.ER},
               "arms": {"A": "crop only - call 1 is BALD_PROMPT byte for byte, the band is cut "
                             "on the mask",
                        "B": "call 1 also neutralises the unselected half with a plain white "
                             "garment, then the same band. DEPARTS from the call-1 prompt of "
                             "record, so no v3.8/v3.10 number transfers to it"},
               "input_bound_px": MAXPIX,
               "canvas": "the person's own size under the 1 MP bound, floor 32, never "
                         "upscaled - the shipped rule since v3.10",
               "call1_seed": CALL1_SEED,
               "regions_rule": {"full": "crop_bc unchanged: subject bbox, noface alpha",
                                "upper": "noface kept above the hip line (landmarks 23/24), "
                                         "then the bbox of what remains",
                                "lower": "the same, below it"},
               "fallback": f"no pose, no hip in frame, or a band keeping < {MIN_BAND:.0%} of "
                           f"the subject falls back to full and is recorded per reference",
               "klein": K.info(), "python": platform.python_version()},
              open(d("meta", "cost_v311.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
