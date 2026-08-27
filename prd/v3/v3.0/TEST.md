# v3.0 — TEST

**Status: run A complete and unmarked; run B specified.** The matrices for v3.0's
generation runs. This document exists so that every arm sees exactly the same pairs, and
so a later run can be compared to an earlier one without arguing about what was in the
set.

Both runs are kept. Run A is not withdrawn — it is 72 paid outputs on disk, and the
`clothesonly` product references in it are the only product-shot evidence V3 has.

| | run A | **run B** |
|---|---|---|
| source set | `test_set2/` | **`test_set3/`** |
| shape | 12 garment references × 3 people | **56 images folded in half** |
| pairs | 36 | **28** |
| generations | 72 | **56** |
| matrix of record | [`v30_matrix_a.csv`](../../../v3/testsets/v30_matrix_a.csv) | [`v30_matrix_b.csv`](../../../v3/testsets/v30_matrix_b.csv) |
| outputs | `v3/runs/v3.0a/` | `v3/runs/v3.0b/` |
| review page | `v3/report/v30a_review.html` | `v3/report/v30b_review.html` |

**Edit the generator, never the CSV or the tables below.** Run B's generator is
[`v3/build/make_matrix_b.py`](../../../v3/build/make_matrix_b.py); the run itself is
`python3 v3/build/run_v30.py --run b`.

---

## 1. Run B — the fold

`test_set3` is **56 on-model photographs**, every one of which contains a person wearing
an outfit and can therefore take either side of a pairing. The list is folded at its
midpoint: **item *i* is the person, item *i* + 28 is the garment source.**

**28 pairs. Every image used exactly once. Nothing left over.**

That property is the point. A garment-driven design like run A's asks *does this
reference fail for everyone*, and answers it well, but it can only cover 12 references.
A fold asks *where does the arm fail across the whole set* and touches all 56 images for
the same money. The two designs answer different questions and neither replaces the
other.

### Why the fold falls where it does

Order is manifest order, which is build order and therefore fixed: test_set1 people (30)
→ test_set2 people (8) → test_set2 on-model (5) → test_set1 on-model garments (13).

The midpoint lands so that **`p001`–`p028` are the person inputs** and everything
editorial — the celebrities, the lookbook shots, the on-model garment photography — is
on the garment side. That is the useful orientation, and it is a **consequence of the
order rather than a thumb on the scale**. It is written down here so it is not mistaken
for one.

| side | composition |
|---|---|
| person input | 28 × `test_set1` people |
| garment source | 13 × ts1 on-model garments, 8 × ts2 people, 5 × ts2 on-model, 2 × ts1 people |

### What the set does and does not cover

**Covers.** Every image in `test_set3`. Hard cases inherited from test-set-1 on the
garment side: `fine_pattern` ×3, `graphic_logo` ×1, `graphic_text` ×1, `open_front` ×1,
`texture_sheer` ×1.

**Does not cover.** Product-only references — flat-lay and ghost mannequin. They are
excluded from `test_set3` because they can only ever be the garment, which makes the pool
asymmetric and a fold impossible to state cleanly. **Run A is where the product-shot
evidence lives**, including the plain ghost tee that replicates QX's invention failure.
If run B says something about product references, it is saying it without data.

**One pairing per image.** A fold gives coverage, not repetition. It cannot separate
*this garment fails* from *this pairing failed* the way run A's three-people-per-reference
design can. Where run B flags something, the follow-up is to re-pair that reference
against two more people.

### Two references where the bald pass is a no-op

`dualuse_lp_plaid_overcoat_brown_suit` and `g015` show **no hair in frame** — cropped at
the neck. BC_klein's call 1 has nothing to remove on those two, so it is a wasted
generation, and they are the run's cheapest test of
[EXPERIMENT link 3](EXPERIMENT.md#3-is-the-bald-pass-net-negative-where-hair-damage-is-low):
if BC underperforms QX on exactly these two, the bald pass is costing something where it
cannot pay.

The signal behind that call is a coarse 256×256 whole-frame area fraction recorded in
`test_set3/manifest.csv`. **It ranks references; it does not classify them.** V2's eight
failed head-detection heuristics are the reason for saying so.

## 2. Run conditions — identical to run A, so the two are comparable

| | |
|---|---|
| model | `fal-ai/flux-2/klein/4b/distilled/edit`, 4 steps, guidance 1.0 (both fixed by the checkpoint — [INVESTIGATION.md §3.3](../INVESTIGATION.md#33-the-no-op-is-a-named-failure-mode-and-4-steps-is-why)) |
| seed | **46**, the V2 AMT seed, so anything generated here is comparable to `v2/runs/amt/gen/` |
| resolution | inputs normalised to ≤1.15 MP; fal normalises output to ~832×1248 |
| prompt | the V2 AMT prompt verbatim: *"Dress the person in image 1 in the clothing shown in image 2. Keep the person's face, identity, body and the background exactly as they are."* |
| BC_klein arm | klein bald pass on the reference → CPU crop → klein edit |
| QX arm | Qwen-Image-Edit-2511 extraction, prompt `p1` → klein edit |
| not varied | prompt wording, seed, resolution, steps, guidance, crop parameters. Anything that moves is recorded as a deviation |

**Budget for run B.** 28 bald + 56 edits = **84 klein calls at $0.015 = $1.26**, plus 28
Qwen extractions. Every reference is worn, so unlike run A there is no reference that
skips the bald pass — including the two where it has nothing to do, which are being run
deliberately rather than optimised away.

## 3. Review protocol

Same ternary as V2, so the numbers join the existing record: **perfect** = ship
unchanged, **ok** = acceptable but improvable, **fail** = unusable. Alongside the tier,
record **which band** each non-perfect output falls in — over-attention, questionable
attention, or failed attention — because the run is for finding the *conditions* of each
band, not the rate.

**Stated deviations from the protocol this document asked for:**

1. **Not blinded.** The review page labels the arm. 56 cells is small enough to shuffle,
   but marking twice costs more than the blinding buys when the goal is to locate failure
   conditions rather than publish a rate. Anywhere a rate from this run is quoted, it is
   quoted as unblinded.
2. **One reviewer, one seed.** Carried from V2 and not fixed here.

---

## 4. Run B matrix
| # | person input | garment source | source of garment | category | hard case | bald pass |
|---|---|---|---|---|---|---|
| 1 | `p001` | `p029` | ts1 people | person | — | yes |
| 2 | `p002` | `p030` | ts1 people | person | — | yes |
| 3 | `p003` | `dualuse_emma_watson_black_blazer_armscrossed` | ts2 people | — | — | yes |
| 4 | `p004` | `dualuse_gal_gadot_blue_dress_redcarpet` | ts2 people | — | — | yes |
| 5 | `p005` | `dualuse_hugh_jackman_grey_suit_outdoor` | ts2 people | — | — | yes |
| 6 | `p006` | `dualuse_man_black_suit_studio_nonceleb` | ts2 people | — | — | yes |
| 7 | `p007` | `dualuse_queen_latifah_gown_stage` | ts2 people | — | — | yes |
| 8 | `p008` | `dualuse_scarlett_johansson_black_dress_backview_night` | ts2 people | — | — | yes |
| 9 | `p009` | `dualuse_woman_top_denim_skirt_nonceleb` | ts2 people | — | — | yes |
| 10 | `p010` | `dualuse_zendaya_white_blazer_skirt` | ts2 people | — | — | yes |
| 11 | `p011` | `dualuse_lp_beige_long_coat_menswear` | ts2 on-model | — | — | yes |
| 12 | `p012` | `dualuse_lp_floral_kimono_set` | ts2 on-model | — | — | yes |
| 13 | `p013` | `dualuse_lp_navy_quarterzip_knit_LOWRES` | ts2 on-model | — | — | yes |
| 14 | `p014` | `dualuse_lp_plaid_overcoat_brown_suit` | ts2 on-model | — | — | **no-op** |
| 15 | `p015` | `dualuse_navy_peacoat_onmodel` | ts2 on-model | — | — | yes |
| 16 | `p016` | `g004` | ts1 on-model | tight_top | — | yes |
| 17 | `p017` | `g005` | ts1 on-model | tight_top | graphic_logo | yes |
| 18 | `p018` | `g009` | ts1 on-model | loose_top | — | yes |
| 19 | `p019` | `g011` | ts1 on-model | dress | — | yes |
| 20 | `p020` | `g012` | ts1 on-model | dress | fine_pattern | yes |
| 21 | `p021` | `g013` | ts1 on-model | dress | fine_pattern | yes |
| 22 | `p022` | `g014` | ts1 on-model | dress | — | yes |
| 23 | `p023` | `g015` | ts1 on-model | dress | — | **no-op** |
| 24 | `p024` | `g018` | ts1 on-model | outerwear | open_front | yes |
| 25 | `p025` | `g024` | ts1 on-model | lower_body | — | yes |
| 26 | `p026` | `g027` | ts1 on-model | hard_case | graphic_text | yes |
| 27 | `p027` | `g029` | ts1 on-model | hard_case | fine_pattern | yes |
| 28 | `p028` | `g030` | ts1 on-model | hard_case | texture_sheer | yes |
---

## 5. Run A matrix — 12 references × 3 people (complete, unmarked)

**`dualuse_lp_floral_kimono_set`** — worn, stresses **BC** · dense floral on a loose editorial drape; the V2 kimono reference  
`test_set2/clothes/dualuse_lp_floral_kimono_set.webp`

| person input | hair | tone | view |
|---|---|---|---|
| `dualuse_emma_watson_black_blazer_armscrossed` | long | light | frontal |
| `dualuse_hugh_jackman_grey_suit_outdoor` | short | light | frontal |
| `dualuse_woman_top_denim_skirt_nonceleb` | long | light | frontal |

**`dualuse_navy_peacoat_onmodel`** — worn, stresses **BC** · high stand collar - the head cut lands on the garment itself  
`test_set2/clothes/dualuse_navy_peacoat_onmodel.webp`

| person input | hair | tone | view |
|---|---|---|---|
| `dualuse_queen_latifah_gown_stage` | long | deep | frontal |
| `dualuse_man_black_suit_studio_nonceleb` | short | medium | frontal |
| `dualuse_zendaya_white_blazer_skirt` | long | medium | frontal |

**`dualuse_lp_plaid_overcoat_brown_suit`** — worn, stresses **both** · plaid and a collar together: BC cut-line and QX smoothing in one reference  
`test_set2/clothes/dualuse_lp_plaid_overcoat_brown_suit.jpg`

| person input | hair | tone | view |
|---|---|---|---|
| `dualuse_gal_gadot_blue_dress_redcarpet` | long | light | frontal |
| `dualuse_scarlett_johansson_black_dress_backview_night` | long | light | back |
| `dualuse_emma_watson_black_blazer_armscrossed` | long | light | frontal |

**`dualuse_lp_beige_long_coat_menswear`** — worn, stresses **BC** · beige against skin - the low-amplitude boundary case  
`test_set2/clothes/dualuse_lp_beige_long_coat_menswear.webp`

| person input | hair | tone | view |
|---|---|---|---|
| `dualuse_hugh_jackman_grey_suit_outdoor` | short | light | frontal |
| `dualuse_woman_top_denim_skirt_nonceleb` | long | light | frontal |
| `dualuse_queen_latifah_gown_stage` | long | deep | frontal |

**`dualuse_zendaya_white_blazer_skirt`** — worn, stresses **BC** · long hair over a white garment on a light ground  
`test_set2/people/dualuse_zendaya_white_blazer_skirt.jpeg`

| person input | hair | tone | view |
|---|---|---|---|
| `dualuse_man_black_suit_studio_nonceleb` | short | medium | frontal |
| `dualuse_gal_gadot_blue_dress_redcarpet` | long | light | frontal |
| `dualuse_scarlett_johansson_black_dress_backview_night` | long | light | back |

**`dualuse_queen_latifah_gown_stage`** — worn, stresses **BC** · long hair, stage lighting, gown drape  
`test_set2/people/dualuse_queen_latifah_gown_stage.jpg`

| person input | hair | tone | view |
|---|---|---|---|
| `dualuse_emma_watson_black_blazer_armscrossed` | long | light | frontal |
| `dualuse_hugh_jackman_grey_suit_outdoor` | short | light | frontal |
| `dualuse_woman_top_denim_skirt_nonceleb` | long | light | frontal |

**`dualuse_scarlett_johansson_black_dress_backview_night`** — worn, stresses **QX** · back view - view-dependent information a regenerated front cannot hold  
`test_set2/people/dualuse_scarlett_johansson_black_dress_backview_night.avif`

| person input | hair | tone | view |
|---|---|---|---|
| `dualuse_queen_latifah_gown_stage` | long | deep | frontal |
| `dualuse_man_black_suit_studio_nonceleb` | short | medium | frontal |
| `dualuse_zendaya_white_blazer_skirt` | long | medium | frontal |

**`clothesonly_ts1g010_plain_tee_ghost`** — product, stresses **QX** · plain: nothing to extract and everything to invent  
`test_set2/clothes/clothesonly_ts1g010_plain_tee_ghost.jpg`

| person input | hair | tone | view |
|---|---|---|---|
| `dualuse_gal_gadot_blue_dress_redcarpet` | long | light | frontal |
| `dualuse_scarlett_johansson_black_dress_backview_night` | long | light | back |
| `dualuse_emma_watson_black_blazer_armscrossed` | long | light | frontal |

**`clothesonly_ts1g026_metallica_text_tee_flat`** — product, stresses **QX** · heavy text - regeneration mangles glyphs  
`test_set2/clothes/clothesonly_ts1g026_metallica_text_tee_flat.jpg`

| person input | hair | tone | view |
|---|---|---|---|
| `dualuse_hugh_jackman_grey_suit_outdoor` | short | light | frontal |
| `dualuse_woman_top_denim_skirt_nonceleb` | long | light | frontal |
| `dualuse_queen_latifah_gown_stage` | long | deep | frontal |

**`clothesonly_ts1g028_fine_stripe_shirt_ghost`** — product, stresses **QX** · fine stripes - the smoothing case  
`test_set2/clothes/clothesonly_ts1g028_fine_stripe_shirt_ghost.jpg`

| person input | hair | tone | view |
|---|---|---|---|
| `dualuse_man_black_suit_studio_nonceleb` | short | medium | frontal |
| `dualuse_zendaya_white_blazer_skirt` | long | medium | frontal |
| `dualuse_gal_gadot_blue_dress_redcarpet` | long | light | frontal |

**`clothesonly_ts1g001_graphic_logo_tee`** — product, stresses **QX** · a logo mark: destroyed or invented  
`test_set2/clothes/clothesonly_ts1g001_graphic_logo_tee.jpg`

| person input | hair | tone | view |
|---|---|---|---|
| `dualuse_scarlett_johansson_black_dress_backview_night` | long | light | back |
| `dualuse_emma_watson_black_blazer_armscrossed` | long | light | frontal |
| `dualuse_hugh_jackman_grey_suit_outdoor` | short | light | frontal |

**`clothesonly_ts1g008_plaid_flannel`** — product, stresses **QX** · dense plaid without a wearer, so the crop is not a variable  
`test_set2/clothes/clothesonly_ts1g008_plaid_flannel.jpg`

| person input | hair | tone | view |
|---|---|---|---|
| `dualuse_woman_top_denim_skirt_nonceleb` | long | light | frontal |
| `dualuse_queen_latifah_gown_stage` | long | deep | frontal |
| `dualuse_man_black_suit_studio_nonceleb` | short | medium | frontal |