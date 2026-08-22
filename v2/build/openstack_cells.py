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
RUN_REALISM      = True    # SeedVR2-3B, 14.6 GB. Off by default in the product too.
REBUILD_REFS     = True    # rebuild garment references from RAW images (the
                           # production path) instead of using the stored ones
N_SETS           = 8       # raise once a full pass works
SEED             = 46
BRANCH           = "v2.2.3-harness"

!pip -q install -U "transformers>=4.57" accelerate diffusers safetensors bitsandbytes onnxruntime-gpu mediapipe insightface huggingface_hub scikit-image
# pillow is deliberately NOT upgraded: it leaves Colab with a mixed PIL install that
# dies as "cannot import name _Ink from PIL._typing" as soon as transformers loads.

import os, sys, json, time, gc, csv, subprocess
import torch
from google.colab import drive
drive.mount("/content/drive", force_remount=False)
os.environ["HF_HOME"] = "/content/drive/MyDrive/hf_cache"
os.makedirs(os.environ["HF_HOME"], exist_ok=True)

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
_MODELS = {}

# ---- editor -------------------------------------------------------------------
def local_generate(arm, person_path, garment_path, cfg):
    stem = os.path.splitext(os.path.basename(garment_path))[0]
    row = M[M.garment == stem]
    if arm == "PHEAD" and REBUILD_REFS:
        ref = S[f"ref|{row.iloc[0].set_id}"]["ref"]           # rebuilt from raw
    else:
        ref = row.iloc[0].get(f"ref_{arm}")                   # cached (incl. QX)
    if not isinstance(ref, str) or not os.path.exists(ref):
        raise FileNotFoundError(f"no {arm} reference for {stem}")
    pipe = _MODELS["klein"]
    img = pipe(prompt=arms.PROMPT,
               image=[Image.open(person_path).convert("RGB"),
                      Image.open(ref).convert("RGB")],
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

t0 = time.time()
_MODELS["klein"] = DiffusionPipeline.from_pretrained(
    "black-forest-labs/FLUX.2-klein-4B", torch_dtype=DTYPE)
_MODELS["klein"].enable_model_cpu_offload()
print(f"klein loaded {(time.time()-t0)/60:.1f} min")

q = None if VRAM > 26 else BitsAndBytesConfig(
    load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=DTYPE)
t0 = time.time()
_MODELS["vlm"] = VLMCls.from_pretrained("Qwen/Qwen3-VL-8B-Instruct",
                                        quantization_config=q, device_map="auto",
                                        dtype=DTYPE, attn_implementation="sdpa").eval()
_MODELS["vproc"] = AutoProcessor.from_pretrained("Qwen/Qwen3-VL-8B-Instruct",
                                                 min_pixels=256*28*28,
                                                 max_pixels=1024*28*28)
print(f"Qwen3-VL loaded {(time.time()-t0)/60:.1f} min  (4-bit: {q is not None})")

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
        dst = f"out/klein/{r.set_id}__{res.arm}.jpg"
        if os.path.exists(res.image_path):
            cv2.imwrite(dst, cv2.imread(res.image_path), [cv2.IMWRITE_JPEG_QUALITY, 94])
            rec["out"] = dst
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
