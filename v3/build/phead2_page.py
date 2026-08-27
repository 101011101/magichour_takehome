"""Build the v3.2 comparison: BC_klein, PH and PH2 over the run-B fold.

  BC   klein bald pass, then the CPU crop, then klein edit      2 calls
  PH   the CPU crop on the raw reference, then klein edit       1 call  (PHEAD)
  PH2  the PH output fed back as image 1, same reference, same
       prompt, same seed, klein edit again                      2 calls

Reference strip shows the BC reference and the raw crop both arms on the right use.
No verdict buttons; marking lives on v30b_review.html.
"""
import arms_vs_page as A

ARMS = [("BC", "BC_klein", "bald → crop → edit"),
        ("PH", "PH", "raw crop → edit, one call"),
        ("PH2", "PH2", "PH output → edit again")]

HEAD = A.HEAD.replace("<title>Three references, one editor</title>",
                      "<title>PHEAD, klein run twice</title>") \
    .replace("<h1>Three references, one editor</h1>", "<h1>PHEAD, klein run twice</h1>") \
    .replace("""<p class='lede'>The same 28 pairs, the same klein edit call, the same seed and prompt.
<b>Only the reference image differs</b>, so every difference between the three columns is
attributable to the reference and nothing else. Small strip: the inputs and the three
references. Large row: what klein made from each. Click any image for full size.</p>""",
             """<p class='lede'>The same 28 pairs, seed and prompt. <b>BC</b> spends its two
calls on a bald pass and an edit. <b>PH</b> skips the bald pass and spends one. <b>PH2</b>
spends the second call on the same edit again, with PH's output as image 1. Read left to
right: what the second pass changed, and whether it should have. Click any image for
full size.</p>""")

NOTE = """<div class='q'><b>What to look for.</b> PH&rarr;PH2 <b>up</b>: a half-resolved
garment completes. <b>Same</b>: the pass was wasted &mdash; or the reference no-opped
twice. <b>Down</b>: the cut boundary was copied a second time onto a target that already
agrees with it, or the face and background drifted on their second trip through klein.
The person side matters as much as the garment side on PH2.</div>"""

if __name__ == "__main__":
    A.build(ARMS, "v32_phead_twice.html", HEAD, NOTE, best=None,
            ref_tags=["BC", "RAWCROP"])
