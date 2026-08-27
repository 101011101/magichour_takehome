# test_set3

Assembled 2026-08-26 from `test_set1/` and `test_set2/` by
[`v3/build/make_testset3.py`](../v3/build/make_testset3.py). Of record:
[`manifest.csv`](manifest.csv). Gallery: `v3/report/testset3.html`.

## One pool

**56 on-model photographs.** Every image contains a person wearing an outfit, so every
image can be the person input *or* the garment source, and a pairing is only a choice of
which side each one takes.

Product-only shots — flat-lay and ghost mannequin — are excluded. They can only ever be
the garment, which makes the pool asymmetric and a fold impossible to state cleanly.

| from | n | rule |
|---|---|---|
| `test_set1/people` | 30 | all people |
| `test_set1/garments` | 13 | only those tagged `photo_style = on_model` |
| `test_set2/people` | 8 | all on-model |
| `test_set2/clothes` | 5 | only the `dualuse_` files, which have a wearer |

**Excluded:** the 17 `test_set1/garments` tagged `flat_lay` or `ghost_mannequin`, and the
seven `clothesonly_` files in `test_set2` that are byte-identical copies of them.

**The tags were checked, not trusted.** All 13 `on_model` images show a person and all 17
excluded show none, verified against the images before the filter was applied.

**Symlinks, not copies and not moves.** Every entry in `people/` is a relative symlink
into `test_set1/` or `test_set2/`. The source sets are cited by runs already paid for, so
they cannot be emptied; and copying would have duplicated ~20 MB of images that already
exist two directories away. **test_set3 is a view — a selection plus a manifest — not a
third pile of JPEGs.** It is 16 KB on disk.

The one cost: an archive of this repo that does not follow symlinks will get a
`test_set3/` full of dangling links. Rebuild it with the generator.

## Metadata

`manifest.csv` carries test-set-1's tags where they exist: `pose`, `body_size`,
`skin_tone`, `gender`, `framing`, `photo_style`, `category`, `hard_case`. The 13 images
originating in `test_set2` have none, because that set was never tagged. The gallery
marks them *no metadata* rather than leaving the gap silent.

Hard cases inherited from test-set-1, over the images that survived the filter:
`hand_over_torso` ×7, `fine_pattern` ×3, `graphic_logo` ×1, `graphic_text` ×1,
`open_front` ×1, `texture_sheer` ×1.

### `hair_frac` and `face_frac`

Coarse whole-frame area fractions from the 256×256 selfie multiclass map, computed at
build time. They are recorded because **hair in frame is the variable that decides
whether BC_klein's bald pass has anything to do** — several on-model garment shots are
cropped at the neck, and a reference with no hair cannot have hair removed from it.

Six images show no hair: `p006`, `p011`, `p013`, `p015`, `g015`, and
`dualuse_lp_plaid_overcoat_brown_suit`.

**This is a raw signal, not a verdict.** The map is 256×256 and the fractions are of the
whole frame, so they rank references rather than classify them. V2's history with
head-detection heuristics is the reason for saying so out loud.

## Naming

The three sets are `test_set1/`, `test_set2/`, `test_set3/`. `test_set/` and `Testset2/`
survive as symlinks to the first two so that frozen V2 code, its published HTML and its
evidence CSVs — about 1,400 path references — keep resolving without the frozen record
being rewritten. **New work should use the numbered names.**
