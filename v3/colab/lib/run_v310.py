"""v3.10 - is the upscale half of call 2's canvas rule right, on the whole fold.

v3.9 asked this on 93 cells chosen for being interesting and got NOSCALE 22 : SCALE 8
(p=0.016) - but the win was almost entirely on cells that were already failing (20:3), it
REVERSED on the 31 cells that already passed (2:5), and it was weakest where the upscale was
largest, which is backwards for the mechanism it would need. v3.8's own adoption rule is that
an arm tested on failures cannot be adopted on failures: what decides it is the cost on
passing cells. This run measures that, on all 547 of them.

  SCALE    the rule of record: call 2's canvas is area 2^20, aspect kept, scaled UP or down,
           floor 32 (klein_local._size_fal).
  NOSCALE  the candidate: the person photo's own size, floor 32, never upscaled. Under this
           run's 1 MP input bound it is never downscaled either, so the arm is exactly
           "<= 1 MP and otherwise untouched".

ONE VARIABLE. The reference is a constant: every cell of both arms is handed the ARCHIVED
`refs/{g}__BC.jpg` of iron man 2, unchanged and unrebuilt. No bald pass and no crop runs here
- this is a call-2-only run, which is also what makes 1,056 generations affordable. Person
photos are re-bounded to 2^20 for BOTH arms, so the only thing that differs between them is
whether a photo under 1 MP is scaled up to it.

NOT POOLABLE WITH v3.9. v3.9 rebuilt its references under the 1 MP bound; this run uses the
archive's, built at 1.15 MP. Both are internally consistent - an arm and its baseline always
share a reference - but a cell here is not the same cell there, and the marks must not be
merged.

THE CANVAS INJECTION. klein_local.edit picks between its two rules by name. NOSCALE's rule is
neither, and klein_local is shared with the runs of record, so the function is injected around
the call (_canvas) instead of adding a third name to it. Both arms floor to 32: the variable
is the up/down scaling, not the rounding.

Both arms run on whatever pipeline klein_local.load was given - the notebook gives it
Photoroom's transformer_bf16 - so SCALE is a fresh baseline, not the v3.8 archive. The runner
refuses to start without the swap.

Inputs (cell 4 unpacks them off Drive): inputs/{stem}.jpg, refs/{garment}__BC.jpg.
Resumable: every stage skips what is on disk. Output: run/{in1mp,gen,meta}.
"""
import csv
import json
import os
import platform
import sys
import time

import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import klein_local as K                # noqa: E402  the call, and the fal canvas rule
import run_v36 as V36                  # noqa: E402  ER's prompt, byte for byte as v3.8 sent it

OUT = "run"
MAXPIX = 2 ** 20                       # the hard bound the candidate rule implies
ARMS = ("SCALE", "NOSCALE")
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


CANVAS = {"SCALE": K._size_fal, "NOSCALE": size_noscale}


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


def main(matrix="v310_set.csv", arms=ARMS, gpu_usd_per_hour=None, limit=None):
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
    persons = sorted({r["person"] for r in rows})
    garments = sorted({r["garment"] for r in rows})

    # 0 the 1 MP bound - person photos only; the references are the archive's, untouched
    n = 0
    for s in persons:
        src, out = d("inputs", f"{s}.jpg"), d("in1mp", f"{s}.jpg")
        if not os.path.exists(src):
            raise SystemExit(f"missing {src} - cell 4 unpacks the inputs off Drive")
        if os.path.exists(out):
            continue
        cv2.imwrite(out, normalise(cv2.imread(src)), JPG)
        n += 1
    print(f"0 person photos bounded to {MAXPIX} px: {n} written, {len(persons)} total")
    for g in garments:
        if not os.path.exists(d("refs", f"{g}__BC.jpg")):
            raise SystemExit(f"missing refs/{g}__BC.jpg - the archived reference, cell 4 "
                             f"unpacks it; this run never rebuilds a reference")
    print(f"  {len(garments)} archived references, used unchanged")

    mp = d("meta", "v310_meta.json")
    meta = json.load(open(mp)) if os.path.exists(mp) else {"cells": {}}
    print(f"{len(rows)} cells · arms {arms}")

    # 1 call 2 - per cell, per arm. The only generative stage in this run.
    n = noop = 0
    for r in rows:
        sid, seed = r["set_id"], int(r["seed"])
        person = cv2.imread(d("in1mp", f"{r['person']}.jpg"))
        ref = cv2.imread(d("refs", f"{r['garment']}__BC.jpg"))
        assert ref is not None, f"missing refs/{r['garment']}__BC.jpg"
        cell = meta["cells"].setdefault(f"{sid}|{seed}", {"prior": r.get("prior", "")})
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
            im = klein("edit", arm, sid, seed, [person, ref], V36.ER, CANVAS[arm])
            cv2.imwrite(out, im, JPG)
            n += 1
            if n % 50 == 0:
                print(f"    {n} edits", flush=True)
                json.dump(meta, open(mp, "w"), indent=1)
                _write(rows, arms, wall0, gpu_usd_per_hour)
    json.dump(meta, open(mp, "w"), indent=1)
    _write(rows, arms, wall0, gpu_usd_per_hour)
    print(f"1 edits: {n} made · NOSCALE no-ops {noop} (canvas identical to SCALE's, not generated)")
    print(f"done in {(time.time() - wall0) / 60:.1f} min")


def _write(rows, arms, wall0, rate):
    with open(d("meta", "timings_v310.csv"), "w", newline="") as f:
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
               "prompts": {"edit": V36.ER},
               "input_bound_px": MAXPIX,
               "canvas": {"SCALE": "area 2^20, up or down, floor 32 (klein_local._size_fal)",
                          "NOSCALE": "own size under the 1 MP bound, floor 32, never upscaled"},
               "references": "iron man 2's archived refs/{g}__BC.jpg, unchanged - no bald "
                             "pass and no crop runs in this experiment",
               "klein": K.info(), "python": platform.python_version()},
              open(d("meta", "cost_v310.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
