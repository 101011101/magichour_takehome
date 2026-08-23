"""Stage 3 -- the three arms.

They are pipelines, not models. All three end in the same klein call; each arm's
whole contribution is WHICH garment reference it hands over.

    PHEAD     1 gen   parser head-removal, no generative preprocessing
    BC_klein  2 gen   klein makes the reference person bald, then the same crop
    QX        2 gen   Qwen-Image-Edit-2511 returns only the clothing

PHEAD and BC_klein both SUBTRACT; QX REGENERATES. That single fact is why BC_klein
is reached by the router rather than by escalation -- it shares PHEAD's failure mode,
rescuing only 6 of PHEAD's 13 hard cases against QX's 11 -- and why escalation always
lands on QX.

    arm       perfect  ok  fail
    PHEAD          23   5    10
    BC_klein       28   6     4      highest ceiling
    QX             20  17     1      lowest floor -- the safety net

References are read from disk WHEN THEY EXIST, because those are what every
measured number came from -- a rebuilt PHEAD crop comes out 1347x475 against the
stored 1194x467, and a reference that differs from the one the numbers came from is
a different experiment. For a garment with no stored reference -- which is every
real upload -- build_reference() constructs one. That is the production path.
"""
import os
import tempfile
import urllib.request

from ._research import REPO, ensure

ensure()

PROMPT = ("Dress the person in image 1 in the clothing shown in image 2. Keep the "
          "person's face, identity, body and the background exactly as they are.")

REF = {
    "PHEAD":      ("v2/runs/amt",  "{src}__PHEAD.jpg"),
    "BC_klein":   ("v2/runs/amt",  "{src}__BC_klein.jpg"),
    "QX_qwen_p1": ("v2/runs/acab", "{src}__QX_qwen_p1.jpg"),
}


def reference(arm, garment_stem):
    """Path to this arm's garment reference, or None if it has not been built."""
    d, pat = REF[arm]
    p = os.path.join(REPO, d, pat.format(src=garment_stem))
    return p if os.path.exists(p) else None


def build_reference(arm, garment_path, cfg, out_dir=None):
    """Build this arm's garment reference from a RAW image. The production path.

    Each arm differs only in what it hands klein:

        PHEAD     mask arithmetic alone -- free, CPU, no generative call
        BC_klein  klein makes the person bald first, then the SAME crop. Cropping a
                  bald frame removes less garment, because there is less hair to cut
        QX        Qwen-Image-Edit returns the clothing with the person removed

    Returns a path. Raises rather than returning a degraded reference: a silently
    wrong crop is worse than a failed request, and the router's own feature already
    taught that lesson by returning 0.0 instead of failing.
    """
    import cv2
    import numpy as np
    import tempfile
    import phase3_variants as PV
    import garment_crop as GC

    out_dir = out_dir or tempfile.mkdtemp(prefix="ref_")
    stem = os.path.splitext(os.path.basename(garment_path))[0]
    dst = os.path.join(out_dir, f"{stem}__{arm}.jpg")

    if arm == "QX_qwen_p1":
        img = _extract_garment(garment_path, cfg)
        cv2.imwrite(dst, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return dst

    raw = cv2.imread(garment_path)
    if raw is None:
        raise ValueError(f"unreadable garment image: {garment_path}")
    if arm == "BC_klein":
        raw = _make_bald(raw, cfg)          # generation 1 of 2
        stem = stem + "__bald"

    M = PV.masks(raw, stem, cranium=True)
    x0, y0, x1, y1 = GC.bbox_of((M["subject"] > 0.5).astype(np.uint8), raw.shape[:2])
    crop = PV.flatten(raw[y0:y1, x0:x1], M["noface"][y0:y1, x0:x1], PV.WHITE)
    cv2.imwrite(dst, crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return dst


BALD_PROMPT = ("Make this person completely bald. Remove all hair from the head, "
               "any hair falling over the shoulders, chest or back, and show the "
               "clothing that was underneath it. Keep the clothing, the pose, the "
               "body and the background exactly as they are \u2014 change nothing "
               "except the hair.")

QX_PROMPT = ("Return only the clothing from this photo, isolated on a plain white "
             "background. Remove the person entirely - no face, no skin, no hair, "
             "no body.")


def _fal_image(endpoint, args):
    import tempfile
    import urllib.request
    import cv2
    import fal_client
    res = fal_client.subscribe(endpoint, arguments=args)
    url = ((res.get("images") or [{}])[0].get("url")
           or (res.get("image") or {}).get("url"))
    if not url:
        raise RuntimeError(f"{endpoint} returned no image: {list(res)}")
    tmp = tempfile.mktemp(suffix=".jpg")
    urllib.request.urlretrieve(url, tmp)
    return cv2.imread(tmp)


def _make_bald(raw_bgr, cfg):
    """Hairless RAW frame. The unchanged cropper runs on it afterwards, so the only
    variable is the image the cropper receives."""
    import cv2
    import tempfile
    import fal_client
    p = tempfile.mktemp(suffix=".jpg")
    cv2.imwrite(p, raw_bgr)
    out = _fal_image(cfg.editor, {"image_urls": [fal_client.upload_file(p)],
                                  "prompt": BALD_PROMPT, "seed": cfg.seed})
    # match the original dimensions so the crop geometry is unchanged
    return cv2.resize(out, (raw_bgr.shape[1], raw_bgr.shape[0]),
                      interpolation=cv2.INTER_AREA)


def _extract_garment(garment_path, cfg):
    import fal_client
    return _fal_image(cfg.extractor,
                      {"image_urls": [fal_client.upload_file(garment_path)],
                       "prompt": QX_PROMPT, "seed": cfg.seed})


def generate(arm, person_path, garment_path, cfg):
    """One arm, end to end. Returns a path to the generated frame.

    The klein call is identical for all three arms. Preprocessing that needed a
    generative step -- BC_klein's bald pass, QX's extraction -- is already baked into
    the stored reference, which is why GENERATIONS counts 2 for those two.
    """
    import fal_client

    stem = os.path.splitext(os.path.basename(garment_path))[0]
    ref = reference(arm, stem)
    if ref is None:
        # No stored reference: an unseen garment, i.e. every real upload.
        ref = build_reference(arm, garment_path, cfg)

    res = fal_client.subscribe(cfg.editor, arguments={
        "image_urls": [fal_client.upload_file(person_path),
                       fal_client.upload_file(ref)],
        "prompt": PROMPT, "seed": cfg.seed})
    url = ((res.get("images") or [{}])[0].get("url")
           or (res.get("image") or {}).get("url"))
    if not url:
        raise RuntimeError(f"{cfg.editor} returned no image: {list(res)}")
    dst = tempfile.mktemp(suffix=f"__{arm}.jpg")
    urllib.request.urlretrieve(url, dst)
    return dst
