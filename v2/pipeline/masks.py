"""Stage 1 -- the garment reference crops, and the routing feature derived from them.

Delegates to v2/build/garment_crop.py, which is where the crop was designed and
measured. That module writes to a fixed run directory and is driven by a CSV, so this
adapter is the seam where a production caller supplies an arbitrary path instead.

STATUS: `crop()` currently reads crops that garment_crop has already produced. Wiring
it to compute them on demand is a refactor of garment_crop.process(), which is
deliberately not done here -- that module is load-bearing for every result in the
project and every C1-C4 output must stay byte-identical.
"""
import glob
import os

import cv2

from ._research import REPO, ResearchUnavailable, ensure

ensure()
SCREEN = os.path.join(REPO, "v2", "runs", "crop_screen")

C31 = "__c3_no_face_alpha.png"          # hair AND face removed -- the shipped crop
C32 = "__c32_no_face_keep_hair_alpha.png"   # face only removed


def _stem(garment_path):
    s = os.path.splitext(os.path.basename(garment_path))[0]
    for cand in glob.glob(os.path.join(SCREEN, "*" + C31)):
        base = os.path.basename(cand)[:-len(C31)]
        if base == s or base.endswith(s) or s in base:
            return base
    return None


def crop(garment_path, keep_hair=False):
    """Path to the alpha PNG for this reference. None if it has not been produced."""
    st = _stem(garment_path)
    if st is None:
        return None
    p = os.path.join(SCREEN, st + (C32 if keep_hair else C31))
    return p if os.path.exists(p) else None


def hair_from_raw(garment_path):
    """Compute the router feature from a raw image, no prepared crop needed.

    Uses the repo's own mask stack so the number matches the stored one rather
    than approximating it. Costs a BiRefNet + SCHP + pose pass (~1.9s on CPU).

    RAISES rather than returning 0.0 on any failure. 0.0 is a valid feature value
    meaning "no hair over the garment", so returning it on an error silently routes
    every request to the cheap arm -- which is exactly what happened on the first
    self-hosted run, and it looked like a working system.
    """
    import numpy as np
    try:
        import phase3_variants as PV
    except ImportError as e:
        raise ResearchUnavailable("hair_over_garment") from e
    bgr = cv2.imread(garment_path)
    if bgr is None:
        raise ValueError(f"unreadable garment image: {garment_path}")
    stem = os.path.splitext(os.path.basename(garment_path))[0]
    M = PV.masks(bgr, stem, cranium=True)
    a31 = float((M["noface"] > 0.5).sum())        # hair AND face removed
    a32 = float((M["nofacehair"] > 0.5).sum())    # face only removed
    if not a32:
        raise ValueError(
            f"empty subject mask for {garment_path}: no person found in the "
            "garment reference, so there is no hair to measure")
    return max(0.0, (a32 - a31) / a32)


def area(alpha_path):
    """Opaque pixel count of an RGBA crop."""
    if not alpha_path:
        return 0
    a = cv2.imread(alpha_path, cv2.IMREAD_UNCHANGED)
    if a is None or a.ndim < 3 or a.shape[2] < 4:
        return 0
    return int((a[..., 3] > 127).sum())
