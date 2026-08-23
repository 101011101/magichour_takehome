"""V2 virtual try-on harness.

    from pipeline import HarnessConfig, run
    res = run("person.jpg", "garment.jpg")
    print(res.arm, res.generations, res.image_path)

V2 is FROZEN as of 2026-08-23. It is a checkpoint, not the direction of travel:
the harness logic is the thing worth keeping, and it is preserved here whole so it
can be read and re-measured. The next version simplifies to a single two-call path.
See prd/v2/LOCK.md.
"""
from .config import HarnessConfig
from .harness import run, route, hair_over_garment, Result

__version__ = "2.0.0"
__all__ = ["HarnessConfig", "run", "route", "hair_over_garment", "Result",
           "__version__"]
