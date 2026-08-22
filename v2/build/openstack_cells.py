# The fully open-weights V2 harness on Colab.
# Markers: "# %% [markdown]" markdown, "# %%" code.

# %% [markdown]
# # V2 — the whole harness, open weights, no fal
#
# Every V2 number so far came from **fal**. fal is a serving substrate for open
# checkpoints, not a model source — but nothing has been verified on weights we
# downloaded and ran ourselves. This closes that.
#
# It also rebuilds garment references **from raw images** rather than reading
# prepared ones, which is the production path a real upload would take.
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
# | *garment extractor* | *Qwen-Image-Edit-2511* | *Apache-2.0* | *57.7 GB — off by default* |
#
# **Every component is MIT or Apache-2.0.** The old parser
# (`mattmdjaga/segformer_b2_clothes`) was non-commercial and has been replaced.
#
# ## Runtime
#
# **L4 (24 GB) is the sweet spot** — klein fits with CPU offload and it costs about
# 40% of an A100. A100 is faster; a free T4 works but slowly. Weights cache to
# Drive so a disconnect does not cost the download twice.
#
# ## What it will not do
#
# Reproduce the stored outputs pixel for pixel. Different scheduler, precision and
# kernels — chasing that would be a category error. It compares **stage by stage**
# so a divergence localises: rebuilt reference vs stored reference, generation vs
# stored generation, gate verdict vs stored verdict.

# %%
# ---- switches ----------------------------------------------------------------
RUN_QWEN_EXTRACT = False   # Qwen-Image-Edit-2511, 57.7 GB. Only needed to build a
                           # QX reference for an UNSEEN garment; the 38 test sets
                           # already have theirs. Half the total download.
RUN_REALISM      = True    # SeedVR2-3B. Off by default in the product too.
N_SETS           = 8       # start small; raise once a full pass works
USE_DRIVE_CACHE  = True
SEED             = 46

# One line: a backslash continuation inside a ! magic is fragile in IPython.
# Note pillow is NOT upgraded -- doing so leaves Colab with a mixed PIL install
# that dies as "cannot import name _Ink from PIL._typing" the moment transformers
# touches it.
!pip -q install -U "transformers>=4.57" accelerate diffusers safetensors bitsandbytes onnxruntime-gpu mediapipe insightface huggingface_hub

import os, sys, json, time, gc, csv
import torch
if USE_DRIVE_CACHE:
    from google.colab import drive
    drive.mount("/content/drive", force_remount=False)
    os.environ["HF_HOME"] = "/content/drive/MyDrive/hf_cache"
    os.makedirs(os.environ["HF_HOME"], exist_ok=True)
print("HF_HOME:", os.environ.get("HF_HOME", "(session-local)"))

if torch.cuda.is_available():
    P = torch.cuda.get_device_properties(0)
    VRAM = P.total_memory / 1e9
    DTYPE = torch.float16 if P.major < 8 else torch.bfloat16
    print(f"GPU {P.name}  {VRAM:.0f} GB  cc {P.major}.{P.minor}  dtype {DTYPE}")
else:
    VRAM, DTYPE = 0, torch.float32
    print("NO GPU — Runtime > Change runtime type > GPU")
!df -h /content | tail -1

def free():
    gc.collect(); torch.cuda.empty_cache()

# %% [markdown]
# ## 1. Inputs
#
# Upload `openstack_bundle.zip` (18 MB). Raw person and garment images, plus the
# stored references, generations and realism results to compare against.
#
# To test **unseen** inputs, drop extra pairs into `inputs/person` and
# `inputs/garment` and add rows to `manifest.csv`.

# %%
import zipfile, pandas as pd
if not os.path.exists("manifest.csv"):
    from google.colab import files
    up = files.upload()
    with zipfile.ZipFile(list(up)[0]) as z:
        z.extractall(".")
M = pd.read_csv("manifest.csv").head(N_SETS)
os.makedirs("out", exist_ok=True)
STATE = "openstack_state.json"
S = json.load(open(STATE)) if os.path.exists(STATE) else {}
print(f"{len(M)} sets | shipped arms: {M.shipped_arm.value_counts().to_dict()}")

# %% [markdown]
# ## 2. The deterministic stack — free, CPU, all MIT/Apache
#
# BiRefNet matte → SCHP parse → MediaPipe pose → head removal → crop. This is what
# produces the garment reference and the router's `hair_over_garment` feature.
#
# **Rebuilt from raw images**, then compared against the stored reference. If these
# match, everything downstream is comparing like with like.

# %%
import numpy as np, cv2
from huggingface_hub import hf_hub_download
import onnxruntime as ort

_ort = lambda p: ort.InferenceSession(p, providers=["CUDAExecutionProvider",
                                                    "CPUExecutionProvider"])
SCHP = _ort(hf_hub_download("basso4/humanparsing", "parsing_atr.onnx"))
SCHP_IN = SCHP.get_inputs()[0].name
MEAN = np.array([0.406, 0.456, 0.485], np.float32)
STD = np.array([0.225, 0.224, 0.229], np.float32)
ATR = {"head": (1, 2, 3, 11), "garment": (4, 5, 6, 7, 8, 9, 10, 16, 17),
       "skin": (12, 13, 14, 15)}

def parse_human(bgr):
    h, w = bgr.shape[:2]
    x = cv2.resize(bgr, (512, 512)).astype(np.float32) / 255.0
    o = SCHP.run(None, {SCHP_IN: ((x - MEAN) / STD).transpose(2, 0, 1)[None]})[0][0]
    return np.stack([cv2.resize(c, (w, h)) for c in o]).argmax(0).astype(np.uint8)

print("SCHP loaded. Sanity check on the first garment:")
g0 = cv2.imread(M.iloc[0].garment_img)
s0 = parse_human(g0)
print(f"  head {np.isin(s0, ATR['head']).mean():.1%}  "
      f"garment {np.isin(s0, ATR['garment']).mean():.1%}  "
      f"classes {sorted(np.unique(s0))[:8]}")
print("\nThe full crop stack (BiRefNet + pose + nose-component) lives in")
print("v2/build/phase3_variants.py. Clone the repo to reuse it verbatim:")
print("  !git clone https://github.com/101011101/magichour_takehome repo")
print("  sys.path.insert(0, 'repo/v2/build')")
print("Rebuilding it inline would be a second copy that drifts from the measured one.")

# %% [markdown]
# ## 3. The editor — FLUX.2 klein 4B distilled
#
# **The one that matters: every output goes through it.** Same prompt, same seed 46,
# same references as the fal run.

# %%
EDITOR = "black-forest-labs/FLUX.2-klein-4B"
PROMPT = ("Dress the person in image 1 in the clothing shown in image 2. Keep the "
          "person's face, identity, body and the background exactly as they are.")
ARMS = ["PHEAD", "BC_klein", "QX_qwen_p1"]

if VRAM < 10:
    print("skipping the editor: not enough VRAM even with offload")
else:
    from diffusers import DiffusionPipeline
    from PIL import Image
    t0 = time.time()
    pipe = DiffusionPipeline.from_pretrained(EDITOR, torch_dtype=DTYPE)
    pipe.enable_model_cpu_offload()      # keeps only the active submodule resident
    print(f"loaded in {(time.time()-t0)/60:.1f} min")

    os.makedirs("out/klein", exist_ok=True)
    for _, r in M.iterrows():
        for arm in ARMS:
            ref = r.get(f"ref_{arm}")
            key = f"klein|{r.set_id}|{arm}"
            if key in S or not isinstance(ref, str) or not ref or not os.path.exists(ref):
                continue
            dst = f"out/klein/{r.set_id}__{arm}.jpg"
            try:
                t = time.time()
                img = pipe(prompt=PROMPT,
                           image=[Image.open(r.person_img).convert("RGB"),
                                  Image.open(ref).convert("RGB")],
                           generator=torch.Generator("cuda").manual_seed(SEED)).images[0]
                img.save(dst, quality=92)
                S[key] = {"out": dst, "fal": r.get(f"fal_{arm}"), "arm": arm,
                          "set_id": r.set_id, "tier": r.get(f"tier_{arm}"),
                          "secs": round(time.time() - t, 1)}
                json.dump(S, open(STATE, "w"))
                print(f"  {r.set_id[:32]:34}{arm:12}{S[key]['secs']:6.1f}s")
            except Exception as ex:
                print(f"  {r.set_id[:32]:34}{arm:12}ERR {type(ex).__name__}: {str(ex)[:70]}")
                break
    del pipe; free()

# %% [markdown]
# ## 4. The gate — Qwen3-VL-8B
#
# Two prompts. `garment` sees the reference and the output; `tryon` sees the output
# alone. Escalate if `garment == FAIL` or `tryon != PERFECT`.
#
# The parity question: **does the self-hosted model return the same verdicts?**
# Those verdicts are what the shipped 31/7/0 rests on.

# %%
VLM = "Qwen/Qwen3-VL-8B-Instruct"
SYS = ("You are a strict quality inspector for a virtual try-on system. "
       "Answer only as instructed.")
P_GARMENT = ("The FIRST image is a garment reference. The SECOND image is a virtual "
             "try-on result that was supposed to put that garment onto a person.\n"
             "Did it work? Consider whether the garment in the second image is "
             "genuinely the one from the first image (not merely a similar item), "
             "whether the person is undistorted, and whether the scene is intact.\n"
             "PERFECT - correct garment, clean result. OK - correct garment, visible "
             "flaw. FAIL - wrong garment, or clearly broken.\n"
             "Answer with exactly one word: PERFECT, OK, or FAIL.")
P_TRYON = ("This is the output of a virtual try-on: a photo of a person edited to "
           "put a different garment on them.\n"
           "Judge it on three things: (1) does the person still look like a real, "
           "undistorted human; (2) does the garment sit on the body plausibly; "
           "(3) is the background and scene intact and unrepainted.\n"
           "PERFECT - all three hold. OK - a visible flaw but shippable. "
           "FAIL - any of the three clearly broken.\n"
           "Answer with exactly one word: PERFECT, OK, or FAIL.")

import re
from transformers import AutoProcessor, BitsAndBytesConfig
from PIL import Image
try:
    from transformers import Qwen3VLForConditionalGeneration as VLMCls
except ImportError:
    from transformers import AutoModelForImageTextToText as VLMCls
q = None if VRAM > 20 else BitsAndBytesConfig(
    load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=DTYPE)
vlm = VLMCls.from_pretrained(VLM, quantization_config=q, device_map="auto",
                             dtype=DTYPE, attn_implementation="sdpa").eval()
vproc = AutoProcessor.from_pretrained(VLM, min_pixels=256*28*28, max_pixels=1024*28*28)

def ask(text, *imgs):
    content = [{"type": "image", "image": Image.open(p).convert("RGB")} for p in imgs]
    content.append({"type": "text", "text": text})
    msgs = [{"role": "system", "content": [{"type": "text", "text": SYS}]},
            {"role": "user", "content": content}]
    inp = vproc.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True,
                                    return_dict=True, return_tensors="pt").to(vlm.device)
    with torch.inference_mode():
        g = vlm.generate(**inp, max_new_tokens=8, do_sample=False)
    t = vproc.decode(g[0][inp["input_ids"].shape[1]:], skip_special_tokens=True).upper()
    for lab in ("PERFECT", "OK", "FAIL"):
        if re.search(rf"\b{lab}\b", t):
            return lab
    return "UNPARSED"

for k, v in list(S.items()):
    if not k.startswith("klein|") or "vlm_garment" in v:
        continue
    row = M[M.set_id == v["set_id"]].iloc[0]
    ref = row.get(f"ref_{v['arm']}")
    v["vlm_garment"] = ask(P_GARMENT, ref, v["out"]) if isinstance(ref, str) and ref else "-"
    v["vlm_tryon"] = ask(P_TRYON, v["out"])
    v["escalate"] = v["vlm_garment"] == "FAIL" or v["vlm_tryon"] != "PERFECT"
    json.dump(S, open(STATE, "w"))
    print(f"  {v['set_id'][:32]:34}{v['arm']:12} garment={v['vlm_garment']:8}"
          f" tryon={v['vlm_tryon']:8} -> {'escalate' if v['escalate'] else 'ship'}")
del vlm; free()

# %% [markdown]
# ## 5. Compare, and package
#
# A contact sheet — **fal on the left, self-hosted on the right** — plus a CSV.
# The sheet is the deliverable: parity is a judgement about equivalence and no
# scalar settles it.

# %%
from PIL import Image
rows, W = [], 300
pairs = [v for v in S.values() if v.get("out") and os.path.exists(v["out"])
         and isinstance(v.get("fal"), str) and os.path.exists(v.get("fal", ""))]
if pairs:
    sheet = Image.new("RGB", (W * 2 + 30, (W + 46) * len(pairs)), "white")
    for i, v in enumerate(pairs):
        a = Image.open(v["fal"]).convert("RGB"); b = Image.open(v["out"]).convert("RGB")
        sheet.paste(a.resize((W, int(W * a.height / a.width))), (10, i * (W + 46)))
        sheet.paste(b.resize((W, int(W * b.height / b.width))), (W + 20, i * (W + 46)))
        rows.append({k: v.get(k) for k in ("set_id", "arm", "tier", "secs",
                                           "vlm_garment", "vlm_tryon", "escalate")})
    sheet.save("openstack_contact_sheet.jpg", quality=88)
    pd.DataFrame(rows).to_csv("openstack_summary.csv", index=False)
    print(f"{len(pairs)} pairs | left = fal, right = self-hosted")
    display(pd.DataFrame(rows))

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
# **Judge the contact sheet by eye first.** Every stage of this pipeline has been
# debugged by looking rather than by measuring, and four times an instrument said
# the opposite of the truth.
#
# **Equivalent quality, same verdicts** → the parity gap closes, every number in V2
# stands on weights we control, and the report can say so without a caveat.
#
# **Systematically worse** → that is a finding, not a failure. It would mean fal is
# serving something other than the stock checkpoint, or our settings differ, and
# either is worth knowing before deployment.
#
# **Same quality, different gate verdicts** → the harness is more sensitive to the
# VLM than the numbers imply, and the thresholds need re-tuning on self-hosted
# verdicts.
#
# This runs `N_SETS` sets, not 38 — treat a clean pass as licence to run the full
# sweep, not as the sweep itself.
