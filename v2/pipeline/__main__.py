"""Command line entry point.

    python -m pipeline person.jpg garment.jpg
    python -m pipeline person.jpg garment.jpg --high-resolution -o out.png
    python -m pipeline --route-only garment.jpg     # free, CPU, no generation

--route-only exists because it is the only part of the pipeline that costs nothing
and needs no API key, which makes it the first thing to check on a new machine.
"""
import argparse
import json
import shutil
import sys

from . import HarnessConfig, __version__, hair_over_garment, route, run


def _parser():
    p = argparse.ArgumentParser(
        prog="pipeline", description=f"V2 virtual try-on harness {__version__}")
    p.add_argument("person", nargs="?", help="path to the person photo")
    p.add_argument("garment", help="path to the garment reference")
    p.add_argument("-o", "--out", help="copy the result here")
    p.add_argument("--high-resolution", action="store_true",
                   help="run the realism pass (x2, ~$0.04, ~9s). Off by default")
    p.add_argument("--quality", choices=("safe", "cheap"), default="safe",
                   help="safe: 30/7/1 at 2.105 gen. cheap: 31/5/2 at 1.737 gen")
    p.add_argument("--garment-region", metavar="TEXT",
                   help='a named region ("just the jacket"). Routes to QX. Unmeasured')
    p.add_argument("--hair-threshold", type=float, default=None,
                   help="override the router cut-point (default 0.14; see LOCK.md)")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--route-only", action="store_true",
                   help="print the routing decision and exit. Free, CPU, no API key")
    p.add_argument("--json", action="store_true", help="machine-readable result")
    return p


def main(argv=None):
    a = _parser().parse_args(argv)
    cfg = HarnessConfig(high_resolution=a.high_resolution, quality=a.quality,
                        garment_region=a.garment_region)
    if a.hair_threshold is not None:
        cfg.hair_threshold = a.hair_threshold
    if a.seed is not None:
        cfg.seed = a.seed
    cfg.validate()

    if a.route_only:
        # `garment` is positional-last, so a lone path lands in it either way.
        arm, why, hair = route(a.garment, cfg)
        out = {"arm": arm, "reason": why, "hair_over_garment": hair,
               "generations": {"PHEAD": 1, "BC_klein": 2, "QX_qwen_p1": 2}[arm]}
        print(json.dumps(out, indent=2) if a.json else f"{arm}  ({why})")
        return 0

    if a.person is None:
        _parser().error("person and garment are both required unless --route-only")

    res = run(a.person, a.garment, cfg)
    if a.out:
        shutil.copyfile(res.image_path, a.out)
        res.image_path = a.out

    if a.json:
        print(json.dumps(res.__dict__, indent=2, default=str))
    else:
        for line in res.trace:
            print(f"  {line}")
        print(f"\n{res.arm}  {res.generations} generation(s)"
              f"{'  ESCALATED' if res.escalated else ''}")
        print(res.image_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
