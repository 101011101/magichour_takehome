"""Deterministic checks. Thin adapters over v2/build/failure_gate.py, which is the
module those checks were measured in -- reimplementing them here would let the two
drift apart silently."""
import os
import sys

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "build"))
import failure_gate as _fg  # noqa: E402


def degenerate(path, floor=0.15):
    """Blank, constant or blurred-out frame."""
    img = cv2.imread(path)
    if img is None:
        return True
    return _fg.check_degenerate(img)[0] < floor


def identity_margin(out_path, person_path):
    """failure_gate.check_identity's NORMALISED margin, in [0,1].

    Not the raw cosine. check_identity returns _norm(cos, 0.18, 0.42), so a raw
    cosine of 0.88 between the same person maps to 1.000 and 0.36 maps to 0.755.
    Every threshold in the documents is on this scale, because this is the function
    the analysis used. upscale.identity_cos returns the RAW cosine and is calibrated
    separately for the realism floor -- do not interchange them.
    """
    a, b = cv2.imread(out_path), cv2.imread(person_path)
    if a is None or b is None:
        return None
    return float(_fg.check_identity(a, b)[0])


def noop(out_path, person_path):
    """1.0 = the output differs from the person input; near 0 = nothing changed."""
    a, b = cv2.imread(out_path), cv2.imread(person_path)
    if a is None or b is None:
        return 1.0
    return float(_fg.check_noop(a, b)[0])
