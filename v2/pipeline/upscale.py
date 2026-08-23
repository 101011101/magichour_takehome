"""Stage 5. SeedVR2 when asked for, Lanczos when SeedVR2 would cost identity."""
import tempfile

import cv2
import numpy as np

from ._research import ensure

ensure()


def lanczos(path, factor=2):
    """Deterministic upscale. Zero generative risk, so it is the correct fallback
    when the caller asked for resolution and the generative pass misbehaved."""
    img = cv2.imread(path)
    out = cv2.resize(img, (img.shape[1] * factor, img.shape[0] * factor),
                     interpolation=cv2.INTER_LANCZOS4)
    dst = tempfile.mktemp(suffix="_lanczos.png")
    cv2.imwrite(dst, out)
    return dst


def seedvr2(path, cfg):
    """SeedVR2 x2 at noise_scale=0 -- NOT fal's default 0.1, which measured worse on
    both fidelity (4.88 vs 5.00) and identity (0.892 vs 0.943). Returns None on any
    failure so the caller can fall back rather than break."""
    import urllib.request
    try:
        import fal_client
        url = fal_client.upload_file(path)
        res = fal_client.subscribe(cfg.upscaler, arguments={
            "image_url": url, "upscale_mode": "factor", "upscale_factor": 2,
            "noise_scale": 0.0, "seed": cfg.seed, "output_format": "png"})
        got = (res.get("image") or {}).get("url") or res.get("url")
        dst = tempfile.mktemp(suffix="_seedvr2.png")
        urllib.request.urlretrieve(got, dst)
        return dst
    except Exception:
        return None


def identity_cos(before_path, after_path):
    """RAW AuraFace cosine between the two faces, compared at matched scale.

    RAW, not the normalised margin that checks.identity_margin returns. Same-person
    cosines across a generative edit run roughly 0.80-0.92, which is why the 0.90
    threshold here (identity_floor) means something quite different from the 0.90 in
    identity_escalate. Do not interchange them; crossing the two fired 6 false
    escalations in 8 on the first self-hosted run.

    Caveat the numbers in v2.4/RESULTS.md carry: the reference measurement compared
    a frame against a 2x upscale of itself, so part of the reported drop is
    resampling rather than damage. Downscaling here removes that confound, which
    means this runs slightly stricter than the figures that set the threshold.
    """
    a, b = cv2.imread(before_path), cv2.imread(after_path)
    if a is None or b is None:
        return None
    b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)
    import failure_gate as _fg
    app = _fg._face()
    if app is None:
        return None

    def emb(x):
        fs = app.get(x)
        if not fs:
            return None
        f = max(fs, key=lambda z: (z.bbox[2] - z.bbox[0]) * (z.bbox[3] - z.bbox[1]))
        v = f.normed_embedding
        return v / (np.linalg.norm(v) + 1e-9)
    e0, e1 = emb(a), emb(b)
    if e0 is None or e1 is None:
        return None          # no face to protect
    return float(np.dot(e0, e1))
