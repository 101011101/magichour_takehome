# V3 general investigation — what is actually wrong

Opened 2026-08-26. The general investigation document under
[SCHEMA.md](SCHEMA.md): the diagnosis every sub-investigation stands on. It says what
is wrong and by what mechanism, and it is where the `v3.x` split is drawn from. It
reports no sub-investigation's outcome — when one lands, this file gains a link.

Evidence bundle: [`v3/artefacts/`](../../v3/artefacts/). Side-by-side page:
[`v3/report/artefacts.html`](../../v3/report/artefacts.html).

[V3's brief](README.md) says "V3's job is the four failures." This document says what
the four failures *are*, at the level of the pixel and the mechanism, because the
answer changes which of the three candidate shapes is worth building first.

---

## 1. The headline: three of the four are not artefacts

The word "artefact" is doing damage. Measured over the same 38 sets, `v223_vlm_eval.csv`
records the VLM `artefact` prompt returning **CLEAN on all 114 outputs — including
every human `fail`**. V2 wrote the conclusion down and V3 has not absorbed it:

> our failures are not artefacts — they are competent photographs of the wrong thing.

Looking at the four frames confirms it. Only one is a render defect.

| set | hair | what BC_klein produced | class |
|---|---|---|---|
| `HD_p023` | 16.9% | person unchanged, still in the floral kimono. SSIM vs the person input **0.982** — the degenerate IF = 0 / IP = 10 point, [§3.3](#33-the-no-op-is-a-named-failure-mode-and-4-steps-is-why) | **returns the input unchanged** |
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
([`04_ref_BC_klein.jpg`](../../v3/artefacts/cases/dualuse_navy_peacoat_onmodel+p012/04_ref_BC_klein.jpg))
cuts flat through the neck just above the cardigan's stand collar and leaves a bare
neck stub. The output has no collar and an elongated neck. This is the over-cut V2
already logged — "head removal takes the collar on several worn references (p004, p022
clearest)" (`prd/v2/RESEARCH_LOG.md`, 2026-08-15) — showing up in a *shipped* arm
rather than in a discarded crop iteration.

The mechanism behind all three is [§3](#3-why-this-happens-at-the-model-level): image 2
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
test, YCrCb, recorded in [`manifest.json`](../../v3/artefacts/manifest.json)) and
**carries no signal**. On `p023` every reference scores 0.91–0.99 *including QX's*,
because a coarse chroma box cannot tell a nude tank from the arm wearing it. On `p007`
QX scores a clean 0%, but its non-white pixels are near-achromatic cream, so anything
would. Only `p012`, a dark navy, gives a number that means what it looks like. The
number stays in the manifest, labelled; the argument rests on the frames.

Global SSIM is similarly narrow. It isolates the `HD_p023` no-op at 0.982 and separates
nothing else — on the other three cases all four arms sit within 0.01 of each other,
failure and rescue alike.

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

## 4. `p015+p007` is the expensive one, and the bald pass caused it

Hair damage on `p007` is **4.5%**. The bald pass buys nothing at that level, and
**PHEAD — the same crop without the bald call, one generation instead of two — is
`perfect` on this set.** The second klein call re-rendered the reference, softened its
edges, and the softened edge is what got copied.

BC_klein's cheapest failure is caused by a call it did not need to make.

This is a direct argument against one line in the V3 brief. V3 drops the router as
complexity, but the hair-damage figure is a number the CPU mask stack already computes,
and choosing PHEAD over BC_klein *removes* a generation. It is one model, one `if`, and
one or two calls — inside the constraint, not outside it. The V2 sweep
([ARCHITECTURE §9.2](../v2/ARCHITECTURE.md)) puts a cut-point of 0.05–0.09 at
**29 / 6 / 3 at 1.55 generations** against flat BC's 28 / 6 / 4 at 2.000: better *and*
22% cheaper.

Standing caveat, carried from [the lock list](../v2/LOCK.md#3-known-wrong-at-the-moment-of-freeze):
0.08 was chosen by reading the same 38 sets it is scored on, and the held-out
recomputation over all 48 references was never run. "Drop the router" and "make the
bald pass unconditional" are separate decisions, and only the second one costs
`p015+p007`.

## 5. Why QX rescues all four, and what it costs

QX (`QX_qwen_p1`, Qwen-Image-Edit-2511 regenerating the garment onto white) takes all
four: perfect, perfect, perfect, ok. The mechanism is the whole explanation — a
regenerated reference **has no cut boundary to copy and no fringe to reproduce**. There
is nothing at its edges that came from a mask.

That is also why it cannot fail the way BC_klein fails, and why V2 measured **zero
overlap** between their failure sets.

The cost is measured and it is not small (`prd/v2/v2.2/EXPERIMENT.md` §AC-A):

- hue drift **21–30° on every reference**; worst `p009` at **88°**
- texture retention as low as **×0.23** (`p030`'s pattern)
- only `p019` and `p028` come back clean
- "No extraction arm currently returns the same garment"
- and the trap worth stating out loud: the reviewer *preferred* the Qwen crops by eye
  while they were losing half the pattern. Cleanest-looking and most faithful pull apart.

That trade is what 20 perfect / 17 ok / 1 fail means. QX raises the floor and lowers the
ceiling.

It is also not an invention of ours. Regenerating the garment onto a clean ground before
try-on is a published task — **Virtual Try-Off** — whose stated purpose is enabling
person-to-person try-on, with a measured gain for exactly this case, and no published
system feeds a worn head-removed torso the way we do. See
[§3.5](#35-our-qx-arm-is-a-published-preprocessing-step). That is the strongest external
validation in this investigation and it changes the standing of shape 1 in §7. **V3 shape 1 — klein as the extractor — inherits the trade, and klein's own
extraction quality is unmeasured; QX's numbers are Qwen's.** Measure drift on klein
extractions with `v2/build/extraction_drift.py` before treating shape 1 as a
substitution.

## 6. Nothing caught any of them

For all four BC_klein failures, from `v223_vlm_eval.csv`:

| set | artefact | usable | tryon | transfer | garment | human |
|---|---|---|---|---|---|---|
| `p015+p007` | CLEAN | OK | **PERFECT** | OK | OK | fail |
| `dualuse_navy_peacoat_onmodel+p012` | CLEAN | OK | **PERFECT** | FAIL | FAIL | fail |
| `HD_p023` | CLEAN | OK | **PERFECT** | OK | FAIL | fail |
| `HD_p023+p019` | CLEAN | OK | **PERFECT** | OK | FAIL | fail |

The `tryon` prompt calls every one of them perfect. The `artefact` prompt is dead across
the whole eval. The mechanism, and why the reference-shown prompt is the only one that
works, is [§3.6](#36-why-the-vlm-saw-nothing) — briefly: showing the garment converts the
task from low-level perceptual quality assessment, where sub-10B VLMs are near-useless,
into semantic matching against a referent, where they are competent. The same blind spot
is measured for our deterministic metrics: SSIM's rank correlation with human judgement of
**clothing fit is 0.056**. Only `garment` — the one prompt that is shown the reference — fires, on
three of four, and the case it misses is `p015+p007`: **the one true render artefact is
the one every instrument is blindest to.**

V3 ships no gate at all, so this failure would ship silently. One CPU SSIM against the
person input costs nothing, needs no model, and catches `HD_p023` at 0.982. It is not a
harness.

## 7. What this implies for the three candidate shapes

The `v3.x` split is not fixed yet. What follows re-orders the brief's own candidate
list against the mechanism above; it is not the investigation map.

Re-ordering [the brief's table](README.md#4-the-one-thing-to-carry-over-qxs-mechanism)
against the mechanism above:

| shape | verdict |
|---|---|
| **3 — regenerate only the damage** | Promoted to first. All four failures are boundary defects, and the mask stack already knows where the boundary is. `p023` is the honest test: RESULTS.md flags that its damage is *open, not enclosed*, which makes inpainting a category error — so this either fixes `p012`/`p007` and fails `p023`, or the framing is wrong. Either outcome is information. |
| **1 — klein as extractor** | Promoted on the research, qualified on the evidence. The *stage* is standard practice with a published quantified gain for person-to-person ([§3.5](#35-our-qx-arm-is-a-published-preprocessing-step)); what is unmeasured is klein's ability to perform it. Score it on drift (hue, pattern retention), not only on tier, or it reproduces QX's ceiling without QX's provenance. |
| **2 — one prompt, bald *and* isolate** | Last. It asks a 4-step distilled call to do two edits, and `p023` shows that a single confusing reference is enough to make klein no-op. |

Plus two that are not on the brief's list and cost nothing:

- **Make the bald pass conditional on hair damage.** Free, already measured, and the only
  change that touches `p015+p007`.
- **Fix the reference before fixing the model.** Six of the mitigations in
  [§3.7](#37-mitigations-that-have-a-mechanism-behind-them) are CPU-side reference
  preparation — do not cut through the garment, erode rather than feather, pad and centre,
  upsample toward the 1024² cap that BFL's code will never reach on its own — and two are
  prompt wording. None costs a generation. The cropper was built to make the boundary
  *cleaner*; the mechanism says it should be made *less informative*, which is a different
  objective and has never been tested here.

---

## 8. Evidence paths

| what | where |
|---|---|
| Assembled bundle, four cases, inputs + intermediates + all four arms | [`v3/artefacts/cases/`](../../v3/artefacts/cases/) |
| Manifest with provenance and metrics | [`v3/artefacts/manifest.json`](../../v3/artefacts/manifest.json) |
| Rebuild the bundle | [`v3/artefacts/build_bundle.py`](../../v3/artefacts/build_bundle.py) |
| Side-by-side page | [`v3/report/artefacts.html`](../../v3/report/artefacts.html) |
| Human tiers, all 38 sets × 3 arms | `v223_perfect_tier_picks.csv` |
| VLM verdicts, 570 rows | `v223_vlm_eval.csv` |
| Every arm failure with its rescue | `v2/report/failures.html` |
| Extraction drift, QX's cost | `prd/v2/v2.2/EXPERIMENT.md` §AC-A; images `v2/runs/acab/` |
| Crop mechanism and its known defects | `v2/build/garment_crop.py` header; `prd/v2/DECISIONS.md` §3 |

## 9. One correction to the V2 record

[`prd/v2/EDGE_CASE_INDEX.md`](../v2/EDGE_CASE_INDEX.md) §3c states "BC_klein's only two
failures (`HD_p023`, `HD_p023+p019`)". There are **four**. `v223_perfect_tier_picks.csv`
and `v2/report/failures.html` both agree on four; §3c is wrong. The V3 brief's
"V3's job is the four failures" is right, and the index it points at is not.
