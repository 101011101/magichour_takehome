# v2.4 — the realism pass, validated end to end and made conditional

**What this closes.** Two things that had been open since v2.1:

1. **"klein 4B → SeedVR2 has never been validated end to end."** It has now, over
   exactly the frames the v2.2.3 harness ships.
2. **v2.4 open question 3 — "should the auxiliary stage be *conditional* on a
   measured realism deficit?"** Yes. The answer and the trigger are below.

Lineage note: the configuration itself (`SeedVR2 ×2, noise_scale = 0`) is **v2.1's**
choice and is not reopened here. What is new is applying it to a harness output and
deciding *when* to apply it.

Evidence: [`v223_realism_pass.html`](../../../v2/artifacts/v223_realism_pass.html) —
38 before/after pairs with a drag wipe and zoom to 12×.

---

## What the pass does

The harness was replayed over stored arm outputs, the frame it lands on was taken for
each of the 38 sets, and only that frame went through SeedVR2.

| measure | value |
|---|---|
| resolution | 832×1248 → **1664×2496** |
| mean absolute pixel change | **2.28 / 255** (under 1%) |
| high-frequency ratio (after / before) | 1.121 |
| identity cosine, mean | **0.933** |
| identity cosine, worst | **0.772** |
| frames below 0.90 identity | **7 of 38** |

**The change is small and the identity cost was not.** For scale: v2.1 measured this
same configuration at **0.943** identity on klein outputs, and rejected Z-Image Turbo
for dropping to **0.72**. The worst frame here is **0.772** — inside the range that
eliminated a model.

Judged by eye on the review page, the resolution increase is a **clear, noticeable
improvement**, which is why the pass stays in the pipeline rather than being dropped.
The task was therefore not *whether* to keep it but *when* to run it.

---

## The finding that gives the trigger

**The frames that lose identity are the frames SeedVR2 failed to sharpen.**

| | frames | mean identity | below 0.90 |
|---|---|---|---|
| `hf_ratio` < 1.0 — the pass **softened** it | 6 | **0.891** | **4** |
| `hf_ratio` ≥ 1.0 — the pass sharpened it | 32 | 0.941 | 3 |

`corr(hf_ratio, identity) = +0.512`. **One signal covers both problems: when the pass
works it is safe, and when it fails to sharpen it is also damaging the face.** That is
what makes a cheap post-hoc check viable — the failure announces itself.

A pre-hoc signal exists too but is weaker: `hf_before` (high-frequency energy of the
input) correlates with gain at only −0.148. It is still useful, because already-sharp
frames gain the least *and* are dead cost.

---

## The policy comparison

| policy | calls | kept | reverted | skipped | mean identity | worst | below .90 | hf gain | cost |
|---|---|---|---|---|---|---|---|---|---|
| **A** always run | 38 | 38 | 0 | 0 | 0.933 | 0.772 | **7** | 1.121 | $1.52 |
| **B** run only if soft | 29 | 29 | 0 | 9 | 0.953 | 0.772 | 4 | 1.104 | $1.16 |
| **C** always run + revert | 38 | 31 | 7 | 0 | 0.962 | 0.904 | **0** | 1.124 | $1.52 |
| **D** run if soft **+** revert | **29** | 25 | 4 | 9 | **0.971** | **0.922** | **0** | 1.110 | **$1.16** |

**Policy D was the recommendation, and is now superseded in part.** The realism pass
ships as an **explicit `high_resolution` option, off by default** — it exists to serve
a request for resolution, not to make an automatic quality decision. With the caller
having asked for resolution, the `hf_before >= 2.5` skip would deny the request, so
that half of policy D does not ship. **The identity floor does ship**, with one change:
the fallback is a deterministic **Lanczos ×2** rather than the original frame, because
handing back the original fails the request that was made. See
[ARCHITECTURE.md §7](../ARCHITECTURE.md).

The measurement below stands, and is what justifies the floor.

**Policy D as measured.** It makes 24% fewer calls than always-on, eliminates every frame
below 0.90 identity, and keeps 1.110 of the 1.121 mean sharpening gain. The benefit is
essentially intact; the damage is gone.

### The rule

```
if hf_before(frame) >= 2.5:            # already sharp — nothing to restore
    skip the realism pass
else:
    out = seedvr2(frame, x2, noise_scale=0)
    if identity_cos(out, frame) < 0.90:  # it damaged the face
        keep the original frame          # free, deterministic, CPU
    else:
        ship out
```

Both checks are **free and deterministic** — one Laplacian-style high-frequency
measure and one AuraFace cosine, both already in the pipeline. The revert costs
nothing but a discarded API call.

**Revert, not retry.** SeedVR2 takes a seed but accepts no text input, and the failure
is a property of the frame rather than the roll — the same reasoning that killed
reseeding in v2.2.3. Falling back to the original is the correct response.

---

## Caveats

1. **The identity number is confounded by scale.** AuraFace compares an 832×1248 frame
   against a 2× upscale of itself, so some of the drop is resampling rather than
   damage. v2.1's 0.943 was measured at matched scale. This does **not** invalidate
   the policy — the *relative* ordering is what the trigger uses, and the frames
   flagged are the frames that visibly changed — but the absolute figure should not be
   compared directly against v2.1's.
2. **The 2.5 and 0.90 thresholds are fitted** on these 38 frames. The mechanism
   (`hf_ratio` < 1 predicts identity damage) is the transferable finding; the
   cut-points are not.
3. **v2.4's actual question is still open.** This closes "should the stage be
   conditional" and "does the v2.1 winner survive end to end". It does not ask whether
   anything *beats* SeedVR2. The highest-priority candidate remains **Z-Image Base +
   PAI Fun tile-ControlNet + UltraReal LoRA** (self-host only) — the only remaining
   route to **de-glossing**, which SeedVR2 does not do and never did.
4. **n = 38, one reviewer, fal numbers.**
