# v3.8 — EXPERIMENT

**Status: LOCKED 2026-09-10.** The architecture is in [SOLUTION.md](SOLUTION.md). What
follows is the record of how it was arrived at; it is not amended after the lock. One
sub-investigation, one behaviour: **how much is left in call 2's prompt?**

Post-synthesis conclusions only, per [SCHEMA.md](../SCHEMA.md). Cases, numbers and the
methodology of every measurement are in [RESULTS.md](RESULTS.md); the matrix is
[TEST.md](TEST.md).

**Names.** The code, runs and pages are `v36`-prefixed — written before v3.7 concluded and
the numbering settled. They are not renamed, so every command here runs as written.

---

## Why this arm

Everything before v3.8 worked on **call 1**. [v3.1](../v3.1/EXPERIMENT.md) locked a
two-model reference, [v3.2](../v3.2/EXPERIMENT.md) closed "iterate the edit" as a negative,
[v3.3](../v3.3/EXPERIMENT.md) collapsed the stack to one model,
[v3.4](../v3.4/EXPERIMENT.md) priced the canvas, [v3.5](../v3.5/EXPERIMENT.md) found the
regeneration tax — that the sophisticated arm fails **more** than the incumbent because a
generative pass over a garment resamples it — and [v3.7](../v3.7/EXPERIMENT.md) closed the
last call-1 idea, re-posing from a photograph.

That leaves one thing untouched since V2: **the sentence call 2 is sent.**

> Dress the person in image 1 in the clothing shown in image 2. Keep the person's face,
> identity, body and the background exactly as they are.

Unchanged since the attention-modulation run, never varied, never measured. v3.8 holds call 1
completely fixed — every arm is handed the same `BC` reference on the same canvas at the same
seed — and varies only that text.

---

## The chain

### 1 — Do call 2's failures reproduce off the hardware they were recorded on? **← landed, and it reframed the investigation**

**How.** The 29 cells `BC_klein` failed in its blind 600-cell sweep, re-run on fal with the
shipped prompt and two variants, 87 calls, $1.30. →
[RESULTS §3](RESULTS.md#3-the-marking-instrument-and-what-it-did-to-2s-numbers)

**Result. They largely do not.** Same prompt, same seed, same canvas rule — and most archived
failures come back clean on fal. The first arm tested therefore looked like a triumph and was
measuring the deployment, not the prompt.

**Next:** every subsequent number is self-hosted on the A100, the hardware the record was made
on. This is the single most useful thing the fal probe produced, and it cost $1.30 to learn.

### 2 — Does changing call 2's verb change anything? **← landed**

**How.** `ER` — *replace the clothing in image 1 with* in place of *dress the person in* —
against the shipped prompt and two longer variants, on 150 cells: the 29 `BC` failed and 121
it passed. Both sides on purpose, because a prompt tested only on failures cannot be adopted.
450 calls, 17.9 min, CAD 0.21. → [RESULTS §4](RESULTS.md#4-the-150-cell-prompt-comparison-2026-09-10)

**Result. Yes, on one class.** *Dress the person in* names only the putting-on and leaves the
removal implicit; *replace…with* names both. The failures it repairs are all the same shape:
**the wearer's own clothing surviving underneath the new garment.** Marked head to head, `ER`
was better on 7 cells, the same on 1, and **worse on none**.

### 3 — Do longer prompts do more? **← landed, negative**

**How.** `EFR` (`ER` + a no-blend paragraph) and `EX` (removal, layering, piece count, limb
count, framing — five sentences), same cells, same run.

**Result. No.** Neither beat the verb alone; `EX` reframes and invents lower bodies. The
pattern holds across every longer arm in this investigation: **a 4-step distilled model drifts
as the prompt grows.**

### 4 — Does V2's dynamic-prompt rule hold on call 2? **← landed, and it is the measurement worth keeping**

**How.** V2's rule — *never name a body part the crop excludes* — has governed call 1 since
v3.1 as an assumption. `ERD` builds a limb clause per cell from a MediaPipe Pose read of
image 1; `ERS` sends the same clause always. 300 calls. The instrument is the pose read that
**built** the prompt, run again over each arm's **output**. →
[RESULTS §5](RESULTS.md#5-the-limb-clause-measured-2026-09-10)

**Result. It holds, twelvefold.** On the 59 cells whose photograph has no feet in frame, feet
appear in the output of `ERS` on **21** and of `ERD` on **2**. Naming an absent limb makes the
model draw it — which is also the mechanism behind `EX`'s reframing.

**The conclusion is not "use the dynamic clause".** It is **use no clause**: plain `ER` never
names a limb, so it never triggers the failure the clause exists to prevent, and it costs no
pose read. The machinery stays in call 1, where the framing genuinely has to be described.

**Two controls fell out of the same run**, and everything after depends on them: on the 86
cells where `ERD` and `ERS` were sent identical text the outputs are **byte-identical**, so
every difference measured here is the prompt and not sampling noise; and fal is not the A100,
per link 1.

### 5 — What is `ER`'s rate on the fold? **← landed, then undone by link 6**

**How.** The whole iron-man-2 matrix — 200 pairs × seeds 46/47/48, the same 600 cells `BC`'s
blind count was made on, unsampled. 600 calls, 23.8 min, CAD 0.273. Marked on `BC`'s own
counting page with the arm switched. → [RESULTS §2](RESULTS.md#2-the-600-cell-head-to-head--the-run-and-the-rates-as-first-marked-2026-09-10)

**Result, as first marked.** `BC` 4.83%, `ER` 3.00%; joined per cell, 18 repaired against 7
broken. It looked decisive and it was not.

### 6 — Can two rates marked in two sittings resolve a gap that size? **← landed, negative, and it is the most important link in the chain**

**How.** The same reviewer, the same page, the same 600 `BC` cells, a later sitting. →
[RESULTS §3](RESULTS.md#3-the-marking-instrument-and-what-it-did-to-2s-numbers)

**Result. No.** The re-mark found **50 failures where the first found 29** — a 3.5-point swing
on an arm that did not change, larger than the 1.83-point gap link 5 reported between two
arms. Cell agreement is 94.8%, which flatters: on failures the two passes overlap on **24 of
55** distinct cells, Jaccard 0.44.

**Next:** stop comparing rates across sittings. Everything after this link is **paired** —
both images judged together, under one bar.

### 7 — What survives a paired instrument? **← landed, and it is the result of record**

**How.** Two passes. A **blind A/B** over the 25 cells the two sweeps disagreed on, arm hidden
and sides shuffled at a fixed seed. Then a **side-by-side** over all 50 of `BC`'s strict-pass
failures, one sitting, one bar, plus the other direction so the pass yields a cost beside the
rescue.

**Result.** The blind pass says **68% of the disagreements were threshold, not arm** — and of
the 8 that were real, 5–3 for `ER`, which is not significant. The side-by-side pass says
**`ER` repairs 32% of `BC`'s failures** (16 of 50, CI 21–46%), implying **8.33% → 6.17%**, a
**26% relative reduction**, and a floor rather than a point estimate.

**And the other 68% is the finding.** On 34 of `BC`'s 50 failures `ER` has the **same defect**.
Those are reference-side — the crop, the pair, the photograph — and no wording of call 2
reaches them. v3.5 argued this from mechanism; here it is counted.

### 8 — Was the hold clause ever doing anything? **← landed, negative**

**How.** `ER2` — the replace sentence alone, the clause every call-2 prompt has carried since
V2 (*keep the person's face, identity, body and the background exactly as they are*) deleted.
53 cells, the union of both arms' failures. 53 calls, 2.2 min, CAD 0.025.

**Result. It is not worth removing.** On `BC`'s failures `ER2` is clean on 40% against `ER`'s
32% — intervals overlapping, not a detectable difference — but **15 cells clean under `ER`
fail under `ER2`, against 2 the other way.** The hold half of the prompt earns its place.
Identity and scene did not visibly drift without it; the damage is to the transfer.

### 9 — How much of what is left is a seed lottery? **← landed**

**How.** Both arms' 600 cells are 200 pairs at three seeds, so the record itself says what a
retry would have done. → [RESULTS §6](RESULTS.md#6-seed-behaviour-of-the-failures)

**Result. Most of it, and `ER`'s failures are less clustered than `BC`'s.** Given a set fails
at all, `BC` fails at 1.61 of its three seeds and `ER` at 1.29; a retry meets another failure
48% of the time on `BC` and **28% on `ER`**. One retry takes `ER` to roughly **1.7%** for about
6% more calls. (Basis, as the deployed report uses it: `BC` on its strict sitting, `ER`'s
clustering from its one sweep applied to its strict-bar floor of 6.17% —
[RESULTS §6](RESULTS.md#6-seed-behaviour-of-the-failures), which also carries the
lenient-footing figures.) The floor either arm approaches is its pairs that fail at every seed — whose
*reference* is wrong, which no seed repairs.

**Not independent, and the gap is the point.** If seeds were independent a retry would meet a
failure 3% of the time, not 28%. Failures cluster by pair: a cell that failed is evidence its
pair is hard.

### 10 — Does a machine judge corroborate any of it? **← landed, partially**

**How.** A defect-only VLM judge — limb over-count, clothing phasing, other artifacts, three
booleans and nothing else — blind to the arm, both arms over the same 600 cells. 1,200 calls,
$2.43. → [RESULTS §7](RESULTS.md#7-the-vlm-defect-judge-2026-09-10)

**Result. On the one category it measures reliably, yes.** `ER` is better on **phasing** (72
vs 46 discordant, p=0.021) — exactly the class the verb targets — and indistinguishable on
limbs, which is right, because `ER` says nothing about limbs.

**The judge's own failure mode bounds what may be quoted.** Its artifact flag fires on **45%
of cells a human passed**; it is scoring "a seam is visible if I look hard". Only limb
over-count (14.8× lift over base rate) and phasing (2.7×) discriminate. **The 44%/49%
any-defect figures are meaningless as quality rates and are not quoted anywhere.**

### 11 — Is a quantised transformer the same model? **← landed**

**How.** The deploy path may pull klein from a third-party re-host. 74 cells with a known `ER`
verdict, identical prompt, reference, canvas and seed, **only the transformer swapped** for
`Photoroom/FLUX.2-klein-4b-fp8-diffusers/transformer_bf16`. →
[RESULTS §10](RESULTS.md#10-the-transformer-swap-2026-09-10)

**Result. Different weights, same behaviour.** The files share an architecture config and a
tensor layout but **16 of 18 large matrices differ**, with the low-mantissa signature of an
fp8 round trip and ~2.2% median relative error. No output is byte-identical — a 2% weight
perturbation moves the trajectory from step one — but the median pixel difference is **1.88 of
255**, flat across all three groups, and **no outcome changed**.

---

## Conclusion

*Reached; locked 2026-09-10.* v3.8 asked how much is left in call 2's prompt, and the answer
is **one verb and nothing more.** `ER` repairs 32% of the incumbent's failures at zero cost —
no extra call, no extra model, no measurable extra time — and every longer prompt tested was
neutral or harmful. [SOLUTION.md](SOLUTION.md) carries the architecture.

**The negative half is the more useful half.** Two thirds of what remains is reference-side
and unreachable by wording, which closes call-2 prompting as a direction the way v3.2 closed
iterating the edit. What the evidence recommends next is not a prompt: **a seed retry**, which
the record prices at roughly 6.2% → 1.7% for 6% more calls, and which needs a rejector that
does not yet exist.

**And a caution the investigation earned the hard way.** A reviewer's bar moved 1.7× between
two sittings on the same 600 cells. Every claim here that survives is paired; the two that
were not — link 5's rates and its 18:7 join — did not survive contact with the instrument that
checked them, and are kept in RESULTS as the record of what was marked rather than as results.
