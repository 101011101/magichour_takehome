# Phase 3 paid arms: AC7.n generative repair, AC8.n generative crop, AC9 SeedVR2.
#
# Split from phase3_variants.py because these are the only arms that cost money and
# the only ones needing network. Everything here is gated: the free arms are looked
# at first, and this runs after.
#
# Two families, and the distinction matters when reading results:
#   AC7.n  REPAIR  -- takes the cropper's output plus a hole, returns it whole
#   AC8.n  CROP    -- takes the RAW photo, returns the garment. Never sees a crop,
#                     so it is the control on whether the deterministic stack earns
#                     its complexity. It can also hallucinate the garment, which the
#                     deterministic cropper physically cannot -- it only removes.
#
# Mask support is NOT uniform, and the doc previously got this wrong:
#   qwen-image-edit/inpaint   takes a real mask  -> true inpainting
#   z-image/turbo/inpaint     takes a real mask  -> true inpainting
#   klein .../edit            no mask            -> generate-then-composite
#   seedvr upscale            no mask, no prompt -> restore pass only
# Where there is no mask, originals are hard-composited back outside the hole:
# a full-frame latent round-trip otherwise degrades fabric the repair was never
# asked to touch.
import base64
import concurrent.futures as cf
import io
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v2", "runs", "phase3")


def _load_env():
    p = os.path.join(REPO, ".env")
    if not os.path.exists(p):
        return
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


REPAIR_PROMPT = ("Complete the missing section of the garment. Continue the existing "
                 "fabric pattern, colour and weave exactly. Do not add new design "
                 "elements, logos or trim.")
CROP_PROMPT = ("Return only the clothing from this photo, isolated on a plain white "
               "background. Remove the person entirely — no face, no skin, no hair, "
               "no background. Preserve the garment's exact colour, pattern and shape.")

# PRE2/PRE3. A deliberately SMALL, in-distribution edit: hair removal on a whole
# photograph is something these models do routinely, where "return a floating
# garment" asks for an out-of-distribution output. The clothing instruction is
# explicit because the only thing that matters here is what lies UNDER the hair.
BALD_PROMPT = ("Make this person completely bald. Remove all hair from the head and "
               "any hair falling over the shoulders, chest or back, and show the "
               "clothing that was underneath it. Keep the clothing, the pose, the "
               "body and the background exactly as they are — change nothing except "
               "the hair.")
PRE_ARMS = {
    "PRE2": "fal-ai/flux-2/klein/4b/distilled/edit",
    "PRE3": "fal-ai/qwen-image-edit-2511",
}


def make_bald(tag, raw, seed=46):
    """PRE2/PRE3 -- returns a hairless RAW frame. The unchanged cropper runs on it
    afterwards, so the only variable is the image the cropper receives."""
    ep = PRE_ARMS[tag]
    return call(ep, {"image_urls": [_b64(raw)], "prompt": BALD_PROMPT, "seed": seed})

# .1 / .2 / .3 per EXPERIMENT.md 2c
REPAIR_ARMS = {
    "AC7.1": ("fal-ai/flux-2/klein/4b/distilled/edit", "nomask"),
    "AC7.2": ("fal-ai/qwen-image-edit/inpaint", "mask"),
    "AC7.3": ("fal-ai/z-image/turbo/inpaint", "mask"),
}
CROP_ARMS = {
    "AC8.1": ("fal-ai/flux-2/klein/4b/distilled/edit", "nomask"),
    "AC8.2": ("fal-ai/qwen-image-edit-2511", "nomask"),
}


def _b64(bgr, gray=False):
    ok, buf = cv2.imencode(".png", bgr)
    if not ok:
        raise RuntimeError("encode failed")
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode()


def _fetch(url):
    import urllib.request
    with urllib.request.urlopen(url, timeout=180) as r:
        data = r.read()
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)


def call(endpoint, args):
    import fal_client
    r = fal_client.subscribe(endpoint, arguments=args, with_logs=False)
    imgs = r.get("images") or ([r["image"]] if r.get("image") else [])
    if not imgs:
        raise RuntimeError(f"no image in response: {str(r)[:160]}")
    return _fetch(imgs[0]["url"])


def repair(tag, crop, hole, seed=46):
    """AC7.n — the crop is already made; fill what the head cut removed."""
    ep, kind = REPAIR_ARMS[tag]
    dmg = np.where(hole[..., None] > 0, 255, crop).astype(np.uint8)
    if kind == "mask":
        # mask parameter names differ per endpoint: qwen wants mask_url,
        # z-image wants mask_image_url. Verified by smoke test, not assumed.
        mk = "mask_image_url" if "z-image" in ep else "mask_url"
        out = call(ep, {"image_url": _b64(dmg), mk: _b64((hole * 255)),
                        "prompt": REPAIR_PROMPT, "seed": seed})
    else:
        out = call(ep, {"image_urls": [_b64(dmg)], "prompt": REPAIR_PROMPT, "seed": seed})
    out = cv2.resize(out, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_CUBIC)
    # mandatory for the no-mask arms and harmless for the others
    return np.where(hole[..., None] > 0, out, crop)


def crop_e2e(tag, raw, seed=46):
    """AC8.n — raw photo in, garment out. No cropper involvement at all."""
    ep, _ = CROP_ARMS[tag]
    # qwen-image-edit-2511 also takes the plural form, verified by smoke test
    key = "image_urls" if ("klein" in ep or "qwen" in ep) else "image_url"
    args = {key: [_b64(raw)] if key == "image_urls" else _b64(raw),
            "prompt": CROP_PROMPT, "seed": seed}
    return call(ep, args)


def seedvr(img):
    """AC9 — restoration over a crude fill. No prompt parameter exists on this
    endpoint (verified against the schema), so this arm is image-only by necessity."""
    return call("fal-ai/seedvr/upscale/image",
                {"image_url": _b64(img), "upscale_factor": 2, "noise_scale": 0})


def run(jobs, workers=6):
    """jobs: [(name, callable)] -> {name: image or None}. Failures are recorded as
    None rather than aborting: one dead endpoint must not lose the whole run."""
    _load_env()
    if not os.environ.get("FAL_KEY"):
        print("  FAL_KEY missing — paid arms skipped")
        return {}
    res = {}
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fn): n for n, fn in jobs}
        for f in cf.as_completed(futs):
            n = futs[f]
            try:
                res[n] = f.result()
                print(f"    ok    {n}")
            except Exception as e:
                res[n] = None
                print(f"    FAIL  {n}: {str(e)[:110]}")
    return res
