# V3 general investigation — what is actually wrong

The general investigation document under [SCHEMA.md](SCHEMA.md): the shared ground every
sub-investigation stands on. It carries **the vocabulary** and **the model-level
mechanism**, and it maps which `v3.x` owns which question. Case detail, numbers and
outcomes live in the sub-investigations and are linked, never repeated here.

---

## 1. What V3 is investigating

[The brief](README.md) says "V3's job is the four failures." Looking at the four frames
says the brief is describing them wrongly: only one is a render artefact, two are the
model returning the input unchanged, and one is a garment rendered with the wrong
geometry. They share a cause, and the cause is in the reference rather than in the model.

That reframing is what the sub-investigations are drawn from. It is established in
[v3.0](v3.0/EXPERIMENT.md) and summarised in one line: **klein reproduces whatever the
reference's boundary contains, and where the reference contains no legible garment it
reproduces nothing at all.**

## 2. Vocabulary: three bands, named by what reached the output

Working vocabulary for V3, extending V2's "attention deficit". Every failure seen so far
sits in one of three bands, and the bands are defined by **what arrived in the output
relative to the garment** — which is observable — rather than by attention, **which we
have never actually looked at.** That caveat is load-bearing: no attention map has been
inspected in this project. "Attention" is inherited descriptive vocabulary from V2's
descent hypothesis, not a measured mechanism, and it should not harden into one without
someone opening the model.

| band | what it means | seen in |
|---|---|---|
| **over-attention** | **More arrived than the garment.** Content that is not the garment survives into the output: the reference's *pose*, its cut boundary, its matte fringe, its wearer's identity, its background | `p012`'s deleted collar, `p007`'s dissolved hem, V2's identity import at −0.933 margin, the uncropped baseline's background damage |
| **questionable attention** | **Some of the garment arrived, incompletely.** The right region is attended and resolved wrong or half — a shallow collar where a stand collar belongs, a hue that shifted, a pattern that smoothed | most of the 6 BC and 17 QX `ok` verdicts; the whole extraction-drift table |
| **failed attention** | **None of the garment arrived.** The reference contributed no usable signal at the timesteps that decide layout, and the output is the input | `HD_p023`, both pairings |

### 2.1 Over-attention has two sources, and they are the mechanism split

A subtractive arm gets more than the garment by **copying** what was beside it — the
mechanism in [§3.1](#31-image-2-is-not-conditioning-it-is-clean-tokens-in-the-same-attention-sequence).
A regenerative arm gets more than the garment by **inventing** what was not there: QX's
one outright failure is white speckle and scratch marks strewn across a plain black tee
that exist in neither input. Same band, opposite mechanism — which is precisely why the
two arms have no shared failures, and why the band is worth naming above the mechanism
rather than below it.

### 2.2 Pose belongs in over-attention, and there is prior evidence for it

The reference's *pose* is over-attention's most legible case: a seated profile, a torso
lean, crossed arms. V2 has a measurement pointing at it that was never followed up — the
routing probe built from **torso lean, non-frontality and garment share** put 6 of 8
BC_klein-weak garments in its top 8, against a 36% baseline
(`prd/v2/v2.2/RESULTS.md`). That is not proof that pose transfers; it is evidence that
non-frontality of the *reference* predicts failure of the *edit*, which is the same claim
one step back. **[inferred]**

### 2.3 The question the vocabulary makes askable

QX raises the floor by forcing the reference into a canonical view, and in doing so
discards drape, rotation and pattern — **×0.51 of the edge detail on average across the
cohort** ([v3.0/RESULTS §4](v3.0/RESULTS.md#4-why-qx-rescues-all-four-and-what-it-costs)). So the trade is not
"cleaner reference versus messier reference". It is:

> **Is the original context worth more than the interference it causes?**

The literature has the same tension on record. **[documented]** MV-VTON finds a single
garment view "insufficient" and uses two (<https://arxiv.org/abs/2404.17364>); RefTon
argues a worn reference reveals drape and translucency a flat shot cannot
(<https://arxiv.org/html/2511.00956v6>). **[documented absence]** Nobody has measured the
trade for a reference like ours, because nobody feeds a reference like ours.

## 3. Why this happens at the model level

Research, not measurement. Every claim below is labelled **[documented]** with a source,
**[inferred]**, or **[speculative]**, per [SCHEMA.md §4](SCHEMA.md). The load-bearing
claims are the ones read out of BFL's own reference implementation, and those are
directly checkable: <https://github.com/black-forest-labs/flux2>.

**Position of record on primary sources.** BFL published **no technical report** for
FLUX.2 or klein. The blog posts state capabilities and no mechanism; the editing docs
give "image 1 / image 2" indexing and megapixel budgets and say nothing about reference
preparation, backgrounds, cutouts or failure modes. Third-party claims that FLUX.2
"cross-attends over reference embeddings" are wrong. The code is the source.

### 3.1 Image 2 is not conditioning. It is clean tokens in the same attention sequence

**[documented — BFL source, `sampling.py::encode_image_refs`]**

- Each reference is `.convert("RGB")` — **the alpha channel is discarded outright.** A
  soft matte survives only as whatever it was flattened onto.
- The multi-reference path caps each reference at `limit_pixels = 1024²`, and
  `cap_pixels` **only ever downsizes**. A small bbox crop is never upsampled, so it gets
  proportionally few tokens.
- VAE-encoded, then flattened: `rearrange(x, "c h w -> (h w) c")`.
- Position ids are 4-D `(t, h, w, l)`, with **`t = 10 + 10·index`** per reference.
- `denoise()`: `img_input = torch.cat((img_input, img_cond_seq), dim=1)` — references are
  **appended to the noisy target tokens in the sequence dimension** and run through the
  same joint self-attention stack. Text is a separate stream.

**[documented]** FLUX.1 Kontext confirms the design intent: context tokens "are then
appended to the image tokens and fed into the visual stream", and the constant offset is
"a virtual time step that cleanly separates the context and target blocks"; channel-wise
concatenation "was found to perform worse". <https://arxiv.org/abs/2506.15742>

**[inferred, well-supported] — the load-bearing step.** Every image in the sequence gets
`h` and `w` indices starting at 0; only `t` differs. A reference token at grid position
(h,w) therefore shares its *spatial* RoPE phase with the target token at (h,w), and
attention is positionally biased toward same-coordinate pairs. ContextDrag documents that
in in-context editors "corresponding tokens share corrected positional RoPE and receive
higher attention scores", and that "minor perturbations in positional embeddings can
significantly affect the geometry of synthesized content"
(<https://arxiv.org/pdf/2512.08477>). So a horizontal luminance discontinuity at a given
row in the reference has a direct, position-privileged channel into the corresponding row
of the target — and **nothing in the token stream flags those edges as annotation rather
than photograph.**

**[documented]** That copying is the attractor is the oldest result in the area.
Paint-by-Example found naive reference conditioning collapses to "a trivial mapping
function" with "obvious copy-and-paste artifacts", and both of its fixes are about
*destroying* reference information — a CLIP class-token bottleneck and strong geometric
augmentation "to break down the connection with the source image"
(<https://ar5iv.labs.arxiv.org/html/2211.13227>). AnyDoor is more direct still: it
**erodes the object mask before feature extraction** — "we add an eroded mask to filter
out the information near the outer contour of the target object" — precisely because "we
do not encourage 'copy-paste' style generation", and it background-removes *and centres*
the object (<https://ar5iv.labs.arxiv.org/html/2307.09481>).

**[documented]** And the architecture FLUX.2 uses has been criticised for exactly this:
spatial concatenation of a clean garment latent into the denoising target causes guidance
leakage, gradient competition and a train–test discrepancy because "the garment latent
deviates from proper noise scheduling" (<https://arxiv.org/html/2511.18775>).

### 3.2 Failures 1 and 2 in those terms

**[inferred]** **The collar.** The neck cut is a high-contrast, horizontally-registered
luminance step at the top of the torso — the single most salient edge in image 2, and
exactly the low-frequency structure resolved first (§3.3). Nothing distinguishes "garment
terminates here" from "mask terminated here", so the model reproduced the most legible
boundary in the reference.

This is the *reference-side* twin of a documented person-side artefact. **[documented]**
FitDiT reports masks "constructed strictly based on human parsing contours" cause the
model to "fill the entire mask area during inference"
(<https://arxiv.org/html/2411.10499v1>); TryOnDiffusion reports agnostic RGB "leaks
information of the original garment" (<https://ar5iv.labs.arxiv.org/html/2306.08276>).
**The field's convergent fix is coarser, dilated, shape-uninformative boundaries — never
sharper ones.** Our cropper spent V2.2.1 making its boundary *sharper*, from jag 0.427 to
0.048. That was the right move for edge quality and it is the wrong move for this failure.

**[inferred]** **The hem.** A guided-filter trimap band produces a monotone alpha ramp;
flattened to white it becomes a soft luminance gradient ending in a hard contour where the
band ends — a legible, reproducible texture. **[documented, indirect]** Trans-Adapter
reports that compositing RGBA onto a solid colour before a standard VAE "not only fails to
preserve alpha consistency, but also exhibits noticeable degradation in RGB fidelity"
(<https://arxiv.org/html/2508.01098v1>). **[documented absence]** **No source states
whether feathered or hard cut edges are safer for a diffusion editor.** Anyone who says
they know is citing folklore.

### 3.3 The no-op is a named failure mode, and 4 steps is why

**[documented — BFL source]** `Klein4BParams` sets **`use_guidance_embed = False`**. The
4B model has no `guidance_in` MLP; the guidance value never reaches the network. `util.py`
marks `guidance` and `num_steps` as `fixed_params` with the comment `# guidance and
timestep distilled`, and the CLI errors if you change them. Diffusers agrees: "for
step-wise distilled models, `guidance_scale` is ignored", and no FLUX.2 pipeline exposes
`true_cfg_scale` or `negative_prompt`
(<https://huggingface.co/docs/diffusers/main/en/api/pipelines/flux2>).

> **Correction to fold forward:** any framing of the form "we could raise guidance" is
> wrong for this checkpoint. The only real fork is distilled klein versus
> `FLUX.2-klein-base-4B` (undistilled, 50 steps, real guidance 4.0, also Apache 2.0) —
> a different model, and therefore outside V3's constraint.

**[documented]** Returning the input unchanged is a *taxonomy entry*, not an oddity.
ImagenWorld defines two editing failure modes — regenerating an entirely new image, and
**returning the input unchanged** — and finds "models tend to exhibit one mode far more
frequently than the other", attributing the split to architecture: "diffusion-only editors
preserve source images more consistently" (<https://arxiv.org/html/2603.27862>). klein's
family is the one biased toward our mode.

> **Second correction:** stop calling 0.982 a similarity measurement. Complex-Edit names
> the degenerate point precisely — "an output image that is identical to the input image
> should have an Instruction Following score of 0, but an Identity Preservation score of
> 10" (<https://arxiv.org/html/2504.13143v1>). `HD_p023` is **IF = 0 / IP = 10**, and
> "no-op" is not a term of art; the literature says *returning the input unchanged*.

**[documented]** This is also why the whole-image metrics flatter it: ComplexBench-Edit
notes whole-image L1/L2 "would erroneously assign the best scores to models that return
the original, unedited image", and that some models "achieve artificially inflated visual
consistency scores precisely because their diminished instruction-following capabilities
prevent them from meaningfully modifying the input image"
(<https://arxiv.org/pdf/2506.12830>).

**[documented]** Distillation plausibly aggravates it. Qwen-Image-Flash is the only work
measuring distillation cost on *editing*: "editing ability cannot be fully preserved by
T2I-only distillation", and "the denoising trajectory may not be fully completed in
certain cases" (<https://arxiv.org/html/2606.03746v1>). Reference-conditioned training has
a known copying attractor — "the model tends to directly copy reference images during
generation, resulting in poor editability" (<https://arxiv.org/html/2510.20887>).
**[inferred]** At 4 steps on a multi-reference endpoint, "return image 1 verbatim" is a
low-loss basin with few opportunities to escape.

**[documented]** BFL names the symptom class on the record: klein "may fail to generate
output that matches the prompts", and "prompt following is heavily influenced by the
prompting-style" (<https://huggingface.co/black-forest-labs/FLUX.2-klein-4B>).

**[documented absence]** **Nobody has published klein returning the input unchanged.** If
we assert it we are the source — report n and the SSIM distribution, and cite
ImagenWorld/Complex-Edit for the category only.

### 3.4 Why `p023` specifically: amplitude, not contrast

**[documented — BFL source]** The VAE is `ch_mult=[1,2,4,4]` → 8× conv compression,
`z_channels=32`, then a `[2,2]` pixel-unshuffle → 128 channels at H/16, flattened
straight to tokens. **One transformer token covers a 16×16 pixel block.** At 832×1248
that is ~4,056 target tokens; a reference is capped at ~4,096 and a tight bbox crop gets
far fewer, because nothing upsamples. A garment edge in a 512-px crop is a couple of
tokens wide.

**[documented]** Diffusion resolves coarse→fine: "the highest frequencies get drowned out
by the noise while the lower frequencies stay intact", so global topology is fixed at
high-noise timesteps (<https://sander.ai/2024/09/02/spectral-autoregression.html>).

**[inferred, and the correct strength of the claim]** The argument does **not** follow
from "contrast" as such — it follows from **amplitude / SNR**. A boundary with a small
luminance and chroma step has small spectral amplitude at the frequencies carrying it, so
it sits below the noise floor at higher noise levels than a high-contrast boundary of the
same spatial scale. At the timesteps where layout and region assignment are decided, a
nude-garment-on-skin edge does not exist as a signal; a navy-on-skin edge does. Stated as
an amplitude argument it is defensible; attributed to a paper about "low-contrast regions"
it is uncitable, because **there is no such paper** — I found nothing measuring VAE
reconstruction error against local contrast or chroma amplitude. **[speculative]**

**[inferred] — and this is where §3.3 and §3.4 are the same failure.** With 4 steps the
first step alone decides essentially all layout, and there is no later opportunity for a
marginal region to resolve into a distinct object. A reference that is a low-amplitude
field with no silhouette contributes nothing at the only timestep that mattered, and the
lowest-loss completion for a target whose layout was never perturbed is the input. The
three reference-side facts stack: the garment is a minority of the frame, the figure is
seated in profile so its extent is small and unregistered against an upright target, and
the garment/skin boundary is sub-threshold. That is three independent reasons image 2
carries near-zero usable low-frequency signal — consistent with the same reference
no-opping against two different people.

**[documented, wrong sign — noted for honesty]** The published contrast pathology in
few-step models runs the *other* way: DMD/DMD2 show "loss of high-frequency details and
noticeable color shifts", and CFG≠1 on a distilled model gives "burnt, over-saturated,
contrast-blown output" (<https://arxiv.org/html/2504.00996v1>). Nothing published shows
few-step models failing on low-chroma subjects.

### 3.5 Our QX arm is a published preprocessing step

**[documented]** Regenerating the garment onto a clean ground before try-on is a named
task — **Virtual Try-Off (VTOFF)** — and its stated purpose is exactly our escalation
arm. TryOffDiff: generated garment images "can be integrated seamlessly into existing
virtual try-on solutions, **enabling the more complex person-to-person try-on by
substituting the ground truth with the generated garment image**"
(<https://arxiv.org/html/2411.18350v1>).

**[documented, quantified]** Inserting VTOFF before VTON "improves p2p-VTON by minimizing
unwanted attribute transfer, such as skin color"; OOTDiffusion + TryOffDiff reaches
DressCode FID 7.9 / CLIP-FID 3.4 against CatVTON's purpose-built p2p at 8.4 — **despite
OOTDiffusion never being trained for p2p** (<https://arxiv.org/html/2504.13078v1>).

**[documented]** No published try-on system feeds a **worn, head-removed torso** as the
garment reference. Surveyed: OOTDiffusion, IDM-VTON, StableVITON, Leffa and FitDiT use
flat in-shop garments; MV-VTON uses two flat views; TryOnDiffusion segments the garment
out of a worn photo — removing head **and body**, not just the head; CatVTON accepts
either; MFP-VTON and RefTon use the whole worn person, head included, uncut. Our
representation is not a studied input class. **[documented absence]** None of the
flat-garment papers says *why* flat; **[inferred]** it is dataset convention, since paired
supervision only exists in shop-flat form.

**[documented]** The difficulty we hit is named: FW-VTON notes a worn source introduces
"occlusions and distortions in the garment image" so the model must "reconstruct the
occluded and distorted portions", whereas in-shop try-on uses "flat garment
representations, which are already clean and complete"
(<https://arxiv.org/html/2507.16010>). And person-to-person "can also transfer unintended
attributes, such as skin color, from target model to the source model"
(<https://arxiv.org/html/2504.13078v1>).

**This is the strongest external validation in the investigation.** It says V3's shape 1
is not a workaround for a constraint; it is the field's standard preprocessing stage,
which V2 reinvented independently and measured a floor-raise from.

### 3.6 Why the VLM saw nothing

**[documented]** The single best analogue for our result is LOKI: GPT-4o scores 63.9% on
synthetic-data judgment, **rising to 73.7% when a real paired reference is included** —
same model, same images, ~+10 points purely from having a referent in context
(<https://opendatalab.github.io/LOKI/>).

**[documented]** VIEScore's structure mirrors our two prompts exactly: semantic
consistency is computed *with the input condition in context*, perceptual quality *from
the output alone*. Spearman ρ for LLaVA: **SC 0.1046 / PQ 0.0319** — the open-source
reference-free leg is statistically indistinguishable from noise. It also notes MLLMs
"often fail to detect minor changes made in image editing"
(<https://arxiv.org/html/2312.14867v1>).

**[documented]** Artefact detection specifically: the strongest of 20 VLMs answers all
four artifact-side questions correctly on only 53.26%, and the axis is exactly ours —
"sensitive models often make unsupported artifact claims, while **conservative models
avoid false alarms largely by missing real artifacts**"
(<https://arxiv.org/abs/2606.12671>). Forensics-Bench puts GPT-4V at 56.75% on a binary
task (<https://arxiv.org/html/2503.15024>). The root cause is perceptual grounding:
MLLM quality scores are "not grounded in actual perception" because "critical IQA-relevant
visual features are lost during the vision-language alignment stage"
(<https://arxiv.org/html/2512.09573>).

**[inferred, well-supported] — the right framing.** It is *not* that "comparison beats
absolute". Q-Bench+ contradicts that for sub-10B models outright: "open-source MLLMs are
poor low-level comparators", with Qwen-VL-Max dropping 73.90% → 66.99% on the Compare
subset (<https://arxiv.org/html/2402.07116>). What showing the garment did was **convert
the task from low-level perceptual quality assessment — where small VLMs are near-useless
— into semantic matching against a concrete referent**, which is the one regime where they
are competent.

**[documented, ruled out]** POPE-style acquiescence bias is real but predicts the
*opposite* of our result: it would make the model answer "yes, artefacts"
(<https://arxiv.org/html/2406.17115v3>). It is the hypothesis to discard, not support.

**[inferred]** 4-bit compounds it — the vision encoder is the most quantisation-sensitive
part of a VLM, and 4-bit produces "a dramatic and often catastrophic surge in
hallucination, with smaller models experiencing extreme effects"
(<https://arxiv.org/html/2409.11055v1>). 8B × 4-bit × low-level perception is the worst
quadrant. Nobody has measured 4-bit effects on artefact tasks specifically.

**And the deterministic metrics have the same blind spot.** **[documented]** VTONQA
(8,132 images, 24,396 MOS) reports SRCC against human judgement on **clothing fit** of
**SSIM 0.056** and LPIPS(VGG) 0.140 — garment fidelity is the dimension every standard
metric predicts worst (<https://arxiv.org/pdf/2601.02945>). TryOffDiff finds SSIM assigns
its highest scores to structurally correct but colour-distorted garments, and prefers
DISTS (<https://arxiv.org/pdf/2411.18350>). This is the published version of what V2 found
by hand when `garment_sim` scored 0.78 on a no-transfer.

### 3.7 Mitigations that have a mechanism behind them

Ordered by cost, filtered to what fits one model and two calls.

**Reference preparation — CPU, no extra generation:**

| # | mitigation | targets | support |
|---|---|---|---|
| M1 | **Do not cut through the garment.** Cut where the garment does not reach, or blur/inpaint the head region rather than slicing it | collar | **[inferred]** from §3.1, plus **[documented]** AnyDoor's eroded contour and FitDiT's dilated mask, both of which exist to stop a parsing contour reading as garment geometry |
| M2 | **Erode the alpha inward before flattening**; kill the trimap ramp | hem | **[documented]** AnyDoor erodes "to filter out the information near the outer contour"; **[speculative]** that erosion beats feathering for a *reference* rather than a feature map |
| M3 | **Pad and centre**; do not crop tight to bbox | collar, hem | **[documented]** AnyDoor centres the object; **[inferred]** margin decorrelates the reference's h/w grid from the target's, weakening the position-aligned copy channel. No published padding fraction exists |
| M4 | **Upsample the reference toward the 1024² cap** before sending | no-op, collar | **[documented — BFL code]** `cap_pixels` only downsizes; a small crop yields proportionally few tokens |
| M5 | Never pass RGBA expecting alpha to mean anything | hem | **[documented — BFL code]** `to_rgb` discards it |
| M6 | **Route the reference through try-off regeneration** (our QX arm) | all three | **[documented]** §3.5 — the only mitigation with a published, quantified result for our exact setting. Costs the second call |

**Prompt — free:**

| # | mitigation | targets | support |
|---|---|---|---|
| M7 | **Name the garment type and its terminating features** ("the cardigan's stand collar", "sleeves ending at the wrist") instead of "the clothing shown in image 2" | collar, no-op | **[documented]** BFL: "prompt following is heavily influenced by the prompting-style"; the prompting guide prescribes exactly this specificity (<https://docs.bfl.ai/guides/prompting_guide_flux2>). **[inferred]** a semantic prior for "stand collar" is the only counterweight to a reference whose most legible feature is a cut line |
| M8 | **State the garment colour** when it is close to skin tone | no-op | **[inferred]** from §3.4 — the text stream can carry the region identity the image stream cannot at high noise. Not documented |
| M9 | Prefer affirmative preservation phrasing over "keep X exactly as they are" | no-op | **[speculative]** for FLUX.2 — the negation literature concerns CLIP encoders and FLUX.2 uses Mistral-3/Qwen3. Do not present as established |

**[documented]** `num_inference_steps` is still honoured on the distilled path even though
guidance is not — it is the only sampler-side lever available.

**[documented absence] — own these as our own results.** Nothing in the literature
compares white versus grey versus transparent grounds, feather radius, padding fraction,
or ghost-mannequin versus flat-lay as a try-on reference. I checked BFL's docs, the
Qwen-Image-Edit guide, Google's Nano Banana prompting guide and FASHN's own image
preprocessing guide. All silent. Any choice we make on those is an original empirical
result with nothing to cite.

### 3.8 Three cheap conversions from [speculative] to [documented]

1. **VAE round-trip L1 against local contrast** on our own reference crops — closes the
   only real gap in §3.4, and is about twenty lines of code with no API spend.
2. **Unchanged-output rate for klein-4B-distilled versus `klein-base-4B`** on the same
   pairs — nobody has published this for any distilled edit model.
3. **Reference-free versus reference-shown VLM prompt** over the same 114 outputs,
   reported as an ablation — LOKI measures the analogous +9.8 points, but not for
   artefact prompting.

## 4. Prompt construction — what is measured, and what is not

Researched 2026-08-27, prompted by the suspicion that
[v3.1's mannequin prompt](v3.1/EXPERIMENT.md) had grown too long. Shared ground because
it governs any prompt written anywhere in V3, not just the mannequin one. Labels per
[SCHEMA.md §4](SCHEMA.md).

### 4.1 Length is not the problem. Constraint count is

**[documented]** Prompt length degrades adherence only far above where we operate.
DetailMaster measures degradation at ~285-token prompts
(<https://arxiv.org/html/2505.16915>); PRISM finds adherence "dropping by up to 30% for
those over 500 tokens" (<https://arxiv.org/html/2604.18258v1>). **Our 94-word prompt is
about 120 tokens.**

**[documented]** And there is no token ceiling to hit. Qwen-Image-Edit's encoder is a
frozen **Qwen2.5-VL-7B-Instruct** (<https://arxiv.org/abs/2508.02324>), and in diffusers
the edit pipeline's `max_sequence_length` is **validated and then never applied** — the
truncation slice exists only in the text-to-image pipeline. The practical ceiling is the
VLM context window, i.e. thousands of tokens. For comparison CLIP caps at 77 and
Long-CLIP measured "the actual effective length is even less than 20"
(<https://arxiv.org/abs/2403.15378>).

**[documented]** What does collapse is *joint* satisfaction of many constraints at once.
ConceptMix scores "all k+1 concepts satisfied" and DALL·E 3 goes 0.83 → 0.50 → 0.17 →
0.08 from k=1 to k=7 (<https://arxiv.org/abs/2408.14339>). **[inferred]** But that is
close to conjunction arithmetic: at 90% per constraint, seven constraints gives 0.48 with
no interaction at all. ConceptMix does not test whether the drop exceeds independence.
So this is evidence our seven-constraint prompt will rarely be perfect — **not** evidence
that length is the mechanism.

**[documented]** The mechanism for individual dropped constraints is attention
competition, not length: Attend-and-Excite documents "catastrophic neglect, where one or
more of the subjects of the prompt are not generated", caused by cross-attention mass
concentrating on a subset of tokens (<https://arxiv.org/abs/2301.13826>). **[inferred]**
Adding a clause that introduces a *new noun* is therefore more costly than adding one that
does not — the noun enters the competition.

### 4.2 Compound instructions cost fidelity, not compliance — and that is our result

**[documented]** Complex-Edit fuses 1 to 8 atomic instructions into one and measures both
axes (<https://arxiv.org/abs/2504.13143>). Going C1 → C8 costs instruction-following
between **−0.11 and −0.81** of 10 for most models, and costs identity preservation
**−1.8 to −2.4**. Its conclusion: increasing complexity "mainly affects editing models'
perceptual quality (especially in identity preservation), while its impact on instruction
following varies across models."

**This names what v3.1's ablation found.** Going from 27 to 94 words did not make the
model *disobey* — every level produced a mannequin, cropped correctly, on white. What it
did was let the garment take the mannequin's colour on `p029`. **That is a fidelity loss,
not an instruction-following loss**, which is exactly the axis the literature says
compound prompts damage. → [v3.1/RESULTS §3c.11](v3.1/RESULTS.md#3c11-prompt-length-ablation-most-of-p73-is-doing-nothing-and-some-of-it-hurts)

**[inferred], and it is a warning about our own scoring:** if a review protocol scores
"did it follow the instruction", it is measuring the axis that degrades *least*. For a
try-on, fidelity **is** the product.

### 4.3 For Qwen specifically, do not split the prompt across calls

**[documented]** EdiVal-Agent ran the A/B directly — three instructions as three turns
versus one compound prompt — and **tested Qwen-Image-Edit by name**
(<https://arxiv.org/abs/2509.13399>):

| model | 3 sequential calls | 1 compound prompt |
|---|---|---|
| Nano Banana | **35.4** | 28.1 |
| GPT-Image-1 | **38.4** | 28.8 |
| **Qwen-Image-Edit** | 22.6 | **27.6** |
| FLUX.1-Kontext-dev | 16.6 | **19.6** |

Qwen had "the sharpest per-turn degradation of any model tested", attributed to exposure
bias — single-turn editors are trained on real images, not on their own outputs. The
paper: "when exposure bias is pronounced, compressing instructions into a single, complex
prompt can perform better; see Qwen-Image-Edit."

**This contradicts the most common practitioner advice.** Black Forest Labs' own skills
repo says to "refine through multiple small edits rather than one large one"
(<https://github.com/black-forest-labs/skills>) — written for FLUX, and EdiVal contradicts
it for FLUX.1-Kontext too. **[documented]** Complex-Edit found the same independently:
"CoT-inspired sequential editing yields much worse results than directly executing complex
instructions."

**[documented]** Reformatting the compound prompt buys nothing either. EdiVal tested four
variants on Qwen-Image-Edit: plain concatenation **27.6**, shuffled 27.1, "first…then…
last" connectors 26.9, and appending "keep {objects} unchanged" **25.9** — the single
most-repeated community tip measured **worst** of the four.

**[documented]** The better use of a second call is **Best-of-N**: Complex-Edit found
"sequential editing with Best-of-N can still barely surpass direct editing without
Best-of-N". Within a two-call budget, two parallel samples plus a selector is
better-evidenced than two sequential edit passes.

### 4.4 Negations should be rewritten as positives

Every first-party source agrees, and our prompts are full of them.

**[documented]** BFL: "FLUX does NOT support negative prompts. Always describe what you
WANT" and "writing 'a person without glasses' causes the model to focus on 'glasses' and
often generate exactly what you were trying to avoid"
(<https://docs.bfl.ml/guides/prompting_unified_technical.md>). Google: use "semantic
negative prompts" — "instead of saying 'no cars,' describe the intended scene positively"
(<https://ai.google.dev/gemini-api/docs/image-generation>). Even Imagen, the one vendor
endorsing negatives, wants bare nouns in a separate field and says "avoid instructive
language or words like 'no' or 'don't'".

**[documented]** **Qwen's own prompt rewriter forbids negation outright** — rule 8 of
`polish_prompt_zh` in <https://github.com/QwenLM/Qwen-Image>: the rewritten prompt must
contain no negation words, and if the user says "no chopsticks", the word "chopsticks"
must not appear at all.

**[documented]** The encoder-side cause: "Vision-Language Models Do Not Understand
Negation" (CVPR 2025, NegBench, 79k examples) finds VLMs "struggle significantly with
negation, often performing at chance level" (<https://arxiv.org/abs/2501.09425>). Qwen
conditions on a VLM, so this applies directly. A human study on DALL·E 3 found **no
logical operator reached >50% agreement**, with negation among the worst
(<https://arxiv.org/abs/2411.17066>).

**[documented]** Negation is properly a score-space operation, not a lexical one —
Composable Diffusion defines NOT over the score function
(<https://arxiv.org/abs/2206.01714>), which is why `negative_prompt` exists as a separate
parameter. fal exposes `negative_prompt` on `qwen-image-edit-2511` but **does not expose
`true_cfg_scale`**, which is what drives the negative branch in Qwen's reference config —
**[inferred]** so it should be verified to do anything before being relied on.

### 4.5 Aspect ratio drives subject duplication

**[documented]** ScaleCrafter reports that sampling at an aspect ratio away from training
produces "object repetition", and that a 512×1024 sample from a 512-trained model shows it
from the ratio change alone (<https://arxiv.org/abs/2310.07702>). ElasticDiffusion reports
models "replicate textures and body parts" at non-square ratios and generate "multiple
dogs for an input prompt 'one dog'" (<https://arxiv.org/abs/2311.18822>).

**[documented absence]** All of that is **U-Net text-to-image**. Both mechanistic
explanations — convolutional receptive field, U-Net deep-block features — are U-Net
specific and do not transfer to Qwen-Image-Edit's MMDiT backbone without new evidence.
**Nobody publishes a duplication rate against aspect ratio for any editing model.**

**[documented — measured here]** So it was tested directly, and it holds for our case.
→ [v3.1/RESULTS §3c.12](v3.1/RESULTS.md#3c12-aspect-ratio-causes-the-duplication-and-padding-fixes-it)

**[documented]** And the obvious prompt-side fix is unlikely to work: T2ICountBench finds
"all state-of-the-art diffusion models fail to generate the correct number of objects" and
that "prompt refinement … generally do[es] not improve counting accuracy"
(<https://arxiv.org/abs/2503.06884>). **Adding "exactly one mannequin" is the intervention
the literature says fails.**

### 4.6 Two things to check about fal before trusting any of this

**[documented]** Qwen's README states: "editing results may become unstable if prompt
rewriting is not used. Therefore, we strongly recommend applying prompt rewriting", and
Alibaba's own API defaults `prompt_extend: true`.

**Checked 2026-08-27. fal does not rewrite. Our prompts reach the model verbatim.**

Two pieces of evidence:

1. **[documented]** The endpoint schema exposes **13 parameters and none of them is prompt
   rewriting** — no `prompt_extend`, no `enable_prompt_expansion`, no toggle of any kind
   (`https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/qwen-image-edit-2511`).
   Alibaba's own API has `prompt_extend` and defaults it true; fal has no such field.
2. **[documented — measured here]** Two separate calls, identical prompt, identical seed,
   returned **byte-identical images**: max pixel difference 0, 0.00% of pixels differing.
   An LLM rewriter in the path would have to be deterministic *and* cached to produce
   that.

**[inferred]** The second test rules out *stochastic* rewriting rather than rewriting
altogether — a temperature-0 rewriter would also be reproducible. Combined with the
absent parameter, no rewriting is the reasonable reading.

**What follows, both ways:**

- **Good:** every prompt result in v3.1 measured **our wording**, not a rewriter's
  paraphrase of it. The prompt-iteration record stands.
- **Bad:** we are running the configuration Qwen itself calls unstable, and unlike
  Alibaba's API there is no switch to turn it on. Any instability attributed to a clause
  may be the instability Qwen warns about.

**Also found in the schema, and directly useful:** `image_size` — *"If None, uses the
input image dimensions."* We have been passing None, which is why a landscape input
produced a landscape canvas and the duplication in
[v3.1/RESULTS §3c.12](v3.1/RESULTS.md#3c12-aspect-ratio-causes-the-duplication-and-padding-fixes-it).
**Setting it explicitly is a second fix for that, and one that costs no padding.**

### 4.7 What the literature does not answer

- **Whether restating or overlapping constraints helps or hurts.** Nothing measures it.
  Redundancy has to be ablated on our own set.
- **Whether Qwen-Image-Edit-2511** — as opposed to the original — degrades with instruction
  count. EdiVal tested the original, and 2511's headline change is precisely "mitigate
  image drift, improved character consistency", i.e. the exposure-bias axis. Its
  sequential-versus-compound tradeoff may have moved. **[speculative]**
- **Positional weighting.** BFL and fal both assert that earlier tokens dominate; **no
  paper measures it.** The defensible version is the attention-competition finding in
  §4.1, which is about *which* tokens win, not *where* they sit.

## 5. The map

| | question | status |
|---|---|---|
| **[v3.0](v3.0/EXPERIMENT.md)** | What are BC_klein's and QX's failure and success conditions, and what causes them? | **open** — diagnosis complete, [new run specified](v3.0/TEST.md) |
| **[v3.1](v3.1/RESULTS.md)** | How far does the ghost-mannequin reference get? | **open** — `p7` chosen from eight prompts, 28 extractions and 28 edits on disk, unscored |
| **[v3.2](v3.2/EXPERIMENT.md)** | Does running the klein edit twice recover what PHEAD loses by skipping the bald pass? | **concluded, negative** — the second pass persists PHEAD's defects rather than correcting them; unusable on all 28 |

### 4.1 Closed side-branches

Things tried and dropped before they earned a directory. Kept because a negative result
is a result, and because the next person will otherwise try them again.

**All-Qwen (`QQ`), 2026-08-26 — dropped.** Qwen extracts, Qwen edits. Held against klein
with the *identical reference file*, so the only variable was the editor. 28/28 generated
without endpoint failure and unusable by eye: **Qwen does not hold the person — identity,
background and framing move together**, where klein keeps the frame. Conclusion: *klein
is the better editor of the two.* Frames: `v3/runs/v3.0b/gen/*__QQ.jpg`; prompt: `QWEN`
in `v3/build/run_v30.py`.

One thing it cost nothing to learn and is worth keeping: Qwen-Image-Edit-2511 **accepts
two input images**. V2 only ever called it with one, so this was unknown rather than
assumed.

A single smoke frame had shown Qwen holding body shape better than klein where both klein
arms slimmed the subject. It was labelled *n = 1, not a finding* at the time and did not
generalise — the worked example of why that label is worth writing down.

`v3.0` owns the whole diagnosis: the four BC_klein failures, QX's single failure and its
extraction drift, the instruments that missed everything, and the 36-pair run designed to
turn one-off observations into conditions. Later investigations will be drawn from its
conclusions, not from this document.
