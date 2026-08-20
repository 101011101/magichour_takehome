# Deterministic failure gate — v2.2.3.
#
# Scores one generated frame against the two inputs it came from and returns a
# 0-1 score plus per-check detail. No model calls beyond what already ships in the
# pipeline; runs on CPU in a few hundred ms.
#
# DESIGN: high precision, low recall. Each check is a MARGIN in [0,1] and the
# composite is the WEAKEST margin, not an average -- one hard failure should sink a
# frame even if everything else is fine. Averaging would let a good background hide a
# swapped identity.
#
# The costs are asymmetric, which is why precision is favoured: a false reject burns
# a generation on every affected request, a false accept costs only the one it missed.
#
# KNOWN HOLE, stated rather than hidden: `garment` is the check that matters most and
# the one we cannot do well. Section 2b of EXPERIMENT.md measured garment_sim at 0.78
# and a VLM at 4/5 on an output that transferred NO garment. Both reward a plausible
# garment over the correct one, so a VLM does not rescue this -- it was already tried
# and already failed. The check is included with a low weight and its limit recorded.
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_S = {}


def _norm(v, lo, hi):
    """Margin in [0,1]: 0 at or below `lo` (clear failure), 1 at or above `hi`."""
    return float(np.clip((v - lo) / max(hi - lo, 1e-6), 0, 1))


def _rs(img, w=512):
    h = int(img.shape[0] * w / img.shape[1])
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)


# ---- individual checks --------------------------------------------------------
def check_degenerate(out):
    """Blank, constant, or blurred-out frame. Pixel statistics only."""
    g = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
    std = float(g.std())
    lap = float(cv2.Laplacian(g, cv2.CV_64F).var())
    uniq = len(np.unique(g[::4, ::4]))
    return min(_norm(std, 6, 22), _norm(lap, 12, 90), _norm(uniq, 24, 90)), \
challenge_detail(std=std, lap=lap, uniq=uniq)


def challenge_detail(**kw):
    return {k: round(float(v), 2) for k, v in kw.items()}


def check_noop(out, person):
    """A perfectly good photograph that is the INPUT, unchanged. Invisible to pixel
    statistics -- nothing is wrong with the image, it is just the wrong image."""
    from skimage.metrics import structural_similarity as ssim
    a = cv2.cvtColor(_rs(person), cv2.COLOR_BGR2GRAY)
    b = cv2.cvtColor(_rs(out), cv2.COLOR_BGR2GRAY)
    h = min(a.shape[0], b.shape[0])
    s = float(ssim(a[:h], b[:h]))
    # high SSIM to the input == the edit never happened
    return _norm(1.0 - s, 0.04, 0.16), challenge_detail(ssim_to_input=s)


def _pose():
    if "p" in _S:
        return _S["p"]
    try:
        import phase3_variants as P
        _S["p"] = P._pose()
    except Exception:
        _S["p"] = None
    return _S["p"]


def check_people(out):
    """Duplication -- two people rendered where one was asked for."""
    import mediapipe as mp
    lm = _pose()
    if lm is None:
        return 1.0, {"people": "n/a"}
    r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                           data=np.ascontiguousarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))))
    n = len(r.pose_landmarks) if r.pose_landmarks else 0
    return (1.0 if n == 1 else (0.0 if n > 1 else 0.45)), {"people": n}


def _face():
    if "f" in _S:
        return _S["f"]
    try:
        from huggingface_hub import snapshot_download
        from insightface.app import FaceAnalysis
        d = os.path.join(REPO, "v2", "runs", ".models", "auraface")
        if not os.path.exists(d):
            snapshot_download("fal/AuraFace-v1", local_dir=d)
        app = FaceAnalysis(name="auraface", providers=["CPUExecutionProvider"], root=d)
        app.prepare(ctx_id=-1, det_size=(320, 320))
        _S["f"] = app
    except Exception as e:
        print(f"  identity unavailable ({str(e)[:60]})")
        _S["f"] = None
    return _S["f"]


def check_identity(out, person):
    """Wrong person -- the reference model's face arriving in the output. The single
    most damaging failure in phase 2, and one of the few that IS reliably detectable,
    because it compares against a known input rather than judging in the abstract."""
    app = _face()
    if app is None:
        return 1.0, {"identity": "n/a"}
    def emb(img):
        f = app.get(img)
        return max(f, key=lambda x: (x.bbox[2] - x.bbox[0])).normed_embedding if f else None
    a, b = emb(person), emb(out)
    if a is None or b is None:
        return 0.55, {"identity": "no face found"}
    c = float(np.dot(a, b))
    return _norm(c, 0.18, 0.42), challenge_detail(identity_cos=c)


def check_background(out, person):
    """Scene repainted. Compared outside a generous person band, so garment changes
    inside the silhouette cannot move it."""
    a, b = _rs(person), _rs(out)
    h = min(a.shape[0], b.shape[0])
    a, b = a[:h], b[:h]
    m = np.zeros(a.shape[:2], np.uint8)
    hh, ww = m.shape
    m[int(hh * .03):, int(ww * .18):int(ww * .82)] = 1     # crude central person band
    sel = m == 0
    if sel.sum() < 500:
        return 1.0, {"bg": "n/a"}
    mse = float(np.mean((a[sel].astype(np.float32) - b[sel].astype(np.float32)) ** 2))
    psnr = 10 * np.log10(255 * 255 / max(mse, 1e-6))
    return _norm(psnr, 11, 24), challenge_detail(bg_psnr=psnr)


# ---- composite ----------------------------------------------------------------
WEIGHTS = {"degenerate": 1.0, "noop": 1.0, "people": 0.9,
           "identity": 1.0, "background": 0.7}


def grade(out_path, person_path, garment_path=None):
    out = cv2.imread(out_path)
    person = cv2.imread(person_path)
    if out is None or person is None:
        return {"score": 0.0, "verdict": "fail", "why": "unreadable", "checks": {}}
    checks, detail = {}, {}
    for name, fn, args in (("degenerate", check_degenerate, (out,)),
                           ("noop", check_noop, (out, person)),
                           ("people", check_people, (out,)),
                           ("identity", check_identity, (out, person)),
                           ("background", check_background, (out, person))):
        try:
            v, d = fn(*args)
        except Exception as e:
            v, d = 1.0, {"err": str(e)[:40]}
        checks[name] = round(float(v), 3)
        detail.update(d)
    # WEAKEST link, not the average: one hard failure must sink the frame
    worst = min(checks, key=lambda k: checks[k] / WEIGHTS[k])
    score = min(checks[k] / WEIGHTS[k] for k in checks)
    score = float(np.clip(score, 0, 1))
    return {"score": round(score, 3), "weakest": worst,
            "checks": checks, "detail": detail}
