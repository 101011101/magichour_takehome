"""VS on the marked failures, via fal: every link-D cell the reviewer marked non-pass
(v34_linkD_marks.csv), re-run with SR-scaled inputs (realesr-general-x4v3, x4 then area-
down to 1 MP; pure downscale when the input is already >= 1 MP) at the exact failing seed.
Outputs v3/runs/v34/vs_fal/{inputs_sr,refs,gen,meta}. fal draws - orientation, not record.
  .venv/bin/python v3/build/run_v34_vs_fal.py
"""
import csv, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2, numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib")); sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import v3lib as L                                                     # noqa: E402
from run_ironman import SWAP, KEEP, HOLD, PERSON_CLAUSE, E3, recrop   # noqa: E402
from run_v33_phase2 import load_env                                   # noqa: E402

IM = os.path.join(REPO, "v3", "runs", "ironman", "20260830_0548")
OUT = os.path.join(REPO, "v3", "runs", "v34", "vs_fal")
SR_W = "/private/tmp/claude-501/-Users-arviny-Downloads-Code-magichour-takehome/1372fc44-70e4-41af-a657-2b49a049a805/scratchpad/realesr-general-x4v3.pth"
AREA = 1_048_576

_NET = {}


def _net():
    if "n" in _NET:
        return _NET["n"]
    import torch, torch.nn as nn, torch.nn.functional as F

    class Compact(nn.Module):
        def __init__(s, nf=64, nc=32, up=4):
            super().__init__(); s.up = up; s.body = nn.ModuleList([nn.Conv2d(3, nf, 3, 1, 1), nn.PReLU(nf)])
            for _ in range(nc): s.body += [nn.Conv2d(nf, nf, 3, 1, 1), nn.PReLU(nf)]
            s.body.append(nn.Conv2d(nf, 3 * up * up, 3, 1, 1)); s.shuf = nn.PixelShuffle(up)

        def forward(s, x):
            o = x
            for m in s.body: o = m(o)
            return s.shuf(o) + F.interpolate(x, scale_factor=s.up, mode='nearest')

    net = Compact(); net.load_state_dict(torch.load(SR_W, map_location='cpu')['params']); net.eval()
    torch.set_num_threads(os.cpu_count()); _NET["n"] = net
    return net


def sr_to_1mp(bgr):
    """SR x4 then area-down to ~1 MP when upscaling; plain area resize when already >= 1 MP."""
    import torch
    h, w = bgr.shape[:2]; k = (AREA / (h * w)) ** 0.5
    if k <= 1.0:
        return cv2.resize(bgr, (int(w * k), int(h * k)), interpolation=cv2.INTER_AREA)
    x = torch.from_numpy(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255).permute(2, 0, 1)[None]
    with torch.no_grad(): y = _net()(x)
    y = cv2.cvtColor((y.clamp(0, 1)[0].permute(1, 2, 0).numpy() * 255).round().astype(np.uint8), cv2.COLOR_RGB2BGR)
    h, w = y.shape[:2]; k = (AREA / (h * w)) ** 0.5
    return cv2.resize(y, (int(w * k), int(h * k)), interpolation=cv2.INTER_AREA)


def main():
    load_env(); L.MODEL_DIR = os.path.join(REPO, "v2", "runs", ".models"); paths = L.fetch_models(verbose=False)
    for x in ("inputs_sr", "refs", "gen", "meta"): os.makedirs(os.path.join(OUT, x), exist_ok=True)
    marks = [r for r in csv.DictReader(open(os.path.join(REPO, "v34_linkD_marks.csv"))) if r["verdict"] != "pass"]
    rows = {r["set_id"]: r for r in csv.DictReader(open(os.path.join(REPO, "v3", "testsets", "v34_failures.csv")))}
    cells = [(m["set_id"], int(m["seed"]), m["verdict"]) for m in marks]
    persons = sorted({rows[s]["person"] for s, _, _ in cells}); garments = sorted({rows[s]["garment"] for s, _, _ in cells})
    print(f"{len(cells)} marked cells · {len(persons)} persons · {len(garments)} garments")

    def sr_cache(stem, kind):
        p = os.path.join(OUT, "inputs_sr", f"{stem}.jpg")
        if not os.path.exists(p):
            src = os.path.join(IM, "inputs", f"{stem}{'__A4' if kind == 'g' else ''}.jpg")
            t0 = time.time(); im = sr_to_1mp(cv2.imread(src))
            cv2.imwrite(p, im, [cv2.IMWRITE_JPEG_QUALITY, 95]); print(f"  sr {stem}: {time.time()-t0:.1f}s", flush=True)
        return cv2.imread(p)

    for g in garments: sr_cache(g, "g")
    for p in persons: sr_cache(p, "p")

    meta = {}
    def ref(g):
        out = os.path.join(OUT, "refs", f"{g}__VS.jpg")
        crop = cv2.imread(os.path.join(IM, "inputs", f"{g}__A4.jpg"))
        fr = L.framing(crop, paths)["framing"]; prompt = SWAP + KEEP + PERSON_CLAUSE[fr] + HOLD
        meta[g] = {"framing": fr, "prompt": prompt}
        if not os.path.exists(out):
            im = recrop(L.call(L.KLEIN, {"image_urls": [L.b64(sr_cache(g, "g"))], "prompt": prompt, "seed": 49}))
            cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return g

    with ThreadPoolExecutor(4) as ex:
        for f in as_completed([ex.submit(ref, g) for g in garments]): print("  ref", f.result(), flush=True)

    def edit(sid, seed):
        out = os.path.join(OUT, "gen", f"{sid}__VS__s{seed}.jpg")
        if os.path.exists(out): return sid, seed
        r = rows[sid]
        im = L.call(L.KLEIN, {"image_urls": [L.b64(sr_cache(r["person"], "p")),
                                             L.b64(cv2.imread(os.path.join(OUT, "refs", f"{r['garment']}__VS.jpg")))],
                              "prompt": E3, "seed": seed})
        cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 95]); return sid, seed

    with ThreadPoolExecutor(6) as ex:
        for f in as_completed([ex.submit(edit, s, sd) for s, sd, _ in cells]):
            print("  edit", *f.result(), flush=True)
    json.dump({"backend": "fal " + L.KLEIN, "cells": [list(c) for c in cells], "sr": "realesr-general-x4v3 x4 -> area 1MP",
               "usd_fal": round((len(garments) + len(cells)) * 0.015, 2)}, open(os.path.join(OUT, "meta", "run.json"), "w"), indent=1)
    json.dump(meta, open(os.path.join(OUT, "meta", "prompts.json"), "w"), indent=1)
    print("done:", len(garments), "refs +", len(cells), "edits")


if __name__ == "__main__":
    main()
