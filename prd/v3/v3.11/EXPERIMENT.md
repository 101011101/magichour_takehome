# v3.11 — EXPERIMENT

**Status: OPEN.** Built 2026-09-12, not yet run. One question: **can a user choose the garment
type — upper, lower, or the whole outfit — and get it?**

Post-synthesis conclusions only, per [SCHEMA.md](../SCHEMA.md). The matrix, both call-1 prompts
and the budget are in [TEST.md](TEST.md); `RESULTS.md` will exist when the run does.

---

## Why this arm

Runbo, verbatim:

> You didn't include a feature that allows users to choose the garment type, right, like if the
> user uploads a full body image but just wants to swap like the top. I don't think I mentioned
> this to you, so I don't think you did.

He is right that it is not there. Everything shipped so far transfers **a whole outfit**: a
photograph of someone in a shirt and trousers makes one reference carrying both, and call 2
replaces both. A catalogue does not work that way — a top is one product and the trousers are
another — and neither does the user's case.

**The outcome asked for is person-side, not reference-side.** A full-body photograph goes in,
the user asks for the top, and afterwards *the person's own trousers are still their own
trousers*. Cutting the reference is only a means to that, and whether it is a sufficient means
is exactly what is unknown.

## The two mechanisms

| arm | how the reference is built | call 1 |
|---|---|---|
| **A — crop only** | the band is cut on the **mask**, before the bbox | `BALD_PROMPT`, byte for byte |
| **B — modify call 1** | call 1 *also* replaces the unselected half with a plain white garment, then the same band | a new prompt ([TEST §2](TEST.md)) |

B is Ray's proposal — *"have the first call replace the upper body with a plain white tshirt for
the crop to be easier"* — and the reasoning is that a uniform, unpatterned region is an easier
thing for a matte and a parser to cut against than a patterned garment.

**B departs from the call-1 prompt of record**, so no v3.8 or v3.10 number transfers to it. A is
the control precisely because its call 1 is untouched. Call 2 is `ER` byte for byte in both, so
the only variable is how the reference was built.

`full` has nothing unselected to neutralise: B's call 1 there would be A's, so it is generated
once, under A.

## What already exists, and what it warns about

`garment_crop.SELECT_REGION` and `region_band(shape, region)` have sat in the tree since V2,
unimplemented and raising if set. Their comment is the useful part:

> A value here would restrict the mask to a body region; the band prior it replaces was removed
> because it dragged the jeans in on the navy peacoat.

That earlier band tried to pick a **garment** by proportion, and a garment has no anatomical
boundary to hang off. This band picks a **body region** from a detected joint, which is a weaker
and better-posed question — but it is still the first failure mode to look for.

## The chain

### 1 — Is the hip line there to read? **← measured before anything was built, 2026-09-12**

**How.** `run_v311.hip_line` — the mean y of Pose landmarks 23/24, counting only hips that are
both confident (visibility ≥ 0.5) and inside the frame, which is the pair of tests
`v3lib.framing` applies to its joints — over all 66 archived bald frames in the tree.

**Result. On worn photographs, yes: 53 of 56**, with the hip between **0.41 and 1.02** of frame
height. The top of that range matters: a hip at 0.98–1.02 is a waist-up photograph, where `lower`
has nothing to keep and must fall back rather than return a sliver.

**On product shots the landmark is worse than absent — it is confidently wrong.** Pose reported a
hip on **6 of 10** flat-lay and ghost-mannequin garments, which contain no person at all. So "a
landmark exists" is not evidence that a body does, and a band drawn on a flat-lay would cut at an
invented row. This is why the fallback is triggered by geometry as well as by a missing
detection, and why the trial set is person photographs only.

### 2 — Does the band arithmetic hold? **← verified against the real code path, 2026-09-12**

**How.** `run_v311.references` exercised with a synthetic mask (subject rows 50–350, head 50–100
removed) through the real `bbox_of` and `flatten`, at four hip positions.

**Result.** The halves partition the mask exactly — upper 0.455 + lower 0.545 = 1.000 at
mid-body, matching the hand calculation. A hip at row 345 leaves `lower` 1.8% of the subject and
a hip at row 55 leaves `upper` 0.9%: both fall back to `full` with the reason recorded, as does a
frame with no pose at all.

### 3 — Which mechanism delivers the person-side outcome? **← the run, not yet made**

Six garments, two full-body people each, five (arm, region) pairs, one seed, every pair drawn from
cells the v3.10 count marked **clean** — so a failure here is attributable to the selector and
not to a pair that was already broken. [TEST.md](TEST.md) carries the matrix and what would count
as working.

The question that decides whether this is a crop change or a much larger piece of work is the
second one on the page: **handed half a garment, does call 2 leave the person's other half
alone?** Nothing in the record answers it. Every reference this project has ever sent has been a
whole outfit, and `ER`'s own sentence — *replace the clothing in image 1* — does not say *some of
the clothing*.

---

## What is deliberately not being asked

- **No call-2 prompt change.** `ER` goes in byte for byte in both arms. If half a reference needs
  different words in call 2, that is the next experiment, and mixing it in here would leave no way
  to tell which change did the work.
- **No rate.** Six garments cannot produce a failure rate and this run will not quote one.
- **No product-shot path.** Flat-lays have no person to split; link 1 measured what happens and
  the set is person photographs only.
