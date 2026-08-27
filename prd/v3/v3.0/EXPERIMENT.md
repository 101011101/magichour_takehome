# v3.0 — EXPERIMENT

**Status: open.** One sub-investigation, one behaviour: **what are the failure and success
conditions of the two arms that survive into V3 — BC_klein, which subtracts, and QX, which
regenerates?**

Post-synthesis conclusions only, per [SCHEMA.md](../SCHEMA.md). Every case, number and
method behind a link in the chain is in [RESULTS.md](RESULTS.md); the vocabulary and the
model-level mechanism are shared ground in
[INVESTIGATION.md](../INVESTIGATION.md).

---

## The chain

### 1 — What are BC_klein's four failures, actually?

**How.** Read the human tiers out of `v223_perfect_tier_picks.csv`, assemble every input,
intermediate and arm output for the four failing sets into a provenance-tracked bundle,
and look at the frames rather than at the summary.
→ [RESULTS §1](RESULTS.md#1-the-headline-three-of-the-four-are-not-artefacts),
[§2](RESULTS.md#2-the-common-cause-klein-copies-the-cut-boundary)

**Result.** **Three of the four are not artefacts.** Two are the model returning the input
unchanged, one is a garment rendered with the wrong geometry, and only one is a render
defect. The V3 brief's framing — "the four failures are AI artefacts" — is wrong, and V2
had already measured why: the VLM `artefact` prompt returned CLEAN on all 114 outputs.

They share a cause: **klein reproduces whatever the reference's cut boundary contains.**
A flat cut above a collar becomes a missing collar; a matte fringe becomes a hem that
dissolves; a crop with no garment silhouette left in it produces no edit at all.

**Next:** if the boundary is the cause, why does a boundary become *content*?

### 2 — Why does the reference's boundary propagate into the output?

**How.** Literature and primary-source research, with every claim labelled and cited.
BFL published no technical report, so the reference implementation was read directly.
→ [INVESTIGATION.md §3](../INVESTIGATION.md#3-why-this-happens-at-the-model-level)

**Result.** Image 2 is **not conditioning**. References are VAE-encoded, flattened, and
concatenated onto the noisy target tokens in the same attention sequence, separated only
by an integer offset on one RoPE axis — so a reference token shares its *spatial* phase
with the target token at the same grid position, and nothing marks its edges as annotation
rather than photograph. Copying is the known attractor for this design, and the field's
convergent fix is a **coarser, less informative** boundary. Our cropper spent V2.2.1
making the boundary *sharper*.

Two corrections fell out and both change what can be proposed: **guidance is not a knob on
this checkpoint** (`use_guidance_embed = False`), and **SSIM 0.982 is not a similarity
measurement** but the named degenerate point IF = 0 / IP = 10.

**Next:** the boundary is produced by the bald pass and the crop. Is the bald pass paying
for itself?

### 3 — Is the bald pass net-negative where hair damage is low?

**How.** Compare BC_klein against PHEAD — the same cropper without the bald call, one
generation instead of two — on the low-damage sets already generated in
`v2/runs/amt/gen/`. No new spend.
→ [RESULTS §3](RESULTS.md#3-p015p007-is-the-expensive-one-and-the-bald-pass-caused-it)

**Result, provisional.** On `p015+p007`, hair damage **4.5%**, PHEAD is `perfect` and
BC_klein `fail`. The extra klein pass re-rendered the reference, softened its edges, and
the softened edge is what was copied. **BC_klein's cheapest failure is caused by a
generation it did not need to make.** V2's own threshold sweep puts a cut-point of
0.05–0.09 at 29/6/3 at 1.55 generations against flat BC's 28/6/4 at 2.000 — better and
22% cheaper.

**Held as provisional, not concluded:** that sweep was read off the same 38 sets it is
scored on, and the held-out recomputation was never run. This is one set, not a condition.

**Next:** QX rescues all four. What does it cost, and is it a free substitute?

### 4 — What does QX actually cost?

**How.** Recompute extraction drift live from `v2/runs/acab/` with V2's own triage script:
median lightness, chroma and circular hue shift of the garment pixels against the control
crop, plus an edge-density ratio. Deliberately dumb statistics, because V2 established
that no embedding metric survives here.
→ [RESULTS §4](RESULTS.md#4-why-qx-rescues-all-four-and-what-it-costs)

**Result.** QX has the **highest floor and the lowest ceiling**, and both come from the
same fact: it does not subtract the context, it replaces the garment. Mean edge retention
is **×0.51 — half the detail of the control crop** — with 9 of 11 references flagged for
gross drift and hue drift up to 88°.

Two findings that were not expected:

- **QX's one outright failure is *invention*, not omission.** On a plain black tee, on a
  set both subtractive arms take to perfect, its output arrives covered in white speckle
  present in neither input. The arm the V2 harness escalated to *in order to route around
  AI artefacts* produced the only true speckle artefact in the evaluation.
- **V3's shape 1 is partly already run.** `v2/runs/acab/` holds klein-extracted references
  from V2's AC-A phase whose numbers were never used. **klein is the better extractor on
  hue and texture and much worse on lightness** — klein base is the only arm that on
  average neither loses nor invents detail, against Qwen's half. The failure modes swap
  rather than improve.

**Next — and this is the open link.** Everything above rests on single instances:
one plain-tee invention, one low-hair bald-pass regression, one skin-valued no-op
reference. A condition cannot be established from an instance.

### 5 — What are the conditions for each band? **← current**

**What is being investigated.** For each of the three bands in
[INVESTIGATION.md §2](../INVESTIGATION.md#2-vocabulary-three-bands-named-by-what-reached-the-output) —
over-attention, questionable attention, failed attention — **which properties of the
garment reference predict it, and do they predict it for BC and QX in opposite
directions?** Stated as the hypotheses under test:

| # | hypothesis | arm it should break |
|---|---|---|
| H1 | A reference whose cut line crosses a garment feature produces over-attention: the cut becomes garment geometry | BC |
| H2 | A reference whose garment sits at skin value produces failed attention — the output is the input | BC |
| H3 | A reference in a non-frontal or seated pose transfers its *pose*, and non-frontality predicts failure independent of hair damage | BC |
| H4 | A reference with little internal detail produces over-attention by **invention** — the model fills what it cannot extract | QX |
| H5 | A reference with dense fine detail — text, stripe, plaid, logo — produces questionable attention: right garment, smoothed or mangled | QX |
| H6 | A reference carrying view-dependent information a canonical front cannot hold loses it under regeneration | QX |
| H7 | The two arms' failure conditions do not intersect — the V2 "zero overlap" claim, retested on a set built to break both | both |

**How.** A new 36-pair run, **12 garment references × 3 person inputs**, drawn from
`test_set2/` and chosen so that each reference stresses a named condition above, with
neither arm set up to win. Both arms on identical pairs, identical seed, identical prompt:
**36 BC_klein generations and 36 QX generations.** Specification, selection rationale,
exclusions and run conditions: **[TEST.md](TEST.md)**.

Garment-driven rather than pair-driven because failure has already been shown to be a
property of the reference — `HD_p023` no-ops against two different people from
byte-identical reference files. Three people per reference is the smallest design that
separates "this garment fails" from "this pairing failed".

**Result.** *Not yet run.*

---

## Conclusion

*Not reached — the investigation is open.* Links 1, 2 and 4 have landed; link 3 is
provisional on one set; link 5 is specified and unrun.

**Whether this yields a solution is undecided.** No `SOLUTION.md` exists in this directory
and none should be written until link 5 returns. The two candidates it would arbitrate
between are already visible and are recorded here only so they are not lost:

1. **Prepare the reference differently** — the mechanism says the boundary should be made
   *less* informative, not cleaner, and six CPU-side mitigations follow from it at no
   generation cost.
2. **Replace the reference entirely** — regeneration, which the literature says is the
   standard preprocessing stage for person-to-person try-on, and which this investigation
   says arrives with an invention failure of its own.

They are not exclusive, and link 5 is designed to say which conditions each one owns.

### Standing implications for the brief's three shapes

Carried here rather than lost, because the diagnosis already re-orders
[the brief's candidate list](../README.md#4-the-one-thing-to-carry-over-qxs-mechanism)
and a later reader will otherwise re-derive it. **These are implications, not decisions;
nothing is chosen until link 5 returns.**

| shape | standing |
|---|---|
| **3 — regenerate only the damage** | Strongest fit to the diagnosis. All four failures are boundary defects and the mask stack already knows where the boundary is. `p023` is the honest test: [RESULTS](RESULTS.md#2-the-common-cause-klein-copies-the-cut-boundary) records that its damage is *open, not enclosed*, which makes inpainting a category error — so this either fixes `p012` and `p007` and fails `p023`, or the framing is wrong. Either outcome is information. |
| **1 — klein as extractor** | Partly already run — see [link 4](#4-what-does-qx-actually-cost). The stage is standard practice with a published gain for person-to-person, and the drift numbers exist on disk. What is missing is a human tier over an end-to-end klein-extracted arm. Score it on drift *and* tier. |
| **2 — one prompt, bald *and* isolate** | Weakest. It asks a 4-step distilled call to do two edits, and `p023` shows one confusing reference is enough to make klein return the input. |

Two more that are not on the brief's list and cost no generation:

- **Make the bald pass conditional on hair damage.** Already measured, and the only change
  that touches `p015+p007`.
- **Fix the reference before fixing the model.** Six of the mitigations in
  [INVESTIGATION.md §3.7](../INVESTIGATION.md#37-mitigations-that-have-a-mechanism-behind-them)
  are CPU-side reference preparation — do not cut through the garment, erode rather than
  feather, pad and centre, upsample toward the 1024² cap BFL's code will never reach on its
  own — and two are prompt wording. **The cropper was built to make the boundary *cleaner*;
  the mechanism says it should be made *less informative*.** That is a different objective
  and has never been tested here.
