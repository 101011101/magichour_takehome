# The V2 delivery notebook. Markers: "# %% [markdown]" = markdown, "# %%" = code.
#
# Thin by design: the pipeline lives in v2/pipeline/ as an importable package, and
# this notebook imports it. Logic in a notebook cannot be imported, tested, diffed
# or deployed, so none of it lives here.

# %% [markdown]
# # V2 — virtual try-on harness
#
# A person photo and a garment reference in, the person wearing that garment out.
#
# **Hard constraint: open weights only in the deployed path.** fal is a *serving
# substrate* for those same checkpoints during iteration, never a model source.
#
# **Result over 38 evaluation sets:**
#
# | | gen/request | perfect | ok | fail |
# |---|---|---|---|---|
# | Qwen-2511 (the model on the website today) | 1.000 | — | — | — |
# | flat klein + shipped crop | 1.000 | 23 | 5 | 10 |
# | flat BC_klein — best single arm | 2.000 | 28 | 6 | 4 |
# | **the harness** | **2.158** | **31** | 7 | **0** |
#
# Essentially the cost of the best single arm, and **nothing ships broken**.
#
# Design and rationale: `prd/v2/ARCHITECTURE.md`. What was tried and discarded:
# `prd/v2/DECISIONS.md`. What is left: `prd/v2/TODO.md`.

# %%
import os, sys, json, csv, collections, statistics as st
REPO = os.path.abspath(".")
while not os.path.exists(os.path.join(REPO, "prd", "v2")) and REPO != "/":
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, "v2"))
print("repo:", REPO)

from pipeline import HarnessConfig          # noqa: E402
print("pipeline imported")

# %% [markdown]
# ## 1. The pipeline
#
# ```
#   person photo  +  garment reference
#                         |
#   1. PREPROCESS         BiRefNet_lite -> SegFormer/ATR -> MediaPipe Pose
#                         subtractive composition, pose-bounded head,
#                         nose-connected component
#                         |
#   2. ROUTE              free, from the masks above
#         caller named a region?      --> QX
#         hair over garment >= 14%?   --> BC_klein  (2 gen)
#         otherwise                   --> PHEAD     (1 gen)
#                         |
#   3. GENERATE           FLUX.2 klein 4B distilled
#                         |
#   4. SCREEN             free checks against the PERSON INPUT, then the VLM:
#                           degenerate / no-op   --> escalate
#                           identity < 0.90      --> escalate   (wrong person)
#                           garment == FAIL      --> escalate
#                           tryon  != PERFECT    --> escalate   (safe mode only)
#                         escalation always lands on QX (+2 gen)
#                         |
#   5. REALISM            OFF by default. When high_resolution=True:
#                         SeedVR2 x2 noise_scale=0, Lanczos fallback if it
#                         costs identity
#                         |
#                      OUTPUT
# ```
#
# **Three decisions that are easy to undo by accident:**
#
# 1. **Escalation switches mechanism, never seed.** Failure is a property of the
#    *garment* — a damaged reference failed on all three people it was paired with —
#    so a fresh seed reproduces it.
# 2. **The VLM must see the garment reference.** Every output-only prompt scored at
#    the do-nothing baseline; only the reference-aware one beat it.
# 3. **Escalation always lands on QX.** A pairwise "which is better" call measured
#    34% self-consistency under image swap and picked the already-failed arm 2 times
#    in 5. Taking QX unconditionally scores 5/5.
# 4. **The VLM does not replace the free input-comparison checks.** Over 114 cells the
#    VLM caught 26 failures they missed and they caught 1 the VLM missed -- and that
#    one was the only frame that shipped broken. Section 5b measures this.

# %% [markdown]
# ## 2. Configuration
#
# One object drives everything. Only the first three fields are expected to be set
# by a caller; the rest are measured defaults.

# %%
cfg = HarnessConfig()
for f in ("high_resolution", "garment_region", "quality", "hair_threshold",
          "identity_floor", "noop_floor", "vlm_model", "seed"):
    print(f"  {f:18} {getattr(cfg, f)!r}")

print("\nquality modes:")
print("  both modes always run the free input-comparison checks first;")
print("  quality selects only how much VLM evidence is required.\n")
print("  cheap  + garment == FAIL                     1.789 gen  32/5/1")
print("  safe   + garment == FAIL or tryon != PERFECT 2.158 gen  31/7/0")
print("\nA caller wanting a high-resolution result:")
print(" ", HarnessConfig(high_resolution=True, quality="safe"))

# %% [markdown]
# ## 3. What is wired, and what is not
#
# Stated plainly so that nothing untested is mistaken for tested.

# %%
from pipeline import harness, masks, checks, vlm, upscale, arms   # noqa: E402
status = [
    ("config + validation",        "WIRED",   "pipeline/config.py"),
    ("router: hair over garment",  "WIRED",   "pipeline/harness.py:hair_over_garment"),
    ("input comparison",           "WIRED",   "pipeline/harness.py:input_comparison"),
    ("VLM screen (2 prompts)",      "WIRED",   "pipeline/vlm.py"),
    ("realism + Lanczos fallback", "WIRED",   "pipeline/upscale.py"),
    ("arm generation",             "NOT YET", "pipeline/arms.py -- see below"),
]
for what, s, where in status:
    print(f"  {s:8} {what:28} {where}")
print("""
arms.generate() is the one open seam. Every measured number came from
v2/build/amt_run.py, which built the references and drove the endpoints. Rebuilding
a PHEAD reference from phase3_variants.masks(cranium=True) produces a DIFFERENT crop
(1347x475 against the stored 1194x467), so the exact construction is not recoverable
from amt_refs.py alone. It is left raising NotImplementedError rather than stubbed,
because a path that looks wired but produces different references than every measured
number is worse than one that refuses. Resolving it is TODO item 1.""")

# %%
# The router is real and runs locally at zero cost. p021 is the worst hair-damage
# reference on record: 19.5% of the garment is destroyed by hair removal.
for ref in ("p021", "p028", "p009", "dualuse_hugh_jackman_grey_suit_outdoor"):
    h = harness.hair_over_garment(ref)
    arm = "BC_klein" if h >= cfg.hair_threshold else "PHEAD"
    print(f"  {ref:44} hair {h:6.1%}  ->  {arm}")

# %% [markdown]
# ## 4. The measured results
#
# Everything below is recomputed from the human-labelled CSVs at the repo root. No
# generation, no spend, no network. Re-running this notebook reproduces every number
# quoted in the documents.

# %%
T = list(csv.DictReader(open(f"{REPO}/v223_perfect_tier_picks.csv")))
E = list(csv.DictReader(open(f"{REPO}/v223_vlm_eval.csv")))
tier = {(r["set_id"], r["arm"]): r["tier"] for r in T}
hair = {r["set_id"]: float(r["hair_over_garment"]) for r in T}
noop = {(r["set_id"], r["arm"]): float(r["chk_noop"]) for r in T}
ident = {(r["set_id"], r["arm"]): float(r["chk_identity"]) for r in T}
V = {(r["set_id"], r["arm"], r["prompt"]): r["vlm_verdict"] for r in E}
sets = sorted(hair)
first = {k: ("BC_klein" if hair[k] >= 0.14 else "PHEAD") for k in sets}
GEN = {"PHEAD": 1, "BC_klein": 2, "QX_qwen_p1": 2}

def simulate(fire):
    tot, sh, esc = 0, collections.Counter(), 0
    for k in sets:
        a = first[k]; tot += GEN[a]
        if fire(k, a):
            esc += 1; tot += 2; sh[tier[(k, "QX_qwen_p1")]] += 1
        else:
            sh[tier[(k, a)]] += 1
    return tot / len(sets), sh, esc

def row(name, fire):
    g, sh, esc = simulate(fire)
    print(f"  {name:34}{g:8.3f}{sh['perfect']:9d}{sh['ok']:5d}{sh['fail']:6d}{esc:6d}")

print(f"  {'configuration':34}{'gen/req':>8}{'perfect':>9}{'ok':>5}{'fail':>6}{'esc':>6}")
print(f"  {'always PHEAD':34}{1.0:8.3f}"
      f"{sum(tier[(k,'PHEAD')]=='perfect' for k in sets):9d}"
      f"{sum(tier[(k,'PHEAD')]=='ok' for k in sets):5d}"
      f"{sum(tier[(k,'PHEAD')]=='fail' for k in sets):6d}{0:6d}")
print(f"  {'always BC_klein (best single arm)':34}{2.0:8.3f}"
      f"{sum(tier[(k,'BC_klein')]=='perfect' for k in sets):9d}"
      f"{sum(tier[(k,'BC_klein')]=='ok' for k in sets):5d}"
      f"{sum(tier[(k,'BC_klein')]=='fail' for k in sets):6d}{0:6d}")
row("router only, no gate", lambda k, a: False)
row("harness, VLM-only safe gate", lambda k, a: noop[(k, a)] < 0.5
    or V.get((k, a, "garment")) == "FAIL" or V.get((k, a, "tryon")) != "PERFECT")
row("harness, cheap + identity",
    lambda k, a: V.get((k, a, "garment")) == "FAIL" or ident[(k, a)] < 0.90)
row("harness, SAFE + identity (SHIPPED)",
    lambda k, a: noop[(k, a)] < 0.5 or ident[(k, a)] < 0.90
    or V.get((k, a, "garment")) == "FAIL" or V.get((k, a, "tryon")) != "PERFECT")
row("oracle gate (upper bound)", lambda k, a: tier[(k, a)] == "fail")

# %% [markdown]
# ## 5. Why the gate is a VLM and not pixel statistics
#
# The deterministic gate was built first, over five checks, and measured against the
# same reviewer labels. **AUC 0.506 — a coin flip**, and no threshold beat accepting
# every frame unchecked.
#
# The VLM comparison below is the reason the shipped gate asks about the *garment*
# rather than about *artefacts*.

# %%
BAD = {"FAIL", "BROKEN"}
print(f"  {'prompt':10}{'sees':28}{'fires':>7}{'acc':>8}{'catches fail':>14}")
SEES = {"artefact": "output", "usable": "output", "tryon": "output",
        "garment": "reference + output", "transfer": "person + ref + output"}
for pid in ("artefact", "usable", "tryon", "garment", "transfer"):
    s = [r for r in E if r["prompt"] == pid]
    if not s:
        continue
    fires = [r["vlm_verdict"] in BAD for r in s]
    should = [r["human_tier"] != "perfect" for r in s]
    acc = sum(f == h for f, h in zip(fires, should)) / len(s)
    hard = [r for r in s if r["human_tier"] == "fail"]
    ch = sum(1 for r in hard if r["vlm_verdict"] in BAD) / max(len(hard), 1)
    print(f"  {pid:10}{SEES[pid]:28}{sum(fires):7d}{acc:8.1%}{ch:14.0%}")
base = sum(1 for r in E if r["prompt"] == "garment" and r["human_tier"] == "perfect")
print(f"  {'(nothing)':10}{'--':28}{0:7d}{base/114:8.1%}{0:14.0%}   <- the bar")
print("""
The artefact prompt returned CLEAN on all 114 outputs and never fired once,
including on every frame marked fail. These failures are not artefacts: they are
competent photographs of the wrong thing -- a plausible but different garment, or
the input returned unchanged. That is also why pixel statistics could not see them.""")

# %% [markdown]
# ## 5b. Why the free checks stay, even though the VLM is the better instrument
#
# Found by a spot-check of one image, not by any statistic. `HD_p028+navy_peacoat`
# shipped with the person **substituted entirely** — the input is a man with short
# auburn hair, the output a woman with long dark hair.

# %%
SID = "HD_p028+dualuse_navy_peacoat_onmodel"
print("all five VLM prompts on that frame (human tier: fail):")
for r in E:
    if r["set_id"] == SID and r["arm"] == "PHEAD":
        print(f"    {r['prompt']:10} -> {r['vlm_verdict']}")
print(f"    deterministic identity = {ident[(SID,'PHEAD')]}   <- the only signal that fired")
print("\n  `transfer` SEES the person image and was asked directly. It said OK.\n")

cells = list(tier)
vf = lambda k: V.get((k[0], k[1], "garment")) == "FAIL" or V.get((k[0], k[1], "tryon")) != "PERFECT"
df = lambda k: noop[k] < 0.5 or ident[k] < 0.90
bad = [k for k in cells if tier[k] != "perfect"]
print(f"  {'instrument':30}{'fires':>7}{'recall':>8}{'alone':>7}")
for nm, f, other in (("VLM (garment/tryon)", vf, df), ("no-op + identity", df, vf)):
    tp = sum(1 for k in cells if f(k) and tier[k] != "perfect")
    print(f"  {nm:30}{sum(1 for k in cells if f(k)):7d}{tp/len(bad):8.0%}"
          f"{sum(1 for k in bad if f(k) and not other(k)):7d}")
print("""
The VLM is nine times the detector on recall. The one case the free checks caught
alone was the only frame that shipped broken. A no-op and an identity swap both
produce a competent, coherent photograph of the wrong thing -- there is nothing in
the image for a semantic judge to find. Recall is the wrong metric for deciding
whether to drop a check that costs nothing.""")

# %% [markdown]
# ## 6. The realism option
#
# Off by default. It serves one request — *give me a high-resolution image* — and is
# not an automatic quality decision.
#
# Run unconditionally over the 38 shipped frames it cost identity on 7, worst 0.772,
# inside the range that eliminated Z-Image Turbo in v2.1. The identity floor decides
# *how* to upscale, never *whether* to: a failure falls back to a deterministic
# Lanczos ×2, which still delivers the resolution the caller asked for.

# %%
M = json.load(open(f"{REPO}/v2/runs/realism/_metrics.json"))
ic = [r["identity_cos"] for r in M if r["identity_cos"] is not None]
kept = [r for r in M if r["identity_cos"] >= cfg.identity_floor]
print(f"  frames                     {len(M)}")
print(f"  resolution                 {M[0]['dim_before']} -> {M[0]['dim_after']}")
print(f"  mean absolute pixel change {st.mean(r['mae'] for r in M):.2f} / 255")
print(f"  high-frequency gain        x{st.mean(r['hf_ratio'] for r in M):.3f}")
print(f"  identity, mean / worst     {st.mean(ic):.3f} / {min(ic):.3f}")
print(f"  below the {cfg.identity_floor} floor        "
      f"{len(M)-len(kept)} -> fall back to Lanczos, resolution still delivered")
soft = [r for r in M if r["hf_ratio"] < 1.0]
print(f"\n  the tell: frames SeedVR2 failed to sharpen (hf_ratio < 1) have mean")
print(f"  identity {st.mean(r['identity_cos'] for r in soft):.3f} against "
      f"{st.mean(r['identity_cos'] for r in M if r['hf_ratio']>=1):.3f} elsewhere.")
print("  The failure announces itself, so a free post-hoc check is sufficient.")

# %% [markdown]
# ## 7. Where the evidence lives
#
# | page | shows |
# |---|---|
# | `v2/artifacts/v223_perfect_tier.html` | the 114 absolute perfect/ok/fail marks |
# | `v2/artifacts/v223_vlm_eval.html` | five prompts against those marks |
# | `v2/artifacts/v223_realism_pass.html` | 38 before/after wipes, zoom to 12× |
# | `v2/artifacts/v223_gate_simulation.html` | the deterministic gate that failed |
# | `v2/artifacts/v221_attention_mod.html` | the test that chose the three arms |
#
# ## What is still owed
#
# 1. **The end-to-end run** — wire `arms.generate` and run one assembled program.
# 2. **Self-hosted parity** — every number here is a fal number, and the premise is
#    open weights in the deploy path.
# 3. **`mattmdjaga/segformer_b2_clothes` licence** — head detection depends on it and
#    it is not cleared for deploy.
#
# See `prd/v2/TODO.md`.
