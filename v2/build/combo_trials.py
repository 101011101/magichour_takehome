# v2.2.1 phase 2b — person-to-person garment transfer, many combinations.
#
# Every image containing a person is both a possible BASE (who gets dressed) and
# a possible SOURCE (whose outfit is taken). Product-only flat-lays are excluded
# entirely: this workstream is about garment+human references, which is the case
# klein is weakest on and the case cropping was built for.
#
# Image 1 = the base person, uncropped.
# Image 2 = the source person's CROP, so their face and background cannot leak.
#
# Sampling is by random derangement rounds: each round pairs all N people so that
# everyone appears exactly once as base and once as source, and nobody is paired
# with themselves. Coverage is therefore even by construction rather than by luck,
# and the seed makes it reproducible.
import argparse, io, json, os, random, sys, threading
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# keys from the repo .env, as the other harnesses do at import time
for _l in (open(os.path.join(REPO, ".env")) if
           os.path.exists(os.path.join(REPO, ".env")) else []):
    _l = _l.strip()
    if _l and not _l.startswith("#") and "=" in _l:
        _k, _, _v = _l.partition("=")
        os.environ.setdefault(_k.strip(), _v.strip())

CROPS = os.path.join(REPO, "v2", "runs", "crop_screen")
TS2_IN = os.path.join(REPO, "v2", "runs", "ts2", "inputs")
PEOPLE = os.path.join(REPO, "test_set", "people")
OUT = os.path.join(REPO, "v2", "runs", "combo")
ENDPOINT = "fal-ai/flux-2/klein/4b/distilled/edit"
EST_USD = 0.015
SEED = 46
CROP_SUFFIX = "c32_no_face_keep_hair"   # C3.2: face removed, hair kept

PROMPT = ("Take the complete outfit worn by the person in image 2 and put it on "
          "the person in image 1. Keep the person in image 1 — their face, hair, "
          "body, pose — and the background completely unchanged. Do not copy the "
          "face, body or background of image 2. Preserve the exact colour, "
          "pattern, and cut of the garments.")

_lock = threading.Lock()
_spent = [0.0]
BASE_MODE = [False]   # True = send the source's uncropped photo (the control)
VARIANT = ["c32_no_face_keep_hair"]   # which crop suffix to send as image 2
SUBSET = [None]       # optional [(base, source), ...] to restrict the run


def pool():
    """Every person image that has a crop. Product flat-lays are excluded by the
    clothesonly_ prefix — they contain no person, so they cannot be a base."""
    out = []
    for f in sorted(os.listdir(CROPS)):
        if not f.endswith(f"__{CROP_SUFFIX}.jpg"):
            continue
        stem = f.split("__")[0]
        if stem.startswith("clothesonly_"):
            continue
        orig = (os.path.join(PEOPLE, f"{stem}.jpg") if stem.startswith("p")
                else os.path.join(TS2_IN, f"{stem}.jpg"))
        if os.path.exists(orig):
            out.append({"stem": stem, "orig": orig,
                        "crop": os.path.join(CROPS, f)})
    return out


def derangement(n, rng):
    """A permutation with no fixed point, so nobody wears their own clothes."""
    while True:
        p = list(range(n))
        rng.shuffle(p)
        if all(i != p[i] for i in range(n)):
            return p


def combos(people, rounds, rng):
    out = []
    for r in range(rounds):
        for i, j in enumerate(derangement(len(people), rng)):
            out.append((people[i], people[j], r))
    return out


def run(rounds, workers, budget):
    import fal_client, requests
    os.makedirs(OUT, exist_ok=True)
    people = pool()
    rng = random.Random(SEED)
    tag = "__base" if BASE_MODE[0] else ("" if VARIANT[0] == CROP_SUFFIX
                                        else "__" + VARIANT[0])
    allc = combos(people, rounds, rng)
    if SUBSET[0]:
        keep = set(SUBSET[0])
        allc = [c for c in allc if (c[0]["stem"], c[1]["stem"]) in keep]
    seen, uniq = set(), []
    for c in allc:                       # rounds can repeat a pairing
        k = (c[0]["stem"], c[1]["stem"])
        if k not in seen:
            seen.add(k); uniq.append(c)
    jobs = [(b, s, r) for b, s, r in uniq
            if not os.path.exists(os.path.join(
                OUT, f"{b['stem']}__wears__{s['stem']}{tag}.png"))]
    est = len(jobs) * EST_USD
    print(f"{len(people)} people, {rounds} rounds -> {len(jobs)} combinations, est ${est:.2f}")
    if est > budget:
        sys.exit(f"estimate ${est:.2f} over the ${budget:.2f} ceiling — lower --rounds")

    cache = {}
    def url(path):
        with _lock:
            if path not in cache:
                cache[path] = fal_client.upload_file(path)
        return cache[path]

    def one(job):
        b, s, rnd = job
        ref = (s["orig"] if BASE_MODE[0]
               else os.path.join(CROPS, f"{s['stem']}__{VARIANT[0]}.jpg"))
        tag = "__base" if BASE_MODE[0] else ("" if VARIANT[0] == CROP_SUFFIX
                                             else "__" + VARIANT[0])
        name = f"{b['stem']}__wears__{s['stem']}{tag}"
        try:
            args = {"prompt": PROMPT,
                    "image_urls": [url(b["orig"]), url(ref)],
                    "seed": SEED, "num_images": 1}
            res = fal_client.subscribe(ENDPOINT, arguments=args)
            u = (res.get("images") or [res.get("image", {})])[0]["url"]
            img = Image.open(io.BytesIO(requests.get(u).content)).convert("RGB")
        except Exception as e:
            print(f"  FAIL {name}: {str(e)[:110]}")
            return
        img.save(os.path.join(OUT, f"{name}.png"))
        json.dump({"base": b["stem"], "source": s["stem"], "round": rnd,
                   "crop_variant": ("none (uncropped)" if BASE_MODE[0] else CROP_SUFFIX),
                   "uncropped": BASE_MODE[0],
                   "endpoint": ENDPOINT, "seed": SEED,
                   "base_img": os.path.relpath(b["orig"], REPO),
                   "source_crop": os.path.relpath(s["crop"], REPO),
                   "source_ref_used": os.path.relpath(ref, REPO),
                   "size": img.size},
                  open(os.path.join(OUT, f"{name}.json"), "w"), indent=2)
        with _lock:
            _spent[0] += EST_USD
        print(f"  ok {b['stem']:>34s} wears {s['stem']}")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, jobs))
    print(f"done — est ${_spent[0]:.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=2,
                    help="each round = one combination per person as base and as source")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--budget", type=float, default=3.00)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--variant", default="c32_no_face_keep_hair")
    ap.add_argument("--subset", default=None,
                    help="file of base|source lines to restrict the run")
    ap.add_argument("--base", action="store_true",
                    help="control arm: uncropped source photo as image 2")
    a = ap.parse_args()
    BASE_MODE[0] = a.base
    VARIANT[0] = a.variant
    if a.subset:
        SUBSET[0] = [tuple(l.strip().split("|")) for l in open(a.subset) if l.strip()]
    if a.dry:
        ppl = pool()
        rng = random.Random(SEED)
        cs = combos(ppl, a.rounds, rng)
        print(f"{len(ppl)} people -> {len(cs)} combinations, est ${len(cs)*EST_USD:.2f}")
        for b, s, r in cs[:6]:
            print(f"  {b['stem']} wears {s['stem']}")
    else:
        run(a.rounds, a.workers, a.budget)
