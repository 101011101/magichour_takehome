"""v3.5 link B — call 2, on the pairs v3.4 actually failed.

The set is `v3/testsets/v35_failures.csv`: the **31 pairs of the 200-pair iron-man 2 matrix
on which the locked v3.4 arm `VEi` has a real failure**, by the reviewer's own per-cell
verdict (`v34_im2_truth.json`, 600 cells, 100% human-judged — v3.4 RESULTS §11). Eight fail
at every seed. Selected on failure, so a rate measured here does not transfer to the fold;
its job is to show whether the head-crop reference *reaches* the failures.

One klein call per (pair, arm, seed). Call 2 is the lock's: prompt `E3`, both images in,
**fal's own canvas** (area 1024², floor 32 — the rule the v3.4 probe measured, so it is
reproduced by simply not passing `image_size`). Every arm's reference is SR'd to ~1 MP
first, exactly as `VEi` does it: the upscale only ever touches a finished reference.

  python3 v3/build/run_v35_edits.py [--arms M0,M1c,BC] [--seeds 46] [--pairs N] [--dry]

Arms name the reference on disk: `M0`/`M1c`/`M0c`/`M1`/`M2`/`G1` from v3.5 link A,
`BC`/`VEi` from the iron-man 2 run (the incumbent and the lock, as shipped).
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
import v3lib as L                     # noqa: E402
import run_ironman as R               # noqa: E402  E3, to_1mp_sr — the lock's own code

SRC = os.path.join(REPO, "v3", "runs", "v34", "ironman2")
LINKA = os.path.join(REPO, "v3", "runs", "v35", "linkA")
OUT = os.path.join(REPO, "v3", "runs", "v35", "linkB")
SET = os.path.join(REPO, "v3", "testsets", "v35_failures.csv")
ENDPOINT = "fal-ai/flux-2/klein/4b/distilled/edit"
USD_PER_CALL = 0.015
FROM_IRONMAN = ("BC", "VEi")          # arms whose references already exist, as shipped


def ref_path(arm, g):
    if arm in FROM_IRONMAN:
        return os.path.join(SRC, "refs", f"{g}__{arm}.jpg")
    return os.path.join(LINKA, "refs", f"{g}__{arm}.jpg")


def sr_ref(arm, g):
    """The reference as call 2 sees it: SR'd to ~1 MP, cached on disk."""
    p = os.path.join(OUT, "refs_sr", f"{g}__{arm}.jpg")
    if os.path.exists(p):
        return cv2.imread(p)
    im = R.to_1mp_sr(cv2.imread(ref_path(arm, g)))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    cv2.imwrite(p, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="M0,M1c,BC")
    ap.add_argument("--seeds", default="46")
    ap.add_argument("--pairs", type=int, default=None, help="first N pairs of the set")
    ap.add_argument("--only", default=None, help="comma-separated set_ids")
    ap.add_argument("--ready", action="store_true", help="skip pairs whose references are not made yet")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    arms, seeds = a.arms.split(","), [int(s) for s in a.seeds.split(",")]

    rows = list(csv.DictReader(open(SET)))
    if a.only:
        keep = set(a.only.split(","))
        rows = [r for r in rows if r["set_id"] in keep]
    elif a.pairs:
        rows = rows[:a.pairs]
    if a.ready:
        rows = [r for r in rows if all(os.path.exists(ref_path(x, r["garment"])) for x in arms)]

    jobs, todo = [], 0
    for r in rows:
        for arm in arms:
            if not os.path.exists(ref_path(arm, r["garment"])):
                raise SystemExit(f"missing reference {ref_path(arm, r['garment'])} "
                                 "(--ready to skip pairs that are not made yet)")
            for s in seeds:
                out = os.path.join(OUT, "gen", f"{r['set_id']}__{arm}__s{s}.jpg")
                jobs.append((r, arm, s, out))
                todo += not os.path.exists(out)
    print(f"{len(rows)} pairs x {len(arms)} arms x {len(seeds)} seeds = {len(jobs)} cells; "
          f"{todo} to call = ${todo * USD_PER_CALL:.2f} on fal")
    if a.dry:
        for r in rows:
            print(f"  {r['set_id']}  seed_stable={r['seed_stable']}  "
                  f"{r['v46']}/{r['v47']}/{r['v48']}")
        return

    _load_env()
    os.makedirs(os.path.join(OUT, "gen"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "meta"), exist_ok=True)
    t0, n, timings = time.time(), 0, []
    for r, arm, s, out in jobs:
        if os.path.exists(out):
            continue
        person = cv2.imread(os.path.join(SRC, "inputs", f"{r['person']}.jpg"))
        ref = sr_ref(arm, r["garment"])
        t1 = time.time()
        # no image_size: fal's own canvas rule is the lock's call-2 rule
        im = L.call(ENDPOINT, {"image_urls": [L.b64(person), L.b64(ref)],
                               "prompt": R.E3, "seed": s})
        secs = round(time.time() - t1, 2)
        cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
        timings.append({"set_id": r["set_id"], "arm": arm, "seed": s, "seconds": secs,
                        "out": f"{im.shape[1]}x{im.shape[0]}"})
        n += 1
        print(f"  {n}/{todo} {arm} {r['set_id']} s{s} {secs}s", flush=True)
        _meta(timings, arms, seeds, rows, t0)
    _meta(timings, arms, seeds, rows, t0)
    print(f"{n} calls, ${n * USD_PER_CALL:.2f}, {(time.time() - t0) / 60:.1f} min")


def _meta(timings, arms, seeds, rows, t0):
    if timings:
        with open(os.path.join(OUT, "meta", "timings.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["set_id", "arm", "seed", "seconds", "out"])
            w.writeheader(); w.writerows(timings)
    p = os.path.join(OUT, "meta", "run.json")
    old = json.load(open(p)) if os.path.exists(p) else {}
    json.dump({"endpoint": ENDPOINT, "arms": sorted(set(old.get("arms", []) + arms)),
               "seeds": sorted(set(old.get("seeds", []) + seeds)),
               "pairs": len(rows), "set": os.path.relpath(SET, REPO),
               "set_definition": "the 31 pairs of iron man 2 with a real VEi failure "
                                 "in v34_im2_truth.json (the reviewer's per-cell verdict)",
               "prompt": R.E3, "canvas": "fal's own call-2 rule (image_size not passed)",
               "reference": "SR'd to ~1 MP before call 2, as VEi does it",
               "calls": old.get("calls", 0) + len(timings),
               "usd": round((old.get("calls", 0) + len(timings)) * USD_PER_CALL, 2),
               "wall_seconds": round(time.time() - t0, 1)}, open(p, "w"), indent=1)


def _load_env():
    for line in open(os.path.join(REPO, ".env"), encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


if __name__ == "__main__":
    main()
