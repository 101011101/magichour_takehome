# The fully open-weights V2 harness on Colab.
# Markers: "# %% [markdown]" markdown, "# %%" code.
#
# Design: this notebook contains NO pipeline logic. It clones the repo and runs the
# real code, swapping only the three functions that call fal for local ones. A
# reimplementation here would be a second copy that drifts from the one every
# measured number came from -- and then a parity difference could not be told apart
# from a transcription bug.

# %% [markdown]
# # V2 — the whole harness, open weights, no fal
#
# Every V2 number so far came from **fal**. fal is a serving substrate for open
# checkpoints, not a model source — but nothing has been verified on weights we
# downloaded and ran ourselves. This closes that.
#
# | stage | model | licence | size |
# |---|---|---|---|
# | subject matte | BiRefNet_lite | MIT | 224 MB |
# | human parser | SCHP ATR | MIT | 267 MB |
# | pose | MediaPipe Pose lite | Apache-2.0 | 6 MB |
# | identity | AuraFace-v1 | Apache-2.0 | 271 MB |
# | **editor** | **FLUX.2 klein 4B distilled** | **Apache-2.0** | **23.7 GB** |
# | gate | Qwen3-VL-8B-Instruct | Apache-2.0 | 17.5 GB |
# | realism | SeedVR2-3B | Apache-2.0 | 14.6 GB |
# | *extractor* | *Qwen-Image-Edit-2511* | *Apache-2.0* | *57.7 GB — off* |
#
# **Every component is MIT or Apache-2.0.**
#
# ## How it works
#
# It clones the repo and runs `v2/pipeline/` unchanged, replacing exactly three
# functions — `arms.generate`, `vlm.ask`, `upscale.seedvr2` — with local
# implementations. Everything else (router, crops, input comparison, escalation,
# the realism fallback) is the shipped code.
#
# **L4 (24 GB) is the sweet spot.** klein fits with CPU offload at ~40% of an A100.
# Weights cache to Drive so a disconnect does not repeat the download.
#
# It will **not** reproduce the stored outputs pixel for pixel — different
# scheduler, precision and kernels. It compares stage by stage so a divergence
# localises.

# %%
# ---- switches ----------------------------------------------------------------
RUN_QWEN_EXTRACT = False   # Qwen-Image-Edit-2511, 57.7 GB -- half the download.
                           # Only needed to build a QX reference for an UNSEEN
                           # garment; the 38 test sets already have theirs, and the
                           # harness falls back to the cached one automatically.
RUN_REALISM      = False   # OFF. SeedVR2 has no diffusers pipeline, so this falls
                           # back to Lanczos x2 -- which doubles the pixels without
                           # adding detail and makes the output look soft next to
                           # fal's native-resolution frame. Undo the Lanczos and the
                           # self-hosted generation measures SHARPER than fal on
                           # every set. It is also off by default in the product.
REBUILD_REFS     = True    # rebuild garment references from RAW images (the
                           # production path) instead of using the stored ones
N_SETS           = 8       # raise once a full pass works
SEED             = 46
USE_DRIVE_CACHE  = False   # False = download ~42 GB to local disk each session
                           # (fast: HF is quick, Drive's FUSE read is not).
                           # True only if you will run several sessions.
BRANCH           = "v2.2.3-harness"

# Deliberately NOT installed:
#   onnxruntime-gpu -- Colab already ships onnxruntime, and installing the GPU build
#     on top leaves two packages providing the same module, which segfaults the
#     kernel. It also buys nothing: every InferenceSession in the repo pins
#     CPUExecutionProvider, and these models are small.
#   pillow          -- upgrading leaves a mixed PIL install that dies as
#     "cannot import name _Ink from PIL._typing" the moment transformers loads.
#   scikit-image    -- Colab's version works and upgrading conflicts with cucim.
!pip -q install -U "transformers>=4.57" accelerate diffusers safetensors bitsandbytes mediapipe insightface huggingface_hub

import os, sys, json, time, gc, csv, subprocess
import torch
if USE_DRIVE_CACHE:
    from google.colab import drive
    drive.mount("/content/drive", force_remount=False)
    os.environ["HF_HOME"] = "/content/drive/MyDrive/hf_cache"
    os.makedirs(os.environ["HF_HOME"], exist_ok=True)
print("weights cache:", os.environ.get("HF_HOME", "/content (session-local)"))

if not os.path.exists("repo"):
    subprocess.run(["git", "clone", "--depth", "1", "-b", BRANCH,
                    "https://github.com/101011101/magichour_takehome", "repo"], check=True)
REPO = os.path.abspath("repo")
sys.path.insert(0, os.path.join(REPO, "v2"))
sys.path.insert(0, os.path.join(REPO, "v2", "build"))

if torch.cuda.is_available():
    P = torch.cuda.get_device_properties(0)
    VRAM, DTYPE = P.total_memory / 1e9, (torch.float16 if P.major < 8 else torch.bfloat16)
    print(f"GPU {P.name}  {VRAM:.0f} GB  cc {P.major}.{P.minor}  dtype {DTYPE}")
else:
    VRAM, DTYPE = 0, torch.float32
    print("NO GPU — Runtime > Change runtime type > GPU")

def free():
    gc.collect(); torch.cuda.empty_cache()

# The deterministic stack runs on CPU, so system RAM is the constraint in cell 3,
# not VRAM. A T4 runtime has ~12.7 GB and BiRefNet at 1024^2 is the heavy one.
import onnxruntime as _ort, psutil
print(f"onnxruntime {_ort.__version__}  providers={_ort.get_available_providers()}")
print(f"system RAM {psutil.virtual_memory().total/1e9:.1f} GB")

# %% [markdown]
# ## 1. Inputs
#
# Upload `openstack_bundle.zip` (18 MB): raw person and garment images, plus the
# stored references, generations and realism results to compare against.
#
# For **unseen** inputs, drop pairs into `inputs/person` and `inputs/garment` and
# add rows to `manifest.csv`.

# %%
import zipfile, pandas as pd
if not os.path.exists("manifest.csv"):
    from google.colab import files
    up = files.upload()
    with zipfile.ZipFile(list(up)[0]) as z:
        z.extractall(".")
M = pd.read_csv("manifest.csv").head(N_SETS)
for d in ("out", "out/refs", "out/klein", "out/realism"):
    os.makedirs(d, exist_ok=True)
STATE = "openstack_state.json"
S = json.load(open(STATE)) if os.path.exists(STATE) else {}
print(f"{len(M)} sets | shipped arms on fal: {M.shipped_arm.value_counts().to_dict()}")

# %% [markdown]
# ## 2. Stage 1 — the deterministic stack, and the router
#
# BiRefNet matte → SCHP parse → MediaPipe pose → head removal. **This is the repo's
# own code**, so the crops are the ones the numbers were measured on.
#
# `hair_over_garment = (area(C3.2) − area(C3.1)) / area(C3.2)` is the router
# feature: above 14% the request starts at BC_klein, below it at PHEAD.

# %%
import numpy as np, cv2
os.environ["PARSER"] = "schp"          # MIT. The SegFormer one is non-commercial.
import phase3_variants as PV
import garment_crop as GC

def build_refs(garment_path, stem):
    """C3.1 (PHEAD reference) and the hair-over-garment router feature, from raw."""
    bgr = cv2.imread(garment_path)
    Mk = PV.masks(bgr, stem, cranium=True)
    x0, y0, x1, y1 = GC.bbox_of((Mk["subject"] > 0.5).astype(np.uint8), bgr.shape[:2])
    c31 = PV.flatten(bgr[y0:y1, x0:x1], Mk["noface"][y0:y1, x0:x1], PV.WHITE)
    a31 = float((Mk["noface"] > 0.5).sum())
    a32 = float((Mk["nofacehair"] > 0.5).sum())
    hair = max(0.0, (a32 - a31) / a32) if a32 else 0.0
    return c31, hair

print(f"  {'garment':34}{'hair (rebuilt)':>15}{'hair (stored)':>15}{'route':>11}")
for _, r in M.iterrows():
    k = f"ref|{r.set_id}"
    if k not in S and REBUILD_REFS:
        img, hair = build_refs(r.garment_img, r.garment)
        dst = f"out/refs/{r.garment}__PHEAD.jpg"
        cv2.imwrite(dst, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        S[k] = {"ref": dst, "hair": hair}
        json.dump(S, open(STATE, "w"))
    h = S.get(k, {}).get("hair", float(r.hair_over_garment))
    arm = "BC_klein" if h >= 0.14 else "PHEAD"
    print(f"  {r.garment[:32]:34}{h:14.1%}{float(r.hair_over_garment):15.1%}{arm:>11}")

# %% [markdown]
# ## 3. Swap the three fal-backed functions for local ones
#
# Everything else in `pipeline/` runs untouched — router, input comparison,
# escalation, the realism identity floor and Lanczos fallback.

# %%
from pipeline import HarnessConfig, harness, arms, vlm, upscale
import tempfile, urllib.request
from PIL import Image

cfg = HarnessConfig(high_resolution=RUN_REALISM, quality="safe", seed=SEED).validate()

# klein 4B is DISTILLED -- the model card calls it "our fastest distilled model for
# sub-second image generation" and its example uses num_inference_steps=4,
# guidance_scale=1.0. diffusers defaults to ~28 steps with CFG, which is the wrong
# operating point for a timestep-distilled model: far slower, and applying guidance
# to a model distilled not to need it degrades rather than improves. Passing these
# explicitly is not a tuning choice, it is the documented way to run this checkpoint.
STEPS, GUIDANCE = 4, 1.0
_MODELS = {}

# ---- editor -------------------------------------------------------------------
# fal's klein endpoint SILENTLY NORMALISES to ~1 MP -- every stored output is
# 832x1248 (1.04 MP) regardless of a person input that ranged 682x1024 to
# 1024x1536. Left to itself, diffusers sizes from the inputs and generated at
# 1344x2048 or 1664x2496, i.e. 2.7-4x the pixels.
#
# That is not free resolution. High-frequency energy came out LOWER on 6 of 8
# frames: more pixels, less detail, a soft upscaled look. klein is tuned around
# 1 MP and degrades above it.
#
# So the self-hosted path has to replicate the normalisation, and this is a
# DEPLOYMENT REQUIREMENT rather than a notebook detail -- a self-hosted service
# that skips it ships softer images than the fal numbers were measured on.
TARGET_MP = 1.04

def target_size(person_path):
    im = Image.open(person_path)
    w, h = im.size
    k = (TARGET_MP * 1e6 / (w * h)) ** 0.5
    # diffusion transformers need dimensions on a 16-pixel grid
    return max(256, int(round(w * k / 16)) * 16), max(256, int(round(h * k / 16)) * 16)


def local_generate(arm, person_path, garment_path, cfg):
    stem = os.path.splitext(os.path.basename(garment_path))[0]
    row = M[M.garment == stem]
    if arm == "PHEAD" and REBUILD_REFS:
        ref = S[f"ref|{row.iloc[0].set_id}"]["ref"]           # rebuilt from raw
    else:
        ref = row.iloc[0].get(f"ref_{arm}")                   # cached (incl. QX)
    if not isinstance(ref, str) or not os.path.exists(ref):
        raise FileNotFoundError(f"no {arm} reference for {stem}")
    W, H = target_size(person_path)
    pipe = _MODELS["klein"]
    img = pipe(prompt=arms.PROMPT,
               image=[Image.open(person_path).convert("RGB"),
                      Image.open(ref).convert("RGB")],
               width=W, height=H,
               num_inference_steps=STEPS, guidance_scale=GUIDANCE,
               generator=torch.Generator("cuda").manual_seed(cfg.seed)).images[0]
    dst = tempfile.mktemp(suffix=f"__{arm}.jpg"); img.save(dst, quality=94)
    return dst

# ---- gate ---------------------------------------------------------------------
import re
def local_ask(spec, cfg, out_path, reference_path=None):
    m, proc = _MODELS["vlm"], _MODELS["vproc"]
    content = []
    if spec["needs_reference"] and reference_path:
        content.append({"type": "image", "image": Image.open(reference_path).convert("RGB")})
    content.append({"type": "image", "image": Image.open(out_path).convert("RGB")})
    content.append({"type": "text", "text": spec["text"]})
    msgs = [{"role": "system", "content": [{"type": "text", "text": vlm.SYSTEM}]},
            {"role": "user", "content": content}]
    inp = proc.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True,
                                   return_dict=True, return_tensors="pt").to(m.device)
    with torch.inference_mode():
        g = m.generate(**inp, max_new_tokens=8, do_sample=False)
    t = proc.decode(g[0][inp["input_ids"].shape[1]:], skip_special_tokens=True).upper()
    for lab in spec["labels"]:
        if re.search(rf"\b{lab}\b", t):
            return lab
    return "UNPARSED"

# ---- realism ------------------------------------------------------------------
def local_seedvr2(path, cfg):
    return _MODELS.get("seedvr2_fn", lambda p: None)(path)

arms.generate = local_generate
vlm.ask = local_ask
upscale.seedvr2 = local_seedvr2
print("patched: arms.generate, vlm.ask, upscale.seedvr2")
print("untouched: router, crops, input comparison, escalation, identity floor")

# %% [markdown]
# ## 4. Load the models
#
# Sequentially, freeing between, so 40 GB of VRAM is not required to hold 56 GB of
# weights.

# %%
from diffusers import DiffusionPipeline
from transformers import AutoProcessor, BitsAndBytesConfig
try:
    from transformers import Qwen3VLForConditionalGeneration as VLMCls
except ImportError:
    from transformers import AutoModelForImageTextToText as VLMCls

# The repo is 23.7 GB but the PIPELINE only needs 16 GB of it:
#
#     transformer/        7.75 GB
#     text_encoder/       8.05 GB   <- the biggest single piece
#     vae/ + tokenizer/   0.19 GB
#     flux-2-klein-4b.safetensors  7.75 GB  <- a DUPLICATE of the transformer in
#                                              single-file format. from_pretrained
#                                              never reads it. Skip the download.
#
# A free T4 runtime has ~12.7 GB of SYSTEM RAM, and CPU offload holds the whole
# model there. 16 GB does not fit, which is why offloading harder did not help --
# the constraint was RAM, not VRAM.
#
# So quantise the TEXT ENCODER to 4-bit (8.05 -> ~2 GB) and leave the diffusion
# transformer in fp16. Text-encoder quantisation costs far less output quality
# than quantising the transformer would, which matters here because a degraded
# transformer would confound the parity comparison this notebook exists to make.
from huggingface_hub import snapshot_download
KLEIN = "black-forest-labs/FLUX.2-klein-4B"
local = snapshot_download(KLEIN, ignore_patterns=["flux-2-klein-4b.safetensors"])
print(f"klein weights at {local}")

t0 = time.time()
te = None
if VRAM < 30:
    from transformers import BitsAndBytesConfig as TFQ, AutoModel
    try:
        te = AutoModel.from_pretrained(
            local, subfolder="text_encoder", dtype=DTYPE,
            quantization_config=TFQ(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                    bnb_4bit_compute_dtype=DTYPE))
        print("text encoder loaded in 4-bit")
    except Exception as ex:
        print(f"4-bit text encoder failed ({type(ex).__name__}), using fp16")
        te = None

kw = {"torch_dtype": DTYPE}
if te is not None:
    kw["text_encoder"] = te
_MODELS["klein"] = DiffusionPipeline.from_pretrained(local, **kw)
_MODELS["klein"].enable_model_cpu_offload()
print(f"klein loaded {(time.time()-t0)/60:.1f} min")
free()
print(f"  VRAM after klein: {torch.cuda.memory_allocated()/1e9:.1f} GB"
      f" | RAM used {psutil.virtual_memory().percent:.0f}%")

q = None if VRAM > 30 else BitsAndBytesConfig(
    load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=DTYPE)
t0 = time.time()
_MODELS["vlm"] = VLMCls.from_pretrained("Qwen/Qwen3-VL-8B-Instruct",
                                        quantization_config=q, device_map="auto",
                                        dtype=DTYPE, attn_implementation="sdpa").eval()
_MODELS["vproc"] = AutoProcessor.from_pretrained("Qwen/Qwen3-VL-8B-Instruct",
                                                 min_pixels=256*28*28,
                                                 max_pixels=1024*28*28)
free()
print(f"Qwen3-VL loaded {(time.time()-t0)/60:.1f} min  (4-bit: {q is not None})")
print(f"  VRAM with both: {torch.cuda.memory_allocated()/1e9:.1f} / {VRAM:.0f} GB"
      f" | RAM {psutil.virtual_memory().percent:.0f}%")
if psutil.virtual_memory().percent > 85:
    print("  WARNING: system RAM is nearly full. If the kernel dies in cell 6, the")
    print("  free tier is out of room -- use Colab Pro's high-RAM runtime with an L4.")

if RUN_REALISM:
    print("\nSeedVR2 has no diffusers pipeline. To enable:")
    print("  !git clone https://github.com/ByteDance-Seed/SeedVR")
    print("  then set _MODELS['seedvr2_fn'] = <callable(path)->path>")
    print("Left unset, upscale.seedvr2 returns None and the harness falls back to")
    print("Lanczos -- which still delivers the resolution the caller asked for.")

# %% [markdown]
# ## 5. Run the harness
#
# `harness.run()` — the shipped code. Router picks the arm, klein generates, the
# input comparison and VLM gate decide, escalation goes to QX, realism is optional.

# %%
rows = []
for _, r in M.iterrows():
    key = f"run|{r.set_id}"
    if key in S:
        rows.append(S[key]); continue
    try:
        t = time.time()
        res = harness.run(r.person_img, r.garment_img, cfg)
        rec = dict(set_id=r.set_id, arm=res.arm, escalated=res.escalated,
                   generations=res.generations, route=res.route_reason,
                   gate=res.gate_reason, upscaled=res.upscaled,
                   identity=res.identity_cos, hair=res.hair_over_garment,
                   secs=round(time.time() - t, 1), out=res.image_path,
                   fal_arm=r.shipped_arm, fal_tier=r.shipped_tier)
        # Save the frame klein produced, separately from whatever the realism stage
        # did to it. Comparing a Lanczos-upscaled frame against fal's native one is
        # not like-for-like, and that mistake cost a whole read of the results.
        dst = f"out/klein/{r.set_id}__{res.arm}.jpg"
        if os.path.exists(res.image_path):
            im = cv2.imread(res.image_path)
            cv2.imwrite(dst, im, [cv2.IMWRITE_JPEG_QUALITY, 94])
            rec["out"] = dst
            rec["out_px"] = f"{im.shape[1]}x{im.shape[0]}"
        S[key] = rec; rows.append(rec); json.dump(S, open(STATE, "w"))
        same = "same" if res.arm == r.shipped_arm else f"DIFFERS (fal: {r.shipped_arm})"
        print(f"  {r.set_id[:30]:32}{res.arm:12}{rec['secs']:6.1f}s  {same}")
        print(f"      {res.route_reason} | {res.gate_reason or 'gate clean'}")
    except Exception as ex:
        print(f"  {r.set_id[:30]:32}ERR {type(ex).__name__}: {str(ex)[:70]}")
        break

# %% [markdown]
# ## 6. Compare and package
#
# **Left = fal, right = self-hosted.** The contact sheet is the deliverable — parity
# is a judgement about equivalence and no scalar settles it.

# %%
D = pd.DataFrame(rows)
if len(D):
    agree = (D.arm == D.fal_arm).mean()
    print(f"same arm chosen as the fal run: {agree:.0%} of {len(D)} sets")
    display(D[["set_id", "arm", "fal_arm", "escalated", "generations", "hair",
               "upscaled", "secs"]])
    D.to_csv("openstack_summary.csv", index=False)

    W, pairs = 300, []
    for _, r in D.iterrows():
        f = M[M.set_id == r.set_id].iloc[0].get(f"fal_{r.arm}")
        if isinstance(f, str) and os.path.exists(f) and os.path.exists(r.out):
            pairs.append((f, r.out, f"{r.set_id} [{r.arm}]"))
    if pairs:
        sheet = Image.new("RGB", (W * 2 + 30, (W + 46) * len(pairs)), "white")
        for i, (a_, b_, _) in enumerate(pairs):
            a, b = Image.open(a_).convert("RGB"), Image.open(b_).convert("RGB")
            sheet.paste(a.resize((W, int(W * a.height / a.width))), (10, i * (W + 46)))
            sheet.paste(b.resize((W, int(W * b.height / b.width))), (W + 20, i * (W + 46)))
        sheet.save("openstack_contact_sheet.jpg", quality=88)
        print(f"contact sheet: {len(pairs)} pairs, left = fal, right = self-hosted")

# %%
import shutil
shutil.make_archive("openstack_out", "zip", "out")
from google.colab import files
for f in ("openstack_out.zip", "openstack_summary.csv",
          "openstack_contact_sheet.jpg", "openstack_state.json"):
    if os.path.exists(f):
        files.download(f)

# %% [markdown]
# ## 7. Demo — two photos in, a try-on out
#
# The production path. Nothing here is looked up: the garment reference is **built
# from the raw image**, exactly as it would be for a customer upload.
#
# Drop any person photo and any garment photo into `demo/` and run. If `demo/` is
# empty it falls back to a test pair so the cell always demonstrates something.

# %%
import glob, shutil
os.makedirs("demo", exist_ok=True)
have = sorted(glob.glob("demo/*"))
if len(have) < 2:
    r0 = M.iloc[0]
    shutil.copy(r0.person_img, "demo/1_person.jpg")
    shutil.copy(r0.garment_img, "demo/2_garment.jpg")
    have = sorted(glob.glob("demo/*"))
    print("demo/ was empty -- using a test pair. Upload your own to replace it.")
PERSON, GARMENT = have[0], have[1]
print(f"person : {PERSON}\ngarment: {GARMENT}")

# Force the unseen path even for a garment that happens to have a cached reference,
# so this demonstrates what a real upload does rather than a lookup.
from pipeline import arms as _arms
_real_reference = _arms.reference
_arms.reference = lambda arm, stem: None

t0 = time.time()
try:
    res = harness.run(PERSON, GARMENT, cfg)
    print(f"\n  route      {res.route_reason}")
    print(f"  arm        {res.arm}" + ("  (escalated)" if res.escalated else ""))
    print(f"  gate       {res.gate_reason or 'clean'}")
    print(f"  realism    {res.upscaled}")
    print(f"  cost       {res.generations} generations, {time.time()-t0:.0f}s")
    print("\n  trace:")
    for line in res.trace:
        print(f"    {line}")
finally:
    _arms.reference = _real_reference

from IPython.display import display
from PIL import Image
w = 300
for lab, p in (("person", PERSON), ("garment", GARMENT), ("RESULT", res.image_path)):
    im = Image.open(p).convert("RGB")
    print(f"\n{lab}  {im.size[0]}x{im.size[1]}")
    display(im.resize((w, int(w * im.size[1] / im.size[0]))))

# %% [markdown]
# ## Reading the result
#
# **Judge the contact sheet by eye first.** Four times in this project an
# instrument said the opposite of the truth, and each time a human looking at one
# image caught it.
#
# | outcome | means |
# |---|---|
# | equivalent quality, same arms chosen | parity closes; every V2 number stands on weights we control |
# | systematically worse | a finding, not a failure — fal may serve non-stock settings, worth knowing before deploy |
# | same quality, different arms | the harness is more VLM-sensitive than the numbers imply; thresholds need re-tuning on self-hosted verdicts |
#
# This runs `N_SETS` sets, not 38. A clean pass is licence to run the full sweep,
# not the sweep itself.
