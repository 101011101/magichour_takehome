# Prompt — Virtual Try-On Colab

**Context (updated 2026-08-13):** This started as a take-home assessment for a Magic Hour
internship. The internship is now secured, and this is **no longer a take-home** — the
project is being built into something **deployable into company code**.
**Ray** (me) is building it; **Runbo** originally gave the prompt.

**Constraint: open weights only.** The production version must use open-weights models
(self-hostable) — no proprietary hosted APIs (fal, Ideogram, Krea, etc.) in the deployed path.

> **See also:** [references/REFERENCES.md](references/REFERENCES.md) — synthesis of the two
> reference notebooks (Krea 2 identity edit, MagicHourOptimize/Ideogram 4) and what
> to reuse from each. The notebooks themselves live in [references/](references/).

## Original request (from Runbo's message to Ray)

> Hi Ray, sure — can you put together a Colab that does virtual try-on (so takes
> an image of a person + image of an outfit, and makes that person wear that
> outfit), and does it better than the one on our website?
>
> Our website used **Qwen 2511**, but newer models have come out — e.g.
> **Krea 2**, **Ideogram**, **Flux 2 Klein** — that are superior.
>
> Reference colabs:
> - Krea 2: https://colab.research.google.com/drive/1CN90_dUu485gCs40mtWBWWSvM8ZuYDqQ
> - Ideogram: https://colab.research.google.com/drive/1oPrJqJJOhIy8kNW620CcEt4zdA1oux8O?usp=sharing
>
> If you need compute let me know and I'll give you a card. Save this as a prompt md as well.

## What "done" looks like

A Google Colab notebook that:
1. Takes two inputs — a **person image** and an **outfit/garment image**.
2. Produces the person **wearing that outfit**, with identity + pose preserved
   and the garment faithfully transferred.
3. Demonstrably **beats the current website output** (Qwen 2511) on a shared set
   of test pairs — side-by-side comparison included.

## Constraints & open questions

> Note: the sections below reflect the original take-home framing. For the production
> version, the open-weights-only constraint above supersedes any API-based options
> (Ideogram, Krea) — those were evaluation-only.

- **Models to evaluate:** Krea 2, Ideogram (3.0?), Flux 2 Klein — vs. baseline Qwen 2511.
  Need to confirm exact model IDs/versions and whether they're API-based
  (Ideogram, Krea) or open-weights runnable on Colab GPU (Flux).
- **Compute:** Ray offered a card (API credits). Determine per-model:
  hosted API vs. self-hosted weights on Colab (T4/A100).
- **Success metric:** "better" is subjective — need a rubric (garment fidelity,
  identity preservation, pose/background consistency, artifact-free) and ideally
  a small human/LLM-judge eval on N pairs.
