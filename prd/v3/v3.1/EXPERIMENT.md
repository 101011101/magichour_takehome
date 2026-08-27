# v3.1 — EXPERIMENT

**Status: open.** One question:

> **How far does a ghost-mannequin reference get?**

[v3.0](../v3.0/EXPERIMENT.md) established that klein reproduces whatever the reference's
boundary contains, and that a regenerated reference has no boundary to reproduce. v3.1
takes the regeneration branch seriously and asks what the regenerated reference should
*look like* — specifically, whether a mannequin that keeps the drape beats a garment
floating isolated on white.

Post-synthesis conclusions only, per [SCHEMA.md](../SCHEMA.md). Cases, numbers and
per-reference evidence are in [RESULTS.md](RESULTS.md).

---

## The chain

### 1 — What wording actually gets the whole outfit out of a photograph? **← landed**

**How.** Eight prompts, judged by eye, first on a four-reference probe set and then over
all 28. → [RESULTS §1](RESULTS.md#1-the-prompt-p7-is-the-one)

**Result.** **`p7` is the prompt.** It is the only one of eight that returns the complete
outfit with nothing invented and no head.

The route there is the finding, not the destination. Each version fixed one thing and
broke another, and every breakage was **the model doing exactly what it was told**:

- `p1`/`p2` say *"the garment"*, **singular** — so pieces get dropped. `g018` came back as
  a blazer with no trousers.
- `p4`/`p5` name the accessory slots to include — so those slots get **generated**. Every
  reference came back wearing a hat that exists in no photograph.
- `p6` says *"from head to feet"* — so **the head arrives**, as a floating wig.
- `p8` says *"side by side"* — so pieces are **duplicated** as variants.

Two rules generalise out of that and are worth carrying to any prompt work in V3:

1. **Naming a slot fills it.** An enumerated list is an instruction to produce, not a
   checklist to satisfy.
2. **A concrete negative constrains where an abstract one does not.** What holds the
   invention down in `p7` is not "do not add anything" but *"if they are not carrying a
   bag, there is no bag."*

**Next:** does the better reference make a better try-on?

### 2 — `p7` through klein, against the two incumbents **← current**

**How.** 28 `p7` extractions, then 28 klein edits, on the [run-B fold](../v3.0/TEST.md).
All three arms end in the **same klein call, same seed, same prompt**, so the reference
image is the only variable. Side by side on `v3/report/v31_arms_vs.html`.

**Result.** Generated, 28/28, no failures. **Not yet scored.** What is visible without
scoring:

- **`p7` is the only reference of the three that carries footwear**, so it is the only arm
  that can transfer shoes. Whether that is *wanted* is a product decision rather than a
  quality one, and it should be marked as its own category.
- **On single-garment references the three arms are indistinguishable.** The mannequin
  shape costs the same two calls and buys nothing there.

### 3 — Three defects that have to be fixed before scoring means anything **← open**

Raised on review and checked against the frames
([RESULTS §3b](RESULTS.md#3b-three-defects-in-the-p7-mannequin-from-review)). Taken
together they say something specific: **`p7` solved the wording problem and did not solve
the representation problem.** Each defect is the reference being asked for something the
photograph does not support.

| | defect | why it happens | direction |
|---|---|---|---|
| **A** | the mannequin is the **same value as the garment** — white form, white shirt — and the garment loses its outline | the form defaults to white; nothing guarantees contrast with what it wears | derive the mannequin colour instead of defaulting it |
| **B** | the mannequin **invents clothing** the photograph does not contain — a waist-up shot comes back with trousers | `p7` says *"from head to feet"*, which asks for a whole body a waist-up photograph cannot supply | make the mannequin match the **framing** of its source |
| **C** | **feet and limb terminations come back blank** or malformed | the model renders a region it had no evidence for and does not resolve it | may follow from B; test after B rather than before |

**A is the same failure V2 already paid for.** A white garment on a white mannequin is a
low-amplitude boundary, and
[§3.4](../INVESTIGATION.md#34-why-p023-specifically-amplitude-not-contrast) says a
low-amplitude boundary does not exist as a signal at the timesteps where layout is
decided. `HD_p023` no-opped because a nude garment sat on bare skin. **We have rebuilt
that condition on purpose, inside a reference we control** — which also means we can
simply stop doing it.

The proposed direction is to compute a mannequin colour on CPU from the **target person's
skin tone** and specify it in the prompt. Two things it would buy at once: the mannequin
stays plausible as a body, and the garment is guaranteed an edge to be found at. It is
worth being honest that this is **not yet designed** — the failure case is a garment that
happens to match the person's skin tone, which is precisely `HD_p023`, so "use the
person's skin tone" cannot be the whole rule. Contrast with the *garment* is the property
that matters; the person's tone is one way to choose a plausible one. **To be designed in
conversation, then written here before it is built.**

**B is a prompt fix and should be tried first**, because it is free and it is the same
lesson as link 1: the prompt asked for something that was not there, and got it. If the
source is waist-up, the mannequin should be waist-up. test-set-1's manifest already tags
`framing`, so for tagged references the condition is known without inference — though 26
of the 28 are untagged, so a CPU check would be needed for the rest.

**C is deliberately not given its own fix yet.** Inventing what is absent (B) and failing
to render what was invented (C) are different faults, and B may remove the condition that
produces C. Testing them separately costs a run; testing B first costs nothing extra.

### 3.1 — framing: `p7.1` **← landed**

**How.** Three arms over 8 references carrying the defect. `.1` and `.2` are pure prompt —
the model is told to limit itself. `.3` reads MediaPipe pose landmarks on CPU (36 ms) and
**injects the extent it found**, so the model is told the answer rather than asked to work
it out. → [RESULTS §3c.2](RESULTS.md#3c2-p713-the-cpu-framing-reader-works)

**Result.** **`p7.1.3` wins.** Reviewer verdict on the clean re-run: the garment is
maintained and the mannequin stops where the photograph stops —
`dualuse_man_black_suit_studio_nonceleb` and `g024` cited. **Reading the framing and
telling the model beats asking the model to limit itself.**

That is worth stating as a rule, because it is the opposite of link 1's lesson and both
are true: **tell the model what is there, do not tell it what to omit.** `p4`/`p5` failed
by naming things to include that were absent, and got them invented. `p7.1.3` succeeds by
naming what *is* present. The distinction is whether the instruction is grounded in the
image.

The standing risk is stated rather than designed away: **a CPU reader that is wrong makes
the prompt confidently wrong.** The pose reader's verdict is printed above every row on
the page so that failure is visible rather than silent. One disagreement is already
open — `p029` is tagged `waist_up` in test-set-1's manifest and the reader calls it
`chest_up`; neither has been adjudicated.

**A defect in the first pass, and what it cost.** All 24 p7.1 frames in the first run were
generated with `"on a mannequin mannequin"` — the colour slot was fed the literal noun and
the suffix already supplies it. Found by printing the prompts as sent, not by inspecting
frames. It left `.1` vs `.2` vs `.3` sound, since all three carried it equally, but
confounded any comparison against the `p7` baseline. **The builder is fixed and all 24
were re-run**; the defective frames are kept as `-dup.jpg` rather than deleted.
→ [RESULTS §3c.4](RESULTS.md#3c4-a-defect-in-the-p71-arms-of-this-run)

### 3.2 — colour: `p7.2` **← failed, `p7.2b` open**

**How.** Four colour words in the same slot: `white` (control), `grey`, the paired
person's tone from the CPU skin reader, and the tone furthest in lightness from the
garment. → [RESULTS §3c.3](RESULTS.md#3c3-a-chromatic-mannequin-colour-bleeds-into-the-garment-p72-fails)

**Result.** **Failed, and instructively.** A bare chromatic adjective does not stay on the
mannequin. `"tan"` turned `p029`'s white button-down into a **tan polo shirt** — wrong
colour *and* wrong garment — and `emma_watson`'s black blazer **brown**. `white`, `grey`
and `black` leave the garment alone.

**The axis is achromatic versus chromatic, not matched versus unmatched.** The `contrast`
arm picked black or white on all eight references, because it maximises lightness distance
and the tone ladder's extremes are achromatic — and it has the lowest drift of the four.

**This kills skin-tone matching in the form it was proposed.** Skin tones are chromatic by
definition, so the property that makes a mannequin plausible as a body is the same one
that contaminates the garment. Two things survive: `grey` is a cheap achromatic answer
that needs no reader at all, and the leak may be a **binding** failure rather than a
colour failure — the adjective sits in a slot the model can read as applying to the whole
picture.

**`p7.2b` fixes it.** The word becomes `"tan skin"` instead of `"tan"`, naming what the
colour belongs to, and the colour stays on the mannequin. **The failure was a binding
failure, not a colour failure**, and the fix is one word and free.
→ [RESULTS §3c.6](RESULTS.md#3c6-p72b-the-colour-named-as-skin)

**`p7.2b+`** widens the ladder to ten ordinary phrases and runs the CPU reader's own pick
on the paired person. Generated, **not yet judged**. The question it exists to answer is
not "is it accurate" but **"is it finer than the model can resolve"** — if neighbouring
steps look the same, the reader can be coarser and cheaper.
→ [RESULTS §3c.7](RESULTS.md#3c7-p72b-the-wider-ladder)

**One rule now has three instances and is worth stating on its own:** the model does
exactly what the words permit. `"the garment"` permitted one garment; `"bag, belt, hat"`
permitted invention; `"tan"` permitted a tan picture; `"tan skin"` permits only a tan
mannequin. Every prompt failure in this investigation has been a permission that was
wider than the intent.

**Result of link 3 overall.** *Framing solved by `p7.1.3`. Colour solved by `p7.2b`, with
`p7.2b+` open on granularity. Blank terminations (C) not addressed — still parked behind
the framing fix.*

**The two fixes have never been combined.** `p7.1.3` carries a framing clause and no
colour word; `p7.2b` carries a colour word and no framing clause — verified against the
prompts as sent. One variable at a time was the right way to run them and it means the
combined prompt is untested. **That combination is the next run, and it is the first one
that should go through a klein edit** — everything in link 3 so far is a reference, and a
better reference is not yet a better try-on.

---

## Phase 2 — the components are accepted; now assemble and stress them

Opened 2026-08-27. Links 1&ndash;3 ran one variable at a time and produced two accepted
components. Phase 2 does three things that links 1&ndash;3 deliberately did not: it
**verifies the reader that feeds the prompt**, it **combines** the two components, and it
**stresses the framing component** on the one thing it currently has no words for.

Everything in phase 2 lands on its own page — `v3/report/v31_phase2.html` — because it
answers different questions from the prompt-iteration pages and mixing them would make
both harder to read.

### 4 — Is the colour reader extracting correctly? **← open**

**Why now.** The enum structure is adopted, which means **the ladder is the interface**:
everything downstream sees a named phrase and nothing else. That makes the reader the one
component whose errors are invisible at every later stage — a wrong phrase produces a
perfectly well-formed prompt and a plausible mannequin of the wrong colour. It has been
looked at on a sample; it has never been audited.

**The architecture being audited.** Four stages, all CPU, ~149 ms end to end:

```
person photograph
  └─ MediaPipe Selfie Multiclass  (256×256, Apache-2.0, cached locally)
       └─ FACE class at confidence > 0.6      ── fallback: BODY class if face < 500 px
            └─ median L*a*b* over the selected pixels      ← median, not mean
                 ├─ ITA = arctan((L*−50)/b*) · 180/π       ← reported, not used to choose
                 └─ nearest ladder step by L*
                      └─ phrase, e.g. "dark beige skin"
                           └─ PREFIX + phrase + SUFFIX
```

Two choices in there are load-bearing and are stated so they can be argued with. **The
median rather than the mean**, because a face carries shadow, specular highlight and
often makeup, and the mean follows all three. **Quantisation to a named phrase rather
than a hex**, because `p7.2` established that the model reads words and because a fixed
ladder means the reader can be replaced without touching the prompt.

**How it is tested.** Every image in test_set3, not a sample. For each: the photograph,
the pixels the median was taken from, **the raw measured hex**, **the enum label it was
assigned**, and **the swatch of that label** side by side. Plus ΔE between measured and
assigned, so the quantisation error is visible as a number rather than left to the eye.

**What would count as wrong.** A measured hex that does not look like the person's skin
(the mask grabbed background, hair or garment). A large ΔE, meaning the ladder has no
step near this person. A systematic drift in one direction, meaning the thresholds are
misplaced. Each of those has a different fix and the audit distinguishes them.

### 5 — `p7.3`: the two components combined **← open**

**Why.** `p7.1.3` and `p7.2b+` were run with the other variable held empty, on purpose.
Two fixes that each work alone are not thereby a fix that works together — the framing
clause and the colour phrase occupy different slots in the same sentence and could
interact.

**What changes.** One prompt carrying both:

```
PREFIX + <ladder phrase from the paired person> + SUFFIX + <framing clause from the pose reader>
```

**How it is tested.** The same 8 probe references, against three baselines already on
disk: `p7` (neither fix), `p7.1.3` (framing only) and `p7.2b+.matched` (colour only). A
four-way comparison on identical references answers whether the combination is additive,
neutral, or worse than either alone.

**And then, for the first time, through klein.** Everything in links 1&ndash;3 is a
reference. `p7.3` is the first candidate worth the edit call, because a better-looking
mannequin is not yet a better try-on and that gap has been open since link 2.

### 6 — `p7.1.3.n`: keeping or dropping accessories **← open**

**Why.** `p7` contains one sentence about accessories and it only points one way:
*"The mannequin wears only what the person is wearing and nothing else: if they are not
carrying a bag, there is no bag."* That **forbids addition** and says nothing about
**retention**, so a bag that does exist has no instruction protecting it. Bags, belts and
jewellery are dropped in most references.

The goal is not "always keep". It is **a reliable toggle** — wording that keeps
accessories when they are wanted and drops them when they are not, so the behaviour is
chosen rather than accidental.

**The risk, named in advance.** `p4`/`p5` failed by enumerating accessory slots, which
the model read as an instruction to produce them. Any variant that enumerates is walking
back into that failure. That is precisely why one variant enumerates: **to find out
whether the "only what the person is wearing" guard is strong enough to make enumeration
safe.** A negative result there is worth as much as a positive one.

**The four variants.**

| | intent | the clause |
|---|---|---|
| `a` | keep, **symmetric, no enumeration** | *"Whatever the person is wearing or carrying, the mannequin has too, in the same place; whatever they do not have, it does not."* |
| `b` | keep, **enumerated** — the deliberate risk | *"Keep the bag, hat, scarf, belt, glasses and jewellery if the person has them, and add none if they do not."* |
| `c` | **drop** — the other half of the toggle | *"Show the clothing only: no bag, no hat, no jewellery, no eyewear, even if the person has them."* |
| `d` | keep, **placement-preserving** | *"Anything the person carries hangs on the mannequin the same way — over the same shoulder, in the same hand."* |

**How it is judged.** Against the source photograph, per reference: was each accessory in
the photograph retained, and was anything present that was not in the photograph. `b` and
`c` are the informative pair — if `b` invents and `c` reliably strips, then enumeration is
unsafe in the positive direction and safe in the negative one, which is a usable rule
rather than a preference.

---

## Phase 3 — first principles: strip the prompt, and prepare the input

Opened 2026-08-27. Phases 1 and 2 built the prompt by **accretion** — every clause was
added because removing it caused a failure. Phase 3 inverts that: **start from nothing and
add only what is shown to be necessary.**

Two things changed the ground under the earlier phases and both are now settled:

1. **The duplication was never the prompt.** It was the landscape canvas
   ([RESULTS §3c.12](RESULTS.md#3c12-aspect-ratio-causes-the-duplication-and-padding-fixes-it)).
   Clause-level explanations for it are withdrawn.
2. **fal does not rewrite our prompts** — schema has no rewriter field, and two identical
   calls returned byte-identical images
   ([INVESTIGATION.md §4.6](../INVESTIGATION.md#46-two-things-to-check-about-fal-before-trusting-any-of-this)).
   So the prompt record measures our wording. It also means we run the configuration Qwen
   calls unstable, with no switch to change it.

Phase 3 lands on its own page — `v3/report/v31_phase3.html`.

### 7 — `p7.3.n`: the minimum prompt **← open**

**Why.** The [ablation](RESULTS.md#3c11-prompt-length-ablation-most-of-p73-is-doing-nothing-and-some-of-it-hurts)
showed 27 words matching 94 on five of eight references, and the 94-word version **losing
garment colour** on a sixth. The literature names that axis: compound instructions cost
identity preservation −1.8 to −2.4 of 10 and instruction-following only −0.11 to −0.81
([INVESTIGATION.md §4.2](../INVESTIGATION.md#42-compound-instructions-cost-fidelity-not-compliance-and-that-is-our-result)).
**Every extra clause is paid for in fidelity, which is the thing we are trying to keep.**

**What the prompt has to carry, and nothing else.** Three requirements:

| | why it is irreducible |
|---|---|
| **mannequin colour** | a white form under a white garment is a low-amplitude boundary — the `HD_p023` mechanism, rebuilt inside our own reference |
| **garment preservation** | the entire purpose; the reference is worthless if it is a different garment |
| **extent / ratio** | a whole-body instruction against a waist-up photograph is satisfied by inventing legs |

Everything else in `p7.3` — the person's absence, the completeness clause, the
no-addition guard — is a **candidate for deletion** until it earns its place.

**A second change, from the research.** `p7.3` contains four negations and names four
nouns it does not want rendered — *bag, face, skin, hair*. Every first-party source says
to write positives instead, and **Qwen's own rewriter forbids negation words outright**
([INVESTIGATION.md §4.4](../INVESTIGATION.md#44-negations-should-be-rewritten-as-positives)).
So the ladder is built negation-free and the negated version is kept only as the control.

**The variants**, each a strict addition to the one before except where noted:

| | adds | words |
|---|---|---|
| `p7.3.1` | the three irreducibles, nothing else | ~22 |
| `p7.3.2` | + garment fidelity stated explicitly | ~32 |
| `p7.3.3` | + the mannequin is featureless — *positive* phrasing for "no face, no skin, no hair" | ~38 |
| `p7.3.4` | + completeness, positively phrased | ~48 |
| `p7.3.5` | the whole of `p7.3` rewritten with **no negations** | ~80 |
| `p7.3.6` | current `p7.3`, unchanged — the control | 94 |

**How it is judged.** Every column's full prompt is printed above it, so the difference
between adjacent columns is readable without consulting a file. The question per column is
the same: **is the garment still the garment**, and did anything get invented.

### 8 — Cropping the input before extraction **← open**

**Why.** Until now the model has been handed a **raw photograph** — a person in a room,
with background, and in one case 83% of the frame empty. The mask stack that V2 built is
sitting unused in this path, and the whole of
[v3.0](../v3.0/EXPERIMENT.md) is about the fact that **the reference given to a call
determines what comes back**.

Two things a crop should buy, both testable:

- **Less to attend to.** The mechanism in
  [INVESTIGATION.md §4.1](../INVESTIGATION.md#41-length-is-not-the-problem-constraint-count-is)
  is attention competition — a background is content competing with the garment.
- **More garment per token.** A reference is tokenised at 16×16 pixels per token and
  BFL's `cap_pixels` **only ever downsizes**. Subject fill runs as low as 17%
  ([RESULTS §3](RESULTS.md#3-observed-not-yet-scored)); cropping to the subject raises
  the garment's share of the token budget without a larger image.

**Two crop variants, one variable between them: the head.**

| arm | what it is | what it tests |
|---|---|---|
| `CROPB` | background removed, **subject whole, head kept**, cropped to the subject bbox on white | whether removing the *background* alone is enough |
| `CROPH` | background removed **and head removed** — the V2 `PHEAD`-style cut | whether the head is itself the distraction, at the cost of a cut boundary |

`CROPH` is the interesting one and it is not free: cutting the head reintroduces exactly
the cut boundary that [v3.0](../v3.0/EXPERIMENT.md) showed klein copies into its output.
**The question is whether that cost is worth paying when the consumer is a regenerative
model rather than a subtractive one** — QX regenerates, so it may not copy the boundary
the way klein does. That is the hypothesis, and it has never been tested because the
mask stack and the regeneration arm have never been used together.

Both crops are **pure CPU**, both use the mask stack unchanged, and both hold the prompt
fixed at `p7.3` so the input is the only variable.

**Architecture.** The reference path becomes, for the first time, more than a resize:

```
photograph
  ├─ MediaPipe Selfie Multiclass ─┐            149 ms
  ├─ MediaPipe Pose ──────────────┤             36 ms
  └─ BiRefNet_lite @1024²  ───────┤            ~60 s   subject matte
                                  ↓
     ┌── framing category ────────────────→ extent clause
     ├── person's skin tone ─────────────→ colour phrase   (from the WEARER, not this image)
     └── subject alpha ──────────────────→ crop: bbox, white ground, head kept or cut
                                  ↓
                    PREFIX + colour + SUFFIX + extent
                                  ↓
                       Qwen-Image-Edit-2511 → reference
```

Everything left of the model is CPU and free. **No stage here consumes one of the two
production calls** — the extraction is call one and the try-on edit is call two.

**Result.** *Nothing run.*

---

## Phase 4 — how good does the crop have to be?

Opened 2026-08-27. Phase 3 showed cropping works and left one number unexamined: **the
crop costs 49 seconds, and 48.9 of them are BiRefNet_lite at 1024²**. Pose landmarks give
a bounding box in 40 ms and Selfie Multiclass gives a subject mask in 151 ms. Nobody has
asked whether the expensive matte earns its place.

### 9 — The crop-quality ladder **← open**

**Why the question is open rather than settled.** V2 chose BiRefNet at 1024² for a
specific, measured reason: the cheap 256² map is *"a staircase by construction"* and
**klein copies the staircase into its output** — that is the finding the whole cropper was
rebuilt around, taking jag from 0.427 to 0.048.

**But the consumer here is not klein.** QX regenerates rather than subtracts. The same
argument that says a regenerative model may absorb a *cut boundary* says it may absorb a
*stair-stepped edge*. **If it does, 49 seconds buys nothing**, and the entire mask stack
collapses to 151 ms.

**What is varied: the input, and nothing else.** The prompt is held at the **full
`p7.3`** on every arm. Phase 3 established that the minimum prompt's sufficiency is
conditional on the input — `zendaya` under a head-kept crop came back as a person because
`p7.3.1` never says to remove one
([RESULTS §3c.17](RESULTS.md#3c17-the-minimum-prompt-is-only-sufficient-for-some-inputs-zendaya-under-cropb)).
Holding the prompt at the full version removes that interaction from this experiment. It
is a deliberate scope cut: **prompt minimisation and crop minimisation are separate
questions and mixing them would confound both.**

**Cohort.** The six references V2 measured as worst for hair over the garment — `p021`
19.5%, `p023` 16.9%, `zendaya` 14.4%, `p019` 13.5%, `p028` 11.9%, `p009` 7.2%. The hardest
cases, so a cheap method that survives them is not surviving by luck.

**The ladder, monotone in cost**, so the result reads as a curve rather than a comparison:

| arm | preparation | cost |
|---|---|---|
| `A0 raw` | the photograph, unmodified — the control | 0 |
| `A1 bbox` | crop to the subject's bounding box from pose landmarks, **background kept** | **40 ms** |
| `A2 mask256` | bbox + background removed with Selfie Multiclass 256² — the staircase V2 rejected | **151 ms** |
| `A3 biref512` | bbox + background removed, BiRefNet at **512²** — same model, a quarter of the pixels | to measure |
| `A4 biref1024` | bbox + background removed, BiRefNet at 1024² — what phase 3 ran | ~49 s |
| `A5 biref1024+head` | as A4, plus the head removed — the PHEAD-style cut | ~122 s |

`A1` is the arm that isolates **cropping from background removal.** They have always been
done together and they are different operations with different costs; if `A1` is enough,
no matte is needed at all.

**Also measured, without spending a call:** wall-clock per method, and **edge roughness of
each crop against `A4` as the reference**. That quantifies *how much worse* the cheap edges
are before asking whether it matters — so a null result reads as "the difference is real
and does not matter" rather than "there was no difference".

**What each outcome would settle:**

- `A2` ≈ `A4` → **BiRefNet leaves the path**, and the crop goes from 49 s to 151 ms.
- `A1` ≈ `A2` → **background removal leaves the path too**; cropping alone is the whole
  benefit.
- `A5` best → head removal is worth 122 s, or worth reimplementing cheaply.
- `A0` best → cropping is not the win phase 3 suggested, and phase 3's result was carried
  by the eight-reference probe cohort.

**36 cells: 6 references × 6 arms, one prompt.** No prompt variation, no second axis.

**Result.** *Nothing run.*

---

## Conclusion

*Not reached.* Link 1 has landed and is durable — `p7` and the two prompt rules survive
whatever happens next. Link 2 is generated and unscored. Link 3 is the reason scoring has
not happened: **three known defects would be scored as arm failures when they are
reference-construction failures**, and the fix for two of them is free.

No `SOLUTION.md`, and none should be written until link 3 closes.
