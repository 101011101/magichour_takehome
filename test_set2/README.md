# Testset2 — high-res / realistic eval set (V2)

Second-generation test set: higher-resolution, more realistic images than
`test_set/` (which was normalized to 1024px — too soft for identity metrics).
Originals are kept at full resolution here; nothing is downscaled.

## Layout

```
people/      person inputs (celebrity + non-celebrity, mixed formats/res)
clothes/     garment inputs (editorial on-model looks + ts1_* product shots)
superseded/  low-res versions that have a higher-res replacement in people/
rejected/    failed quality check (watermark/cutout) — kept for reference
```

## Naming scheme

`<role>_<short description>.<ext>` where role is:

- **`dualuse_`** — an on-model photo: a person wearing an outfit. Can serve as
  the *person* input OR as the *garment source* (clothes swapping).
- **`clothesonly_`** — a product-only garment shot (flat-lay / ghost mannequin,
  no person). Garment input only.

`_nonceleb` marks the two non-celebrity memorization controls; `_LOWRES` marks
a file below the resolution bar awaiting replacement; `ts1gXXX` preserves the
test-set-1 manifest ID.

### Provenance (original filenames → current)

| Current name | Original download |
|---|---|
| people/dualuse_gal_gadot_blue_dress_redcarpet.jpg | 81ab4a38fb5848faa5c4b3c8cd7b237c.jpg |
| people/dualuse_scarlett_johansson_black_dress_backview_night.avif | gettyimages-2236824984-68d2b0b4282d0.avif |
| people/dualuse_hugh_jackman_grey_suit_outdoor.jpg | Hugh_Jackman_-_Flickr_-_Eva_Rinaldi_… (Wikimedia/Flickr, Eva Rinaldi) |
| people/dualuse_emma_watson_black_blazer_armscrossed.jpg | replacement_emma_watson.jpg (Celeste Sloman portfolio, 2500×1726) |
| people/dualuse_man_black_suit_studio_nonceleb.jpg | replacement_man_suit.jpg (Pexels 17050139, 3070×4605) |
| people/dualuse_queen_latifah_gown_stage.jpg | replacement_queen_latifah.jpg (Wikimedia, Red Sea FF 2025, 5152×7728) |
| people/dualuse_woman_top_denim_skirt_nonceleb.jpg | replacement_woman_fullbody.jpg (Pexels 4118745, 3456×5184) |
| people/dualuse_zendaya_white_blazer_skirt.jpeg | Zendaya-GQ-Australia-GettyImages-1192207539-… |
| clothes/dualuse_lp_beige_long_coat_menswear.webp | 00001-loro-piana-spring-2025-menswear-credit-brand.webp |
| clothes/dualuse_lp_navy_quarterzip_knit_LOWRES.avif | 5371CCE2-…_FAD7358_J348_MEDIUM.avif (Loro Piana, 690×966) |
| clothes/dualuse_lp_floral_kimono_set.webp | imgi_622_Loro_Piana_SS_26_Womenswear_Lookbook_015.webp |
| clothes/dualuse_lp_plaid_overcoat_brown_suit.jpg | Loro-Piana-Fall-Winter-2026-2027-Women_s-Collection_Look-1.jpg |
| clothes/dualuse_navy_peacoat_onmodel.webp | Shopify_5995_SF2_1.webp |
| clothes/clothesonly_ts1gXXX_*.jpg | test_set/garments/gXXX.jpg (see test_set/manifest.csv) |

## people/ vs clothes/ is NOT a hard division

Both folders contain people, and both contain clothes. Most `clothes/` images
are *worn* by a model (editorial lookbook shots), and every `people/` image is
someone already wearing an outfit — so any image here can, in principle, play
either role. Interspersing is expected and useful:

- a `clothes/` lookbook photo can serve as the *person* input,
- a `people/` photo can serve as the *garment source* — i.e. **clothes
  swapping**: transfer what person B is wearing onto person A (directly, via a
  garment-region crop, or via a background-removed cutout).

The folder split only records what each image was *downloaded for*, not what it
may be used as. See "Future steps" in `v2/NOTES.md` for the outfit-swap eval
plan. On-model garment images need a per-pair target-garment designation
("the coat in image 2, not the trousers") since they show full outfits.

## ts1_* files in clothes/

Product-only garment shots (flat-lay / ghost-mannequin, no person) imported
from `test_set/garments/` because Testset2 otherwise had none — they cover the
hard cases missing from the editorial set: graphic logo (g001), plaid (g008,
g023), plain baseline (g010), lower-body items (g021, g023), heavy text
(g026), fine stripes (g028). Caveat: these were normalized to **1024px max
side** in test-set-1 processing — fine as garment references, but they don't
meet this set's high-res bar. Full provenance/tags: `test_set/manifest.csv`.

## Known caveats

- Celebrity faces (Zendaya, Hugh Jackman, Queen Latifah, Emma Watson, Gal
  Gadot, Scarlett Johansson) make identity degradation easy to eyeball, but
  models may have memorized them — identity-preservation scores can be
  inflated. The two `_nonceleb` files are the controls for exactly this.
- The Scarlett Johansson shot is a back view (extreme case by design).
- Formats are mixed (jpg/webp/avif); AVIF needs a PIL plugin — normalize to
  JPEG before wiring into the notebook.
- `clothes/dualuse_lp_navy_quarterzip_knit_LOWRES.avif` is 690×966 and still
  needs a higher-res replacement — loropiana.com blocks non-browser fetches at
  the IP level (Akamai), so grab it manually: product code FAD7358 (also listed
  on Cettire), then replace the `_LOWRES` file.
