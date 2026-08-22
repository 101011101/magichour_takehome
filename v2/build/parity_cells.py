# Self-hosted parity notebook. Markers: "# %% [markdown]" markdown, "# %%" code.
#
# Every number in V2 is a fal number and the premise is open weights in the deploy
# path. This runs the same checkpoints on a GPU you control and asks whether the
# conclusions survive the change of host.

# %% [markdown]
# # V2 — self-hosted parity
#
# **The gap this closes.** Every measured number in V2 came from fal. fal is a
# serving substrate for open checkpoints, not a model source — but nothing has been
# verified on weights we actually downloaded. That is the largest outstanding risk in
# the programme, and it is the one most likely to matter in review.
#
# **Parity is not bit-equality.** Different schedulers, precisions and kernels will
# not reproduce a diffusion output pixel for pixel, and chasing that would be a
# category error. The question is narrower and answerable:
#
# > Does the checkpoint load, run, and produce output of **equivalent quality**, such
# > that the harness would make the **same decision**?
#
# **How to use this.** Sections are independent — run what fits your GPU. Each one
# reports what it loaded, what it produced, and how that compares to the stored fal
# output. Section 6 packages everything for download.
#
# | model | role | rough need |
# |---|---|---|
# | Qwen3-VL-8B | escalation judge | ~6 GB at 4-bit — **fits a free T4** |
# | SeedVR2 | realism upscaler | 3B/7B variants |
# | FLUX.2 klein 4B distilled | **the editor — 100% of outputs** | largest single risk |
# | Qwen-Image-Edit-2511 | garment extractor | 20B — likely needs A100 |
#
# The VLM is the highest-value quick win: its numbers were measured through
# **OpenRouter**, a third-party proxy, so it is the weakest link evidentially.
# The editor is the highest-value overall.

# %%
# 1. Environment. Report the tier honestly rather than assuming one.
!pip -q install -U "transformers>=4.57" accelerate bitsandbytes diffusers safetensors huggingface_hub

import torch, os, json, time, subprocess
print("torch", torch.__version__, "| cuda", torch.cuda.is_available())
VRAM = 0
if torch.cuda.is_available():
    p = torch.cuda.get_device_properties(0)
    VRAM = p.total_memory / 1e9
    print(f"GPU: {p.name}  {VRAM:.1f} GB  capability {p.major}.{p.minor}")
    # capability < 8.0 (T4 is 7.5) has no native bf16 and no flash-attention-2
    DTYPE = torch.float16 if p.major < 8 else torch.bfloat16
    print(f"compute dtype: {DTYPE}")
else:
    DTYPE = torch.float32
    print("NO GPU — Runtime > Change runtime type > GPU, then rerun.")

print(f"\ntier: {'A100/L4 class — try everything' if VRAM > 30 else 'T4 class — VLM and SeedVR2 are realistic; the editor may need 4-bit' if VRAM > 14 else 'insufficient'}")
!nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv 2>/dev/null || true

# %% [markdown]
# ## 2. Upload the parity bundle
#
# `parity_bundle.zip` (40 MB) from `v2/build/parity_bundle.py`. It carries 8 pairs
# chosen to span the interesting cases — two the harness ships from PHEAD, two from
# BC_klein, two escalations, the frame the identity check saved, and the worst
# hair-damage reference — plus every garment reference and the stored fal output to
# compare against.

# %%
import zipfile, pandas as pd
if not os.path.exists("manifest.csv"):
    from google.colab import files
    up = files.upload()
    with zipfile.ZipFile(list(up)[0]) as z:
        z.extractall(".")
M = pd.read_csv("manifest.csv")
os.makedirs("out", exist_ok=True)
RESULTS = "parity_results.json"
R = json.load(open(RESULTS)) if os.path.exists(RESULTS) else {}
print(f"{len(M)} rows, {M.set_id.nunique()} sets")
print(M.groupby("arm").size().to_dict())

# %% [markdown]
# ## 3. Resolve the checkpoints
#
# Repository IDs are **probed, not assumed** — they get renamed and relicensed, and a
# hardcoded guess that 404s halfway through a run wastes an hour. This reports what
# actually exists before anything is downloaded.

# %%
from huggingface_hub import HfApi
api = HfApi()
CANDIDATES = {
    "vlm":       ["Qwen/Qwen3-VL-8B-Instruct", "Qwen/Qwen2.5-VL-7B-Instruct"],
    "editor":    ["black-forest-labs/FLUX.2-klein-4B", "black-forest-labs/FLUX.2-klein",
                  "black-forest-labs/FLUX.2-dev"],
    "extractor": ["Qwen/Qwen-Image-Edit-2511", "Qwen/Qwen-Image-Edit"],
    "upscaler":  ["ByteDance-Seed/SeedVR2-3B", "ByteDance-Seed/SeedVR2-7B",
                  "ByteDance/SeedVR2-3B"],
}
RESOLVED = {}
for role, cands in CANDIDATES.items():
    for c in cands:
        try:
            info = api.model_info(c)
            sz = sum(getattr(s, "size", 0) or 0 for s in (info.siblings or [])) / 1e9
            RESOLVED[role] = c
            print(f"  {role:10} {c:42} licence={info.cardData.get('license','?') if info.cardData else '?'}"
                  f"  ~{sz:.0f} GB" if sz else f"  {role:10} {c:42} OK")
            break
        except Exception as ex:
            print(f"  {role:10} {c:42} -> {type(ex).__name__}")
    else:
        print(f"  {role:10} NONE RESOLVED — set it manually below")
print("\nresolved:", RESOLVED)

# %% [markdown]
# ## 4a. VLM parity — the escalation judge
#
# **Highest value per minute.** The shipped gate's numbers were measured through
# OpenRouter, so they are "the open checkpoint on somebody else's host with their
# quantisation and sampling defaults." This is the only section that removes a
# third-party from the evidence chain.
#
# Success criterion: the `garment` prompt reproduces roughly **70% accuracy against a
# 62.3% do-nothing baseline** on the 114 labelled cells. If it does, the gate's
# numbers stand on weights we control.

# %%
# Needs the VLM eval bundle (v2/runs/vlm_eval_bundle.zip), not the parity bundle.
# Skip this section if you are only checking the generative models.
RUN_VLM = os.path.exists("outputs") and os.path.exists("manifest.csv")
print("VLM section:", "ready" if RUN_VLM else
      "skipped — upload vlm_eval_bundle.zip too if you want it")

# %% [markdown]
# ## 4b. SeedVR2 parity — the realism pass
#
# Compares a self-hosted upscale against the stored fal upscale of the same frame.
# The comparison that matters is not pixel difference but whether the **identity
# floor decision** comes out the same: the shipped rule discards the pass when
# AuraFace cosine drops below 0.90, and parity means that verdict does not flip.

# %%
import glob
ins = sorted(glob.glob("realism_in/*"))
fals = {os.path.basename(p).split("__")[0]: p for p in glob.glob("realism_fal/*")}
print(f"{len(ins)} frames to upscale, {len(fals)} stored fal results to compare against")
print("SeedVR2 has no diffusers pipeline; install from the ByteDance repo:")
print("  !git clone https://github.com/ByteDance-Seed/SeedVR && pip -q install -r SeedVR/requirements.txt")
print("Then run its inference script over realism_in/ into out/realism_self/.")
print("This section is left as an explicit manual step rather than a guessed API.")

# %% [markdown]
# ## 5. Editor parity — FLUX.2 klein 4B distilled
#
# **The one that matters most: every output goes through it.**
#
# Runs the same person + garment reference pairs, same prompt, same seed 46, and puts
# the self-hosted result beside the stored fal result. Judge by eye — the numbers
# below are context, not the verdict.

# %%
EDITOR = RESOLVED.get("editor")
if not EDITOR:
    print("editor not resolved — set EDITOR manually and rerun")
elif VRAM < 14:
    print(f"skipping: {VRAM:.0f} GB is not enough for the editor")
else:
    from diffusers import DiffusionPipeline
    t0 = time.time()
    pipe = DiffusionPipeline.from_pretrained(EDITOR, torch_dtype=DTYPE)
    pipe.enable_model_cpu_offload()          # fits a smaller card at a speed cost
    print(f"loaded {EDITOR} in {(time.time()-t0)/60:.1f} min")

    PROMPT = ("Dress the person in image 1 in the clothing shown in image 2. Keep the "
              "person's face, identity, body and the background exactly as they are.")
    os.makedirs("out/editor_self", exist_ok=True)
    from PIL import Image
    for _, row in M.iterrows():
        key = f"editor|{row.set_id}|{row.arm}"
        if key in R or not isinstance(row.garment_ref, str) or not row.garment_ref:
            continue
        dst = f"out/editor_self/{row.set_id}__{row.arm}.jpg"
        try:
            t = time.time()
            img = pipe(prompt=PROMPT,
                       image=[Image.open(row.person).convert("RGB"),
                              Image.open(row.garment_ref).convert("RGB")],
                       generator=torch.Generator("cuda").manual_seed(46)).images[0]
            img.save(dst)
            R[key] = {"out": dst, "fal": row.fal_output, "secs": round(time.time()-t, 1),
                      "arm": row.arm, "set_id": row.set_id, "human_tier": row.human_tier}
            json.dump(R, open(RESULTS, "w"))
            print(f"  {row.set_id[:34]:34} {row.arm:12} {R[key]['secs']:5.1f}s")
        except Exception as ex:
            print(f"  {row.set_id[:34]:34} {row.arm:12} ERR {type(ex).__name__}: "
                  f"{str(ex)[:80]}")
            break

# %% [markdown]
# ## 6. Compare, and package for download
#
# Writes a side-by-side contact sheet plus a CSV. **The contact sheet is the
# deliverable** — parity is a judgement about equivalence, and no scalar settles it.

# %%
from PIL import Image
import csv as _csv
pairs = [(k, v) for k, v in R.items() if k.startswith("editor|")
         and os.path.exists(v["out"]) and os.path.exists(v.get("fal", ""))]
print(f"{len(pairs)} self-hosted / fal pairs")
if pairs:
    W = 340
    sheet = Image.new("RGB", (W * 2 + 30, (W + 40) * len(pairs)), "white")
    rows = []
    for i, (k, v) in enumerate(pairs):
        a = Image.open(v["fal"]).convert("RGB"); b = Image.open(v["out"]).convert("RGB")
        h = int(W * a.height / a.width)
        sheet.paste(a.resize((W, h)), (10, i * (W + 40)))
        sheet.paste(b.resize((W, int(W * b.height / b.width))), (W + 20, i * (W + 40)))
        rows.append({"set_id": v["set_id"], "arm": v["arm"], "human_tier": v["human_tier"],
                     "secs_self_hosted": v["secs"], "fal": v["fal"], "self": v["out"]})
    sheet.save("parity_contact_sheet.jpg", quality=88)
    with open("parity_summary.csv", "w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print("left column = fal, right column = self-hosted")
    print("wrote parity_contact_sheet.jpg and parity_summary.csv")

# %%
import shutil
shutil.make_archive("parity_out", "zip", "out")
from google.colab import files
for f in ("parity_out.zip", "parity_results.json", "parity_summary.csv",
          "parity_contact_sheet.jpg"):
    if os.path.exists(f):
        files.download(f)

# %% [markdown]
# ## What a result here means
#
# **If the editor loads and produces equivalent output:** the parity gap closes for
# the component that carries 100% of requests, and the V2 numbers stand on weights we
# control. That is the single largest risk in the programme retired.
#
# **If it does not fit this GPU:** that is itself a finding worth writing down — the
# deploy path needs a specific class of hardware, and knowing which one is a
# requirement, not a failure.
#
# **What this cannot tell you:** whether the *harness decisions* change. That needs
# the full 38 sets, and this notebook deliberately runs 8. Treat a pass here as
# licence to run the full parity sweep, not as the sweep itself.
