# Ticket amendments — the garment-type selector (v3.11)

For the Linear ticket, which now lives in a Google Doc. Each item names the ticket's own
section, says **REPLACE / ADD / DELETE**, and gives the exact text to paste. Written
2026-09-12 from `prd/v3/v3.11/RESULTS.md`.

> **Status.** The selector is in the production Colab `vp/tryon_er.ipynb` as of 2026-09-12 —
> the `REGION` input, the hip-line cut, the fallback and the region-naming call 2 — so the
> ticket's existing Colab link serves a script that has it. It was proven first in the trial
> notebook (`v3/colab/v311_a100.ipynb`), and the evidence level below is that trial's.

---

## Correction, 2026-09-13 — if you already pasted the fallback bullet

The v3.15 smoke test ran the production notebook end to end and found that the band fallback
was too weak: two `lower` requests crashed instead of falling back
(`prd/v3/v3.15/RESULTS.md`). The notebook is fixed. If the Google Doc already carries the
bullet beginning *"If the hip line cannot be found, or the requested half would keep less
than 2% of the garment"*, **REPLACE** it with:

```
- If the hip line cannot be found, if the requested half would keep less than 15% of the garment, or if the reference it would produce has a side under 64px (the image model's own minimum input), the request falls back to full and records which of those fired. It never guesses a cut at a fraction of the frame height. A waist-up photograph asked for lower is the case this protects: before this rule, two such requests crashed inside the image model instead of falling back
```

And **ADD** to Notes, if it is not there yet:

```
- For a product shot the region is always forced to full, since there is no waist to find. The record keeps the region the user asked for alongside the one applied, so a log explains why an upper request came back as a whole-outfit swap
```

---

## Modes

**DELETE** the whole section. Runbo: *"You don't need this modes section then because this
whole thing just has one mode."* There is one mode — virtual try-on — and the region is an
input, not a mode.

One line from it still needs saying. **ADD** it as the last line of **Inputs**, after the
bullets:

```
This does one thing: virtual try-on. Not text-to-image, not general image editing. The prompts are fixed and not exposed.
```

---

## Inputs

**ADD** as the third bullet, directly after the garment image:

```
- Region — optional, one of: full (default), upper, lower. full swaps the whole outfit. upper swaps what the person is wearing above the waist and leaves everything below it alone; lower is the mirror of that. It changes two things inside the script: the garment reference is cut at the person's hip line, and call 2 is sent a sentence naming the half. Nothing else about the request changes.
```

**ADD** after the Region bullet:

```
- Max resolution — optional integer, default 1536. Constrains the longer dimension of the output. The aspect ratio of the person photo is always preserved; this only ever lowers the result, never raises it, and it cannot lift the 1MP ceiling. Sides stay on a multiple of 32
```

**ADD** at the end of the "Handling the product should do before calling" paragraph:

```
Region applies to garment photos that have a person in them. The script checks the uploaded garment photo for a person and, finding none, prepares it the short way and treats the request as full — so a flat-lay sent as upper comes back as a whole-outfit swap rather than a bad cut. The UI can make the same check at upload time if it would rather grey the options out than silently ignore them.
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

The region does not affect size or aspect, but **max resolution** now does. **ADD** both of
these at the end of the section:

```
The region does not change any of this. The output is the person photo's own size whichever region was requested; the region changes what is swapped inside the frame, not the frame.
```

```
Max resolution caps the longer dimension, preserving the aspect ratio of the person photo. The default is 1536, which is above anything the 1MP rule produces for ordinary photographs — everything up to about 2:1 is untouched by it — and it bites only on unusually long or tall images, where the 1MP rule would otherwise return a very long thin canvas. A 3:1 panorama is 1760x576 without it and 1536x480 with it; a 4:1 is 2048x512 without it and 1536x384 with it. Lower it whenever the product wants smaller or faster output: a 3:4 photo is 864x1152 at the default, 768x1024 at 1024, and 576x768 at 768. Below the default is untested for quality — every measured number in this ticket was produced with no effective cap, and the default was chosen so that stays true.
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
- If the hip line cannot be found, if the requested half would keep less than 15% of the garment, or if the reference it would produce has a side under 64px (the image model's own minimum input), the request falls back to full and records which of those fired. It never guesses a cut at a fraction of the frame height. A waist-up photograph asked for lower is the case this protects: before this rule, two such requests crashed inside the image model instead of falling back
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
- The script tells worn photos from product shots itself, on the upload, before it generates anything. A garment with nobody in it skips the two person-side stages — it needs no wearer removed — which saves one model call per product garment, so it prepares in the crop alone (0.58s) rather than a model call plus the crop (~2.1s). The check is a head detector the crop already runs: no extra model, one more pass of something already loaded, and nothing added to per-request latency because it happens once per garment at preparation time. Measured over 56 worn garment photos and 17 flat-lay or ghost-mannequin ones, it made no error in either direction
- A product garment is always prepared as a whole outfit, whatever region was requested, and the response says so. This is also why a product shot cannot be cut at the waist: there is no wearer, and asking the model to bald one makes it invent a body, which is what an earlier draft of this ticket mistook for the detector misfiring
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
