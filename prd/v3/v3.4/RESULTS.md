# v3.4 — RESULTS

**Status: open.** Evidence for [EXPERIMENT.md](EXPERIMENT.md); the matrix is [TEST.md](TEST.md).

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
| everything else | — | unchanged: A4 crop, head swap from the neck up, `PERSON_CLAUSE`, hold sentence, `E3`, seed 46 references |

Arm name **`V34`** in `run_ironman.py`. Call 1 is untouched (its ~0.5 MP crop never
crossed the branch). `BC`, when it is run beside `V34`, gets the same canvas so the
comparison stays fair — the canvas is a property of call 2, not of the arm.

**Link D as it will run.** `v3/colab/v34_a100.ipynb`, `V34` on the **failure set only**
(the reviewer's choice — a sample first), seeds **49/50/51**, the link-C seeds, so the
`Vnc` cell and the `V34` cell for the same pair and seed differ in the canvas and nothing
else. Page: `python3 v3/build/v34_a100_page.py <dir> --arm V34` puts the three side by
side — `V34` · the original scored cell · the link-C `Vnc` cell. Judge if wanted: the
same gpt-5.5 rubric as §4.4, on `V34` vs `Vnc`, is the paired number.

**What would count.** Per §4.4, the canvas should move identity/scene preservation
first; garment fidelity (F1/F2) is not expected to move. The four seed-stable pairs are
not expected to move either.

*Result: pending.*
