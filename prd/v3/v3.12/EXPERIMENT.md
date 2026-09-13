# v3.12 — EXPERIMENT

**Status: open.** Built 2026-09-12, not yet run. One question: **what does a region request do to
a garment photograph with no person in it?**

Post-synthesis conclusions only, per [SCHEMA.md](../SCHEMA.md). The matrix is [TEST.md](TEST.md);
when the run lands its cases and numbers go in `RESULTS.md`.

---

## Why this exists

[v3.11](../v3.11/EXPERIMENT.md) shipped the garment-type selector and, in passing, measured
something about the inputs it must refuse: **Pose reports a hip on 6 of 10 flat-lay and
ghost-mannequin photographs**, which contain no person at all. That went into the ticket as a
reason to send product shots as `full`.

Runbo read the line and asked the obvious question:

> *"So basically, this is saying that if the user uploads a flat lay ghost mannequin 4 out of 10
> times, it won't work in upper body and lower body mode?"*

It is the natural reading and it is not what the number says. **6 of 10 measures the detector, not
the outcome.** No flat-lay has ever been run through `upper` or `lower` — v3.11's set was person
photographs by construction ([v3.11 RESULTS §6](../v3.11/RESULTS.md)) — so neither group has an
outcome attached to it, and "the other 4 work" has never been tested.

What the code does with each group is not symmetrical, and the asymmetry is the point:

| the detector | the request | how it presents |
|---|---|---|
| reports a hip | the band cuts at that row, on an image with no body in it | a **silent error** — nothing in the run says anything is wrong |
| reports nothing | falls back to `full`, reason recorded (`run_v311.references`) | a **visible no-op** — the whole outfit is swapped instead of the half |

Neither returns the half the user selected. If anything the group that **fails to detect** is the
safer one, which is the opposite of the reading the number invites.

## The chain

### 1 — Does either group return the requested half? **← built, not yet run**

**How.** The ten `test_set1` product shots v3.11 measured, each at `full`, `upper` and `lower`,
against two full-body people already clean in the v3.10 count. The shipping path exactly: arm A's
call 1, the band on the mask, `ER` for `full` and the region-naming call 2 for the halves. Nothing
new is introduced — the run points the shipped thing at an input the ticket tells the product not
to send it. 70 klein calls, ≈2.5 min, ≈CAD 0.03. → [TEST.md](TEST.md)

**The instrument is a drawing.** The hip line is drawn across each photograph at the row the band
would cut, so where the cut lands can be seen rather than described. `v3/build/v312_page.py`
renders it beside the reference and the try-ons, labelled **HIP DETECTED (cut here)** or
**NO HIP — FELL BACK TO FULL**, with the counts at the top.

**What would count.** Two things, and they are separable. Whether a cut at an invented row
produces something a user would notice as broken — if it does, the silent error is at least
visible to them; if it does not, it is worse, because a plausible-looking wrong answer is harder
to catch. And whether the fallback group is as safe as the code implies.

**What cannot be concluded from it.** A rate. Ten garments and two people at one seed is a look,
not a count, and the set is deliberately the same ten v3.11 measured so the hip reads are
comparable.

---

## What this does not change

The recommendation already in the ticket — send product shots as `full` — does not depend on this
run. It follows from the detector measurement alone: a landmark on a person-free photograph is a
guess about a body the picture does not contain. This run establishes what the product should
*show a user* when it happens, and whether refusing the region outright is the right behaviour or
whether the fallback is good enough.
