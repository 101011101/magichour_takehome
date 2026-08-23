"""The one seam between the shipped package and the research modules.

Three modules in ``v2/build/`` are load-bearing at runtime:

    failure_gate.py      the deterministic checks, as they were measured
    phase3_variants.py   the mask stack (BiRefNet, SCHP ATR, MediaPipe, pose)
    garment_crop.py      the crop geometry

They are imported rather than reimplemented on purpose. Every measured number in
prd/v2/ came out of those files; a second copy here would drift from them silently,
and a garment reference that differs from the one the numbers came from is a
different experiment.

They are flat top-level modules in a research directory rather than a package, so
they are reached by path. Centralised here so there is exactly one place to change
when they are vendored into company code -- which is the right move at that point,
and is deliberately not done here.

Install mode: ``pip install -e v2/``. An editable install leaves the files in place,
so this path resolves. A wheel would not carry ``build/`` -- see README.
"""
import os
import sys

BUILD = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "build"))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def ensure():
    """Idempotent. Returns the research directory."""
    if BUILD not in sys.path:
        sys.path.insert(0, BUILD)
    return BUILD


def available():
    """Are the research modules reachable? Lets callers degrade with a real message
    instead of an ImportError from three frames down."""
    ensure()
    return all(os.path.exists(os.path.join(BUILD, m + ".py"))
               for m in ("failure_gate", "phase3_variants", "garment_crop"))


class ResearchUnavailable(RuntimeError):
    """Raised instead of returning a plausible default.

    The router already taught this lesson once: hair_over_garment returned 0.0 when
    its masks were missing, which routed every request to the cheap arm and looked
    like a working system for a whole run.
    """
    def __init__(self, what):
        super().__init__(
            f"{what} needs the research modules in {BUILD}, which are not importable. "
            "Install with `pip install -e v2/` from the repo root.")


ensure()
