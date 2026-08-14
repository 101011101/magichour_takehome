#  Local smoke test for composite_cells — free; V1 outputs stand in for gens.
import glob
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import composite_cells as cc

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.environ.get(
    "SMOKE_OUT",
    "/private/tmp/claude-501/-Users-arviny-Downloads-Code-magichour-takehome/"
    "692580a9-cd7b-4bb9-a6d8-be57532d610c/scratchpad/composite_smoke")
N_PAIRS = 3


def pick_runs():
    """3 grid_* run dirs with result.png; distinct arms, distinct pairs."""
    picked, arms, pairs = [], set(), set()
    for d in sorted(glob.glob(os.path.join(REPO, "v1", "runs", "grid_*"))):
        rp, cp = os.path.join(d, "result.png"), os.path.join(d, "run_config.json")
        if not (os.path.isfile(rp) and os.path.isfile(cp)):
            continue
        cfg = json.load(open(cp))
        if not cfg.get("pair") or cfg.get("arm") in arms or cfg["pair"] in pairs:
            continue
        picked.append((d, cfg))
        arms.add(cfg["arm"])
        pairs.add(cfg["pair"])
        if len(picked) == N_PAIRS:
            break
    return picked


def side_by_side(images, labels, path):
    h = 512
    scaled = [im.resize((int(im.width * h / im.height), h)) for im in images]
    canvas = Image.new("RGB", (sum(im.width for im in scaled), h + 24), "white")
    x = 0
    draw = ImageDraw.Draw(canvas)
    for im, lab in zip(scaled, labels):
        canvas.paste(im, (x, 24))
        draw.text((x + 4, 4), lab, fill="black")
        x += im.width
    canvas.save(path)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    runs = pick_runs()
    assert runs, "no usable grid_* run dirs found"
    rows = []
    for d, cfg in runs:
        pair = cfg["pair"]
        person_path = os.path.join(REPO, "test_set", "people",
                                   pair.split("x")[0] + ".jpg")
        person = cc.load_image(person_path)
        result = cc.load_image(os.path.join(d, "result.png"))
        ref = cc.face_embedding(person)
        cos_before = cc.identity_cosine(ref, result)
        pasted, meta = cc.face_paste_back(person, result)
        cos_after = cc.identity_cosine(ref, pasted)
        out = os.path.join(OUT_DIR, f"{pair}_{cfg['arm']}.png")
        side_by_side([person, result, pasted],
                     ["person", "v1 output (stand-in gen)", "paste-back"], out)
        rows.append((pair, cfg["arm"], cos_before, cos_after, meta))
        fmt = lambda c: "n/a" if c is None else f"{c:.4f}"
        gate = lambda c: "n/a" if c is None else \
            ("PASS" if c >= cc.IDENTITY_THRESHOLD else "FAIL")
        print(f"{pair} [{cfg['arm']}]: cos before={fmt(cos_before)} "
              f"({gate(cos_before)}) after={fmt(cos_after)} "
              f"({gate(cos_after)}) paste_applied={meta['paste_applied']} "
              f"skip={meta['skip_reason']}  -> {out}")

    # Full-pipeline control flow with free stub callables on the first pair.
    d, cfg = runs[0]
    stand_in = cc.load_image(os.path.join(d, "result.png"))
    person_path = os.path.join(REPO, "test_set", "people",
                               cfg["pair"].split("x")[0] + ".jpg")
    garment_path = os.path.join(REPO, "test_set", "garments",
                                cfg["pair"].split("x")[1] + ".jpg")
    img, meta = cc.composite_try_on(
        person_path, garment_path, seed=46,
        gen_fn=lambda pu, gu, s: stand_in,
        refine_fn=lambda im, s: im,
        upload_fn=lambda x: "stub://local")
    img.save(os.path.join(OUT_DIR, f"{cfg['pair']}_pipeline_stub.png"))
    print("\npipeline stub meta:")
    print(json.dumps(meta, indent=2))


main()
