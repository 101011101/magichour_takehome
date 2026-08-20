# v2.2 Plan — architecture and procedure

## Scope

v2.2 answers one question: **did the model make the correct change?** Three
failure modes, per [EXPERIMENT.md](EXPERIMENT.md): wrong person (reference
content leaks in), wrong clothes (a lookalike, or an imprecise transfer), and no
change or garbage.

Out of scope, cross-referenced rather than duplicated: region restore and the
predicted-warp metric ([../V2.x_DIRECTIONS.md](../V2.x_DIRECTIONS.md) directions
1 and 2), realism and gloss (v2.1), artifacts and seams (v2.3).

Base model fixed: **FLUX.2 klein 4B distilled**, decided in
[V2.1_RESULTS.md](../results_summary/V2.1_RESULTS.md). v2.2 does not reopen the
model choice. Production constraint throughout: anything in the deployed path is
open-weights and must never produce a broken input — every stage has a
pass-through fallback.

## Procedure

Each sub-workstream runs in two phases: **build and screen locally at zero
cost**, then **test against klein**. The screen exists so that we never pay to
evaluate an input we have not already looked at, and so a null result can be
attributed to the idea rather than to a bad artifact.

| | Phase 1 — build and screen (free) | Phase 2 — klein trials (paid) |
|---|---|---|
| **v2.2.1** garment reference cropping | complete | complete |
| **v2.2.1 phase 3** reference conditioning | **complete** | **complete** — Attention Modulation Test, 38 sets × 10 arms |
| **v2.2.2** person crop and composite | **obsolete** | addressed by v2.2.1 — see below |
| **v2.2.3** failure gate **+ routing** | not started | scope widened — see below |

### v2.2.1 phase 3 — how it is executed

Rationale, arm definitions and the test sets are in
[EXPERIMENT.md](EXPERIMENT.md) section 2c. This is the execution shape only.

**Everything is an option on the existing cropper.** No new pipeline: `process()`
in `v2/build/garment_crop.py` already computes every mask required — `subject`,
`clothes`, and the hair / face-skin / body-skin class maps — and composites them
in one place:

```python
def flat(a):                                     # garment_crop.py:465
    f = a[..., None].astype(np.float32)
    return crop * f + 255.0 * (1.0 - f)          # the 255.0 is the ground
```

M changes what fills `subject − clothes`. BG changes that `255.0`. AC changes the
mask and pixels before they reach this function.

**`garment_crop.py` is not modified.** Phase 3 lives in `v2/build/phase3_variants.py`,
which imports the cropper's primitives and recomputes the intermediate masks —
`route_duo()` returns only the four finished variants, and M and AC need `head`,
`face`, `skin` and the raw hair probability. Keeping the cropper untouched means
every existing C1–C4 output stays byte-identical, so phase 2 results remain
reproducible.

| order | component | build | free artifact reviewed | klein |
|---|---|---|---|---|
| 1 | **M** M1–M2 | mask arithmetic, LAB conversion | crop screen page | after quick review |
| 2 | **BG** BG1–BG4 | luminance-margin detector; ground as a parameter | a page of references **labelled with the detector's call and margin**, so the judgement is checked rather than the output | after the calls are confirmed correct |
| 3 | **AC** AC0–AC9 | see the arm ladder below | before/after on the worst holes, plus synthetic-bed scores | **not until AC is verified to work** |

**Each component is gated on a free artifact before anything is bought**, and the
gate is not the same question in each case: M and AC ask *does the crop look
right*, BG asks *did the detector decide correctly*.

#### AC build order — free arms first, deliberately

| arms | needs | when |
|---|---|---|
| AC0 control, AC1 algebra, AC2 Telea, AC3 FSR | nothing — all in OpenCV or numpy | built |
| AC4 PatchMatch | MIT C++ ext, no weights | next |
| AC5 MI-GAN, AC6 LaMa | TorchScript weights, downloaded to `v2/runs/.models/purgeable/` and **deleted after use**; CPU, minutes | done |
| AC7.n repair, AC8.n crop, AC9 SeedVR2 | fal calls, 66 total | done, 65/66 |

AC5 and AC6 are the only arms carrying a licence question (clean Apache/MIT code,
Places2-trained checkpoints). Running the free arms first means that question may
never need answering.

**Mask support varies by endpoint.** AC7.2 (Qwen inpaint) and AC7.3 (Z-Image Turbo
inpaint) are **mask-native**, so they inpaint the region directly. AC7.1 (klein) and
AC9 (SeedVR2) have no mask input and run **generate-then-composite**, with original
pixels hard-composited back outside the hole — mandatory, since a full-frame latent
round-trip otherwise degrades pattern the repair was not asked to touch. **AC8.n is the
exception**: it replaces the crop rather than repairing it, so there is no
"outside the hole" to preserve and no composite step. Its output is a garment
reference in its own right and is compared directly against C3.1 / C4 / M.

**AC8.n needs a second score the other arms do not.** Because a generative crop can
invent garment content, cutout cleanliness is not sufficient — fidelity to the
original garment region must be measured alongside it. Section 2b already showed
`garment_sim` rewards a plausible garment over the correct one, so this check is by
eye against the source, with the metric as support only.

**Scoring.** The real-hair cohort is eyeball-only (no ground truth). The synthetic
bed scores AC2–AC6 numerically against known pixels; AC1 is excluded there by
construction, since an opaque punched hole has no semi-transparent pixels to
un-composite.

**Trials reuse `v221_trials.py` unchanged.** Same runner, same arm
(`klein_4b_edit` distilled), same seed 46, same prompt — one variable, the garment
reference, exactly as in phase 2. The cherry-picked 11-pair list replaces the
13-pair Testset2 list; at ~$0.015 per generation an arm costs roughly $0.17.

**Review reuses `make_v221_review.py`.** Annotation columns added: `solved_by_M`,
`solved_by_BG`, `solved_by_AC` alongside the existing per-crop columns, plus
`ground_leakage` — whether any tint, gradient or pattern from the ground appears in
the output. That last one exists because a garment-applied-rate-only review cannot
see the failure mode an alternative ground is suspected of.

**Deferred deliberately:** head-versus-no-head on the mannequin, and the M3 blur /
face-smear arms. All are built and working; they are held back to keep the arm
count honest and are decided on images in a later phase.

## v2.2.2 — person crop and composite

**Obsolete. Closed 2026-08-19, addressed by v2.2.1.**

v2.2.2 existed to protect the **background**, by cropping the person out so the model
never sees it. That is only worth building if background damage is **its own failure
mode**. It is not — it is a symptom of the same attention deficit v2.2.1 removed.

**The evidence, from the phase-2 annotations over 33 sets:**

| | |
|---|---|
| Sets with wrong background on the uncropped baseline | 11 of 33 |
| …co-occurring with **wrong person** | **9 of 11 (82%)** |
| …co-occurring with **wrong clothes** | **9 of 11 (82%)** |
| …with **both** | 8 of 11 (73%) |
| …background wrong **on its own** | **1 of 11 (9%)** — `p009+p018` |

The conditional makes it sharper still:

| | |
|---|---|
| P(wrong background \| wrong person) | **82%** |
| P(wrong background \| person was correct) | **9%** |

**A nine-fold difference.** Background damage is almost never an independent event: it
appears when the model is already confusing which person and which clothing it is
looking at. That is the signature of **one cause, not three** — the model attending to
the whole reference image rather than the garment in it, which is exactly the deficit
v2.2.1 was built to remove and now does.

**The downstream confirmation.** Over the 38 sets of the Attention Modulation Test,
**BC_klein + QX reach 100% usable**. Background failure ran at 33% of baseline sets;
if it were still occurring at anything like that rate it would show up as unusable
outputs, because a repainted background makes a try-on unusable regardless of how good
the garment is. It does not.

**What remains unproven, and why it does not change the decision.** The AMT rankings
were holistic — one verdict per output, no per-axis columns — so background was never
scored on its own axis. The claim rests on the co-occurrence structure plus the
absence of failures downstream, not on a direct background measurement. That is
sufficient to close the workstream, and the residual check is cheap if it is ever
wanted: score `bg_psnr` outside a dilated person mask on the AMT outputs, which are
already on disk.

**Reopen only if** background damage reappears in the v2.3 artifact review, or a
product requirement makes background fidelity explicit and measured. The single
independent instance (`p009+p018`) is the pattern to watch for.

Original design, retained for whoever reopens it: crop the person, run the edit on the
crop, composite back onto the original background; background preservation then holds
by construction because the model never sees the background. **C2** was the intended
input variant.

## v2.2.3 — failure gate **and routing**

Not started. Scope widened on 2026-08-19: the phase-3 result produced **three arms
that solve the attention deficit by different mechanisms and rescue each other**, so
what remains is not another arm but **deciding which to call, and catching it when
the call was wrong.** Those are two halves of one component.

| half | when it runs | question |
|---|---|---|
| **Routing** | **before** generation | which arm should this reference use? |
| **Failure gate** | **after** generation | did the result come out usable? |

They are different in kind — routing predicts from the *input*, the gate measures the
*output* — but they share a config surface and an escalation policy, and neither is
useful alone: routing without a gate cannot recover from a wrong call, and a gate
without routing can only retry the same arm that just failed.

**Why the gate matters more than it did.** The failures are a property of the
**garment**, not the roll — a damaged reference failed on all three people it was
paired with. So **retrying the same arm on the same reference will fail again**; the
gate's job is not to reseed but to **escalate to a different mechanism**.

**The escalation ladder the phase-3 data implies:**

| step | arm | cost | why |
|---|---|---|---|
| 1 | **PHEAD** | free | 63% perfect, 79% usable, no generative call |
| 2 | **BC_klein** | 1 call | best single arm, 74% perfect / 5% fail |
| 3 | **QX** | 1 call | rescues exactly what the subtractive arms cannot |

Expected cost lands near **1.3 calls** rather than a flat 2.0, and BC_klein + QX
covers **100% usable** across all 38 sets, so the ladder has no floor case.

### The deterministic router — a signal exists, not yet validated

A candidate routing score is recorded in [RESULTS.md](RESULTS.md): **torso lean +
non-frontality + low garment-share**, z-summed, all free from MediaPipe Pose and the
human parser, both already in the pipeline. It places **6 of the 8 BC_klein-weak
garments in the top 8** — 75% precision against a 36% baseline.

**It is not validated.** The features were chosen after seeing which direction they
pointed, on 22 garments with 8 weak — selection on the same data, so the number is
optimistic. Two things are owed before it can route anything:

1. recompute over all 48 references and check the known-weak ones still rank high —
   held-out rather than fitted;
2. add **FashionSigLIP distance from the corpus centroid** as the garment-unusualness
   signal, since the parser-based proxies (class count, class entropy) pointed the
   *wrong* way and are not measuring what they were meant to.

Until then the gate carries the load and routing is an optimisation on top of it.

### The original gate spec, unchanged

A deterministic, CPU-only gate that decides whether a generated frame is usable,
producing a verdict and reason codes per output.

**Built but not called** during the v2.2.1 and v2.2.2 runs. This is deliberate:
if auto-reseed fires during an ablation it silently replaces failures, and the
failure rate we are trying to measure disappears. Recall is enabled only after
the residual rate is known.

Two independent checks, because F3 has two shapes:

| Shape | Detection |
|---|---|
| **Degenerate** — solid, constant, or blurred-out frame | Pixel statistics: global standard deviation, Laplacian variance, unique-colour count |
| **No-op** — a good photograph that is the *input*, unchanged | Output against person input: high SSIM plus near-zero change inside the garment region |

A no-op is invisible to pixel statistics; nothing is wrong with the image, it is
just the wrong image. Retries use fresh deterministic seeds (`seed + 1`,
`seed + 2`), never random, so a re-run reproduces.

An identity floor may raise `suspect` for review but must never auto-discard — a
strict identity gate would silently prefer conservative outputs and re-open the
model trade-off the program already settled.
