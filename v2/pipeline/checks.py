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


def noop(out_path, person_path):
    """1.0 = the output differs from the person input; near 0 = nothing changed."""
    a, b = cv2.imread(out_path), cv2.imread(person_path)
    if a is None or b is None:
        return 1.0
    return float(_fg.check_noop(a, b)[0])
