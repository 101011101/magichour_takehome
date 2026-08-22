"""Stage 3 -- the three arms.

They are pipelines, not models. All three end in the same klein call; they differ in
what garment reference they hand it.

    PHEAD     1 gen   parser head-removal, no generative preprocessing
    BC_klein  2 gen   klein makes the reference person bald, then the same crop
    QX        2 gen   Qwen-Image-Edit-2511 returns only the clothing

PHEAD and BC_klein both SUBTRACT; QX REGENERATES. That single fact is why BC_klein
is reached by the router rather than by escalation (it shares PHEAD's failure mode,
rescuing only 6 of PHEAD's 13 hard cases against QX's 11), and why escalation always
lands on QX.

    arm       perfect  ok  fail
    PHEAD          23   5    10
    BC_klein       28   6     4      highest ceiling
    QX             20  17     1      lowest floor -- the safety net

STATUS: `generate()` is the seam between the assembled harness and the run scripts
that produced every measured number (v2/build/amt_run.py, phase3_fal.py). It is
deliberately a thin dispatcher; the reference-building logic lives in amt_refs.py and
has not been copied here, because a second copy would drift.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "build"))

PROMPT = ("Put the garment from the second image onto the person in the first image. "
          "Keep the person's face, hair, body and the background exactly as they are.")

BALD_PROMPT = "Make this person completely bald. Keep everything else identical."

QX_PROMPT = ("Return only the clothing from this image on a plain white background. "
             "No person, no face, no skin, no background.")


def generate(arm, person_path, garment_path, cfg):
    """One arm, end to end, returning a path to the generated frame.

    NOT YET WIRED. Every number in the documents comes from v2/build/amt_run.py,
    which built the references and drove the endpoints for the measured runs. This
    dispatcher is the shape the deploy path needs; connecting it is TODO item 1, the
    end-to-end run, and it is listed as unwired rather than stubbed silently so that
    nobody mistakes an untested path for a tested one.
    """
    raise NotImplementedError(
        f"arm {arm!r}: connect to v2/build/amt_run.py's reference builder and "
        f"endpoint driver. See prd/v2/TODO.md item 1.")
