# Gallery — 4-way comparison set (12 grid pairs)

One row per pair, six images, ordered by filename suffix:

| Suffix | Content |
|---|---|
| `_1_person` | Input person image |
| `_2_garment` | Input garment image |
| `_3_qwen2511_raw` | Raw Qwen-Image-Edit-2511 at sane defaults (the model behind the website) |
| `_4_magichour_website` | **Magic Hour production output — downloaded straight from the Magic Hour AI Clothes Changer API** (`v1/ai_clothes_changer`), byte-identical PNG, native resolution 384x576 |
| `_5_seedream` | Our single-model implementation (seedream5_lite) |
| `_6_cascade` | Our shipped composite (seedream -> qwen_image3 realism refine) |

Inputs and our outputs are resized to <=1200px JPEG for repository size; the
Magic Hour outputs are unmodified API downloads. Full-resolution originals for
all arms live in the (gitignored) `runs/` packages and the hosted report.
