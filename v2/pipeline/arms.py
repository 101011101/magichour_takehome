"""Stage 3 -- the three arms.

They are pipelines, not models. All three end in the same klein call; each arm's
whole contribution is WHICH garment reference it hands over.

    PHEAD     1 gen   parser head-removal, no generative preprocessing
    BC_klein  2 gen   klein makes the reference person bald, then the same crop
    QX        2 gen   Qwen-Image-Edit-2511 returns only the clothing

PHEAD and BC_klein both SUBTRACT; QX REGENERATES. That single fact is why BC_klein
is reached by the router rather than by escalation -- it shares PHEAD's failure mode,
rescuing only 6 of PHEAD's 13 hard cases against QX's 11 -- and why escalation always
lands on QX.

    arm       perfect  ok  fail
    PHEAD          23   5    10
    BC_klein       28   6     4      highest ceiling
    QX             20  17     1      lowest floor -- the safety net

References are READ FROM DISK, not rebuilt. They were produced by
v2/build/amt_run.py and are what every measured number came from; a rebuilt PHEAD
crop comes out 1347x475 against the stored 1194x467, and a reference that differs
from the one the numbers came from is a different experiment. Building a reference
for an UNSEEN garment is the one remaining gap -- see prd/v2/TODO.md item 1.
"""
import os
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "build"))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

PROMPT = ("Dress the person in image 1 in the clothing shown in image 2. Keep the "
          "person's face, identity, body and the background exactly as they are.")

REF = {
    "PHEAD":      ("v2/runs/amt",  "{src}__PHEAD.jpg"),
    "BC_klein":   ("v2/runs/amt",  "{src}__BC_klein.jpg"),
    "QX_qwen_p1": ("v2/runs/acab", "{src}__QX_qwen_p1.jpg"),
}


def reference(arm, garment_stem):
    """Path to this arm's garment reference, or None if it has not been built."""
    d, pat = REF[arm]
    p = os.path.join(REPO, d, pat.format(src=garment_stem))
    return p if os.path.exists(p) else None


def generate(arm, person_path, garment_path, cfg):
    """One arm, end to end. Returns a path to the generated frame.

    The klein call is identical for all three arms. Preprocessing that needed a
    generative step -- BC_klein's bald pass, QX's extraction -- is already baked into
    the stored reference, which is why GENERATIONS counts 2 for those two.
    """
    import fal_client

    stem = os.path.splitext(os.path.basename(garment_path))[0]
    ref = reference(arm, stem)
    if ref is None:
        raise FileNotFoundError(
            f"no {arm} reference for {stem!r}. References are built by "
            f"v2/build/amt_run.py; building them for an unseen garment is the "
            f"remaining gap (prd/v2/TODO.md item 1).")

    res = fal_client.subscribe(cfg.editor, arguments={
        "image_urls": [fal_client.upload_file(person_path),
                       fal_client.upload_file(ref)],
        "prompt": PROMPT, "seed": cfg.seed})
    url = ((res.get("images") or [{}])[0].get("url")
           or (res.get("image") or {}).get("url"))
    if not url:
        raise RuntimeError(f"{cfg.editor} returned no image: {list(res)}")
    dst = tempfile.mktemp(suffix=f"__{arm}.jpg")
    urllib.request.urlretrieve(url, dst)
    return dst
