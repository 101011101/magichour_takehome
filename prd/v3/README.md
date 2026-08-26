# V3 — one model, two calls

Opened 2026-08-23, the day [V2 was frozen](../v2/LOCK.md).

V3 is a **restart on V2's foundation**, not a continuation of it. V2 asked whether an
open-weights stack could match the closed V1 cascade and answered yes. V3 asks a
different question, and the different question is the reason for a new version rather
than a v2.5.

---

## 1. The question

> **What is the best try-on that fits in one model and two calls?**

Not "how good can this get" — V2 answered that, and the answer needed three arms, a
router, a gate and a VLM. V3 optimises a different objective, in which complexity is a
first-class cost alongside latency and price.

## 2. The constraint, and why it is the right one

Set by Runbo, for a production server:

- **One base model on the server: FLUX.2 klein 4B distilled.** Nothing else loaded.
- **Two model calls, maximum.**
- **No harness, no VLM, no escalation, no router.**

This is not a reduction of V2's ambition. It is a recognition that V2's own numbers
say most of the quality sits in one place:

| | perfect | fail |
|---|---|---|
| uncropped baseline | 53% | 34% |
| **cropped reference** | **74%** | **11%** |
| + router, gate, VLM, escalation | 82% | 0% |

**The crop is worth twenty points. Everything built on top of it is worth eight, and
costs the entire routing and gating surface.** V3 keeps the twenty and rebuilds the
eight differently.

One clarification worth holding, because it is easy to lose: **the CPU mask stack that
produces the crop is not the harness.** BiRefNet_lite, SCHP ATR, MediaPipe Selfie
Multiclass and MediaPipe Pose — ~1.9s, no GPU, no API call, all commercially licensed.
That is preprocessing, and it stays.

## 3. The starting point

**BC_klein, flat.** Two klein calls:

```
garment reference ──► klein: "make this person bald"        call 1
                       │
                       └──► CPU crop (BiRefNet · SCHP · MediaPipe · pose)
                              │
person photo ─────────────────┴──► klein: edit               call 2
                                     │
                                     ▼
                                  output
```

Measured over 38 sets: **28 perfect / 6 ok / 4 fail** at exactly 2.000 generations.
Already inside the constraint, and already the strongest single arm V2 produced.

V3's job is the four failures.

## 4. The one thing to carry over: QX's mechanism

The single most useful structural fact V2 established:

> **PHEAD and BC_klein subtract. QX regenerates. They therefore have no shared failure
> mode.** BC_klein and QX between them were usable on 100% of 38 sets, five failures
> total, **zero overlap** — every case where one fell over, the other was fine.

QX rescued **11 of PHEAD's 13 hard cases**, against BC_klein's 6, and had the lowest
failure count of any arm (20 / 17 / **1**). Its weakness is its ceiling, not its floor:
regeneration invents detail, so it wins few *perfects*. It is a floor-raiser.

The reason is mechanical. Subtraction cannot recover a garment region that hair was
covering — the pixels were never observed. Regeneration can, because it is not bound to
what was there. Jagged cut edges, the failure that no crop arm solved, are a
subtraction artefact by construction and cannot occur in a regenerated reference.

**V3's central technical problem:** get the regeneration property inside two klein
calls, on one model.

Three candidate shapes, none yet tested, in rough order of promise:

| # | shape | calls | the risk |
|---|---|---|---|
| 1 | **klein extracts the garment** instead of Qwen — `klein: "return only the clothing, plain white ground"` → `klein: edit` | 2 | klein's extraction quality is unmeasured; QX's numbers are Qwen's |
| 2 | **One prompt, bald *and* isolate** — collapse the bald pass and the extraction into a single klein call, then edit | 2 | asking one distilled 4-step call to do two edits |
| 3 | **Keep the bald pass, regenerate only the damage** — inpaint the jagged cut region rather than the whole garment | 2 | needs a damage mask; the mask stack may already provide it |

Shape 1 is the direct substitution and the obvious first experiment. Shape 3 is the
most interesting, because it targets the *actual* residual failure mechanism rather
than replacing a working step.

## 5. What to measure, and against what

**Baseline to beat: flat BC_klein at 28 / 6 / 4.** Not V2's harness — that is a
different objective and comparing against it would be measuring the wrong thing.

Same 38 sets, same reviewer protocol, same seed. The four BC_klein failures are the
scoreboard; a change that fixes two of them without losing a perfect is a win.

**Report cost and latency at ~1 MP with no upscale**, per the production framing:
current measured figures are klein at **5.3s per generation**, so flat BC_klein is
~10.6s of generation plus ~1.9s of CPU preprocessing, at roughly **$30 per 1000
images** on fal. Self-hosted numbers replace these before anything is claimed.

## 6. Inherited debts

Carried from [V2's lock list](../v2/LOCK.md#3-known-wrong-at-the-moment-of-freeze),
because they do not disappear with the harness:

- **n = 38, one reviewer, one seed, unblinded.** The test set needs to grow or the
  protocol needs to blind before any of these numbers survive contact with a customer.
- **AuraFace on CPU at 16.9s** dominates latency wherever identity is checked. If V3
  keeps any identity check, this moves to GPU first.
- **Self-hosted parity is partial.** Every figure above is a fal figure.
- **The 1 MP normalisation is not optional.** fal silently normalises to ~832×1248;
  generating at 3.45 MP self-hosted cost 32% detail and took 128s against 39s. A
  self-hosted deployment must do this explicitly or it will be slower and worse for
  reasons that do not show up in a diff.

## 7. Status

Nothing built. This document is the brief.

| | |
|---|---|
| Baseline | flat BC_klein, 28 / 6 / 4, 2.000 generations — already runnable via `tryon-v2 --hair-threshold 0` |
| General investigation | [INVESTIGATION.md](INVESTIGATION.md) — the diagnosis every sub-investigation stands on: what each of the four failures is, and why three are not artefacts. Evidence bundle `v3/artefacts/`, page `v3/report/artefacts.html` |
| Document schema | [SCHEMA.md](SCHEMA.md) — how V3's documents are laid out and what each is allowed to contain |
| First experiment | shape 1, klein-as-extractor, on the four BC_klein failures |
| Not yet decided | whether the crop's CPU stack is vendored or kept as a service |
