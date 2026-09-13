"""Candidate person-gates, measured on photographs whose answer is already known.

The gate runs on the uploaded garment photograph, before call 1, and decides one thing: is
there a person in it. A wrong "no person" sends a worn garment down a path that never removes
its wearer's head; a wrong "person" sends a flat-lay through a bald pass that invents one. The
second error only preserves today's behaviour, so the two are not equally bad and the tables
here keep them apart.

Every candidate is built from a model the crop ALREADY loads - Selfie Multiclass, MediaPipe
Pose, the SCHP ATR parser - so none of them adds a weight file or a download.

No generation happens here. This module measures; `CANDIDATES` turns measurements into
verdicts, and both the notebook and `v3/build/v313_page.py` import it so they cannot drift.
"""

# Selfie Multiclass channel order, as v3lib has it
BG, HAIR, BODY, FACE, CLOTHES, OTHER = range(6)
# ATR classes the parser calls head: hat, hair, sunglasses, face
ATR_HEAD = (1, 2, 3, 11)
NOSE, L_EAR, R_EAR, L_SH, R_SH = 0, 7, 8, 11, 12

FACE_PX = 500          # v3lib.tone's own test: fewer than this and it refuses to read a tone
VIS = 0.5              # the visibility floor used everywhere else in the pipeline
HEAD_FRAC = 0.02       # SCHP head pixels as a share of everything it labels

# name -> (verdict from a measurement, the number behind the verdict)
CANDIDATES = [
    ("HEAD selfie", lambda r: r["face_px"] + r["hair_px"] >= FACE_PX,
     lambda r: f'{r["face_px"] + r["hair_px"]:,} px'),
    ("FACE selfie", lambda r: r["face_px"] >= FACE_PX, lambda r: f'{r["face_px"]:,} px'),
    ("NOSE pose", lambda r: r["nose_vis"] >= VIS, lambda r: f'{r["nose_vis"]:.2f}'),
    ("FACE or NOSE", lambda r: r["face_px"] >= FACE_PX or r["nose_vis"] >= VIS,
     lambda r: f'{r["face_px"]:,} px / {r["nose_vis"]:.2f}'),
    ("HEAD parser", lambda r: r["schp_head_frac"] >= HEAD_FRAC,
     lambda r: f'{r["schp_head_frac"]:.1%}'),
    ("HEAD pose", lambda r: r["pose_ellipse"],
     lambda r: "ears+shoulders" if r["pose_ellipse"] else "-"),
]


def _mp_image(bgr):
    import cv2
    import numpy as np
    import mediapipe as mp
    return mp.Image(image_format=mp.ImageFormat.SRGB,
                    data=np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))


def measure(bgr, seg, pose, schp=None):
    """Every number every candidate needs, from one pass of each model.

    seg: a MediaPipe ImageSegmenter, pose: a PoseLandmarker, schp: an onnxruntime session for
    parsing_atr.onnx or None. Returns a plain dict so it can be written straight to JSON.
    """
    import cv2
    import numpy as np
    h, w = bgr.shape[:2]
    ch = [cv2.resize(m.numpy_view(), (w, h), interpolation=cv2.INTER_LINEAR)
          for m in seg.segment(_mp_image(bgr)).confidence_masks]
    out = {"face_px": int((ch[FACE] > 0.6).sum()), "hair_px": int((ch[HAIR] > 0.6).sum()),
           "body_px": int((ch[BODY] > 0.6).sum()), "px": h * w,
           "nose_vis": 0.0, "ear_vis": 0.0, "pose_ellipse": False,
           "schp_head_px": 0, "schp_subject_px": 0, "schp_head_frac": 0.0}
    res = pose.detect(_mp_image(bgr))
    if res.pose_landmarks:
        p = res.pose_landmarks[0]
        out["nose_vis"] = round(float(p[NOSE].visibility), 3)
        out["ear_vis"] = round(float(max(p[L_EAR].visibility, p[R_EAR].visibility)), 3)
        out["pose_ellipse"] = bool(min(p[L_EAR].visibility, p[R_EAR].visibility) >= VIS
                                   and min(p[L_SH].visibility, p[R_SH].visibility) >= VIS)
    if schp is not None:
        mean = np.array([0.406, 0.456, 0.485], np.float32)
        std = np.array([0.225, 0.224, 0.229], np.float32)
        x = cv2.resize(bgr, (512, 512), interpolation=cv2.INTER_LINEAR)
        x = ((x.astype(np.float32) / 255.0 - mean) / std).transpose(2, 0, 1)[None]
        lab = schp.run(None, {schp.get_inputs()[0].name: x})[0][0].argmax(0)
        total = int((lab > 0).sum())
        head = int(np.isin(lab, ATR_HEAD).sum())
        out.update(schp_head_px=head, schp_subject_px=total,
                   schp_head_frac=round(head / total, 4) if total else 0.0)
    return out


def score(rows):
    """Per candidate: the worn photographs it missed, and the flat-lays it missed."""
    table = {}
    for name, fn, _ in CANDIDATES:
        missed_worn = [r["stem"] for r in rows if r["truth"] == "person" and not fn(r)]
        missed_flat = [r["stem"] for r in rows if r["truth"] == "no_person" and fn(r)]
        table[name] = (missed_worn, missed_flat)
    return table
