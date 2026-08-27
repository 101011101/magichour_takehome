# v3.0 — RESULTS

**Status: open.** The evidence layer for [v3.0/EXPERIMENT.md](EXPERIMENT.md): every case,
every number, and how each was measured. Per [SCHEMA.md](../SCHEMA.md) this document
reports what was observed and how it was established; it does not carry the decision.

Shared ground — the vocabulary and the model-level mechanism — is in
[INVESTIGATION.md](../INVESTIGATION.md) and is cited here, not repeated.

Bundle: [`v3/artefacts/`](../../../v3/artefacts/) · page:
[`v3/report/artefacts.html`](../../../v3/report/artefacts.html)

---


## 1. The headline: three of the four are not artefacts

The word "artefact" is doing damage. Measured over the same 38 sets, `v223_vlm_eval.csv`
records the VLM `artefact` prompt returning **CLEAN on all 114 outputs — including
every human `fail`**. V2 wrote the conclusion down and V3 has not absorbed it:

> our failures are not artefacts — they are competent photographs of the wrong thing.

Looking at the four frames confirms it. Only one is a render defect.

| set | hair | what BC_klein produced | class |
|---|---|---|---|
| `HD_p023` | 16.9% | person unchanged, still in the floral kimono. SSIM vs the person input **0.982** — the degenerate IF = 0 / IP = 10 point, [INVESTIGATION.md §3.3](../INVESTIGATION.md#33-the-no-op-is-a-named-failure-mode-and-4-steps-is-why) | **returns the input unchanged** |
| `HD_p023+p019` | 16.9% | cream fleece jacket kept, collar mildly restyled, garment not transferred | **near no-op** |
| `dualuse_navy_peacoat_onmodel+p012` | 14.0% | cardigan transferred, but the **stand collar is deleted and the neck stretched** | **garment geometry** |
| `p015+p007` | 4.5% | correct sleeveless tee, but the **armhole hem dissolves into the shoulder** instead of terminating | **render artefact** |

This matters because a de-artefacting pass — a realism model, an inpaint, a second
edit — repairs the fourth row and does nothing for the first three. V2 already
measured that: `artifact_fix = 3.00` in 14 of 14 batches, and "no global realism pass
has ever repaired an artifact" (`prd/v2/v2.1/RESULTS.md`).

## 2. The common cause: klein copies the cut boundary

klein treats image 2 as a picture to imitate, not as a garment to parse. Whatever the
subtractive crop leaves at its boundary is reproduced in the output. Every one of the
four is that same fact at a different severity.

**`p012` — the boundary becomes garment geometry.** The BC crop
([`04_ref_BC_klein.jpg`](../../../v3/artefacts/cases/dualuse_navy_peacoat_onmodel+p012/04_ref_BC_klein.jpg))
cuts flat through the neck just above the cardigan's stand collar and leaves a bare
neck stub. The output has no collar and an elongated neck. This is the over-cut V2
already logged — "head removal takes the collar on several worn references (p004, p022
clearest)" (`prd/v2/RESEARCH_LOG.md`, 2026-08-15) — showing up in a *shipped* arm
rather than in a discarded crop iteration.

The mechanism behind all three is [INVESTIGATION.md §3](../INVESTIGATION.md#3-why-this-happens-at-the-model-level): image 2
is not conditioning, it is a block of clean tokens sitting in the same attention sequence
as the pixels being generated, spatially registered against them. There is nothing in the
token stream that marks an edge as annotation rather than photograph. Worth sitting with:
the field's convergent fix for this class of leak is a **coarser, dilated,
shape-uninformative** boundary, and V2.2.1 spent its effort making ours *sharper* — jag
0.427 to 0.048. That was right for edge quality and it is wrong for this failure.

**`p007` — the boundary becomes a texture artefact.** The BC crop carries a soft alpha
fringe at the shoulder. In the output the sleeve hem fades into skin rather than ending
at a hem, with a thin hard contour above it. PHEAD and QX both render a defined armhole
with folds on the same set.

**`p023` — the boundary destroys the garment entirely.** After the head cut, the crop
is a seated figure in profile: mostly thigh and arm, garment a minority of the frame,
no recognisable garment silhouette. klein cannot find a garment in it and returns the
input. **The same reference, two different people, two no-ops** — the two bundles'
reference files are byte-identical — so failure is a property of the garment, not the
pairing, exactly as v2.2 concluded.

The aggravating factor on `p023` is colour: the tank and skirt are **nude, the same
value as the bare arms and thigh they are worn on**. After the head cut the crop is a
low-contrast field of skin-toned pixels with no silhouette in it. That is a different
hard case from `p021`'s hair, and the two are grouped together in V2 only because both
are `HD_` references.

`p023` is also one of the two references with **furniture in the subject matte** (the
stool), a defect `prd/v2/ARCHITECTURE.md` lists as known and unfixed.

### A measurement that did not survive

The obvious quantification — a subtractive crop should be mostly bare skin where a
regenerated one is mostly garment — was tried over all four references (chroma skin
test, YCrCb, recorded in [`manifest.json`](../../../v3/artefacts/manifest.json)) and
**carries no signal**. On `p023` every reference scores 0.91–0.99 *including QX's*,
because a coarse chroma box cannot tell a nude tank from the arm wearing it. On `p007`
QX scores a clean 0%, but its non-white pixels are near-achromatic cream, so anything
would. Only `p012`, a dark navy, gives a number that means what it looks like. The
number stays in the manifest, labelled; the argument rests on the frames.

Global SSIM is similarly narrow. It isolates the `HD_p023` no-op at 0.982 and separates
nothing else — on the other three cases all four arms sit within 0.01 of each other,
failure and rescue alike.

## 3. `p015+p007` is the expensive one, and the bald pass caused it

Hair damage on `p007` is **4.5%**. The bald pass buys nothing at that level, and
**PHEAD — the same crop without the bald call, one generation instead of two — is
`perfect` on this set.** The second klein call re-rendered the reference, softened its
edges, and the softened edge is what got copied.

BC_klein's cheapest failure is caused by a call it did not need to make.

This is a direct argument against one line in the V3 brief. V3 drops the router as
complexity, but the hair-damage figure is a number the CPU mask stack already computes,
and choosing PHEAD over BC_klein *removes* a generation. It is one model, one `if`, and
one or two calls — inside the constraint, not outside it. The V2 sweep
([ARCHITECTURE §9.2](../../v2/ARCHITECTURE.md)) puts a cut-point of 0.05–0.09 at
**29 / 6 / 3 at 1.55 generations** against flat BC's 28 / 6 / 4 at 2.000: better *and*
22% cheaper.

Standing caveat, carried from [the lock list](../../v2/LOCK.md#3-known-wrong-at-the-moment-of-freeze):
0.08 was chosen by reading the same 38 sets it is scored on, and the held-out
recomputation over all 48 references was never run. "Drop the router" and "make the
bald pass unconditional" are separate decisions, and only the second one costs
`p015+p007`.

## 4. Why QX rescues all four, and what it costs

QX (`QX_qwen_p1`, Qwen-Image-Edit-2511 regenerating the garment onto white) takes all
four: perfect, perfect, perfect, ok. The mechanism is the whole explanation — a
regenerated reference **has no cut boundary to copy and no fringe to reproduce**. There
is nothing at its edges that came from a mask.

That is also why it cannot fail the way BC_klein fails, and why V2 measured **zero
overlap** between their failure sets.

The cost is measured and it is not small (`prd/v2/v2.2/EXPERIMENT.md` §AC-A):

- hue drift **21–30° on every reference**; worst `p009` at **88°**
- texture retention as low as **×0.23** (`p030`'s pattern); mean edge retention **×0.51**,
  i.e. **half the detail of the control crop, on average**
- **9 of 11** references flagged for gross drift
- only `p019` and `p028` come back clean
- "No extraction arm currently returns the same garment"
- and the trap worth stating out loud: the reviewer *preferred* the Qwen crops by eye
  while they were losing half the pattern. Cleanest-looking and most faithful pull apart.

### 4.1 QX's one failure is invention, not omission

`p017+p002`, a plain black tee, on a set both subtractive arms take to *perfect*. QX's
reference invents an entire ghost figure — tee, jeans and sneakers — and the output
arrives **covered in white speckle and scratch marks that exist in neither input**. The
arm the V2 harness escalated to *specifically to route around AI artefacts* produced the
only true speckle artefact in the evaluation. In the vocabulary of [INVESTIGATION.md §2](../INVESTIGATION.md#2-vocabulary-three-bands-named-by-what-reached-the-output)
that is over-attention by **invention** rather than by copying, and it is the failure mode
V3 would inherit along with the rescue.

Shown: `v3/report/artefacts.html`, section *QX's own failures*.

### 4.2 klein as an extractor is already measured

**V2 ran shape 1 and never used the numbers.** `v2/runs/acab/` contains
`{ref}__QX_kleind.jpg` and `{ref}__QX_kleinb.jpg` — klein distilled and klein base as
extraction arms — across the same 11-reference cohort, and `v2/build/extraction_drift.py`
recomputes their drift live today. Mean absolute drift against the control crop:

| arm | \|dL\| | \|dC\| | dHue | edge retention | flagged |
|---|---|---|---|---|---|
| **QX_qwen_p1** (shipped) | 11.7 | 5.8 | 28.6° | **×0.51** | 9/11 |
| klein distilled | 27.3 | 5.9 | 26.7° | ×0.80 | 10/11 |
| klein base | 21.8 | 8.5 | **21.3°** | **×1.01** | 9/11 |

They do not say what the brief assumes. **klein is the better extractor on hue and on
texture and much worse on lightness** — klein base is the only arm that on average neither
loses nor invents detail, while Qwen returns half of it. The failure modes swap rather than
improve: `p030` loses its pattern to Qwen at ×0.23; `p021` gains pattern ×2.70 and chroma
+42 from klein base — texture and saturation that were never there.

This does not settle shape 1, because drift is a rank and not a verdict — a changed collar
or a moved seam appears in none of these columns, and no human has tiered a klein-extracted
arm end to end. It does mean shape 1 starts from data rather than from zero.

That trade is what 20 perfect / 17 ok / 1 fail means. QX raises the floor and lowers the
ceiling.

It is also not an invention of ours. Regenerating the garment onto a clean ground before
try-on is a published task — **Virtual Try-Off** — whose stated purpose is enabling
person-to-person try-on, with a measured gain for exactly this case, and no published
system feeds a worn head-removed torso the way we do. See
[INVESTIGATION.md §3.5](../INVESTIGATION.md#35-our-qx-arm-is-a-published-preprocessing-step). That is the strongest external
validation in this investigation and it changes the standing of shape 1 in §7. **V3 shape 1 — klein as the extractor — inherits the trade, and klein's own
extraction quality is unmeasured; QX's numbers are Qwen's.** Measure drift on klein
extractions with `v2/build/extraction_drift.py` before treating shape 1 as a
substitution.

## 5. Nothing caught any of them

For all four BC_klein failures, from `v223_vlm_eval.csv`:

| set | artefact | usable | tryon | transfer | garment | human |
|---|---|---|---|---|---|---|
| `p015+p007` | CLEAN | OK | **PERFECT** | OK | OK | fail |
| `dualuse_navy_peacoat_onmodel+p012` | CLEAN | OK | **PERFECT** | FAIL | FAIL | fail |
| `HD_p023` | CLEAN | OK | **PERFECT** | OK | FAIL | fail |
| `HD_p023+p019` | CLEAN | OK | **PERFECT** | OK | FAIL | fail |

The `tryon` prompt calls every one of them perfect. The `artefact` prompt is dead across
the whole eval. The mechanism, and why the reference-shown prompt is the only one that
works, is [INVESTIGATION.md §3.6](../INVESTIGATION.md#36-why-the-vlm-saw-nothing) — briefly: showing the garment converts the
task from low-level perceptual quality assessment, where sub-10B VLMs are near-useless,
into semantic matching against a referent, where they are competent. The same blind spot
is measured for our deterministic metrics: SSIM's rank correlation with human judgement of
**clothing fit is 0.056**. Only `garment` — the one prompt that is shown the reference — fires, on
three of four, and the case it misses is `p015+p007`: **the one true render artefact is
the one every instrument is blindest to.**

V3 ships no gate at all, so this failure would ship silently. One CPU SSIM against the
person input costs nothing, needs no model, and catches `HD_p023` at 0.982. It is not a
harness.

## 6. Evidence paths

| what | where |
|---|---|
| Assembled bundle, four cases, inputs + intermediates + all four arms | [`v3/artefacts/cases/`](../../../v3/artefacts/cases/) |
| Manifest with provenance and metrics | [`v3/artefacts/manifest.json`](../../../v3/artefacts/manifest.json) |
| Rebuild the bundle | [`v3/artefacts/build_bundle.py`](../../../v3/artefacts/build_bundle.py) |
| Side-by-side page | [`v3/report/artefacts.html`](../../../v3/report/artefacts.html) |
| Human tiers, all 38 sets × 3 arms | `v223_perfect_tier_picks.csv` |
| VLM verdicts, 570 rows | `v223_vlm_eval.csv` |
| Every arm failure with its rescue | `v2/report/failures.html` |
| Extraction drift, QX's cost | `prd/v2/v2.2/EXPERIMENT.md` §AC-A; images `v2/runs/acab/` |
| Crop mechanism and its known defects | `v2/build/garment_crop.py` header; `prd/v2/DECISIONS.md` §3 |

## 7. One correction to the V2 record

[`prd/v2/EDGE_CASE_INDEX.md`](../../v2/EDGE_CASE_INDEX.md) §3c states "BC_klein's only two
failures (`HD_p023`, `HD_p023+p019`)". There are **four**. `v223_perfect_tier_picks.csv`
and `v2/report/failures.html` both agree on four; §3c is wrong. The V3 brief's
"V3's job is the four failures" is right, and the index it points at is not.
