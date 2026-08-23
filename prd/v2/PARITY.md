# Self-hosted parity — what running our own weights actually found

**The question.** Every number in V2 came from **fal**. fal is a serving substrate
for open checkpoints, not a model source — but nothing had been verified on weights
we downloaded and ran ourselves, and V2's premise is open weights in the deploy path.

**The answer, first.** klein reproduces. The generations are visually equivalent —
right person, right garment, right scene. But the run found **one invisible
deployment requirement and two bugs in the shipped pipeline code**, and the fal path
had concealed all three.

Evidence: [`v223_self_hosted_parity.html`](../../v2/artifacts/v223_self_hosted_parity.html)
— 8 pairs, drag to wipe. Data: `v2/runs/openstack/`.
Notebook: [`v2/v2_openstack.ipynb`](../../v2/v2_openstack.ipynb).

Run on a Colab L4, FLUX.2 klein 4B distilled in **fp16, unquantised**, seed 46,
identical prompts and references. Qwen3-VL-8B in 4-bit — the same configuration the
gate evaluation used, so it is consistent with the numbers it is compared against.

---

## 1. The finding that matters — normalise to ~1 MP

**fal's klein endpoint silently normalises every request to ~1 MP.** All 456 stored
outputs are 832×1248 (1.04 MP) regardless of person inputs ranging 682×1024 to
1024×1536. Nothing in the API documents this and nothing in our code did it.

Left to itself, diffusers sizes from the inputs. The self-hosted run generated at
**3.45 MP average** — and the result was *worse*:

| | fal | self-hosted, un-normalised |
|---|---|---|
| output | 832×1248 (1.04 MP) | 1344×2048 – 1664×2496 (avg 3.45 MP) |
| high-frequency detail | baseline | **−32%** on the measured pair |
| file size | 356 KB | 667 KB — **bigger and softer** |
| time per generation | — | **128 s** against ~39 s at 1 MP |

**2.65× the pixels, 32% less detail, 3× the compute.** Above its trained resolution
a diffusion model cannot populate the extra pixels with real structure, so it
interpolates. Empty resolution.

Ruled out as a cause: JPEG. The self-hosted files are nearly twice the size on disk
at comparable bits-per-pixel.

**This is a deployment requirement**, recorded in
[ARCHITECTURE.md §6b](ARCHITECTURE.md). A self-hosted service that skips it ships
softer images than every number in these documents was measured on, and pays triple
the GPU. It stayed invisible for the whole programme because fal did it for us.

**The right architecture is generate small, upscale after:**

| | klein @ 2.75 MP | klein @ 1 MP → SeedVR2 ×2 |
|---|---|---|
| final size | 1344×2048 | 1664×2496 |
| detail | −32% hf | **+12% hf** (v2.4) |
| time | 128 s | ~39 s + ~9 s |
| identity | unguarded | floor at 0.90, Lanczos fallback |

---

## 2. Two bugs in the shipped pipeline, found by executing it

Both lived in `v2/pipeline/`, the deliverable — not in the notebook. **The parity run
was the first time that code had ever been executed end to end**; every published
number came from analysis over stored outputs. The measurements were sound; the
program was not.

### Identity compared on the wrong scale — 6 false escalations in 8

`failure_gate.check_identity` returns `_norm(cos, 0.18, 0.42)`, a **normalised
margin**: raw cosine 0.88 → 1.000, raw 0.36 → 0.755. Every threshold in these
documents is on that scale, because that is the function the analysis used.

`pipeline/upscale.identity_cos` returns the **raw cosine**, and `input_comparison`
applied the 0.90 threshold to it. Same-person cosines across a generative edit run
0.80–0.92, so it fired on nearly everything.

Re-scored with the correct function: **all 8 clean, six escalations withdrawn.** The
analysis that added identity to the escalation rule was right; only the
implementation was wrong.

**`identity_escalate` (0.90 margin) and `identity_floor` (0.90 raw) are the same
number meaning different things.** Both are now documented with their scale.

### The router returned 0.0 instead of failing — routing never happened

`hair_over_garment` read prepared crops from `v2/runs/crop_screen/`, which is
gitignored and absent from a fresh clone. It returned `0.0` rather than raising, so
**every set routed to PHEAD** and the router was silently disabled.

Fixed: `masks.hair_from_raw` computes it from the raw image using the repo's own
mask stack. Verified — p021 20.0% against 19.5% stored, p009 8.1% / 7.2%,
p019 13.7% / 13.5%.

**The pattern is the lesson, not the instances:** both failures returned a plausible
default instead of raising. In production the first triples cost and the second
disables a component, and neither logs anything.

---

## 3. What the published numbers do and do not depend on

**Unaffected.** The headline — 2.158 generations/request, 31 perfect / 7 ok / 0 fail
— was recomputed after both fixes and matches exactly. It comes from analysis over
the labelled CSVs, where `chk_identity` was always the margin and
`hair_over_garment` was always the stored value.

**Withdrawn.** The arm-agreement figure from this run (62%). It measured the two
bugs, not the weights.

---

## 4. Still untested

**SeedVR2 self-hosted — a project, not a cell.** The weights are open and
downloadable (Apache-2.0, `seedvr2_ema_3b.pth`, 13.6 GB, ungated — verified with a
no-auth fetch). What is missing is a usable inference path. From the ByteDance repo:

| requirement | consequence |
|---|---|
| `flash_attn==2.5.9.post1` | needs Ampere or newer; will not build on a T4 |
| **`apex`** | NVIDIA apex, awkward to build reliably |
| `torchrun --nproc-per-node` | distributed by design |
| **video-only** | no documented single-image path |
| *"1 H100-80G can handle 100×720×1280"* | their own stated hardware baseline |

**fal is doing real wrapping work to expose this as a single-image endpoint.** That
cost was invisible while we consumed it as an API.

The notebook therefore leaves an explicit hook rather than a guessed API; unset,
`upscale.seedvr2` returns `None` and the shipped Lanczos fallback takes over, which
is the designed degradation and still exercises the identity floor.

**Three options for deployment**, and the stage is `high_resolution=False` by
default so none of them block shipping:

1. **Reproduce fal's wrapping** — apex, flash-attn, a single-image adapter, H100-class
   hardware.
2. **Swap the upscaler** for one with a clean single-image path — Real-ESRGAN or
   AuraSR-v2, both already on v2.4's candidate list.
3. **Ship Lanczos.** Free, deterministic, already the fallback. Costs the +12%
   high-frequency gain SeedVR2 measured.

**Qwen-Image-Edit-2511** (the QX extractor, 57.7 GB) was not downloaded. The 38 test
garments already have their QX references, so escalation worked; building one for an
**unseen** garment is untested.

**Decision agreement.** A corrected re-run is ~15 minutes on cached weights and would
recover the arm-agreement number plus a clean per-generation time at 1 MP — which is
what the self-host-versus-fal cost case rests on, and why that estimate is currently
a wide $3–11k/month against fal's ~$19.5k.

---

## 5. The meta-point

The parity run was framed as a formality — confirm the weights behave, tick the box.
It instead found a requirement that changes deployment, two bugs that would have
shipped, and it did so because **someone ran the code and then looked at the
pictures**. The instruments said 62% agreement, which was wrong; the eye said
"correct swap, bad pixels", which was right on both counts.

That is the fifth time in this programme an instrument has said the opposite of the
truth and a human looking at one image has caught it.
