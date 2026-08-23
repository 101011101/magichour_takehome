"""The V2 virtual try-on harness, assembled.

    from pipeline import HarnessConfig, run
    res = run("person.jpg", "garment.jpg", HarnessConfig(high_resolution=True))

Pipeline, in order:

    1  preprocess the garment reference   BiRefNet + SegFormer/ATR + MediaPipe Pose
    2  route                              hair-over-garment -> PHEAD or BC_klein
    3  generate                           klein 4B distilled
    4  screen                             input comparison, then the VLM
       escalate                           -> QX, take QX unconditionally
    5  realism (optional)                 SeedVR2 x2, Lanczos fallback

Design decisions that are load-bearing and easy to undo by accident:

  * Escalation switches MECHANISM, never seed. Failure is a property of the garment
    -- a damaged reference failed on all three people it was paired with -- so a
    re-roll reproduces it.
  * The VLM must see the GARMENT REFERENCE, not only the output. Every output-only
    prompt scored at the do-nothing baseline; only the reference-aware one beat it.
  * Escalation always lands on QX. A pairwise "which is better" VLM call was built
    and measured at 34% self-consistency under image swap; it picked the already
    failed arm 2 times in 5. Taking QX unconditionally scores 5/5.
  * The deterministic checks are NOT redundant with the VLM. Over 114 cells the
    VLM caught 26 failures the checks missed, the checks caught 1 the VLM missed --
    and that 1 was the only frame that shipped broken. Identity swaps and no-ops are
    coherent photographs of the wrong thing; a semantic judge has nothing to find.
  * Every stage passes its input through unchanged if it cannot do its job. No
    stage may emit a broken image.

Rationale and measurements: prd/v2/ARCHITECTURE.md, prd/v2/DECISIONS.md.
"""
import os
from dataclasses import dataclass, field
from typing import Optional, List

from .config import HarnessConfig

PHEAD, BC, QX = "PHEAD", "BC_klein", "QX_qwen_p1"
GENERATIONS = {PHEAD: 1, BC: 2, QX: 2}


@dataclass
class Result:
    image_path: str
    arm: str
    generations: int
    escalated: bool = False
    route_reason: str = ""
    gate_reason: str = ""
    upscaled: str = "off"          # off | seedvr2 | lanczos
    identity_cos: Optional[float] = None
    hair_over_garment: Optional[float] = None
    trace: List[str] = field(default_factory=list)

    def log(self, msg):
        self.trace.append(msg)
        return self


# --------------------------------------------------------------------------
# stage 1-2: preprocessing and routing
# --------------------------------------------------------------------------
def hair_over_garment(garment_path):
    """Share of the garment crop that hair removal destroys: (C3.2 - C3.1) / C3.2.

    Not a proxy -- it is the pixel area itself, and a free byproduct of masks the
    cropper already computes. Predicts PHEAD failure at AUC 0.862, against 0.38-0.57
    for every check that reads the OUTPUT instead of the input.
    """
    from . import masks
    c31 = masks.crop(garment_path, keep_hair=False)
    c32 = masks.crop(garment_path, keep_hair=True)
    a31, a32 = masks.area(c31), masks.area(c32)
    if a32:
        return max(0.0, (a32 - a31) / a32)
    # No prepared crop on disk -- an unseen garment, or a checkout without
    # v2/runs/. Compute it. Returning 0.0 here silently routes EVERY request to
    # PHEAD, which is what happened on the first self-hosted run and is worse than
    # failing loudly.
    return masks.hair_from_raw(garment_path)


def route(garment_path, cfg):
    """Which arm to start with. Reads the INPUT, which is where the signal is."""
    if cfg.garment_region:
        return QX, f"caller named a region ({cfg.garment_region!r})", None
    h = hair_over_garment(garment_path)
    if h >= cfg.hair_threshold:
        return BC, f"hair over garment {h:.1%} >= {cfg.hair_threshold:.0%}", h
    return PHEAD, f"hair over garment {h:.1%} < {cfg.hair_threshold:.0%}", h


# --------------------------------------------------------------------------
# stage 4: the screen
# --------------------------------------------------------------------------
def input_comparison(out_path, person_path, cfg):
    """Deterministic checks against the PERSON INPUT. Runs before the VLM.

    The composite deterministic gate failed as a scorer -- AUC 0.506 against the
    reviewer, a coin flip -- but two of its five checks survive as detectors:
    precise, very low recall, and covering exactly the blind spot a semantic judge
    has by construction.

    Both catch the same shape of failure: an output that is a competent, coherent
    photograph of the WRONG THING. A no-op is the person unchanged; an identity swap
    is a different person entirely. Neither looks broken, so every output-only VLM
    prompt correctly calls them clean -- and on the one measured identity swap, so
    did the prompt that was shown the person photo and asked directly. Only a
    numeric comparison against the input reveals them.

    Recall is 7% against the VLM's 65%. That is not the point: over 114 cells these
    checks caught exactly one thing the VLM did not, and it was the only frame that
    shipped broken. They cost nothing -- CPU, already loaded, no API call.
    """
    from . import checks
    if checks.degenerate(out_path):
        return True, "degenerate frame"
    if checks.noop(out_path, person_path) < cfg.noop_floor:
        return True, "no-op: output is the person input unchanged"
    # NOT a raw cosine. checks.identity_margin wraps failure_gate.check_identity,
    # which returns _norm(cos, 0.18, 0.42) -- the same normalised scale the 0.90
    # threshold was validated on. A raw cosine between the same person across a
    # generative edit runs 0.80-0.92, so a 0.90 raw threshold fires on almost
    # everything; the equivalent margin is 1.000. The two scales look alike and
    # are not, which cost a whole Colab run.
    m = checks.identity_margin(out_path, person_path)
    if m is not None and m < cfg.identity_escalate:
        return True, f"identity margin {m:.3f} < {cfg.identity_escalate}: wrong person"
    return False, ""


def vlm_screen(out_path, garment_path, cfg):
    """Escalate? Two prompts on one open-weights VLM.

    `garment` is the only prompt that beat the do-nothing baseline (70.2% vs 62.3%)
    and it is the only one that sees the reference image. Do NOT ask about
    artefacts: that prompt returned CLEAN on all 114 test outputs and never fired,
    because these failures are not artefacts -- they are competent photographs of
    the wrong thing.
    """
    from . import vlm
    g = vlm.ask(vlm.GARMENT, cfg, out_path, garment_path)
    if g == "FAIL":
        return True, "vlm garment == FAIL"
    if cfg.quality == "safe":
        t = vlm.ask(vlm.TRYON, cfg, out_path)
        if t != "PERFECT":
            return True, f"vlm tryon == {t}"
    return False, ""


# --------------------------------------------------------------------------
# stage 5: realism, optional
# --------------------------------------------------------------------------
def realism(frame_path, cfg, res):
    """Only when the caller asked for resolution.

    The identity floor decides HOW to upscale, never WHETHER to: the caller asked
    for resolution, so a failure falls back to a deterministic Lanczos x2 rather
    than handing back the original. Run unconditionally over the 38 shipped frames
    the generative pass cost identity on 7, worst 0.772 -- inside the range that
    eliminated Z-Image Turbo in v2.1.
    """
    from . import upscale
    if not cfg.high_resolution:
        return frame_path, "off", None
    out = upscale.seedvr2(frame_path, cfg)
    if out is None:
        res.log("seedvr2 unavailable, falling back to lanczos")
        return upscale.lanczos(frame_path), "lanczos", None
    cos = upscale.identity_cos(frame_path, out)
    if cos is not None and cos < cfg.identity_floor:
        res.log(f"identity {cos:.3f} < {cfg.identity_floor}, discarding seedvr2")
        return upscale.lanczos(frame_path), "lanczos", cos
    return out, "seedvr2", cos


# --------------------------------------------------------------------------
def run(person_path, garment_path, cfg=None):
    """One request, end to end."""
    cfg = (cfg or HarnessConfig()).validate()
    from . import arms

    for p in (person_path, garment_path):
        if not os.path.exists(p):
            raise FileNotFoundError(p)

    arm, why, hair = route(garment_path, cfg)
    res = Result(image_path="", arm=arm, generations=GENERATIONS[arm],
                 route_reason=why, hair_over_garment=hair)
    res.log(f"route -> {arm}: {why}")

    out = arms.generate(arm, person_path, garment_path, cfg)
    res.log(f"{arm} produced {os.path.basename(out)}")

    if arm != QX:
        fired, reason = input_comparison(out, person_path, cfg)
        if not fired:
            fired, reason = vlm_screen(out, garment_path, cfg)
        if fired:
            res.log(f"escalating: {reason}")
            out = arms.generate(QX, person_path, garment_path, cfg)
            res.arm, res.escalated, res.gate_reason = QX, True, reason
            res.generations += GENERATIONS[QX]
        else:
            res.log("gate clean, shipping the first arm")

    out, how, cos = realism(out, cfg, res)
    res.image_path, res.upscaled, res.identity_cos = out, how, cos
    res.log(f"realism: {how}" + (f" (identity {cos:.3f})" if cos else ""))
    return res
