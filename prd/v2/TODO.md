# V2 — what is left

Ordered. Everything above the line closes V2; everything below is iteration.
Design: [ARCHITECTURE.md](ARCHITECTURE.md) · History: [DECISIONS.md](DECISIONS.md)

Last updated 2026-08-22.

**v2.2 is closed.** The harness is settled at 2.158 generations/request,
**31 perfect / 7 ok / 0 fail** — essentially the cost of the best single arm
(2.000 for 28/6/4), and nothing ships broken.

**v2.4 is partly closed.** The realism pass is validated end to end over harness
output and is now **conditional** — skip if already sharp, revert if it damages
the face. 24% fewer calls, no frame below 0.90 identity, essentially all of the
sharpening benefit. See [v2.4/RESULTS.md](v2.4/RESULTS.md). What remains of v2.4
is the *replacement* question, not the validation one.

---

## Blocking V2 completion

### 1. The end-to-end run — the deliverable number

Run the **assembled** pipeline, not a replay of stored arm outputs, over the 38
sets: router → arm → crash guard → VLM-A → escalate → conditional realism pass.

The realism stage no longer needs *validating* here — v2.4 did that — but it does
need running **as part of one assembled program** rather than as a replay plus a
separate script, because that program is the deliverable.

Comparison arms, same sets, same seed:

| arm | why |
|---|---|
| `qwen_2511` | the model on the Magic Hour website today — the baseline that matters |
| flat `klein` (C3.1) | the v2.0 base with the shipped crop, no harness |
| flat `BC_klein` | the strongest single arm |
| **the harness** | the deliverable |

**Not** the V1 cascade: seedream is closed-weights, and its numbers came from a
different test set, so the comparison would be invalid twice over.

Estimated **~$2–3 fal**.

### 2. Self-hosted parity run

Every number in every V2 document is a **fal** number and V2's premise is open
weights in the deploy path. **Needs a rented GPU or Colab** — the local machine is
an i3 with 8 GB and no GPU. The VLM notebook is the template.

### 3. Licence verification

- **`mattmdjaga/segformer_b2_clothes`** — head detection depends on it, currently
  unverified and **not cleared for deploy**. This one can block shipping.
- **Qwen3-VL-8B** — expected Apache-2.0, unconfirmed against the model card.

### 4. The V2 report

Draws on ARCHITECTURE.md, DECISIONS.md and the numbers from step 1.

---

## Iteration — not blocking

### 5. Binary forced-choice prompts, and fp16

The single highest-value follow-up on the gate. The model hedges — **331 of 570
verdicts were `OK`**, only 49 `FAIL` — which is exactly what caps recall at 51%.
Removing the middle option and running fp16 instead of 4-bit are both untried and
both plausibly worth several points. ~5 minutes of runtime in the same notebook.

### 6. Recompute the hair threshold over all 48 references

14% is fitted on 38 sets. AUC 0.862 is the honest number; the cut-point is not.

### 7. v2.3 (artefacts) — scope has shrunk, decide after step 1

Its founding question was whether artefacts can be repaired. Two results bear on
it: the VLM cannot *detect* artefacts in our outputs (the `artefact` prompt never
fired), and the harness already removes 3 of 4 shipped failures. Re-scope to
whatever survives the end-to-end run rather than running the original plan.

### 8. v2.4 — what is left of it: the replacement question only

Validation and the conditional trigger are **done** ([RESULTS](v2.4/RESULTS.md)).
What remains is whether anything *beats* SeedVR2. Highest-priority candidate:
**Z-Image Base + PAI Fun tile-ControlNet + UltraReal LoRA** (self-host only) — the
only remaining route to **de-glossing**, which SeedVR2 does not do and never did.

Also worth revisiting cheaply: the realism thresholds (2.5, 0.90) are fitted on 38
frames, and the identity figure is confounded by comparing against a 2× upscale of
the same frame. Re-measure at matched scale.

### 9. Anatomical plausibility pre-filter

MediaPipe Hands finger counting, impossible pose landmarks. Free, deterministic,
runs ahead of VLM-A. Narrow, but the only deterministic artefact signal available.

### 10. The user-specification branch has no evidence

Nothing in the test set carries a user-named garment region. Either add cases or
mark it reasoned-not-measured in the report.

### 11. Independent-score tie-break — revisit only if QX stops dominating

Scoring each candidate separately and comparing beat the pairwise call (4/5 vs
3/5) and is structurally sounder — no position to be biased by. Still lost to
"always take QX" (5/5) on n = 5.

---

## Housekeeping

- [ ] `v2/artifacts/index.html` is stale — lists 8 pages, 26 exist.
- [ ] `v221_crop_tuning_pcrop.html` is a dead orphan; `pcrop_page.py` writes the
      `_phead` page but still carries a stale `<title>...PCROP</title>`.
- [ ] Branch `v2.2.3-harness` is unmerged and unpushed.
