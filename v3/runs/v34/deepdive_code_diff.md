# Self-hosted klein vs fal: code-level differences (deep dive)

Date: 2026-08-31. Scope: `v3/colab/lib/klein_local.py` (diffusers `Flux2KleinPipeline`) versus
the BFL reference implementation and the fal endpoint `fal-ai/flux-2/klein/4b/distilled/edit`,
same weights, same E3 prompt, same images. Every claim below is either quoted from source that
was fetched and read in full, or marked **unverifiable**. No fal calls were made; the fal
evidence is the 20 probe responses already in `v3/runs/v34/probe_fal/out/*.json` and the 186
outputs in `v3/runs/v34/judge_fal_vs_a100/gen/`.

Sources read (full files, not summaries):

| Source | Version |
|---|---|
| `src/diffusers/pipelines/flux2/pipeline_flux2_klein.py` | diffusers **v0.40.0** (PyPI 2026-08-20; byte-identical to `main` on 2026-08-31). Our notebooks run `pip install -U diffusers` (`v3/colab/v34_a100.ipynb`, `v3/colab/v33_ironman.ipynb`, cell 3), so 0.40.0 is what the 08-30 and 09-01 runs used. The three quoted behaviours (1 MP cap, `> 4300` mu branch, `height = height or image_height`) are unchanged since the first commit `61f17566` (2026-01-15). |
| `src/diffusers/pipelines/flux2/image_processor.py`, `src/diffusers/image_processor.py`, `src/diffusers/schedulers/scheduling_flow_match_euler_discrete.py`, `src/diffusers/models/transformers/transformer_flux2.py`, `src/diffusers/models/autoencoders/autoencoder_kl_flux2.py` | diffusers `main`, 2026-08-31 |
| `black-forest-labs/flux2` — `src/flux2/sampling.py`, `util.py`, `model.py`, `text_encoder.py`, `autoencoder.py`, `scripts/cli.py`, `README.md`, `docs/flux2_klein_kv_cache.md` | commit `50fe5162` (`main`, 2026-08-31) |
| `huggingface.co/black-forest-labs/FLUX.2-klein-4B` — `model_index.json`, `scheduler/scheduler_config.json`, `transformer/config.json`, `text_encoder/config.json`, `tokenizer/tokenizer_config.json`, `README.md`, safetensors headers | `main` |
| fal OpenAPI `https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/flux-2/klein/4b/distilled/edit` and the model page | 2026-08-31 |

Base URLs used below:
`D` = `https://github.com/huggingface/diffusers/blob/v0.40.0/src/diffusers/`,
`B` = `https://github.com/black-forest-labs/flux2/blob/50fe5162777813d869182b139e83b10743caef15/`.

---

## 0. The one-paragraph answer

Our call passes `height, width` = image 1 scaled to **1.15 MP**; the pipeline (and BFL, and fal
by observation) size the **reference** copy of image 1 to **≤ 1.0 MP**. That single choice
produces two systematic, code-verified differences that fal never has:

1. **A different sigma schedule.** `compute_empirical_mu` (identical in diffusers and BFL) has a
   hard branch at `image_seq_len > 4300` tokens (= 1,100,800 px). Every 1.15 MP output we make
   is above it (4,366–4,489 tokens) and gets `mu ≈ 1.20`; every fal output is ≤ 4,096 tokens
   and gets `mu ≈ 2.29`. Four-step sigmas: **ours `[1, .909, .769, .526, 0]`** vs
   **fal `[1, .967, .908, .767, 0]`**. A step-distilled model is being run off its schedule.
2. **A misaligned reference grid.** Our output latent grid is 1.15 MP (e.g. 80×55 tokens) while
   the person-reference grid is 1.0 MP (77×53 tokens). RoPE positions are absolute integers, so
   the reference token that "is" a given wearer pixel sits up to 3–4 tokens (48–64 px) away from
   the output token at the same place, worst at the bottom/right (legs, hem, feet). fal's output
   grid equals its reference grid to within one token.

Everything else that was hypothesised (guidance value, step count, PNG vs PIL, prompt
truncation, RoPE offsets, VAE sampling, text-encoder layers, sequence order) was checked and is
**the same** on both paths, up to numerics (§3). What could not be verified is listed in §4.

Caveat from the repo's own data: `prd/v3/v3.4/RESULTS.md` §2–3 found fal's failure rate on clean
controls (~5 %) comparable to the A100's, and concluded "fal is a different draw of the same
model". The differences below are real and systematic, but whether they move the failure rate
is an open empirical question; §5 gives the cheapest test.

---

## 1. Ranked differences

### 1. Sigma schedule: our outputs cross the `> 4300`-token cliff in `compute_empirical_mu`  (HIGH confidence, fully verified)

**What we do.** `klein_local.py:43-46`:
```python
def _size(bgr, maxpix=1_150_000):
    h, w = bgr.shape[:2]
    k = min(1.0, (maxpix / (h * w)) ** 0.5)
    return max(16, int(h * k) // 16 * 16), max(16, int(w * k) // 16 * 16)
```
and `klein_local.py:54-58` passes that as `height=h, width=w`. Persons arrive already
normalised to 1.15 MP by `v3lib.normalise` (`v3lib.py:185, 274-279`, `MAXPIX = 1_150_000`), so
call-2 outputs are 1,117,696–1,149,184 px: 4,366–4,489 tokens (`prepare_latents`,
`D/pipelines/flux2/pipeline_flux2_klein.py#L492-L495`: latent grid is `height//16 × width//16`).

**What diffusers does with it.** `D/pipelines/flux2/pipeline_flux2_klein.py#L54-L67`:
```python
def compute_empirical_mu(image_seq_len: int, num_steps: int) -> float:
    a1, b1 = 8.73809524e-05, 1.89833333
    a2, b2 = 0.00016927, 0.45666666
    if image_seq_len > 4300:
        mu = a2 * image_seq_len + b2
        return float(mu)
    m_200 = a2 * image_seq_len + b2
    m_10 = a1 * image_seq_len + b1
    a = (m_200 - m_10) / 190.0
    b = m_200 - 200.0 * a
    mu = a * num_steps + b
    return float(mu)
```
`#L812-L823`: `sigmas = np.linspace(1.0, 1 / num_inference_steps, num_inference_steps)`,
`image_seq_len = latents.shape[1]`, `mu = compute_empirical_mu(image_seq_len, num_steps)`,
passed to the scheduler. `D/schedulers/scheduling_flow_match_euler_discrete.py#L348-L349`
(`use_dynamic_shifting: true` in `scheduler_config.json`): `sigmas = self.time_shift(mu, 1.0, sigmas)`;
`#L646-L647`: `return math.exp(mu) / (math.exp(mu) + (1 / t - 1) ** sigma)`; `#L377` appends 0.

**What BFL does.** Byte-for-byte the same function, `B/src/flux2/sampling.py#L251-L266`, and
the same shift `#L240-L248`:
```python
def generalized_time_snr_shift(t, mu, sigma):
    return math.exp(mu) / (math.exp(mu) + (1 / t - 1) ** sigma)
def get_schedule(num_steps, image_seq_len):
    mu = compute_empirical_mu(image_seq_len, num_steps)
    timesteps = torch.linspace(1, 0, num_steps + 1)
    timesteps = generalized_time_snr_shift(timesteps, mu, 1.0)
```
`scripts/cli.py#L586`: `timesteps = get_schedule(cfg.num_steps, x.shape[1])` where `x` is the
*output* token sequence (`#L581`: `shape = (1, 128, height // 16, width // 16)`). So the schedule
depends only on the output token count, on both paths.

**What fal does.** fal's output area is always ≤ 1,048,576 px (§1.3), so ≤ 4,096 tokens, so
always on the `≤ 4300` branch. Note the `> 4300` branch is the `m_200` line (the 200-step fit)
applied regardless of `num_steps`; BFL's own defaults (`cli.py#L34-L35`: 1360×768 = 4,080
tokens) and the HF README example (1024×1024 = 4,096) never touch it either.

**Numbers** (4 steps; computed from the quoted formulas):

| output | tokens | mu | sigmas |
|---|---|---|---|
| fal 1216×832 | 3952 | 2.279 | 1, .967, .907, .765, 0 |
| fal 832×1248 | 4056 | 2.288 | 1, .967, .908, .767, 0 |
| fal 1024×1024 | 4096 | 2.291 | 1, .967, .908, .767, 0 |
| **A100 1280×880** | 4400 | **1.201** | 1, .909, .769, .526, 0 |
| **A100 864×1312** | 4428 | **1.206** | 1, .909, .770, .527, 0 |
| **A100 944×1184** | 4366 | **1.196** | 1, .908, .768, .524, 0 |
| **A100 1072×1072** | 4489 | **1.217** | 1, .910, .771, .529, 0 |
| 4300 tokens | 4300 | 2.308 | 1, .968, .910, .770, 0 |
| 4301 tokens | 4301 | 1.185 | 1, .907, .766, .522, 0 |

The A100 sizes are the actual files in `judge_fal_vs_a100/gen/*__A100__*.jpg`; the fal sizes are
the actual `*__FAL__*.jpg` files for the same pairs.

**Mechanism.** klein-4B is step-distilled at 4 steps (`B/src/flux2/util.py#L24-L26`:
`"defaults": {"guidance": 1.0, "num_steps": 4}, "fixed_params": {"guidance", "num_steps"},  # guidance and timestep distilled`).
A step-distilled model is trained to map specific noise levels to specific next levels; on our
schedule the model is queried at σ = 0.77 and 0.53 instead of 0.91 and 0.77, and asked to make
the final jump from 0.53 → 0 instead of 0.77 → 0. Which schedule it was distilled on is
**unverifiable**, but the reference implementation, BFL's defaults and fal all sit on the
`mu ≈ 2.3` side and we sit alone on the other. Call 1 (head swap on the ~0.5 MP A4 crop,
≈ 2,000–2,400 tokens) is on the fal side; only call 2, where the failures are, crosses the cliff.
The one low-res person in the judge set (`dualuse_lp_navy_quarterzip_knit_LOWRES.jpg`, 690×966,
2,580 tokens) is a natural control.

### 2. Output grid ≠ person-reference grid (7 % scale mismatch in RoPE space)  (HIGH confidence that the grids differ; mechanism plausible, untested)

**What diffusers does to each `image=[...]` entry.** `D/pipelines/flux2/pipeline_flux2_klein.py#L765-L782`:
```python
for img in image:
    image_width, image_height = img.size
    if image_width * image_height > 1024 * 1024:
        img = self.image_processor._resize_to_target_area(img, 1024 * 1024)
        image_width, image_height = img.size
    multiple_of = self.vae_scale_factor * 2
    image_width = (image_width // multiple_of) * multiple_of
    image_height = (image_height // multiple_of) * multiple_of
    img = self.image_processor.preprocess(img, height=image_height, width=image_width, resize_mode="crop")
    condition_images.append(img)
    height = height or image_height
    width = width or image_width
```
`_resize_to_target_area` (`D/pipelines/flux2/image_processor.py#L108-L115`):
`scale = sqrt(target_area / (w*h)); width = int(w*scale); height = int(h*scale); resize(LANCZOS)`.
Each reference is handled independently; `height/width` do **not** touch the references; the
first image's post-cap size becomes the output size **only if we did not pass one**. We pass one.

**What BFL does.** `B/src/flux2/sampling.py#L52-L65`:
```python
def encode_image_refs(ae, img_ctx):
    scale = 10
    if len(img_ctx) > 1:
        limit_pixels = 1024**2
    elif len(img_ctx) == 1:
        limit_pixels = 2024**2
    ...
    img_ctx_prep = default_prep(img=img_ctx, limit_pixels=limit_pixels)
```
`default_prep` (`#L226-L237`): `to_rgb → cap_min_pixels (ar ≤ 8, side ≥ 64) → cap_pixels → center_crop_to_multiple_of_x(16) → [-1,1]`;
`cap_pixels` (`#L178-L192`) is the same `int(w*sqrt(k/px))` + LANCZOS. Same 1 MP cap per
reference for 2 refs. (For a **single** ref BFL allows 2024² ≈ 4.1 MP; diffusers always caps at 1 MP — only matters for call 1, and our crops are ≤ 1.15 MP.)

**Concrete grids** (judge set; `_resize_to_target_area` + floor-16 applied to the actual input files):

| person input | ref-1 grid (both paths) | our output grid | fal output |
|---|---|---|---|
| 1290×891 | 1232×848 = 77×53 | 1280×880 = 80×55 | 1216×832 = 76×52 |
| 875×1313 | 832×1248 = 52×78 | 864×1312 = 54×82 | 832×1248 = 52×78 |
| 959×1198 | 912×1136 = 57×71 | 944×1184 = 59×74 | 896×1120 = 56×70 |
| 1072×1072 | 1024×1024 = 64×64 | 1072×1072 = 67×67 | 1024×1024 = 64×64 |

**Position ids.** Output tokens: `t=0, h∈[0,H), w∈[0,W)` (`D/...pipeline_flux2_klein.py#L286-L315`,
"`T=0, H=[0..H-1], W=[0..W-1], L=0`"). Reference i: `t = 10 + 10*i`, `h,w` from 0
(`#L319-L366`: `t_coords = [scale + scale * t for t in torch.arange(0, len(image_latents))]`).
BFL identical (`B/src/flux2/sampling.py#L76`: `t_off = [scale + scale * t ...]`; `#L141-L151`
`prc_img`). RoPE is `Flux2PosEmbed(theta=2000, axes_dim=[32,32,32,32])`
(`transformer/config.json`; `D/models/transformers/transformer_flux2.py#L971-L997`), i.e. an
absolute integer grid, no normalisation by image size.

**Mechanism.** In an aligned edit (fal: 52×78 vs 52×78) the reference token for wearer pixel
(h,w) is exactly `(10, h, w)`, a constant RoPE offset from the output token `(0, h, w)`. In ours
the wearer's pixel at output token `(0, 82, 54)` lives at reference token `(10, 78, 52)`: 4 rows
and 2 columns away, i.e. the attention that should say "this is the wearer's leg / the old hem"
is displaced by 32–64 px, growing toward the bottom/right of the frame. That is the region of
legs, hem and feet where "original clothing surviving" and "extra limbs" are scored. fal's
mismatch is ≤ 1 token (only if its reference rounding differs from its output rounding, see §4).
Whether this displacement is what causes the failures is **not verified** by an experiment.

### 3. fal re-sizes the output to ~1 MP (floor-32) for every input; we keep native size ≤ 1.15 MP  (verified from 20 probe responses)

fal OpenAPI schema (fetched): `image_size` — "The size of the generated image. If not
provided, uses the input image size." That sentence is **wrong** in practice. Probe responses
(`v3/runs/v34/probe_fal/out/*.json`, `out_wh` = decoded pixels):

| call | image 1 | image 2 | output |
|---|---|---|---|
| c01_base | 682×1024 (0.70 MP) | 557×1666 | **832×1248** |
| c02_p05 | 577×866 (0.50 MP) | 557×1666 | 832×1248 |
| c03_p25 | 1290×1937 (2.50 MP) | 557×1666 | 832×1248 |
| c04_p11 | 856×1285 (1.10 MP) | 557×1666 | 832×1248 |
| c10_swap | 557×1666 | 682×1024 | 576×1760 |
| c17_a0635 | 650×1024 | 557×1666 | 800×1280 |
| c18_a0758 | 682×900 | 557×1666 | 864×1152 |
| c19_wide | 1024×682 | 557×1666 | 1248×832 |
| c20_imgsize | 682×1024, `image_size={672,1024}` | 557×1666 | 672×1024 |
| c05/c06/c15 (ref 0.25/3.0/2.0 MP) | 682×1024 | — | 832×1248 |

Rule that reproduces all 20: `k = sqrt(1048576 / (w1*h1)); out = (floor32(w1*k), floor32(h1*k))`
(floor-16 fails c10 and c18; floor-32 fits every case). Output follows image 1's aspect; image 2
never affects the size; explicit `image_size` is honoured. All fal `inference` timings are
0.91–1.04 s for 2 refs at 4 steps (1.67 s at 8 steps), consistent with a single ~1 MP forward.

Consequences: (a) for the judge set (all persons ≥ 1.1 MP) fal's output = 1 MP; ours = 1.15 MP
(this is what feeds items 1 and 2); (b) for small persons fal **upsamples** the output to 1 MP
while we stay small; (c) fal floors to 32, we to 16 (cosmetic, ≤ 1 token).

### 4. Reference crop/resample: resize-to-cover then center-crop (diffusers) vs pure center crop (BFL)  (verified; negligible)

diffusers: `preprocess(..., resize_mode="crop")` → `VaeImageProcessor._resize_and_crop`
(`D/image_processor.py#L429-L460`): resizes with LANCZOS by the ≤ 15/1000 factor needed to cover
the floor-16 target, then pastes centered. BFL: `center_crop_to_multiple_of_x`
(`B/src/flux2/sampling.py#L159-L175`) crops without resampling. Difference ≤ 15 px of content and
one extra LANCZOS pass. Not a candidate for the failure mode.

### 5. Noise RNG: CPU generator (ours) vs CUDA generator (BFL) vs unknown (fal)  (verified; non-systematic)

`klein_local.py:58`: `torch.Generator("cpu").manual_seed(seed)` →
`randn_tensor(..., device=cpu)` then moved (`D/utils/torch_utils.py`, `rand_device = "cpu"`).
BFL `cli.py#L582-L583`: `torch.Generator(device="cuda")`, `torch.randn(..., dtype=bfloat16, device="cuda")`.
Same seed ≠ same noise across the three paths. This is exactly the "different draw" in
`prd/v3/v3.4/RESULTS.md`; it does not bias either path.

### 6. Text encoder precision: bf16 (ours) vs FP8 (BFL reference)  (verified for BFL; fal unverifiable; non-systematic)

`B/src/flux2/text_encoder.py#L436`: `Qwen3Embedder(model_spec=f"Qwen/Qwen3-{variant}-FP8")`,
loaded with `torch_dtype=None` (`#L374-L378`); the HF `Qwen/Qwen3-4B-FP8` safetensors header
is `{BF16: 398, F8_E4M3: 252}`. Ours: the bf16 copy in `FLUX.2-klein-4B/text_encoder`
(`config.json` `"dtype": "bfloat16"`, header all BF16). Everything else about the text path is
identical: chat template with `add_generation_prompt=True, enable_thinking=False`, `padding="max_length"`,
`truncation=True`, `max_length=512`, hidden states `[9, 18, 27]` concatenated
(diffusers `#L204, #L214-L262`; BFL `#L28, #L383-L419`); text ids `t=h=w=0, l=arange(L)`
(diffusers `#L266-L282`; BFL `sampling.py#L93-L103`); no attention mask on the 512 padded
tokens in either transformer. The E3 prompt is ~80 tokens, far below 512: **no truncation**.

### 7. Scheduler arithmetic precision  (verified; negligible)

diffusers `step` upcasts to float32 (`scheduling_flow_match_euler_discrete.py#L484`),
`prev_sample = sample + dt * model_output` (`#L511`), casts back (`#L517`). BFL does the Euler
update in bf16 (`sampling.py#L305`). Same update rule.

---

## 2. Hypotheses checked and killed (same on both paths)

| Hypothesis | Verdict | Evidence |
|---|---|---|
| `guidance_scale=0.0` vs fal/BFL guidance 1.0 changes conditioning | **No effect.** | `transformer/config.json`: `"guidance_embeds": false`. Pipeline always passes `guidance=None` (`pipeline_flux2_klein.py#L852`); `do_classifier_free_guidance = guidance_scale > 1 and not is_distilled` (`#L594`), `model_index.json` `"is_distilled": true`; `check_inputs` only warns for `> 1.0` (`#L585`). BFL `Klein4BParams.use_guidance_embed = False` (`model.py#L49`), and `model.py#L128-L130` only adds the guidance embedding when that flag is set; the `guidance=1.0` it passes is ignored. |
| Different step count | **No.** | fal OpenAPI: `num_inference_steps` default 4, min 4, max 8. BFL fixed 4. Ours 4. |
| Different sigma spacing before shift | **No.** | diffusers `linspace(1, 1/4, 4)` + appended 0 = BFL `linspace(1, 0, 5)`; shift formula identical (item 1). |
| PNG data-URI (fal) vs PIL RGB (local) | **No.** | Both lossless 8-bit RGB; `v3lib.py:326-330` encodes PNG; pipeline converts to RGB tensor in [-1,1] like `default_images_prep`. Probe c12 (JPEG q95) and c13 (uploaded URL) returned the same size; pixel-level sha differences are expected. |
| Prompt truncated by `max_sequence_length` | **No.** | 512 on both; prompt ≈ 80 tokens. |
| RoPE / position-id scheme differs (t offsets, h/w origin, theta, axes) | **No.** | Item 2 quotes: `t = 10 + 10*i`, `h,w` from 0, `theta 2000`, `axes [32,32,32,32]`, identical in both. |
| Reference latents concatenated differently | **No.** | diffusers `torch.cat([latents, image_latents], dim=1)` (`#L845-L846`), ids likewise; BFL `torch.cat((img_input, img_cond_seq), dim=1)` (`sampling.py#L292-L293`). Transformer builds `[txt, img]` and RoPE `[txt, img]` in both (`transformer_flux2.py#L1329-L1332`; `model.py#L153-L154`). |
| VAE encode samples vs uses the mean | **No.** | diffusers `sample_mode="argmax"` → `latent_dist.mode()` (`#L467`, `#L145-L148`); BFL `mean = torch.chunk(moments, 2, dim=1)[0]` (`autoencoder.py#L316`). BatchNorm normalisation identical (`#L470-L474` vs `autoencoder.py#L304-L306, #L318-L324`). |
| Timestep scaling into the transformer | **No.** | Pipeline passes `timestep / 1000`, transformer multiplies by 1000 (`transformer_flux2.py#L1284`); BFL `timestep_embedding(..., time_factor=1000)` (`model.py#L710-L719`). |
| Reference aspect/size validation differs | **No.** | Both: aspect ≤ 8, min side 64 (`image_processor.py#L69`; `sampling.py#L195-L203`). |
| Our input to fal was different from our input to the A100 | **No.** | `judge_fal_vs_a100/inputs` are the same 1.13–1.15 MP files; fal downsized to 1 MP internally (item 3). |

---

## 3. Things that are the same "up to numerics" (not candidates for a systematic bias)

Weights (HF headers: transformer, VAE, text encoder all BF16; the single-file
`flux-2-klein-4b.safetensors` BF16), attention (SDPA in both), bf16 activations, Euler update.
FP8 text encoder (BFL) and any fal-side kernel choices could change individual draws but not
the schedule or the token geometry.

---

## 4. What could NOT be verified

- **What fal actually runs.** fal's implementation is closed. Nothing on the model page or in
  the OpenAPI schema states diffusers vs BFL vs custom, GPU, dtype, quantisation, attention
  kernel, or acceleration. The model page contains only pricing text ("$0.014 for the first
  megapixel and $0.001 for each additional megapixel of output"). The floor-32 output rounding
  differs from both diffusers (16) and BFL (16), which suggests a custom sizing layer.
- **fal's reference sizing.** Only the output size is observable. For inputs > 1 MP the
  reference cap is 1 MP on both public implementations, so fal's output and reference grids are
  aligned to ≤ 1 token on the judge set regardless. For inputs < 1 MP it is unknown whether fal
  upsamples the reference along with the output.
- **Which 4-step schedule klein-4B was distilled on.** BFL's code, defaults and fal all land on
  the `mu ≈ 2.3` side; that is circumstantial, not a training-log fact.
- **fal's seed → noise mapping** (CPU vs CUDA generator, dtype of the noise).
- **BFL AE dtype.** `FLUX.2-dev/ae.safetensors` is gated (HTTP 401). `encode_image_refs`
  feeds a float32 tensor with no cast (`sampling.py#L72`), which would raise on bf16 conv
  weights, so fp32 is likely; ours is bf16 (`vae/diffusion_pytorch_model.safetensors` BF16;
  `torch_dtype=bfloat16`).
- **Whether items 1–2 change the failure rate.** Not tested; §5.

---

## 5. What to change in `klein_local.py` to match fal, in order of confidence

1. **Stop passing `height`/`width`** (fixes items 1 and 2 in one line, highest confidence).
   `pipeline_flux2_klein.py#L781-L782` then sizes the output to image 1's post-cap size, so the
   output grid equals the person-reference grid exactly and the token count is ≤ 4,096, putting
   the schedule on the fal/BFL side (`mu ≈ 2.29`). Equivalent explicit form if the caller must
   know the size: `_size(bgr, maxpix=1024*1024)` computed with the pipeline's own rounding
   (`int(side*sqrt(maxpix/px))` then `// 16 * 16`), not `1_150_000`. Callers that need
   image-1-sized output (`run_ironman.py:183` already resizes the bald pass back to raw) should
   resize after the call, as fal effectively does.
2. **Pre-scale image 1 to 1,048,576 px (LANCZOS, floor to 32) before the call**, up or down,
   so small persons behave as on fal (item 3). Keep image 2 untouched; the pipeline caps it at
   1 MP exactly as BFL does.
3. **Set `v3lib.MAXPIX` to `1_048_576`** so the fal path and the local path see the same
   inputs; on fal this is a no-op (it re-sizes anyway), locally it removes the 1.15 MP regime.
4. `guidance_scale=1.0` instead of `0.0` for hygiene only (HF README example uses 1.0); verified
   no-op.
5. Do not spend time on PNG/JPEG, prompt length, RNG device, or `max_sequence_length`.

**Cheapest test of items 1–2:** rerun the v3.4 failure set with change 1 only, same seeds, same
inputs (`v3/runs/v34/v34_a100_nocut_20260901_0323`), and split existing A100 failures by
person-input token count (> 4300 vs ≤ 4300; the `LOWRES` pair is the built-in control). If the
schedule/grid story holds, failures should concentrate on the > 4300 persons and drop after
change 1. If they do not, the repo's "different draw of the same model" conclusion stands and
the two backends differ only in noise.
