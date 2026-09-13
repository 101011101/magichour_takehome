# v3.11 — RESULTS

Per-case detail, numbers and methodology for the garment-type selector, per
[SCHEMA.md](../SCHEMA.md). The decision this evidence supports is in
[EXPERIMENT.md](EXPERIMENT.md); the matrix and every prompt are in [TEST.md](TEST.md).

**What this document can and cannot carry.** The verdict here was reached **by eye, over 12
cells at one seed, by one reviewer**, on a page that shows the candidate arms and nothing else.
It is a feasibility result: it says the mechanism works on cells that already worked. It is
**not a rate**, and no failure rate anywhere else in v3 transfers to a region request — §6 says
what would turn it into a number.

## 1. The run

`v3/colab/v311_a100.ipynb` on an A100-SXM4-40GB, the Photoroom transformer
(`408c457f…/transformer_bf16`) with BFL's encoder, VAE and scheduler at `e7b7dc27…`:
**126 klein calls, 3.36 min, CAD 0.039** (`meta/cost_v311.json`). Outputs
`v3/runs/v311/a100/`, 108 try-ons and 48 references.

| | |
|---|---|
| cells | 12 — 6 garments × 2 full-body people, seed 46 |
| plan | 9 combinations per cell: 5 `S` + 4 `R` |
| call 1 | 18 bald passes — `A` once per garment, `B` once per garment per region |
| references | 30 — 6 garments × (A/full, A/upper, A/lower, B/upper, B/lower) |
| call 2 | 108 edits |

Every pair is one the v3.10 count marked **clean**, and every person reads `full_body` on the
framing read (`v3/colab/v311_set.csv`), so a failure here is the selector's and not a pair's.

## 2. The band, measured on all 30 references

**Nothing fell back.** The hip line was found on every one of the 6 garments, on every bald
frame, under both arms — 30 of 30 references cut at a detected joint rather than a guessed row
(`meta/v311_meta.json`, `fallback` empty throughout).

| | `upper` | `lower` |
|---|---|---|
| share of the subject kept | 36.0–58.7%, mean **44.2%** | 41.3–64.0%, mean **55.8%** |
| reference size | 0.040–0.300 MP, mean **0.126** | 0.076–0.283 MP, mean **0.188** |

`full` references average **0.411 MP**, which is the figure of record for the shipped path
(v3.8 BUILD §1 measures 0.40 MP mean over the 56 iron-man references). So the two halves
partition the subject as arithmetic says they should, and the hip row is stable between arms —
`A` and `B` agree within ~15 px on every garment, the difference being that B's frame is a
different draw of the same person.

**A half reference is a third to a half the token footprint of a whole one.** v3.4 link H found
that the reference's footprint in call 2 is what fixes proportion collapse, and `VEi` exists
because of it. Nothing in this run measured whether a 0.13 MP reference is too small for that —
it is a live risk on the smallest garments, and §6 carries it.

## 3. Link 3 — the reference alone does not deliver the outcome

The first run (78 calls, 2.2 min, CAD 0.025) varied only how the reference was built: `A` cut
the band, `B` neutralised the other half in call 1 first. Call 2 was `ER` byte for byte.

**Marked by eye, the outputs were poor under both arms.** The band cut correctly and the
references held the half they claimed — §2 — and the try-ons still failed: the unselected half
was replaced or reinvented rather than left alone. That is [TEST §9](TEST.md#9-what-would-count-as-working)'s
third bullet, named in advance as the outcome that would make a crop insufficient.

The mechanism is visible in the instruction. `ER` says:

> Replace the clothing in image 1 with the clothing in image 2.

*The clothing*, not *some of it*. A reference cannot say "only this half" on the sentence's
behalf, and no reference this project had ever sent was partial.

## 4. Link 4 — the call-2 sentence is what was missing

48 further edits (≈1.5 min, ≈CAD 0.02) added a second call-2 text over the **same references,
the same crop, the same mask and the same seed**, so an `S`/`R` pair differs by one sentence
and nothing else. `R`, for `upper`:

> Replace only the upper half of the outfit in image 1 with the clothing in image 2. Everything
> below the waist is the person's own and stays, along with their face, identity, body and the
> background.

**Verdict (Ray, 2026-09-12, on `v3/report/v311_selector.html`): it works — the selector
ships.** The page shows the candidate only: the band cut *and* a call 2 naming the half, both
reference arms, 48 outputs, with the input person and garment pinned beside them for
comparison.

**What that means precisely.** The unselected half survives under `R` where it did not under
`S`, on 12 cells at one seed, judged against the input photograph. So the selector is **a crop
plus a dynamic sentence** — the first of the two remedies TEST §9 named, and the cheaper one. It
is not a mask, and it is not v4 scope.

**The comparison is clean but the judgement is not blind.** `S` and `R` sit side by side on
`v311.html` with their arms labelled, and the reviewer knew which was which. Link 3's negative
and link 4's positive were also marked in different sittings — the failure mode v3.8 §3 measured
at 1.72× between sittings on the same 600 cells. Against that, the effect here is not a few
cells changing verdict: it is the difference between an unusable arm and a usable one, which is
larger than any drift that instrument has shown.

**`R` costs nothing.** Call 2 means **1.651 s under `R` against 1.659 s under `S`** — the same
call with a different string. There is no second model, no extra call, no mask to carry.

## 5. Arm A against arm B — not settled, and A is the cheaper default

Both arms were run under `R` and both appear on the page Ray approved. **His verdict does not
name an arm**, and this document does not invent one. What the run does establish is the cost
difference, which is not small:

| | arm A | arm B |
|---|---|---|
| call 1 | **one bald pass per garment**, 1.95 s, serves all three regions | **one per garment per region** — 1.73 s each for `upper` and `lower` |
| crop | **one mask per garment**, 1.317 s, all three bands cut off it | 0.567 s and 0.583 s, one region each |
| all three regions, per garment | **3.27 s** | ≈6.56 s (B's two, plus A's `full`) |
| call-1 prompt | `BALD_PROMPT` **byte for byte** — the prompt of record | a new prompt; **no v3.8 or v3.10 number transfers** |

B's crop *is* about twice as fast per region (0.57 s against A's 1.32 s), which is the effect
Ray predicted — a uniform white region mattes more cleanly than a patterned one. But A cuts
**three** bands from that one 1.32 s mask, so per region A is already cheaper, and B pays two
extra generative calls per garment on top.

**So A is the default unless B is visibly better**, and nothing in this run says it is. Deciding
that needs one paired look at A/`R` against B/`R` on the same page — the comparison the first
run could not make, because both arms were losing the half. Until then the selector should ship
on A, whose call 1 is the one every other number in v3 was measured on.

## 6. What this does not establish

- **No rate.** Six garments and 12 cells cannot produce a failure rate, and none is quoted. The
  v3.10 figure (2.6% fold-wide) describes a **whole-outfit** request and does not describe a
  region request.
- **One reviewer, one seed, by eye.** No blind pass, no second eye, no seed variation.
- **Only clean cells.** Every pair already worked. Nothing here says what a region request does
  to a pair that was already marginal.
- **Full-body people only.** Every person reads `full_body`. A waist-up photograph with
  `REGION=lower` has nothing below the hip to keep; §2's fallback exists for it and was never
  exercised, because the set could not exercise it.
- **The token-footprint risk of §2 is unmeasured.** A 0.13 MP `upper` reference is a third of
  what the shipped path sends.
- **Product shots are excluded by construction.** Link 1 measured why: Pose reports a hip on
  **6 of 10** flat-lay and ghost-mannequin garments that contain no person at all. A band drawn
  on those cuts at an invented row, so the selector must refuse the region on a garment-only
  photograph rather than trust the landmark.

**What would turn this into a number.** A counted sweep, the way v3.10 was counted: a region set
over the fold — every pair at `upper` and `lower` — generated under the shipping arm, marked one
image per card by a reviewer clicking failures, exported to a CSV, and reported as a rate beside
the whole-outfit rate. That is the instrument this project trusts, and it is the same cost shape
as v3.10: ~25 min and well under a dollar.

## 7. Evidence paths

| what | where |
|---|---|
| the run | `v3/runs/v311/a100/` — 108 outputs, 48 references, `meta/{v311_meta,cost_v311}.json` |
| the set | `v3/colab/v311_set.csv` — 12 cells, all clean in v3.10, all `full_body` |
| the candidate, alone | `v3/report/v311_selector.html` ← **the page the decision was made on** |
| inputs and outputs, no intermediates | `v3/report/v311_outputs.html` |
| everything, including bald frames and references | `v3/report/v311.html` |
| the band, the arms, every prompt | `v3/colab/lib/run_v311.py` |
| page builders | `v3/build/v311_page.py`, `v3/build/v311_outputs_page.py` |
| notebook | `v3/colab/v311_a100.ipynb`, bundle `v311_bundle.zip` |
