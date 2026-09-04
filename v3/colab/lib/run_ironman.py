"""The iron-man run: the locked v3.3 version against BC, self-hosted klein, any matrix.

  BC   klein bald pass on the raw photograph -> A4 crop -> klein edit        (v3.1's incumbent)
  V    A4 crop -> klein head swap + PERSON_CLAUSE + hold -> re-crop -> ankle cut -> klein edit (E3)   (the v3.3 lock)
  Vnc  V without the ankle cut                                                                        (v3.4 link A)
  V34  Vnc with call 2 rendered on fal's canvas: area 1024^2, floor 32, up or down                    (the v3.4 version)
  VE   V34 with call 1 on fal's canvas as well - references at ~1 MP                                  (link E)
  VA   VE with every input Lanczos/area-resized to ~1 MP BEFORE its call - klein never scales         (link F)

Both arms: same model, same call 2 except the E3 sentence is the version's. Every model
call and every CPU/GPU stage is timed into meta/timings.csv; meta/cost.json totals them
against a GPU hourly rate you set, beside the fal-equivalent at $0.015/call.

Resumable: every stage skips what is on disk. Output: run/{inputs,refs,gen,meta}.
"""
import csv
import json
import os
import platform
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v3lib as L          # noqa: E402  readers, crop, prompts of the locked v3.1 stack
import klein_local as K    # noqa: E402

OUT = "run"
ARMS = ("BC", "V")
FAL_PER_CALL = 0.015

# ---- the locked v3.3 prompts (prd/v3/v3.3/SOLUTION.md §3, §3b) --------------
SWAP = ("Replace this person's head, from the neck up, with a smooth, featureless "
        "mannequin head of the same size, in the same position and facing the same way "
        "- no face, no hair.")
KEEP = " Keep the clothing, the body, the hands and the background exactly as they are."
HOLD = (" The clothing stays exactly the same through the change of pose - the same "
        "pieces, the same shape, the same length.")
PERSON_CLAUSE = {
    "full_body": (" Change the pose: the person stands upright in a neutral pose, facing "
                  "forward, arms relaxed at the sides, feet together. The photograph shows "
                  "them from head to feet; keep that framing."),
    "knee_up": (" Change the pose: the person stands upright in a neutral pose, facing "
                "forward, arms relaxed at the sides, legs together. The photograph shows "
                "them from the head to the knee only; keep exactly that framing, cut off "
                "below the knee."),
    "waist_up": (" Change the pose: the person stands upright and square to the camera, "
                 "shoulders level, arms relaxed at the sides. The photograph shows them "
                 "from the head to the hip only; keep exactly that framing, cut off below "
                 "the hip."),
    "chest_up": (" Change the pose: the person faces the camera squarely, shoulders level, "
                 "arms down, relaxed at the sides. The photograph shows them from the head "
                 "to the chest only; keep exactly that framing, cut off below the chest."),
    "unknown": (" Change the pose: the person stands upright and square to the camera. "
                "Keep exactly the framing the photograph has."),
}
E3 = (L.EDIT_PROMPT + " The person's body, limbs and feet are exactly as in image 1 - "
      "nothing added, nothing removed.")
BC_EDIT = L.EDIT_PROMPT           # the incumbent keeps V2's edit prompt, as in v3.1
ANKLE_MARGIN = 0.03

_T = []   # timing rows


def d(*p):
    q = os.path.join(OUT, *p)
    os.makedirs(os.path.dirname(q), exist_ok=True)
    return q


def timed(stage, arm, ident, seed, fn):
    t0 = time.time()
    r = fn()
    secs = round(time.time() - t0, 3)
    _T.append({"stage": stage, "arm": arm, "id": ident, "seed": seed, "seconds": secs})
    return r


FAL_CANVAS_ARMS = ("V34", "Vfc")   # the v3.4 version: call 2 on fal's canvas (area 1024^2, floor 32, up or down)
FAL_BOTH_ARMS = ("VE", "VA")       # calls 1 AND 2 on fal's canvas; VA also pre-scales inputs so klein never upscales
ALGO_ARMS = ("VA",)                # link F: inputs algorithmically resized to ~1 MP before the call (Lanczos up, area down)


def to_1mp(bgr, area=1_048_576):
    h, w = bgr.shape[:2]
    k = (area / (h * w)) ** 0.5
    if abs(k - 1.0) < 0.02:
        return bgr
    return cv2.resize(bgr, (max(1, int(w * k)), max(1, int(h * k))),
                      interpolation=cv2.INTER_LANCZOS4 if k > 1 else cv2.INTER_AREA)
_RUN = {"bc_canvas": "v33"}        # BC's call 2 follows the version in the run - the canvas is a property of call 2, not of the arm (RESULTS v3.4 §5)


def klein(stage, arm, ident, seed, images, prompt):
    fal = (arm in FAL_BOTH_ARMS and stage in ("ref", "edit")) or (
        stage == "edit" and (arm in FAL_CANVAS_ARMS or (arm == "BC" and _RUN["bc_canvas"] == "fal")))
    im, secs = K.edit(images, prompt, seed, canvas="fal" if fal else "v33")
    _T.append({"stage": stage, "arm": arm, "id": ident, "seed": seed, "seconds": secs,
               "klein_call": 1})
    return im


# ---- CPU stages ----------------------------------------------------------------
def ankle_y(bgr, paths):
    res = L._poser(paths).detect(L._mp_image(bgr))
    if not res.pose_landmarks:
        return None
    lm = res.pose_landmarks[0]
    ys = [lm[i].y for i in (27, 28) if lm[i].visibility >= 0.5]
    return int(min(ys) * bgr.shape[0]) if ys else None


def recrop(bgr, pad=0.04, thr=245):
    m = (bgr < thr).any(axis=2)
    ys, xs = np.where(m)
    if len(ys) < 20:
        return bgr
    h, w = bgr.shape[:2]
    py, px = int(h * pad), int(w * pad)
    return bgr[max(0, ys.min() - py):min(h, ys.max() + py), max(0, xs.min() - px):min(w, xs.max() + px)]


def ankle_cut(bgr, paths, fallback_ratio=None):
    y = ankle_y(bgr, paths)
    if y is None and fallback_ratio is not None:
        y = int(fallback_ratio * bgr.shape[0])
    if y is None:
        return bgr, None
    y = max(1, int(y - ANKLE_MARGIN * bgr.shape[0]))
    return bgr[:y], y


# ---- the run -------------------------------------------------------------------
def main(matrix="matrix.csv", testset="testset", limit=None, seeds=(46,), arms=ARMS,
         gpu_usd_per_hour=None, stage="all", bc_canvas=None):
    """stage: 'all' | 'bald' (BC bald frames only, refs/{g}__bald.jpg, no crop, no edits)
              | 'bcedit' (BC edits from refs/{g}__BC.jpg supplied from outside - the V2 cropper)
       bc_canvas: BC's call-2 canvas - None follows the run (fal iff a FAL_CANVAS_ARMS arm is
                  present); pass 'fal' explicitly when a 'bcedit' stage pairs with a V34 run"""
    _RUN["bc_canvas"] = bc_canvas or ("fal" if any(a in FAL_CANVAS_ARMS + FAL_BOTH_ARMS for a in arms) else "v33")
    for x in ("inputs", "refs", "gen", "meta"):
        os.makedirs(os.path.join(OUT, x), exist_ok=True)
    paths = L.fetch_models(persist=os.environ.get("V3_MODEL_DIR"))   # cached to Drive after the first fetch
    rows = list(csv.DictReader(open(matrix)))
    if limit:
        rows = rows[:int(limit)]
    seeds = [int(s) for s in seeds]
    stems = sorted({r["person"] for r in rows} | {r["garment"] for r in rows})
    garments = sorted({r["garment"] for r in rows})
    files = {r["person"]: r["person_file"] for r in rows}
    files.update({r["garment"]: r["garment_file"] for r in rows})
    wall0 = time.time()
    print(f"{len(rows)} pairs · {len(stems)} images · {len(garments)} garments · arms {arms} · seeds {seeds}")

    # 1 normalise
    for s in stems:
        p = d("inputs", f"{s}.jpg")
        if not os.path.exists(p):
            cv2.imwrite(p, L.normalise(cv2.imread(os.path.join(testset, files[s]))), [cv2.IMWRITE_JPEG_QUALITY, 95])

    # 2 A4 crops of every garment (BiRefNet on the GPU)
    made = 0
    for g in garments:
        p = d("inputs", f"{g}__A4.jpg")
        if os.path.exists(p):
            continue
        im = timed("a4_crop", "-", g, 0, lambda g=g: L.crop_a4(cv2.imread(d("inputs", f"{g}.jpg")), paths))
        cv2.imwrite(p, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
        made += 1
    print(f"2 crops: {made} made on {L._S.get('biref_prov', '?')}")

    if stage != "bcedit":
        K.load()
    else:
        K.load()
    meta = {}
    mp = d("meta", "prompts.json" if matrix == "matrix.csv" else f"prompts_{os.path.splitext(os.path.basename(matrix))[0]}.json")
    if os.path.exists(mp):
        meta = json.load(open(mp))

    # 3 references, per garment
    for g in garments:
        crop = cv2.imread(d("inputs", f"{g}__A4.jpg"))
        raw = cv2.imread(d("inputs", f"{g}.jpg"))
        for varm in [a for a in ("V", "Vnc", "Vfc", "V34", "VE", "VA") if a in arms]:   # Vnc = no cut; V34 = fal call-2 canvas; VE = fal canvas both calls; VA = + algorithmic input scaling
            fr = timed("framing", varm, g, 0, lambda c=crop: L.framing(c, paths)["framing"])
            prompt = SWAP + KEEP + PERSON_CLAUSE[fr] + HOLD
            meta[f"{g}|{varm}"] = {"framing": fr, "prompt": prompt, "ankle_cut": varm == "V"}
            out = d("refs", f"{g}__{varm}.jpg")
            if not os.path.exists(out):
                im = klein("ref", varm, g, seeds[0], [to_1mp(crop) if varm in ALGO_ARMS else crop], prompt)
                im = recrop(im)
                cv2.imwrite(d("refs", f"{g}__{varm}_uncut.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 95])   # kept from now on
                if varm == "V":
                    ya = ankle_y(crop, paths)
                    im, y = timed("ankle_cut", "V", g, 0, lambda im=im, ya=ya: ankle_cut(
                        im, paths, (ya / crop.shape[0]) if ya is not None else None))
                    meta[f"{g}|V"]["ankle_cut_row"] = y
                cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 95])
        if "BC" in arms and stage != "bcedit":
            meta[f"{g}|BC"] = {"prompt": L.BALD_PROMPT, "crop": "V2 cropper, head subtracted (run locally: v3/build/ironman_bc_crop.py)"}
            braw = d("refs", f"{g}__bald.jpg")
            if not os.path.exists(braw):
                bald = klein("bald", "BC", g, seeds[0], [raw], L.BALD_PROMPT)
                bald = cv2.resize(bald, (raw.shape[1], raw.shape[0]), interpolation=cv2.INTER_AREA)
                cv2.imwrite(braw, bald, [cv2.IMWRITE_JPEG_QUALITY, 95])
            # the BC reference itself (head subtracted) is made by the V2 cropper outside this
            # runner; it must exist as refs/{g}__BC.jpg before the 'bcedit' stage
        json.dump(meta, open(mp, "w"), indent=1)
    print(f"3 references: {len(garments)} per arm")
    if stage == "bald":
        write_timings(wall0, rows, arms, seeds, gpu_usd_per_hour); print("bald stage done"); return

    # 4 edits, per pair, per seed
    n = 0
    for r in rows:
        sid, p, g = r["set_id"], r["person"], r["garment"]
        person = cv2.imread(d("inputs", f"{p}.jpg"))
        for arm in arms:
            if stage == "bcedit" and arm != "BC": continue
            if arm == "Vnc" and stage == "all" and "BC" in arms: pass
            if not os.path.exists(d("refs", f"{g}__{arm}.jpg")):
                raise SystemExit(f"missing reference refs/{g}__{arm}.jpg" + (" - run the V2 cropper first" if arm == "BC" else ""))
            ref = cv2.imread(d("refs", f"{g}__{arm}.jpg"))
            prompt = E3 if arm in ("V", "Vnc", "Vfc", "V34", "VE", "VA") else BC_EDIT
            im1 = to_1mp(person) if arm in ALGO_ARMS else person
            for seed in seeds:
                out = d("gen", f"{sid}__{arm}__s{seed}.jpg")
                if os.path.exists(out):
                    continue
                cv2.imwrite(out, klein("edit", arm, sid, seed, [im1, ref], prompt), [cv2.IMWRITE_JPEG_QUALITY, 95])
                n += 1
                if n % 25 == 0:
                    print(f"    {n} edits", flush=True)
        write_timings(wall0, rows, arms, seeds, gpu_usd_per_hour)
    print(f"4 edits: {n} made")
    write_timings(wall0, rows, arms, seeds, gpu_usd_per_hour)
    json.dump({"pairs": len(rows), "arms": list(arms), "seeds": seeds, "matrix": matrix,
               "bc_canvas": _RUN["bc_canvas"],
               "klein": K.info(), "prompts": {"swap": SWAP, "keep": KEEP, "hold": HOLD,
               "person_clause": PERSON_CLAUSE, "edit_V": E3, "edit_BC": BC_EDIT,
               "bald": L.BALD_PROMPT}, "python": platform.python_version()},
              open(d("meta", "run.json"), "w"), indent=1)
    print(f"done in {(time.time() - wall0) / 60:.1f} min")


def write_timings(wall0, rows, arms, seeds, rate):
    with open(d("meta", "timings.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["stage", "arm", "id", "seed", "seconds", "klein_call"])
        w.writeheader()
        for t in _T:
            w.writerow({**{"klein_call": 0}, **t})
    calls = [t for t in _T if t.get("klein_call")]
    by = {}
    for t in _T:
        k = (t["stage"], t["arm"])
        by.setdefault(k, []).append(t["seconds"])
    gpu_s = sum(t["seconds"] for t in _T)
    wall = time.time() - wall0
    cost = {"gpu_usd_per_hour": rate, "model_load_seconds": K.info().get("load_seconds"),
            "klein_calls": len(calls), "klein_seconds": round(sum(t["seconds"] for t in calls), 1),
            "klein_seconds_per_call": round(sum(t["seconds"] for t in calls) / max(len(calls), 1), 2),
            "stage_seconds_total": round(gpu_s, 1), "wall_seconds": round(wall, 1),
            "usd_measured": round(wall / 3600 * rate, 3) if rate else None,
            "usd_fal_equivalent": round(len(calls) * FAL_PER_CALL, 2),
            "per_arm": {a: {"klein_calls": sum(1 for t in calls if t["arm"] == a),
                            "klein_seconds": round(sum(t["seconds"] for t in calls if t["arm"] == a), 1)} for a in arms},
            "per_stage_mean_seconds": {f"{s}/{a}": round(float(np.mean(v)), 3) for (s, a), v in by.items()},
            "pairs": len(rows), "seeds": seeds}
    json.dump(cost, open(d("meta", "cost.json"), "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
