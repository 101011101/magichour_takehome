# v3.14 — EXPERIMENT

**Status: open.** Runbo asked whether the four small vision models can be consolidated — with
each other or with the base model. This is the sub-investigation that answers it.

Post-synthesis conclusions only, per [SCHEMA.md](../SCHEMA.md). Per-case numbers are in
`RESULTS.md` when the run lands; the matrix is [TEST.md](TEST.md).

---

## The criterion, which is not the usual one

Runbo stated what he is optimising for: *"we don't want to reduce quality. We just want
robustness and simplicity and as much determinism as we can in this process."*

So this investigation is **not** scored on cost or latency. Every stage in question runs once
per garment and is cached; shaving a tenth of a second off a cached step is worth nothing.
It is scored on three things, in order:

1. **Quality is a veto, not a trade.** A candidate that removes a model and moves a reference
   for the worse is a rejection, however much it simplifies.
2. **Fewer branches beats fewer models.** What can go wrong is the number of ways a garment
   can be handled, not the number of weights on disk. A candidate that deletes a model but
   keeps every decision point buys little; one that collapses a fallback chain buys a lot
   even at an unchanged model count.
3. **Determinism is already true in-process, and the open question is branch frequency.** The
   four vision models have no seed and no sampling; v3.8 measured byte-identical outputs on
   the 86 cells sent identical text. What varies is *which branch an image takes*, which is
   data-dependent rather than random. A route that fires on 3% of garments is a
   rarely-exercised path, and therefore where an unnoticed bug will live.

**"Keep what we have" is a permitted outcome** and is stated as such if that is what the
numbers say. Nothing here is obliged to produce a consolidation.

## Closed before it started: consolidating into klein

Asking the generative model to produce the mask means letting it re-render the garment, and
v3.5 priced that directly — the arms that let klein redraw the garment failed **9.2%** against
the matte-based arm's **4.8%** on the same 600 cells
([v3.5 RESULTS §4](../v3.5/RESULTS.md)). That finding is the reason the current design exists.
Not reopened.

---

## The chain

### 1 — What does the selfie map still do, now that the parser supersedes it? **← established by reading the code**

`phase3_variants.masks` gives the parser priority: when `parser_classes` fires it supplies
head, garment and skin, and the selfie map's `skin` is explicitly zeroed (`skin * 0.0`). But
three uses survive, and they are the reason candidate A is not a one-line deletion:

1. the `HAIR + FACE` mask is **unioned** into the head (`np.maximum`), so the selfie map can
   only ever *add* to the head region;
2. the `CLOTHES` channel is the **collar guard** inside `parser_classes` — added because SCHP
   labels 99.1% of a raised collar on `p019` as `face`, which the pose bound does not reach;
3. both fallbacks, `head_from_pose` and `with_cranium`, take `clothes_prob` from it.

So **dropping the segmenter also strands the fallback chain.** That is the real content of
candidate A: not "one model fewer" but "one model fewer, the collar guard gone, and the
fallbacks either rewritten or deleted".

### 2 — How often is the fallback chain exercised? **← answered from the record**

The parser fired on **112 of 112** garments in one v3.5 pass and **33 of 33** in another, with
`cranium_used=True` throughout and nothing falling through
([v3.5 RESULTS](../v3.5/RESULTS.md)). The pose ellipse and the face-anchored band are
therefore close to dead code — three of the four head routes fire at approximately zero.

This cuts both ways, and the run is what decides which way matters: near-dead code is a
liability Runbo would be right to want gone, but deleting it means a garment the parser
cannot read gets **no head removed at all**, where today it degrades to a cruder route. The
one recorded case of falling through all three routes is the backview dress of v3.5 link A.

### 3 — Can the waist come from the parser instead of Pose? **← measured locally, and it fails**

ATR labels upper-clothes, dress, skirt, trousers and legs separately, so the boundary between
the upper garment and the lower one is a waist the garment itself defines — a better idea in
principle than hip landmarks, because it follows the clothing rather than the skeleton.

Measured on the archived bald frames and the product shots, before any GPU run:

- **On worn photographs it disagrees with the hip line far too often.** Both methods fire on
  51 of 56; the median disagreement is 0.054 of image height, but the 90th percentile is
  **0.222** and the worst is **0.491** — half the image.
- **The mechanism is not tuning, it is the labelling.** Every worst case is a garment the
  parser labels `dress`: a single class covering the whole body, with no lower class to bound
  against. `g015`, `g012`, `g011` and `p003` are 12–21% `dress` and essentially nothing else.
  **A dress has no waist in ATR by construction**, and dresses and coats are a large share of
  this fold.
- **On product shots it is worse than what it would replace**, which is the opposite of the
  hoped-for benefit: the parser invents a waist on **3 of 10** person-free photographs
  (`g008`, `g016`, `g026`), where Pose invents a hip on **1 of 10**.

### 4 — Would it remove Pose anyway? **← no, established by reading the code**

`parser_classes` calls `_neck_line(bgr)`, which is Pose, to bound the head's extent and to
find the nose component. So Pose is loaded and called inside the parser path regardless of
where the waist comes from. **Candidate B removes zero models**, even if its waist were good.

---

## Where this stands

Candidate B is answered and the answer is no: worse on product shots, unreliable on dresses,
and it removes no model. Candidate A is the one the GPU run is for — the question is whether
parser-only references move, and by how much, over garments whose bald frames must be
regenerated because the archive lived on a Drive that has since been cleared.
