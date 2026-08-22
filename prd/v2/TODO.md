# V2 — what is left

Ordered. Everything above the line closes V2; everything below is iteration.
Design: [ARCHITECTURE.md](ARCHITECTURE.md) · History: [DECISIONS.md](DECISIONS.md)

Last updated 2026-08-21.

---

## Blocking V2 completion

### 1. Validate the VLM artefact check — the one unbuilt component

Everything in the harness assumes VLM-A fires correctly. **Cost is settled** (~$0.0003
a call, 0.02 generation-equivalents); **capability is not measured.**

- Measure a self-hosted open VLM against the 114 absolute tiers in
  `v223_perfect_tier_picks.csv`. 456 outputs are already on disk — **GPU time, no fal
  spend.**
- Ask the narrow question: *"does this contain rendering artefacts, anatomical
  impossibilities, or obvious generation errors?"* — **not** *"is this good"*, which
  §2b showed a VLM fails (4/5 on an output that transferred no garment).
- **Success bar:** clearly beats AUC 0.57, the best deterministic check.
- **Fallback if it fails:** ship the crash guard alone. 32/6/0 degrades to 28/5/5 —
  still no worse than flat PHEAD, and the router alone still earns its place.
- First candidate **Qwen2.5-VL-7B** (Apache-2.0). Then Pixtral-12B, InternVL3-8B,
  Kimi-VL-A3B. **Not** Llama 3.2 Vision (excludes EU-domiciled entities) or Gemma 3.

### 2. End-to-end harness trials

Run the assembled harness on the test set and compare against **V1 cascade · flat klein
(the v2.0 baseline) · flat BC_klein · the harness**. Same test set, same seed.
Roughly 4 arms × 38 sets ≈ $2 fal. This produces the number that goes in the report.

### 3. Self-hosted parity run

Every number in every V2 document is a **fal** number, and V2's premise is open weights
in the deploy path. **Owed regardless of everything else, and the gap most likely to
matter in review.** Cheap hedge available: one pair end to end before the full run.

### 4. Licence verification

- **`mattmdjaga/segformer_b2_clothes`** — head detection depends on it; currently
  **unverified and not cleared for deploy.** This one can block shipping.
- Whichever VLM is chosen, against its model card.

### 5. The V2 report

The deliverable. Draws on ARCHITECTURE.md, DECISIONS.md and the trial numbers from 2.

---

## Iteration — not blocking

### 6. Recompute the hair threshold over all 48 references

14% is fitted on 38 sets. AUC 0.862 is the honest number. Held out, not fitted. The
12–16% plateau is reassuring but is not a substitute.

### 7. v2.3 (artefacts) — *may be skippable, decide after step 2*

If VLM-A plus QX escalation removes AI artefacts, v2.3's founding question is already
partly answered and its scope shrinks to whatever survives the harness trials.

### 8. v2.4 (auxiliary realism) — a single test

Per current scope: does anything beat SeedVR2 `noise_scale=0` on both batches. Highest-
priority candidate is **Z-Image Base + PAI Fun tile-ControlNet + UltraReal LoRA**
(self-host only) — the only remaining route to de-glossing, which SeedVR2 does not do.

### 9. Anatomical plausibility pre-filter

MediaPipe Hands finger counting, impossible pose landmarks. Free, deterministic, runs
ahead of VLM-A. Narrow, but it is the **only** deterministic artefact signal that exists
— every other output check measured 0.38–0.57 AUC.

### 10. The user-specification branch has no evidence

Nothing in the test set carries a user-named garment region. Either add cases, or mark
the branch reasoned-not-measured in the report.

### 11. A VLM router — testable, low ceiling

Could generalise past hair to non-standard pose and unusual garments. Must beat AUC
0.862 for a ceiling of **0.033 gen/request** (a perfect router saves 0.053; a VLM router
costs 0.020). Record it; do not build it yet.

---

## Housekeeping

- [ ] **Nothing is committed** since the harness work began.
- [ ] `v2/artifacts/index.html` is stale — lists 8 pages, 25 exist; omits every page
      built since Aug 18.
- [ ] `v221_crop_tuning_pcrop.html` is a dead orphan with no generator;
      `pcrop_page.py` writes the `_phead` page but still carries a stale
      `<title>Crop Tuning — PCROP</title>`.
- [ ] `v221_phase3_acab.html` and `v221_phase3_fashn.html` are unreferenced by any doc.
- [ ] Resolve the contradiction over whether the klein base/distilled comparison had a
      resolution confound (`V2.1_RESULTS.md:122` says no, `:20` and
      `V2.1.1_RESULTS.md:67` say yes).
- [ ] AC ladder is numbered AC0–AC8 in `EXPERIMENT.md:234` and AC0–AC9 in the table
      below it and in `PLAN.md:64`.
