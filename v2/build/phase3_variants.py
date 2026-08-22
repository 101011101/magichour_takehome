# Phase 3 reference conditioning — mannequin (M), ground (BG), auto-complete (AC).
#
# Free, local, CPU. Produces the crops a human inspects BEFORE any klein spend;
# each component is gated on that review (EXPERIMENT.md section 2c).
#
# This module does not modify garment_crop.py. It imports its primitives and
# recomputes the intermediate masks, because route_duo() returns only the four
# finished variants and M/AC need head, skin and the raw hair probability. Keeping
# the cropper untouched means every existing C1-C4 output stays byte-identical.
#
# Base for every variant is C3.1 (`noface` = subject - head), the arm that won
# phase 2. The three components attach at three different points:
#   M   replaces the PIXELS in the body region      (noface & skin)
#   BG  replaces the GROUND the alpha composites onto
#   AC  repairs the MASK+pixels the head cut removed (nofacehair - noface)
#
# Usage:
#   python v2/build/phase3_variants.py                    # all components, cohort refs
#   python v2/build/phase3_variants.py --only M --refs p021,p028
#   python v2/build/phase3_variants.py --only BG      # one component
import argparse
import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment_crop as G  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "v2", "runs", "phase3")
ART = os.path.join(REPO, "v2", "artifacts")

# The eleven references measured as losing garment area to the head cut
# (RESULTS.md, "Hair-removal damage"). p021 and woman_top_denim_skirt are the
# must-pass cases: worst overall, and the source of the one set no arm solved.
COHORT = ["p021", "dualuse_woman_top_denim_skirt_nonceleb", "p023",
          "dualuse_zendaya_white_blazer_skirt", "p012", "p019", "p028", "p030",
          "dualuse_scarlett_johansson_black_dress_backview_night", "p016", "p009"]

# ---- ground values -----------------------------------------------------------
# Achromatic throughout: a neutral ground cannot tint the garment, and has no
# periodic structure to be read as weave. Values are the documented shop-imagery
# ramp -- Zalando specifies #FFFFFF for packshots but #F1F1F1 for MODEL shots, and
# our cropped duo references are model shots being flattened to packshot white.
WHITE, SOFT = 255.0, 241.0            # #FFFFFF, #F1F1F1
RAMP = [241.0, 217.0, 200.0]          # #F1F1F1, #D9D9D9, #C8C8C8
DELTA_L = 15.0                        # required L* margin, garment border vs ground


def _l_star(v):
    """sRGB 0-255 grey -> CIE L*. Only valid for achromatic values, which is all
    we use; the ground is never allowed a hue."""
    y = v / 255.0
    y = y / 12.92 if y <= 0.04045 else ((y + 0.055) / 1.055) ** 2.4
    return 116.0 * (y ** (1 / 3.0)) - 16.0 if y > 0.008856 else 903.3 * y


def _lmap(bgr):
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    y = np.where(g <= 0.04045, g / 12.92, ((g + 0.055) / 1.055) ** 2.4)
    return np.where(y > 0.008856, 116.0 * np.cbrt(y) - 16.0, 903.3 * y)


PALE_MIN = 0.15   # share of garment that must be near-ground before the ground moves


def pale_stats(bgr, a, ground=None):
    """How much of the garment cannot be separated from the ground.

    NOT a median or a border statistic. An earlier version measured the median
    luminance in a band inside the boundary and it FAILED ITS OWN TEST CASE: p014,
    the one reference with a documented white-garment failure, is a white t-shirt
    over dark trousers -- median L*=57, 10th percentile L*=8, but 22% of the garment
    near-white. A single statistic over the whole garment averages the white region
    away. The failure is 'part of it is pale', so the measure has to be an AREA
    SHARE, not a central tendency."""
    gl = _l_star(WHITE if ground is None else ground)
    L = _lmap(bgr)
    sel = a > 0.5
    if sel.sum() < 50:
        return 0.0, 100.0
    close = (np.abs(L - gl) < DELTA_L) & sel
    frac = float(close.sum() / sel.sum())
    med = float(np.median(L[close])) if close.any() else float(np.median(L[sel]))
    return frac, med


def pick_ground(bgr, a):
    """BG3: keep white unless a meaningful share of the garment collides with it,
    then step down the neutral ramp until that share clears the margin. The common
    case must not regress to fix the rare one, so white is the default and the bar
    to move it is an area share, not a single pixel."""
    frac, med = pale_stats(bgr, a)
    if frac < PALE_MIN:
        return WHITE, f"{frac * 100:.0f}% of garment near white — under the {PALE_MIN * 100:.0f}% bar"
    for v in RAMP:
        f2, _ = pale_stats(bgr, a, v)
        if f2 < PALE_MIN:
            return v, (f"{frac * 100:.0f}% of garment collided with white "
                       f"(median L*={med:.0f}); at L*={_l_star(v):.0f} only {f2 * 100:.0f}% does")
    return RAMP[-1], f"{frac * 100:.0f}% collided with white; ramp floor"


def checker(shape, cell, lo=232.0, hi=255.0):
    """BG6. Large cells and low contrast deliberately: models have demonstrably
    learned checkerboard as something to DRAW (it is the canonical failure of
    'transparent background' requests), so a fabric-scale grid is a leakage risk."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    return np.where(((yy // cell) + (xx // cell)) % 2 == 0, hi, lo).astype(np.float32)


def contact_shadow(ground, a, strength=0.20, soft=0.018, drop=0.012):
    """BG5: WHITE ground plus a cast shadow, and nothing else.

    Decoupled from BG4 deliberately. BG4 changes the ground colour AND adds falloff
    AND adds a shadow, so if it wins we cannot say which part did the work. This arm
    isolates the shadow: the ground stays #FFFFFF, so nothing can tint the garment
    and the packshot convention is untouched, but the garment now sits ON something
    instead of floating. The boundary cue is created LOCALLY, at the silhouette,
    which is where the model looks for the garment -- and it works regardless of
    garment colour, including white-on-white, without a global distribution shift."""
    h, w = a.shape
    m = (a > 0.5).astype(np.float32)
    sh = cv2.GaussianBlur(m, (0, 0), max(h, w) * soft)
    sh = np.roll(sh, int(h * drop), axis=0)
    sh = np.clip(sh - m, 0, 1)
    g = ground if isinstance(ground, np.ndarray) else np.full((h, w), ground, np.float32)
    return g * (1.0 - strength * sh)


def falloff_and_shadow(ground, a, shape):
    """BG4. Real packshot white is PHOTOGRAPHED: ~95% albedo, a contact shadow and
    a luminance falloff. Our flat #FFFFFF is the degenerate case of it, and the
    falloff is exactly the separability cue that flatness deletes."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    g = ground * (1.0 - 0.05 * np.clip(r, 0, 1.4))
    sh = cv2.GaussianBlur((a > 0.5).astype(np.float32), (0, 0), max(h, w) * 0.02)
    sh = np.roll(sh, int(h * 0.012), axis=0)
    return g * (1.0 - 0.16 * np.clip(sh - (a > 0.5), 0, 1))


# ---- masks -------------------------------------------------------------------
def masks(bgr, stem, cranium=False):
    """Everything route_duo computes internally, returned. Same primitives, same
    order, same thresholds -- noface/clothes here equal C3.1/C4 on disk."""
    import mediapipe as mp
    h, w = bgr.shape[:2]
    prob, _ = G.biref_matte(bgr, stem, False)
    subject = G.drop_specks(prob)
    seg = G._multiclass()
    if seg is None:
        raise RuntimeError("multiclass unavailable")
    res = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB,
                               data=np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))))
    p = np.stack([cv2.resize(m.numpy_view(), (w, h), interpolation=cv2.INTER_LINEAR)
                  for m in res.confidence_masks])
    band = max(3, 0.010 * min(h, w))
    head = G.refine_band(bgr, p[G.HAIR] + p[G.FACE], band)
    face = G.refine_band(bgr, p[G.FACE], band)
    skin = G.refine_band(bgr, p[G.BODY], band)
    cranium_used = False
    parser_clothes = None
    if cranium:
        # anatomy first, appearance second: the ellipse always fires, the hair class
        # only adds what lies OUTSIDE the skull (long hair over the shoulders)
        # proper tool first; the pose ellipse and the face-anchored band survive
        # only as fallbacks for when the parser is unavailable or finds nothing
        pc = parser_classes(bgr, subject, clothes=p[G.CLOTHES])
        if pc is not None:
            # the parser supersedes the 256x256 selfie map for ALL THREE roles, so
            # head/garment/skin come from one consistent labelling
            head = np.clip(np.maximum(head, pc["head"]), 0, 1)
            skin = np.clip(np.maximum(skin * 0.0, pc["skin"]), 0, 1)
            parser_clothes = pc["garment"]
            cranium_used = True
        else:
            hp, ok = head_from_pose(bgr, subject, p[G.CLOTHES])
            if not ok:
                head, cranium_used = with_cranium(subject, head, face, p[G.CLOTHES])
            else:
                head, cranium_used = np.clip(np.maximum(head, hp), 0, 1), True
    noface = G.drop_specks(subject * (1.0 - head))
    nofacehair = G.drop_specks(subject * (1.0 - face))
    clothes = (G.drop_specks(noface * parser_clothes) if parser_clothes is not None
               else G.drop_specks(noface * (1.0 - skin)))
    return dict(subject=subject, head=head, face=face, skin=skin, noface=noface,
                cranium_used=cranium_used,
                nofacehair=nofacehair, clothes=clothes,
                hair_prob=np.clip(p[G.HAIR], 0, 1), face_prob=np.clip(p[G.FACE], 0, 1))


# ---- M: mannequin ------------------------------------------------------------
# The mannequin region is exactly `noface & skin` -- the wearer's visible body once
# the head is gone. Two failure risks pull opposite ways: read as clothing (wants
# contrast) and attracts attention (wants none). They are contrasts against
# DIFFERENT things -- sit close to the ground so the silhouette is quiet, stay
# separable from the garment so it is not read as cloth.
L_LO, L_HI = 116.0, 196.0             # the grey band; achromatic by construction


def _shaded(bgr, region):
    """M2 core: keep the shading that makes an arm read as a cylinder, destroy the
    hue that makes it read as a person. LAB with a/b zeroed is achromatic by
    construction, so no skin tone can survive."""
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    L = lab[..., 0]
    sel = region > 0.01
    if sel.sum() < 20:
        return bgr.copy()
    lo, hi = np.percentile(L[sel], [4, 96])
    if hi - lo < 1e-3:
        hi = lo + 1.0
    lab[..., 0] = np.clip((L - lo) / (hi - lo), 0, 1) * (L_HI - L_LO) + L_LO
    lab[..., 1] = 128.0
    lab[..., 2] = 128.0
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2BGR)


def _blend(base, repl, region):
    f = np.clip(region, 0, 1)[..., None]
    return (base.astype(np.float32) * (1 - f) + repl.astype(np.float32) * f).astype(np.uint8)


def mannequin(bgr, M, tag):
    """Returns (pixels, alpha). M3 blur, M4 face-smear and M5 head form were built
    and are held back to keep the arm count honest -- see EXPERIMENT.md 2c."""
    body = np.clip(M["noface"] * M["skin"], 0, 1)
    if tag == "M1":
        flat = np.full_like(bgr, int(round((L_LO + L_HI) / 2)))
        return _blend(bgr, flat, body), M["noface"]
    if tag == "M2":
        return _blend(bgr, _shaded(bgr, body), body), M["noface"]
    raise ValueError(tag)


# ---- AC: auto-complete -------------------------------------------------------
# The head cut takes garment area. Measured, that damage is almost entirely OPEN
# (connected to the background) rather than enclosed -- 19.52 of p021's 19.53
# points -- so this is silhouette repair, not hole filling. An enclosed hole is
# ringed by known fabric and inpainting is well posed; an open notch has garment on
# one side and background on the other, so filling it EXTENDS the silhouette with
# nothing constraining where the garment should end. AC1 (do not cut it) is
# therefore the principled fix and the rest are recovery.
def _lost(M):
    """What the head cut took: C3.2 minus C3.1. The region every AC arm addresses."""
    return np.clip(M["nofacehair"] - M["noface"], 0, 1)


def _feather_head(bgr, M):
    """Orthogonal preprocessing, not an arm. Erode the head mask and drop
    thin-strand regions: the measured damage is an OPEN boundary notch, not an
    enclosed hole, so not creating it beats repairing it. Composes with every arm."""
    k = max(3, int(min(bgr.shape[:2]) * 0.006) | 1)
    hm = (M["head"] > 0.5).astype(np.uint8)
    thick = cv2.morphologyEx(hm, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
    head = cv2.GaussianBlur(cv2.erode(thick, np.ones((3, 3), np.uint8)).astype(np.float32),
                            (0, 0), max(1.5, k * 0.35))
    return G.drop_specks(M["subject"] * (1.0 - np.clip(head, 0, 1)))


def _uncomposite(bgr, M):
    """AC1. Where hair is semi-transparent, I = a*F + (1-a)*B, so the garment pixel
    is recoverable: B = (I - a*F)/(1 - a). Reconstruction, not hallucination. Blows
    up as a->1, so it shrinks the damage to the opaque core and softens the
    boundary rather than removing it -- the two symptoms actually observed."""
    al = np.clip(M["hair_prob"], 0, 1) * (_lost(M) > 0.02)
    core = al >= 0.90
    F = (np.median(bgr[core].reshape(-1, 3), axis=0) if core.sum() > 40
         else np.array([40.0, 40.0, 40.0]))
    w = np.clip(al, 0, 0.88)[..., None]
    rec = np.clip((bgr.astype(np.float32) - w * F) / (1.0 - w), 0, 255)
    px = np.where((al > 0.02)[..., None] & ~core[..., None], rec, bgr).astype(np.uint8)
    a = G.drop_specks(np.clip(M["noface"] + (_lost(M) * (al < 0.90)), 0, 1))
    return px, a, core


def _fill(bgr, hole, how):
    """AC2-AC4. All three are zero-weight and therefore carry no licence exposure.
    Copy-based methods are expected to beat learned ones on patterned fabric: they
    reproduce a plaid where a 512-trained CNN approximates one."""
    if hole.sum() < 20:
        return bgr.copy(), "no region to fill"
    if how == "telea":
        return cv2.inpaint(bgr, hole, 7, cv2.INPAINT_TELEA), "Telea PDE"
    from cv2 import xphoto
    mode = {"fsr": xphoto.INPAINT_FSR_FAST, "shiftmap": xphoto.INPAINT_SHIFTMAP}[how]
    dst = bgr.copy()
    # xphoto wants the KEEP mask (255 = known), the inverse of the hole
    xphoto.inpaint(bgr, ((1 - hole) * 255).astype(np.uint8), dst, mode)
    return dst, {"fsr": "xphoto FSR", "shiftmap": "xphoto SHIFTMAP patch search"}[how]


# ---- AC5/AC6: learned fillers ------------------------------------------------
# PURGEABLE weights. Both are TorchScript, so neither needs hydra/omegaconf and
# both run on CPU at this scale (11 references = minutes, not the hours that put
# BiRefNet on Colab). Delete v2/runs/.models/purgeable/ when the comparison is done.
#
# Licence note carried from EXPERIMENT.md: LaMa's code is Apache-2.0 and MI-GAN's is
# MIT, but BOTH checkpoints are Places2-trained and the Places2 data terms say
# non-commercial. These arms exist to find out whether a learned filler is needed at
# all -- if AC1-AC4 match them, the question never has to be answered.
MODELS = os.path.join(REPO, "v2", "runs", ".models", "purgeable")
_JIT = {}


def _jit(name):
    if name not in _JIT:
        import torch
        p = os.path.join(MODELS, name)
        if not os.path.exists(p):
            return None
        m = torch.jit.load(p, map_location="cpu")
        m.eval()
        _JIT[name] = m
    return _JIT.get(name)


def _learned_fill(bgr, hole, which):
    """LaMa and MI-GAN both want a square power-of-two input and a binary mask.
    Work at 512: our holes are small-to-medium and both nets were trained near this
    scale, so upscaling the whole reference buys nothing and costs seconds."""
    import torch
    m = _jit("big-lama.pt" if which == "lama" else "migan.pt")
    if m is None:
        return bgr.copy(), f"{which} weights not present"
    h, w = bgr.shape[:2]
    S = 512
    img = cv2.resize(bgr, (S, S), interpolation=cv2.INTER_AREA)
    msk = (cv2.resize(hole, (S, S), interpolation=cv2.INTER_NEAREST) > 0).astype(np.float32)
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    with torch.no_grad():
        if which == "lama":
            t = torch.from_numpy(rgb).permute(2, 0, 1)[None]
            mt = torch.from_numpy(msk)[None, None]
            out = m(t, mt)
            arr = out[0].permute(1, 2, 0).numpy()
            arr = arr * 255.0 if arr.max() <= 1.01 else arr
        else:
            # MI-GAN's traced graph takes ONE 4-channel tensor, not (image, mask):
            # cat([keep - 0.5, image * keep]) with image in [-1,1] and keep=1 where
            # pixels are known. Output is [-1,1].
            keep = torch.from_numpy((1.0 - msk))[None, None]
            im = torch.from_numpy(rgb).permute(2, 0, 1)[None] * 2 - 1
            out = m(torch.cat([keep - 0.5, im * keep], 1))
            arr = (out[0].permute(1, 2, 0).numpy() + 1.0) / 2.0 * 255.0
    filled = cv2.cvtColor(np.clip(arr, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    filled = cv2.resize(filled, (w, h), interpolation=cv2.INTER_CUBIC)
    # hard-composite originals back: a net that round-trips the whole frame will
    # otherwise degrade fabric OUTSIDE the region it was asked to repair
    return np.where(hole[..., None] > 0, filled, bgr), (
        "big-lama TorchScript @512" if which == "lama" else "MI-GAN traced @512")


# ---- human parsing: the proper tool -------------------------------------------
# SegFormer-B2 fine-tuned on ATR (18 human-part classes). This replaces a geometric
# heuristic that had been patched seven times and was still trading references
# against each other: grow the ellipse and it catches the scalp but eats collars,
# shrink it and it protects collars but leaves scalp. That is a heuristic at its
# ceiling, not a tuning problem -- an ellipse cannot know where a head ends and a
# collar begins, because it has no notion of either.
#
# MediaPipe Selfie Multiclass, which the cropper has used throughout, is a
# lightweight SELFIE BACKGROUND segmenter with 6 coarse classes at 256x256. Human
# parsers are the purpose-built tool and are what VTON pipelines use to build
# agnostic masks. ATR's Face class covers the HEAD REGION rather than facial skin,
# which is exactly the property the bald case needs: measured on the bald frames it
# returns 10-17% of the person as head, the correct anatomical proportion, with
# hair ~0% as expected.
ATR = {"head": (1, 2, 3, 11),                    # hat, hair, sunglasses, face
       "garment": (4, 5, 6, 7, 8, 9, 10, 16, 17),
       "skin": (12, 13, 14, 15)}                 # legs, arms
_HP = {}

# Which parser backend. SCHP is the default because the SegFormer one is
# NON-COMMERCIAL: mattmdjaga/segformer_b2_clothes sets `license: other` pointing at
# the NVLabs SegFormer LICENSE, whose section 3.3 restricts the Work and any
# derivative works to "research or evaluation purposes only". The weights derive
# from NVIDIA's MiT-B2 backbone so the restriction propagates, and every
# SegFormer-lineage parser on HF inherits it -- including fashn-ai/fashn-human-parser.
# Third-party re-uploads tagging those weights mit/apache-2.0 are mislabels.
#
# SCHP (Self-Correction Human Parsing) is MIT (c) 2020 Peike Li, ResNet-101 backbone,
# no NVIDIA lineage, and emits the SAME 18 ATR classes -- so ATR below, the pose
# bound and the nose-connected-component rule are all unchanged.
#
# Set PARSER=segformer to compare against the incumbent; the numbers in
# prd/v2/v2.2/RESULTS.md were measured on it.
PARSER = os.environ.get("PARSER", "schp")

# SCHP normalises BGR with ImageNet statistics in BGR order, which is what the
# original repo does and looks reversed if you expect RGB.
_SCHP_MEAN = np.array([0.406, 0.456, 0.485], np.float32)
_SCHP_STD = np.array([0.225, 0.224, 0.229], np.float32)


def _parser():
    """The parsing backend, or None. Cached."""
    if "m" in _HP:
        return _HP["m"]
    os.environ.setdefault("HF_HOME", os.path.join(REPO, "v2", "runs", ".models", "hf"))
    try:
        if PARSER == "schp":
            import onnxruntime as ort
            from huggingface_hub import hf_hub_download
            _HP["m"] = ort.InferenceSession(
                hf_hub_download("basso4/humanparsing", "parsing_atr.onnx"),
                providers=["CPUExecutionProvider"])
            _HP["in"] = _HP["m"].get_inputs()[0].name
        else:
            import torch
            from transformers import (SegformerImageProcessor,
                                      AutoModelForSemanticSegmentation)
            name = "mattmdjaga/segformer_b2_clothes"
            _HP["proc"] = SegformerImageProcessor.from_pretrained(name)
            m = AutoModelForSemanticSegmentation.from_pretrained(name)
            m.eval()
            _HP["m"] = m
            _HP["torch"] = torch
    except Exception as e:
        print(f"  human parser ({PARSER}) unavailable ({str(e)[:70]})")
        _HP["m"] = None
    return _HP["m"]


def parse_human(bgr):
    """ATR class map at full resolution, or None. Identical 18-class output from
    either backend, so everything downstream is backend-agnostic."""
    m = _parser()
    if m is None:
        return None
    h, w = bgr.shape[:2]
    if PARSER == "schp":
        x = cv2.resize(bgr, (512, 512), interpolation=cv2.INTER_LINEAR)
        x = ((x.astype(np.float32) / 255.0 - _SCHP_MEAN) / _SCHP_STD)
        o = m.run(None, {_HP["in"]: x.transpose(2, 0, 1)[None]})[0][0]   # 18x128x128
        up = np.stack([cv2.resize(c, (w, h), interpolation=cv2.INTER_LINEAR) for c in o])
        return up.argmax(0).astype(np.uint8)
    torch = _HP["torch"]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    with torch.no_grad():
        o = m(**_HP["proc"](images=rgb, return_tensors="pt")).logits
    up = torch.nn.functional.interpolate(o, size=(h, w), mode="bilinear",
                                         align_corners=False)
    return up.argmax(1)[0].numpy().astype(np.uint8)


def _neck_line(bgr):
    """y of the neck, from pose landmarks. Between ears and shoulders, both
    detected, so it is measured rather than guessed."""
    import mediapipe as mp
    lm = _pose()
    if lm is None:
        return None
    h, w = bgr.shape[:2]
    r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                           data=np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))))
    if not r.pose_landmarks:
        return None
    p = r.pose_landmarks[0]
    ear_y = (p[L_EAR].y + p[R_EAR].y) / 2 * h
    sh_y = (p[L_SH].y + p[R_SH].y) / 2 * h
    nose = (p[NOSE].x * w, p[NOSE].y * h)
    return ear_y + (sh_y - ear_y) * 0.72, nose


def parser_classes(bgr, subject, clothes=None):
    """head / garment / skin, ALL from the parser. Returns None if unavailable.

    Taking all three from one model matters. A first version took head from the
    parser while leaving garment on MediaPipe, and the "garment lost" number then
    measured two models DISAGREEING rather than any real loss -- the parser calling
    a region head while the 256x256 selfie map called it clothes. Since the parser
    is the better model on exactly that question, the disagreement was being scored
    as damage. argmax also guarantees the classes are disjoint, so head can never
    overlap garment by construction."""
    seg = parse_human(bgr)
    if seg is None:
        return None
    sub = subject > 0.5
    out = {}
    for k, ids in ATR.items():
        m = np.isin(seg, ids) & sub
        if k == "head":
            # ATR's `face` class BLEEDS DOWN THE BODY on bald frames: the parser was
            # trained on people with hair, so a bald head above a bare neck and chest
            # reads as one continuous face region. Measured, the head class reached
            # 134% of the ear-to-shoulder span on p021, 292% on zendaya and 499% --
            # the bottom of the frame -- on p023.
            #
            # So each model does only what it is good at: the PARSER supplies the
            # SHAPE (the scalp boundary, which no heuristic could get), and POSE
            # supplies the EXTENT (where a head stops). Then the component containing
            # the nose is kept, so any disconnected skin blob elsewhere is dropped.
            # A raised COLLAR is a clothes region that a parser can read as head:
            # measured on p019, SCHP labels 99.1% of the collar `face` where
            # SegFormer labels 99.6% of it garment, and the collar sits ABOVE the
            # neck line so the pose bound does not reach it. Retuning that bound
            # trades p019 against p021 -- the same one-reference-for-another
            # signature that ended the geometric era -- so instead each model does
            # only what it is good at: the parser supplies the head SHAPE, pose the
            # EXTENT, and MediaPipe's clothes class vetoes anything it is confident
            # is garment. Set HEAD_CLOTHES_GUARD=0 to disable.
            if (clothes is not None
                    and os.environ.get("HEAD_CLOTHES_GUARD", "1") != "0"):
                m = m & (clothes < 0.5)

            nl = _neck_line(bgr)
            if nl is not None:
                cut, nose = nl
                m = m.copy()
                m[int(np.clip(cut, 0, bgr.shape[0] - 1)):] = False
                if m.any():
                    n, lab = cv2.connectedComponents(m.astype(np.uint8), 8)
                    k_ = lab[int(np.clip(nose[1], 0, bgr.shape[0] - 1)),
                             int(np.clip(nose[0], 0, bgr.shape[1] - 1))]
                    if k_ > 0:
                        m = lab == k_
        out[k] = np.clip(cv2.GaussianBlur(m.astype(np.float32), (0, 0), 2.0), 0, 1)
    return out if out["head"].sum() > 40 else None


def head_from_parser(bgr, subject):
    c = parser_classes(bgr, subject)
    return (c["head"], True) if c else (None, False)


# ---- head from pose: the general solution -------------------------------------
# The head is ANATOMY; hair is APPEARANCE. Conflating them is what broke the bald
# pipeline: the head mask was HAIR + FACE, so when the hair signal disappeared the
# head signal went with it and the cranium survived the cut.
#
# Pose landmarks do not depend on hair at all, so one rule covers every case:
#   bald        ellipse alone -- HAIR contributes nothing, and nothing is needed
#   short hair  ellipse alone -- short hair lies inside the skull ellipse
#   long hair   ellipse + HAIR class, for the part spilling onto the garment
#
# It also removes the failure that three geometric patches could not: the previous
# rule was "cut everything above the chin", which on p030 swept in a blob covering
# 36% of the subject and 60% clothes-class (raised arms). An ellipse is bounded on
# every side by anatomy, so nothing above or beside the head can be caught.
#
# MediaPipe Pose Landmarker lite, Apache-2.0, 5.8MB.
POSE_URL = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
            "pose_landmarker_lite/float16/1/pose_landmarker_lite.task")
POSE_PATH = os.path.join(REPO, "v2", "runs", ".models", "pose_landmarker_lite.task")
NOSE, L_EAR, R_EAR, L_SH, R_SH = 0, 7, 8, 11, 12


def _pose():
    if "pose" in _P_STATE:
        return _P_STATE["pose"]
    try:
        import urllib.request
        from mediapipe.tasks import python as mpp
        from mediapipe.tasks.python import vision
        os.makedirs(os.path.dirname(POSE_PATH), exist_ok=True)
        if not os.path.exists(POSE_PATH):
            urllib.request.urlretrieve(POSE_URL, POSE_PATH)
        _P_STATE["pose"] = vision.PoseLandmarker.create_from_options(
            vision.PoseLandmarkerOptions(
                base_options=mpp.BaseOptions(model_asset_path=POSE_PATH),
                running_mode=vision.RunningMode.IMAGE))
    except Exception as e:
        print(f"  pose unavailable ({str(e)[:70]})")
        _P_STATE["pose"] = None
    return _P_STATE["pose"]


_P_STATE = {}


def head_from_pose(bgr, subject, clothes_prob=None):
    """Skull ellipse from pose landmarks. Returns (mask, ok).

    Sized from ear separation, which is the skull width at ear level, with a
    fallback to the ear->shoulder distance when the ears are close together (a
    profile or three-quarter view collapses their horizontal separation)."""
    import mediapipe as mp
    lm = _pose()
    if lm is None:
        return None, False
    h, w = bgr.shape[:2]
    r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                           data=np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))))
    if not r.pose_landmarks:
        return None, False
    p = r.pose_landmarks[0]
    px = lambda i: (p[i].x * w, p[i].y * h)  # noqa: E731
    (lx, ly), (rx_, ry_) = px(L_EAR), px(R_EAR)
    (nx, ny) = px(NOSE)
    shy = (px(L_SH)[1] + px(R_SH)[1]) / 2.0
    ear_x, ear_y = (lx + rx_) / 2.0, (ly + ry_) / 2.0
    ear_sep = float(np.hypot(lx - rx_, ly - ry_))
    neck = abs(shy - ear_y)
    # SCALE FROM THE SILHOUETTE, not from ear separation alone. On p016 the two ear
    # landmarks came back 9px apart -- a profile or a bad detection collapses their
    # 2D separation -- and the ellipse was sized at 54px across for a much larger
    # head, so the scalp was missed. The silhouette's own width at ear level IS the
    # head width, needs no model, and cannot collapse this way.
    row = int(np.clip(ear_y, 0, h - 1))
    line = (subject[row] > 0.5)
    xs_on = np.where(line)[0]
    sil_w = 0.0
    if len(xs_on):
        c = int(np.clip((lx + rx_) / 2.0, 0, w - 1))
        # the run containing the ears, not the widest run in the row
        b = np.split(xs_on, np.where(np.diff(xs_on) > 1)[0] + 1)
        for seg in b:
            if seg[0] - 4 <= c <= seg[-1] + 4:
                sil_w = float(seg[-1] - seg[0])
                break
    # The silhouette width is only trustworthy when the row at ear level crosses the
    # HEAD; if the pose is tilted or the ears sit low it crosses the shoulders and
    # the estimate explodes. Cap its contribution by the neck length, which is an
    # independent landmark-derived scale -- a head is not much wider than the
    # ear-to-shoulder span.
    half_w = max(ear_sep * 0.78, neck * 0.62, min(sil_w * 0.58, neck * 0.95), 12.0)
    half_h = half_w * 1.28                      # skulls are taller than wide
    cy = ear_y - half_h * 0.18                  # the cranium sits above ear level
    cx = (ear_x + nx) / 2.0
    m = np.zeros((h, w), np.uint8)
    cv2.ellipse(m, (int(cx), int(cy)), (int(half_w), int(half_h)), 0, 0, 360, 1, -1)
    # A head ends at the NECK. Without this the ellipse reached below ear level far
    # enough to touch the chest -- p019 lost 4 points of clothes area and p028 one.
    # The neck sits between the ears and the shoulders, both of which are landmarks,
    # so the cut-off is measured rather than guessed.
    chin = int(ear_y + max(neck, 8.0) * 0.55)
    m[chin:] = 0
    keep = (subject > 0.5)
    # The clothes guard protects a collar or hood from being cut -- but applied to
    # the WHOLE ellipse it also protected misclassified scalp: on p019, 19.5% of the
    # head region came back as clothes-class and survived, leaving the crown behind.
    # A collar sits at the BOTTOM of the head region; the crown of a skull cannot be
    # clothing. So the guard applies only below ear level, which keeps the garment
    # protection that took p019 from -3.3 to -0.1 without shielding the scalp.
    if clothes_prob is not None:
        below = np.zeros_like(m, dtype=bool)
        below[int(np.clip(ear_y, 0, h - 1)):] = True
        keep = keep & ~((clothes_prob > 0.5) & below)
    a = cv2.GaussianBlur((m.astype(np.float32)) * keep, (0, 0), 2.0)
    return np.clip(a, 0, 1), True


# ---- cranium fix -------------------------------------------------------------
# The head mask is HAIR + FACE. On a BALD frame no HAIR class fires and the FACE
# class covers the face rather than the skull, so the cranium survives the cut --
# measured, head removal drops from 17-23% of the subject to 6.5-12.8% on the bald
# versions. Half the head stays in the crop.
#
# This also invalidated the first PRE measurement: "garment lost" was computed as
# C3.2 - C3.1 (face-only-removed minus hair-and-face-removed), and on a bald frame
# those two masks are nearly identical because there is no hair to separate them.
# The difference collapsed to ~0 BY CONSTRUCTION, so every bald frame scored ~0
# regardless of quality. The numbers measured nothing.
#
# Fix: find the neck geometrically and treat everything above it as head. Works
# whether or not hair is present, and is unioned with the class-based mask rather
# than replacing it, so haired references behave exactly as before.
def neck_row(subject, lo=0.06, hi=0.45):
    """Row index of the neck: the narrowest subject cross-section in the upper part
    of the figure, below the head's widest point. Returns None when no plausible
    neck is found, in which case the caller keeps the class-based mask alone."""
    m = (subject > 0.5).astype(np.uint8)
    ys = np.where(m.any(axis=1))[0]
    if len(ys) < 40:
        return None
    y0, y1 = int(ys[0]), int(ys[-1])
    h = y1 - y0
    a, b = y0 + int(h * lo), y0 + int(h * hi)
    if b - a < 8:
        return None
    w = m[a:b].sum(axis=1).astype(np.float32)
    if w.max() < 5:
        return None
    w = cv2.GaussianBlur(w.reshape(-1, 1), (1, 9), 0).ravel()
    k = int(np.argmin(w))
    head_max = w[:k].max() if k > 2 else 0
    # a neck is a genuine waist in the silhouette, not just the smallest row we
    # happened to scan: require it to be clearly narrower than the head above it
    if head_max < 5 or w[k] > 0.62 * head_max:
        return None
    return a + k


def with_cranium(subject, head, face, clothes_prob=None):
    """Union the class-based head mask with the skull.

    Anchored to the DETECTED FACE rather than to silhouette geometry. A first
    version looked for the neck as the narrowest cross-section and was not reliable
    -- it found no neck at all on p021 and p019, and barely moved zendaya or p012.
    The face is detected directly and the cranium sits immediately above it in the
    same horizontal band, so anchoring there works whether or not hair is present.

    Region taken: everything in the subject above the face's lower edge, within the
    face's x-range widened by a margin. Arms raised beside the head fall outside
    that band, and the result is unioned with the class mask so haired references
    are unchanged."""
    fm = (face > 0.4).astype(np.uint8)
    if fm.sum() < 60:
        return head, False
    ys, xs = np.where(fm > 0)
    fy1 = int(np.percentile(ys, 97))          # bottom of the face (chin)
    fx0, fx1 = int(np.percentile(xs, 2)), int(np.percentile(xs, 98))
    fy0 = int(np.percentile(ys, 3))
    fw, fh = max(fx1 - fx0, 8), max(fy1 - fy0, 8)
    m = int(fw * 0.42)
    # VERTICAL BOUND. Without it the band ran from the top of the frame down to the
    # chin, which on p030 was 71% of the image for a head occupying about a third of
    # that -- 394 extra rows of subject, and only 46% of the over-reach was
    # clothes-class so the clothes guard could not catch the rest. A human head is
    # roughly 1.5-1.8x the face box from chin to crown, so the crown cannot be above
    # this line. Anatomy is a much tighter constraint than "everything above the
    # chin", and it is the same constraint on every reference.
    top = max(0, fy1 - int(1.8 * fh))
    # ELLIPSE, not a rectangle. A bounded rectangle still caught neck and shoulder
    # corners near the chin -- p030 kept losing ~5 points of clothes area to the
    # bottom corners of the box. A skull is an ellipse, so using one removes the
    # corners that were never head in the first place.
    head_h = fy1 - top
    band = np.zeros_like(fm)
    cv2.ellipse(band, ((fx0 + fx1) // 2, int(fy1 - head_h * 0.52)),
                (int((fw / 2 + m) * 0.95), int(head_h * 0.56)), 0, 0, 360, 1, -1)
    skull = (band > 0) & (subject > 0.5)
    if skull.sum() < 40:
        return head, False
    skull = G.largest_cc((skull.astype(np.uint8) * 255)) > 0
    # A cranium is never clothing. Subtracting the clothes class makes garment loss
    # impossible BY CONSTRUCTION rather than by tuning the band: without this the
    # face-anchored region over-reached and cost p028 10 points of clothes area and
    # p030 17. The guard is exact, not a threshold.
    if clothes_prob is not None:
        skull = skull & (clothes_prob <= 0.5)
    if skull.sum() < 40:
        return head, False
    soft = cv2.GaussianBlur(skull.astype(np.float32), (0, 0), 2.0)
    return np.clip(np.maximum(head, soft), 0, 1), True


# ---- PRE: repair BEFORE cropping ---------------------------------------------
# A different architecture from AC, not another arm of it.
#
#   AC   crop -> damage exists -> fill the damage
#   PRE  repair the RAW photo -> crop normally -> damage never exists
#
# Why PRE should win, stated before the run so it is a prediction and not a
# rationalisation: AC asks a model to fill a WHITE HOLE IN A CROP -- out of
# distribution, no surrounding context, and white-read-as-cloth is the exact failure
# this workstream exists to fix. PRE asks for an edit on a WHOLE PHOTOGRAPH OF A
# PERSON, which is in distribution, and the model keeps the entire body as context
# for what the garment under the hair should look like. The head cut then has
# nothing to take, so the fringe never exists rather than being removed afterwards.
#
# PRE1 is deterministic-ish (LaMa over the hair region, no prompt); PRE2/PRE3 are
# prompted ("make this person bald"). All three then run the UNCHANGED cropper, so
# the only variable is the raw image it receives.
def hair_region(M, grow=6):
    """Hair pixels that overlap the garment -- what PRE has to remove from the raw
    image. Grown slightly so the fill covers the soft boundary too."""
    hp = M["hair_prob"] > 0.25
    over = hp & (M["nofacehair"] > 0.5)
    k = np.ones((2 * grow + 1,) * 2, np.uint8)
    return cv2.dilate(over.astype(np.uint8), k)


def pre_lama(bgr, M):
    """PRE1 -- LaMa fills the hair away in the RAW frame, with the whole body as
    context. Then the normal cropper runs on the result."""
    hole = hair_region(M)
    if hole.sum() < 50:
        return bgr.copy(), "no hair over garment"
    px, note = _learned_fill(bgr, hole, "lama")
    return px, f"LaMa over {hole.mean() * 100:.1f}% of frame ({note})"


# ---- deliberate over-crop ----------------------------------------------------
# The head cut leaves a HAIR FRINGE inside the kept garment: measured at 0.08-2.66%
# of garment area across the cohort, and DARKER than the garment in every case
# (p021 fringe L*=25 vs garment L*=46; zendaya 49 vs 92). On a white ground that
# reads as a dark rim tracing the cut -- exactly the kind of edge klein can take for
# piping or trim.
#
# The algebra is not skipping it: 100% of fringe pixels fall inside the a in
# (0.02, 0.90) window it operates on. It UNDERCORRECTS, because un-compositing uses
# one global hair colour taken from the opaque core, and where dark hair meets dark
# fabric the correction is too small to erase the rim.
#
# So: cut wider on purpose and let AC fill it back. Trading a known, fillable gap
# for an unknown contamination is the better trade only if AC works -- which is
# precisely what the AC arms are measuring.
def overcrop(M, pct=5.0, max_r=60):
    """Dilate the head mask until the EXTRA garment removed is `pct` percent of the
    C3.2 garment area. Solved per reference rather than applied as a fixed radius,
    because a fixed radius means wildly different amounts on a 500px and a 1500px
    reference. Returns (alpha, radius_used, actual_pct)."""
    base = M["nofacehair"] > 0.5
    tot = float(base.sum()) or 1.0
    already = float(((M["nofacehair"] > 0.5) & (M["noface"] <= 0.5)).sum()) / tot * 100.0
    target = already + pct
    head = (M["head"] > 0.5).astype(np.uint8)
    lo, hi, best = 0, max_r, None
    while lo <= hi:                      # binary search on the dilation radius
        r = (lo + hi) // 2
        h2 = cv2.dilate(head, np.ones((2 * r + 1,) * 2, np.uint8)) if r else head
        a = G.drop_specks(M["subject"] * (1.0 - h2.astype(np.float32)))
        got = float((base & (a <= 0.5)).sum()) / tot * 100.0
        best = (a, r, got)
        if got < target:
            lo = r + 1
        else:
            hi = r - 1
        if r == 0 and got >= target:
            break
    return best


def overcrop_fringe(M, margin=4):
    """OCF -- dilate just past the measured contamination band instead of hitting an
    area target. The area target proved INVERSELY related to the defect: p016 has the
    largest fringe (4.69%) and solved to 5px, while p023 has almost none (0.29%) and
    solved to 60px, because an area target is driven by head-mask perimeter rather
    than by contamination. This scales with the defect instead of against it."""
    fr = fringe_mask(M)
    if not fr.any():
        return M["noface"], 0, 0.0
    # radius that covers the fringe band: its thickness, plus a small margin
    d = cv2.distanceTransform((fr > 0).astype(np.uint8), cv2.DIST_L2, 3)
    r = int(min(30, max(3, np.percentile(d[fr], 95) * 2 + margin)))
    head = cv2.dilate((M["head"] > 0.5).astype(np.uint8), np.ones((2 * r + 1,) * 2, np.uint8))
    a = G.drop_specks(M["subject"] * (1.0 - head.astype(np.float32)))
    base = M["nofacehair"] > 0.5
    got = float((base & (a <= 0.5)).sum()) / max(float(base.sum()), 1.0) * 100.0
    return a, r, got


def fringe_mask(M, band=9):
    """Hair-contaminated pixels that SURVIVE the cut, in a band inside the boundary.
    Rendered on the page so the defect is visible rather than asserted."""
    keep = M["noface"] > 0.5
    edge = keep & (cv2.dilate((~keep).astype(np.uint8), np.ones((band, band), np.uint8)) > 0)
    return (edge & (M["hair_prob"] > 0.15))


def autocomplete(bgr, M, tag, feather=False):
    """Returns (pixels, alpha, note). Base alpha is C3.1 unless the arm widens it."""
    if isinstance(feather, np.ndarray):        # an explicit over-cropped alpha
        base = feather
    elif feather:
        base = _feather_head(bgr, M)
    else:
        base = M["noface"]
    if tag == "AC0":
        return bgr.copy(), base, "unrepaired control"
    if tag == "AC1":
        px, a, core = _uncomposite(bgr, M)
        if feather:
            a = np.clip(a + base, 0, 1)
        return px, a, f"un-composited a<0.90; opaque core {core.mean() * 100:.2f}% left open"
    if tag in ("AC5", "AC6"):
        hole = cv2.dilate((_lost(M) > 0.02).astype(np.uint8), np.ones((3, 3), np.uint8))
        px, note = _learned_fill(bgr, hole, "migan" if tag == "AC5" else "lama")
        a = G.drop_specks(np.clip(base + _lost(M), 0, 1))
        return px, a, note
    if tag in ("AC2", "AC3", "AC4"):
        # every fill arm gets the SAME region and the SAME starting pixels, so the
        # only variable is the fill method
        hole = cv2.dilate((_lost(M) > 0.02).astype(np.uint8), np.ones((3, 3), np.uint8))
        how = {"AC2": "telea", "AC3": "fsr", "AC4": "shiftmap"}[tag]
        px, note = _fill(bgr, hole, how)
        px = np.where(hole[..., None] > 0, px, bgr)
        a = G.drop_specks(np.clip(base + _lost(M), 0, 1))
        return px, a, note
    raise ValueError(tag)


# ---- flatten -----------------------------------------------------------------
def flatten(crop, a, ground):
    f = np.clip(a, 0, 1)[..., None].astype(np.float32)
    g = ground if isinstance(ground, np.ndarray) else np.float32(ground)
    if isinstance(g, np.ndarray) and g.ndim == 2:
        g = g[..., None]
    return np.clip(crop.astype(np.float32) * f + g * (1.0 - f), 0, 255).astype(np.uint8)


def grounds(crop, a):
    """BG1-BG4 for one already-composited alpha. Returns [(tag, image, note)].

    Achromatic throughout: a neutral ground cannot tint the garment and has no
    periodic structure to be read as weave. The checkerboard arm was cut -- models
    have learned checkerboard as something to DRAW, which makes it a leakage risk
    rather than an erasure instruction (EXPERIMENT.md 2c)."""
    h, w = a.shape
    v, why = pick_ground(crop, a)
    frac, med = pale_stats(crop, a)
    spec = [("BG1", WHITE, "#FFFFFF -- control, ships today"),
            ("BG2", SOFT, "#F1F1F1 -- shop-imagery model-shot spec"),
            ("BG3", v, f"adaptive -> #{int(v):02X}{int(v):02X}{int(v):02X}; {why}"),
            ("BG4", falloff_and_shadow(np.full((h, w), v, np.float32), a, (h, w)),
             f"#{int(v):02X}{int(v):02X}{int(v):02X} + falloff + contact shadow"),
            ("BG5", contact_shadow(WHITE, a),
             "#FFFFFF + contact shadow ONLY — isolates the shadow from the colour change")]
    out = [(t, flatten(crop, a, g), n) for t, g, n in spec]
    return out, {"pale_pct": round(frac * 100, 1), "pale_median_L": round(med, 1),
                 "pick": int(v), "fires": bool(v != WHITE)}


def crop_and_alpha(stem):
    """The C3.1 alpha PNG carries the UNFLATTENED crop in its BGR channels and the
    real alpha in A -- so crop and mask are aligned by construction. An earlier
    calibration read the full source image instead and resized it onto the crop
    dimensions, which misaligned the band and made a black blazer measure L*=95."""
    f = os.path.join(REPO, "v2", "runs", "crop_screen", f"{stem}__c3_no_face_alpha.png")
    if not os.path.exists(f):
        return None, None
    im = cv2.imread(f, cv2.IMREAD_UNCHANGED)
    if im is None or im.ndim < 3 or im.shape[2] < 4:
        return None, None
    return im[..., :3].copy(), (im[..., 3].astype(np.float32) / 255.0)


def pale_cohort(limit=10):
    """BG's own reference list: the garments that white fails to separate. Selected
    by measurement rather than by eye, because the failure is a luminance margin."""
    import csv
    log = os.path.join(REPO, "v2", "runs", "crop_screen", "crop_log.csv")
    rows = []
    for r in csv.DictReader(open(log)):
        crop, a = crop_and_alpha(r["stem"])
        if crop is None:
            continue
        frac, _ = pale_stats(crop, a)
        rows.append((round(frac * 100, 1), r["stem"]))
    rows.sort(reverse=True)
    return [s for _, s in rows[:limit]], rows


# ---- synthetic bed -----------------------------------------------------------
def punch(shape, mask, seed, n=3):
    """Known holes in intact fabric. Deterministic per reference so a re-run
    reproduces. Shapes are elongated and irregular to resemble a hair sweep rather
    than a tidy disc, which would flatter the fills."""
    rng = np.random.RandomState(seed)
    h, w = shape
    ys, xs = np.where(mask > 0.5)
    hole = np.zeros((h, w), np.uint8)
    if len(ys) < 500:
        return hole
    for _ in range(n):
        i = rng.randint(len(ys))
        cy, cx = int(ys[i]), int(xs[i])
        ax = int(max(14, min(h, w) * rng.uniform(0.075, 0.16)))
        cv2.ellipse(hole, (cx, cy), (ax, int(ax * rng.uniform(0.30, 0.75))),
                    float(rng.uniform(0, 180)), 0, 360, 1, -1)
    hole = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 1.2)
    return ((hole > 0.35) & (mask > 0.5)).astype(np.uint8)


def synthetic(stem, seed):
    """before / repaired / TRUTH triples. The point of this bed is that the fabric
    that was actually there can be looked at -- on real hair damage nobody knows the
    answer, so the reviewer can only judge plausibility. AC1 is absent by
    construction: an opaque punched hole has no semi-transparent pixels to
    un-composite, so the algebra is a mathematical no-op here."""
    crop, a = crop_and_alpha(stem)
    if crop is None:
        return None
    hole = punch(a.shape, a, seed)
    if hole.sum() < 200:
        return None
    damaged = np.where(hole[..., None] > 0, 255, crop).astype(np.uint8)
    out = {"truth": flatten(crop, a, WHITE),
           "damaged": flatten(damaged, a, WHITE),
           "hole_pct": float(hole.sum() / max((a > 0.5).sum(), 1) * 100)}
    for tag, how in (("AC2", "telea"), ("AC3", "fsr"), ("AC4", "shiftmap")):
        px, note = _fill(damaged, hole, how)
        px = np.where(hole[..., None] > 0, px, crop)
        out[tag] = flatten(px, a, WHITE)
        out[f"note_{tag}"] = note
    # the learned arms matter MOST here: a convincing-but-wrong fill is their
    # failure mode, and only the truth panel catches it
    for tag, which in (("AC5", "migan"), ("AC6", "lama")):
        px, note = _learned_fill(damaged, hole, which)
        px = np.where(hole[..., None] > 0, px, crop)
        out[tag] = flatten(px, a, WHITE)
        out[f"note_{tag}"] = note
    return out


# ---- driver ------------------------------------------------------------------
M_TAGS = ["M1", "M2"]
AC_TAGS = ["AC0", "AC1", "AC2", "AC3", "AC4", "AC5", "AC6"]


def _save(stem, tag, img):
    G.write_rgb(os.path.join(OUT, f"{stem}__{tag}.jpg"), img)


def run_m(stems, meta):
    rows = []
    for stem in stems:
        bgr = cv2.imread(meta[stem], cv2.IMREAD_COLOR)
        M = masks(bgr, stem)
        x0, y0, x1, y1 = G.bbox_of((M["subject"] > 0.5).astype(np.uint8), bgr.shape[:2])
        crop = bgr[y0:y1, x0:x1]
        _save(stem, "M0", flatten(crop, M["noface"][y0:y1, x0:x1], WHITE))
        for t in M_TAGS:
            px, a = mannequin(bgr, M, t)
            _save(stem, t, flatten(px[y0:y1, x0:x1], a[y0:y1, x0:x1], WHITE))
        body = float((M["noface"] * M["skin"] > 0.5).sum() / max((M["noface"] > 0.5).sum(), 1) * 100)
        rows.append({"stem": stem, "body_pct": round(body, 1)})
        print(f"  M   {stem:52} body {body:5.1f}%")
    return rows


def run_bg(stems, meta):
    rows = []
    for stem in stems:
        crop, a = crop_and_alpha(stem)
        if crop is None:
            print(f"  BG  {stem}: no crop artifact, skipped")
            continue
        imgs, d = grounds(crop, a)
        for t, img, note in imgs:
            _save(stem, t, img)
            d[f"note_{t}"] = note
        d["stem"] = stem
        rows.append(d)
        print(f"  BG  {stem:52} pale {d['pale_pct']:5.1f}% -> "
              f"{'GREY #%02X' % d['pick'] if d['fires'] else 'white'}")
    return rows


def run_ac(stems, meta, feather=False):
    rows = []
    for i, stem in enumerate(stems):
        bgr = cv2.imread(meta[stem], cv2.IMREAD_COLOR)
        M = masks(bgr, stem)
        x0, y0, x1, y1 = G.bbox_of((M["subject"] > 0.5).astype(np.uint8), bgr.shape[:2])
        rec = {"stem": stem,
               "lost_pct": round(float(_lost(M).sum() / max(M["nofacehair"].sum(), 1) * 100), 2)}
        for t in AC_TAGS:
            px, a, note = autocomplete(bgr, M, t, feather)
            _save(stem, t, flatten(px[y0:y1, x0:x1], a[y0:y1, x0:x1], WHITE))
            rec[f"note_{t}"] = note
        # feathering is orthogonal preprocessing, reported as on/off not as an arm
        px, a, _ = autocomplete(bgr, M, "AC0", True)
        _save(stem, "ACfeather", flatten(px[y0:y1, x0:x1], a[y0:y1, x0:x1], WHITE))
        # The synthetic punched bed is DELIBERATELY NOT RUN (2026-08-17). It tested
        # enclosed holes in intact fabric, which is not the defect we have: the real
        # damage is an OPEN boundary notch left by the head cut. Scoring fills on a
        # hole shape that never occurs would have rewarded the wrong behaviour, and
        # having ground truth is not worth measuring the wrong thing. `synthetic()`
        # is retained unused in case a genuine enclosed-hole case appears.
        rows.append(rec)
        print(f"  AC  {stem:52} lost {rec['lost_pct']:5.2f}%")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["M", "BG", "AC"])
    ap.add_argument("--refs", help="comma-separated stems; default is the measured cohort")
    ap.add_argument("--feather", action="store_true", help="head-mask feathering on")
    a = ap.parse_args()

    import csv
    log = os.path.join(REPO, "v2", "runs", "crop_screen", "crop_log.csv")
    meta = {r["stem"]: r["src_path"] for r in csv.DictReader(open(log))}
    os.makedirs(OUT, exist_ok=True)
    stems = a.refs.split(",") if a.refs else COHORT
    from phase3_page import page_m, page_bg, page_ac

    if a.only in (None, "M"):
        print(f"{chr(10)}M -- mannequin, {len(stems)} refs")
        print("  page:", os.path.relpath(page_m(stems, run_m(stems, meta)), REPO))
    if a.only in (None, "BG"):
        pale, ranked = pale_cohort()
        print(f"{chr(10)}BG -- ground, pale cohort selected by margin: {', '.join(pale[:5])} ...")
        print("  page:", os.path.relpath(page_bg(pale, run_bg(pale, meta), ranked), REPO))
    if a.only in (None, "AC"):
        print(f"{chr(10)}AC -- auto-complete, {len(stems)} refs")
        import json
        fn = os.path.join(OUT, "_fal_notes.json")
        fal = json.load(open(fn)) if os.path.exists(fn) else {}
        print("  page:", os.path.relpath(page_ac(stems, run_ac(stems, meta, a.feather), fal), REPO))


if __name__ == "__main__":
    main()
