# V2 — what is left

Ordered. Everything above the line closes V2; everything below is iteration.
Design: [ARCHITECTURE.md](ARCHITECTURE.md) · History: [DECISIONS.md](DECISIONS.md)

Last updated 2026-08-22.

**v2.2 is closed.** The harness is settled at 2.158 generations/request,
**31 perfect / 7 ok / 0 fail** — essentially the cost of the best single arm
(2.000 for 28/6/4), and nothing ships broken.

**v2.4 is partly closed.** The realism pass is validated end to end over harness
output and is now **conditional** — skip if already sharp, revert if it damages
the face. 24% fewer calls, no frame below 0.90 identity, essentially all of the
sharpening benefit. See [v2.4/RESULTS.md](v2.4/RESULTS.md). What remains of v2.4
is the *replacement* question, not the validation one.

---

## Blocking V2 completion

### 1. ~~The end-to-end run on fal~~ — **dropped as redundant** (2026-08-22)

Written when `arms.generate` still raised `NotImplementedError`, to prove the
assembled program actually runs. **The self-hosted parity run did that** — and
proved it by executing the code for the first time and finding two bugs.

It also had a flaw worth recording: a fresh fal run would produce **new images with
no human tiers**. The 31 / 7 / 0 result depends on the labels attached to the
*existing* outputs, so fresh generations would need a full re-marking session before
they could be scored at all. That is $2–3 plus hours of eye time to reproduce a
number we already have from replaying the decision logic over labelled outputs.

**What the report should say instead:** the harness result is a replay of the
shipped decision rule over 456 human-labelled generations, and the assembled program
has been executed end to end self-hosted. Those are two different claims and both
are now true.

### 2. Self-hosted parity run — **first pass done**, see [PARITY.md](PARITY.md)

klein reproduces: generations visually equivalent on weights we control. The run
found **one deployment requirement** (normalise to ~1 MP — fal was doing it
silently; skipping it costs 32% of the detail and 3× the GPU) and **two bugs in
`v2/pipeline/`** that would have shipped (identity compared on the wrong scale,
and a router that returned 0.0 instead of failing). All three fixed.

Published numbers are unaffected — recomputed and identical. The arm-agreement
figure from that run is withdrawn; it measured the bugs.

**Remaining:** a corrected re-run (~15 min on cached weights) for the
arm-agreement number and a clean per-generation time at 1 MP; SeedVR2 self-hosted
(no diffusers pipeline, needs the ByteDance repo); Qwen-Image-Edit for the
unseen-garment path.

#### Original scope

Every number in every V2 document is a **fal** number and V2's premise is open
weights in the deploy path. **Needs a rented GPU or Colab** — the local machine is
an i3 with 8 GB and no GPU.

**Notebook ready:** **`v2/v2_openstack.ipynb`** + `v2/runs/openstack_bundle.zip`
(18 MB) — the whole harness on open weights, no fal anywhere. Rebuilds garment
references from **raw** images, so it doubles as the unseen-garment path.
`RUN_QWEN_EXTRACT=False` skips the 57.7 GB extractor, which is only needed to build
a QX reference for a garment we have never seen; the 38 test sets already have
theirs. That halves the download to 56 GB.

**L4 (24 GB) is the sweet spot** — klein fits with CPU offload at ~40% of an A100's
cost. Weights cache to Drive so a disconnect does not repeat the download.

(`v2/v2_parity.ipynb` was the narrower first pass and is superseded by it.)

Order of value: **the editor (klein)** carries 100% of requests and is the largest
single risk; **the VLM** is the quickest win because its numbers currently come
through OpenRouter, a third-party proxy, so it is the weakest link evidentially.

Parity means *equivalent quality and the same harness decision*, **not** pixel
equality — different schedulers and precisions will never reproduce a diffusion
output exactly, and chasing that would be a category error.

### 3. Licence — verified, blocker **resolved** (2026-08-22)

**The parser was swapped.** `mattmdjaga/segformer_b2_clothes` (non-commercial) is
replaced by **SCHP ATR** (`basso4/humanparsing/parsing_atr.onnx`, upstream MIT
© 2020 Peike Li, ResNet-101, no NVIDIA lineage), which emits the **same 18 ATR
classes** so nothing downstream changed.

**Verified equivalent, so the 38-set numbers transfer.** Crop IoU against the
SegFormer references over 10 hard cases: **mean 0.999, worst 0.998.**

One regression was found and fixed. SCHP labelled 99.1% of p019's raised **collar**
as head where SegFormer labelled 99.6% of it garment, costing 7.2% of the crop —
and the collar sits *above* the pose neck line, so the existing bound did not reach
it. Retuning that bound traded p019 against p021, the same
one-reference-for-another signature that ended the geometric era. The fix instead
follows the principle already in the code — *each model does only what it is good
at*: the parser supplies the head **shape**, pose the **extent**, and **MediaPipe's
clothes class vetoes** anything it is confident is garment. p019 went 0.927 → 0.999
with no other reference moving. `HEAD_CLOTHES_GUARD=0` disables it;
`PARSER=segformer` restores the incumbent for comparison.

**Still owed:** regenerate the 22 garment references under the new parser and
re-run the 38 sets, so the published numbers are measured on the shipped parser
rather than inherited on an equivalence argument. At IoU 0.999 the outcome should
not move — but *should not* is not *did not*.

#### The original finding, retained



**Everything clears except one, and that one is a hard blocker for production —
but not for anything we are doing between now and the report.**

| model | licence | deploy |
|---|---|---|
| **FLUX.2 klein 4B** (what we use) | **Apache-2.0** | yes |
| *klein 9B* | flux-non-commercial | no — the split is real |
| Qwen3-VL-8B · Qwen-Image-Edit-2511 · SeedVR2 · AuraFace · MediaPipe Pose | Apache-2.0 | yes |
| BiRefNet_lite | MIT (upstream repo) | yes |
| **`mattmdjaga/segformer_b2_clothes`** | **`other` → NVLabs SegFormer** | **NO** |

**The blocker, verified directly against the licence text.** The card sets
`license: other` and links to the NVLabs SegFormer LICENSE, §3.3 of which reads:
*"The Work and any derivative works thereof only may be used or intended for use
**non-commercially**… NVIDIA and its affiliates may use the Work and any derivative
works commercially."* Non-commercial is defined as *"research or evaluation purposes
only."* The weights derive from NVIDIA's MiT-B2 backbone, so it propagates.

**We had the risk backwards.** The dataset (ATR) was the suspected problem; it is
permissive-ish, requiring only citation and explicitly naming commercial research.
The *model* licence is the binding constraint and it was on the card all along.

**Why deferring is safe.** The licence permits *research or evaluation*, which is
exactly what every run, the report, and any internal review are. **Nothing before
production deploy is affected.**

**The trigger:** swap before the pipeline runs on real user requests. Not before.

**The replacement is same-shape and already identified.** SCHP (Self-Correction
Human Parsing), ATR checkpoint — verified **MIT, © 2020 Peike Li**, ResNet-101
backbone, no NVIDIA lineage, **same 18 ATR classes**. The `ATR` class grouping and
the pose-bounded / nose-component head rule need no rework. ~66M params against
27.4M. Roughly a day: load, then verify against p021, p028, p016, p009, p023.

**Two traps to remember when it is picked up:**

1. `fashn-ai/fashn-human-parser` is **also blocked** (`license_name:
   nvidia-segformer`). Every SegFormer-lineage parser inherits this, and third-party
   re-uploads tagging those weights `mit` or `apache-2.0` are **mislabels, not
   relicensings**.
2. `MnLgt/yolo-human-parse` has Apache weights but runs on **AGPL-3.0** ultralytics —
   normally a non-starter in a hosted product.

**One latent trap worth a CI assertion now**, unrelated to the above: insightface's
*code* is MIT but its pretrained packs (`buffalo_l`, `antelopev2`) are
non-commercial. The repo correctly points `FaceAnalysis` at AuraFace, but a bare
`FaceAnalysis()` anywhere, or any path that lets insightface auto-download, silently
pulls NC weights. Assert that no `models/buffalo_*` ever appears in the cache.

### 4. The V2 report

Draws on ARCHITECTURE.md, DECISIONS.md and the numbers from step 1.

---

## Iteration — not blocking

### 5. Binary forced-choice prompts, and fp16

The single highest-value follow-up on the gate. The model hedges — **331 of 570
verdicts were `OK`**, only 49 `FAIL` — which is exactly what caps recall at 51%.
Removing the middle option and running fp16 instead of 4-bit are both untried and
both plausibly worth several points. ~5 minutes of runtime in the same notebook.

### 6. Recompute the hair threshold over all 48 references

14% is fitted on 38 sets. AUC 0.862 is the honest number; the cut-point is not.

### 7. v2.3 (artefacts) — scope has shrunk, decide after step 1

Its founding question was whether artefacts can be repaired. Two results bear on
it: the VLM cannot *detect* artefacts in our outputs (the `artefact` prompt never
fired), and the harness already removes 3 of 4 shipped failures. Re-scope to
whatever survives the end-to-end run rather than running the original plan.

### 8. v2.4 — what is left of it: the replacement question only

Validation and the conditional trigger are **done** ([RESULTS](v2.4/RESULTS.md)).
What remains is whether anything *beats* SeedVR2. Highest-priority candidate:
**Z-Image Base + PAI Fun tile-ControlNet + UltraReal LoRA** (self-host only) — the
only remaining route to **de-glossing**, which SeedVR2 does not do and never did.

Also worth revisiting cheaply: the realism thresholds (2.5, 0.90) are fitted on 38
frames, and the identity figure is confounded by comparing against a 2× upscale of
the same frame. Re-measure at matched scale.

### 9. Anatomical plausibility pre-filter

MediaPipe Hands finger counting, impossible pose landmarks. Free, deterministic,
runs ahead of VLM-A. Narrow, but the only deterministic artefact signal available.

### 10. The user-specification branch has no evidence

Nothing in the test set carries a user-named garment region. Either add cases or
mark it reasoned-not-measured in the report.

### 11. Independent-score tie-break — revisit only if QX stops dominating

Scoring each candidate separately and comparing beat the pairwise call (4/5 vs
3/5) and is structurally sounder — no position to be biased by. Still lost to
"always take QX" (5/5) on n = 5.

---

## Housekeeping

- [ ] `v2/artifacts/index.html` is stale — lists 8 pages, 26 exist.
- [ ] `v221_crop_tuning_pcrop.html` is a dead orphan; `pcrop_page.py` writes the
      `_phead` page but still carries a stale `<title>...PCROP</title>`.
- [ ] Branch `v2.2.3-harness` is unmerged and unpushed.
