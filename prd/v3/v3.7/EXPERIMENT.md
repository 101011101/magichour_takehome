# v3.7 — EXPERIMENT

**Status: concluded 2026-09-10 — negative, no solution.** One sub-investigation, one
behaviour: **can klein re-pose the garment's wearer to match a photograph of the target
person, handed to it as a second image in call 1?**

Post-synthesis conclusions only, per [SCHEMA.md](../SCHEMA.md). Cases, numbers and method
are in [RESULTS.md](RESULTS.md); the matrix is [TEST.md](TEST.md); shared ground is
[INVESTIGATION.md](../INVESTIGATION.md).

---

## Why this arm

Every pose-fixing arm V3 has built asks for a pose **in words**. The v3.3 lock's
`PERSON_CLAUSE` names a stance and a framing — "stands upright in a neutral pose, facing
forward, arms relaxed at the sides" — chosen by a landmark read of the crop, and klein
invents the rest. v3.5's `M1q` is the same sentence with the mannequin clause deleted.
The description is a lossy encoding of a pose, and the framing half of it is a
classification (`full_body` / `knee_up` / `waist_up` / `chest_up`) that can be wrong.

The target person's photograph is already in the pipeline — call 2 receives it as image 1.
v3.7 asks whether giving it to **call 1** as well replaces the description with an example.
If it works, `PERSON_CLAUSE` and the framing classifier both go away, and the reference
arrives at call 2 already in the pose the output has to be in.

The arm is otherwise `BC` — v3.1's incumbent — unchanged. Call 1 balds the raw garment
photo, the V2 cropper subtracts the head, call 2 is `v3lib.EDIT_PROMPT` at seed 46. One
input added to one call; nothing else moves.

The risk it takes on is stated up front, because it is what two people in one call invites:
**klein may return the target's face, body, clothing or background instead of the wearer's
garment.** That is why the reference frames, not only the finished cells, are on the page.

## The chain

### 1 — Does the pose come across, and does anything else come with it?

**What is being investigated.** Call 1 on all 51 pairs of the link C fold, in two wordings,
against `BC`'s own references and cells on the same pairs and the same seed. Hypotheses,
stated so they can fail:

| # | hypothesis | what would confirm it |
|---|---|---|
| H1 | The wearer arrives in the target's pose | `shift` > 0.5 with the output still based on image 1 |
| H2 | The framing comes across with the pose, making the classifier redundant | the output's framing class equals the target's |
| H3 | Nothing else crosses from image 2 | no garment, face or background of the target in the output |
| H4 | A failure is the model's, not one sentence's | both wordings behave the same way |

**How.** Call 1 on all 51 pairs in both wordings; the V2 crop and call 2 on a subset,
because the arm's only change is in call 1. `fal-ai/flux-2/klein/4b/distilled/edit`, seed 46.
→ [TEST.md](TEST.md). Evidence → [RESULTS.md](RESULTS.md), page `v3/report/v37.html`.

**Result.** **H1 fails, H2 fails, H3 fails, H4 confirmed.** The wearer comes back in the
source pose on most of the fold, and on roughly a third of it klein returns the *target's*
photograph with the garment swapped in — the arm's stated risk, realised. One pair of the 51
is a genuine transfer. The second image is read as a source of **clothing and scene, not of
pose**, and re-ordering the request and declaring image 2 a pose reference changes the split
by a single pair. Counts → [RESULTS §2](RESULTS.md#2-verdict)

---

## Conclusion

**Negative. No solution; no `SOLUTION.md`.** klein does not re-pose a subject to match a
reference photograph, and the way it fails makes the arm strictly worse than the incumbent
it modifies:

- Where the pose is not touched — most of the fold — the reference **is** `BC`'s reference.
  The arm has bought nothing, and it costs more than `BC` to buy it: the reference now
  depends on the target, so it cannot be amortised across the pairs that share a garment.
  → [TEST §5](TEST.md#5-budget)
- Where it collapses — about a third — the arm is **actively worse than `BC`**: call 1
  returns the target's own photograph re-dressed, so the "reference" handed to call 2 is a
  picture of the wrong person, and the garment has been re-rendered once more than it should
  be. → [RESULTS §4](RESULTS.md#4-what-the-two-failure-classes-look-like)

This closes "show klein the pose" as a way to spend call 1. The v3.3 lock's written
`PERSON_CLAUSE` stays the only mechanism that moves a pose, and the framing classifier
stays load-bearing — v3.7 does not remove it.

One result is worth carrying forward rather than discarding with the arm: the 18 collapses
are klein performing **an entire try-on in a single call**, unprompted, from a person photo
and a garment photo — in the wrong direction and uncontrolled, but in one call rather than
two. Nothing in V3 has asked for that directly. It is not this arm, and it is not evidence
that it would work if asked; it is a thing seen, recorded here so it is not seen again and
treated as new.
