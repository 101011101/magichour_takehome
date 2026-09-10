# V3 — what is left

Live list. One line per item, newest investigation last. An item is done when its evidence
is in the tree, not when the code runs. Written 2026-09-10.

## The decision

**`ER` is the arm that ships.** One verb in call 2 — *replace the clothing in image 1 with
the clothing in image 2* — over `BC`'s pipeline unchanged: klein bald pass, V2 cropper head
subtraction, klein edit. No extra call, no extra model, no measurable extra time
(CAD 0.273 against `BC`'s 0.277 for 600 cells), and no cell in the 150-cell head-to-head was
marked worse than `BC`.

**The product on top of it is a seed randomiser: on a rejected image, redraw at a fresh
seed.** The failure record says why. Over `BC`'s 600 blind-marked cells (200 pairs x seeds
46/47/48):

| | |
|---|---|
| failed cells | 29 of 600 (4.8%) |
| pairs failing at 1 of 3 seeds | 11 |
| pairs failing at 2 of 3 seeds | 6 |
| **pairs failing at every seed** | **2 (1.0% of the catalogue)** |

So **17 of the 19 pairs that fail at all (89%) have at least one seed that passes**, and
given a failed cell, a different seed of the same pair passes **34/58 = 59%** of the time.
One retry takes the expected residual from 4.8% to **~2.0%**, two retries approach the
**1.0% floor** set by the pairs that fail at every seed — the ones whose reference is wrong,
which no seed repairs. The cost is bounded by the failure rate itself: only rejected images
are redrawn, so a one-retry policy adds ~5% to the call count.

- [ ] **The dependency, and it is the real work: a rejector.** A seed randomiser needs
      something that decides an image failed. The v3.6 VLM judge is a first attempt and is
      **not yet good enough** — its `artifacts` flag fires on 45% of cells a human passed.
      Its `limbs_over` flag is the strongest signal found so far (14.8x lift over base rate)
      and `phasing` is usable (2.7x); the artifact bucket is not. Build the rejector on the
      flags that discriminate, and measure it against the blind human marks before trusting
      it to spend calls.

## Now — the road to the report

- [ ] **Mark `BC` against `ER`.** `v3/report/v36_er_vs_bc.html`, 150 cells, three keys and a
      star. The star is the report's figure shortlist and is deliberately not the verdict.
      Export to `v36_er_vs_bc.csv`.
- [ ] **Decide `ER` on the marks**, split by `BC`'s own record: wins on the 29 it failed,
      and — the one that decides — losses on the 121 it passed.
- [ ] **Run the iron man for the chosen prompt.** `v3/colab/v36_ironman_er.ipynb`, 600 cells,
      `BC`'s own references, ~25 min, ~CAD 0.3. Already built and pushed.
- [ ] **Count it blind.** `python3 v3/build/bc_count_page.py ER` → `v3/report/er_count.html`,
      the identical page `BC`'s 4.8% came from. Export `er_count.csv`.
- [ ] **Re-mark 100 random `BC` cells in the same sitting** as the `ER` count. `BC` was
      marked 2026-09-10 and `ER` will not be; without this the two rates are one reviewer-day
      apart and the gap is not attributable. v3.5 §4 raised exactly this problem for
      `VEi`/`BC` and it is not yet closed.
- [ ] **Join the two counts per cell** — which cells changed verdict, not just the two
      percentages. The join survives strictness drift; the headline rates do not.
- [ ] **Write `prd/v3/v3.6/`** — EXPERIMENT, RESULTS, TEST per `SCHEMA.md`, then the
      submission report.

## Open questions v3.5 and v3.6 raised and did not close

- [ ] **The regeneration tax is still unpriced.** v3.5 §4: `BC` 4.8% against the lock's 9.2%,
      43 cells where the lock fails and `BC` does not against 17 the other way — but the two
      rates came from different protocols. `v3/report/vei_count.html` exists to fix that and
      **the pass has not been exported**. Until it is, no conclusion in v3.5 §4 should be
      quoted in the report.
- [ ] **`BC` cannot re-pose and the fold does not punish it.** The 200-pair matrix is mostly
      front-facing wearers. The honest question is not "is `BC` better" but "does the re-pose
      buy back more than the re-draw costs, and on what share of a real catalogue?"
- [ ] **The hybrid nobody has built.** If the re-draw is the tax, the arm to build re-poses
      **only when the pose reader says the wearer is not neutral** and otherwise ships the
      garment pixels untouched. That is a router, not a prompt, and nothing has tested it.
- [ ] **`F1` — the wearer's own accessories survive.** Handbags and shorts persist under every
      reference arm identically (v3.5 §2). Person-side, untouched by anything in v3.6.
- [ ] **The geometry class is unreachable by prompt.** `g004+g005` (trousers under shorts),
      `g005+g009` (one trouser leg, one bare knee) fail identically under all six v3.6
      prompts. If it matters it needs a mask, not words.

## Settled in v3.6 — do not reopen without new evidence

- [x] **The verb, not the paragraph.** Adding clauses to call 2 (`EFR`, `EX`) did not beat
      changing the verb. Longer prompts drift a 4-step distilled model.
- [x] **Never name a body part the crop excludes — on call 2 as well.** Measured, not
      argued: on the 59 cells whose photograph has no feet, feet appear in the output of
      `ERS` (names them anyway) on **21**, and of `ERD` (dynamic read) on **2**.
      `v3/build/v36_spawn_check.py`, `meta/spawned_feet.csv`.
- [x] **The limb clause does not ship.** `ERS` is harmful and `ERD` only buys back the harm
      `ERS` causes — plain `ER` never names a limb and never pays it. The pose read stays in
      call 1 where it belongs.
- [x] **The pipeline is deterministic.** On the 86 cells where `ERD` and `ERS` were sent
      identical text, the outputs are byte-identical, so every difference measured in v3.6 is
      the prompt and not sampling noise.
- [x] **fal and the A100 are not the same deployment.** Same prompt, seed and canvas rule;
      most archived `BC` failures do not reproduce on fal. Any comparison against a record
      must run on the hardware the record was made on. (v3.6 fal probe, 87 calls.)

## Housekeeping

- [ ] `v3/runs/v36/**` and `v3/report/img_v36*` are gitignored by the V3 rule — the evidence
      lives on Drive (`v3_runs/v36_*.zip`). Make sure the report links say so.
- [ ] `prd/v3/README.md` is modified in the working tree and uncommitted.
- [ ] Root-level `bc_count.csv`, `im2_*.csv` and `v34_*.csv` are loose marks files; the
      tracked copies live in `v3/testsets/`. Tidy before the submission commit.
