# Garment cropping screen — local, CPU-only, license-clean.
#
# Purpose: see how good automatic garment isolation is BEFORE spending anything on
# generation. Two downloaded weights, both permissive: MediaPipe Selfie Multiclass
# (selfie_multiclass_256x256, Apache-2.0) and BiRefNet-general (MIT, ONNX export).
# Both cache under v2/runs/.models/, which is not committed.
#
# The old boundary was a 256x256 probability map thresholded to binary and upsampled
# ~6x — a staircase by construction. The fix is RESOLUTION:
#   1 segmentation   BiRefNet at 1024x1024 -> a high-resolution subject alpha, used
#                    exactly as it comes out. It is already soft; nothing is
#                    thresholded and no filter is run over it.
#   2 trimap         erode / dilate into definite-fg, definite-bg, unknown band —
#                    applied ONLY to the Selfie Multiclass CLASS labels
#   3 matting        guided-filter solve inside that band, so the internal
#                    clothes-against-skin edge is soft rather than stair-stepped
# Stages 2 and 3 were tried on the subject silhouette too and made it visibly worse
# (white speckles punched into a dark navy sleeve), so they are confined to the
# internal boundary. Product references get a plain geometric feather instead.
#
# BiRefNet defines WHAT THE SUBJECT IS. Selfie Multiclass is kept for SEMANTIC
# LABELS ONLY (clothes / body-skin / face-skin / hair). The two are composed by
# multiplying class alpha by the BiRefNet matte, so the outer silhouette always
# comes from the high-resolution matte and never from the 256x256 map.
#
# Four variants per garment reference, an increasing ladder of removal. All four
# are WHOLE-SUBJECT crops (subject bbox + margin) — no category band. Choosing
# which garment to change is the prompt's job, not the cropper's.
#   C1 bbox          whole-subject crop, background untouched
#   C2 bbox_nobg     same crop, background white, the wearer kept
#   C3 no_face       background white AND head removed (hair + face skin), body
#                    skin (arms, neck) kept
#   C4 clothes_only  every clothing class (coat, trousers, shoes, accessories),
#                    skin and face removed
# C3 and C4 also get an RGBA PNG carrying the real alpha, and an SVG contour —
# inspection artifacts only. Anything that could reach a model is flattened onto
# white BY US; we never hand an endpoint an alpha channel, because a default black
# flatten would be far worse.
#
# Two routes, selected by matrix `kind`:
#   product  flat-lay / ghost mannequin on uniform ground -> border-seeded OpenCV,
#            then the same trimap + matting stage for the edge
#   duo_*    garment worn by a person -> BiRefNet matte x Selfie Multiclass labels
#
# Deterministic: fixed thresholds, fixed model selections, no sampling.
# Usage: python v2/build/garment_crop.py [--html-only] [--recompute-matte]
import argparse
import csv
import os
import time
import urllib.request

import cv2
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TS2 = os.path.join(REPO, "v2", "runs", "ts2")
INP = os.path.join(TS2, "inputs")
OUT = os.path.join(REPO, "v2", "runs", "crop_screen")
ART = os.path.join(REPO, "v2", "artifacts")
MATRIX = os.path.join(TS2, "matrix.csv")
INP_REL = "../runs/ts2/inputs"      # page lives in v2/artifacts/
OUT_REL = "../runs/crop_screen"

# --- config -------------------------------------------------------------------
SELECT_REGION = None  # stub for a future selectable version. None = whole subject.
                      # A value here would restrict the mask to a body region; the
                      # band prior it replaces was removed because it dragged the
                      # jeans in on the navy peacoat.
PAD = 0.03            # bbox margin, fraction of the longer bbox side
CORNER = 40           # corner patch size sampled for the background colour; the full
                      # border strip is unusable — wide garments contaminate it
TOL_MIN, TOL_MAX = 8, 30
MIN_AREA = 0.015      # mask area fraction below which a route is called failed
MAX_AREA = 0.97
SPECK = 0.01          # connected components below this share of the mask are dropped
GAIN = 1.6            # transition sharpening applied after the guided-filter solve

MODEL_DIR = os.path.join(REPO, "v2", "runs", ".models")   # under runs/, not committed
CACHE_DIR = os.path.join(REPO, "v2", "runs", ".cache", "matte")
MODEL = os.path.join(MODEL_DIR, "selfie_multiclass_256x256.tflite")
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/image_segmenter/"
             "selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite")
# BiRefNet_lite (swin-tiny, 224MB) rather than the 973MB general checkpoint: 78s vs
# 246s per reference on this 4-core CPU, for boundary quality concentrated in hair
# and fur — which C3 and C4 delete anyway. Our edges are fabric against background,
# and the defect being fixed here is RESOLUTION (256 -> 1024), not matting finesse.
# BiRefNet_HR (2048) was rejected on runtime; references top out at 1536px, so 1024
# is already only a 1.5x upsample.
BIREF = os.path.join(MODEL_DIR, "BiRefNet_lite.onnx")
BIREF_URL = ("https://huggingface.co/onnx-community/BiRefNet_lite-ONNX/resolve/main/"
             "onnx/model.onnx")
BIREF_SIDE = 1024
BIREF_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
BIREF_STD = np.array([0.229, 0.224, 0.225], np.float32)

BG, HAIR, BODY, FACE, CLOTHES, OTHERS = range(6)

_STATE = {}


# ---------------------------------------------------------------- helpers ----
def _edge_connected(binary):
    """255 wherever a set pixel of `binary` is NOT reachable from the frame edge.
    A single-corner flood is not enough — a wide garment splits the background into
    two edge-touching regions and the second one would be filled in as a hole."""
    n, lab, _, _ = cv2.connectedComponentsWithStats(binary, 8)
    edge = np.zeros(n, bool)
    for k in set(lab[0].tolist() + lab[-1].tolist()
                 + lab[:, 0].tolist() + lab[:, -1].tolist()):
        edge[k] = True
    edge[0] = False
    return ((~edge[lab]).astype(np.uint8) * 255)


def fill_holes(mask):
    return _edge_connected((mask == 0).astype(np.uint8))


def largest_cc(mask):
    n, lab, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)
    if n <= 1:
        return mask
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return ((lab == k).astype(np.uint8) * 255)


def drop_specks(alpha, share=SPECK):
    """Remove islands without re-hardening the edge: components are judged on the
    binary mask, but the keep-mask is dilated past the alpha support before it is
    multiplied back, so no new boundary is introduced. Detached-but-real parts (a
    carried bag, a raised hand, shoes) survive; a strict largest-component rule
    would delete them."""
    b = (alpha > 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(b, 8)
    if n <= 1:
        return alpha
    tot = max(1, int(b.sum()))
    keep = np.zeros(n, bool)
    keep[1:] = st[1:, cv2.CC_STAT_AREA] >= share * tot
    if not keep.any():
        return alpha
    k = int(max(5, 0.006 * min(alpha.shape))) | 1
    m = cv2.dilate((keep[lab]).astype(np.uint8),
                   cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    return alpha * m


def feather(mask, px):
    """Geometric antialias for a HARD mask: blur the binary edge, no image guidance.
    Used on the product route, whose OpenCV cut is already at full resolution and
    only needs its stair-stepped label turned into a ramp. Deliberately not the
    guided filter — with nothing vague to resolve, structure transfer only invents
    holes in dark fabric."""
    k = int(max(3, px)) | 1
    return np.clip(cv2.GaussianBlur(mask.astype(np.float32), (k, k), 0), 0.0, 1.0)


def refine_band(bgr, prob, band_px, eps=1e-4):
    """Trimap + guided-filter solve, for a CLASS boundary only. Erode / dilate the
    thresholded probability into definite fg, definite bg and an unknown band, then
    resolve the band against the full-resolution image. Definite fg and bg are
    pinned, so the solve never touches the interior.

    Applied to the Selfie Multiclass labels, whose 256x256 boundary genuinely is
    vague. NOT applied to the BiRefNet matte: measured on the navy peacoat, running
    this over an already-soft 1024px matte punched white speckles ~15px into the
    dark navy sleeve, because guided filtering transfers image structure into the
    alpha and a near-black garment against a white ground is exactly the case where
    that goes wrong. The high-resolution matte needs no third stage."""
    band_px = int(max(2, band_px))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * band_px + 1,) * 2)
    hard = (prob > 0.5).astype(np.uint8)
    fg = cv2.erode(hard, k) > 0
    bg = cv2.dilate(hard, k) == 0
    a = cv2.ximgproc.guidedFilter(bgr, prob.astype(np.float32),
                                  max(2, band_px), eps)
    a = np.clip((a - 0.5) * GAIN + 0.5, 0.0, 1.0)
    a[fg] = 1.0
    a[bg] = 0.0
    return a


def bbox_of(mask, shape, pad=PAD):
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return 0, 0, shape[1], shape[0]
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    m = int(round(pad * max(x1 - x0, y1 - y0)))
    return (max(0, x0 - m), max(0, y0 - m),
            min(shape[1], x1 + m + 1), min(shape[0], y1 + m + 1))


def region_band(shape, region):
    """Stub for SELECT_REGION. Off by default — the whole subject is kept."""
    if region is None:
        return None
    raise NotImplementedError(f"select_region={region!r} is not implemented")


# ------------------------------------------------------- stage 1: BiRefNet ----
def _biref():
    if "biref" in _STATE:
        return _STATE["biref"]
    import onnxruntime as ort
    if not os.path.exists(BIREF):
        os.makedirs(MODEL_DIR, exist_ok=True)
        print(f"  fetching BiRefNet ({BIREF_URL.rsplit('/', 1)[-1]}, ~1GB)")
        urllib.request.urlretrieve(BIREF_URL, BIREF)
    so = ort.SessionOptions()
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    # onnxruntime already threads inside the graph; when several references run in
    # parallel processes the two levels oversubscribe 4 cores, so cap intra-op
    so.intra_op_num_threads = int(_STATE.get("threads", 0))
    _STATE["biref"] = ort.InferenceSession(BIREF, so, providers=["CPUExecutionProvider"])
    return _STATE["biref"]


def _matte_job(job):
    """ProcessPoolExecutor entry point: fill the disk cache for one reference.
    A worker holds the ~1GB graph plus activations, so worker count is bounded by
    RAM, not cores."""
    stem, path, threads, recompute = job
    _STATE["threads"] = threads
    t = time.time()
    biref_matte(cv2.imread(path, cv2.IMREAD_COLOR), stem, recompute)
    return stem, time.time() - t


def matte_prepass(refs, workers, recompute=False):
    """Compute every missing matte up front, in parallel, then let the main loop
    read them back from cache. Keeps the per-reference path single-threaded and
    deterministic while still using the box."""
    from concurrent.futures import ProcessPoolExecutor
    # Measured on this box (4 cores, 8GB): 3 workers is SLOWER than 1. Free memory
    # falls to ~16MB, ORT's mmap of the graph starts paging, and total CPU drops to
    # ~35% — the job is memory-bandwidth bound, not core bound. Default 1.
    workers = min(3, max(1, workers))
    jobs = [(s, p, max(1, 4 // max(1, workers)), recompute)
            for s, p, kind, _, _, _ in refs if kind != "product"
            and (recompute or not os.path.exists(os.path.join(CACHE_DIR, f"{s}.png")))]
    if not jobs:
        return 0.0
    os.makedirs(CACHE_DIR, exist_ok=True)
    print(f"  matte pre-pass: {len(jobs)} references, {workers} worker(s)")
    t0 = time.time()
    if workers <= 1:
        for j in jobs:
            s, dt = _matte_job(j)
            print(f"    {s[:48]:48s} {dt:6.1f}s")
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for s, dt in ex.map(_matte_job, jobs):
                print(f"    {s[:48]:48s} {dt:6.1f}s")
    wall = time.time() - t0
    print(f"  matte pre-pass wall {wall:.1f}s ({wall / len(jobs):.1f}s/ref effective)")
    return wall


def biref_matte(bgr, stem, recompute=False):
    """High-resolution subject probability, cached to disk as 8-bit. The cache is
    the raw network output only — every refinement stage below is recomputed, so
    thresholds stay editable without a 4-minute re-inference."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cp = os.path.join(CACHE_DIR, f"{stem}.png")
    h, w = bgr.shape[:2]
    if not recompute and os.path.exists(cp):
        c = cv2.imread(cp, cv2.IMREAD_GRAYSCALE)
        if c is not None and c.shape == (h, w):
            return c.astype(np.float32) / 255.0, 0.0
    s = _biref()
    rgb = cv2.cvtColor(cv2.resize(bgr, (BIREF_SIDE, BIREF_SIDE),
                                  interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
    x = (rgb.astype(np.float32) / 255.0 - BIREF_MEAN) / BIREF_STD
    x = np.ascontiguousarray(x.transpose(2, 0, 1)[None])
    t = time.time()
    y = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
    dt = time.time() - t
    p = 1.0 / (1.0 + np.exp(-y.astype(np.float32)))
    p = cv2.resize(p, (w, h), interpolation=cv2.INTER_CUBIC)
    p = np.clip(p, 0.0, 1.0)
    cv2.imwrite(cp, (p * 255).astype(np.uint8))
    return p, dt


# ------------------------------------------------------------ route: product --
def route_product(bgr):
    """Corner-seeded background removal. Uniform ground assumed; verified by the
    corner colour spread, which is reported as the route confidence. No person in
    frame, so all three masks are the same thing."""
    h, w = bgr.shape[:2]
    c = CORNER
    patches = np.concatenate([bgr[:c, :c].reshape(-1, 3), bgr[:c, -c:].reshape(-1, 3),
                              bgr[-c:, :c].reshape(-1, 3), bgr[-c:, -c:].reshape(-1, 3)])
    bg = np.median(patches, axis=0)
    spread = float(np.mean(np.std(patches.astype(np.float32), axis=0)))
    conf = float(max(0.0, 1.0 - spread / 20.0))
    tol = int(np.clip(6 + 3 * spread, TOL_MIN, TOL_MAX))

    diff = np.max(np.abs(bgr.astype(np.int16) - bg.astype(np.int16)), axis=2)
    m = _clean_binary(_edge_connected((diff < tol).astype(np.uint8)))
    frac = float((m > 0).mean())
    codes = [f"corner_spread={spread:.1f}", f"tol={tol}"]

    # low-contrast ground (white garment on light grey): re-cut on Otsu of the
    # distance map rather than a fixed tolerance
    if frac < MIN_AREA or frac > 0.90:
        t, _ = cv2.threshold(np.clip(diff, 0, 255).astype(np.uint8), 0, 255,
                             cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        m2 = _clean_binary(_edge_connected((diff < t).astype(np.uint8)))
        f2 = float((m2 > 0).mean())
        codes.append(f"retry_otsu t={int(t)} frac={f2:.3f}")
        if MIN_AREA < f2 < 0.90:
            m, frac = m2, f2
    if frac < MIN_AREA or frac > MAX_AREA:
        codes.append("fallback_full_frame")
        m = np.full((h, w), 255, np.uint8)

    a = feather(m > 0, 0.004 * min(h, w))
    return a, a, a, conf, codes


def _clean_binary(mask, k=9):
    e = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    m = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, e)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, e)
    return fill_holes(largest_cc(m))


# ----------------------------------------------------------------- route: duo --
def _multiclass():
    """Selfie Multiclass: 6 classes, 256x256 input, Apache-2.0. Semantic labels
    only — the silhouette comes from BiRefNet. Returns None if unavailable."""
    if "mc" in _STATE:
        return _STATE["mc"]
    try:
        if not os.path.exists(MODEL):
            os.makedirs(MODEL_DIR, exist_ok=True)
            urllib.request.urlretrieve(MODEL_URL, MODEL)
        from mediapipe.tasks import python as mpp
        from mediapipe.tasks.python import vision
        _STATE["mc"] = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
            base_options=mpp.BaseOptions(model_asset_path=MODEL),
            running_mode=vision.RunningMode.IMAGE,
            output_category_mask=False, output_confidence_masks=True))
    except Exception as e:
        print(f"  multiclass unavailable ({str(e)[:80]})")
        _STATE["mc"] = None
    return _STATE["mc"]


def route_duo(bgr, stem, recompute=False):
    import mediapipe as mp
    h, w = bgr.shape[:2]
    codes = []

    # the subject silhouette is the BiRefNet matte AS IT COMES: it is already a
    # 1024px soft alpha, and every post-filter tried on it made it worse
    prob, dt = biref_matte(bgr, stem, recompute)
    subject = drop_specks(prob)
    codes.append("birefnet" + ("" if dt else "_cached"))
    if dt:
        codes.append(f"matte_s={dt:.1f}")
    sfrac = float((subject > 0.5).mean())
    if sfrac < MIN_AREA:
        codes.append("fallback_full_frame")
        subject = np.ones((h, w), np.float32)
        sfrac = 1.0
    codes.append(f"subject_frac={sfrac:.2f}")

    seg = _multiclass()
    if seg is None:
        codes.append("no_multiclass")
        return subject, subject, subject, 0.0, codes
    res = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB,
                               data=np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))))
    p = np.stack([cv2.resize(m.numpy_view(), (w, h), interpolation=cv2.INTER_LINEAR)
                  for m in res.confidence_masks])

    # internal class boundary (clothes against skin): the class map is inferred at
    # 256x256, so its band is wide — a wider trimap and the same guided solve
    band = max(3, 0.010 * min(h, w))
    # Two head definitions, because hair over the shoulders is genuinely
    # ambiguous: removing it punches a hole in the garment, keeping it risks the
    # model reading hair as fabric. Not resolvable by argument — C3.1 and C3.2 go
    # to the klein trials and the model's response decides.
    head = refine_band(bgr, p[HAIR] + p[FACE], band)   # C3.1: face + hair
    face_only = refine_band(bgr, p[FACE], band)        # C3.2: face, hair kept
    skin = refine_band(bgr, p[BODY], band)

    # SUBTRACTIVE, not intersective. Intersecting with the clothes class was tried
    # and it notched 6px blocks out of the peacoat's outline: at the silhouette the
    # clothes class is exactly as coarse as the 256x256 map it came from, so it
    # would decide the outer boundary. Head and skin are interior and localised, so
    # subtracting them leaves the high-resolution matte in charge of the outline.
    # C4 is therefore every clothing class by construction — coat, trousers, shoes,
    # bag — which is what the new definition asks for.
    noface = drop_specks(subject * (1.0 - head))            # C3.1
    nofacehair = drop_specks(subject * (1.0 - face_only))   # C3.2
    clothes = drop_specks(noface * (1.0 - skin))

    conf = float(p[CLOTHES][clothes > 0.5].mean()) if (clothes > 0.5).any() else 0.0
    codes += [f"clothes_conf={conf:.2f}",
              f"head_frac={(head > 0.5).mean():.3f}",
              f"hair_frac={float(((head > 0.5) & (face_only <= 0.5)).mean()):.3f}",
              f"skin_frac={(skin > 0.5).mean():.3f}",
              f"select_region={SELECT_REGION or 'off'}"]
    region_band((h, w), SELECT_REGION)
    return subject, noface, nofacehair, clothes, conf, codes


# ------------------------------------------------------------------ outputs ---
def to_svg(alpha, path, stem):
    """Inspection artifact only — the model path stays raster."""
    mask = (alpha > 0.5).astype(np.uint8) * 255
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = mask.shape
    d = []
    for c in cnts:
        if cv2.contourArea(c) < 0.0005 * h * w:
            continue
        a = cv2.approxPolyDP(c, 0.0015 * cv2.arcLength(c, True), True)
        pts = a.reshape(-1, 2)
        d.append("M " + " L ".join(f"{x} {y}" for x, y in pts) + " Z")
    open(path, "w").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" '
        f'height="{h}"><title>{stem} — C4 clothes_only mask contour '
        f'(INSPECTION ARTIFACT, not a model input)</title>'
        f'<path d="{" ".join(d)}" fill="#b7b1fa" fill-rule="evenodd"/></svg>')
    return len(d)


def write_rgb(path, bgr):
    assert bgr.ndim == 3 and bgr.shape[2] == 3, path
    cv2.imwrite(path, bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])


def process(stem, src, kind, category, recompute=False):
    t0 = time.time()
    bgr = cv2.imread(src, cv2.IMREAD_COLOR)
    h, w = bgr.shape[:2]
    if kind == "product":
        route = "product_opencv"
        subject, noface, mask, conf, codes = route_product(bgr)
        nofacehair = noface   # no person in frame; the two head variants coincide
    else:
        route = "duo_biref_multiclass"
        subject, noface, nofacehair, mask, conf, codes = route_duo(bgr, stem, recompute)
        if "no_multiclass" in codes:
            route = "duo_biref_only"
    frac = float((mask > 0.5).mean())

    # whole-subject framing: every variant shares the SUBJECT bbox, not the garment
    # bbox, so C3 and C4 stay registered against C1 and C2
    x0, y0, x1, y1 = bbox_of((subject > 0.5).astype(np.uint8), (h, w))
    crop = bgr[y0:y1, x0:x1]
    A = {"c2_bbox_nobg": subject[y0:y1, x0:x1],
         "c3_no_face": noface[y0:y1, x0:x1],
         "c32_no_face_keep_hair": nofacehair[y0:y1, x0:x1],
         "c4_clothes_only": mask[y0:y1, x0:x1]}

    # flattened onto white BY US — an alpha channel must never reach an endpoint,
    # a default black flatten would be far worse than white. The flatten is done
    # against the real alpha, which is what makes the edge antialiased.
    def flat(a):
        f = a[..., None].astype(np.float32)
        return np.clip(crop.astype(np.float32) * f + 255.0 * (1.0 - f), 0, 255).astype(np.uint8)

    write_rgb(os.path.join(OUT, f"{stem}__c1_bbox.jpg"), crop)
    for tag, a in A.items():
        write_rgb(os.path.join(OUT, f"{stem}__{tag}.jpg"), flat(a))
    # RGBA carries the UNFLATTENED crop plus the true alpha, so the matte can be
    # inspected on its own; only the JPGs above are model-facing
    for tag in ("c3_no_face", "c32_no_face_keep_hair", "c4_clothes_only"):
        cv2.imwrite(os.path.join(OUT, f"{stem}__{tag}_alpha.png"),
                    np.dstack([crop, (A[tag] * 255).astype(np.uint8)]))
    npaths = to_svg(A["c4_clothes_only"], os.path.join(OUT, f"{stem}__c4_contour.svg"), stem)

    # share of the mask that carries a genuinely fractional alpha — 0 means the
    # boundary is still a hard label, which is the defect this rework removes
    soft = float(((A["c4_clothes_only"] > 0.02) & (A["c4_clothes_only"] < 0.98)).mean())
    dt = time.time() - t0
    codes += [f"noface_frac={(noface > 0.5).mean():.2f}", f"soft_frac={soft:.4f}",
              f"svg_paths={npaths}", f"bbox={x1 - x0}x{y1 - y0}", f"runtime_s={dt:.1f}"]
    return {"stem": stem, "kind": kind, "category": category, "route": route,
            "mask_area_frac": round(frac, 4), "confidence": round(conf, 3),
            "soft_edge_frac": round(soft, 5), "runtime_s": round(dt, 1),
            "crop_w": x1 - x0, "crop_h": y1 - y0, "src_w": w, "src_h": h,
            "reason_codes": ";".join(codes),
            "failed": frac < MIN_AREA or "fallback_full_frame" in codes}


def load_refs_dir(dirs):
    """Arbitrary image directories as references. Used for sweeps over person
    sets that are not in the Testset2 matrix (e.g. test_set/people, which carries
    the stratified skin-tone / body-size / gender quotas and is therefore the set
    most likely to surface a bias failure). Everything is treated as a worn
    reference: kind='duo_sweep', no category band (whole-body crop anyway), no
    target phrase."""
    exts = (".jpg", ".jpeg", ".png", ".webp")
    seen, refs = set(), []
    for d in dirs:
        if not os.path.isdir(d):
            print(f"  MISSING dir {d}")
            continue
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith(exts):
                continue
            stem = os.path.splitext(f)[0]
            if stem in seen:
                continue
            seen.add(stem)
            refs.append((stem, os.path.join(d, f), "duo_sweep", "", stem, ""))
    return refs


def load_refs():
    seen, refs = set(), []
    for r in csv.DictReader(open(MATRIX)):
        stem = os.path.splitext(os.path.basename(r["garment"]))[0]
        if stem in seen:
            continue
        seen.add(stem)
        p = os.path.join(INP, stem + ".jpg")
        if not os.path.exists(p):
            print(f"  MISSING {p}")
            continue
        refs.append((stem, p, r["kind"], r["category"], r["id"], r["target"]))
    return refs


# --------------------------------------------------------------------- page ---
# eyeballed on the rendered outputs, one line each; the derived rule below is the
# fallback for anything not on this list
OBSERVED = {
    "dualuse_navy_peacoat_onmodel":
        "the band-prior bug is gone by construction — coat, jeans and boots all "
        "whole, outline smooth, only a sliver of cuff skin left at the wrists",
    "dualuse_gal_gadot_blue_dress_redcarpet":
        "hardest duo and the cleanest result: the gown alone, arms, legs and head "
        "gone, sandal straps kept, edges crisp",
    "dualuse_lp_beige_long_coat_menswear":
        "the bias reference — dark skin, beige coat — clean end to end, whole "
        "outfit from collar to shoes",
    "dualuse_hugh_jackman_grey_suit_outdoor":
        "suit whole and the grass background fully gone; body-skin class misses a "
        "sliver of neck and part of one hand",
    "dualuse_lp_floral_kimono_set":
        "the hanging fabric tie survives intact, where the old cut chopped it",
    "dualuse_man_black_suit_studio_nonceleb":
        "black lapel against white now cuts tight, no halo; the crossed hands are "
        "removed without holing the jacket front",
}


def quality_note(row):
    if row["stem"] in OBSERVED and not row["failed"]:
        return OBSERVED[row["stem"]]
    c = row["reason_codes"]
    if row["failed"]:
        return "FAILED — fell back; do not send"
    if row["route"] == "product_opencv":
        sp = float(c.split("corner_spread=")[1].split(";")[0])
        return ("clean cut, uniform ground" if sp < 6 else
                "usable, some ground texture" if sp < 15 else "noisy ground — check edges")
    if "no_multiclass" in c:
        return "matte only, no class labels — C3 and C4 are copies of C2"
    if row["mask_area_frac"] < 0.06:
        return "clothes mask small — check for under-segmentation"
    return "plausible whole-subject crop; verify hands and neckline"


def html(rows):
    import json
    sets = []
    for r in rows:
        s = r["stem"]
        sub = (f"route {r['route']} · area {r['mask_area_frac']:.3f} · "
               f"conf {r['confidence']:.2f} · {r['reason_codes']}")
        # --refs-dir sweeps pull originals from arbitrary directories, so the
        # path is taken from the log rather than assumed to be ts2/inputs
        _sp = r.get("src_path") or ""
        _orig = (os.path.relpath(_sp, ART) if _sp and os.path.exists(_sp)
                 else f"{INP_REL}/{s}.jpg")
        items = [{"label": "ORIGINAL — source reference",
                  "src": _orig,
                  "sub": f"{r['kind']} · {r['category']} · {r['src_w']}x{r['src_h']}",
                  "bad": None}]
        for k, lab in (("c1_bbox", "C1 bbox — whole-subject crop, background untouched"),
                       ("c2_bbox_nobg", "C2 bbox_nobg — background white, the wearer kept"),
                       ("c3_no_face", "C3.1 no_face — background white, face AND hair removed, "
                                      "body skin kept"),
                       ("c32_no_face_keep_hair",
                        "C3.2 no_face keep_hair — face removed, HAIR KEPT, "
                        "background white"),
                       ("c4_clothes_only", "C4 clothes_only — every clothing class, "
                                           "skin and face removed, on white")):
            items.append({"label": lab, "src": f"{OUT_REL}/{s}__{k}.jpg",
                          "sub": sub, "bad": bool(r["failed"])})
        for k, lab in (("c3_no_face_alpha", "C3 alpha (inspection) — RGBA PNG"),
                       ("c4_clothes_only_alpha", "C4 alpha (inspection) — RGBA PNG")):
            # marked so the viewer can put a checkerboard behind transparency
            items.append({"label": lab, "src": f"{OUT_REL}/{s}__{k}.png",
                          "sub": "true 0-1 alpha over the unflattened crop; the "
                                 "white-flattened JPG is what would be sent, never this",
                          "alpha": True, "bad": bool(r["failed"])})
        items.append({"label": "C4 contour (inspection) — SVG path",
                      "src": f"{OUT_REL}/{s}__c4_contour.svg",
                      "sub": "mask outline, inspection artifact only",
                      "alpha": True, "bad": bool(r["failed"])})
        if os.path.exists(os.path.join(OUT, f"{s}__edge_before_after.png")):
            items.append({"label": "EDGE ZOOM — old pipeline (left) vs new (right)",
                          "src": f"{OUT_REL}/{s}__edge_before_after.png",
                          "sub": "same boundary, same source coordinates, 4x zoom",
                          "bad": None})
        sets.append({"pair": s, "items": items, "before_i": 0})

    trs = "".join(
        f'<tr class="{"fail" if r["failed"] else "win"}"><td class="n">{r["stem"]}</td>'
        f'<td class="n">{r["kind"]}</td><td class="n">{r["route"]}</td>'
        f'<td>{r["mask_area_frac"]:.3f}</td>'
        f'<td>{r["confidence"]:.2f}</td><td>{r["soft_edge_frac"]:.4f}</td>'
        f'<td>{r["runtime_s"]:.1f}</td><td>{r["crop_w"]}x{r["crop_h"]}</td>'
        f'<td class="n">{quality_note(r)}</td></tr>' for r in rows)
    hdr = ("<tr><th>reference</th><th>kind</th><th>route</th>"
           "<th>mask area frac</th><th>conf</th><th>soft edge frac</th>"
           "<th>runtime s</th><th>crop</th><th>quality note</th></tr>")
    nprod = sum(1 for r in rows if r["kind"] == "product")
    dur = [r for r in rows if r["kind"] != "product"]
    med = sorted(r["runtime_s"] for r in dur)[len(dur) // 2] if dur else 0.0

    page = f"""<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Garment Cropping Screen</title><style>
:root{{--bg:#14141d;--card:#1b1b26;--card2:#20202c;--line:#2b2b3a;--ink:#f3f3f7;
--body:#aab0be;--mut:#868da0;--acc:#928af5;--acc2:#b7b1fa;--ok:rgba(90,200,140,.14);
--bad:rgba(230,110,110,.12);--okb:rgba(90,200,140,.65);--badb:rgba(230,110,110,.6)}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--body);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.wrap{{max-width:1600px;margin:0 auto;padding:30px 28px 60px}}
h1{{font-size:29px;margin:2px 0 6px;color:var(--ink);font-weight:700;letter-spacing:-.4px}}
h2{{font-size:19px;margin:34px 0 8px;color:var(--ink);font-weight:700}}
.kick{{color:var(--mut);font-size:13.5px}}p{{max-width:1000px}}b{{color:var(--ink)}}
.mut{{color:var(--mut);font-size:12.5px}}
table{{border-collapse:collapse;margin:10px 0;width:100%;font-variant-numeric:tabular-nums}}
th,td{{border-bottom:1px solid var(--line);padding:6px 9px;font-size:12.5px;text-align:right}}
th{{color:var(--mut);font-weight:600;text-transform:uppercase;font-size:10.5px;letter-spacing:.5px}}
td.n,th:first-child{{text-align:left}}td.n{{color:var(--ink);font-weight:600}}
tr.win td{{background:var(--ok)}}tr.fail td{{background:var(--bad)}}
.tw{{overflow-x:auto}}
.meta{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin:16px 0 4px}}
@media(max-width:1100px){{.meta{{grid-template-columns:1fr}}}}
.mcard{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}}
.mh{{font-size:10.5px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
color:var(--acc);margin-bottom:6px}}
.mt{{font-size:17px;font-weight:700;color:var(--ink);margin-bottom:6px}}
.mp{{font-size:12.5px;color:var(--mut);margin:8px 0 0}}
#v{{margin:14px 0 0;background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:14px 18px 18px;position:sticky;top:0;z-index:5}}
.vbar{{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap;margin-bottom:10px}}
.vlabel{{font-size:20px;font-weight:700;color:var(--ink);letter-spacing:-.2px}}
.vlabel.before{{color:var(--acc2)}}
.pill{{font-size:10.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
padding:2px 8px;border-radius:99px}}
.pill.fail{{background:var(--bad);color:#ff9d9d;border:1px solid var(--badb)}}
.vsub{{color:var(--mut);font-size:13px;font-variant-numeric:tabular-nums}}
.vpos{{margin-left:auto;color:var(--mut);font-size:12.5px;font-family:ui-monospace,Menlo,monospace}}
/* alpha artifacts get a checkerboard so transparency is legible, not invisible */
#stage.alpha,.strip figure.alpha img{{
background-color:#3a3a48;
background-image:linear-gradient(45deg,#22222c 25%,transparent 25%),
linear-gradient(-45deg,#22222c 25%,transparent 25%),
linear-gradient(45deg,transparent 75%,#22222c 75%),
linear-gradient(-45deg,transparent 75%,#22222c 75%);
background-size:20px 20px;
background-position:0 0,0 10px,10px -10px,-10px 0}}
#stage{{background:#0d0d14;border-radius:10px;display:flex;align-items:center;
justify-content:center;overflow:auto;height:74vh;min-height:420px}}
#stage img{{display:block;max-width:100%;max-height:74vh;object-fit:contain;cursor:zoom-in}}
#stage.zoom{{align-items:flex-start;justify-content:flex-start}}
#stage.zoom img{{max-width:none;max-height:none;cursor:zoom-out}}
.keys{{margin-top:10px;color:var(--mut);font-size:12.5px}}
kbd{{background:var(--card2);border:1px solid var(--line);border-bottom-width:2px;
border-radius:4px;padding:1px 6px;font-size:11.5px;color:var(--body)}}
.strip{{display:flex;gap:8px;overflow-x:auto;margin-top:12px;padding-bottom:4px}}
.strip figure{{margin:0;flex:0 0 auto;width:104px;text-align:center;cursor:pointer;opacity:.5}}
.strip figure.on{{opacity:1}}
.strip img{{width:100%;height:104px;object-fit:cover;border-radius:6px;
border:2px solid transparent;background:var(--card2);display:block}}
.strip figure.on img{{border-color:var(--acc)}}
.strip figure.fail img{{border-color:var(--badb)}}
.strip figcaption{{font-size:10px;color:var(--mut);margin-top:4px;line-height:1.3;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.pairs{{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}}
.pairs button{{border:1px solid var(--line);background:var(--card2);color:var(--body);
border-radius:6px;padding:5px 12px;font-size:12px;cursor:pointer;
font-family:ui-monospace,Menlo,monospace}}
.pairs button.on{{background:var(--acc);color:#14141d;border-color:var(--acc);font-weight:700}}
footer{{margin:40px 0 8px;padding-top:14px;border-top:1px solid var(--line);
color:var(--mut);font-size:12.5px}}
</style><div class="wrap">
<div class="kick">Virtual try-on v2.2.1 — exploratory, local, free, CPU-only</div>
<h1>Garment Cropping Screen</h1>
<p>How good is automatic garment isolation before we spend anything on generation?
Everything on this page ran <b>locally on the CPU at zero cost</b>: OpenCV plus two
permissively licensed weights — <b>BiRefNet-general</b> (MIT) for the
high-resolution subject matte and <b>Selfie Multiclass 256&times;256</b> (Apache-2.0)
for semantic labels. No API calls, no paid models.
{len(rows)} unique garment references from <b>v2/runs/ts2/matrix.csv</b>
({nprod} product, {len(rows) - nprod} duo). Median duo runtime
<b>{med:.0f}s</b> per reference on 4 CPU cores.</p>
<div class="meta">
<div class="mcard"><div class="mh">Stage 1 — segmentation</div>
<div class="mt">BiRefNet at 1024&times;1024</div>
<p class="mp">A high-resolution subject alpha, <b>used exactly as it comes out</b> —
nothing is thresholded and no filter is run over it. The old pipeline had no stage
like this: it thresholded a 256&times;256 class map and upsampled it about six times,
which is a staircase by construction. Inference is ~4 min per reference on this
machine, so the raw output is cached under <code>v2/runs/.cache/matte/</code> and
everything downstream is recomputed on each run in about a second.</p></div>
<div class="mcard"><div class="mh">Stage 2 — trimap</div>
<div class="mt">erode / dilate, class labels only</div>
<p class="mp">The <b>class</b> probability — clothes, skin, hair — is thresholded,
then eroded and dilated into definite foreground, definite background and an unknown
band. This is the boundary that is genuinely vague, because it is the one still
coming from the 256&times;256 map. The subject silhouette gets no trimap.</p></div>
<div class="mcard"><div class="mh">Stage 3 — matting</div>
<div class="mt">guided solve, internal edge only</div>
<p class="mp">Inside the unknown band, a guided filter against the full-resolution
image turns the class label into a real <b>0-1 alpha</b>, so clothes-against-skin is
soft rather than stair-stepped. Running the same solve over the <i>subject</i> matte
was tried and reverted: it punched white speckles about 15px into the navy peacoat's
sleeve, because guided filtering transfers image structure into the alpha and dark
fabric on a white ground is the worst case for that. High-resolution segmentation
alone was the whole fix for the outer edge.</p></div>
</div>
<h2>How the two models compose</h2>
<p><b>BiRefNet defines what the subject is; Selfie Multiclass defines which part is
which.</b> Class alpha is multiplied into the matte and only ever subtracts from it,
so the outer silhouette in every variant is the high-resolution one and never the
256&times;256 map. The composition is <b>subtractive</b> for that reason: C3 is the
matte minus the head, C4 is C3 minus body skin. Intersecting with the clothes class
instead was tried and it notched 6px blocks out of the peacoat's outline, because at
the silhouette that class is exactly as coarse as the map it came from. Product references (flat-lay, ghost mannequin) skip BiRefNet
entirely — corner-seeded colour distance is already exact at full resolution there —
but they run the same trimap and matting stage so the edge is an alpha, not a label.</p>
<h2>The four variants</h2>
<p>All four are <b>whole-subject crops</b> — the subject bounding box plus a 3%
margin, identical across variants so they stay registered. There is no
shoulders-to-hips or hips-down band any more: the band prior was what dragged the
jeans into the navy peacoat crop, and deciding <i>which</i> garment to change is the
prompt's job, not the cropper's. A <code>select_region</code> knob is stubbed and
defaulted off for a future selectable version.</p>
<p><b>C1 bbox</b> box crop, background untouched &middot; <b>C2 bbox_nobg</b> background
white, wearer kept &middot; <b>C3 no_face</b> background white and the head removed
(hair + face skin), body skin kept &middot; <b>C4 clothes_only</b> every clothing
class — coat, trousers, shoes, accessories — with all skin and the face removed. The
face is the thing that most needs to go, it is a second identity in the frame, while
removing every scrap of skin may cost more than it buys; C3 against C4 is the next
test. Everything that could be sent to a model is <b>flattened onto white by us</b>
against the real alpha: an endpoint that flattens alpha to black would be much worse
than white, so we never hand one an alpha channel.</p>
<div id="v">
<div class="vbar"><span class="vlabel" id="vl"></span><span id="vp"></span>
<span class="vsub" id="vs"></span><span class="vpos" id="vpos"></span></div>
<div id="stage"><img id="vi"></div>
<div class="keys"><kbd>&larr;</kbd><kbd>&rarr;</kbd> step through this set &middot;
<kbd>&uarr;</kbd><kbd>&darr;</kbd> next / previous set &middot;
<kbd>B</kbd> hold to flip to the ORIGINAL &middot; <kbd>Z</kbd> or click to zoom 1:1 &middot;
<kbd>O</kbd> open full size</div>
<div class="strip" id="strip"></div>
<div class="pairs" id="pairs"></div>
</div>
<h2>Per-reference outcome</h2>
<div class="tw"><table>{hdr}{trs}</table></div>
<p class="mut">Mask area fraction is the C4 clothes mask as a share of the <b>full source
frame</b>, before cropping. Confidence is the corner-colour uniformity (product route)
or the mean clothes-class confidence inside the mask (duo route). Soft edge fraction is
the share of the crop with alpha strictly between 0.02 and 0.98. Runtime is wall clock
for the whole reference with the BiRefNet matte served from cache. All four variants are
written as <b>3-channel RGB flattened onto white</b>; the alpha PNGs and the SVG
contours are inspection artifacts and are never sent to a model.</p>
<footer>Generated by v2/build/garment_crop.py from v2/runs/crop_screen/. Open from
v2/artifacts/. Exploratory v2.2.2 — nothing here has been committed to the deploy path.</footer></div>
<script>
const SETS={json.dumps(sets)};
let S=0,I=0,ZOOM=false,PEEK=false;
const el=id=>document.getElementById(id);
const strip=el("strip"),pairs=el("pairs");
SETS.forEach((s,i)=>{{const b=document.createElement("button");b.textContent=s.pair;
b.onclick=()=>{{S=i;I=0;build();render()}};pairs.appendChild(b)}});
function build(){{strip.innerHTML="";SETS[S].items.forEach((it,i)=>{{
const f=document.createElement("figure");f.className=(it.bad===true?"fail":"");
f.innerHTML='<img src="'+it.src+'"><figcaption>'+it.label+'</figcaption>';
f.onclick=()=>{{I=i;render()}};strip.appendChild(f)}})}}
function render(){{const set=SETS[S];const bi=set.before_i||0;
const it=set.items[PEEK?bi:I];
el("vi").src=it.src;\nel("stage").classList.toggle("alpha",!!it.alpha);
el("vl").textContent=it.label;el("vl").className="vlabel"+((I<=bi||PEEK)?" before":"");
el("vs").textContent=it.sub;
el("vp").innerHTML=it.bad===true?'<span class="pill fail">route failed</span>':"";
el("vpos").textContent=set.pair+"   "+(I+1)+"/"+set.items.length+
"   set "+(S+1)+"/"+SETS.length+(PEEK?"   [ORIGINAL]":"");
[...strip.children].forEach((c,i)=>c.classList.toggle("on",i===I));
[...pairs.children].forEach((c,i)=>c.classList.toggle("on",i===S));
const nx=SETS[(S+1)%SETS.length];nx.items.forEach(x=>{{(new Image()).src=x.src}});}}
el("stage").onclick=()=>{{ZOOM=!ZOOM;el("stage").classList.toggle("zoom",ZOOM)}};
document.addEventListener("keydown",e=>{{const n=SETS[S].items.length;
if(e.key==="ArrowRight"){{I=(I+1)%n;render();e.preventDefault()}}
else if(e.key==="ArrowLeft"){{I=(I+n-1)%n;render();e.preventDefault()}}
else if(e.key==="ArrowDown"){{S=(S+1)%SETS.length;I=0;build();render();e.preventDefault()}}
else if(e.key==="ArrowUp"){{S=(S+SETS.length-1)%SETS.length;I=0;build();render();e.preventDefault()}}
else if(e.key==="b"||e.key==="B"){{if(!PEEK){{PEEK=true;render()}}}}
else if(e.key==="z"||e.key==="Z"){{ZOOM=!ZOOM;el("stage").classList.toggle("zoom",ZOOM)}}
else if(e.key==="o"||e.key==="O"){{window.open(SETS[S].items[I].src,"_blank")}}}});
document.addEventListener("keyup",e=>{{if((e.key==="b"||e.key==="B")&&PEEK){{PEEK=false;render()}}}});
build();render();
</script>"""
    os.makedirs(ART, exist_ok=True)
    out = os.path.join(ART, "v221_crop_screen.html")
    open(out, "w").write(page)
    print(f"wrote {out} ({len(page) // 1024}KB, {len(sets)} sets)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--html-only", action="store_true")
    ap.add_argument("--recompute-matte", action="store_true")
    ap.add_argument("--workers", type=int, default=1,
                    help="parallel BiRefNet workers; >1 measured slower on 8GB")
    ap.add_argument("--refs-dir", action="append", default=None,
                    help="sweep arbitrary image dirs instead of the Testset2 "
                         "matrix; repeatable. Mattes are read from the shared "
                         "cache, so a GPU pre-pass (v2/crop_gpu.ipynb) makes "
                         "this near-instant")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    refs = load_refs_dir(a.refs_dir) if a.refs_dir else load_refs()
    log = os.path.join(OUT, "crop_log.csv")
    if a.html_only:
        rows = list(csv.DictReader(open(log)))
        for r in rows:
            for k in ("mask_area_frac", "confidence", "soft_edge_frac", "runtime_s"):
                r[k] = float(r[k])
            for k in ("crop_w", "crop_h", "src_w", "src_h"):
                r[k] = int(r[k])
            r["failed"] = r["failed"] == "True"
    else:
        matte_prepass(refs, a.workers, a.recompute_matte)
        rows = []
        for stem, p, kind, cat, pid, target in refs:
            r = process(stem, p, kind, cat, a.recompute_matte)
            r["target"] = target
            r["src_path"] = p
            rows.append(r)
            print(f"  {stem[:48]:48s} {r['route']:22s} area={r['mask_area_frac']:.3f} "
                  f"soft={r['soft_edge_frac']:.4f} {r['runtime_s']:6.1f}s "
                  f"{'FAIL' if r['failed'] else 'ok'}")
        with open(log, "w", newline="") as f:
            wcsv = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            wcsv.writeheader()
            wcsv.writerows(rows)
    html(rows)
