"""Logic tests. No GPU, no API key, no network.

These cover the decisions the harness makes, not the models it calls. Three of them
are regressions for bugs that each cost a whole run, and are the reason this file
exists at all:

    test_hair_from_raw_raises_rather_than_zero   the router silently disabled itself
    test_identity_scales_are_distinct            a margin was compared to a cosine
    test_escalation_never_reseeds                the failure is in the garment
"""
import sys
import types

import pytest

from pipeline import HarnessConfig, harness
from pipeline.harness import BC, GENERATIONS, PHEAD, QX, Result


# --------------------------------------------------------------------- config
def test_defaults_are_the_documented_ones():
    c = HarnessConfig()
    assert c.quality == "safe"
    assert c.high_resolution is False      # realism serves resolution, not quality
    assert c.hair_threshold == 0.14
    assert c.seed == 46                    # fixed: a reseed reproduces the failure


@pytest.mark.parametrize("bad", [{"quality": "best"},
                                 {"hair_threshold": 1.5},
                                 {"identity_floor": -0.1}])
def test_validate_rejects(bad):
    with pytest.raises(ValueError):
        HarnessConfig(**bad).validate()


def test_validate_accepts_the_default():
    assert HarnessConfig().validate() is not None


# --------------------------------------------------------------------- router
def _route_with(hair, monkeypatch, **kw):
    monkeypatch.setattr(harness, "hair_over_garment", lambda p: hair)
    return harness.route("g.jpg", HarnessConfig(**kw).validate())


def test_low_hair_takes_the_free_arm(monkeypatch):
    arm, why, h = _route_with(0.02, monkeypatch)
    assert arm == PHEAD and h == 0.02 and "<" in why


def test_high_hair_takes_the_bald_pass(monkeypatch):
    arm, _, _ = _route_with(0.40, monkeypatch)
    assert arm == BC


def test_threshold_is_inclusive(monkeypatch):
    """A reference sitting exactly on the cut-point routes to the SAFER arm."""
    assert _route_with(0.14, monkeypatch)[0] == BC


def test_threshold_is_configurable(monkeypatch):
    """The 0.14 cut-point is fitted on 38 sets; retuning must not need a code edit."""
    assert _route_with(0.10, monkeypatch)[0] == PHEAD
    cfg = HarnessConfig(); cfg.hair_threshold = 0.08
    monkeypatch.setattr(harness, "hair_over_garment", lambda p: 0.10)
    assert harness.route("g.jpg", cfg.validate())[0] == BC


def test_named_region_bypasses_the_hair_feature(monkeypatch):
    """QX regenerates rather than subtracts, so it is the only arm that can honour
    a region. Routing here must not depend on hair at all."""
    def boom(_):
        raise AssertionError("hair feature must not be computed for a named region")
    monkeypatch.setattr(harness, "hair_over_garment", boom)
    arm, why, h = harness.route("g.jpg", HarnessConfig(garment_region="the jacket"))
    assert arm == QX and h is None and "jacket" in why


# ------------------------------------------------------------------ economics
def test_generation_counts():
    """PHEAD is free preprocessing; the other two each buy one generative step
    before the shared klein call."""
    assert GENERATIONS == {PHEAD: 1, BC: 2, QX: 2}


def test_escalation_adds_two_not_one():
    r = Result(image_path="", arm=PHEAD, generations=GENERATIONS[PHEAD])
    r.generations += GENERATIONS[QX]
    assert r.generations == 3


# ------------------------------------------------------------------ the gate
class _Cfg(HarnessConfig):
    pass


def test_gate_order_deterministic_before_vlm(monkeypatch):
    """The free checks must run first. A degenerate frame should never reach a
    paid VLM call."""
    calls = []
    monkeypatch.setattr(harness, "vlm_screen",
                        lambda *a: (calls.append("vlm"), (False, ""))[1])
    from pipeline import checks
    monkeypatch.setattr(checks, "degenerate", lambda p: True)
    fired, why = harness.input_comparison("o.jpg", "p.jpg", HarnessConfig())
    assert fired and "degenerate" in why
    assert calls == []


def test_identity_scales_are_distinct():
    """checks.identity_margin is a NORMALISED margin; upscale.identity_cos is a RAW
    cosine. Both are thresholded at 0.90 against different meanings. Crossing them
    fired 6 false escalations in 8 on the first self-hosted run."""
    from pipeline import checks, upscale
    assert checks.identity_margin is not upscale.identity_cos
    assert "margin" in (checks.identity_margin.__doc__ or "").lower()
    assert "raw" in (upscale.identity_cos.__doc__ or "").lower()
    c = HarnessConfig()
    assert c.identity_escalate == 0.90 and c.identity_floor == 0.90
    assert "margin" in _fieldnote(c, "identity_escalate").lower()


def _fieldnote(cfg, name):
    """The docstring that follows a dataclass field, i.e. the calibration note."""
    import inspect
    src = inspect.getsource(type(cfg))
    return src.split(name + ":")[1].split('"""')[1]


def test_vlm_is_not_asked_about_artefacts():
    """Measured CLEAN on all 114 outputs and never fired. These failures are
    competent photographs of the wrong thing, not artefacts."""
    from pipeline import vlm
    prompts = " ".join(s["text"] for s in (vlm.GARMENT, vlm.TRYON)).lower()
    assert "artifact" not in prompts and "artefact" not in prompts


def test_the_reference_aware_prompt_is_the_one_that_sees_the_reference():
    from pipeline import vlm
    assert vlm.GARMENT["needs_reference"] is True     # 70.2%, the only one above
    assert vlm.TRYON["needs_reference"] is False      # 62.3% = do-nothing baseline


def test_vlm_fails_open(monkeypatch):
    """An outage must not escalate every request. A wasted escalation costs two
    generations; the gate erring open costs quality only on an already-flawed frame."""
    from pipeline import vlm
    monkeypatch.setitem(sys.modules, "fal_client",
                        types.SimpleNamespace(
                            upload_file=lambda p: (_ for _ in ()).throw(IOError())))
    assert vlm.ask(vlm.GARMENT, HarnessConfig(), "o.jpg", "r.jpg") == "PERFECT"


# -------------------------------------------------------------- regressions
def test_hair_from_raw_raises_rather_than_zero(monkeypatch, tmp_path):
    """0.0 is a VALID feature value meaning 'no hair over the garment'. Returning it
    on an error routes every request to the cheap arm and looks like a working
    system -- which is what it did for one whole self-hosted run."""
    from pipeline import masks
    p = tmp_path / "not_an_image.jpg"
    p.write_bytes(b"nope")
    with pytest.raises((ValueError, RuntimeError, ImportError)):
        masks.hair_from_raw(str(p))


def test_escalation_never_reseeds():
    """Failure is a property of the garment -- a damaged reference failed on all
    three people it was paired with -- so a retry on the same arm reproduces it.
    Escalation must switch MECHANISM."""
    import inspect
    src = inspect.getsource(harness.run)
    assert "arms.generate(QX" in src
    assert "seed" not in src        # nothing in the escalation path touches the seed


def test_every_stage_passes_through_on_failure():
    """No stage may emit a broken image. Realism falls back to a deterministic
    upscale rather than returning nothing."""
    import inspect
    src = inspect.getsource(harness.realism)
    assert "lanczos" in src and src.count("lanczos") >= 2
