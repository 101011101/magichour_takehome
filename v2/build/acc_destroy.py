# AC-C: destroy the head instead of removing it.
#
# Eight iterations went into head REMOVAL and each traded precision in one place for
# damage in another, because removal needs an exact boundary and an error leaves a
# white notch that gets read as garment (mechanism 1). Destruction needs only an
# approximate region: over-covering costs a little extra blurred skin, which carries
# no identity and no garment, and leaves the reference in distribution as a
# photograph rather than an image with a hole in it.
#
# Two bases. /O keeps the hair and destroys only the face -- no generative step, no
# licence question, milliseconds. It is C3.2 ("keep hair, remove face", measured at
# 45%) with the face destroyed IN PLACE rather than cut out, which removes C3.2's
# recorded failure -- "interpreted the white space as cloth" -- by construction.
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_crop as G          # noqa: E402
import phase3_variants as P       # noqa: E402

OUT = os.path.join(P.REPO, "v2", "runs", "acc")


def _region_box(mask, pad=0.10):
    ys, xs = np.where(mask > 0.5)
    if len(ys) < 20:
        return None
    h, w = mask.shape
    py, px = int((ys.max() - ys.min()) * pad), int((xs.max() - xs.min()) * pad)
    return (max(0, ys.min() - py), min(h, ys.max() + py),
            max(0, xs.min() - px), min(w, xs.max() + px))


def blur(bgr, mask, k=0.16, passes=1, pad=0.10):
    """D1. Radius scales with the REGION, not the image, so a small face in a wide
    frame is destroyed as thoroughly as a large one.

    `passes` matters more than radius past a point: repeated Gaussians compound
    (n passes at sigma is equivalent to one at sigma*sqrt(n)) and drive the region
    towards a flat blob far faster than widening a single kernel, which just grows
    the halo. The heavy tier uses both."""
    b = _region_box(mask, pad)
    if b is None:
        return bgr.copy()
    y0, y1, x0, x1 = b
    r = max(9, int(max(y1 - y0, x1 - x0) * k) | 1)
    reg = bgr[y0:y1, x0:x1]
    for _ in range(max(1, passes)):
        reg = cv2.GaussianBlur(reg, (r, r), 0)
    out = bgr.copy()
    out[y0:y1, x0:x1] = reg
    f = cv2.GaussianBlur(np.clip(mask, 0, 1), (0, 0), 6.0)[..., None]
    return (bgr * (1 - f) + out * f).astype(np.uint8)


def twirl(bgr, mask, strength=3.2):
    """D2. Angular displacement proportional to distance from the region centre,
    falling to zero at its edge so nothing outside the face moves. Destroys facial
    STRUCTURE rather than only detail -- the most out-of-distribution arm, and the
    likeliest to produce artefacts."""
    b = _region_box(mask, 0.02)
    if b is None:
        return bgr.copy()
    y0, y1, x0, x1 = b
    reg = bgr[y0:y1, x0:x1]
    h, w = reg.shape[:2]
    cy, cx = h / 2.0, w / 2.0
    R = max(min(h, w) / 2.0, 4.0)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dy, dx = yy - cy, xx - cx
    rad = np.sqrt(dy * dy + dx * dx)
    t = np.clip(1.0 - rad / R, 0, 1) ** 2          # zero at the rim, max at centre
    ang = np.arctan2(dy, dx) + strength * t
    mapx = (cx + rad * np.cos(ang)).astype(np.float32)
    mapy = (cy + rad * np.sin(ang)).astype(np.float32)
    out = bgr.copy()
    out[y0:y1, x0:x1] = cv2.remap(reg, mapx, mapy, cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_REFLECT)
    f = cv2.GaussianBlur(np.clip(mask, 0, 1), (0, 0), 4.0)[..., None]
    return (bgr * (1 - f) + out * f).astype(np.uint8)


def pixelate(bgr, mask, cells=6):
    """D3. Mosaic at `cells` blocks across the region. Coarser than blur at
    destroying identity, and unlike blur it cannot be mistaken for depth of field --
    which is either the point or the problem, and the review decides which."""
    b = _region_box(mask)
    if b is None:
        return bgr.copy()
    y0, y1, x0, x1 = b
    reg = bgr[y0:y1, x0:x1]
    h, w = reg.shape[:2]
    small = cv2.resize(reg, (max(2, w // max(1, w // cells)), max(2, h // max(1, h // cells))),
                       interpolation=cv2.INTER_AREA)
    out = bgr.copy()
    out[y0:y1, x0:x1] = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    f = (np.clip(mask, 0, 1) > 0.5).astype(np.float32)[..., None]
    return (bgr * (1 - f) + out * f).astype(np.uint8)


def open_head(head, subject, nose):
    """D4. Sever the neck at its own constriction instead of at a guessed line.

    Morphological opening removes a thin connection while leaving the bulk; the head
    then falls out as its own component. Only valid when a kernel exists BETWEEN
    neck width and head width, which is not guaranteed -- a seated profile has a
    narrow head and a thick neck, and p023 was flagged in advance as the worst case.
    Applicability is therefore checked per reference and reported rather than assumed:
    if no kernel separates the nose component from the bulk, the original mask is
    returned unchanged and the reference is marked as a fallback."""
    m = (head > 0.5).astype(np.uint8)
    if m.sum() < 100 or nose is None:
        return head, "no head mask"
    ny, nx = int(nose[1]), int(nose[0])
    h, w = m.shape
    if not (0 <= ny < h and 0 <= nx < w):
        return head, "nose outside frame"
    base_area = int(m.sum())
    for r in range(3, 41, 2):
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (r, r))
        op = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
        if op[ny, nx] == 0:
            continue                                   # eroded the head away
        n, lab = cv2.connectedComponents(op, 8)
        comp = (lab == lab[ny, nx])
        frac = comp.sum() / max(base_area, 1)
        if frac < 0.75:                                # something was severed
            grown = cv2.dilate(comp.astype(np.uint8), k) > 0
            grown = grown & (m > 0)                    # never grow past the original
            return (np.clip(cv2.GaussianBlur(grown.astype(np.float32), (0, 0), 2.0), 0, 1),
                    f"opened r={r}, kept {frac * 100:.0f}% of the blob")
    return head, "FALLBACK — no kernel separates head from body"
