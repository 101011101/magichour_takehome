"""v3.5 link A — the call-1 reference sweep, on fal.

Four ways to build the garment reference from the same A4 crop, one klein call each:

  M0  SWAP + KEEP + PERSON_CLAUSE + HOLD        the v3.4 lock's Q3, verbatim — the control
  M1  TURN + KEEP + FRAME + HOLD                turn to front, no mannequin sentence
  M2  SWAP + TURN + KEEP + FRAME + HOLD         the same turn, with the mannequin sentence
  G1  GARMENT                                   the clothing alone, person removed

M1/M2 differ by exactly one sentence, so the mannequin's cost and benefit is readable off
the pair; M0 is the incumbent on the same backend, because a fal draw and an A100 draw are
not comparable (v3.4 SOLUTION §5 rule 4).

Everything is reused, nothing recomputed: the A4 crops and the per-garment framing come
from the iron-man 2 run on disk. No BiRefNet, no MediaPipe, no GPU.

The canvas is pinned to the v3.3/v3.4 call-1 rule (the crop's own size, capped 1 MP, floor
16) via fal's image_size, which the v3.4 probe measured as honoured exactly (call c20) —
left unset, fal would render call 1 at ~1 MP, which is arm VE, not VEi.

  python v3/build/run_v35_refs.py [--arms M0,M1,M2,G1] [--limit N] [--seed 46] [--dry]
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
import v3lib as L                     # noqa: E402  b64 + the retrying fal caller
import run_ironman as R               # noqa: E402  the locked prompts, imported not copied

SRC = os.path.join(REPO, "v3", "runs", "v34", "ironman2")     # crops + framing of record
OUT = os.path.join(REPO, "v3", "runs", "v35", "linkA")
ENDPOINT = "fal-ai/flux-2/klein/4b/distilled/edit"
USD_PER_CALL = 0.015

# The framing half of PERSON_CLAUSE, with the repose half removed — M1/M2 carry their own
# turn sentence, so the clause must not also say "change the pose" a second time.
FRAME = {
    "full_body": " The photograph shows them from head to feet; keep that framing.",
    "knee_up": (" The photograph shows them from the head to the knee only; keep exactly "
                "that framing, cut off below the knee."),
    "waist_up": (" The photograph shows them from the head to the hip only; keep exactly "
                 "that framing, cut off below the hip."),
    "chest_up": (" The photograph shows them from the head to the chest only; keep exactly "
                 "that framing, cut off below the chest."),
    "unknown": " Keep exactly the framing the photograph has.",
}
TURN = ("Turn this person to face the camera directly, front-on: standing upright in a "
        "neutral pose, shoulders level and square to the camera, arms relaxed at the sides.")
GARMENT = ("Return only the clothing from this photograph, worn as if by an invisible "
           "body, seen front-on, isolated on a plain white background. Remove the person "
           "entirely - no face, no skin, no hair, no hands, no background. The garment "
           "keeps its exact colour, pattern, shape and length - the same pieces, nothing "
           "added, nothing removed.")


def prompt_for(arm, framing):
    if arm == "M0":
        return R.SWAP + R.KEEP + R.PERSON_CLAUSE[framing] + R.HOLD
    if arm == "M1":
        return TURN + R.KEEP + FRAME[framing] + R.HOLD
    if arm == "M2":
        return R.SWAP + " " + TURN + R.KEEP + FRAME[framing] + R.HOLD
    if arm == "G1":
        return GARMENT
    raise SystemExit(f"unknown arm {arm}")


def canvas(bgr, maxpix=1_048_576):
    """The v3.3/v3.4 call-1 rule, from klein_local._size — never upscale, floor 16."""
    h, w = bgr.shape[:2]
    k = min(1.0, (maxpix / (h * w)) ** 0.5)
    return max(16, int(h * k) // 16 * 16), max(16, int(w * k) // 16 * 16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="M0,M1,M2,G1")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--garments", default=None, help="comma-separated stems, overrides --limit")
    ap.add_argument("--seed", type=int, default=46)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    arms = a.arms.split(",")

    meta_src = json.load(open(os.path.join(SRC, "meta", "prompts.json")))
    framings = {k.split("|")[0]: v["framing"] for k, v in meta_src.items() if k.endswith("|VEi")}
    garments = sorted(framings)
    if a.garments:
        garments = a.garments.split(",")
    elif a.limit:
        garments = garments[:a.limit]

    for x in ("refs", "meta"):
        os.makedirs(os.path.join(OUT, x), exist_ok=True)
    rows, todo = [], 0
    for g in garments:
        crop_p = os.path.join(SRC, "inputs", f"{g}__A4.jpg")
        if not os.path.exists(crop_p):
            raise SystemExit(f"missing crop {crop_p}")
        crop = cv2.imread(crop_p)
        h, w = canvas(crop)
        for arm in arms:
            out = os.path.join(OUT, "refs", f"{g}__{arm}.jpg")
            rows.append({"garment": g, "arm": arm, "framing": framings[g],
                         "crop": f"{crop.shape[1]}x{crop.shape[0]}", "canvas": f"{w}x{h}",
                         "prompt": prompt_for(arm, framings[g]),
                         "done": os.path.exists(out)})
            todo += not os.path.exists(out)

    print(f"{len(garments)} garments x {len(arms)} arms = {len(rows)} refs; "
          f"{todo} to call = ${todo * USD_PER_CALL:.2f} on fal")
    if a.dry:
        for r in rows[:len(arms)]:
            print(f"\n[{r['arm']}] {r['garment']} {r['crop']} -> {r['canvas']}\n  {r['prompt']}")
        return

    L._load_env() if hasattr(L, "_load_env") else _load_env()
    t0, n, timings = time.time(), 0, []
    for r in rows:
        if r["done"]:
            continue
        g, arm = r["garment"], r["arm"]
        crop = cv2.imread(os.path.join(SRC, "inputs", f"{g}__A4.jpg"))
        h, w = canvas(crop)
        t1 = time.time()
        im = L.call(ENDPOINT, {"image_urls": [L.b64(crop)], "prompt": r["prompt"],
                               "seed": a.seed, "image_size": {"width": w, "height": h}})
        secs = round(time.time() - t1, 2)
        im = R.recrop(im)          # the lock's white-margin trim, same for every arm
        cv2.imwrite(os.path.join(OUT, "refs", f"{g}__{arm}.jpg"), im,
                    [cv2.IMWRITE_JPEG_QUALITY, 95])
        timings.append({"arm": arm, "garment": g, "seed": a.seed, "seconds": secs,
                        "out": f"{im.shape[1]}x{im.shape[0]}"})
        n += 1
        print(f"  {n}/{todo} {arm} {g} {secs}s", flush=True)
        _write_meta(rows, timings, arms, garments, a.seed, t0)
    _write_meta(rows, timings, arms, garments, a.seed, t0)
    print(f"{n} calls, ${n * USD_PER_CALL:.2f}, {(time.time() - t0) / 60:.1f} min")


def _write_meta(rows, timings, arms, garments, seed, t0):
    with open(os.path.join(OUT, "meta", "prompts.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["garment", "arm", "framing", "crop", "canvas", "prompt", "done"])
        w.writeheader(); w.writerows(rows)
    if timings:
        with open(os.path.join(OUT, "meta", "timings.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["arm", "garment", "seed", "seconds", "out"])
            w.writeheader(); w.writerows(timings)
    json.dump({"endpoint": ENDPOINT, "arms": arms, "garments": len(garments), "seed": seed,
               "canvas_rule": "call-1 v3.3/v3.4: crop size capped 1MP, floor 16, via fal image_size",
               "source_run": os.path.relpath(SRC, REPO), "calls": len(timings),
               "usd": round(len(timings) * USD_PER_CALL, 2),
               "wall_seconds": round(time.time() - t0, 1),
               "prompts": {"SWAP": R.SWAP, "KEEP": R.KEEP, "HOLD": R.HOLD, "TURN": TURN,
                           "GARMENT": GARMENT, "FRAME": FRAME,
                           "PERSON_CLAUSE": R.PERSON_CLAUSE}},
              open(os.path.join(OUT, "meta", "run.json"), "w"), indent=1)


def _load_env():
    p = os.path.join(REPO, ".env")
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


if __name__ == "__main__":
    main()
