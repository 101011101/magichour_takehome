# v3.4 — SOLUTION

**Locked 2026-09-06.** The v3.4 version is **`VEi`**, chosen by the reviewer after the
canvas chain (links A–H) and the blind six-criterion judge
([RESULTS §9.1](RESULTS.md#91-the-blind-judge-on-vei-vs-ve-and-vs-2026-09-06)).
Two klein calls, one model, plus one 1.2M-parameter SR pass. **No ankle cut.** Every
klein canvas is at most **1 MP (2²⁰ px = 4,096 tokens)** — the 1.15 MP cap v3.3
inherited from V2 is retired everywhere (it admits ~4,492 tokens, over the distilled
schedule's 4,300-token branch; measured as a no-op on this fold, where no A4 crop
exceeds 1 MP, and capped in code so a future oversized crop cannot silently cross).
Validation of record: **iron man 2** (§7) — VEi against a correctly built `BC` on the
200-pair matrix — set up and pending at the time of this lock.

## 1. The architecture

```
garment photo ──normalise──▶ A4 crop (BiRefNet bbox) ──▶ framing read (MediaPipe)
      │
      ▼
CALL 1 — the reference        klein, Q3 prompts (§3), seed = run's first seed
      canvas = the crop's own size, capped 1 MP, never upscaled
      ▼
   recrop (white-margin trim)          ── NO ankle cut ──
      ▼
   SR upscale of the FINISHED reference to ~1 MP        realesr-general-x4v3, ~0.19 s
      (below 1 MP: SR ×4 then area-down; at/above: area-down only — SR never downscales)
      ▼
CALL 2 — the edit             klein, E3 sentence (§3b), per seed
      inputs: person photo (native) + the ~1 MP reference
      canvas = the person's size scaled to area 2²⁰, aspect kept, up or down, floor 32
      ▼
   output (~1 MP)
```

Klein never renders above its conditioning: call 1's canvas is its evidence's own
size, and the one upscale in the pipeline is algorithmic, applied to a *finished*
image, where it cannot change garment structure. Per pair on an A100: framing 0.19 s +
ref 1.05 s + SR 0.19 s + edit 3.18 s ≈ **4.6 s**; a cached garment reference makes
repeat try-ons ≈ 3.4 s. Costs measured in `meta/cost.json` of every run.

## 2. Every stage, and the evidence for it

| stage | rule | evidence |
|---|---|---|
| normalise | raw photo bounded to ≤1.15 MP (INTER_AREA) — a pre-bound only; **no klein canvas ever exceeds 1 MP** | [deep dive §4](RESULTS.md#4-deep-dive--what-is-different-between-our-klein-and-fals-2026-09-01): the schedule branch at 4,300 tokens |
| A4 crop | BiRefNet subject matte → bbox — unchanged from v3.3 | v3.3 SOLUTION §2 |
| call-1 canvas | the crop's own size, capped **1 MP**, never upscaled | link F (Lanczos-inflated inputs lose the g027 framing 3/3); link G (SR inputs don't save it either); the invention pressure of rendering above evidence: [§7.1](RESULTS.md#71-the-reference-hallucination-verified-2026-09-04) (the p004 placket grows at ×2.67 generation-upscale) |
| **no ankle cut** | the reference keeps its feet; footwear follows the reference | link A: the cut is neutral on every failure class — footwear is a product decision, and v3.4 chooses "reference's shoes come along" ([§1](RESULTS.md#1-link-a--the-ankle-cut-removed-on-the-failure-set-2026-08-31), decided 2026-09-04) |
| **SR after call 1** | realesr-general-x4v3 (1.2M params, in the bundle) takes the finished reference to ~1 MP; measured 0.19–0.31 s, ~4% of klein time | link H: the reference's **~1 MP token footprint in call 2**, not klein-drawn content, is what fixes the dwarfism — `g027+p003` holds framing 3/3 ([§9](RESULTS.md#9-link-h-on-the-a100--vei-first-reads-2026-09-06)); judge: VEi > VS outside seed noise, within noise of VE ([§9.1](RESULTS.md#91-the-blind-judge-on-vei-vs-ve-and-vs-2026-09-06)) |
| call-2 canvas | fal's rule: area 2²⁰, aspect kept, **up or down**, floor 32 — ≤4,096 tokens, on the trained schedule | link D: ≥fal on 85/93 failure-set cells ([§5](RESULTS.md#5-the-v34-version-and-link-ds-set-up-2026-09-01)); the rule measured off fal 20/20 ([probe](../../../v3/runs/v34/probe_fal/PROBE.md)) |
| prompts | v3.3's `Q3` and `E3`, verbatim (§3, §3b) | not reopened; v3.3 SOLUTION §3 |
| steps / guidance | 4 / 1.0 — the model's fixed operating point; guidance is a no-op on the 4B (no guidance embed) | klein research of record, [EXPERIMENT §E-notes](EXPERIMENT.md) |

## 3. The call-1 prompt (`Q3`, unchanged from v3.3)

`SWAP` ("Replace this person's head, from the neck up, with a smooth, featureless
mannequin head…") + `KEEP` + `PERSON_CLAUSE[framing]` + `HOLD` — verbatim in
`v3/colab/lib/run_ironman.py` and v3.3 SOLUTION §3.

### 3b. The call-2 prompt (`E3`, unchanged from v3.3)

V2's edit prompt + "The person's body, limbs and feet are exactly as in image 1 —
nothing added, nothing removed." Arm `BC` in comparisons uses V2's edit prompt without
the sentence, and — fairness rule — **the same call-2 canvas as the version**
(`bc_canvas="fal"`), since the canvas is a property of call 2, not of the arm (§5).

## 4. The inquiries that built it, and what is carried open

The chain is EXPERIMENT links A–H; one line each:
**A** ankle cut neutral on failures (→ the product decision above) · **B** fal = a
different draw, not a better model · **C** variance confirmed on the A100 · **D** the
call-2 canvas adopted (one regression: g027 dwarfism) · **E** 1 MP references fix the
dwarfism but klein-upscaling invents structure (the placket) · **F** Lanczos inputs
lose (soft evidence anchors worse) · **G** SR inputs don't transfer the fal priors on
the A100 (but give the cleanest p004 reference) · **H** **the footprint is the
mechanism — VEi**, the reviewer's design.

Carried open (not reopened by this lock): F1 person-side garment survival, F2
skirt→trousers, F3 reference drift under re-pose (the backview/extreme-pose class is a
**source-image problem** — no renderer fixes it; detector at ingestion is the v3.1
§3c.31 stance), F4 exposed-skin pairs, F5 headwear. **Select-from-N and every
beyond-2-calls mechanism: v4 scope** (decided 2026-09-05; RESULTS §8 carries the
statistics that will justify or kill it). Mannequin gloss: cosmetic, intermediate-only,
v4 polish candidate at most.

## 4b. Where the version's outputs are

`v3/runs/v34/v34_a100_vei_20260906_0334/` (failure set, 49/50/51; gitignored — zip on
Drive `v3_runs/`); judged in `v3/runs/v34/judge_vei/` (tracked). Iron man 2 outputs
will land as `v34_ironman2_*` (§7).

## 5. Rules that generalise out of v3.4

1. **The schedule is a cliff, not a dial**: keep every canvas ≤4,096 tokens (1 MP);
   1.15 MP was 5% over the cliff.
2. **Render at evidence scale**: a generative model asked to render above its
   conditioning invents structure (placket); asked to render on softened evidence it
   loses anchoring (dwarfism returns). Generate small, upscale the *finished* image
   algorithmically.
3. **Footprint over content**: what conditioning contributes is bounded by its token
   extent in the sequence — a sharp small image is not the same input as the same
   image at 1 MP.
4. **A draw is not a verdict**: fal priors failed to transfer twice (links F→G); only
   paired same-backend seeds decide an arm.
5. **Check the baseline's build before scoring against it** (the BCA4 lesson, §7).

## 6. Known limits carried into the lock

Judged, not hidden: VEi trails VE within seed noise on fidelity and measurably on
hands/cleanliness (SR sharpens artifacts too — judge §9.1); the garment criterion is
statistically identical across every 1 MP arm (2.5–2.7 of 5 on the failure set) — the
canvas arc bought identity/scene/realism, and the garment-side failure classes await
the person-side work (F1–F3) and v4's selector. All VEi numbers to date are
failure-set numbers; the 200-pair picture is §7's job.

## 7. Next: iron man 2

VEi against **`BC` correctly built** — the prior iron man's BC cells were BCA4-class
(head subtraction never ran; verified visually 2026-09-06, RESULTS §10). 200 pairs ×
2 arms × 3 seeds (46/47/48), self-contained notebook (`v3/colab/v34_a100.ipynb`): raw
photos in, everything computed on the A100 except the local V2 head-subtraction step
between sessions. Then the blinded page and the VLM compare (the §9.1 judge), and the
fold-wide verdict this SOLUTION is held against.

*This document is not amended after the lock; corrections go to RESULTS.*
