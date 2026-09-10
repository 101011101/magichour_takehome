"""v3.6 — call 2's prompt, self-hosted, on both sides of BC's own record.

Call 1 does not exist in this run. Every arm is handed the two images the shipped `BC`
cell was handed — `inputs/{person}.jpg` and `refs/{garment}__BC.jpg`, the bald pass plus
the V2 head-subtracting crop, not SR'd — on `BC`'s own call-2 canvas (`fal`, the rule
`bc_canvas="fal"` set in the iron-man-2 run). The only thing that varies is the prompt.

  E0   the shipped prompt (v3lib.EDIT_PROMPT)          - NOT re-run: the archive on Drive
                                                         is this arm, and it is what the
                                                         reviewer's verdicts were made on
  ER   E0's verb rewritten: replace the clothing
  EFR  ER + v3.6's no-blend paragraph
  EX   the maximal prompt: removal, layering, piece count, limb count, framing
  ERD  ER + a limb clause built from a pose read of image 1 - DYNAMIC, names only what is
       in frame, which is v2's rule: never name a body part the crop excludes
  ERS  ER + the same clause always, whether or not the parts are in frame - the control
       that says whether the dynamic read is doing any work

The set is `v36_editset.csv`: 29 cells the reviewer marked FAIL for `BC` and 121 it left
unmarked (v3/build/make_v36_editset.py). Both sides on purpose - the failures say what a
longer prompt buys, the 121 say what it costs, and only the second number decides whether
it ships.

Resumable: every cell skips what is on disk. Output: run/{gen,meta}.
"""
import csv
import json
import os
import platform
import time

import cv2

import klein_local as K
import v3lib as L

OUT = "run"
ARMS = ("ER", "EFR", "EX")
FAL_PER_CALL = 0.015

E0 = L.EDIT_PROMPT
# ER: one sentence, not a longer one. "Dress the person in X" names only the putting-on;
# "replace the clothing with X" names the removal too, which is the half every failure on
# this set is about.
ER = ("Replace the clothing in image 1 with the clothing in image 2. Keep the person's "
      "face, identity, body and the background exactly as they are.")
# EFR: ER plus v3.6's no-blend paragraph, tested on fal as EF over the older verb.
EFR = ER + (" The clothing in image 2 replaces what the person is wearing completely: none "
            "of their original garment remains, none of it shows through, and nothing is "
            "layered over or under it. Each piece keeps its own edge - no two fabrics blend "
            "into one another, and no fabric spreads onto skin, hair, hands, feet or shoes.")
# EX: every control at once, in the order the edit happens - remove, then dress, then hold
# the body, then hold the frame. The last sentence exists because the fal probe's limb-count
# arm answered "two legs and two feet" by zooming out and inventing a lower body the crop
# never had.
EX = ("Replace the clothing in image 1 with the clothing in image 2."
      " First remove every garment the person in image 1 is wearing: none of their original"
      " clothing remains anywhere in the picture - not underneath the new clothing, not"
      " showing at a collar, sleeve, hem or waistband, not hanging behind the legs, not in a"
      " reflection or a shadow."
      " Then dress them in exactly the pieces shown in image 2 and no others, layered in the"
      " same order as image 2, each piece the same length, cut, colour and pattern, and each"
      " with its own clear edge - no two fabrics blend into one another, and no fabric"
      " spreads onto skin, hair, hands, feet or shoes."
      " The person keeps their face, identity, hair, skin, body and pose exactly as in image"
      " 1: exactly two arms, two hands, two legs and two feet, in the positions image 1 has"
      " them, and one pair of shoes - add no extra arm, hand, leg, foot or shoe, merge none"
      " together, and remove none."
      " Keep image 1's background and framing exactly: do not zoom out, and draw no part of"
      " the body that image 1 does not show.")

# ---- the dynamic limb clause -------------------------------------------------
# v2's mechanism, applied to call 2 for the first time. MediaPipe Pose already returns a
# visibility and a coordinate per landmark, so "is the foot in frame" is a read, not a
# boundary hunt - and BiRefNet cannot answer it at all: a matte is a silhouette with no
# part labels. Wrists and foot-index are not in v3lib.JOINTS, so they are read here rather
# than by widening the module every other arm of record depends on.
LIMB_LM = {"hands": (15, 16), "feet": (27, 28, 31, 32)}
_ARMS_C = ("two arms and two hands", "arm or hand")
_FEET_C = ("two legs and two feet", "leg, foot or shoe")


def limbs(bgr, paths, vis=0.5, margin=0.02):
    """Which of hands/feet are confident AND inside image 1's frame."""
    res = L._poser(paths).detect(L._mp_image(bgr))
    if not res.pose_landmarks:
        return []
    lm = res.pose_landmarks[0]
    return [k for k, idx in LIMB_LM.items()
            if any(lm[i].visibility >= vis and -margin <= lm[i].x <= 1 + margin
                   and -margin <= lm[i].y <= 1 + margin for i in idx)]


def limb_clause(present):
    """One sentence naming exactly the parts the photograph shows, and nothing else. With
    neither in frame there is no sentence: the arm falls back to plain ER, on purpose."""
    parts = ([_ARMS_C] if "hands" in present else []) + ([_FEET_C] if "feet" in present else [])
    if not parts:
        return ""
    have = ", and ".join(p[0] for p in parts)
    none = ", ".join(p[1] for p in parts)
    shoes = ", and wears one pair of shoes" if "feet" in present else ""
    return (f" The person has exactly {have}, in the positions image 1 has them{shoes} -"
            f" add no extra {none}, merge none together, and remove none.")


ALL_LIMBS = limb_clause(["hands", "feet"])   # ERS: the same sentence on every cell

PROMPT = {"E0": E0, "ER": ER, "EFR": EFR, "EX": EX, "ERS": ER + ALL_LIMBS}
DYNAMIC = ("ERD",)                            # prompt depends on the cell, so it is built per call

_T = []


def d(*p):
    q = os.path.join(OUT, *p)
    os.makedirs(os.path.dirname(q), exist_ok=True)
    return q


def main(matrix="v36_editset.csv", limit=None, arms=ARMS, gpu_usd_per_hour=None):
    wall0 = time.time()
    rows = list(csv.DictReader(open(matrix)))[:limit]
    for arm in arms:
        if arm not in PROMPT and arm not in DYNAMIC:
            raise SystemExit(f"unknown arm {arm}; one of {sorted(set(PROMPT) | set(DYNAMIC))}")
    paths = (L.fetch_models(persist=os.environ.get("V3_MODEL_DIR"))
             if any(a in DYNAMIC for a in arms) else None)
    for r in rows:
        for p in (d("inputs", f"{r['person']}.jpg"), d("refs", f"{r['garment']}__BC.jpg")):
            if not os.path.exists(p):
                raise SystemExit(f"missing input {p} - cell 4 unpacks these off Drive")

    K.load()
    seen = {}       # per-cell record of what the dynamic read said, and what it sent
    mp = d("meta", "prompts_v36.json")
    if os.path.exists(mp):
        seen = json.load(open(mp))
    todo = [(r, a) for r in rows for a in arms
            if not os.path.exists(d("gen", f"{r['set_id']}__{a}__s{r['seed']}.jpg"))]
    print(f"{len(rows)} cells x {len(arms)} arms = {len(rows) * len(arms)}; {len(todo)} to make")

    n = 0
    for r, arm in todo:
        seed = int(r["seed"])
        person = cv2.imread(d("inputs", f"{r['person']}.jpg"))
        ref = cv2.imread(d("refs", f"{r['garment']}__BC.jpg"))
        # canvas 'fal': BC's own call-2 rule in iron man 2, so these cells sit on the same
        # canvas as the archive they are compared against
        if arm in DYNAMIC:
            present = limbs(person, paths)
            prompt = ER + limb_clause(present)
            seen[f"{r['set_id']}|{arm}"] = {"in_frame": present, "prompt": prompt}
        else:
            prompt = PROMPT[arm]
        im, secs = K.edit([person, ref], prompt, seed, canvas="fal")
        cv2.imwrite(d("gen", f"{r['set_id']}__{arm}__s{seed}.jpg"), im,
                    [cv2.IMWRITE_JPEG_QUALITY, 95])
        _T.append({"set_id": r["set_id"], "arm": arm, "seed": seed, "seconds": secs,
                   "out": f"{im.shape[1]}x{im.shape[0]}"})
        n += 1
        if n % 25 == 0 or n == len(todo):
            print(f"    {n}/{len(todo)} edits", flush=True)
            json.dump(seen, open(mp, "w"), indent=1)
            _write(rows, arms, wall0, gpu_usd_per_hour)
    json.dump(seen, open(mp, "w"), indent=1)
    _write(rows, arms, wall0, gpu_usd_per_hour)
    print(f"done: {n} edits in {(time.time() - wall0) / 60:.1f} min")


def _write(rows, arms, wall0, rate):
    with open(d("meta", "timings_v36.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["set_id", "arm", "seed", "seconds", "out"])
        w.writeheader(); w.writerows(_T)
    gpu_s = sum(t["seconds"] for t in _T)
    wall = time.time() - wall0
    json.dump({"cells": len(rows), "arms": list(arms), "calls": len(_T),
               "set": "v36_editset.csv",
               "set_definition": "29 cells the reviewer marked FAIL for BC in the blind "
                                 "bc_count sweep + 121 unmarked cells sampled with "
                                 "random.Random(46) - both sides of the record",
               "prompts": {a: PROMPT[a] for a in ("E0",) + tuple(arms) if a in PROMPT},
               "dynamic_arms": {a: {"base": ER, "clause": "built per cell from a MediaPipe "
                                    "Pose read of image 1 - see meta/prompts_v36.json",
                                    "clause_if_all_in_frame": ALL_LIMBS}
                                for a in arms if a in DYNAMIC},
               "reference": "refs/{garment}__BC.jpg as shipped - bald pass + V2 "
                            "head-subtracting crop, no SR",
               "canvas": "BC's own call-2 rule (fal canvas), as bc_canvas=fal",
               "call_seconds_total": round(gpu_s, 1),
               "call_seconds_median": round(sorted(t["seconds"] for t in _T)[len(_T) // 2], 2) if _T else None,
               "wall_minutes": round(wall / 60, 2),
               "usd_gpu": round(wall / 3600 * rate, 3) if rate else None,
               "usd_fal_equivalent": round(len(_T) * FAL_PER_CALL, 2),
               "klein": K.info(), "python": platform.python_version()},
              open(d("meta", "cost_v36.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
