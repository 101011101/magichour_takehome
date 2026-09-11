# v3.4 — RESULTS

**Status: open.** Evidence for [EXPERIMENT.md](EXPERIMENT.md); the matrix is [TEST.md](TEST.md).

## Where the failure records live

Two different things are called "the v3.4 failure set" and they are not the same set.
`v3/testsets/v34_failures.csv` is selected on **v3.3's** failures — it was generated from
`v33_ironman_votes_bca4.csv` and predates the lock. `v34_im2_truth.json` and the set
derived from it, `v3/testsets/v35_failures.csv`, are the **v3.4 lock's own** failures,
from iron man 2. A reader asking what v3.4 failed on wants the second. Every count below
was read off the file; rows exclude the header.

**The v3.4 lock's own record — arm `VEi`, 200 pairs × seeds 46/47/48.**

| file | what it is | columns / keys | rows | defined in |
|---|---|---|---|---|
| `v34_im2_truth.json` | the per-cell human ground truth; the artefact of record | keys `set_id\|seed`, values `CLEAN` 475 / `MID` 70 / `FAIL` 55 | 600 | §10.5 |
| `v34_im2_failure_audit.csv` | the reviewer re-judging every cell the judge failed | `set_id,seed,judge_verdict,audit` — `judge_verdict` is `fail` throughout; `audit` = `agree` 42 / `passable` 62 / `wrong` 74; 84 pairs | 178 | §10.4 |
| `im2_failure_audit.csv` | **byte-identical** to the above — the browser's download name, kept by accident. Cite the `v34_` one | as above | 178 | §10.4 |
| `im2_pass_audit.csv` | the false-negative pass, every cell the judge passed | `set_id,seed,judge_verdict,audit` — `judge_verdict` is `pass` throughout; `audit` = `agree` 401 / `fails` 13 / `borderline` 8; 165 pairs | 422 | §10.5 |
| `v3/runs/v34/judge_ironman2_vei/meta/vlm_scores.csv` | the judge's raw six scores, the input the audits overturn | `set_id,arm,seed,model,garment,identity,scene,clean,hands,realism,note,seconds,tokens_in,tokens_out` | 600 | §10.2 |
| `v3/testsets/v35_failures.csv` | derived: the 31 pairs where `VEi` has a real failure at ≥1 seed | `set_id,person,person_file,garment,garment_file,person_framing,garment_hard_case,v46,v47,v48,seed_stable` — verdicts are `CLEAN`/`MID`/`FAIL`; `seed_stable=yes` on 8 | 31 | [v3.5 TEST.md](../v3.5/TEST.md) |

The truth file is exactly the two audit CSVs merged — all 600 keys reconcile, with
`wrong` and pass-`agree` → `CLEAN`, `passable` and `borderline` → `MID`, fail-`agree` and
`fails` → `FAIL`. Nothing is judged twice and nothing is unjudged.

**The v3.3-selected sets, and the link marks.**

| file | what it is | columns | rows | defined in |
|---|---|---|---|---|
| `v3/testsets/v34_failures.csv` | v3.3's failures — the matrix for links A–H, **not** v3.4's failures | `set_id,person,person_file,garment,garment_file,class,seed_stable,v46,v47,v48,person_pose,person_framing` — `class` F1 9 / F2 8 / F3 12 / F4 2; `seed_stable=yes` on 4 | 31 | [TEST.md](TEST.md) |
| `v3/testsets/v34_controls.csv` | the unselected control set | `set_id,person,person_file,garment,garment_file,v46,v47,v48` | 30 | [TEST.md](TEST.md) |
| `v33_ironman_votes_bca4.csv` | v3.3's votes, the source `v34_failures.csv` was cut from | `set_id,seed,vote,nudge` — `vote` tie 459 / B 59 / A 55 / fail 26; `nudge=ok` on 11. 200 pairs but **599 rows, not 600** — one seed-47 cell is missing | 599 | [v3.3 RESULTS §14.5](../v3.3/RESULTS.md#145-second-export-0245-with-nudges-and-the-failure-taxonomy) |
| `v34_linkD_marks.csv` | link D's marks on `V34` | `set_id,seed,verdict` — `pass` 74 / `fail_better` 11 / `worse` 8; 31 pairs × seeds 49/50/51 | 93 | §5 |
| `v34_linkE_votes.csv` | link E's row winners | `set_id,seed,verdict` — `tie` 68 / `last` 13 / `latest` 8 / `original` 4 | 93 | §7 |
| `v34_a100_marks.csv` | **byte-identical** to `v34_linkE_votes.csv` — the page's download name. Cite the `linkE` one | as above | 93 | §7 |
| `v3/runs/v34/judge_vei/meta/per_pair.csv` | the blind judge, `VEi` vs `VE` vs `VS`, per pair | 79 columns, per-arm scores and pairwise diffs | 31 | §9.1 |

**The pages that render them**, each with the script under `v3/build/` that builds it:
`ironman2_vei.html` (`ironman2_vei_page.py`) · `ironman2_failures.html`
(`ironman2_failures_page.py`, exports `im2_failure_audit.csv`) · `ironman2_passed.html`
(`ironman2_passed_page.py`, exports `im2_pass_audit.csv`) · `ironman2_fourway.html`
(`ironman2_fourway_page.py`, reads `v34_im2_truth.json` for the verdict borders) ·
`v34_a100*.html` (`v34_a100_page.py`, exports `v34_a100_marks.csv`) ·
`v34_vs_failed.html` (`v34_vs_failed_page.py`, reads `v34_linkD_marks.csv`) ·
`v35_linkB.html` (`v35_linkB_page.py`, reads `v3/testsets/v35_failures.csv`).

**Not in the repo.** TEST.md says `v34_failures.csv` was "generated from
`v33_ironman_votes_bca4.csv` + `key.csv` by the script in this commit"; no such script is
under `v3/build/`, so that set is on disk without its generator and a regeneration would be
a rewrite. `v35_failures.csv` had the same gap when this section was written; it now has
one — `v3/build/make_v35_failures.py`, verified to reproduce the file on disk byte for
byte.

## 1. Link A — the ankle cut removed, on the failure set (2026-08-31)

**Run.** fal `fal-ai/flux-2/klein/4b/distilled/edit`, not the A100 — the reviewer's call for
a small set. One reference call per garment (22), the cut applied or not as a
post-process, so `V` and `Vnc` share every pixel except the feet; 31 pairs × 3 seeds × 2
arms = 186 edits, 0 failures, ~$3.1 fal-equivalent. Runner `v3/build/run_v34_linkA.py`,
outputs `v3/runs/v34/linkA/`, page `v3/report/v34_linkA.html` (the A100 v3.3 output the
reviewer scored is the third column, for orientation; fal and the A100 are not
seed-identical, so the comparison of record is `V` vs `Vnc` *within* this run).

The cut fired on 16 of the 22 references; on 6 (`queen_latifah`, `g015`, `g029`, `g030`,
`p004`, `p014`) the reader found no ankles — partial crops or hidden feet — and `V` = `Vnc`
there by construction.

### 1.1 Result — no failure class moves

| class | pairs | `V` vs `Vnc` at the output |
|---|---|---|
| F1 wearer's clothing survives | 9 | **identical failure**: the kimono sleeves, hat and bag, `g004`'s olive trousers, `p001`'s jeans are there in both. The reference's feet have nothing to do with the wearer's sleeves |
| F2 skirt / dress → trousers | 8 | **identical**: zendaya's wrap skirt is trousers on Hugh, `p015`, `p025` in both; the slip dress on `g005` splits in both |
| F3 reference drift | 12 | **identical** on colour and pieces — the drift is in the regeneration, upstream of the cut |
| F4 exposed skin | 2 | identical |

What the cut *does* change, on a handful of cells: **footwear.** With the feet left in
the reference, the reference's shoes transfer where the wearer's own were kept before
(`peacoat + g030`'s boots, `g004 + g005`'s sneakers); with the cut, the wearer's shoes
stay. Neither was scored as the failure on those cells. Nothing else differs to the eye
across the 93 cell-pairs.

### 1.2 Reading

- **The ankle cut is not a cause of any v3.3 failure.** It stays in the lock as adopted
  (§9.2 of v3.3): safe, and now shown neutral on the failure set as well as on the fold.
- **The footwear question is a product decision, not a defect**: cut = wearer keeps their
  shoes; no cut = the reference's shoes come along when the model takes them. Either is
  defensible; the lock chose the former.
- The failures are where the taxonomy said: F1/F2 on the person side, F3 in the
  regeneration. Link A closes the one reference-side suspicion that was cheap to test.

*A side observation, not a result:* several cells differ visibly between the fal run
and the A100 run of the same prompt and seed (`g014 + g029`: the blazer over the blue
dress on the A100, a long coat on fal) — the backend variance of v3.3 §13 again, and
another reason select-from-N is the first real link.

## 2. Link B — fal on 30 clean controls: is fal "more consistent"? (2026-08-31)

**Why.** On link A's failure set fal passed many cells the A100 had failed, and the
reviewer asked whether fal's inference stack is simply better at limbs and leaks. The
failure set cannot answer that — it is selected on A100 failures, and 27 of its 31 pairs
pass on *any* fresh draw ([v3.3 §14.6](../v3.3/RESULTS.md#146-are-the-failures-seed-stable-mostly-not)).
A control set can: if fal is better, it should not fail pairs the A100 did not.

**Run.** `v3/testsets/v34_controls.csv` — 30 pairs drawn (seed 34) from the 163 pairs on
which v3.3 had **no** failing cell at any seed. Arm `Vnc` (no ankle cut) on fal, seeds
46/47/48: 23 references, 90 edits, 0 failures, ~$1.7. Page `v3/report/v34_controls.html`
(fal beside the A100 output the reviewer scored, per seed, with a fail toggle for the
reviewer). Outputs `v3/runs/v34/linkB_controls/`.

### 2.1 Result — fal fails the controls at the fold's rate

By my eye (the reviewer's marks, when exported, are the number of record):

| fal cell | what | class |
|---|---|---|
| `g005 + g009` seeds 46, 48 | the wearer's grey shorts survive under the cream trousers → shorts | F1 |
| `g013 + g014` seeds 47, 48 | the wearer's patterned dress hem shows under the blue slip dress | F1 |
| `floral_kimono + quarterzip` all seeds | kimono sleeves and bag survive — as on the A100 (the reviewer had called those cells ties: equally wrong) | F1 |
| the other 25 pairs | indistinguishable from the A100 to the eye; small drape / footwear differences | — |

**≈ 4–5 of 90 cells (5%)** are failures on fal that the A100 did not make on these pairs
— against the A100's own 4.3% fail rate on the fold. Same rate, same class (F1, the
wearer's clothing surviving), different cells.

### 2.2 Reading

- **fal is not more consistent. It is a different draw of the same model.** Link A's
  rescues were regression to the mean on a failure-selected set; on unselected pairs fal
  fails where the A100 passed, at the same rate and in the same way.
- The failures are **F1 again**, on cells that were clean on the A100 — the strongest
  evidence yet that the clothing-leak class is a *sampling* hazard on hard pairs, not a
  property of a backend or of a seed. Select-from-N is the lever; the person-side
  agnostic is the fix.
- No difference between the stacks is worth chasing at the reference-preprocessing
  level on this evidence. The one difference that *is* real — 35/255 mean pixel
  difference between "same-seed" references — is the RNG, not the model.

**Staged, not run:** `v3/colab/v34_a100.ipynb` — the same two matrices on the A100 at
**new seeds 49/50/51**, no ankle cut, one clean notebook. It closes the loop from the
other side: if a fresh A100 draw rescues the failure set as fal did, backend is off the
table entirely.

## 3. Link C — the A100 at new seeds, no ankle cut, failure set + controls (2026-09-01)

**Run** `v34_a100_nocut_20260901_0323` from `v3/colab/v34_a100.ipynb`: arm `Vnc`, seeds
**49/50/51**, NVIDIA A100-40GB, klein 4B bf16 from the Drive cache (load 273 s). 36
references + 183 edits = 219 klein calls at **1.94 s/call**; the two matrices ran as
separate stages, ~3.5 min of generation each; **~CAD 0.08** for both at the reviewer's
rate. Page `v3/report/v34_a100.html` (new cell · original scored cell · fal cell, per
seed, with fail toggles for the reviewer); outputs `v3/runs/v34/v34_a100_nocut_*/`.

### 3.1 Failure set — the fresh A100 draw rescues what fal rescued, and no more

By my eye, against the original verdicts:

| | pairs | what the new seeds do |
|---|---|---|
| seed-stable on the original run (`floral_kimono + g005`, `+ g024`, `hugh + zendaya`, `emma + scarlett`) | 4 | **still fail at all three new seeds** — the kimono sleeves and bag, the wrap skirt as trousers, the dress as a strapless top. A fifth, `p025 + zendaya`, is trousers at all three new seeds too |
| the rest | 27 | **mixed, as before**: `g005 + g014` passes 1 of 3 (shorts leak at 49, split at 50), `g024 + p002` 1 of 3, `g004 + g005` 1 of 3, `g014 + g029` varies between coat and blazer-over-dress; the F3 pairs (`plaid + g029`, `peacoat + g030`, `zendaya + peacoat`, `g018 + g024`, `p026 + g013`, `p011 + p016`, `p028 + g015`) are clean or near-clean at most new seeds |

The rescue rate is the same order as fal's on link A. Nothing here that fal did and the
A100 does not, or the reverse.

### 3.2 Controls — the fresh A100 draw creates new F1 leaks at ~5%

| new-A100 cell | what |
|---|---|
| `g005 + g009` seed 49 | the wearer's grey shorts under the cream trousers (the same cell that leaked on fal at 46/48) |
| `g014 + p007` seeds 49, 50 | the wearer's blue dress hem under the white dress |
| `g018 + p010` seed 49 | the wearer's black skirt under the blue pleated skirt |
| `floral_kimono + quarterzip` all seeds | kimono sleeves and bag, as on every backend and seed |

**~4–5 of 90 (5%)**, all F1, on cells that were clean at 46/47/48 — the same rate and the
same class fal produced on link B, on partly different cells.

### 3.3 Reading — the backend is off the table

Three backends/draws on the same pairs now agree: the original A100 (46/47/48), fal
(46/47/48), the A100 again (49/50/51). Each rescues ~85% of the failure set and each
fails ~5% of clean controls, always in class F1 (the wearer's clothing surviving) and on
seed-stable pairs always the same four or five. **The failure rate is a property of the
model on hard pairs, sampled; not of fal, not of the A100, not of a seed.** That settles
links A–C together:

- the ankle cut is neutral (A);
- fal is not a better sampler (B);
- a fresh A100 draw is not either (C);
- **select-from-N is the lever** for the ~85% that are draws, and the person-side
  agnostic is the only route to the seed-stable residue.

## 4. Deep dive — what is different between our klein and fal's (2026-09-01)

Three background investigations, launched on the reviewer's observation that fal passes
cells the A100 fails (`floral_kimono + g024` at fal seeds 46 and 48; every A100 seed
failed) and that "if fal fails, everything fails, but not the reverse". Full write-ups:
`v3/runs/v34/deepdive_code_diff.md` (sources read and quoted),
`v3/runs/v34/probe_fal/PROBE.md` (28 fal calls, measured), and the VLM judge report in
`v3/runs/v34/judge_fal_vs_a100/` (pending at the time of writing).

### 4.1 Measured on fal (probe)

| question | measured |
|---|---|
| output canvas | **not image 1's size.** 0.5 / 0.7 / 1.1 / 1.5 / 2.5 MP inputs all return 832×1248. Rule reproducing 20/20 responses: scale image 1 to **area 1,048,576 px preserving aspect, up or down, floor each side to a multiple of 32**. The OpenAPI's "uses the input image size" is wrong in practice |
| reference size | irrelevant: 0.25 / 0.93 / 3 MP references give outputs equal to the noise floor → the reference is re-sampled to a fixed size internally |
| steps | default is 4 (4 vs explicit 4: identical; 4 vs 8: MAD 3.7) |
| determinism | 9 of 11 same-argument repeats pixel-identical; 2 differ by MAD ≈ 0.4 (noise floor). Never byte-identical (a per-response C2PA chunk) |
| input encoding | PNG vs JPEG-q95 data-URI, data-URI vs uploaded URL: at or below the noise floor |
| order / duplicates | image 1 sets the canvas; identity follows the human photo wherever it is; duplicated references are not collapsed |

### 4.2 Read from source (diffusers `Flux2KleinPipeline`, BFL `flux2/sampling.py`)

The one line that differs: `klein_local.py` passes `height, width` = image 1 at ≤1.15 MP,
floor 16, never upscaled. Two consequences, both code-verified:

1. **The sigma schedule.** `compute_empirical_mu` — byte-identical in diffusers and BFL —
   branches at **4,300 image tokens (≈1.10 MP)**. Above it, `mu ≈ 1.20` (sigmas
   `[1, .91, .77, .53, 0]`); below, `mu ≈ 2.29` (`[1, .97, .91, .77, 0]`). klein 4B is
   timestep-distilled; its 4 steps are for one schedule. fal's canvas (≤4,096 tokens) is
   always below the branch. **Ours crossed it on 38 of 200 iron-man call-2 outputs**
   (token range 2,304–4,489) — the agent's "every output" was wrong and is corrected
   here. Those 38 pairs have a v3.3 failing cell **21%** of the time against **14%** for
   the 162 below; suggestive, not decisive at n = 38.
2. **Token count in general.** Because fal upscales to ~1 MP and we do not, the 162
   pairs below the branch render on **2,300–4,000 tokens locally against fal's ~4,000
   every time**. The wearer's sleeves, hems and limbs are smaller structures on a
   coarser grid. Also the output grid ≠ the pipeline's 1 MP reference grid for image 1
   (e.g. 54×82 vs 52×78), so RoPE-aligned wearer tokens are displaced 3–4 tokens toward
   the bottom/right — plausible, untested.

Killed by reading both sources: guidance (`guidance_embeds: false`), step count, sigma
spacing, PNG vs PIL, prompt truncation (512 tokens, prompt ≈ 80), position ids, concat
order, VAE sampling. Unverifiable: fal's kernels/dtype/GPU, its exact reference cap, its
seed→noise mapping.

### 4.3 What follows — link D

One rule fixes both: **fal's canvas on call 2** (area 1024², floor 32, up or down),
implemented as `klein_local._size_fal` and arm **`Vfc`** (= `Vnc` + that canvas; call 1
unchanged, its ~0.5 MP crop never crossed the branch). Run on the failure set and the
controls at **the link-C seeds 49/50/51**, so `Vnc` vs `Vfc` differ in the canvas and
nothing else. Notebook `v34_a100.ipynb` cell 8.

The honest prior, from §3: three draws already agree the failure rate is variance on hard
pairs; the canvas can move the *rate*, not abolish the seed-stable residue.

### 4.4 The blind judge: is fal better on the failure set? — not distinguishably

gpt-5.5, blind to the arm, all 186 cells (31 pairs × 3 seeds × {fal 46/47/48, A100
49/50/51}, both `Vnc`), $3.56. Report and data: `v3/runs/v34/judge_fal_vs_a100/`.

| metric (1–5) | fal | A100 | diff | 95% CI | sign p | Wilcoxon p |
|---|---|---|---|---|---|---|
| fidelity (garment, identity, scene) | 3.87 | 3.78 | +0.09 | [−0.01, +0.20] | 0.15 | 0.13 |
| realism (clean, hands, realism) | 3.66 | 3.60 | +0.05 | [−0.08, +0.20] | 1.00 | 0.58 |
| garment alone | 2.70 | 2.76 | −0.06 | n.s. | | |
| pair wins (fidelity first) | 19 | 12 | +7 | permutation p 0.24 | | |

- fal's edge is **identity/scene preservation** (+0.16/+0.17, CIs touching zero) — the
  canvas story, plausibly — **not garment**: on the criterion the failure classes are
  about, the A100 is marginally ahead, and the fail proxy is **41 of 93 cells on both
  arms**.
- **The gap is smaller than one seed's noise.** Within-pair seed SD is 0.24 on both
  backends; A100 seed 49 beats A100 seed 51 by +0.16 fidelity (17–8 pairs) — larger than
  fal's edge over the A100.
- Per class: F1 +0.14 (8/9 pairs, but garment 2–3 on both arms), F2 +0.07, **F3 −0.02
  (a dead heat on 12 pairs)**, F4 +0.61 (n = 2).
- fal wins all nine cross-seed cells on 4 pairs (`hugh + zendaya`, `scarlett + denim`,
  `g027 + p003`, `p013 + scarlett`); the A100 on none. Small, and consistent with the
  identity/scene edge.
- **`floral_kimono + g024`**: the judge calls the F1 leak — hat, bag, sandals, cuffs
  surviving — in **all six cells**, fal seeds 46 and 48 included (garment 3 and 2; seed
  48 is the lowest of the six). Pair fidelity 3.56 fal vs 3.67 A100. The reviewer's
  reading that fal passed at 46 and 48 is not supported by the judge, and link A's own
  record (§1.1, "identical failure") did not see it either — worth a second look at
  full size on `v3/report/v34_linkA.html`.

**Reading, with §4.1–4.3.** The code difference is real (canvas → tokens → schedule),
and the judge sees its likely signature — a small, consistent identity/scene edge for
fal. It does **not** see a garment-fidelity edge, and the overall gap sits inside
seed-to-seed noise. "If fal fails, we fail; if we fail, fal may not" is therefore
**variance plus a small canvas effect**, not a stronger model. Link D measures the
canvas effect directly; select-from-N remains the lever for the variance.

## 5. The v3.4 version, and link D's set-up (2026-09-01)

**The v3.4 version** (decided by the reviewer after §4): the v3.3 lock with two changes.

| | v3.3 lock | v3.4 version |
|---|---|---|
| ankle cut | on | **off** (link A: neutral on the failures; footwear follows the reference) |
| call-2 canvas | image 1 at ≤1.15 MP, floor 16, never upscaled | **fal's rule: area 1,048,576 px, aspect kept, up or down, floor 32** (`klein_local._size_fal`) — ≤4,096 tokens, below the 4,300-token schedule branch, ~4,000 tokens for every person |
| everything else | — | unchanged: A4 crop, head swap from the neck up, `PERSON_CLAUSE`, hold sentence, `E3`, references at the run's first seed (49 in link D, as in link C — "seed 46 references" held only for runs seeded at 46) |

Arm name **`V34`** in `run_ironman.py`. Call 1 is untouched (its ~0.5 MP crop never
crossed the branch). `BC`, when it is run beside `V34`, gets the same canvas so the
comparison stays fair — the canvas is a property of call 2, not of the arm. (Implemented
2026-09-03: the runner's `bc_canvas` follows the run — fal iff a `FAL_CANVAS_ARMS` arm is
present, overridable for a stand-alone `bcedit` stage — and is recorded in `run.json`.)

**Link D as it will run.** `v3/colab/v34_a100.ipynb`, `V34` on the **failure set only**
(the reviewer's choice — a sample first), seeds **49/50/51**, the link-C seeds, so the
`Vnc` cell and the `V34` cell for the same pair and seed differ in the canvas and nothing
else. Page: `python3 v3/build/v34_a100_page.py <dir> --arm V34` puts the three side by
side — `V34` · the original scored cell · the link-C `Vnc` cell. Judge if wanted: the
same gpt-5.5 rubric as §4.4, on `V34` vs `Vnc`, is the paired number.

**What would count.** Per §4.4, the canvas should move identity/scene preservation
first; garment fidelity (F1/F2) is not expected to move. The four seed-stable pairs are
not expected to move either.

**Result (2026-09-04).** Run `v3/runs/v34/v34_a100_v34_20260904_0458` (zip on Drive):
115 klein calls at 2.07 s/call, $0.045 measured. Page `v3/report/v34_a100_V34.html`,
four columns per seed row — `V34` · the original scored cell · link C's `Vnc` (the
canvas pairing) · fal (link A's `Vnc`, s46/47/48, the benchmark). The reviewer marked
every `V34` cell three ways against the bar "worse than fal, or acceptable"
(`v34_linkD_marks.csv`):

| verdict | cells |
|---|---|
| pass — acceptable, no worse than fal | **74 / 93** |
| fails, but no worse than fal's | 11 |
| worse than fal | 8 |

Per pair: 18/31 pass at all three seeds; **29/31 pass at ≥1 seed** — select-from-N
territory, consistent with links B/C. The two pairs with no passing seed are the two
F4 pairs:

- **`g027 + p003` — the one canvas-suspect regression.** Worse than fal at **all three
  seeds**, artifact named by the reviewer: **proportion compression ("dwarfism")** —
  the person renders short and compressed, and reads as *worse* than the v3.3-canvas
  cells. The only pair where the canvas plausibly hurt. Open item: klein
  training/settings research, and a reference-side hypothesis (image 2's size/aspect
  feeding the geometry).
- **`p019 + gal_gadot`** fails at all three seeds but **no worse than fal** — this pair
  fails under either canvas and on fal's own draws; a pair problem, not a canvas one.

**Reading.** The v3.4 canvas holds parity-or-better with the fal benchmark on 85/93
cells and does not disturb the seed-variance picture; per-call cost is unchanged from
link C. One pair regressed with a specific, repeated artifact — the `g027+p003`
dwarfism — and that is the open question before v3.4 is called better than the lock.
Next: select-from-N (EXPERIMENT §0), and the dwarfism follow-up.

## 6. The `g027+p003` dwarfism, diagnosed (2026-09-04)

**The artifact, looked at directly.** `g027` is a **waist-up photograph** — image 1 has
no legs. The reference is a full-length dress. On every A100 cell (`Vnc` 49/50/51 and
`V34` 49/50/51 — six of six) the model **zooms out to an invented full-body view**, and
the invented lower half carries the compressed proportions the reviewer calls dwarfism.
fal, on the same pair (link A, s46/47/48), **keeps the waist-up framing on all three
seeds** — person exactly as in image 1, dress running out of frame, proportions intact;
its failures there are garment-side (tank-top hybrid; at s47 the Ramones print bleeds
through the dress). So the dwarfism is a **framing-retention failure**, not a canvas
artifact per se: `V34`'s canvas neither caused it (link C's `Vnc` has it too) nor fixed it.

**The one code-path difference left on this pair: call 1's canvas.** fal renders *every*
call on its ~1 MP canvas, references included — its `p003` reference is **583×1561
(0.91 MP)**. Our call 1 still uses the v33 rule (never upscale), so ours is **296×799
(0.24 MP)** — same aspect, 3.8× fewer pixels. §5's "call 1 is untouched (its ~0.5 MP
crop never crossed the branch)" was written from the fold's typical crop; the failure
set's A4 crops run as low as 0.07 MP, and most references land under 0.4 MP.

**What the fold says about scope.** Reference size alone is not predictive — refs under
0.4 MP pass 3/3 in most pairs. `g027+p003` is a conjunction: waist-up person (framing
must be held) + full-length garment (pulls toward zoom-out) + the fold's smallest person
image (0.60 MP, the only ×1.3 upscale under the fal rule) + a small, skinny reference
(0.24 MP, aspect 0.37). `p019+gal_gadot`, the other no-pass pair, fails on fal's own
draws too — not this mechanism.

**Candidate link E.** fal's canvas on **call 1** as well — references generated at ~1 MP
("all things undergo the scaling pipeline"). Prediction: `g027+p003` recovers the
waist-up framing as fal does; risk to watch: reference regressions elsewhere, since
call 1's ~0.5 MP operating point is what every scored run used. Cheap: one notebook
run on the failure set, arm beside `V34`.

## 7. Link E — references at ~1 MP, run and voted (2026-09-04)

**Run.** `v3/runs/v34/v34_a100_ve_20260904_0611` (zip on Drive): arm `VE` (fal's canvas
on both calls), failure set, seeds 49/50/51. 115 klein calls; ref 1.62 s, edit 2.94 s
(the 1 MP reference adds tokens to call 2), ≈4.9 s per pair end to end, 0.058 measured.
Page `v3/report/v34_a100_VE.html` — five columns per row (LATEST `VE` · LAST `V34` ·
`Vnc` · original · fal); the reviewer voted the **row winner** (`v34_linkE_votes.csv`):

| winner | cells |
|---|---|
| tie | **68 / 93** |
| LAST — `V34` (small ref) | 13 |
| LATEST — `VE` (1 MP ref) | 8 |
| ORIGINAL — v3.3 lock | 4 |

**Reading.**

- **The dwarfism is fixed, and it is the reference.** `g027+p003` goes to `VE` at all
  three seeds — framing held, proportions natural, as §6 predicted (its reference:
  0.95 MP vs 0.24). `p019+gal_gadot` stays tied — still a pair problem.
- **But the 1 MP reference is a targeted fix, not a general win.** Fold-wide `V34`
  edges `VE` 13–8 with 68 ties; blanket upscaling costs about as much as it buys
  (`g029+p004`, with the smallest crop of all at 0.13 MP, votes LAST 3/3 — so "small
  ref" alone does not predict who wins).
- **The v3.3 lock is out of the running**: ORIGINAL best on 4/93 cells (3 of them one
  pair, `hugh_jackman+zendaya`). Both v3.4 canvases beat it.

**The fork, for the reviewer.** Neither canvas dominates: `V34` is the better base,
`VE` rescues what `V34` cannot. Options: (a) `V34` as the version, `VE` folded into
select-from-N as an alternate draw — the selector picks per pair, dwarfism covered;
(b) conditional reference upscale on a trigger (no clean trigger found yet — crop size
does not separate the wins); (c) `VE` flat, accepting the 13 LAST cells. (a) is the
recommendation: it needs no new trigger and select-from-N is next anyway (§0).

### 7.1 The reference hallucination, verified (2026-09-04)

The upscale is **generation, not resizing**: the A4 crop enters call 1 at its native
size in both arms; only the output canvas differs. Under `VE`, klein renders ~1 MP
conditioned on a 0.13–0.9 MP crop — diffusion super-resolution, with its failure mode.
Verified on the extreme case: `p004`'s crop (0.13 MP) is a plain notch-neck tee, no
buttons; the `VE` reference (×2.67) **invents a two-button henley placket** and a hem
tag. Call 2 then faithfully dresses the person in the hallucinated garment —
`g029+p004` votes LAST 3/3. This is §E's predicted "reference regression" with its
mechanism: on very small crops, the generation-upscale invents garment structure.

**Candidate arm `VEi`:** upscale the *finished small reference* by interpolation
(Lanczos to area 1 MP) before call 2 — no new klein call, no invented structure, same
token extent in the RoPE grid. Splits the g027 fix: if interpolation alone recovers the
framing, the win was the reference's grid extent, not synthesized detail — and the
hallucination channel closes for free.

*(2026-09-05: revived as **link H**, upgraded from interpolation to SR, after the
reviewer independently arrived at the same design — "the upscale should only occur
after the first call." Wired as arm `VEi`; EXPERIMENT §H.)*

### 7.2 VS on the marked failures (fal, 2026-09-05)

**Run.** Every link-D cell marked non-pass (19 cells, 13 pairs), re-generated with
**arm `VS`** — inputs scaled by the SR model (realesr-general-x4v3, ×4 then area-down
to 1 MP; plain area-down when already ≥1 MP) — on fal at the exact failing seeds.
Runner `v3/build/run_v34_vs_fal.py`, outputs `v3/runs/v34/vs_fal/`
(`inputs_sr/` · `refs/` · `gen/`), page `v3/report/v34_vs_failed.html`
(V34 marked cell · VE · VS per row). 11 refs + 19 edits, $0.45; SR ≈ 1.5–16 s/image
on CPU, tens of ms on an A100.

**First reads.**

- `p015+p016` (F3, the 0.10 MP crop, SR ×3.17): the SR input is faithful, but call 1's
  re-pose still restructures the loose babydoll into a fitted drop-waist dress — **F3
  drift survives sharp input**, third confirmation that call-1 regeneration, not
  scaling, is the drift channel. The VS *rendering* is markedly cleaner than the marked
  V34 cell (no arm-through-fabric artifact).
- **Reviewer note (2026-09-05): "VS s50 — SR inputs (fal) is very good."**
- **Reviewer note (2026-09-05): `p019+gal_gadot` s50 under `VS` "did really good — the
  first one ever to be successful for this specific woman with her turtleneck and
  stuff."** This is the pair with no passing cell in any prior run — v3.3, links A–F,
  and fal's own draws all failed it. First recorded success on it, any recipe, any
  backend (fal draw; unconfirmed on the A100).
- Caveat as printed on the page: VS cells are fal draws beside A100 draws — orientation,
  not record. The deciding run is `VS` on the A100.

## 8. The improvement ledger (2026-09-05, for the report)

What the v3.4 scaling changes have measurably improved, in order of adoption. Every
line links to the section that carries the evidence.

| change | measured improvement | where |
|---|---|---|
| `V34` — call-2 canvas at 1 MP (up or down, floor 32) | the reviewer's bar vs fal met on **85/93** failure-set cells; **29/31 pairs pass at ≥1 seed** (the failure set was 0/31 at its original seeds by construction); stays on the distilled schedule (≤4,096 tokens < the 4,300 branch) | [§5](#5-the-v34-version-and-link-ds-set-up-2026-09-01) |
| `VE` — references generated at ~1 MP | the `g027+p003` dwarfism **eliminated 3/3** (0/6 A100 cells held framing before); references carry ~4× the garment evidence into call 2 | [§6](#6-the-g027p003-dwarfism-diagnosed-2026-09-04), [§7](#7-link-e--references-at-1-mp-run-and-voted-2026-09-04) |
| `VS` — SR-scaled inputs (algorithmic, sharp) | on the 19 marked link-D failures (fal draws): reviewer notes the s50 cells "very good"; **first-ever success on `p019+gal_gadot`** (no passing cell in v3.3, links A–F, or fal's own draws before it); `p015+p016` rendering visibly cleaner than the marked cell | [§7.2](#72-vs-on-the-marked-failures-fal-2026-09-05) |
| the lock, for contrast | the original v3.3 cell is best on only **4/93** link-E votes — both v3.4 canvases beat it | [§7](#7-link-e--references-at-1-mp-run-and-voted-2026-09-04) |

**The seed-probability reading.** The scaling changes raise the per-seed success
probability on the failure set (V34: 74/93 cells at the fal bar; 18/31 pairs pass at
all three seeds) — they shrink the bad-mode mass rather than eliminate it. The residue
is per-pair ambiguity (F1–F4). Select-from-N / gate-and-retry would absorb it, but the
reviewer ruled (2026-09-05) that **any mechanism beyond the two klein calls is v4
scope** — v3 ships exactly 2 calls per pair, and this ledger's statistics are the
evidence for whether v4 needs the mechanism at all.

**Not yet claimed:** all VS numbers are fal draws; the A100 `VS` run (link G) is the
confirmation. No v3.4 arm is scored on the 200-pair matrix yet.


## 9. Link H on the A100 — VEi first reads (2026-09-06)

**Run** `v3/runs/v34/v34_a100_vei_20260906_0334`: 115 calls, ref 1.05 s (small canvas —
cheapest of the 1 MP arms) + sr 0.19 s + edit 3.18 s ≈ 4.4 s/pair, $0.061. Page
`v3/report/v34_a100_VEi.html` (VEi · VS · VE · original · fal, winner vote,
intermediaries row).

- **`g027+p003` holds the waist-up framing at all three seeds** — the second A100
  recipe ever to do it (VE the other), with V34's exact reference content,
  SR-sharpened. **The footprint hypothesis is confirmed**: the dwarfism fix is the
  reference's ~1 MP token extent in call 2, not klein-drawn 1 MP content.
- **Reviewer (2026-09-06): "it looks pretty good for VEi."** Blind five-metric judge
  queued to check (§9.1).


### 9.1 The blind judge on VEi vs VE and VS (2026-09-06)

**Method.** The judge of record (`ironman_vlm.py::score()`, gpt-5.5, blinded — arm
names never sent), all 279 cells (31 pairs × 3 seeds × 3 arms) in one interleaved
batch; statistics as the prior report (paired diffs on pair means, 20k bootstrap,
permutation null, same-arm seed splits as the noise yardstick). $4.07.
Outputs `v3/runs/v34/judge_vei/` (REPORT.md, meta/). One correction of record: the
rubric has **six** criteria, not five — garment · identity · scene · clean · hands ·
realism (fidelity = mean of the first three).

| comparison | fidelity Δ | pairs | vs noise |
|---|---|---|---|
| **VEi vs VS** | **+0.125** (CI +0.04..+0.23, perm p=0.008) | **23–7** VEi | **outside** — real |
| **VEi vs VE** | −0.068 (CI −0.14..+0.01, perm p=0.09) | 21–10 **VE** | inside for fidelity; the hands (−0.151) and realism-axis (−0.093) deficits cross the line |
| VE vs VS (context) | +0.194, perm p<0.001 | — | ordering is consistent: **VE ≥ VEi > VS** |

Key pairs: `g027+p003` — VEi holds the framing 3/3 and beats VS by +1.00 (its largest
edge anywhere), but VE holds it too and wins the pair; `g029+p004` — VEi's worst,
last on all 9 cells; `p019+gal_gadot` — garment 1–2 on every arm, nothing fixes it;
`p015+p016` — exact three-way fidelity tie. On the **garment criterion** the three
arms are statistically identical (2.5–2.7) — the canvas work moved identity/scene/
realism, and the seed-stable failures fail on all three arms.

**Verdict (the judge's).** VEi is decisively better than VS and at-best-tied,
leaning slightly worse, against VE — never ahead on any of the six criteria, with a
small but real hands/cleanliness cost from the SR step. **If VEi takes the slot over
VE, the argument is cost (ref 1.05 s vs 2.2 s — the cheapest 1 MP arm) and the
"klein never renders above its evidence" mechanism, not judged output quality.**
The canvas call between VE and VEi is the reviewer's, with the fold-wide winner vote
on `v34_a100_VEi.html` as the remaining input.


## 10. The v3.4 version locked: VEi. Iron man 2 set up (2026-09-06)

**Decision (the reviewer).** `VEi` is the v3.4 version — see EXPERIMENT "What is
decided" for the recipe and grounds (judge §9.1: > VS outside noise, within noise of
VE, cheapest 1 MP arm, klein never renders above its evidence).

**Iron man 2.** VEi against `BC` on the 200-pair matrix (`matrix.csv`), seeds
46/47/48 — the v3.3 iron-man design: ~1,312 klein calls, blinded page, VLM compare.

**The BC discovery.** Checking the incumbent's build before the run: the prior
iron-man's `refs/{g}__BC.jpg` still carry full (bald) heads — verified visually on
`p003__BC` and `g004__BC` — so `ironman_bc_crop.py` (the head-subtraction repair,
commit a283dce) was committed but **never run**, and the 600 on-disk `__BC__` cells
are BCA4-class, consistent with v3.3 RESULTS §13's filing. Iron man 2 therefore
rebuilds BC from scratch by the flow of record: A100 bald pass (raw photo, v3.3
canvas) → **local** head subtraction (`ironman_bc_crop.py`, V2 cranium path → white)
→ A100 `bcedit` at the fal call-2 canvas (`bc_canvas="fal"`, §5's fairness rule).
Three steps because the V2 cropper's stack lives locally; the notebook carries both
sessions.

**Result: both arms complete (2026-09-08).** Session 1 `v34_ironman2_20260906_0904.zip`
(600 VEi cells, 56 bald frames, inputs); session 2 `v34_ironman2_bc_20260908_0332.zip`
(600 BC cells, 56 head-subtracted refs), run from the standalone BC notebook
`v3/colab/v34_bc.ipynb`, 2.40 s/call, $0.277. Merged into `v3/runs/v34/ironman2/`.

**The incumbent is verified built correctly this time**, three ways: `run.json` records
`bc_canvas="fal"` (the §5 fairness rule) and V2's edit prompt, not `E3`; the Colab
cropper's output was checked against the 33 references the local run of record made —
**median MAD 0.00, max 2.34** across all 33 (i.e. the two environments produce the same
head subtraction, most of them bit-identical); and the refs are head-subtracted by
inspection (100% white in the top band where the head was). The BCA4 mistake is not
repeated: this is `BC` as v3.1 defines it.

### 10.1 The head subtraction moves onto the A100 (2026-09-06)

The local V2 cropper measured **200–1,000 s per frame on CPU** (~6–8 h for 56 — the
"~45 min" estimate was wrong), so the step is ported into the Colab: the bundle now
carries `garment_crop.py`, `phase3_variants.py` and `ironman_bc_crop.py` **verbatim**
(no rewrites — the BCA4 lesson), their models self-download on Colab, and session 2's
cell 7 crops all 56 frames on the A100 and then **validates against the 33
head-subtracted refs the local run of record produced** before it was stopped
(per-stem MAD ≤ 4.0, shapes within 8 px; the run aborts on any mismatch). The BC arm
is thus single-environment (all-Colab) with a 33-ref cross-environment check.
SOLUTION §7's "local step between sessions" is corrected by this section (the
SOLUTION is not amended).

### 10.2 Iron man 2, VEi arm — the VLM readout (2026-09-07)

All 600 VEi cells scored by the judge of record ($8.71); outputs
`v3/runs/v34/judge_ironman2_vei/`. Baseline: the v3.3 lock's scores from the old
iron-man run (incomplete — 396 cells, seed 48 partial; earlier judge run, so deltas
<~0.1 are calibration noise).

**Success rate (fail proxy garment≤2 or clean≤2):** cells **70.3% pass** (178/600
fail); pairs **58.0%** clean at all three seeds, **82.5%** at ≥1 seed. Matched-cell
comparison vs the lock: VEi 28.5% cell fails vs V 23.2%; fidelity **−0.094** (VEi
3.88 vs V 3.99) — identity −0.11 and scene −0.14 carry the deficit; **garment −0.03,
inside noise**. Paired per pair: V better on 119, VEi on 62, tie 18.

**The absolute ceiling, both arms:** garment mean ≈3.0/5, modal score 3, one
garment-5 cell in 600, zero 5/5/5 fidelity cells in either arm's record — the
mediocre garment transfer is the system's ceiling on this matrix, not a VEi property.
Worst-10 classes: F3×5, F1×3, F2×2.

**New failure mode flagged — and resolved in §10.4–10.5.** The judge reported that on
some s46 cells (`g013+p006`, `g029+p012`) the output shows the garment reference's
model instead of the person. The reviewer's audit adjudicated both pairs at all three
seeds: **`g013+p006` is fine on every cell** (3/3 "wrongly flagged" — the judge
invented the swap), while **`g029+p012` genuinely fails 3/3**. So the class is real but
rarer than reported, and confined to one pair on this fold; it is inside the 55 real
failures counted in §10.5, not an additional mode on top of them.

**Reading.** VEi on the full matrix is modestly *worse* than the lock's record, at
the edge of calibration noise, on identity/scene — the failure-set gains did not
generalize into a fold-wide win over the lock. Caveats before any relock: the
baseline is incomplete and from an older judge run; the clean readouts are the
reviewer's 600-cell marks and the same-judge VEi-vs-BC comparison (session 2). The
SOLUTION lock stands or falls on iron man 2 as designed (§7); this section is the
first, cautionary half of that evidence.

### 10.3 The fail proxy is too lenient — the honest success rate (2026-09-07)

The reviewer's eye disagreed with §10.2's "70% pass", and the eye is right. The proxy
of record (garment≤2 or clean≤2) only counts a cell as failed when the garment is
**clearly wrong**; the modal score is **garment = 3** — "partially correct" — which
reads as a failure in a try-on product. Sweeping the bar, on the same scores:

| definition | VEi (600) | V (396) | BCA4 (388) |
|---|---|---|---|
| garment≤2 or clean≤2 (the proxy of record) | 29.7% | 23.2% | 21.4% |
| **garment≤3 — the garment is not clearly right** | **72.7%** | **73.5%** | **69.1%** |
| garment≤3 or clean≤3 | 75.5% | 76.0% | 74.0% |
| fidelity < 4 | 44.0% | 35.1% | 38.4% |

Garment histogram (% of cells): 1 → 1.5/1.0/1.8 · 2 → 27.5/22.0/18.3 · **3 →
43.7/50.5/49.0** · 4 → 27.2/26.5/30.9 · **5 → 0.2/0.0/0.0**.

**Two consequences.**

1. **The real success rate is ~27% of cells with the garment clearly right** (score
   ≥4), on *every* arm — v3.3's lock included. One cell in 600 has ever scored a
   garment 5. This is the number to carry into any report; "70% pass" measures only
   the absence of gross failure.
2. **The V-vs-VEi gap is threshold-dependent.** Under the lenient bar VEi looks
   6 points worse (29.7 vs 23.2); under the strict bar they are the same within noise
   (72.7 vs 73.5). The §10.2 reading — "VEi modestly worse" — holds only for
   borderline cells; on the question that matters (is the garment right) the two arms
   are indistinguishable, and BCA4 is marginally ahead of both.

**Also of record:** a **correctly built BC exists only on the 28-pair fold**
(`v3/runs/v3.0b/refs/*__BC.jpg`, 28 refs, head subtracted via the cranium path;
12 more in `v3.0a`). On the 200-pair matrix the true incumbent has never been built —
`ironman2` currently holds 600 VEi cells, 0 BC edits, and 33 local BC refs; Colab
session 2 stalled on a missing `cv2.ximgproc` (opencv-contrib) and never ran.

### 10.4 The reviewer audits the judge — it over-flags by 4× (2026-09-07)

Every one of the 178 cells the judge failed, re-judged by the reviewer on
`ironman2_failures.html` (`v34_im2_failure_audit.csv`): **fail — agree** (the call
stands) · **passable** (a real flaw, still shippable) · **wrongly flagged** (the cell
is fine).

| the reviewer's verdict on the judge's failure calls | cells | share |
|---|---|---|
| agree — genuinely failed | **42** | 23.6% |
| passable — flawed but shippable | 62 | 34.8% |
| **wrongly flagged — the judge is simply wrong** | **74** | **41.6%** |

**The judge upholds only 23.6% of its own failure calls.** Corrected rates on the 600
cells:

| bar | fail | pass |
|---|---|---|
| the judge's proxy (garment≤2 or clean≤2) | 178 · 29.7% | 70.3% |
| **product bar** (agree + passable both counted against) | **104 · 17.3%** | **82.7%** |
| **strict** (only cells the reviewer calls failures) | **42 · 7.0%** | **93.0%** |

Per pair: of the 84 pairs with any flagged cell, **36 are fully overturned** (every
flagged cell wrongly flagged) and **13 fully upheld** — those 13 are the real
failures: `g004+g005`, `g005+g009`, `g005+p002`, `g027+g029`, `g027+p011`,
`g029+p004`, `g029+p012`, `p001+p024`, `p002+p003`, `p003+p026`, `p019+p020`,
`scarlett+woman_top_denim_skirt`, and `dualuse_emma_watson+scarlett` (partial).

**What this invalidates.** Every VLM-derived number in §10.2–§10.3 — including "VEi
is modestly worse than the lock" and the ~27%-garment-correct ceiling — rests on a
judge whose failure calls are wrong 42% of the time. The judged comparisons between
arms may still hold *relatively* (the same bias applies to every arm), but the
absolute rates do not: **the honest headline is 93% of cells acceptable, 82.7% clean
of any flaw**, pending the false-negative check — which §10.5 then ran, settling the
figure at **90.8% usable / 9.2% real failures** once the 13 wrongly-passed cells are
counted in.

**Still open:** this audit covers only cells the judge *failed*. Cells it passed have
not been checked — `ironman2_passed.html` (§10.5) is that pass, and until it lands the
7.0% is a floor, not a final number.

### 10.5 The complete human verdict — all 600 VEi cells audited (2026-09-08)

Both directions of the judge's error are now measured: the reviewer re-judged all 178
cells it failed (`v34_im2_failure_audit.csv`) **and** all 422 it passed
(`im2_pass_audit.csv`). **100% of the arm is human-judged.** Ground truth per cell in
`v34_im2_truth.json`.

| the reviewer's verdict | cells | share |
|---|---|---|
| clean — ships as is | 475 | **79.2%** |
| flawed but shippable | 70 | 11.7% |
| **real failure** | **55** | **9.2%** |
| **success (clean + shippable)** | **545** | **90.8%** |

**Per pair (all 200, three seeds each):** clean at all three seeds **69.5%** · no real
failure at any seed **84.5%** · usable at ≥1 seed **96.0%** · broken at every seed
**4.0%** — the eight irreducible pairs are `g004+g005`, `g005+g009`, `g005+p002`,
`g027+g029`, `g027+p011`, `g029+p012`, `p001+p024`, `p019+p020`.

**The judge, scored against the reviewer** (failure = positive):

| | judge says fail | judge says pass |
|---|---|---|
| **really fails** | 42 | 13 |
| **really fine** | 136 | 409 |

**Precision 23.6%, recall 76.4%** — it catches three quarters of the real failures but
**over-flags by 3.2×** (178 flagged, 55 real). Its errors are overwhelmingly false
alarms, and they are not random: 62 of the 136 false alarms are cells the reviewer
calls flawed-but-shippable, i.e. the judge cannot tell "imperfect" from "unusable".

**What this settles.** The headline for v3.4 is **90.8% of cells usable, 9.2% real
failures, 96% of pairs usable at ≥1 seed** — not the 70.3% of §10.2. Every VLM-derived
absolute rate in §10.2–§10.3 is superseded by this section; the cross-arm *comparisons*
in §9.1 and §10.2 remain provisional, since the same 3.2× over-flagging applies to all
arms but has been calibrated on none of them but VEi.


## 11. The four-way verdict, and the report's examples (2026-09-08)

All four arms side by side on the 200-pair matrix at 46/47/48 — `VEi` (the v3.4
version), `BC` (the true incumbent), `V` (the v3.3 lock), `BCA4` (the incumbent as
mis-built) — reviewed on `v3/report/ironman2_fourway.html` with labelled, fixed
columns and VEi carrying its §10.5 verdict as a border. The rule of the pass: VEi is
assumed to stand; a row is voted only where VEi failed **and** another arm did better.
Votes: `v34_im2_fourway_votes.csv`.

| outcome | rows |
|---|---|
| **VEi stands** | **597 / 600** |
| another arm did better | **1** — `scarlett_backview + woman_top_denim_skirt` s48, to **BC** |
| every arm failed | 2 — `woman_top_denim_skirt + zendaya_white_blazer_skirt` s46, s48 |

**This discharges [SOLUTION §7](SOLUTION.md)** — the validation the v3.4 lock was
explicitly held against. The SOLUTION is not amended (house rule); this section is its
result of record.

**On the head-to-head that iron man 2 was built to settle: the incumbent beats the
v3.4 version on one cell in six hundred.** Not one of the 55 VEi failures was rescued
by `V` or `BCA4` either — where VEi fails, the other arms overwhelmingly fail too, which
is the same "hard pairs, not arm choice" reading links B/C reached, now on the full
matrix with the incumbent correctly built.

### 11.1 The report's examples — the cells to show for the BC-klein comparison

**These 26 cells, across 20 pairs, are the reviewer's picks for the write-up: the
figures to show when arguing v3.4 against BC klein.** Flagged with the ★ button on the
four-way page and carried in `v34_im2_fourway_votes.csv` as `report_example=yes`.
VEi's own verdict on them: 15 clean, 4 shippable, 7 failure — deliberately
mixed, so the report shows where the version wins *and* where it is honestly beaten.

| pair | cells (VEi's verdict) |
|---|---|
| `dualuse_scarlett_johansson_black_dress_backview_night+dualuse_woman_top_denim_skirt_nonceleb` | s47 (fail), s48 (fail) |
| `dualuse_woman_top_denim_skirt_nonceleb+dualuse_lp_plaid_overcoat_brown_suit` | s48 (clean) |
| `dualuse_woman_top_denim_skirt_nonceleb+dualuse_zendaya_white_blazer_skirt` | s48 (mid) |
| `g005+p002` | s47 (fail), s48 (fail) |
| `g013+p006` | s46 (clean), s48 (clean) |
| `g015+g018` | s48 (mid) |
| `g024+p010` | s47 (mid) |
| `g027+p011` | s48 (fail) |
| `g029+p004` | s47 (clean) |
| `g030+p013` | s47 (clean) |
| `p001+p002` | s47 (mid) |
| `p002+p003` | s47 (fail) |
| `p008+dualuse_emma_watson_black_blazer_armscrossed` | s46 (clean) |
| `p008+p013` | s47 (clean), s48 (clean) |
| `p012+p025` | s47 (clean) |
| `p013+p014` | s46 (clean) |
| `p015+p016` | s48 (clean) |
| `p017+p030` | s46 (clean), s47 (clean), s48 (clean) |
| `p024+p025` | s46 (clean) |
| `p028+p029` | s46 (fail) |

Whoever builds the report renders these four-up — VEi · BC · V · BCA4, with the A4
crop and each arm's reference above them, as the four-way page lays them out.

## 12. What is carried open out of v3.4 (2026-09-10)

Recorded so the next version starts from the evidence rather than the last impression.
(Failure classes F1–F5 and select-from-N are already in
[SOLUTION §4](SOLUTION.md); these are the items that surfaced after the lock.)

**1. The garment ceiling is the real target.** The canvas arc (links D–H) moved
identity, scene and realism; the garment criterion never moved — 2.5–3.1 of 5 on every
arm, every recipe, including the incumbent. The 55 real failures are overwhelmingly
garment-side (F1 the wearer's clothing survives, F2 skirt→trousers, F3 the reference
drifts under re-pose). **Nothing in the scaling family will fix them**; the person-side
agnostic (EXPERIMENT §3) and the conditional re-pose (§2) are where the value is.

**2. Is fal better than our A100? Unresolved, and the evidence leans "no".** Measured
three ways — link B (fal fails clean controls at the fold's own ~5%), link C (the A100
at new seeds does what fal did), §4.4 (blind judge: +0.09 fidelity, inside one seed's
noise) — plus the deep dive, which reproduced fal's canvas rule 20/20 and found the
paths identical on attention, dtype, steps, guidance and the schedule branch. What
stays unverifiable: what fal actually runs (its floor-32 rounding matches neither
diffusers nor BFL), whether it upsamples sub-1 MP references, its seed→noise mapping
(so **cross-backend seed pairing is meaningless**), and its VAE dtype. **The test that
would settle it** now that the judge is known to over-flag: run VEi's exact recipe on
fal over the same pairs and seeds, and audit fal's cells *by eye* on the same three-way
marks used in §10.4–10.5 — distribution against distribution, one human standard. ~$20
for the full matrix. Until that exists, "fal is a different draw" is the supported
reading, and single fal draws shown beside A100 draws are selection bias, not evidence.

**3. Calibrate the judge before trusting it again.** §10.5 gives 600 human-labelled
cells against the judge's six scores — enough to fit a threshold that reproduces the
reviewer's bar (precision is 23.6% at the current one, recall 76.4%). Doing that fit
first would let every arm be rescored consistently and cheaply; **every cross-arm VLM
number in §9.1 and §10.2 remains provisional until it is done**, because the 3.2×
over-flagging was calibrated on VEi alone.

**4. Two pairs no arm can do.** `woman_top_denim_skirt + zendaya_white_blazer_skirt`
(s46, s48) failed on all four arms (§11); the eight seed-stable failures in §10.5 are
the standing hard set. The backview-source diagnosis (§7.2 reading, `p013`-class pairs)
says some of these are **source-image problems** — a garment photographed from behind
cannot be re-posed to frontal from information that is not there — and belong at
ingestion (detect and ask for a front view), not in the renderer.
