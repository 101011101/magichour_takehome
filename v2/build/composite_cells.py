#  V2 composite arm (composite_v2ow) — notebook cells ------------------------
#  klein_4b gen -> geometric face paste-back -> z-image low-strength refine
#  -> AuraFace identity gate (retry seed+1000, best-of-N).
#  Geometric paste-back only: V1 prompted identity-restore pulled the original
#  clothing back or lost to baseline; do not add prompted-restore stages.
#  fal is confined to the default_* wrappers; the harness injects gen_fn /
#  refine_fn / upload_fn so pipeline logic never touches fal_client.

#  §C1 · Constants ------------------------------------------------------------
import io
import math
import os
import tempfile

import cv2
import numpy as np
from PIL import Image

ARM_NAME = "composite_v2ow"
GEN_ENDPOINT = "fal-ai/flux-2/klein/4b/distilled/edit"       # $0.014 first MP
REFINE_ENDPOINT = "fal-ai/z-image/turbo/image-to-image"      # $0.005/MP
# Schemas per research/fal_v2_endpoint_schemas.md (verified 2026-08-14):
# klein: prompt + image_urls (person first, garment second) + seed; no
# negative_prompt/guidance. z-image: single image_url string + strength.
GEN_PROMPT = (
    "Replace the clothing of the person in image 1 with the garment shown in "
    "image 2. Keep the person's face, hair, skin tone, pose, hands, body and "
    "the background completely unchanged. Preserve the garment's exact "
    "color, pattern, print, and cut."
)
REFINE_PROMPT = (
    "Enhance the photo realism of this image. Fix any artifacts in hands, "
    "skin, and fabric textures. Do not change the person's identity, face, "
    "pose, clothing, or the background."
)
REFINE_STRENGTH = 0.2
IDENTITY_THRESHOLD = 0.55        # AuraFace cosine gate; starting point, tune on data
MAX_CANDIDATES = 3
CANDIDATE_SEED_STEP = 1000
FEATHER_FRAC = 0.05              # Gaussian sigma as fraction of face size
FACE_EXPAND = 0.25               # bbox expansion for the paste crop
HEAD_EXPAND = 0.35               # bbox expansion for the garment-overlap guard
CHANGE_DIFF_FLOOR = 30           # min gray delta counted as "changed"
MIN_CHANGE_AREA_FRAC = 0.01      # smaller change regions cannot block paste
GLOBAL_CHANGE_FRAC = 0.60        # above this the change region is unlocalizable
HEAD_OVERLAP_FRAC = 0.08         # garment pixels / head area that block paste
AURAFACE_REPO = "fal/AuraFace-v1"
AURAFACE_ROOT = os.environ.get(
    "AURAFACE_ROOT", os.path.join(tempfile.gettempdir(), "auraface"))


#  §C2 · Image + fal wrappers (fal only lives here) ---------------------------
def load_image(x):
    """Path or PIL -> RGB PIL."""
    if isinstance(x, Image.Image):
        return x.convert("RGB")
    return Image.open(x).convert("RGB")


def fal_upload(img_or_path):
    """Default upload_fn. Returns a URL fal endpoints accept."""
    import fal_client
    if isinstance(img_or_path, str):
        return fal_client.upload_file(img_or_path)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        load_image(img_or_path).save(f.name)
        path = f.name
    try:
        return fal_client.upload_file(path)
    finally:
        os.unlink(path)


def _fal_image(endpoint, args):
    import fal_client
    import requests
    res = fal_client.subscribe(endpoint, arguments=args)
    url = (res.get("images") or [res.get("image", {})])[0].get("url")
    return Image.open(io.BytesIO(requests.get(url).content)).convert("RGB")


def default_gen_fn(person_url, garment_url, seed):
    """gen_fn(person_url, garment_url, seed) -> PIL. Person first, garment second."""
    return _fal_image(GEN_ENDPOINT, {
        "prompt": GEN_PROMPT, "image_urls": [person_url, garment_url],
        "seed": seed, "num_images": 1})


def default_refine_fn(img, seed):
    """refine_fn(img, seed) -> PIL. Low-strength realism pass."""
    return _fal_image(REFINE_ENDPOINT, {
        "prompt": REFINE_PROMPT, "image_url": fal_upload(img),
        "strength": REFINE_STRENGTH, "seed": seed, "num_images": 1,
        "enable_prompt_expansion": False})


#  §C3 · Face detection (mediapipe, insightface fallback) ---------------------
_MP_DETECTOR = None


def _mediapipe_detector():
    global _MP_DETECTOR
    if _MP_DETECTOR is None:
        import mediapipe as mp
        _MP_DETECTOR = mp.solutions.face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.5)
    return _MP_DETECTOR


def detect_face(img):
    """Largest-face pixel bbox (x0, y0, x1, y1) or None."""
    rgb = np.asarray(load_image(img))
    h, w = rgb.shape[:2]
    try:
        res = _mediapipe_detector().process(rgb)
        dets = res.detections or []
        boxes = []
        for d in dets:
            r = d.location_data.relative_bounding_box
            boxes.append((r.xmin * w, r.ymin * h,
                          (r.xmin + r.width) * w, (r.ymin + r.height) * h))
    except Exception:                       # mediapipe unavailable on this host
        faces = auraface_app().get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        boxes = [tuple(f.bbox) for f in faces]
    if not boxes:
        return None
    x0, y0, x1, y1 = max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(w, int(x1)), min(h, int(y1))
    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1, y1)


def _expand_bbox(bbox, frac, w, h):
    x0, y0, x1, y1 = bbox
    dx, dy = (x1 - x0) * frac, (y1 - y0) * frac
    return (max(0, int(x0 - dx)), max(0, int(y0 - dy)),
            min(w, int(x1 + dx)), min(h, int(y1 + dy)))


#  §C4 · Garment-overlap guard ------------------------------------------------
def garment_blocks_face(person_img, gen_img, gen_face_bbox):
    """True when the garment change region reaches the head (hoods etc.);
    also True when the change is too global to localize — in doubt, no paste."""
    gen = np.asarray(load_image(gen_img))
    h, w = gen.shape[:2]
    orig = cv2.resize(np.asarray(load_image(person_img)), (w, h))
    diff = cv2.absdiff(cv2.cvtColor(gen, cv2.COLOR_RGB2GRAY),
                       cv2.cvtColor(orig, cv2.COLOR_RGB2GRAY))
    diff = cv2.GaussianBlur(diff, (5, 5), 0)
    # Otsu separates garment-scale change from global render drift.
    otsu, _ = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = (diff > max(CHANGE_DIFF_FLOOR, otsu)).astype(np.uint8)
    if mask.mean() > GLOBAL_CHANGE_FRAC:
        return True
    fb = gen_face_bbox
    head = _expand_bbox(fb, HEAD_EXPAND, w, h)
    work = mask.copy()
    work[fb[1]:fb[3], fb[0]:fb[2]] = 0             # face re-render never counts
    work = cv2.dilate(work, np.ones((7, 7), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(work)
    head_area = max(1, (head[2] - head[0]) * (head[3] - head[1]))
    for i in range(1, n):
        if stats[i][4] < MIN_CHANGE_AREA_FRAC * w * h:
            continue
        # Hood-style coverage fills the head region; a neckline only grazes it.
        inside = int((labels[head[1]:head[3], head[0]:head[2]] == i).sum())
        if inside > HEAD_OVERLAP_FRAC * head_area:
            return True
    return False


#  §C5 · Face paste-back ------------------------------------------------------
def face_paste_back(person_img, gen_img):
    """Feathered-ellipse paste of the original face over the generated face.
    Returns (PIL, meta). Skips gracefully: missing faces, garment over head."""
    person_img, gen_img = load_image(person_img), load_image(gen_img)
    meta = {"paste_applied": False, "skip_reason": None}
    src = detect_face(person_img)
    if src is None:
        meta["skip_reason"] = "no_face_in_person"
        return gen_img, meta
    dst = detect_face(gen_img)
    if dst is None:
        meta["skip_reason"] = "no_face_in_generated"
        return gen_img, meta
    if garment_blocks_face(person_img, gen_img, dst):
        meta["skip_reason"] = "garment_overlaps_head"
        return gen_img, meta

    sw, sh = person_img.size
    gw, gh = gen_img.size
    se = _expand_bbox(src, FACE_EXPAND, sw, sh)
    de = _expand_bbox(dst, FACE_EXPAND, gw, gh)
    dw, dh = de[2] - de[0], de[3] - de[1]
    if dw < 8 or dh < 8:
        meta["skip_reason"] = "face_too_small"
        return gen_img, meta
    crop = np.asarray(person_img.crop(se), dtype=np.float32)
    crop = cv2.resize(crop, (dw, dh), interpolation=cv2.INTER_LANCZOS4)

    mask = np.zeros((dh, dw), np.float32)
    cv2.ellipse(mask, (dw // 2, dh // 2), (int(dw * 0.42), int(dh * 0.44)),
                0, 0, 360, 1.0, -1)
    sigma = max(1.0, FEATHER_FRAC * max(dst[2] - dst[0], dst[3] - dst[1]))
    mask = cv2.GaussianBlur(mask, (0, 0), sigma)[..., None]

    out = np.asarray(gen_img, dtype=np.float32)
    region = out[de[1]:de[3], de[0]:de[2]]
    out[de[1]:de[3], de[0]:de[2]] = crop * mask + region * (1.0 - mask)
    meta.update({"paste_applied": True, "src_bbox": list(src),
                 "dst_bbox": list(dst)})
    return Image.fromarray(out.clip(0, 255).astype(np.uint8)), meta


#  §C6 · AuraFace identity gate -----------------------------------------------
_AURAFACE = None


def auraface_app():
    """AuraFace-v1 (Apache-2.0) via insightface; downloads ~300MB once."""
    global _AURAFACE
    if _AURAFACE is None:
        from huggingface_hub import snapshot_download
        from insightface.app import FaceAnalysis
        snapshot_download(AURAFACE_REPO, local_dir=os.path.join(
            AURAFACE_ROOT, "models", "auraface"))
        app = FaceAnalysis(name="auraface", root=AURAFACE_ROOT,
                           providers=["CPUExecutionProvider"],
                           allowed_modules=["detection", "recognition"])
        app.prepare(ctx_id=0, det_size=(640, 640))
        _AURAFACE = app
    return _AURAFACE


def face_embedding(img):
    """Normalized AuraFace embedding of the largest face, or None."""
    bgr = cv2.cvtColor(np.asarray(load_image(img)), cv2.COLOR_RGB2BGR)
    faces = auraface_app().get(bgr)
    if not faces:
        return None
    f = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return f.normed_embedding


def identity_cosine(ref_emb, img):
    """Cosine(ref person, largest face in img); None when either is missing."""
    if ref_emb is None:
        return None
    emb = face_embedding(img)
    if emb is None:
        return None
    return float(np.dot(ref_emb, emb))


#  §C7 · Full arm -------------------------------------------------------------
def composite_try_on(person, garment, seed, gen_fn=None, refine_fn=None,
                     upload_fn=None):
    """Person + garment -> (PIL, meta). Meta is JSON-safe for run_config.json:
    per-candidate cosines, paste decisions, shipped candidate index."""
    gen_fn = gen_fn or default_gen_fn
    refine_fn = refine_fn or default_refine_fn
    upload_fn = upload_fn or fal_upload
    person_img = load_image(person)
    person_url = upload_fn(person if isinstance(person, str) else person_img)
    garment_url = upload_fn(garment if isinstance(garment, str)
                            else load_image(garment))
    ref_emb = face_embedding(person_img)

    images, cands = [], []
    for i in range(MAX_CANDIDATES):
        s = seed + i * CANDIDATE_SEED_STEP
        gen = gen_fn(person_url, garment_url, s)
        pasted, pmeta = face_paste_back(person_img, gen)
        cos_pre = identity_cosine(ref_emb, pasted)
        refined = refine_fn(pasted, s)
        cos_post = identity_cosine(ref_emb, refined)
        repasted = False
        # Refine drifted the face past the gate: one geometric re-paste.
        if (cos_pre is not None and cos_post is not None
                and cos_pre >= IDENTITY_THRESHOLD
                and cos_post < IDENTITY_THRESHOLD):
            repaired, rmeta = face_paste_back(person_img, refined)
            if rmeta["paste_applied"]:
                refined, repasted = repaired, True
                cos_post = identity_cosine(ref_emb, refined)
        images.append(refined)
        cands.append({"seed": s, "paste_applied": pmeta["paste_applied"],
                      "paste_skip_reason": pmeta["skip_reason"],
                      "cos_pre_refine": cos_pre, "cos_post_refine": cos_post,
                      "repasted": repasted})
        if ref_emb is None:                 # gate cannot run; retries are noise
            break
        if cos_post is not None and cos_post >= IDENTITY_THRESHOLD:
            break

    scores = [(-math.inf if c["cos_post_refine"] is None
               else c["cos_post_refine"]) for c in cands]
    best = int(np.argmax(scores)) if any(s > -math.inf for s in scores) else 0
    meta = {"arm": ARM_NAME, "gen_endpoint": GEN_ENDPOINT,
            "refine_endpoint": REFINE_ENDPOINT,
            "refine_strength": REFINE_STRENGTH,
            "identity_threshold": IDENTITY_THRESHOLD,
            "identity_model": AURAFACE_REPO, "seed": seed,
            "gate_active": ref_emb is not None, "candidates": cands,
            "shipped_candidate": best,
            "shipped_cos": cands[best]["cos_post_refine"],
            "paste_applied": cands[best]["paste_applied"]
            or cands[best]["repasted"]}
    return images[best], meta
