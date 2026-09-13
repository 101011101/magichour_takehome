# v3.11 — EXPERIMENT

**Status: CONCLUDED 2026-09-12 — it yielded a solution.** One question: **can a user choose the
garment type — upper, lower, or the whole outfit — and get it?** Yes: the band cut at the hip
**and** a call 2 that names the half. The band alone was not enough.

Post-synthesis conclusions only, per [SCHEMA.md](../SCHEMA.md). The matrix, every prompt and the
budget are in [TEST.md](TEST.md); the cases, numbers and the limits of the verdict are in
[RESULTS.md](RESULTS.md).

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
the control precisely because its call 1 is untouched.

**Call 2 is the third dimension**, added after the first run came back poor (link 4): each
(arm, region) runs under `S` — `ER` byte for byte — and `R`, which names the half being replaced
([TEST §3](TEST.md#3-the-call-2-prompts-verbatim)). `full` is `S` only. The reference is shared
between them, so a `S`/`R` pair differs by one sentence and nothing else.

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

### 3 — Which mechanism delivers the person-side outcome? **← run 2026-09-12; the band works, the outputs do not**

Six garments, two full-body people each, five (arm, region) pairs, one seed, every pair drawn from
cells the v3.10 count marked **clean** — so a failure here is attributable to the selector and
not to a pair that was already broken. [TEST.md](TEST.md) carries the matrix and what would count
as working.

The question that decides whether this is a crop change or a much larger piece of work is the
second one on the page: **handed half a garment, does call 2 leave the person's other half
alone?** Nothing in the record answers it. Every reference this project has ever sent has been a
whole outfit, and `ER`'s own sentence — *replace the clothing in image 1* — does not say *some of
the clothing*.

**Result (2026-09-12): the run completed and the outputs are poor.** 78 calls, 2.2 min, CAD 0.025;
the band found a hip on all 30 references and **nothing fell back**, so the cut itself worked. The
reviewer's read by eye is that the try-ons are not usable under either reference arm — which is
[TEST §9](TEST.md#9-what-would-count-as-working)'s third bullet, the outcome named in advance, and
it is what makes link 4 necessary rather than optional.

### 4 — Is the call-2 sentence what was missing? **← the amendment, 2026-09-12, not yet run**

Link 3 varied only the reference. But the instruction never changed: `ER` says *replace the
clothing in image 1*, and a half-garment reference cannot say *only this half* on the reference's
behalf. So call 2's text becomes a third dimension over the same references, the same seed and the
same cells — `S` is `ER` byte for byte, the control and what link 3 already made; `R` names the
half being replaced and says the other half is the person's own and stays
([TEST §3](TEST.md#3-the-call-2-prompts-verbatim)).

48 new edits on a resumed run, ≈1.5 min, ≈CAD 0.02 — the references are untouched and nothing
already on disk is regenerated. The page puts `S` and `R` beside each other per reference, so the
comparison is one sentence against another with everything else held.

**What it separates.** If `R` holds the unselected half where `S` loses it, the selector is a crop
plus a dynamic sentence, and the remaining question is which reference arm to pair it with. If `R`
leaks too, then no wording reaches this and the half has to be protected structurally — a mask
into call 2, or compositing the untouched half back — which is a different and larger piece of
work than a selector.

**Result (2026-09-12): the sentence was what was missing.** 126 calls in total, 3.36 min,
CAD 0.039. Judged on `v3/report/v311_selector.html` — the candidate alone, band cut plus a call 2
naming the half, with the input photographs beside the outputs — **the reviewer's verdict is that
it works.** The unselected half survives under `R` where it did not under `S`, on the same
references, the same crop and the same seed, so the difference is one sentence. It costs nothing:
**1.651 s under `R` against 1.659 s under `S`**. →
[RESULTS §4](RESULTS.md#4--link-4--the-call-2-sentence-is-what-was-missing)

**And it does not choose an arm.** Both A/`R` and B/`R` were on the page and the verdict names
neither, so this investigation does not claim one. A is the cheaper default by construction —
one bald pass and one mask per garment serve all three regions (**3.27 s**) against B's roughly
6.56 s — and A's call 1 is `BALD_PROMPT` byte for byte, which is what every other number in v3
rests on. → [RESULTS §5](RESULTS.md#5--arm-a-against-arm-b--not-settled-and-a-is-the-cheaper-default)

---

## Conclusion

*Reached; concluded 2026-09-12.* v3.11 asked whether a user can choose the garment type and get
it. **They can, and it takes two changes, not one:** the reference cut to the selected band at
the hip line, **and** a call 2 that names the half being replaced. Link 3 established that the
crop alone is not enough — the band cut perfectly, nothing fell back, and the outputs were still
unusable — and link 4 established that the sentence closes it, at no cost in time, calls or
models.

**The negative half is worth as much as the positive.** A region-shaped reference does not
instruct the model; `ER`'s *replace the clothing in image 1* means all of it, and it behaves that
way. That generalises past this feature: **what the reference contains is not an instruction**,
and any future work that expects a cropped input to constrain an edit should expect the same
result.

**What ships**, subject to the arm question above: a `REGION` selector of `upper | lower | full`,
defaulting to `full`, which cuts the reference at the hip and swaps call 2's sentence. `full` is
the shipped path untouched, byte for byte.

**What this is not.** A feasibility result on 12 clean cells at one seed, by one reviewer, by
eye — not a rate, and the v3.10 figure describes a whole-outfit request, not a region request.
The honest next step is a counted sweep of a region set, marked the way v3.10 was marked
([RESULTS §6](RESULTS.md#6--what-this-does-not-establish)). Before that, two things are known to
be unhandled: a **waist-up photograph asked for `lower`**, which must fall back rather than
return a sliver, and a **product shot asked for a region at all**, where Pose reports a hip on 6
of 10 person-free photographs and the band would cut at an invented row.

## What is deliberately not being asked

- ~~**No call-2 prompt change.**~~ **Struck 2026-09-12.** It was the right boundary for link 3 —
  one variable at a time, and the reference arms had to be readable on their own. Link 3 answered
  its question (the band cuts, nothing falls back) and the outputs still failed, so the call-2
  sentence became the next experiment rather than a confound. `S` is retained unchanged as the
  control precisely so the two changes stay separable.
- **No rate.** Six garments cannot produce a failure rate and this run will not quote one.
- **No product-shot path.** Flat-lays have no person to split; link 1 measured what happens and
  the set is person photographs only.
