"""Configuration for the V2 try-on harness.

Every default here is measured, not guessed; the number that justifies each one is in
the comment beside it and in prd/v2/ARCHITECTURE.md. Only the first three fields are
expected to be set by a caller.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class HarnessConfig:
    # --- caller-facing -----------------------------------------------------
    high_resolution: bool = False
    """Run the realism pass. x2 output, ~$0.04, ~9s. Off by default: it serves a
    request for resolution, it is not a quality fix."""

    garment_region: Optional[str] = None
    """A user-named region ("just the jacket"). Routes straight to QX, which is the
    arm that regenerates rather than subtracts. UNMEASURED -- no test-set case
    carries one; this branch is reasoning, not evidence."""

    quality: str = "safe"
    """"safe"  -> 2.105 gen/request, 30 perfect / 7 ok / 1 fail over 38 sets.
    "cheap" -> 1.737 gen/request, 31 perfect / 5 ok / 2 fail.
    Both beat flat BC_klein (2.000, 28/6/4). Default is safe because a shipped
    failure is the worst outcome the system can produce."""

    # --- tuned, and fitted on 38 sets --------------------------------------
    hair_threshold: float = 0.14
    """Above this share of garment lost to hair removal, start at BC_klein rather
    than PHEAD. Predicts PHEAD failure at AUC 0.862. Quality is flat from 0.12 to
    0.16, so this is not a knife-edge -- but the cut-point is fitted."""

    identity_floor: float = 0.90
    """Below this AuraFace cosine the realism pass is discarded in favour of a
    deterministic Lanczos upscale. Removes all 7 of the frames the pass damaged."""

    identity_escalate: float = 0.90
    """Escalate when the output's face no longer matches the person input.

    Fires on 1 of 114 measured cells -- and that one is the only frame that
    shipped broken. All five VLM prompts passed it, including the one that was
    shown the person photo and asked whether the right person was in the result.
    An identity swap produces a competent, coherent photograph; there is nothing
    in it for a semantic judge to find. Only a numeric comparison against the
    input reveals it. Costs nothing: CPU, already loaded, no API call."""

    noop_floor: float = 0.50
    """Crash guard. Below this the output is near-identical to the person input,
    i.e. no transfer happened. Catches a failure class every output-only VLM prompt
    structurally cannot see."""

    # --- models ------------------------------------------------------------
    editor: str = "fal-ai/flux-2/klein/4b/distilled/edit"
    extractor: str = "fal-ai/qwen-image-edit-2511"
    upscaler: str = "fal-ai/seedvr/upscale/image"
    vlm_model: str = "Qwen/Qwen3-VL-8B-Instruct"
    vlm_endpoint: str = "openrouter/router/vision"
    """fal endpoints are a SERVING SUBSTRATE for open checkpoints during iteration,
    never a model source. Swapping these for self-hosted URLs is the parity run and
    is the only change the deploy path needs."""

    seed: int = 46
    """Fixed, so a re-run reproduces. Never randomised: failure is a property of the
    garment rather than the roll, so a fresh seed reproduces the failure anyway."""

    def validate(self):
        if self.quality not in ("safe", "cheap"):
            raise ValueError(f"quality must be 'safe' or 'cheap', got {self.quality!r}")
        if not 0 <= self.hair_threshold <= 1:
            raise ValueError("hair_threshold must be in [0,1]")
        if not 0 <= self.identity_floor <= 1:
            raise ValueError("identity_floor must be in [0,1]")
        return self
