# Test Set Plan — 30 People + 30 Garments (budget: $10)

> Scaled down from the original 120+120 plan on Aug 7, 2026: eval budget is $10.
> One pair through all 4 models ≈ $0.20–0.25, so 30 pairs ≈ $6/full run, leaving
> ~$4 for dev iterations. The 120-scale matrices are kept at the bottom for
> reference if budget ever grows; the active plan is the 30-scale below.

Sourcing brief for a team of search agents. Each agent gets assigned rows from the
matrices below, finds images on the web (Google Images / retailer sites / Unsplash /
Pexels — licensing is a non-issue for this non-commercial take-home), downloads them
into `test_set/`, and appends a row to `manifest.csv` per image.

## Active matrices — 30 people (p001–p030), 30 garments (g001–g030)

### People (30) — pose allocation

| Pose | Count |
|---|---|
| Neutral standing, arms at sides | 8 |
| **Hand-over-torso / arms crossed** (hardest case) | 7 |
| 3/4 turn or side profile | 5 |
| Sitting | 4 |
| Walking / dynamic | 3 |
| Arms raised / holding object / occlusion | 3 |

Cross-quotas over the 30: skin tone 10 light / 10 medium / 10 dark (Monk scale);
body size 10 slim / 10 average / 10 plus-or-broad; gender ~15/15;
background 15 plain / 15 cluttered; framing 20 full-body / 10 waist-up; ≥3 aged 50+.

### Garments (30)

| Category | Count | Must include |
|---|---|---|
| Tight tops | 5 | 2 graphic-logo, 1 fine-pattern |
| Loose tops | 5 | 1 graphic, 1 fine-pattern |
| Dresses | 5 | 2 printed/floral |
| Outerwear | 5 | 1 open-front |
| Lower body | 5 | 1 patterned |
| Dedicated hard cases | 5 | 2 text-heavy graphic, 2 fine stripes/plaid, 1 sheer or sequin/texture |

Photo-style quota over the 30: flat-lay 12 / ghost mannequin 10 / worn-on-model 8.

### Pairing (30 pairs, 1:1 — the eval unit)

Curated, not random: route hard garments to hard poses (striped tee → arms-crossed;
long coat → sitting). No cross-product, no swap subset at this budget — instead tag
2–3 pairs where the same garment category meets different body sizes.
Cost per full run: lineup changed after Krea 2 and Ideogram were verified unable to
do try-on via API (see NOTES.md). Current candidates: Qwen 2511 baseline (~$0.035),
FLUX.2 klein 4B edit (~$0.014), plus dedicated try-on APIs (FASHN ~$0.075, Google
Vertex $0.06, Alibaba aitryon ~$0.028) → roughly $0.05–0.21 per pair depending on
lineup ≈ **$2–6 per 30-pair run**, comfortably inside the $10 budget.

---

## Reference: original 120-scale plan (inactive)

## Directory & naming

```
test_set/
  people/     p001.jpg … p030.jpg
  garments/   g001.jpg … g030.jpg
  manifest.csv   # one row per image, columns below
  pairs.csv      # person_id, garment_id, difficulty_tags  (built after collection)
```

`manifest.csv` columns:
`id, kind (person|garment), category, pose, body_size, skin_tone, gender, background, framing, photo_style, hard_case, source_url, notes`

## Acceptance criteria (every image)

- ≥ 768px on the shortest side (prefer ≥ 1024px); resize to 1024px longest edge on save, JPEG q90.
- No watermarks or overlaid text/logos from stock sites (degrades model output — grab clean originals, not Google thumbnails: click through to the source page).
- People: exactly one person, torso-to-knees minimum visible, face visible, not heavily motion-blurred.
- Garments: single garment, front view, fully in frame, on plain/near-plain background.
- Record the real source URL in the manifest (for traceability, not legal cover).

---

## People matrix (120 total)

Primary allocation is by **pose** (the main difficulty driver). The cross-quotas
below must also hold over the whole set — agents tag every image so we can audit.

### Pose allocation

| Pose | Count | Why / notes |
|---|---|---|
| Neutral standing, arms at sides | 35 | Easy baseline; front-facing |
| **Hand-over-torso / arms crossed** | 25 | **Single hardest case** — arm occludes garment area |
| 3/4 turn or side profile | 20 | Tests garment wrap-around |
| Sitting | 15 | Garment drape + fold handling |
| Walking / dynamic | 15 | Motion, asymmetric limbs |
| Arms raised / holding object / partial occlusion (bag, phone) | 10 | Misc occlusion stress |

### Cross-quotas (must hold across the full 120)

| Dimension | Split |
|---|---|
| Skin tone (Monk scale) | light (1–3): 40 · medium (4–7): 40 · dark (8–10): 40 |
| Body size | slim: 40 · average: 40 · plus-size/broad: 40 |
| Gender presentation | ~60 women · ~60 men |
| Background | plain/studio: 60 · cluttered/outdoor/street: 60 |
| Framing | full-body: 80 · waist-up/half-body: 40 |
| Age | mostly 20–45; include ≥10 aged 50+ |

Agent search-query seeds: "street style photo full body standing", "plus size model
studio portrait", "man arms crossed casual outfit photo", "person sitting cafe candid",
site-specific: unsplash.com / pexels.com "portrait full body", lookbook/editorial pages.

## Garment matrix (120 total)

| Category | Count | Breakdown | Hard-case sub-quota within category |
|---|---|---|---|
| Tight tops | 20 | fitted tee 8 · tank/crop 4 · fitted knit 4 · athletic/bodysuit 4 | 5 graphic-logo, 4 fine-pattern |
| Loose tops | 20 | oversized hoodie 6 · flowy blouse 6 · oversized shirt/flannel 4 · sweater 4 | 3 graphic, 4 fine-pattern |
| Dresses | 20 | bodycon 5 · A-line/flowy 6 · maxi 4 · floral/printed 5 | prints count as pattern cases |
| Outerwear | 20 | denim/leather jacket 6 · blazer 5 · puffer 4 · long coat 5 | ≥4 shot open-front (layering test) |
| Lower body | 20 | jeans 6 · trousers 5 · skirts 5 · shorts/athletic 4 | ≥3 patterned (plaid skirt etc.) |
| Dedicated hard cases | 20 | text-heavy graphic tees 6 · fine stripes/plaid/houndstooth 6 · texture (cable knit, sequins, leather) 4 · sheer/asymmetric/layered 4 | all |

### Photo-style quota (across all 120 garments)

| Style | Count | Notes |
|---|---|---|
| Flat-lay | 50 | Easiest to source (retailer product pages) |
| Ghost mannequin | 40 | Standard e-commerce shots |
| Worn on model | 30 | Tests garment *extraction* — hardest input type |

Agent search-query seeds: "\<garment\> product photo white background", "\<garment\> flat lay",
retailer PDP images (Zara/H&M/Uniqlo/ASOS product pages), "graphic tee front print photo".

---

## Pairing plan (built after collection)

- **120 curated 1:1 pairs** — assign each garment to a person that makes a meaningful
  case; deliberately route hard garments to hard poses (e.g. striped fitted tee →
  arms-crossed person; long coat → sitting person). Not random.
- **Swap subset (+20 pairs)** — 5 garments each tried on 4 different body sizes,
  to test size generalization. Total ≈ 140 pairs per full eval run (~$25–45 across
  all 4 models at current fal.ai prices).
- Eval runs use `pairs.csv`; never the full 120×120 cross-product (≈ $3–5k/run,
  no added signal).

## Agent workflow

1. Each agent gets one matrix slice (e.g. "25 hand-over-torso people, hitting these
   skin-tone/body-size tags") with ID range pre-assigned (e.g. p036–p060).
2. Agent searches, downloads originals, resizes to 1024px, saves with assigned IDs,
   writes manifest rows.
3. A final audit pass checks cross-quotas actually hold and culls/replaces rejects
   (watermarks, low-res, wrong tags).
