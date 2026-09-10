"""v3.6 — call 2's prompt, on the cells `BC_klein` actually failed.

The set is `v3/testsets/v36_bc_failures.csv`: the **29 cells of the 600-cell iron-man-2
sweep the reviewer marked FAIL for `BC`** (`v3/report/bc_count.html` -> `bc_count.csv`,
2026-09-10; 19 pairs, 4.8%). Selected on failure, so nothing measured here is a rate on
the fold — the question is only whether a longer call-2 prompt *reaches* these failures.
What it costs on the 571 cells that already pass is a separate run, and is not in this one.

Only call 2 changes. Every arm takes the same two images the shipped `BC` cell took: the
person as `ironman2/inputs/{p}.jpg` and the reference as `ironman2_bc/refs/{g}__BC.jpg` —
the bald pass plus the V2 head-subtracting crop, unchanged, **not** SR'd (`BC` never was).
Canvas is fal's own rule, which is what the archived cells used (`bc_canvas: fal`), so
leaving `image_size` unset reproduces it.

  E0  the shipped call-2 prompt, re-run on fal            (the control)
  EL  E0 + a limb and extremity count                     (the failure class: extra/merged limbs, shoes)
  EF  E0 + full replacement, and fabrics that do not merge (the failure class: two outfits at once, fabric onto skin)
  ER  E0's verb changed: replace the clothing, not dress the person

`E0` is re-run rather than read off disk on purpose: the archive was made self-hosted on an
A100, and a prompt comparison is only clean if the three arms differ in the prompt and in
nothing else.

  python3 v3/build/run_v36_editprompts.py [--arms E0,EL,EF] [--cells N] [--dry]
"""
import argparse
import csv
import json
import os
import sys
import time

import cv2

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
import v3lib as L                     # noqa: E402  b64, call, EDIT_PROMPT

SRC = os.path.join(REPO, "v3", "runs", "v34", "ironman2")          # inputs
BCR = os.path.join(REPO, "v3", "runs", "v34", "ironman2_bc")       # BC references, BC gens
OUT = os.path.join(REPO, "v3", "runs", "v36", "editprompts")
SET = os.path.join(REPO, "v3", "testsets", "v36_bc_failures.csv")
ENDPOINT = "fal-ai/flux-2/klein/4b/distilled/edit"
USD_PER_CALL = 0.015

# ---- the three call-2 prompts ------------------------------------------------
# E0 is v3lib.EDIT_PROMPT verbatim - unchanged since V2's attention-modulation run.
E0 = L.EDIT_PROMPT
# Both variants are E0 plus one paragraph. Nothing is removed from E0, so any difference
# is attributable to the sentences added and not to a rewrite.
EL = E0 + (" The person has exactly two arms, two hands, two legs and two feet, in the "
           "same positions as in image 1, and wears one pair of shoes. Add no extra arm, "
           "hand, leg, foot or shoe, merge none together, and remove none.")
EF = E0 + (" The clothing in image 2 replaces what the person is wearing completely: none "
           "of their original garment remains, none of it shows through, and nothing is "
           "layered over or under it. Each piece keeps its own edge - no two fabrics blend "
           "into one another, and no fabric spreads onto skin, hair, hands, feet or shoes.")
# ER is not E0 plus a clause - it is E0's first sentence rewritten. "Dress the person in X"
# names an act of putting clothes on; "replace the clothing with X" names the removal as
# well, which is the half E0 leaves implicit and the half these cells fail on.
ER = ("Replace the clothing in image 1 with the clothing in image 2. Keep the person's "
      "face, identity, body and the background exactly as they are.")
PROMPT = {"E0": E0, "EL": EL, "EF": EF, "ER": ER}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="E0,EL,EF,ER")
    ap.add_argument("--cells", type=int, default=None, help="first N cells of the set")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    arms = a.arms.split(",")
    for arm in arms:
        if arm not in PROMPT:
            raise SystemExit(f"unknown arm {arm}; one of {sorted(PROMPT)}")

    rows = list(csv.DictReader(open(SET)))
    if a.cells:
        rows = rows[:a.cells]

    jobs, todo = [], 0
    for r in rows:
        ref = os.path.join(BCR, "refs", f"{r['garment']}__BC.jpg")
        person = os.path.join(SRC, "inputs", f"{r['person']}.jpg")
        for p in (ref, person):
            if not os.path.exists(p):
                raise SystemExit(f"missing input {p}")
        for arm in arms:
            out = os.path.join(OUT, "gen", f"{r['set_id']}__{arm}__s{r['seed']}.jpg")
            jobs.append((r, arm, int(r["seed"]), out))
            todo += not os.path.exists(out)
    print(f"{len(rows)} cells x {len(arms)} arms = {len(jobs)}; {todo} to call "
          f"= ${todo * USD_PER_CALL:.2f} on fal")
    if a.dry:
        for arm in arms:
            print(f"\n{arm}: {PROMPT[arm]}")
        return

    _load_env()
    os.makedirs(os.path.join(OUT, "gen"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "meta"), exist_ok=True)
    t0, n, timings = time.time(), 0, []
    for r, arm, seed, out in jobs:
        if os.path.exists(out):
            continue
        person = cv2.imread(os.path.join(SRC, "inputs", f"{r['person']}.jpg"))
        ref = cv2.imread(os.path.join(BCR, "refs", f"{r['garment']}__BC.jpg"))
        t1 = time.time()
        # no image_size: fal's own canvas rule, which is the one the archived BC cells used
        im = L.call(ENDPOINT, {"image_urls": [L.b64(person), L.b64(ref)],
                               "prompt": PROMPT[arm], "seed": seed})
        secs = round(time.time() - t1, 2)
        cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
        timings.append({"set_id": r["set_id"], "arm": arm, "seed": seed, "seconds": secs,
                        "out": f"{im.shape[1]}x{im.shape[0]}"})
        n += 1
        print(f"  {n}/{todo} {arm} {r['set_id']} s{seed} {secs}s", flush=True)
        _meta(timings, arms, rows, t0)
    _meta(timings, arms, rows, t0)
    print(f"{n} calls, ${n * USD_PER_CALL:.2f}, {(time.time() - t0) / 60:.1f} min")


_BASE = {}   # calls already on disk before this run - read once, so the total is not quadratic


def _meta(timings, arms, rows, t0):
    if timings:
        with open(os.path.join(OUT, "meta", "timings.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["set_id", "arm", "seed", "seconds", "out"])
            w.writeheader(); w.writerows(timings)
    p = os.path.join(OUT, "meta", "run.json")
    old = json.load(open(p)) if os.path.exists(p) else {}
    _BASE.setdefault("calls", old.get("calls", 0))
    json.dump({"endpoint": ENDPOINT, "arms": sorted(set(old.get("arms", []) + arms)),
               "cells": len(rows), "set": os.path.relpath(SET, REPO),
               "set_definition": "the 29 cells of iron man 2 the reviewer marked FAIL for "
                                 "BC_klein in the blind bc_count sweep (v3/testsets/bc_count.csv)",
               "prompts": PROMPT,
               "reference": "ironman2_bc/refs/{g}__BC.jpg as shipped - bald pass + V2 "
                            "head-subtracting crop, no SR",
               "canvas": "fal's own call-2 rule (image_size not passed), as bc_canvas=fal",
               "calls": _BASE["calls"] + len(timings),
               "usd": round((_BASE["calls"] + len(timings)) * USD_PER_CALL, 2),
               "wall_seconds": round(time.time() - t0, 1)}, open(p, "w"), indent=1)


def _load_env():
    for line in open(os.path.join(REPO, ".env"), encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


if __name__ == "__main__":
    main()
