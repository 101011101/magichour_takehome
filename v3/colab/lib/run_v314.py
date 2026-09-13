"""v3.14 - can any of the four small models be consolidated?

Two candidates, measured on images that already exist. Neither involves klein unless a
candidate moves a reference far enough that the difference has to be seen rather than
argued, which is what `generate` is for.

  A  drop Selfie Multiclass, keep the SCHP parser
     Today the parser supersedes the selfie map for head/garment/skin when it fires, and
     the selfie map survives as three things: the HAIR+FACE union into the head mask, the
     CLOTHES collar guard inside parser_classes, and the clothes_prob both fallbacks take.
     So "drop the segmenter" is not one edit - it also strands the fallback chain.

  B  take the waist from the parser instead of Pose
     ATR labels upper-clothes, dress, skirt, trousers and legs separately, so the boundary
     between the upper garment and the lower one is a waist the garment itself defines.

The acceptance criterion is Runbo's, not a cost one: quality must not drop, fewer BRANCHES
beats fewer models, and a route that fires on 3% of garments is a rarely-exercised path and
therefore where an unnoticed bug will live. A candidate that removes a model and keeps every
branch buys little. "Keep what we have" is a permitted answer.
"""
import json
import os

import cv2
import numpy as np

import garment_crop as G
import phase3_variants as P

# ATR, the 18 classes the parser emits
UPPER = (4, 7, 17)            # upper-clothes, dress, scarf
LOWER = (5, 6, 12, 13, 9, 10)  # skirt, trousers, legs, shoes
BELT = (8,)
MIN_CLASS_PX = 400


def parse_map(bgr):
    return P.parse_human(bgr)


def waist_from_parser(seg, min_px=MIN_CLASS_PX):
    """A waist row from the garment's own labelling, or None with the reason.

    A belt is the waist when the parser finds one. Otherwise the row between the bottom of
    the upper garment and the top of the lower one. A DRESS has neither - one class covers
    the whole body - and that is the case this cannot answer.
    """
    if seg is None:
        return None, "parser unavailable"
    h = seg.shape[0]
    up, lo, be = np.isin(seg, UPPER), np.isin(seg, LOWER), np.isin(seg, BELT)
    if be.sum() >= min_px:
        return float(np.mean(np.where(be)[0])) / h, "belt"
    if up.sum() < min_px:
        return None, f"no upper garment ({int(up.sum())} px)"
    if lo.sum() < min_px:
        return None, f"no lower garment ({int(lo.sum())} px) - a dress or coat has no waist"
    return float((np.percentile(np.where(up)[0], 95)
                  + np.percentile(np.where(lo)[0], 5)) / 2) / h, "boundary"


def hip_from_pose(bgr, vis=0.5, margin=0.02):
    import mediapipe as mp
    lm = P._pose()
    if lm is None:
        return None, "pose unavailable"
    r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                           data=np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))))
    if not r.pose_landmarks:
        return None, "no pose"
    p = r.pose_landmarks[0]
    ok = [i for i in (23, 24)
          if p[i].visibility >= vis and -margin <= p[i].x <= 1 + margin
          and -margin <= p[i].y <= 1 + margin]
    if not ok:
        return None, "no in-frame hip"
    return float(sum(p[i].y for i in ok) / len(ok)), "hips"


def references(bgr, stem):
    """The reference as built today, and as candidate A would build it. Returns None when
    the parser does not fire, because then the two are not comparable - today falls to the
    pose ellipse and candidate A has nothing to fall to, which is the finding, not an error."""
    import mediapipe as mp
    h, w = bgr.shape[:2]
    prob, _ = G.biref_matte(bgr, stem, False)
    subject = G.drop_specks(prob)
    seg = G._multiclass()
    if seg is None:
        return None
    res = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB,
                               data=np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))))
    p = np.stack([cv2.resize(m.numpy_view(), (w, h), interpolation=cv2.INTER_LINEAR)
                  for m in res.confidence_masks])
    band = max(3, 0.010 * min(h, w))
    head_selfie = G.refine_band(bgr, p[G.HAIR] + p[G.FACE], band)
    today = P.parser_classes(bgr, subject, clothes=p[G.CLOTHES])
    only = P.parser_classes(bgr, subject, clothes=None)
    if today is None or only is None:
        return None
    head_today = np.clip(np.maximum(head_selfie, today["head"]), 0, 1)
    head_only = np.clip(only["head"], 0, 1)
    x0, y0, x1, y1 = G.bbox_of((subject > 0.5).astype(np.uint8), bgr.shape[:2])

    def flat(head):
        nf = G.drop_specks(subject * (1.0 - head))
        return P.flatten(bgr[y0:y1, x0:x1], nf[y0:y1, x0:x1], P.WHITE)

    return {"today": flat(head_today), "parser_only": flat(head_only),
            "head_px_today": int((head_today > 0.5).sum()),
            "head_px_only": int((head_only > 0.5).sum())}


def compare(a, b):
    if a.shape != b.shape:
        return {"shape_today": list(a.shape[:2]), "shape_only": list(b.shape[:2])}
    d = np.abs(a.astype(np.float32) - b.astype(np.float32))
    return {"mad": round(float(d.mean()), 3), "max": int(d.max()),
            "changed_pct": round(float((d.max(axis=2) > 8).mean()) * 100, 3)}


def d(out, *parts):
    q = os.path.join(out, *parts)
    os.makedirs(os.path.dirname(q), exist_ok=True)
    return q


def main(worn, product, out="run", generate=0):
    """worn/product: {stem: path}. Writes run/{refs,meta} and returns the record."""
    rec = {"A": {}, "B": {}, "routes": {}}
    for stem, path in sorted(worn.items()):
        bgr = cv2.imread(path)
        if bgr is None:
            continue
        r = references(bgr, f"v314_{stem}")
        if r is None:
            rec["A"][stem] = {"skipped": "parser did not fire - not comparable"}
        else:
            cv2.imwrite(d(out, "refs", f"{stem}__today.jpg"), r["today"],
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            cv2.imwrite(d(out, "refs", f"{stem}__parser_only.jpg"), r["parser_only"],
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            rec["A"][stem] = dict(compare(r["today"], r["parser_only"]),
                                  head_px_today=r["head_px_today"],
                                  head_px_only=r["head_px_only"])
        seg = parse_map(bgr)
        wf, why = waist_from_parser(seg)
        hf, hwhy = hip_from_pose(bgr)
        rec["B"][stem] = {"kind": "worn", "waist": wf, "waist_why": why,
                          "hip": hf, "hip_why": hwhy,
                          "diff": None if (wf is None or hf is None) else round(abs(wf - hf), 4)}
    for stem, path in sorted(product.items()):
        bgr = cv2.imread(path)
        if bgr is None:
            continue
        seg = parse_map(bgr)
        wf, why = waist_from_parser(seg)
        hf, hwhy = hip_from_pose(bgr)
        rec["B"][stem] = {"kind": "product", "waist": wf, "waist_why": why,
                          "hip": hf, "hip_why": hwhy,
                          "diff": None if (wf is None or hf is None) else round(abs(wf - hf), 4)}
    json.dump(rec, open(d(out, "meta", "v314_meta.json"), "w"), indent=1)
    return rec
