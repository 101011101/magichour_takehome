# Attention Modulation Test — the klein run. One command once fal has balance.
#
# Completes any missing references (bald frames, QX extractions), then runs klein
# over every (pair x arm) with person image, prompt and seed held fixed so the only
# variable is the garment reference.
import csv
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amt_refs                    # noqa: E402
import garment_crop as G           # noqa: E402
import phase3_fal as F             # noqa: E402
import phase3_variants as P        # noqa: E402

OUT = os.path.join(P.REPO, "v2", "runs", "amt")
ARMS = ["control", "QX_qwen_p1", "BC_klein", "BALD_raw",
        "D1hO", "D2O", "D3O", "D1hB", "D2B", "D3B"]
PROMPT = ("Dress the person in image 1 in the clothing shown in image 2. Keep the "
          "person's face, identity, body and the background exactly as they are.")
SEED = 46


def complete_refs(meta, srcs):
    """Fill in what needs a paid call: bald frames, then Qwen extractions."""
    need_b = [s for s in srcs
              if not os.path.exists(os.path.join(P.REPO, "v2", "runs", "phase3", f"{s}__PRE2raw.jpg"))]
    if need_b:
        print(f"balding {len(need_b)} sources")
        r = F.run([(s, (lambda b=cv2.imread(meta[s]): F.make_bald("PRE2", b))) for s in need_b], 5)
        for s, v in r.items():
            if v is None:
                continue
            o = cv2.imread(meta[s])
            G.write_rgb(os.path.join(P.REPO, "v2", "runs", "phase3", f"{s}__PRE2raw.jpg"),
                        cv2.resize(v, (o.shape[1], o.shape[0]), interpolation=cv2.INTER_AREA))
    need_q = [s for s in srcs
              if not os.path.exists(os.path.join(P.REPO, "v2", "runs", "acab", f"{s}__QX_qwen_p1.jpg"))]
    if need_q:
        print(f"extracting {len(need_q)} sources")
        pr = json.load(open(os.path.join(P.REPO, "v2", "runs", "acab", "_manifest.json")))["prompts"]["p1"]
        r = F.run([(s, (lambda b=cv2.imread(meta[s]): F.call(
            "fal-ai/qwen-image-edit-2511",
            {"image_urls": [F._b64(b)], "prompt": pr, "seed": SEED}))) for s in need_q], 5)
        for s, v in r.items():
            if v is not None:
                G.write_rgb(os.path.join(P.REPO, "v2", "runs", "acab", f"{s}__QX_qwen_p1.jpg"), v)


def main():
    F._load_env()
    meta = {r["stem"]: r["src_path"] for r in
            csv.DictReader(open(os.path.join(P.REPO, "v2", "runs", "crop_screen", "crop_log.csv")))}
    pj = json.load(open(os.path.join(OUT, "_pairs.json")))
    complete_refs(meta, pj["srcs"])
    amt_refs.main()                       # rebuild refs now that everything exists
    refs = json.load(open(os.path.join(OUT, "_refs.json")))["files"]

    gen = os.path.join(OUT, "gen")
    os.makedirs(gen, exist_ok=True)
    jobs, seen = [], {}
    for sid, per, src in pj["pairs"]:
        pimg = cv2.imread(meta[per])
        for a in ARMS:
            key = f"{src}|{a}"
            if key not in refs:
                continue
            out = f"{sid.replace('/', '_')}__{a}.jpg"
            if os.path.exists(os.path.join(gen, out)):
                seen[f"{sid}|{a}"] = out
                continue
            rp = os.path.join(OUT, refs[key])
            jobs.append((f"{sid}|{a}", (lambda p=pimg, rp=rp: F.call(
                "fal-ai/flux-2/klein/4b/distilled/edit",
                {"image_urls": [F._b64(p), F._b64(cv2.imread(rp))],
                 "prompt": PROMPT, "seed": SEED}))))
    print(f"\n{len(jobs)} klein generations (~${len(jobs) * 0.015:.2f}), {len(seen)} already done")
    res = F.run(jobs, workers=6)
    for k, v in res.items():
        if v is None:
            continue
        sid, a = k.split("|")
        o = f"{sid.replace('/', '_')}__{a}.jpg"
        G.write_rgb(os.path.join(gen, o), v)
        seen[k] = o
    json.dump({"pairs": pj["pairs"], "arms": ARMS, "gen": seen, "refs": refs},
              open(os.path.join(OUT, "_run.json"), "w"), indent=1)
    print(f"\n{len(seen)} outputs on disk")


if __name__ == "__main__":
    main()
