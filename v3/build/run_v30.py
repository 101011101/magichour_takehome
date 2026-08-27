"""Run the v3.0 evaluation matrix: BC_klein and QX over 36 pairs.

Reads v3/testsets/v30_matrix.csv and does nothing it is not told to by that file.
Resumable: every stage skips work already on disk, so a partial failure costs the
missing calls only. Stages, in order:

  norm    normalise every input to ~1 MP JPEG                     free
  crop    CPU mask stack on the raw reference (proves the stack)  free
  bald    klein bald pass, WORN references only                   paid
  bcref   crop the bald frame -> the reference call 2 receives    free
  qxref   Qwen-Image-Edit-2511 extraction, prompt p1              paid
  edit    klein edit, both arms                                    paid
  qqedit  QWEN edit on the QX reference - the abandoned all-Qwen arm  paid
  shape   extract one named shape over every reference (--shape TAG)  paid
  arm     klein edit against one named shape (--arm TAG), writing
          gen/{set_id}__TAG.jpg so it sits beside BC and QX           paid
  ph      v3.2 pass 1: klein edit against the RAW crop (PHEAD - no
          bald pass), writing gen/{set_id}__PH.jpg                    paid
  ph2     v3.2 pass 2: the PH output goes back in as image 1 against
          the same RAW crop, writing gen/{set_id}__PH2.jpg            paid

Product references (flat-lay / ghost mannequin) are not balded: there is no head
to remove, so the call would be spend with nothing to do. That is recorded per
reference in _run.json rather than left implicit.

Run A used the 36-pair Testset2 matrix; run B uses the 28-pair test_set3 fold.
Which one is selected by --run, and each writes to its own directory.

Usage: python3 v3/build/run_v30.py --run {a,b} [--dry] [--only stage[,stage]]
"""
import csv
import json
import os
import sys

import cv2
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v2", "build"))
import garment_crop as G          # noqa: E402
import phase3_fal as F            # noqa: E402
import phase3_variants as P       # noqa: E402

LABEL = "b"
RUN = MATRIX = None


def select(label):
    """Point the module at one run's matrix and output directory."""
    global LABEL, RUN, MATRIX
    LABEL = label
    RUN = os.path.join(REPO, "v3", "runs", f"v3.0{label}")
    MATRIX = os.path.join(REPO, "v3", "testsets", f"v30_matrix_{label}.csv")
    return RUN, MATRIX
SEED = 46
MAXPIX = 1_150_000
PROMPT = ("Dress the person in image 1 in the clothing shown in image 2. Keep the "
          "person's face, identity, body and the background exactly as they are.")
# The three V2 extraction prompts, verbatim from v2/runs/acab/_manifest.json, so that
# anything measured here is comparable to V2's drift table rather than a near-miss.
#   p1 QX  isolate on white - what has been shipping
#   p2 QF  flat product photograph - laid out
#   p3 QM  ghost mannequin - keeps the drape, loses the wearer
EXTRACT = {
    "QX": ("Return only the clothing from this photo, isolated on a plain white "
           "background. Remove the person entirely - no face, no skin, no hair, "
           "no background. Preserve the garment's exact colour, pattern and shape."),
    "QF": ("Extract the garment as a flat product photograph on pure white. Keep every "
           "detail of the fabric - the exact colour, print, texture and cut. Do not "
           "redesign, restyle or complete anything that is not visible."),
    "QM": ("Show this outfit as a ghost mannequin product shot on white: the clothing "
           "keeps its shape and drape as if worn, but the person is invisible. "
           "Identical colour and pattern."),
    # p4/p5 - written 2026-08-26 after p1 and p2 were found to drop pieces.
    # The fault in p1/p2 is one word: "the garment", singular, which invites the model
    # to pick one. p2 compounds it with "do not complete anything that is not visible",
    # which discourages showing an occluded piece at all - g018 came back as a blazer
    # with no trousers. Footwear and accessories were dropped almost everywhere.
    # The fix is to enumerate the slots rather than to ask harder for "everything":
    # a named list is something the model can check itself against.
    "QFA": ("Lay out the complete outfit this person is wearing as a flat product "
            "photograph on pure white. Include every piece: the top, any outer layer "
            "or jacket, the lower garment, the footwear, and every accessory - bag, "
            "belt, hat, scarf, eyewear and jewellery. Arrange the pieces side by side "
            "so that each one is separate and fully visible, none overlapping another. "
            "Reproduce each piece's exact colour, print, texture and cut. Every piece "
            "in the photograph must appear in the layout."),
    # p6/p7 - p4/p5 fixed the dropping and caused a worse fault: naming the accessory
    # slots ("bag, belt, hat, scarf, eyewear and jewellery") made the model GENERATE
    # them. Every reference came back wearing a hat it never wore. The list has to go.
    "QFB": ("Lay out the outfit this person is wearing as a flat product photograph on "
            "pure white. Show every piece they are actually wearing, from what is on "
            "their head to what is on their feet, arranged side by side so each piece "
            "is separate and fully visible. Copy each piece exactly as it appears - the "
            "same colour, print, texture and cut. The layout contains only what the "
            "person is wearing and nothing else: if they are not wearing a hat, there "
            "is no hat in the layout."),
    "QMB": ("Show this person's outfit on a mannequin against pure white. The mannequin "
            "wears every piece the person is actually wearing, from head to feet, "
            "exactly as they wear it, keeping its shape and drape - and the person "
            "themself is gone, no face, no skin, no hair. Copy each piece exactly - the "
            "same colour, print, texture and cut. The mannequin wears only what the "
            "person is wearing and nothing else: if they are not carrying a bag, there "
            "is no bag."),
    # p8 - QFB was clean on accessories but "from what is on their head to what is on
    # their feet" was read as an instruction to include the HEAD: three of four layouts
    # came back with a floating wig or a face. Footwear named directly instead.
    # Still imperfect: "side by side" appears to be read as "show variants", and three
    # of four layouts duplicate pieces. The mannequin shape has no such problem.
    "QFC": ("Lay out the outfit this person is wearing as a flat product photograph on "
            "pure white. Show every garment they are wearing together with their "
            "footwear, arranged side by side so each piece is separate and fully "
            "visible. Copy each piece exactly as it appears - the same colour, print, "
            "texture and cut. The layout contains clothing only: no person, no head, "
            "no hair, no skin, and nothing the person is not wearing."),
    "QMA": ("Show this person's complete outfit on a mannequin against pure white. "
            "Every layer is worn exactly as it is worn in the photograph, keeping its "
            "shape and drape, and the person themself is gone - no face, no skin, no "
            "hair. Include the footwear and every accessory - bag, belt, hat, scarf, "
            "eyewear and jewellery - worn or placed as they are in the photograph. "
            "Reproduce each piece's exact colour, print, texture and cut. Every piece "
            "in the photograph must appear on the mannequin."),
}
QX_PROMPT = EXTRACT["QX"]
KLEIN = "fal-ai/flux-2/klein/4b/distilled/edit"
QWEN = "fal-ai/qwen-image-edit-2511"


def d(*p):
    q = os.path.join(RUN, *p)
    os.makedirs(os.path.dirname(q), exist_ok=True)
    return q


def norm(src, dst):
    if os.path.exists(dst):
        return
    im = cv2.imread(src)
    if im is None:
        raise SystemExit(f"unreadable: {src}")
    h, w = im.shape[:2]
    if h * w > MAXPIX:
        k = (MAXPIX / (h * w)) ** 0.5
        im = cv2.resize(im, (int(w * k), int(h * k)), interpolation=cv2.INTER_AREA)
    G.write_rgb(dst, im)


def crop_ref(img, stem, cranium):
    """The cropper, unchanged: subject matte x class labels, head removed, white."""
    M = P.masks(img, stem, cranium=cranium)
    x0, y0, x1, y1 = G.bbox_of((M["subject"] > 0.5).astype(np.uint8), img.shape[:2])
    return P.flatten(img[y0:y1, x0:x1], M["noface"][y0:y1, x0:x1], P.WHITE)


def main():
    label = sys.argv[sys.argv.index("--run") + 1] if "--run" in sys.argv else "b"
    select(label)
    dry = "--dry" in sys.argv
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))

    def want(stage):
        return only is None or stage in only

    rows = list(csv.DictReader(open(MATRIX)))
    garments = {}
    for r in rows:
        garments.setdefault(r["garment"], r)
    people = {r["person"]: r["person_path"] for r in rows}
    print(f"run {label}: {len(rows)} pairs, {len(garments)} references, "
          f"{len(people)} people -> {os.path.relpath(RUN, REPO)}")

    # --- norm -------------------------------------------------------------
    if want("norm"):
        for stem, path in people.items():
            norm(os.path.join(REPO, path), d("inputs", f"{stem}.jpg"))
        for g, r in garments.items():
            norm(os.path.join(REPO, r["garment_path"]), d("inputs", f"{g}.jpg"))
        print(f"norm   {len(people) + len(garments)} inputs at <= {MAXPIX/1e6:.2f} MP")

    # --- crop (free, proves the stack before anything is paid for) --------
    if want("crop"):
        for g, r in garments.items():
            out = d("refs", f"{g}__RAWCROP.jpg")
            if os.path.exists(out):
                continue
            img = cv2.imread(d("inputs", f"{g}.jpg"))
            G.write_rgb(out, crop_ref(img, f"v30_{g}", cranium=False))
            print(f"  crop  {g}")

    # --- bald (paid, worn references only) --------------------------------
    worn = [g for g, r in garments.items() if r.get("garment_kind", "worn") == "worn"]
    if want("bald"):
        need = [g for g in worn if not os.path.exists(d("refs", f"{g}__bald.jpg"))]
        print(f"bald   {len(need)} klein calls" + (" [dry]" if dry else ""))
        if need and not dry:
            res = F.run([(g, (lambda b=cv2.imread(d("inputs", f"{g}.jpg")):
                              F.make_bald("PRE2", b, seed=SEED))) for g in need], 4)
            for g, v in res.items():
                if v is None:
                    continue
                o = cv2.imread(d("inputs", f"{g}.jpg"))
                G.write_rgb(d("refs", f"{g}__bald.jpg"),
                            cv2.resize(v, (o.shape[1], o.shape[0]), interpolation=cv2.INTER_AREA))

    # --- bcref (free) -----------------------------------------------------
    if want("bcref"):
        for g in garments:
            out = d("refs", f"{g}__BC.jpg")
            if os.path.exists(out):
                continue
            bald = d("refs", f"{g}__bald.jpg")
            if g in worn and not os.path.exists(bald):
                print(f"  skip  {g} (no bald frame)")
                continue
            src = bald if os.path.exists(bald) else d("inputs", f"{g}.jpg")
            G.write_rgb(out, crop_ref(cv2.imread(src), f"v30_{g}__BC",
                                      cranium=os.path.exists(bald)))
            print(f"  bcref {g}")

    # --- qxref (paid) -----------------------------------------------------
    if want("qxref"):
        need = [g for g in garments if not os.path.exists(d("refs", f"{g}__QX.jpg"))]
        print(f"qxref  {len(need)} qwen calls" + (" [dry]" if dry else ""))
        if need and not dry:
            res = F.run([(g, (lambda b=cv2.imread(d("inputs", f"{g}.jpg")): F.call(
                QWEN, {"image_urls": [F._b64(b)], "prompt": QX_PROMPT, "seed": SEED})))
                for g in need], 4)
            for g, v in res.items():
                if v is not None:
                    G.write_rgb(d("refs", f"{g}__QX.jpg"), v)

    # --- shape (paid) — extract one named shape over every reference -----
    if want("shape"):
        tag = sys.argv[sys.argv.index("--shape") + 1]
        if tag not in EXTRACT:
            raise SystemExit(f"unknown shape {tag}; have {sorted(EXTRACT)}")
        need = [g for g in garments if not os.path.exists(d("refs", f"{g}__{tag}.jpg"))]
        print(f"shape  {tag}: {len(need)} qwen calls" + (" [dry]" if dry else ""))
        if need and not dry:
            res = F.run([(g, (lambda b=d("inputs", f"{g}.jpg"): F.call(
                QWEN, {"image_urls": [F._b64(cv2.imread(b))],
                       "prompt": EXTRACT[tag], "seed": SEED}))) for g in need], 6)
            for g, v in res.items():
                if v is not None:
                    G.write_rgb(d("refs", f"{g}__{tag}.jpg"), v)

    # --- arm (paid) — klein edit against one named shape ------------------
    if want("arm"):
        tag = sys.argv[sys.argv.index("--arm") + 1]
        jobs = []
        for r in rows:
            out = d("gen", f"{r['set_id']}__{tag}.jpg")
            ref = d("refs", f"{r['garment']}__{tag}.jpg")
            if os.path.exists(out) or not os.path.exists(ref):
                continue
            jobs.append((f"{r['set_id']}|{tag}", (
                lambda p=d("inputs", f"{r['person']}.jpg"), rp=ref: F.call(
                    KLEIN, {"image_urls": [F._b64(cv2.imread(p)), F._b64(cv2.imread(rp))],
                            "prompt": PROMPT, "seed": SEED}))))
        print(f"arm    {tag}: {len(jobs)} klein calls (~${len(jobs) * 0.015:.2f})"
              + (" [dry]" if dry else ""))
        if jobs and not dry:
            res = F.run(jobs, 6)
            for k, v in res.items():
                if v is not None:
                    G.write_rgb(d("gen", f"{k.split('|')[0]}__{tag}.jpg"), v)

    # --- ph / ph2 (paid) — v3.2: PHEAD, klein run twice ------------------
    # PHEAD is the cropper on the raw reference with no bald pass: one call. V3
    # allows two, so the second is spent re-running the same edit on its own
    # output. Reference, prompt and seed are identical in both passes; the only
    # thing that changes between pass 1 and pass 2 is image 1.
    def klein_pass(tag, person_of):
        jobs = []
        for r in rows:
            out = d("gen", f"{r['set_id']}__{tag}.jpg")
            ref = d("refs", f"{r['garment']}__RAWCROP.jpg")
            src = person_of(r)
            if os.path.exists(out) or not os.path.exists(ref) or not os.path.exists(src):
                continue
            jobs.append((f"{r['set_id']}|{tag}", (
                lambda p=src, rp=ref: F.call(
                    KLEIN, {"image_urls": [F._b64(cv2.imread(p)), F._b64(cv2.imread(rp))],
                            "prompt": PROMPT, "seed": SEED}))))
        print(f"{tag.lower():6s} {len(jobs)} klein calls (~${len(jobs) * 0.015:.2f})"
              + (" [dry]" if dry else ""))
        if jobs and not dry:
            res = F.run(jobs, 6)
            for k, v in res.items():
                if v is not None:
                    G.write_rgb(d("gen", f"{k.split('|')[0]}__{tag}.jpg"), v)

    if want("ph"):
        klein_pass("PH", lambda r: d("inputs", f"{r['person']}.jpg"))
    if want("ph2"):
        klein_pass("PH2", lambda r: d("gen", f"{r['set_id']}__PH.jpg"))

    # --- qvar (paid) — the other two extraction shapes -------------------
    if want("qvar"):
        jobs = []
        for tag in ("QF", "QM", "QFA", "QMA"):
            for g in garments:
                if os.path.exists(d("refs", f"{g}__{tag}.jpg")):
                    continue
                jobs.append((f"{g}|{tag}", (
                    lambda b=d("inputs", f"{g}.jpg"), t=tag: F.call(
                        QWEN, {"image_urls": [F._b64(cv2.imread(b))],
                               "prompt": EXTRACT[t], "seed": SEED}))))
        print(f"qvar   {len(jobs)} qwen calls" + (" [dry]" if dry else ""))
        if jobs and not dry:
            res = F.run(jobs, 6)
            for k, v in res.items():
                if v is not None:
                    g, t = k.split("|")
                    G.write_rgb(d("refs", f"{g}__{t}.jpg"), v)

    # --- qqedit (paid) — v3.1 -------------------------------------------
    # Same reference QX uses, different edit model. One variable between them.
    if want("qqedit"):
        jobs = []
        for r in rows:
            out = d("gen", f"{r['set_id']}__QQ.jpg")
            ref = d("refs", f"{r['garment']}__QX.jpg")
            if os.path.exists(out) or not os.path.exists(ref):
                continue
            jobs.append((f"{r['set_id']}|QQ", (
                lambda p=d("inputs", f"{r['person']}.jpg"), rp=ref: F.call(
                    QWEN, {"image_urls": [F._b64(cv2.imread(p)), F._b64(cv2.imread(rp))],
                           "prompt": PROMPT, "seed": SEED}))))
        print(f"qqedit {len(jobs)} qwen calls" + (" [dry]" if dry else ""))
        if jobs and not dry:
            res = F.run(jobs, 6)
            for k, v in res.items():
                if v is not None:
                    G.write_rgb(d("gen", f"{k.split('|')[0]}__QQ.jpg"), v)

    # --- edit (paid) ------------------------------------------------------
    if want("edit"):
        jobs = []
        for r in rows:
            for arm in ("BC", "QX"):
                out = d("gen", f"{r['set_id']}__{arm}.jpg")
                ref = d("refs", f"{r['garment']}__{arm}.jpg")
                if os.path.exists(out) or not os.path.exists(ref):
                    continue
                jobs.append((f"{r['set_id']}|{arm}", (
                    lambda p=d("inputs", f"{r['person']}.jpg"), rp=ref: F.call(
                        KLEIN, {"image_urls": [F._b64(cv2.imread(p)), F._b64(cv2.imread(rp))],
                                "prompt": PROMPT, "seed": SEED}))))
        print(f"edit   {len(jobs)} klein calls (~${len(jobs) * 0.015:.2f})"
              + (" [dry]" if dry else ""))
        if jobs and not dry:
            res = F.run(jobs, 6)
            for k, v in res.items():
                if v is None:
                    continue
                sid, arm = k.split("|")
                G.write_rgb(d("gen", f"{sid}__{arm}.jpg"), v)

    have = {}
    for r in rows:
        for arm in ("BC", "QX", "QQ", "QMB", "PH", "PH2"):
            f = d("gen", f"{r['set_id']}__{arm}.jpg")
            if os.path.exists(f):
                have[f"{r['set_id']}|{arm}"] = os.path.relpath(f, REPO)
    json.dump({"seed": SEED, "prompt": PROMPT, "qx_prompt": QX_PROMPT,
               "klein": KLEIN, "qwen": QWEN, "max_pixels": MAXPIX,
               "balded": sorted(g for g in worn if os.path.exists(d("refs", f"{g}__bald.jpg"))),
               "not_balded": sorted(g for g in garments if g not in worn),
               "outputs": have},
              open(d("_run.json"), "w"), indent=1)
    print(f"\n{len(have)} outputs on disk across {len({k.split('|')[1] for k in have})} arms")


if __name__ == "__main__":
    F._load_env()
    main()
