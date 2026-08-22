"""The escalation judge.

Two prompts, one open-weights VLM. Measured over 114 human-tiered outputs:

    prompt      sees                      fires  accuracy  catches fail
    artefact    output                        0     62.3%           0%
    usable      output                        4     62.3%          13%
    tryon       output                        2     62.3%           7%
    garment     reference + output           35     70.2%          53%
    transfer    person + reference + output   8     64.0%          20%
    (accept everything)                       0     62.3%           0%

Only `garment` beat the do-nothing baseline, and it is the only one with a reference
image. Do not add an artefact prompt: it returned CLEAN on all 114 outputs and never
fired, because these failures are not artefacts -- they are competent photographs of
the wrong thing. Do not add the person image either: `transfer` sees all three and
scored below `garment`, so at 8B a third image dilutes rather than informs.
"""
import re

SYSTEM = ("You are a strict quality inspector for a virtual try-on system. "
          "Answer only as instructed.")

GARMENT = dict(
    needs_reference=True, labels=("PERFECT", "OK", "FAIL"), text=(
        "The FIRST image is a garment reference. The SECOND image is a virtual "
        "try-on result that was supposed to put that garment onto a person.\n"
        "Did it work? Consider whether the garment in the second image is genuinely "
        "the one from the first image (not merely a similar item), whether the "
        "person is undistorted, and whether the scene is intact.\n"
        "PERFECT - correct garment, clean result. OK - correct garment, visible "
        "flaw. FAIL - wrong garment, or clearly broken.\n"
        "Answer with exactly one word: PERFECT, OK, or FAIL."))

TRYON = dict(
    needs_reference=False, labels=("PERFECT", "OK", "FAIL"), text=(
        "This is the output of a virtual try-on: a photo of a person that has been "
        "edited to put a different garment on them.\n"
        "Judge it on three things: (1) does the person still look like a real, "
        "undistorted human; (2) does the garment sit on the body plausibly; "
        "(3) is the background and scene intact and unrepainted.\n"
        "PERFECT - all three hold. OK - a visible flaw but shippable. "
        "FAIL - any of the three clearly broken.\n"
        "Answer with exactly one word: PERFECT, OK, or FAIL."))


def ask(spec, cfg, out_path, reference_path=None):
    """Returns one of the spec's labels, or 'UNPARSED'.

    Fails OPEN -- on any error it returns the spec's top label, so the gate does not
    escalate on an outage. A wasted escalation costs 2 generations; a missed one
    costs quality on a frame that was already imperfect."""
    import fal_client
    try:
        urls = []
        if spec["needs_reference"] and reference_path:
            urls.append(fal_client.upload_file(reference_path))
        urls.append(fal_client.upload_file(out_path))
        res = fal_client.subscribe(cfg.vlm_endpoint, arguments={
            "model": cfg.vlm_model, "prompt": spec["text"], "image_urls": urls,
            "system_prompt": "Answer with exactly one word.", "max_tokens": 8})
        txt = (res.get("output") or "").strip().upper()
        for lab in spec["labels"]:
            if re.search(rf"\b{lab}\b", txt):
                return lab
        return "UNPARSED"
    except Exception:
        return spec["labels"][0]
