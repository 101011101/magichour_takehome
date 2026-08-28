"""Orchestrator for the full run. Resumable, arm by arm, stage by stage.

Every stage skips what is already on disk, so a run interrupted by an exhausted balance
resumes without paying twice. That has happened five times at smaller scale; at 200
pairs it is not optional.

Stage order is deliberate: all CPU first, then the per-reference calls, then the
per-pair edits. If the run stops early you keep the expensive shared work.
"""
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v3lib as L  # noqa: E402

OUT = "run"
DIRS = ["inputs", "refs", "gen", "meta"]
ARMS = ("BC", "QX", "MQ")


def d(*p):
    q = os.path.join(OUT, *p)
    os.makedirs(os.path.dirname(q), exist_ok=True)
    return q


def parallel(jobs, workers=6, label=""):
    """Failures are recorded as None rather than aborting; a balance error stops early
    because every subsequent call would fail the same way."""
    res, stop = {}, False
    if not jobs:
        return res
    print(f"  {label}: {len(jobs)} calls", flush=True)
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fn): n for n, fn in jobs}
        done = 0
        for f in as_completed(futs):
            n = futs[f]
            try:
                res[n] = f.result()
            except Exception as e:
                res[n] = None
                if "balance" in str(e).lower() or "locked" in str(e).lower():
                    stop = True
                    print(f"    STOPPED: {str(e)[:90]}", flush=True)
                    break
                print(f"    fail {n}: {str(e)[:80]}", flush=True)
            done += 1
            if done % 20 == 0:
                print(f"    {done}/{len(jobs)}", flush=True)
    return res


def main(matrix="matrix.csv", testset="testset", limit=None, arms=ARMS):
    for x in DIRS:
        os.makedirs(os.path.join(OUT, x), exist_ok=True)
    paths = L.fetch_models()
    rows = list(csv.DictReader(open(matrix)))
    if limit:
        rows = rows[:int(limit)]
    stems = sorted({r["person"] for r in rows} | {r["garment"] for r in rows})
    files = {r["person"]: r["person_file"] for r in rows}
    files.update({r["garment"]: r["garment_file"] for r in rows})
    print(f"{len(rows)} pairs · {len(stems)} images · arms {arms}")

    # ---- 1. normalise, CPU ------------------------------------------
    for s in stems:
        p = d("inputs", f"{s}.jpg")
        if not os.path.exists(p):
            cv2.imwrite(p, L.normalise(cv2.imread(os.path.join(testset, files[s]))),
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"1 normalise: {len(stems)} inputs")

    # ---- 2. A4 crops, CPU/GPU ---------------------------------------
    if "MQ" in arms:
        t0, made = time.time(), 0
        for s in stems:
            p = d("inputs", f"{s}__A4.jpg")
            if os.path.exists(p):
                continue
            cv2.imwrite(p, L.crop_a4(cv2.imread(d("inputs", f"{s}.jpg")), paths),
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            made += 1
            if made % 10 == 0:
                print(f"    crop {made} ({(time.time()-t0)/made:.1f}s each)", flush=True)
        print(f"2 crops: {made} made on {L._S.get('biref_prov','?')}"
              f" ({(time.time()-t0)/max(made,1):.1f}s each)")

    # ---- 3. per-reference calls -------------------------------------
    meta = {}
    if "BC" in arms:
        jobs = [(s, (lambda b=cv2.imread(d("inputs", f"{s}.jpg")): L.call(
            L.KLEIN, {"image_urls": [L.b64(b)], "prompt": L.BALD_PROMPT,
                      "seed": L.SEED}))) for s in stems
            if not os.path.exists(d("refs", f"{s}__BC.jpg"))]
        for k, v in parallel(jobs, 6, "3a bald (BC)").items():
            if v is not None:
                o = cv2.imread(d("inputs", f"{k}.jpg"))
                cv2.imwrite(d("refs", f"{k}__BC.jpg"),
                            cv2.resize(v, (o.shape[1], o.shape[0]),
                                       interpolation=cv2.INTER_AREA))
    if "QX" in arms:
        jobs = [(s, (lambda b=cv2.imread(d("inputs", f"{s}.jpg")): L.call(
            L.QWEN, {"image_urls": [L.b64(b)], "prompt": L.QX_PROMPT,
                     "seed": L.SEED}))) for s in stems
            if not os.path.exists(d("refs", f"{s}__QX.jpg"))]
        for k, v in parallel(jobs, 6, "3b extract (QX)").items():
            if v is not None:
                cv2.imwrite(d("refs", f"{k}__QX.jpg"), v)
    if "MQ" in arms:
        # The prompt record is written for EVERY pair, not only the ones still to
        # generate, and merged with what is already there. Writing only the pending
        # ones overwrote the file with {} on a resumed run and destroyed the record of
        # what had actually been sent.
        mp = d("meta", "mq_prompts.json")
        meta = json.load(open(mp)) if os.path.exists(mp) else {}
        jobs = []
        for r in rows:
            g, p = r["garment"], r["person"]
            key = f"{g}|{p}"
            done = os.path.exists(d("refs", f"{g}__MQ__{p}.jpg"))
            if done and key in meta:
                continue                      # already generated and already recorded
            crop = cv2.imread(d("inputs", f"{g}__A4.jpg"))
            pr, colour, fr = L.mq_prompt(cv2.imread(d("inputs", f"{p}.jpg")), crop, paths)
            meta[key] = {"prompt": pr, "colour": colour, "framing": fr}
            if done:
                continue
            jobs.append((f"{g}__MQ__{p}",
                         (lambda c=crop, q=pr: L.call(
                             L.QWEN, {"image_urls": [L.b64(c)], "prompt": q,
                                      "seed": L.SEED}))))
        json.dump(meta, open(mp, "w"), indent=1)
        for k, v in parallel(jobs, 6, "3c extract (MQ)").items():
            if v is not None:
                cv2.imwrite(d("refs", f"{k}.jpg"), v)

    # ---- 4. the edit, per pair --------------------------------------
    for arm in arms:
        jobs = []
        for r in rows:
            sid, p, g = r["set_id"], r["person"], r["garment"]
            ref = d("refs", f"{g}__MQ__{p}.jpg") if arm == "MQ" \
                else d("refs", f"{g}__{arm}.jpg")
            out = d("gen", f"{sid}__{arm}.jpg")
            if os.path.exists(out) or not os.path.exists(ref):
                continue
            jobs.append((sid, (lambda pi=d("inputs", f"{p}.jpg"), rp=ref: L.call(
                L.KLEIN, {"image_urls": [L.b64(cv2.imread(pi)), L.b64(cv2.imread(rp))],
                          "prompt": L.EDIT_PROMPT, "seed": L.SEED}))))
        for k, v in parallel(jobs, 6, f"4 edit ({arm})").items():
            if v is not None:
                cv2.imwrite(d("gen", f"{k}__{arm}.jpg"), v)

    have = {a: len([f for f in os.listdir(os.path.join(OUT, "gen"))
                    if f.endswith(f"__{a}.jpg")]) for a in arms}
    print("\noutputs: " + " · ".join(f"{a} {n}/{len(rows)}" for a, n in have.items()))
    json.dump({"pairs": len(rows), "arms": list(arms), "have": have,
               "prompts": {"mq_prefix": L.PREFIX, "mq_suffix": L.SUFFIX,
                           "frame_clause": L.FRAME_CLAUSE, "qx": L.QX_PROMPT,
                           "bald": L.BALD_PROMPT, "edit": L.EDIT_PROMPT},
               "seed": L.SEED}, open(d("meta", "run.json"), "w"), indent=1)
    return have


if __name__ == "__main__":
    main(*sys.argv[1:])
