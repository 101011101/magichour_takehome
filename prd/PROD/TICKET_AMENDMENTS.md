# Ticket amendments — the garment-type selector (v3.11)

For the Linear ticket, which now lives in a Google Doc. Each item names the ticket's own
section, says **REPLACE / ADD / DELETE**, and gives the exact text to paste. Written
2026-09-12 from `prd/v3/v3.11/RESULTS.md`.

> **Status.** The selector is in the production Colab `vp/tryon_er.ipynb` as of 2026-09-12 —
> the `REGION` input, the hip-line cut, the fallback and the region-naming call 2 — so the
> ticket's existing Colab link serves a script that has it. It was proven first in the trial
> notebook (`v3/colab/v311_a100.ipynb`), and the evidence level below is that trial's.

---

## Modes

**REPLACE** the section with:

```
Modes:
- Virtual try-on, whole outfit: a photo of a person and a photo of a garment in, the person wearing that garment out
- Virtual try-on, one half: the same, with only the upper or only the lower half of the outfit swapped and the rest of what the person is wearing left alone
Not text-to-image, and not general image editing. The prompts are fixed and not exposed.
```

---

## Inputs

**ADD** as the third bullet, directly after the garment image:

```
- Region — optional, one of: full (default), upper, lower. full swaps the whole outfit. upper swaps what the person is wearing above the waist and leaves everything below it alone; lower is the mirror of that. It changes two things inside the script: the garment reference is cut at the person's hip line, and call 2 is sent a sentence naming the half. Nothing else about the request changes.
```

**ADD** at the end of the "Handling the product should do before calling" paragraph:

```
Offer upper and lower only for garment photos with a person in them. On a flat-lay or ghost-mannequin photo the pose detector reports a hip on 6 of 10 person-free images, so a region cut there would slice at an invented row — send those as full.
```

---

## Outputs

**REPLACE** the third bullet:

```
- The prepared garment reference, an intermediate image, written to disk and cached — see Notes. There is one per garment per region, so a garment offered in all three regions has three
```

---

## Generation time (A100), per request

**No change.** A region request is the same two calls and the same latency: call 2 measured
**1.651 s naming a region against 1.659 s for the whole outfit**. The region costs nothing per
request.

**ADD** as a final bullet, so nobody assumes it does:

```
- A region request costs the same as a whole-outfit one: 1.651s against 1.659s. The difference is one sentence in the same call
```

---

## Garment preparation (once per garment, cached, off the request path)

**ADD** after the "So a new garment costs ~2.1s to prepare" bullet:

```
- If a garment is offered in more than one region, prepare them together: the bald pass does not depend on the region and one mask serves all three cuts, so all three references cost ~3.3s per garment against ~2.1s for full alone. Cutting them one at a time recomputes that mask each time and costs far more
- Cache the prepared reference under the garment AND the region. A garment prepared for full is not a reference for upper
```

---

## Resolution

**No change** — the region does not affect the output's size or aspect. **ADD** one line at the
end of the section, because the question will be asked:

```
The region does not change any of this. The output is the person photo's own size whichever region was requested; the region changes what is swapped inside the frame, not the frame.
```

---

## Cost

**No change to the per-1,000 try-on figures** — a region request is the same single call.
**ADD** to the second bullet, or as a new one:

```
- Offering a garment in all three regions raises its one-off preparation from ~2.1s to ~3.3s. At the test set's ratio that moves the all-in figure by well under a cent per 1,000 try-ons
```

---

## Notes

**ADD** these, grouped with the existing behaviour notes:

```
- What the region actually does: the garment reference is cut at the hip line, which comes from the pose detector's hip landmarks on the prepared garment frame, and call 2 is sent a sentence naming the half being replaced. Both are needed. Cutting the reference alone was tried and does not work — the model replaces the whole outfit anyway, because the instruction says to. The reference is not an instruction
- If the hip line cannot be found, or the requested half would keep less than 2% of the garment, the request falls back to full and records why. It never guesses a cut at a fraction of the frame height. A waist-up photograph asked for lower is the case this protects
- Evidence level, and it is lower than the rest of this ticket: the selector was judged by eye on 12 cells at one seed by one reviewer, on pairs that already worked. It is a feasibility result, not a rate
- The failure rates quoted in this ticket (3-6%, and 2.6% fold-wide) describe whole-outfit requests. No rate has been measured for a region request, and those figures should not be quoted for one
```

**REPLACE** the "Already set correctly in the script" bullet, so the new prompts are covered by
the same rule:

```
- Already set correctly in the script, and not tunable when porting it to the backend: all four prompts (the bald pass, the whole-outfit call 2, and the upper and lower region variants of call 2), 4 sampling steps, guidance 0.0, bfloat16, a CPU random generator for the seed, the fixed seed 46 used when preparing a garment, batch size 1, the pinned model revisions, and the 1MP ceiling. Each was measured; changing any of them invalidates the numbers in this ticket
```

**REPLACE** the "Garment photos work both ways" bullet, which the selector makes incomplete:

```
- Garment photos work both ways. Most of the measurement is on garments worn by a person, and that is the best-supported input. Product shots — flat-lay and ghost-mannequin — were tested separately on 10 garments and came out indistinguishable from a route that skips the person-side step, so they are usable for whole-outfit requests. They are not suitable for upper or lower: there is no person in them to find a waist on
```

---

## Nothing else in the ticket changes

The redraw contract, determinism, caching, the no-LoRA rule, the model list, the GPU
requirement, the 1 MP ceiling and every timing outside garment preparation are unaffected by
the selector.

## What is still open, and worth saying out loud if asked

- **Which reference arm ships.** Two were tried: cutting the band alone (arm A), and having the
  bald pass dress the unselected half in plain white first (arm B). Both work under the region
  sentence, and the trial did not rank them. **A is the cheaper default** — one bald pass and
  one mask per garment for all three regions, ~3.3 s against ~6.6 s — and its call 1 is the
  prompt of record, so every other number in the ticket still applies to it. The figures above
  are A's.
- **No region rate.** A counted sweep over the fold at `upper` and `lower`, marked the way the
  whole-outfit rate was marked, is what would produce one. ~25 minutes of GPU.
