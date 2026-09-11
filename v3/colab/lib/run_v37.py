"""v3.7 link A - BC with the target person handed to the bald call.

CONCLUDED 2026-09-10, NEGATIVE. This arm does not work and is not shipping; the record is
prd/v3/v3.7/EXPERIMENT.md. klein does not re-pose a wearer to match a reference photograph:
over 51 pairs, 32 came back in the source pose, 18 collapsed onto image 2 - returning the
TARGET's own photograph with the garment swapped in - and 1 was a genuine transfer. Both
wordings behave the same, so it is the model's answer and not the prompt's. Kept runnable
because the evidence page rebuilds from its outputs, and because the next person to think
of this should be able to re-run it rather than re-derive it.

One arm, one change, against the incumbent's own record:

  BC    klein balds the raw garment photo -> V2 head-subtracting crop -> klein edit
  BCp   klein balds the raw garment photo WHILE RE-POSING IT TO THE TARGET -> same crop -> same edit
  BCp2  BCp with call 1 re-worded: image 2 declared a POSE REFERENCE ONLY, pose asked first

Call 1 of `BC` sees one image and is told to remove hair. Call 1 of `BCp` sees two - the
garment photo first, the target person second - and is told to remove hair AND to put the
wearer into the target's pose. Call 2 is `BC`'s verbatim (`v3lib.EDIT_PROMPT`), at the same
seed 46, so the only thing that has moved between the two arms is what call 1 was given and
asked for.

**Why this is worth a run.** Every pose-fixing arm so far (v3.3's `V`/E3, v3.5's `M1q`) asks
for a pose in *words* - PERSON_CLAUSE names a stance and a framing from a landmark read of
the crop, and the model has to invent the rest. Handing klein the actual target photograph
replaces that description with an example. It also removes the framing guess: the target
image carries its own crop, so there is nothing to classify into full_body/knee_up/waist_up.
The risk it takes on is identity leak - two people in one call, and klein may return the
target's face, body or background instead of the wearer's garment - which is exactly what
the reference images on the report page are there to show.

`BCp2` exists because a single failing sentence proves nothing about the model. `BCp` asks
for the re-pose third, after the bald instruction, in the shape the arm was specified in.
`BCp2` puts the pose first and states image 2's role before asking for anything, then
forbids taking anything else from it. If klein can read a pose out of a second image at all,
one of the two wordings should show it; if neither does, the capability is absent rather
than badly asked for.

The reference is now PER PAIR, not per garment: it depends on the target. That is a real
cost (BC amortises one bald call across every pair sharing a garment, this cannot) and it is
recorded rather than argued about - meta/cost_v37.json counts the calls both ways.

Order of operations is BC's, unchanged:

    raw garment photo + target photo ─▶ call 1 ─▶ V2 head-subtracting crop ─▶ call 2

The crop is `ironman_bc_crop.crop_bc`, the V2 cropper of record - the same call that makes
every `BC` reference in the iron-man and link C runs. It fires on a bald head without a
face, which is what call 1 returns.

What must already be in `run/` (extracted from the link C zip):
    inputs/{stem}.jpg                    the normalised photos
    refs/{g}__BC.jpg                     the incumbent's reference
    gen/{sid}__BC__s46.jpg               the incumbent's cells, already judged
Anything missing is computed here; nothing present is recomputed.

Resumable: every stage skips what is on disk. Output: run/{inputs,refs,gen,meta}.
"""
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "v3", "build"))
import v3lib as L                      # noqa: E402
from ironman_bc_crop import crop_bc    # noqa: E402  the V2 cropper's head subtraction

OUT = "run"
ARMS = ("BCp", "BCp2")
SEED = 46
FAL_PER_CALL = 0.015

# Call 1. Sentence 1-2 are BALD_PROMPT's, verbatim. Sentence 3 is the new instruction and
# the whole of the arm. BALD_PROMPT's own closing clause ("keep the clothing, the body, the
# pose and the background exactly as they are") cannot survive a re-pose, so it is replaced
# by the garment-hold wording the v3.3 lock already uses (run_ironman.HOLD) plus an explicit
# refusal of image 2's person - the one failure mode two images in one call invites.
# "this person" also becomes "the person in image 1": with two images in the call there is
# no longer a single referent for it.
REPOSE = (L.BALD_PROMPT.rsplit(" Keep the clothing", 1)[0]
          .replace("Make this person", "Make the person in image 1", 1) +
          " Re-pose the person from image 1 to match the person in image 2: the same body "
          "orientation, the same stance, the same arm and leg positions, and the same "
          "framing in the photograph. The clothing stays exactly the same through the "
          "change of pose - the same pieces, the same shape, the same length, the same "
          "colour and pattern. Return the person from image 1 only: do not take the face, "
          "the hair, the body or the background of image 2.")
# The same request, re-ordered and role-declared. Nothing about call 2 changes.
REPOSE2 = ("Image 2 is a pose reference only. Put the person from image 1 into the pose of "
           "the person in image 2: the same body orientation, the same stance, the same arm "
           "and leg positions, and the same framing in the photograph. Take nothing else "
           "from image 2 - not its clothing, not its face, not its body, not its background. "
           "The person from image 1 keeps their own clothing exactly: the same pieces, the "
           "same shape, the same length, the same colour and pattern. Make them completely "
           "bald - remove all hair from the head and any hair falling over the shoulders, "
           "chest or back, and show the scalp.")
CALL1 = {"BCp": REPOSE, "BCp2": REPOSE2}
EDIT = L.EDIT_PROMPT                  # BC's call 2, untouched

_T = []


def d(*p):
    q = os.path.join(OUT, *p)
    os.makedirs(os.path.dirname(q), exist_ok=True)
    return q


def parallel(jobs, workers=6, label=""):
    """A balance error stops the run; anything else is recorded as None and the rest go on.
    Lifted from run_all.parallel - the same failure policy the fal runs have always had."""
    res = {}
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
                    print(f"    STOPPED: {str(e)[:90]}", flush=True)
                    break
                print(f"    fail {n}: {str(e)[:80]}", flush=True)
            done += 1
            if done % 10 == 0:
                print(f"    {done}/{len(jobs)}", flush=True)
    return res


def main(matrix, testset, limit=None, workers=6, stage="all", arms=ARMS):
    """stage: 'all' | 'call1' (references only, no crop, no edits)"""
    for x in ("inputs", "refs", "gen", "meta"):
        os.makedirs(os.path.join(OUT, x), exist_ok=True)
    rows = list(csv.DictReader(open(matrix)))
    if limit:
        rows = rows[:int(limit)]
    stems = sorted({r["person"] for r in rows} | {r["garment"] for r in rows})
    files = {r["person"]: r["person_file"] for r in rows}
    files.update({r["garment"]: r["garment_file"] for r in rows})
    wall0 = time.time()
    print(f"{len(rows)} pairs · {len(stems)} images · arms {tuple(arms)} · seed {SEED}")

    # 1 normalise - a no-op on the images the link C zip already carries
    made = 0
    for s in stems:
        p = d("inputs", f"{s}.jpg")
        if not os.path.exists(p):
            cv2.imwrite(p, L.normalise(cv2.imread(os.path.join(testset, files[s]))),
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            made += 1
    print(f"1 normalise: {made} made, {len(stems) - made} reused")

    # 2 call 1, per PAIR and per arm - bald + re-pose to the target
    for arm in arms:
        jobs = []
        for r in rows:
            sid, p, g = r["set_id"], r["person"], r["garment"]
            if os.path.exists(d("refs", f"{sid}__{arm}_raw.jpg")):
                continue
            jobs.append((sid, (lambda gp=d("inputs", f"{g}.jpg"), pp=d("inputs", f"{p}.jpg"), a=arm:
                               L.call(L.KLEIN, {"image_urls": [L.b64(cv2.imread(gp)),
                                                               L.b64(cv2.imread(pp))],
                                                "prompt": CALL1[a], "seed": SEED}))))
        t0 = time.time()
        for k, v in parallel(jobs, workers, f"2 bald+re-pose ({arm} call 1)").items():
            if v is not None:
                cv2.imwrite(d("refs", f"{k}__{arm}_raw.jpg"), v, [cv2.IMWRITE_JPEG_QUALITY, 95])
        _T.append({"stage": "call1", "arm": arm, "n": len(jobs),
                   "seconds": round(time.time() - t0, 1)})

    if stage == "call1":
        print("call1 stage done"); return

    # 3 the V2 head-subtracting crop, CPU, SERIAL
    #
    # Serial on purpose. This looks thread-parallel - BiRefNet and the human parser are
    # onnxruntime and release the GIL - but `phase3_variants.masks` also calls MediaPipe's
    # ImageSegmenter, and one segmenter is not safe for concurrent segment() calls. Three
    # workers sharing it made no progress at all in 26 minutes on this machine, where the
    # serial path takes about a minute per crop. Threads here are a false economy.
    crop_rec = {}
    pend = [(r["set_id"], a) for a in arms for r in rows
            if os.path.exists(d("refs", f'{r["set_id"]}__{a}_raw.jpg'))
            and not os.path.exists(d("refs", f'{r["set_id"]}__{a}.jpg'))]
    t0 = time.time()
    for i, (sid, a) in enumerate(pend, 1):
        try:
            im, cranium = crop_bc(cv2.imread(d("refs", f"{sid}__{a}_raw.jpg")), f"{a}_{sid}")
        except Exception as e:
            print(f"    crop fail {a} {sid[:40]}: {str(e)[:70]}", flush=True)
            continue
        cv2.imwrite(d("refs", f"{sid}__{a}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 95])
        crop_rec[f"{a}|{sid}"] = {"cranium_used": bool(cranium), "size": [im.shape[1], im.shape[0]]}
        print(f"    crop {i}/{len(pend)} {a} {sid[:44]} ({(time.time()-t0)/i:.0f}s each)", flush=True)
    _T.append({"stage": "crop", "arm": "-", "n": len(pend), "seconds": round(time.time() - t0, 1)})
    print(f"3 crops: {len(pend)} made ({(time.time() - t0) / max(len(pend), 1):.0f}s each)")

    # 4 call 2 - BC's edit, verbatim
    for arm in arms:
        jobs = []
        for r in rows:
            sid, p = r["set_id"], r["person"]
            ref = d("refs", f"{sid}__{arm}.jpg")
            if os.path.exists(d("gen", f"{sid}__{arm}__s{SEED}.jpg")) or not os.path.exists(ref):
                continue
            jobs.append((sid, (lambda pp=d("inputs", f"{p}.jpg"), rp=ref:
                               L.call(L.KLEIN, {"image_urls": [L.b64(cv2.imread(pp)),
                                                               L.b64(cv2.imread(rp))],
                                                "prompt": EDIT, "seed": SEED}))))
        t0 = time.time()
        for k, v in parallel(jobs, workers, f"4 edit ({arm} call 2)").items():
            if v is not None:
                cv2.imwrite(d("gen", f"{k}__{arm}__s{SEED}.jpg"), v, [cv2.IMWRITE_JPEG_QUALITY, 95])
        _T.append({"stage": "call2", "arm": arm, "n": len(jobs),
                   "seconds": round(time.time() - t0, 1)})

    have = {a: len([f for f in os.listdir(os.path.join(OUT, "gen"))
                    if f.endswith(f"__{a}__s{SEED}.jpg")]) for a in arms}
    calls = sum(t["n"] for t in _T if t["stage"].startswith("call"))
    garments = len({r["garment"] for r in rows})
    json.dump({"pairs": len(rows), "arms": list(arms), "seed": SEED, "matrix": matrix,
               "have": have, "model": L.KLEIN,
               "prompts": {**{f"call1_{a}": CALL1[a] for a in arms},
                           "call2_edit": EDIT, "call1_BC_incumbent": L.BALD_PROMPT},
               "crop": {"cropper": "v2 phase3_variants.masks(cranium=True) -> noface",
                        "refs": crop_rec},
               "timings": _T,
               "cost_usd": {"this_run": round(calls * FAL_PER_CALL, 3),
                            "per_pair_calls_BCp": 2,
                            "per_pair_calls_BC": round(1 + garments / len(rows), 2),
                            "note": "BC amortises one bald call over every pair sharing a "
                                    "garment; BCp cannot - its reference depends on the target"},
               "wall_minutes": round((time.time() - wall0) / 60, 1)},
              open(d("meta", "run_v37.json"), "w"), indent=1)
    print("\noutputs: " + " · ".join(f"{a} {n}/{len(rows)}" for a, n in have.items()) +
          f" · {calls} calls · "
          f"${calls * FAL_PER_CALL:.2f} · {(time.time() - wall0) / 60:.1f} min")
    return have


if __name__ == "__main__":
    main(*sys.argv[1:])
