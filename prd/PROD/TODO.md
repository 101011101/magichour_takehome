# PROD — TODO

## The brief (Runbo, 2026-09-11, word for word)

> Cool, here's what I need you to do next. I need you to first clean up the Colab as in no unnecessary code, all similar code in the same section. For example, all downloads in the same section, all inputs in the same section, etc. It should have the ability to set a max resolution which constrains the maximum dimension of either height or width and basically it should just be clean, no test code, no comments, etc. And then I need you to fill out a linear ticket with details on how to implement it. I've attached some examples here but the idea being someone that knows nothing about the script can take it and build the front end and back-end product around it. So it should answer any questions that we might want to know. For example, what is the max resolution this can go? What is the expected generation time? Things like that.

**Key points**

- **Clean the Colab.** No unnecessary code; similar code grouped into one section — all
  downloads together, all inputs together, and so on.
- **A max-resolution setting** that caps the larger of height and width.
  (Bounded by the 1 MP rule — [OPEN Q3](OPEN_QUESTIONS.md).)
- **No test code, no comments.** This overrides the terse-comment style of the research
  notebooks.
- **Fill out a Linear ticket** on how to implement it, in the format of the examples
  ([`TICKET_TEMPLATE.md`](TICKET_TEMPLATE.md)).
- **The reader knows nothing about the script** and must be able to build the front end and
  the back end from the ticket alone.
- **The ticket answers their questions in advance** — maximum resolution, expected
  generation time, and the like.

---

## How this file works

- **The ledger** has one row per inquiry Ray has raised. Status is one of **done** (answered,
  evidence in the tree), **decided** (a choice, dated and attributed), **answered — open**
  (what is known is written, something still has to run), or **open** (see
  `OPEN_QUESTIONS.md`).
- **Every closed row names its evidence** as a repo-relative path and section. A row with no
  path is not done.
- **Ticket sources** maps each field of `TICKET.md` to the row or file its value comes from,
  so the ticket can be checked without re-deriving it.
- Dates are absolute.

## The ledger

| # | inquiry | status | answer | evidence |
|---|---|---|---|---|
| 1 | Is production "BiRefNet crop → klein → BiRefNet → seed + klein"? | done | No. The bald pass runs on the uncropped photo; there is one crop, after it, and it uses four non-generative models, not BiRefNet alone | `prd/v3/v3.8/BUILD.md` §0, §1 |
| 2 | Is there a v3 document with the final solution and architecture? | done | Architecture and rationale: v3.8 SOLUTION (commit `a4fe9c1`). Build and deploy: v3.8 BUILD | `prd/v3/v3.8/SOLUTION.md`, `prd/v3/v3.8/BUILD.md` |
| 3 | Is MP size controlled? | done | Every klein canvas ≤ 2²⁰ px; the reference enters call 2 at its own size (0.40 MP mean) | BUILD §1, §4; `v3/colab/lib/klein_local.py` |
| 4 | Why does call 2 scale up **or** down to 1 MP — is that right, and where is it from? | **measured — still open** | Down is required (schedule cliff); 1.15 MP was a V3.0 constant with no rationale, retired in v3.4. v3.9 measured the up half: `NOSCALE` won **22 : 8** (p = 0.016) but that is `fail` 20 : 3 against `clean` 2 : 5, on a set 57% failures. Not enough to change the shipped rule; a fold-wide paired run would settle it. Not upscaling is ~17% faster | `prd/v3/v3.9/RESULTS.md`, `prd/v3/v3.9/EXPERIMENT.md`, `v3/testsets/inquiry_marks.csv` §3; [OPEN Q1](OPEN_QUESTIONS.md) |
| 5 | Is the seed per request, in call 2, random? | done | Yes. Call 1 fixed at 46 and cached per garment; call 2 draws `secrets.randbelow(2**31)` and returns it | BUILD §6.2 |
| 6 | What is the redraw mechanism? | decided — Ray, 2026-09-11 | The user presses fail → call 2 again at a new seed. No VLM, no automatic rejector. A failed cell passes at another seed 72% of the time | BUILD §6.2; `prd/v3/v3.8/RESULTS.md` §6 |
| 7 | Should there be one crop or two? | **done — closed 2026-09-12** | Two is no better. 84 of 93 cells same, 3 : 6 discordant (p = 0.51), **zero movement on all 40 clean cells**. Not adopted. It does make the bald pass 1.9× faster, which is a cost lever, not a quality one | `prd/v3/v3.9/RESULTS.md`, `prd/v3/v3.9/EXPERIMENT.md`, `v3/testsets/inquiry_marks.csv` §4; [OPEN Q2](OPEN_QUESTIONS.md) |
| 8 | Are the prompts and settings locked? | done | Two prompts byte for byte; 4 steps, guidance 0, bf16, CPU generator, no LoRAs, pinned revisions | BUILD §2, §4 |
| 9 | Will the numbers be stable? | done | Outputs are deterministic on fixed hardware and versions. The rate is a range: 3.00% (lenient) to ≥6.17% (strict floor), one reviewer, a mostly front-facing fold | v3.8 RESULTS §2, §3, §5 |
| 10 | Is BiRefNet small, and will it be on the GPU? | **answered — measured 2026-09-12; crop parity still open** | 44.6M params, 224 MB. It **does** run on the GPU: with `onnxruntime-gpu==1.22.0` (the newest wheel fails at `dlopen`), BiRefNet runs a 1024² input in **0.139 s vs 7.798 s on CPU — 56×**. Both notebooks now pin that wheel first and fail closed. This also confirms the v3.9 crops ran on CPU (16.8 s headcrop). Still open: the parser is untimed, the **end-to-end crop on GPU is unmeasured** (MediaPipe and the guided filter stay on CPU), and GPU-vs-CPU crop parity (T1) is unproven | `prd/v3/v3.8/BUILD.md` §3.1, §5; `prd/v3/v3.9/RESULTS.md` §6; [OPEN Q4](OPEN_QUESTIONS.md) |
| 11 | How big is klein? | done | Transformer 3.88B (7.75 GB bf16) + text encoder Qwen3-4B ≈4.0B (8.04 GB) + VAE 0.17 GB ≈ 16 GB resident. Peak VRAM not measured | BUILD §3.1; [OPEN Q5](OPEN_QUESTIONS.md) |
| 12 | Can the Photoroom transformer be used? | **decided — Ray, 2026-09-11: production uses it** | Tested in v3.8: 74 cells with known verdicts, only the transformer swapped, **no outcome changed** (median pixel difference 1.88/255, flat across groups; timing identical). Its card's license label reads `other` and points to BFL's Apache-2.0 license — a note for sign-off, not a blocker | `prd/v3/v3.8/RESULTS.md` §10; `prd/v3/v3.8/EXPERIMENT.md` link 11; `prd/v3/v3.8/SOLUTION.md` §4 post-lock note; `v3/report/v36_fp8.html`; `v3/runs/v36/fp8/`; `v3/colab/v36_fp8_set.csv` |
| 13 | Are these the models we are using? (the Photoroom transformer and BFL's two text-encoder shards) | done | Yes — all three match the pinned revisions to the byte. The list is incomplete: it also needs BFL's VAE, tokenizer, scheduler and configs, and the four small models | BUILD §3.1, §3.2 |
| 14 | Can the production package be tested? | answered — not run | T0–T5: environment, reference parity, call-2 byte parity, resources, end-to-end sweep, edge inputs | BUILD §7.3 |
| 15 | Is there anything else to build — Docker and so on? | open | Depends on whether the handoff is Colab + ticket (Runbo's brief) or we own the backend | [OPEN Q6](OPEN_QUESTIONS.md) |
| 16 | Magic Hour's klein file list — does `ER` use it, LoRAs included? | done | The transformer, text-encoder shards, VAE, scheduler and tokenizer on MH's list match BUILD §3.1 at the same revisions exactly. **`ER` runs with no LoRAs** — MH's three (RebelReal4B, RealSkin4B, ConsistenceEdit4B) are not loaded, and no v3.8 number transfers to a LoRA'd stack. MH's list lacks `model_index.json`, the transformer and text-encoder configs, and the four crop models | BUILD §3.1, §3.2, §4 rule 7; [OPEN Q8](OPEN_QUESTIONS.md) |
| 17 | Why was 1.15 MP the limit, and not 1 MP? | done | Chosen in V3.0 with no recorded rationale, as a "~1 MP" normalisation to match fal's ~832×1248 output; retired as a canvas limit in v3.4 because it admits ~4,492 tokens, over the 4,300-token schedule branch. Survives only as the input pre-bound | [OPEN Q1](OPEN_QUESTIONS.md) — "Why 1.15 MP"; commit `7c1e520`; `prd/v3/README.md` §6; `prd/v3/v3.4/RESULTS.md` §4.2; `prd/v3/v3.4/SOLUTION.md` §2, §5 |
| 18 | Which retry-clustering figures are of record? | done | The deployed report's: `BC` strict (1.61 seeds, 48% of retries meet another failure, 4.00% after one retry); `ER` 1.29 seeds, 28%, **1.71%** after one retry; 72% of `ER`'s failed cells pass at another seed. Recomputed from the CSVs | `prd/v3/v3.8/RESULTS.md` §6; `v3/report_v36/v36_report.html`; `v3/testsets/{bc2_count,er_count}.csv` |
| 19 | Has a garment photo with **no person** in it ever been tried — clothing alone, flat-lay or product shot? | **done 2026-09-12** | Yes, and it works: 10 product garments × 3 people × 2 seeds, **59 of 60 marked same** against the v3.0 no-bald route. Caveat, and it is a cost question: the head-finder fired on 10 of 10 person-free photos and the bald pass repainted 2.7–7.7% of pixels for no visible gain. `ER` has no branch on garment kind; v3.0 did | `prd/v3/v3.9/RESULTS.md`, `prd/v3/v3.9/EXPERIMENT.md`, `v3/testsets/inquiry_marks.csv` §5; [OPEN Q7](OPEN_QUESTIONS.md) |

## Ticket sources

| ticket field | value comes from |
|---|---|
| Colab | `vp/tryon_er.ipynb` (built 2026-09-11); the Colab link itself is still to be created |
| GPU | `v3/runs/v34/ironman2_bc/meta/run.json` (A100-SXM4-40GB); VRAM: T3, not run |
| Model | ledger 12, 13, 16 (the no-LoRA rule); BUILD §3.1, §3.2 |
| Modes | SKELETON §1 |
| Inputs | SKELETON §3, §4; garment photos worn: `v3/colab/matrix.csv` |
| Outputs | SKELETON §3; BUILD §6.1 |
| Generation time | v3.8 RESULTS §8 (call 2, 2.28 s median); `v3/runs/v34/ironman2/meta/timings.csv` (bald 1.48 s median); GPU crop time: unmeasured, filled by the inquiry Colab / T3 — the ticket carries GPU numbers only; cold load v3.8 RESULTS §8, `ironman2_bc/meta/run.json` |
| Resolution | `klein_local._size_fal` applied to each aspect; the 1 MP cliff, BUILD §4 rule 1; max-res setting: OPEN Q3 |
| MAX_RES | `vp/README.md` and `vp/tryon_er.ipynb` §3 (as built); [OPEN Q3](OPEN_QUESTIONS.md); default decided by Ray 2026-09-11 — blank = the full ~1 MP canvas, and 1 MP is the ceiling in general |
| Cost | v3.8 RESULTS §8 |
| Notes — redraw | ledger 6 |
| Notes — failure rate | ledger 9 |

## The work

**Deliverables (Runbo's brief)**

- [x] **Make the cleaned production Colab** — built 2026-09-11 as `vp/tryon_er.ipynb`:
      seven sections per SKELETON §5, `MAX_RES` as decided (blank = the full ~1 MP canvas),
      no comments, no test code, no LoRAs, the crop vendored inline. Verified on CPU only —
      prompts byte-identical, canvas rules matched over 5,160 sizes, the inline crop
      bit-identical to `crop_bc`. **Not yet run on a GPU**, and not yet uploaded to Colab.
- [x] **Run the inquiry-confirmation Colab and check every inquiry against its result** —
      run 2026-09-12 on an A100, 348 calls, 18.15 min, CAD 0.208, on the Photoroom
      transformer. 221 cards marked (`v3/testsets/inquiry_marks.csv`), written up in
      `prd/v3/v3.9/{RESULTS,EXPERIMENT}.md`. **Three of four inquiries closed** — scale
      (measured, not actionable), crop (closed negative), garment-only (closed). **The GPU
      inquiry produced no saved evidence and must be re-run.**

**Raised by that run**

- [ ] **Re-run the GPU inquiry, writing its verdict to a file.** The 2026-09-12 attempt
      printed to the notebook and the session was released; `headcrop` at 16.8 s median says
      the crops ran on CPU anyway. A few crops, no generation. (Q4, ledger 10)
- [ ] **Decide the product branch for garment-only photos.** v3.0 skipped the bald pass on
      product shots; `ER` balds everything, repainting 2.7–7.7% of pixels per product garment
      for no visible gain. Restoring the branch saves a call per product garment and removes
      an invention surface, at the cost of a classifier that must be right. (Q7, ledger 19)
- [ ] **Optional: the fold-wide canvas run.** `SCALE` against `NOSCALE` over all 200 pairs,
      unenriched, ideally with a second reviewer on the discordant cells — the only thing
      that would license changing the shipped canvas rule, and worth ~17% per-try-on latency.
      (Q1, ledger 4)
- [ ] **The Linear ticket** — `TICKET.md`, updated 2026-09-11: 1 MP stated as the general
      ceiling, GPU numbers only, and the per-request figures assume the garment is prepared.
      Still to fill: Colab link, GPU crop time, cold-load time from local disk, credits,
      which product it ships in, whether the existing klein script is reused.

**Measurements that fill the ticket** (BUILD §7.3)

- [ ] T0 environment · [ ] T1 reference parity, CPU and GPU crops · [ ] T2 call-2 byte parity ·
      [ ] T3 peak VRAM, per-stage time, cold load · [ ] T4 600-cell sweep on the Photoroom
      transformer · [ ] T5 edge inputs

**Housekeeping**

- [x] `prd/v3/v3.8/RESULTS.md` has no transformer-swap section — written as RESULTS §10
      (2026-09-11); SOLUTION §4, EXPERIMENT link 11 and BUILD §3.3 now cite it.
- [x] v3.8 EXPERIMENT link 9 (1.61 / 48%) and RESULTS §6 (1.53 / 41%) disagreed — they were
      two footings. RESULTS §6 now leads with the deployed report's (strict `BC`), states the
      basis, and keeps the lenient figures as secondary (2026-09-11).
- [ ] **Export the fp8 outcome marks.** `v3/report/v36_fp8.html` writes `v36_fp8.csv`; no
      such file is in the tree, so "no outcome changed" is recorded in prose only
      (RESULTS §10). Save it to `v3/testsets/v36_fp8.csv`.
- [ ] Commit `prd/v3/v3.8/BUILD.md` and `prd/PROD/` on a docs branch.
