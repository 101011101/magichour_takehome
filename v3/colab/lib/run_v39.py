"""v3.9 - is the upscale half of call 2's canvas rule necessary, and does cropping twice help.

Ray's spec: "just have it so that it is hard limit of <=1mp instead of 1.15 for this test and
no upscaling vs upscaling ... also I want to see the double crop vs single crop".

  SCALE    the rule of record: call 2's canvas is area 2^20, aspect kept, scaled UP or down,
           floor 32 (klein_local._size_fal). One crop. The baseline both questions face.
  NOSCALE  the same cell with the upscale removed: the canvas is the person photo's own size,
           floor 32, never upscaled. Under this run's 1 MP input bound it is never downscaled
           either, so the arm is exactly "<= 1 MP and otherwise untouched".
  CROP2    two crops: A4 crop (BiRefNet bbox, head kept) -> bald pass on the crop -> the same
           head-subtracting crop. Call 2 on SCALE's canvas, so the crop is the only variable.

THE 1 MP BOUND. Every photo is re-normalised here to <= 2^20 px, not v3lib's 1,150,000 - so
no image anywhere in this run exceeds 1 MP, and the A4 crops are recomputed from the bounded
photos rather than taken from the archive. That re-bounds the bald pass's input as well, which
is why SCALE is REBUILT here rather than read from the v3.8 archive: an arm and its baseline
must differ in one thing only.

THE CANVAS INJECTION. klein_local.edit picks between its two rules by name. NOSCALE's rule is
neither, and klein_local is shared with the runs of record, so the function is injected around
the call (_canvas) instead of adding a third name to it. Both arms floor to 32: the variable
is the up/down scaling, not the rounding.

All three arms run on whatever pipeline klein_local.load was given - the notebook gives it
Photoroom's transformer_bf16 - so SCALE is a fresh baseline, not the BFL archive. The runner
refuses to start without the swap.

Inputs (cell 4 unpacks them off Drive): inputs/{stem}.jpg.
Resumable: every stage skips what is on disk. Output: run/{in1mp,refs,gen,meta}.
"""
import csv
import json
import os
import platform
import sys
import time

import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v3lib as L                      # noqa: E402  BALD_PROMPT, crop_a4
import klein_local as K                # noqa: E402  the call, and the fal canvas rule
import run_v36 as V36                  # noqa: E402  ER's prompt, byte for byte as v3.8 sent it
from ironman_bc_crop import crop_bc    # noqa: E402  the V2 cropper's head subtraction

OUT = "run"
MAXPIX = 2 ** 20                       # the hard bound for this test, in place of v3lib's 1.15 MP
ARMS = ("SCALE", "NOSCALE", "CROP2")
REF = {"SCALE": "1crop", "NOSCALE": "1crop", "CROP2": "2crop"}
BALD_SRC = {"1crop": "{g}.jpg", "2crop": "{g}__A4.jpg"}    # what each reference's bald pass sees
CALL1_SEED = 46
JPG = [cv2.IMWRITE_JPEG_QUALITY, 95]
FAL_PER_CALL = 0.015
_T = []


def d(*p):
    q = os.path.join(OUT, *p)
    os.makedirs(os.path.dirname(q), exist_ok=True)
    return q


def normalise(bgr, maxpix=MAXPIX):
    """v3lib.normalise with this test's bound: nothing over 1 MP, INTER_AREA down."""
    h, w = bgr.shape[:2]
    if h * w <= maxpix:
        return bgr
    k = (maxpix / (h * w)) ** 0.5
    return cv2.resize(bgr, (int(w * k), int(h * k)), interpolation=cv2.INTER_AREA)


def size_noscale(bgr, maxpix=MAXPIX):
    """The person's own size, floor 32, never upscaled (and, past the bound, never reduced)."""
    h, w = bgr.shape[:2]
    k = min(1.0, (maxpix / (h * w)) ** 0.5)
    return max(32, int(h * k) // 32 * 32), max(32, int(w * k) // 32 * 32)


CANVAS = {"SCALE": K._size_fal, "NOSCALE": size_noscale, "CROP2": K._size_fal}


def _canvas(images, prompt, seed, size_fn):
    """klein_local.edit with the canvas function injected, so every arm goes through the one
    call path. K.edit resolves _size from the module at call time."""
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


def _crop_job(job):
    """One head-subtracting crop. CPU ONNX on threads, as run_v35_linkC._headcut_job: ORT and
    MediaPipe release the GIL, and the first job runs alone to build the shared sessions."""
    g, kind, src, out = job
    t0 = time.time()
    im, cranium = crop_bc(cv2.imread(src), f"v39_{kind}_{g}")
    cv2.imwrite(out, im, JPG)
    return g, kind, bool(cranium), round(time.time() - t0, 1), [im.shape[1], im.shape[0]]


def main(matrix="v39_set.csv", arms=ARMS, gpu_usd_per_hour=None, limit=None, crop_workers=4):
    wall0 = time.time()
    for a in arms:
        if a not in ARMS:
            raise SystemExit(f"unknown arm {a}; one of {ARMS}")
    if not K.info().get("transformer"):
        raise SystemExit("load the production transformer first: K.load(repo=..., "
                         "transformer=(...)) - this runner never falls back to BFL's")
    rows = list(csv.DictReader(open(matrix)))
    if limit:
        rows = rows[:int(limit)]
    garments = sorted({r["garment"] for r in rows})
    kinds = sorted({REF[a] for a in arms})
    stems = sorted({r["person"] for r in rows} | set(garments))

    # 0 the 1 MP bound - every photo re-normalised here, and the A4 crops recomputed from the
    #   bounded photo so no stage in this run ever sees more than 2^20 px
    paths = None
    n = 0
    for s in stems:
        src, out = d("inputs", f"{s}.jpg"), d("in1mp", f"{s}.jpg")
        if not os.path.exists(src):
            raise SystemExit(f"missing {src} - cell 4 unpacks the inputs off Drive")
        if os.path.exists(out):
            continue
        cv2.imwrite(out, normalise(cv2.imread(src)), JPG)
        n += 1
    print(f"0 inputs bounded to {MAXPIX} px: {n} written, {len(stems)} total")
    if "2crop" in kinds:
        n = 0
        for g in garments:
            p = d("in1mp", f"{g}__A4.jpg")
            if os.path.exists(p):
                continue
            paths = paths or L.fetch_models(persist=os.environ.get("V3_MODEL_DIR"))
            t0 = time.time()
            cv2.imwrite(p, L.crop_a4(cv2.imread(d("in1mp", f"{g}.jpg")), paths), JPG)
            _T.append({"stage": "a4_crop", "arm": "CROP2", "id": g, "seed": 0,
                       "seconds": round(time.time() - t0, 3)})
            n += 1
        print(f"  A4 crops recomputed from the bounded photos: {n} made")

    mp = d("meta", "v39_meta.json")
    meta = json.load(open(mp)) if os.path.exists(mp) else {"garments": {}, "cells": {}}
    print(f"{len(rows)} cells · {len(garments)} garments · arms {arms} · references {kinds}")

    # 1 bald passes - call 1, on the GPU, one per garment per reference kind
    n = 0
    for g in garments:
        for kind in kinds:
            out = d("refs", f"{g}__bald_{kind}.jpg")
            if os.path.exists(out):
                continue
            src = cv2.imread(d("in1mp", BALD_SRC[kind].format(g=g)))
            b = klein("bald", kind, g, CALL1_SEED, [src], L.BALD_PROMPT, K._size)
            b = cv2.resize(b, (src.shape[1], src.shape[0]), interpolation=cv2.INTER_AREA)
            cv2.imwrite(out, b, JPG)
            n += 1
    print(f"1 bald passes: {n} made")

    # 2 head-subtracting crops - the one stage off the GPU
    jobs = [(g, k, d("refs", f"{g}__bald_{k}.jpg"), d("refs", f"{g}__{k}.jpg"))
            for g in garments for k in kinds if not os.path.exists(d("refs", f"{g}__{k}.jpg"))]
    if jobs:
        import garment_crop as GC
        n_w = max(1, int(crop_workers))
        if "cuda" in str(GC.ort_providers()[0]).lower():
            n_w = 1                        # on the GPU threads only multiply peak memory
        print(f"2 {len(jobs)} head crops on {n_w} thread{'s' if n_w > 1 else ''}", flush=True)
        t0 = time.time()
        done = [_crop_job(jobs[0])]
        if n_w == 1:
            done += [_crop_job(j) for j in jobs[1:]]
        else:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=n_w) as ex:
                for r in ex.map(_crop_job, jobs[1:]):
                    done.append(r)
                    print(f"    {len(done)}/{len(jobs)} {r[1]} {r[0]} cranium={r[2]} {r[3]}s",
                          flush=True)
        for g, k, cranium, secs, wh in done:
            meta["garments"].setdefault(g, {})[k] = {
                "cranium_used": cranium, "size": wh, "mp": round(wh[0] * wh[1] / 2 ** 20, 3)}
            _T.append({"stage": "headcrop", "arm": k, "id": g, "seed": 0, "seconds": secs})
        print(f"   {len(jobs)} crops in {(time.time() - t0) / 60:.1f} min")
        json.dump(meta, open(mp, "w"), indent=1)

    # 3 call 2 - per cell, per arm
    n = noop = 0
    for r in rows:
        sid, seed = r["set_id"], int(r["seed"])
        person = cv2.imread(d("in1mp", f"{r['person']}.jpg"))
        cell = meta["cells"].setdefault(f"{sid}|{seed}", {})
        base = CANVAS["SCALE"](person)
        for arm in arms:
            h, w = CANVAS[arm](person)
            cell[arm] = [w, h]
            if arm == "NOSCALE" and (h, w) == base:
                cell["NOSCALE_noop"] = True
                noop += 1
                continue
            out = d("gen", f"{sid}__{arm}__s{seed}.jpg")
            if os.path.exists(out):
                continue
            ref = cv2.imread(d("refs", f"{r['garment']}__{REF[arm]}.jpg"))
            assert ref is not None, f"missing refs/{r['garment']}__{REF[arm]}.jpg"
            im = klein("edit", arm, sid, seed, [person, ref], V36.ER, CANVAS[arm])
            cv2.imwrite(out, im, JPG)
            n += 1
            if n % 25 == 0:
                print(f"    {n} edits", flush=True)
                json.dump(meta, open(mp, "w"), indent=1)
                _write(rows, arms, wall0, gpu_usd_per_hour)
    json.dump(meta, open(mp, "w"), indent=1)
    _write(rows, arms, wall0, gpu_usd_per_hour)
    print(f"3 edits: {n} made · NOSCALE no-ops {noop} (canvas identical to SCALE's, not generated)")
    print(f"done in {(time.time() - wall0) / 60:.1f} min")


def _write(rows, arms, wall0, rate):
    with open(d("meta", "timings_v39.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["stage", "arm", "id", "seed", "seconds", "klein_call"])
        w.writeheader()
        for t in _T:
            w.writerow({**{"klein_call": 0}, **t})
    calls = [t for t in _T if t.get("klein_call")]
    wall = time.time() - wall0
    by = {}
    for t in _T:
        by.setdefault((t["stage"], t["arm"]), []).append(t["seconds"])
    json.dump({"cells": len(rows), "arms": list(arms), "klein_calls": len(calls),
               "klein_seconds": round(sum(t["seconds"] for t in calls), 1),
               "wall_minutes": round(wall / 60, 2),
               "cad_gpu": round(wall / 3600 * rate, 3) if rate else None,
               "usd_fal_equivalent": round(len(calls) * FAL_PER_CALL, 2),
               "per_stage_mean_seconds": {f"{s}/{a}": round(sum(v) / len(v), 3)
                                          for (s, a), v in by.items()},
               "prompts": {"bald": L.BALD_PROMPT, "edit": V36.ER},
               "input_bound_px": MAXPIX,
               "canvas": {"SCALE": "area 2^20, up or down, floor 32 (klein_local._size_fal)",
                          "NOSCALE": "own size under the 1 MP bound, floor 32, never upscaled",
                          "CROP2": "area 2^20, up or down, floor 32 (klein_local._size_fal)"},
               "call1_seed": CALL1_SEED, "call1_canvas": "klein_local._size (floor 16, never up)",
               "references": {"1crop": "bald(in1mp/{g}.jpg) -> crop_bc",
                              "2crop": "bald(in1mp/{g}__A4.jpg) -> crop_bc"},
               "klein": K.info(), "python": platform.python_version()},
              open(d("meta", "cost_v39.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
