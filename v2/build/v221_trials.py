# v2.2.1 phase 2 — do the crops change what klein produces?
#
# One variable only: the garment reference. Person image, prompt, seed, endpoint
# and arm are all held fixed at the values that produced the existing Testset2
# `base` outputs, so any difference is attributable to the crop.
#
# base is not regenerated — v2/runs/ts2/outputs/klein_4b_edit__{id}.png already
# exists at seed 46 and is reused as the control.
import argparse, io, json, os, sys, threading
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ts2_harness import (REPO, TS2, ARMS, SEED, local, matrix_df, prompt_for)

CROPS = os.path.join(REPO, "v2", "runs", "crop_screen")
OUT = os.path.join(REPO, "v2", "runs", "v221")
ARM = "klein_4b_edit"

# variant -> crop file suffix; None means the untouched reference (the control)
VARIANTS = {
    "base": None,
    "c1_bbox": "c1_bbox",
    "c2_bbox_nobg": "c2_bbox_nobg",
    "c31_no_face": "c3_no_face",
    "c32_keep_hair": "c32_no_face_keep_hair",
    "c4_clothes_only": "c4_clothes_only",
}

_lock = threading.Lock()
_spent = [0.0]


def garment_for(variant, garment_rel):
    """The cropped reference for this variant, or the prepped original."""
    stem = os.path.splitext(os.path.basename(garment_rel))[0]
    if VARIANTS[variant] is None:
        return local(garment_rel)
    p = os.path.join(CROPS, f"{stem}__{VARIANTS[variant]}.jpg")
    return p if os.path.exists(p) else None


def run(variants, workers=6):
    import fal_client, requests
    os.makedirs(OUT, exist_ok=True)
    df = matrix_df()
    cfg = ARMS[ARM]

    jobs = []
    for v in variants:
        if VARIANTS[v] is None:
            continue                      # control already on disk
        for r in df.itertuples():
            dst = os.path.join(OUT, f"{v}__{r.id}.png")
            if os.path.exists(dst):
                continue
            g = garment_for(v, r.garment)
            if g is None:
                print(f"  MISSING crop {v} {r.id}")
                continue
            jobs.append((v, r, g))

    est = len(jobs) * cfg["est_usd"]
    print(f"{len(jobs)} generations ({len(variants)} variants x {len(df)} pairs) — est ${est:.2f}")
    if est > 3.00:
        sys.exit("estimate over $3.00 ceiling")

    cache = {}
    def url(path):
        with _lock:
            if path not in cache:
                cache[path] = fal_client.upload_file(path)
        return cache[path]

    def one(job):
        v, r, gpath = job
        try:
            args = cfg["args"](r, url(local(r.person)), url(gpath), r.duo)
            res = fal_client.subscribe(cfg["endpoint"], arguments=args)
            u = (res.get("images") or [res.get("image", {})])[0]["url"]
            img = Image.open(io.BytesIO(requests.get(u).content)).convert("RGB")
        except Exception as e:
            print(f"  FAIL {v} {r.id}: {str(e)[:120]}")
            return
        img.save(os.path.join(OUT, f"{v}__{r.id}.png"))
        json.dump({"variant": v, "id": r.id, "kind": r.kind, "duo": bool(r.duo),
                   "arm": ARM, "endpoint": cfg["endpoint"], "seed": SEED,
                   "person": r.person, "garment_ref": os.path.relpath(gpath, REPO),
                   "target": r.target, "size": img.size},
                  open(os.path.join(OUT, f"{v}__{r.id}.json"), "w"), indent=2)
        with _lock:
            _spent[0] += cfg["est_usd"]
        print(f"  ok {v:16s} {r.id} ({r.kind}) {img.size}")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, jobs))
    print(f"done — est ${_spent[0]:.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default="c1_bbox,c2_bbox_nobg,c31_no_face,c32_keep_hair,c4_clothes_only")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    run([v for v in a.variants.split(",") if v in VARIANTS], a.workers)


# ----------------------------------------------------------------- scoring ---
def score_all():
    """Deterministic metrics against the ORIGINAL reference, not the cropped one:
    the question is fidelity to the true garment, so the crop must not also be
    the yardstick."""
    import numpy as np, glob
    import metrics_v2 as M
    from ts2_harness import garment_reference
    df = matrix_df().set_index("id")
    rows = []
    # ts2_harness.TS2 is the SOURCE image dir, not the runs dir — the base
    # outputs live under v2/runs/ts2/outputs
    ts2_out = os.path.join(REPO, "v2", "runs", "ts2", "outputs")
    srcs = [(v, f"{OUT}/{v}__{i}.png") for v in VARIANTS if v != "base"
            for i in df.index] + [("base", f"{ts2_out}/klein_4b_edit__{i}.png")
                                  for i in df.index]
    for v, f in srcs:
        pid = os.path.basename(f).split("__")[-1].replace(".png", "")
        if not os.path.exists(f):
            continue
        r = df.loc[pid]
        person = Image.open(local(r.person)).convert("RGB")
        gref = garment_reference(local(r.garment), bool(r.duo))
        res = Image.open(f).convert("RGB")
        rows.append({"variant": v, "id": pid, "kind": r.kind, "duo": bool(r.duo),
                     "garment_sim": float(np.dot(M._embed(gref),
                                                 M._embed(M._torso_crop(res)))),
                     "identity_cos": M.identity_cosine(person, res),
                     "pose_err": M.pose_error(person, res),
                     "bg_psnr": M.background_psnr(person, res)})
    d = pd.DataFrame(rows)
    A, W = M.CV_ANCHORS, {"garment_sim": 2.0, "identity_cos": 1.0,
                          "pose_err": 1.0, "bg_psnr": 1.0}

    def comp(r):
        n = t = 0.0
        for k, w in W.items():
            if pd.isna(r[k]):
                continue
            lo, hi = A[k]
            n += w * min(1.0, max(0.0, (r[k] - lo) / (hi - lo)))
            t += w
        return round(n / t, 3) if t else None
    d["score"] = d.apply(comp, axis=1)
    d.to_csv(os.path.join(OUT, "v221_metrics.csv"), index=False)
    order = ["base", "c2_bbox_nobg", "c31_no_face", "c32_keep_hair", "c4_clothes_only"]
    print(d.groupby("variant")[["garment_sim", "identity_cos", "bg_psnr", "score"]]
          .mean().reindex(order).round(3).to_string())
    print()
    print(d[d.duo].groupby("variant")[["garment_sim", "score"]].mean()
          .reindex(order).round(3).to_string(), "  <- duo pairs only")
    return d
