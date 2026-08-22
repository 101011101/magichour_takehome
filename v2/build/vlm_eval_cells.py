# Colab notebook for the v2.2.3 VLM gate evaluation.
# Markers: "# %% [markdown]" = markdown cell, "# %%" = code cell.
# Runs on a FREE Colab T4. Professional tone, no emojis, terse comments.

# %% [markdown]
# # v2.2.3 — VLM gate evaluation
#
# Measures whether an open-weights VLM can do the job the deterministic failure
# gate could not: decide whether a virtual try-on output should be shipped or
# escalated to another arm.
#
# The deterministic gate was measured at **AUC 0.506** against the reviewer over
# these same 114 cells — a coin flip. This notebook asks whether a VLM separates
# them, using the identical labelled set so the two are directly comparable.
#
# ## What it does
#
# 114 outputs, each already marked `perfect` / `ok` / `fail` by eye. Four prompt
# variants are run against each. Output is a CSV of one row per (cell, prompt).
#
# ## Runtime
#
# **Free tier is enough.** Runtime > Change runtime type > **T4 GPU**.
# Qwen3-VL-8B is loaded in 4-bit (~6 GB of the T4's 16 GB). No Colab Pro, no
# Drive mount, no API key.
#
# Expect ~10 min for the weight download and ~15-25 min for 456 inferences.

# %%
# 1. Dependencies. bitsandbytes gives 4-bit loading; qwen-vl-utils handles the
#    image preprocessing Qwen's processor expects.
!pip -q install -U "transformers>=4.57" accelerate bitsandbytes qwen-vl-utils pillow

import torch, sys
print("torch", torch.__version__, "| cuda", torch.cuda.is_available())
if torch.cuda.is_available():
    p = torch.cuda.get_device_properties(0)
    print(f"GPU: {p.name}, {p.total_memory/1e9:.1f} GB, capability {p.major}.{p.minor}")
    # T4 is capability 7.5: fp16 is native, bf16 is emulated and slow, and
    # flash-attention-2 is unsupported. Both are handled at load time below.
else:
    print("NO GPU — set Runtime > Change runtime type > T4 GPU, then rerun.")

# %% [markdown]
# ## 2. Upload the evaluation bundle
#
# Upload `vlm_eval_bundle.zip` (25 MB), produced locally by
# `v2/build/vlm_bundle.py`. It contains the 114 outputs, their 22 garment
# references, and `manifest.csv` carrying the human tier for each.

# %%
import os, zipfile, pandas as pd

if not os.path.exists("manifest.csv"):
    from google.colab import files
    up = files.upload()
    with zipfile.ZipFile(list(up)[0]) as z:
        z.extractall(".")

M = pd.read_csv("manifest.csv")
print(f"{len(M)} cells | tiers: {M.tier.value_counts().to_dict()}")
print(f"{M.output.nunique()} outputs, {M.garment_ref.nunique()} garment refs")

# %% [markdown]
# ## 3. Load the model
#
# **Qwen3-VL-8B-Instruct** — the ship candidate. 8B is the largest size that
# self-hosts on a single 24 GB GPU, which is what keeps the per-call cost at
# roughly 2% of a generation and makes the whole VLM step affordable.
#
# 4-bit here is a Colab constraint, not the deployment plan; a company server
# would run fp16. If 4-bit clears the bar, fp16 will too.

# %%
from transformers import AutoProcessor, BitsAndBytesConfig
MODEL = "Qwen/Qwen3-VL-8B-Instruct"

quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                           bnb_4bit_use_double_quant=True,
                           bnb_4bit_compute_dtype=torch.float16)  # fp16: T4 has no bf16

try:
    from transformers import Qwen3VLForConditionalGeneration as VLM
except ImportError:
    from transformers import AutoModelForImageTextToText as VLM

model = VLM.from_pretrained(MODEL, quantization_config=quant, device_map="auto",
                            dtype=torch.float16, attn_implementation="sdpa")
model.eval()

# Cap the visual token budget. Inputs are ~1 MP; without a cap Qwen can spend
# several thousand tokens on one image, which is slow and buys nothing for a
# judgement this coarse.
processor = AutoProcessor.from_pretrained(MODEL, min_pixels=256*28*28,
                                          max_pixels=1024*28*28)
print("loaded", MODEL)

# %% [markdown]
# ## 4. The prompts
#
# Four variants, because prompt design is the open question. The deterministic
# gate failed on *semantic* errors — wrong garment, repainted scene — not on
# artefacts, so an artefact-phrased question may systematically under-fire.
# These separate that hypothesis from the model's capability.
#
# | id | sees | asks |
# |---|---|---|
# | `artefact` | output only | is it broken? (binary) |
# | `usable` | output only | perfect / ok / fail |
# | `tryon` | output only | task-aware, three-tier |
# | `garment` | output **+ garment reference** | did the right garment transfer? |
#
# `garment` is the interesting one: a wrong-garment error is not knowable from
# the output alone, so if only that variant works it tells us VLM-A needs the
# reference image as input.

# %%
SYS = "You are a strict quality inspector for a virtual try-on system. Answer only as instructed."

PROMPTS = {
 "artefact": dict(refs=False, labels=["CLEAN", "BROKEN"], text=(
   "This image was produced by an AI virtual try-on system.\n"
   "Does it contain rendering artefacts, anatomical impossibilities (malformed "
   "hands, extra or missing limbs, distorted faces), melted fabric, or obvious "
   "generation errors?\n"
   "Answer with exactly one word: BROKEN or CLEAN.")),

 "usable": dict(refs=False, labels=["PERFECT", "OK", "FAIL"], text=(
   "This image was produced by an AI virtual try-on system.\n"
   "Rate it:\n"
   "PERFECT - you would ship this to a customer unchanged.\n"
   "OK - acceptable, but you would rather have something better.\n"
   "FAIL - unusable.\n"
   "Answer with exactly one word: PERFECT, OK, or FAIL.")),

 "tryon": dict(refs=False, labels=["PERFECT", "OK", "FAIL"], text=(
   "This is the output of a virtual try-on: a photo of a person that has been "
   "edited to put a different garment on them.\n"
   "Judge it on three things: (1) does the person still look like a real, "
   "undistorted human; (2) does the garment sit on the body plausibly; "
   "(3) is the background and scene intact and unrepainted.\n"
   "PERFECT - all three hold. OK - a visible flaw but shippable. "
   "FAIL - any of the three clearly broken.\n"
   "Answer with exactly one word: PERFECT, OK, or FAIL.")),

 "garment": dict(refs=True, labels=["PERFECT", "OK", "FAIL"], text=(
   "The FIRST image is a garment reference. The SECOND image is a virtual "
   "try-on result that was supposed to put that garment onto a person.\n"
   "Did it work? Consider whether the garment in the second image is genuinely "
   "the one from the first image (not merely a similar item), whether the person "
   "is undistorted, and whether the scene is intact.\n"
   "PERFECT - correct garment, clean result. OK - correct garment, visible flaw. "
   "FAIL - wrong garment, or clearly broken.\n"
   "Answer with exactly one word: PERFECT, OK, or FAIL.")),
}
print(f"{len(PROMPTS)} prompts x {len(M)} cells = {len(PROMPTS)*len(M)} inferences")

# %% [markdown]
# ## 5. Run
#
# Resumable: rerun the cell after a disconnect and it skips rows already done.
# Greedy decoding (`do_sample=False`) so a rerun reproduces.

# %%
import json, re, time
from PIL import Image

RESULTS = "vlm_raw.json"
done = json.load(open(RESULTS)) if os.path.exists(RESULTS) else {}

def ask(spec, out_path, ref_path):
    content = []
    if spec["refs"] and isinstance(ref_path, str) and ref_path:
        content.append({"type": "image", "image": Image.open(ref_path).convert("RGB")})
    content.append({"type": "image", "image": Image.open(out_path).convert("RGB")})
    content.append({"type": "text", "text": spec["text"]})
    msgs = [{"role": "system", "content": [{"type": "text", "text": SYS}]},
            {"role": "user", "content": content}]
    inputs = processor.apply_chat_template(
        msgs, tokenize=True, add_generation_prompt=True,
        return_dict=True, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        gen = model.generate(**inputs, max_new_tokens=8, do_sample=False)
    txt = processor.decode(gen[0][inputs["input_ids"].shape[1]:],
                           skip_special_tokens=True).strip().upper()
    for lab in spec["labels"]:                    # first label that appears wins
        if re.search(rf"\b{lab}\b", txt):
            return lab, txt
    return "UNPARSED", txt

t0 = time.time()
todo = [(pid, i) for pid in PROMPTS for i in range(len(M))
        if f"{pid}|{M.output[i]}" not in done]
print(f"{len(todo)} inferences to run ({len(done)} already done)")

for n, (pid, i) in enumerate(todo, 1):
    row, spec = M.iloc[i], PROMPTS[pid]
    if spec["refs"] and not isinstance(row.garment_ref, str):
        continue
    try:
        lab, raw = ask(spec, row.output, row.garment_ref)
    except Exception as e:
        lab, raw = "ERROR", f"{type(e).__name__}: {e}"[:120]
    done[f"{pid}|{row.output}"] = {"prompt": pid, "verdict": lab, "raw": raw}
    if n % 25 == 0 or n == len(todo):
        json.dump(done, open(RESULTS, "w"))
        el = time.time() - t0
        print(f"  {n}/{len(todo)}  {el/n:.1f}s/call  eta {(len(todo)-n)*el/n/60:.1f} min")
json.dump(done, open(RESULTS, "w"))
print(f"done in {(time.time()-t0)/60:.1f} min")

# %% [markdown]
# ## 6. Write the CSV
#
# One row per (cell, prompt), carrying the human tier and the deterministic
# gate's score alongside, so the two instruments can be scored against the same
# labels without any further joining.

# %%
recs = []
for i in range(len(M)):
    row = M.iloc[i]
    for pid in PROMPTS:
        d = done.get(f"{pid}|{row.output}")
        if not d:
            continue
        recs.append({"set_id": row.set_id, "arm": row.arm, "condition": row.condition,
                     "output": row.output, "prompt": pid,
                     "vlm_verdict": d["verdict"], "vlm_raw": d["raw"],
                     "human_tier": row.tier,
                     "hair_over_garment": row.hair_over_garment,
                     "det_gate_score": row.det_gate_score, "model": MODEL})
out = pd.DataFrame(recs)
out.to_csv("v223_vlm_eval.csv", index=False)
print(f"{len(out)} rows -> v223_vlm_eval.csv")
out.head()

# %% [markdown]
# ## 7. Separation — the number that decides it
#
# The gate's job is to fire when a frame should not ship. Scored as a binary
# task: `perfect` should pass, `ok` and `fail` should escalate.
#
# **The bar to beat is the deterministic gate at AUC 0.506, and the trivial
# baseline of accepting every frame unchecked.**

# %%
BAD = {"FAIL", "BROKEN"}
print(f"{'prompt':10}{'acc':>7}{'prec':>7}{'recall':>8}{'catches fail':>14}{'unparsed':>10}")
for pid in PROMPTS:
    s = out[out.prompt == pid]
    if not len(s):
        continue
    fires = s.vlm_verdict.isin(BAD)                     # gate says do not ship
    should = s.human_tier != "perfect"                  # reviewer agrees
    tp = int((fires & should).sum()); fp = int((fires & ~should).sum())
    fn = int((~fires & should).sum()); tn = int((~fires & ~should).sum())
    hard = s[s.human_tier == "fail"]
    print(f"{pid:10}{(tp+tn)/len(s):7.1%}{tp/max(tp+fp,1):7.0%}{tp/max(tp+fn,1):8.0%}"
          f"{hard.vlm_verdict.isin(BAD).mean():14.0%}"
          f"{(s.vlm_verdict=='UNPARSED').mean():10.0%}")

base = (out[out.prompt == list(PROMPTS)[0]].human_tier == "perfect").mean()
print(f"\naccept-everything baseline: {base:.1%}   deterministic gate: AUC 0.506")
print("\nconfusion, per prompt (rows = human, cols = VLM):")
for pid in PROMPTS:
    s = out[out.prompt == pid]
    if len(s):
        print(f"\n[{pid}]"); print(pd.crosstab(s.human_tier, s.vlm_verdict))

# %%
# 8. Download. Send v223_vlm_eval.csv back to the repo root.
from google.colab import files
files.download("v223_vlm_eval.csv")
