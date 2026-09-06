"""Self-hosted klein for the iron-man run. One pipeline, loaded once, timed per call.

black-forest-labs/FLUX.2-klein-4B (distilled, Apache-2.0): 4 steps, guidance 0 — the
settings V2 used self-hosted. On an A100 the whole model sits on the GPU; no offload.
Every call returns the image and its wall-clock seconds, so cost is measured, not
estimated.
"""
import time

import cv2
import numpy as np

REPO = "black-forest-labs/FLUX.2-klein-4B"
STEPS = 4
GUIDANCE = 0.0
_P = {}


def load(repo=REPO, dtype="bfloat16"):
    import torch
    from diffusers import Flux2KleinPipeline
    if "pipe" in _P:
        return _P["pipe"]
    t0 = time.time()
    pipe = Flux2KleinPipeline.from_pretrained(repo, torch_dtype=getattr(torch, dtype)).to("cuda")
    _P["pipe"] = pipe
    _P["load_seconds"] = round(time.time() - t0, 1)
    _P["gpu"] = torch.cuda.get_device_name(0)
    _P["repo"], _P["dtype"] = repo, dtype
    print(f"klein loaded in {_P['load_seconds']}s on {_P['gpu']}")
    return pipe


def info():
    return {k: _P[k] for k in ("load_seconds", "gpu", "repo", "dtype") if k in _P}


def _pil(bgr):
    from PIL import Image
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def _size(bgr, maxpix=1_048_576):
    """v3.4 rule for call 1: keep image 1's size up to 1 MP (2^20 - at most 4,096 tokens,
    under the distilled schedule's 4,300 branch), never upscale, floor to 16. v3.3 used
    1.15 MP, which admits up to ~4,492 tokens; no A4 crop on the fold exceeds 1 MP, so
    this cap change is a measured no-op there - it exists so an oversized future crop
    cannot silently cross the branch."""
    h, w = bgr.shape[:2]
    k = min(1.0, (maxpix / (h * w)) ** 0.5)
    return max(16, int(h * k) // 16 * 16), max(16, int(w * k) // 16 * 16)


def _size_fal(bgr, area=1_048_576):
    """fal's rule, measured (v3.4 probe, 20/20 responses reproduced): scale image 1 to
    area 1024^2 preserving aspect - UP or down - then floor each side to a multiple of 32.
    Keeps every call-2 canvas at <= 4096 tokens, below the 4300-token branch in
    compute_empirical_mu, i.e. on the schedule the distilled model was trained for."""
    h, w = bgr.shape[:2]
    k = (area / (h * w)) ** 0.5
    return max(32, int(h * k) // 32 * 32), max(32, int(w * k) // 32 * 32)


def edit(images_bgr, prompt, seed, steps=STEPS, guidance=GUIDANCE, canvas="v33"):
    """images_bgr: [image 1, (image 2)] as BGR arrays. Output canvas from image 1 by the
    'v33' rule (the lock) or the 'fal' rule (v3.4 link D). Returns (bgr, seconds)."""
    import torch
    pipe = load()
    h, w = (_size_fal if canvas == "fal" else _size)(images_bgr[0])
    t0 = time.time()
    out = pipe(prompt=prompt, image=[_pil(b) for b in images_bgr],
               height=h, width=w, num_inference_steps=steps, guidance_scale=guidance,
               generator=torch.Generator("cpu").manual_seed(int(seed))).images[0]
    torch.cuda.synchronize()
    return cv2.cvtColor(np.asarray(out), cv2.COLOR_RGB2BGR), round(time.time() - t0, 2)
