"""v3.5 link C — VEi + head crop against re-pose + head crop, self-hosted klein.

Four arms over `v35_failures.csv` — the 31 pairs the locked v3.4 arm actually failed by
the reviewer's own per-cell verdict (v3.4 RESULTS "Where the failure records live"):

  VEi     the v3.4 lock, unchanged                                   reused, not recomputed
  BC      v3.1's incumbent, unchanged                                reused, not recomputed
  VEic    the lock's reference with the mannequin head CROPPED OFF   new
  M1qbc   Q3 minus the mannequin sentence, PLUS bald, head cropped   new
  VEica   VEic with the ankle cut restored                           new, optional
  M1qbca  M1qbc with the ankle cut restored                          new, optional

An arm name is read, not looked up: base (`VEi` | `M1q` | `M1qb`) + `c` head crop +
`a` ankle cut. Bases are matched longest-first, so `M1qb` is never mistaken for `M1q`
with a stray `b`.

**Why the re-pose arm is bald.** `BC` bald-passes the raw photograph before it crops,
because hair on the shoulders and chest cannot be told from garment by any matte, and
`VEi` gets that free — the mannequin sentence takes the head and its hair together. A
re-pose arm that keeps the wearer's own head does neither, so cropping it leaves whatever
hair spilled onto the garment. `M1q` without the bald clause is therefore not a shippable
arm and is not run: the bald version covers it and is the only functional form. Measured on
the five longest-haired garments of the fold, one klein call does both jobs
(`v3/report/v35_bald.html`).

`VEic` and `M1qc` differ from each other by exactly one deleted sentence in call 1, and
from the lock by the crop. Nothing else moves: same A4 crop, same framing read, same `E3`,
same call-2 canvas, same seeds 46/47/48 as the iron-man 2 record, so every new cell is
paired with a human verdict that already exists.

Order of operations, which is not the obvious one:

    call 1 ─▶ white-margin re-crop ─▶ HEAD CROP ─▶ [ankle cut] ─▶ SR to ~1 MP ─▶ call 2

The crop goes BEFORE the SR pass. Cropping afterwards would take the reference back below
1 MP and break the one rule v3.4 link H bought — what conditioning contributes is bounded
by its token footprint in call 2 (v3.4 SOLUTION §5, rule 3). A head-cropped reference is a
smaller image and has to be re-floated, or the arm tests two changes at once.

**The ankle cut** (`a` arms) is v3.3's, `run_ironman.ankle_cut` verbatim: MediaPipe's ankle
landmarks on the reference, cut 3% of the height above the lower one, with the A4 crop's own
ankle ratio as the fallback. v3.4 **removed** it at the lock — link A found it neutral on
every failure class and made footwear a product decision — so it is reopened here as its own
variable rather than smuggled into the head-crop arms, and it is a no-op by construction on
a reference with no ankles in frame (the detector returns nothing and the image passes
through). Every `a` arm is paired with its cut-less twin at the same seed, so the cut is the
only difference between them.

The head crop is not new code: it is `ironman_bc_crop.crop_bc`, the V2 cropper's own head
subtraction, the identical call that makes the `BC` references. It fires on a mannequin
head as well as a real one — the cranium path was built for BC's bald frames, and takes
head shape from the human parser and head extent from pose landmarks, neither of which
needs hair or a face.

What must already be in `run/` (extracted from the iron-man 2 zips on Drive):
    inputs/{stem}.jpg, inputs/{g}__A4.jpg      the normalised photos and crops
    refs/{g}__VEi_small.jpg                    the lock's reference BEFORE its SR pass
    refs/{g}__BC.jpg                           the incumbent's reference
    gen/{sid}__{VEi,BC}__s{46,47,48}.jpg       the two arms' cells, already judged
Anything missing is computed here; nothing present is recomputed.

Resumable: every stage skips what is on disk. Output: run/{inputs,refs,gen,meta}.
"""
import csv
import json
import os
import platform
import sys
import time

import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v3lib as L                      # noqa: E402
import klein_local as K                # noqa: E402
import run_ironman as R                # noqa: E402  prompts, SR and re-crop of the lock
from ironman_bc_crop import crop_bc    # noqa: E402  the V2 cropper's head subtraction

OUT = "run"
ARMS = ("VEic", "M1qbc")               # +("VEica", "M1qbca") for the ankle-cut twins
REUSED = ("VEi", "BC")                 # the arms it expects to find already made
FAL_PER_CALL = 0.015

# Q3 with the mannequin sentence (SWAP) deleted and nothing else changed. PERSON_CLAUSE
# already carries the re-pose - "Change the pose: the person stands upright in a neutral
# pose, facing forward..." - so no new wording is needed or wanted: one deleted sentence
# is the whole difference between this arm and the lock.
# Lifted from v3lib.BALD_PROMPT's own wording, so the bald instruction is the record's
# rather than a new invention; its third sentence is dropped because KEEP and
# PERSON_CLAUSE already say it.
BALD = (" The person is completely bald: remove all hair from the head and any hair "
        "falling over the shoulders, chest or back, and show the scalp.")


def m1q_prompt(framing):
    return (R.KEEP.lstrip() + R.PERSON_CLAUSE[framing] + R.HOLD)


def m1qb_prompt(framing):
    return (R.KEEP.lstrip() + BALD + R.PERSON_CLAUSE[framing] + R.HOLD)


def q3_prompt(framing):
    return R.SWAP + R.KEEP + R.PERSON_CLAUSE[framing] + R.HOLD


BASES = ("M1qb", "M1q", "VEi")     # longest first: 'M1qb' must not match 'M1q' + 'b'
PROMPT = {}                        # filled below, once the prompt functions exist


def parse_arm(arm):
    """'VEica' -> ('VEi', head_crop=True, ankle_cut=True). The name IS the recipe."""
    for base in BASES:
        if arm.startswith(base):
            tail = arm[len(base):]
            assert set(tail) <= {"c", "a"} and tail.count("c") <= 1 and tail.count("a") <= 1, \
                f"unreadable arm {arm}"
            return base, "c" in tail, "a" in tail
    raise SystemExit(f"unknown arm {arm}")


PROMPT.update({"VEi": q3_prompt, "M1q": m1q_prompt, "M1qb": m1qb_prompt})


_T = []


def _headcut_job(job):
    """One head crop.

    The crop is CPU-bound (BiRefNet + the human parser, both ONNX) and stays that way on
    Colab: onnxruntime's CUDA provider is built against a different CUDA major than torch
    ships (ORT 1.29 wants libcublas.so.13, torch cu128 gives .12), so the provider
    registers, fails to dlopen and falls back silently. Measured on an A100 runtime:
    22s BiRefNet + 17s parser per image.

    These run on THREADS, not processes. ONNX Runtime and MediaPipe release the GIL for
    the duration of inference, so threads get real parallelism; processes do not survive a
    notebook (`spawn` re-imports `__main__`, which is the kernel, and `fork` is unsafe with
    klein already on the GPU). ORT sessions are safe for concurrent Run() calls, and the
    caller warms them on one image first so no two threads race to build the same session.
    """
    import time as _t
    import cv2 as _cv
    from ironman_bc_crop import crop_bc as _crop
    g, base, src, out = job
    t0 = _t.time()
    im, cranium = _crop(_cv.imread(src), f"v35_{base}_{g}")
    _cv.imwrite(out, im, [_cv.IMWRITE_JPEG_QUALITY, 95])
    return g, base, bool(cranium), round(_t.time() - t0, 1)


def _warm(job):
    """The first crop, run alone: it builds the ONNX sessions the threads then share."""
    return _headcut_job(job)


def d(*p):
    q = os.path.join(OUT, *p)
    os.makedirs(os.path.dirname(q), exist_ok=True)
    return q


def timed(stage, arm, ident, seed, fn):
    t0 = time.time()
    r = fn()
    _T.append({"stage": stage, "arm": arm, "id": ident, "seed": seed,
               "seconds": round(time.time() - t0, 3)})
    return r


def klein(stage, arm, ident, seed, images, prompt, canvas):
    im, secs = K.edit(images, prompt, seed, canvas=canvas)
    _T.append({"stage": stage, "arm": arm, "id": ident, "seed": seed, "seconds": secs,
               "klein_call": 1})
    return im


def main(matrix="v35_failures.csv", testset="testset", seeds=(46, 47, 48),
         arms=ARMS, gpu_usd_per_hour=None, limit=None, crop_workers=4):
    for x in ("inputs", "refs", "gen", "meta"):
        os.makedirs(os.path.join(OUT, x), exist_ok=True)
    paths = L.fetch_models(persist=os.environ.get("V3_MODEL_DIR"))
    rows = list(csv.DictReader(open(matrix)))
    if limit:
        rows = rows[:int(limit)]
    seeds = [int(s) for s in seeds]
    garments = sorted({r["garment"] for r in rows})
    files = {r["person"]: r["person_file"] for r in rows}
    files.update({r["garment"]: r["garment_file"] for r in rows})
    wall0 = time.time()
    print(f"{len(rows)} pairs · {len(garments)} garments · arms {arms} "
          f"(+{', '.join(REUSED)} reused) · seeds {seeds}")

    # 1 inputs — only what the iron-man 2 zips did not supply
    made = 0
    for s in sorted(set(files)):
        p = d("inputs", f"{s}.jpg")
        if os.path.exists(p):
            continue
        src = os.path.join(testset, files[s])
        assert os.path.exists(src), f"no photo for {s} at {src}"
        cv2.imwrite(p, L.normalise(cv2.imread(src)), [cv2.IMWRITE_JPEG_QUALITY, 95])
        made += 1
    print(f"1 inputs: {made} normalised, {len(files) - made} reused")

    made = 0
    for g in garments:
        p = d("inputs", f"{g}__A4.jpg")
        if os.path.exists(p):
            continue
        im = timed("a4_crop", "-", g, 0, lambda g=g: L.crop_a4(cv2.imread(d("inputs", f"{g}.jpg")), paths))
        cv2.imwrite(p, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
        made += 1
    print(f"2 crops: {made} made, {len(garments) - made} reused")

    K.load()
    mp = d("meta", "prompts_v35.json")
    meta = json.load(open(mp)) if os.path.exists(mp) else {}

    # 3a every small reference the arms need, one klein call each (GPU, sequential)
    bases = sorted({parse_arm(a)[0] for a in arms}, key=lambda b: BASES.index(b))
    framing, srcs = {}, {}
    for g in garments:
        crop = cv2.imread(d("inputs", f"{g}__A4.jpg"))
        fr = timed("framing", "-", g, 0, lambda c=crop: L.framing(c, paths)["framing"])
        framing[g] = fr
        meta.setdefault(g, {})["framing"] = fr
        for base in bases:
            small = d("refs", f"{g}__{base}_small.jpg")
            srcs[(g, base)] = small
            meta[g][base] = PROMPT[base](fr)
            if os.path.exists(small):       # supplied by a zip, or a previous session
                continue
            im = klein("ref", base, g, seeds[0], [crop], PROMPT[base](fr), "v33")
            cv2.imwrite(small, R.recrop(im), [cv2.IMWRITE_JPEG_QUALITY, 95])
    json.dump(meta, open(mp, "w"), indent=1)

    # 3b head crops, in parallel - the one stage that is not on the GPU
    jobs = [(g, base, srcs[(g, base)], d("refs", f"{g}__{base}_headcut.jpg"))
            for g in garments for base in bases
            if any(parse_arm(a)[1] for a in arms if parse_arm(a)[0] == base)
            and not os.path.exists(d("refs", f"{g}__{base}_headcut.jpg"))]
    if jobs:
        n_w = max(1, int(crop_workers))
        print(f"3b {len(jobs)} head crops on {n_w} thread{'s' if n_w > 1 else ''}", flush=True)
        t0 = time.time()
        if n_w == 1:
            done = [_headcut_job(j) for j in jobs]
        else:
            from concurrent.futures import ThreadPoolExecutor
            done = [_warm(jobs[0])]     # the first crop alone builds the shared sessions
            with ThreadPoolExecutor(max_workers=n_w) as ex:
                for r in ex.map(_headcut_job, jobs[1:]):
                    done.append(r)
                    print(f"    {len(done)}/{len(jobs)} {r[1]} {r[0]} "
                          f"cranium={r[2]} {r[3]}s", flush=True)
        for g, base, cranium, secs in done:
            meta[g][f"{base}_cranium_used"] = cranium
            _T.append({"stage": "headcrop", "arm": base, "id": g, "seed": 0, "seconds": secs})
        el = time.time() - t0
        print(f"   {len(jobs)} crops in {el / 60:.1f} min "
              f"({el / len(jobs):.1f}s each wall, {sum(r[3] for r in done) / len(jobs):.1f}s each cpu)")
        json.dump(meta, open(mp, "w"), indent=1)

    # 3c the ankle cut, then SR - in that order (module docstring)
    for g in garments:
        crop = cv2.imread(d("inputs", f"{g}__A4.jpg"))
        for arm in arms:
            base, head_crop, ankle = parse_arm(arm)
            out = d("refs", f"{g}__{arm}.jpg")
            if os.path.exists(out):
                continue
            im = cv2.imread(d("refs", f"{g}__{base}_headcut.jpg") if head_crop else srcs[(g, base)])
            assert im is not None, f"missing intermediate for {g} {arm}"
            if ankle:
                ya = timed("ankle_read", arm, g, 0, lambda c=crop: R.ankle_y(c, paths))
                im, y = timed("ankle_cut", arm, g, 0, lambda i=im, ya=ya: R.ankle_cut(
                    i, paths, (ya / crop.shape[0]) if ya is not None else None))
                meta[g][f"{arm}_ankle_row"] = y      # None = no ankles in frame, a no-op
            im = timed("sr", arm, g, 0, lambda i=im: R.to_1mp_sr(i))
            cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
            meta[g][f"{arm}_size"] = [im.shape[1], im.shape[0]]
        json.dump(meta, open(mp, "w"), indent=1)
    print(f"3 references: {len(garments)} per arm")

    # 4 edits — only the new arms; VEi and BC cells come from the iron-man 2 run
    have = {a: sum(os.path.exists(d("gen", f"{r['set_id']}__{a}__s{s}.jpg"))
                   for r in rows for s in seeds) for a in REUSED}
    print(f"   reused cells on disk: " + " · ".join(f"{a} {n}/{len(rows) * len(seeds)}"
                                                    for a, n in have.items()))
    n = 0
    for r in rows:
        sid, p, g = r["set_id"], r["person"], r["garment"]
        person = cv2.imread(d("inputs", f"{p}.jpg"))
        for arm in arms:
            ref = cv2.imread(d("refs", f"{g}__{arm}.jpg"))
            assert ref is not None, f"missing reference refs/{g}__{arm}.jpg"
            for seed in seeds:
                out = d("gen", f"{sid}__{arm}__s{seed}.jpg")
                if os.path.exists(out):
                    continue
                cv2.imwrite(out, klein("edit", arm, sid, seed, [person, ref], R.E3, "fal"),
                            [cv2.IMWRITE_JPEG_QUALITY, 95])
                n += 1
                if n % 25 == 0:
                    print(f"    {n} edits", flush=True)
        write_timings(wall0, rows, arms, seeds, gpu_usd_per_hour)
    print(f"4 edits: {n} made")
    write_timings(wall0, rows, arms, seeds, gpu_usd_per_hour)
    json.dump({"pairs": len(rows), "arms": list(arms), "reused_arms": list(REUSED),
               "seeds": seeds, "matrix": matrix, "klein": K.info(),
               "set_definition": "the 31 pairs of iron man 2 with a real VEi failure in "
                                 "v34_im2_truth.json (the reviewer's per-cell verdict)",
               "order": "call 1 -> re-crop -> head crop -> [ankle cut] -> SR to ~1 MP -> call 2",
               "ankle_cut": "run_ironman.ankle_cut (v3.3's), reopened as its own variable; "
                            "a no-op where no ankles are in frame",
               "head_crop": "ironman_bc_crop.crop_bc, the V2 cropper's own subtraction",
               "crop_workers": crop_workers,
               "prompts": {"q3": "SWAP + KEEP + PERSON_CLAUSE + HOLD (the lock)",
                           "m1q": "KEEP + PERSON_CLAUSE + HOLD (Q3 with SWAP deleted)",
                           "m1qb": "KEEP + BALD + PERSON_CLAUSE + HOLD",
                           "bald": BALD, "edit": R.E3, "swap": R.SWAP, "keep": R.KEEP,
                           "hold": R.HOLD, "person_clause": R.PERSON_CLAUSE},
               "python": platform.python_version()},
              open(d("meta", "run_v35.json"), "w"), indent=1)
    print(f"done in {(time.time() - wall0) / 60:.1f} min")


def write_timings(wall0, rows, arms, seeds, rate):
    with open(d("meta", "timings_v35.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["stage", "arm", "id", "seed", "seconds", "klein_call"])
        w.writeheader()
        for t in _T:
            w.writerow({**{"klein_call": 0}, **t})
    calls = [t for t in _T if t.get("klein_call")]
    wall = time.time() - wall0
    by = {}
    for t in _T:
        by.setdefault((t["stage"], t["arm"]), []).append(t["seconds"])
    json.dump({"gpu_usd_per_hour": rate, "model_load_seconds": K.info().get("load_seconds"),
               "klein_calls": len(calls),
               "klein_seconds": round(sum(t["seconds"] for t in calls), 1),
               "stage_seconds_total": round(sum(t["seconds"] for t in _T), 1),
               "wall_seconds": round(wall, 1),
               "usd_measured": round(wall / 3600 * rate, 3) if rate else None,
               "usd_fal_equivalent": round(len(calls) * FAL_PER_CALL, 2),
               "per_stage_mean_seconds": {f"{s}/{a}": round(sum(v) / len(v), 3)
                                          for (s, a), v in by.items()},
               "pairs": len(rows), "seeds": seeds},
              open(d("meta", "cost_v35.json"), "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
