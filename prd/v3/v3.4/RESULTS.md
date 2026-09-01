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
