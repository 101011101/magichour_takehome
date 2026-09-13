"""Did the re-pose actually happen? A landmark read, not an opinion.

For every pair the arm was run on, four images are posed with the same MediaPipe detector
the pipeline already uses (`v3lib._poser`, pose_landmarker_lite):

    the garment photo          where the wearer started
    the target person          where the arm was asked to move them to
    {sid}__BCp_raw.jpg         what call 1 returned, wording 1
    {sid}__BCp2_raw.jpg        what call 1 returned, wording 2

Landmarks are made comparable the usual way - translate to the mid-hip, scale by the
shoulder-to-hip length - and compared only over the landmarks confidently visible in ALL
FOUR, so a waist-up target cannot flatter or punish a full-body source. The number reported
per arm is

    shift = d(out, source) / (d(out, source) + d(out, target))

0 means the output is still exactly the source pose, 1 means it reached the target's, 0.5
means it sits halfway.

**`shift` alone is a trap, and this is the reason the page shows images beside it.** The
loudest failure of the arm is that klein takes image 2 as the BASE - it returns the target's
own photograph, background and all, with the garment swapped in and the head balded. That is
a total failure of the arm, and it scores `shift` near 1, because the output really is in the
target's pose: it IS the target's photo. So `base` is recorded too - which of the two inputs
the output resembles globally, by mean absolute difference of a 128x128 grey thumbnail. A
high `shift` with `base = target` is the collapse, not a re-pose; a high `shift` with
`base = source` is the thing the arm was built to do.

`px_changed` is the third number and the plainest: the fraction of pixels differing from
the garment photo by more than 25 levels. It separates the two failure classes at a glance
where the pose metrics cannot - a call that only removed hair changes a few percent, a call
that collapsed changes almost everything - and it needs no landmarks, so it is defined on
every pair including the ones no detector reads.

`shift` is only meaningful when the two poses are far enough apart to tell apart, so
`d_src_tgt` - the distance between the source pose and the target pose over the same kept
landmarks - is recorded beside it. Where that is small the pair cannot discriminate and the
ratio is noise: a pair is counted as SEPARABLE only above `SEP`, and the headline is taken
over the separable pairs alone. Framing (full_body / knee_up / waist_up / chest_up) is read with
`v3lib.framing`, the classifier the v3.3 PERSON_CLAUSE is chosen by, and reported beside it:
a re-pose that worked has to bring the framing across too.

  python3 v3/build/v37_pose_metrics.py [run_dir]     default v3/runs/v37/run
"""
import csv
import json
import os
import sys

import cv2
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "v3", "colab", "lib"))
import v3lib as L  # noqa: E402

RUN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "v3", "runs", "v37", "run")
SET = os.path.join(REPO, "v3", "testsets", "v35_linkC.csv")
ARMS = ("BCp", "BCp2")
VIS = 0.5
SEP = 0.35   # min d(source,target) for the ratio to mean anything; below it the poses
             # are already alike and `shift` is dividing one small number by another


def pose(path, paths):
    """Normalised landmark array + a visibility mask, or None when nobody is detected."""
    im = cv2.imread(path)
    if im is None:
        return None
    res = L._poser(paths).detect(L._mp_image(im))
    if not res.pose_landmarks:
        return None
    lm = res.pose_landmarks[0]
    h, w = im.shape[:2]
    # pixel coordinates so the aspect ratio does not distort the shape
    xy = np.array([[l.x * w, l.y * h] for l in lm], np.float32)
    vis = np.array([l.visibility for l in lm], np.float32) >= VIS
    hip, sho = (xy[23] + xy[24]) / 2, (xy[11] + xy[12]) / 2
    scale = float(np.linalg.norm(sho - hip))
    if scale < 1e-3:
        return None
    return (xy - hip) / scale, vis


def thumb(path, side=128):
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if im is None:
        return None
    t = cv2.resize(im, (side, side), interpolation=cv2.INTER_AREA).astype(np.float32)
    return (t - t.mean()) / (t.std() + 1e-6)      # contrast-normalised, so exposure alone
                                                  # does not decide which input it matches


PX_TOL = 25        # levels; below this is JPEG and re-render noise, not a changed region


def px_changed(out_path, src_path, tol=PX_TOL):
    """Fraction of the garment photo's pixels the call actually moved. The output is
    resized to the source's shape first - klein returns its own canvas - so this measures
    content change, not a change of resolution."""
    a, b = cv2.imread(src_path), cv2.imread(out_path)
    if a is None or b is None:
        return None
    b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)
    return round(float((np.abs(a.astype(np.int16) - b.astype(np.int16)).max(2) > tol).mean()), 4)


def dist(a, b, keep):
    return float(np.linalg.norm(a[keep] - b[keep], axis=1).mean())


def main():
    paths = L.fetch_models(verbose=False)
    rows = list(csv.DictReader(open(SET)))
    out = {}
    for i, r in enumerate(rows, 1):
        sid, p, g = r["set_id"], r["person"], r["garment"]
        src = pose(os.path.join(RUN, "inputs", f"{g}.jpg"), paths)
        tgt = pose(os.path.join(RUN, "inputs", f"{p}.jpg"), paths)
        rec = {"framing": {}}
        for name, path in (("source", os.path.join(RUN, "inputs", f"{g}.jpg")),
                           ("target", os.path.join(RUN, "inputs", f"{p}.jpg"))):
            im = cv2.imread(path)
            rec["framing"][name] = L.framing(im, paths)["framing"] if im is not None else None
        ts = thumb(os.path.join(RUN, "inputs", f"{g}.jpg"))
        tt = thumb(os.path.join(RUN, "inputs", f"{p}.jpg"))
        for a in ARMS:
            rp = os.path.join(RUN, "refs", f"{sid}__{a}_raw.jpg")
            im = cv2.imread(rp)
            rec["framing"][a] = L.framing(im, paths)["framing"] if im is not None else None
            px = px_changed(rp, os.path.join(RUN, "inputs", f"{g}.jpg"))
            to = thumb(rp)
            base = None
            if to is not None and ts is not None and tt is not None:
                bs, bt = float(np.abs(to - ts).mean()), float(np.abs(to - tt).mean())
                base = {"d_thumb_source": round(bs, 3), "d_thumb_target": round(bt, 3),
                        "base": "source" if bs <= bt else "target"}
            base = {**(base or {}), "px_changed": px}
            got = pose(rp, paths)
            if not (src and tgt and got):
                rec[a] = dict(base or {}) or None
                continue
            keep = src[1] & tgt[1] & got[1]
            if keep.sum() < 8:
                rec[a] = {**(base or {}), "n_landmarks": int(keep.sum())}
                continue
            ds, dt = dist(got[0], src[0], keep), dist(got[0], tgt[0], keep)
            dst = dist(src[0], tgt[0], keep)
            rec[a] = {**(base or {}),
                      "d_source": round(ds, 3), "d_target": round(dt, 3),
                      "d_src_tgt": round(dst, 3), "separable": bool(dst >= SEP),
                      "shift": round(ds / (ds + dt), 3) if ds + dt else None,
                      "n_landmarks": int(keep.sum()),
                      "framing_reached": rec["framing"][a] == rec["framing"]["target"]}
        out[sid] = rec
        print(f"  {i}/{len(rows)} {sid[:56]} "
              + " ".join(f"{a}={(rec[a] or {}).get('shift')}" for a in ARMS), flush=True)
    os.makedirs(os.path.join(RUN, "meta"), exist_ok=True)
    json.dump({"note": "shift = d(out,source)/(d(out,source)+d(out,target)); 0 = unmoved, "
                       "1 = target's pose reached. Only pairs with d_src_tgt >= SEP can "
                       "discriminate; below that the two poses are already alike.",
               "vis": VIS, "sep": SEP, "px_tol": PX_TOL, "pairs": out},
              open(os.path.join(RUN, "meta", "pose_metrics.json"), "w"), indent=1)
    for a in ARMS:
        sep = [v[a] for v in out.values()
               if v.get(a) and v[a].get("shift") is not None and v[a].get("separable")]
        s = [x["shift"] for x in sep]
        f = [x["framing_reached"] for x in sep]
        n_all = len([v for v in out.values() if v.get(a) and v[a].get("shift") is not None])
        if s:
            # The three-way over EVERY measured pair, with no threshold in it: the ratio
            # needs separable poses, but "which input did the output come from" and "is it
            # nearer its own starting pose or the target's" do not, and restricting the
            # headline to the separable pairs hid how often the output collapses.
            allb = [v[a] for v in out.values() if v.get(a) and v[a].get("base")]
            coll = [x for x in allb if x["base"] == "target"]
            kept = [x for x in allb if x["base"] == "source"
                    and x.get("d_source") is not None and x["d_source"] <= x["d_target"]]
            rep = [x for x in allb if x["base"] == "source"
                   and x.get("d_source") is not None and x["d_source"] > x["d_target"]]
            pk = [x["px_changed"] for x in kept if x.get("px_changed") is not None]
            pc = [x["px_changed"] for x in coll if x.get("px_changed") is not None]
            print(f"{a}: {len(allb)} pairs · collapsed onto image 2 {len(coll)} · "
                  f"source pose kept {len(kept)} · re-posed toward the target {len(rep)}")
            if pk and pc:
                print(f"     median px_changed: source-pose-kept {np.median(pk):.1%} · "
                      f"collapsed {np.median(pc):.1%}")
            moved = [x for x in sep if x["shift"] > 0.5]
            real = [x for x in moved if x.get("base") == "source"]
            print(f"{a}: {len(s)}/{n_all} pairs separable (d_src_tgt >= {SEP}) · "
                  f"median shift {np.median(s):.2f} · "
                  f"{len(moved)}/{len(s)} closer to the target, of which "
                  f"{len(real)} are a real re-pose and {len(moved) - len(real)} are the "
                  f"output collapsing onto image 2 · "
                  f"collapsed overall {sum(x.get('base') == 'target' for x in sep)}/{len(s)} · "
                  f"framing reached {sum(f)}/{len(f)}")


if __name__ == "__main__":
    main()
