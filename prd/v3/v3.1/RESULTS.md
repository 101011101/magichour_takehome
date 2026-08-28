# v3.1 — RESULTS

**Status: open.** The evidence layer for the ghost-mannequin investigation. Per
[SCHEMA.md](../SCHEMA.md) this document reports what was observed and how; the decision
belongs in `EXPERIMENT.md`, which is not written yet.

Shared ground — the vocabulary and the model-level mechanism — is in
[INVESTIGATION.md](../INVESTIGATION.md).

Pages: `v3/report/v31_p7_accuracy.html` (the extraction against its source),
`v3/report/v31_mannequins.html` (all three mannequin prompts),
`v3/report/v31_arms_vs.html` (the three arms through klein),
`v3/report/extraction_shapes.html` (every prompt tried).

---

## 1. The prompt: `p7` is the one

**Reviewer verdict, 2026-08-26: `p7` (`QMB`) is the best of the eight extraction prompts
tried, and is what v3.1 is built on.** Judged by eye over the probe set and then over all
28 references; not tier-scored, because the failures of the others are categorical rather
than marginal.

Prompt of record — `EXTRACT["QMB"]` in `v3/build/run_v30.py`:

> Show this person's outfit on a mannequin against pure white. The mannequin wears every
> piece the person is actually wearing, from head to feet, exactly as they wear it,
> keeping its shape and drape - and the person themself is gone, no face, no skin, no
> hair. Copy each piece exactly - the same colour, print, texture and cut. The mannequin
> wears only what the person is wearing and nothing else: if they are not carrying a bag,
> there is no bag.

### 1.1 How it was arrived at, and what each version broke

Eight prompts. Each fixed something and broke something else, and the sequence is the
finding — **it is a record of the model doing exactly what it was told.**

| | prompt | fixed | broke |
|---|---|---|---|
| `p1` | QX, isolated on white | — | says **"the garment", singular** — pieces dropped |
| `p2` | QF, flat lay | — | same singular noun, plus *"do not complete anything that is not visible"*. **`g018` returned a blazer with no trousers** |
| `p3` | QM, ghost mannequin | says "outfit", drops least of the three originals | footwear still dropped |
| `p4` | QFA, flat, slots named | **dropping fixed** | naming the accessory slots made the model **generate** them — hats, bags and scarves in no photograph |
| `p5` | QMA, mannequin, slots named | **dropping fixed** | same invention; every mannequin wore a hat |
| `p6` | QFB, flat, no slot list | **invention fixed** | *"from what is on their head to what is on their feet"* read as **include the head** — floating wigs and faces |
| **`p7`** | **QMB, mannequin, no slot list** | **complete outfit, nothing invented, no head** | **— nothing found** |
| `p8` | QFC, flat, footwear named | **head fixed** | *"side by side"* read as **show variants** — pieces duplicated |

Two mechanisms are worth carrying forward, because they are the same one from
[INVESTIGATION.md §2.1](../INVESTIGATION.md#21-over-attention-has-two-sources-and-they-are-the-mechanism-split)
seen from the prompt side:

1. **Naming a slot fills it.** `p4`/`p5` asked for "bag, belt, hat, scarf, eyewear and
   jewellery" and got them whether or not they existed. **Over-attention by invention,
   caused by the prompt rather than by the reference.**
2. **A concrete negative constrains where an abstract one does not.** `p7` does not
   enumerate; it says *"if they are not carrying a bag, there is no bag."* That is what
   holds the invention down without priming it.

`p8` shows the flat shape is **not** solved — it is one word from it, and "side by side"
is the suspect. The flat direction is parked, not abandoned.

## 2. What has been run

| | |
|---|---|
| references | 28, the [v3.0 run-B fold](../v3.0/TEST.md#1-run-b-the-fold) |
| `p7` extractions | 28/28, no failures |
| `p7` → klein edits | 28/28, no failures, ~$0.42 |
| conditions | seed 46, V2 AMT prompt, ≤1.15 MP inputs — identical to BC and QX |
| outputs | `v3/runs/v3.0b/gen/{set_id}__QMB.jpg` |

Because all three arms end in the same klein call with the same seed and prompt, **the
reference image is the only variable between them.**

## 3. Observed, not yet scored

1. **`p7` is the only reference of the three that carries footwear**, and therefore the
   only arm that transfers shoes. Visible on `g024` (white sneakers replacing the
   subject's platform boots) and on the black suit. **Whether that is wanted is a product
   decision, not a quality one**, and it should be marked as its own thing rather than
   scored as a plain win or loss.
2. **On single-garment references the three arms are near-indistinguishable.** The
   mannequin shape costs the same two calls and buys nothing there.
3. **Frame usage is a real problem.** The subject occupies a median **61%** of the
   extraction, but as little as **17%** (`emma_watson`, `p029`). Since a reference is
   tokenised at 16×16 pixels per token and BFL's `cap_pixels` **only ever downsizes**, a
   small subject carries proportionally fewer tokens into the edit call. Cropping to the
   subject bbox and upsampling toward the cap is pure CPU and untested — it is
   mitigation **M4** from
   [INVESTIGATION.md §3.7](../INVESTIGATION.md#37-mitigations-that-have-a-mechanism-behind-them).

## 3b. Three defects in the p7 mannequin, from review

Recorded 2026-08-27. All three were raised by eye and then checked against the frames;
the references named are ones where the defect is unambiguous. **None is tier-scored, and
none has a full count** — that needs the marking pass.

### 3b.1 The mannequin is sometimes the same value as the garment

The form renders white or pale cream. When the garment is also white or pale, **the two
merge and the garment loses its outline**.

| reference | what happens |
|---|---|
| `p030` | white turtleneck on a white form — the result is one continuous white shape, and where the garment ends is not visible |
| `p029` | white shirt on a white form — the shirt blends into the neck and arms |

This is not a new failure mode. It is
[§3.4's amplitude argument](../INVESTIGATION.md#34-why-p023-specifically-amplitude-not-contrast)
happening **inside the reference we built**: a boundary with a small luminance step
carries little spectral amplitude, so at the timesteps where layout is decided it does
not exist as a signal. `HD_p023` failed in V2 because a nude garment sat against bare
skin. A white garment on a white mannequin reproduces that condition deliberately.

**Direction, to be designed:** derive a mannequin colour that contrasts with the garment
rather than defaulting to white — for instance from the **target person's** skin tone,
computed on CPU from the person input. That keeps the mannequin plausible as a body while
guaranteeing the garment has an edge to be found at. Not designed, not built, not
measured; see [EXPERIMENT.md](EXPERIMENT.md).

### 3b.2 The mannequin invents garments the photograph does not contain

Where the source is cropped, `p7` completes the body and **invents clothing for the part
it cannot see**.

| reference | source | invented |
|---|---|---|
| `p029` | waist-up, white shirt | full black trousers |
| `p030` | waist-up, white turtleneck | full-length white legs / leggings |
| `dualuse_emma_watson_black_blazer_armscrossed` | portrait cropped mid-torso, blazer | a complete trouser suit |

Two of the three (`p029`, `p030`) are tagged `framing = waist_up` in test-set-1's
manifest, so **the condition is already labelled in the data** and does not need to be
inferred. The third is untagged because test_set2 was never tagged.

This is over-attention **by invention** in the sense of
[§2.1](../INVESTIGATION.md#21-over-attention-has-two-sources-and-they-are-the-mechanism-split),
and the cause is in the prompt: `p7` says *"from head to feet"*, which asks for a whole
body. Against a waist-up photograph that instruction cannot be satisfied honestly, so it
is satisfied dishonestly. It is the same class of fault as `p4`/`p5` naming accessory
slots — **the prompt asked for something that was not there, and got it.**

### 3b.3 Feet and limb terminations come back blank or malformed

Where the outfit ends, the mannequin frequently does not resolve: hems stop against
nothing, ankles end without feet.

| reference | what happens |
|---|---|
| `g013` | maxi dress hem ends, no feet below it |
| `g015` | slip dress hem ends, no feet below it |
| `g029` | legs terminate at the ankle in blank white |
| `p030` | full-length legs, no feet |

Worth separating from 3b.2 even though both concern the lower body: **3b.2 is inventing
what is absent, 3b.3 is failing to render what it invented.** A fix for one does not
imply a fix for the other.

## 3c. p7.1 and p7.2 — the framing and colour probes

8 references chosen because they carry the defects in §3b, 7 arms each, 56 extractions,
no failures. Every prompt is the same sentence with **one word or one clause changed**:

```
"Show this person's outfit on a " + <colour word> + " mannequin against pure white. …" + <framing clause>
```

p7.1 holds the colour empty and varies the clause; p7.2 holds the clause empty and varies
the word. Page: `v3/report/v31_p7n.html`. Every prompt as sent:
`v3/runs/v3.0b/_p7n_prompts.json`.

### 3c.1 The CPU readers

Both run on CPU, neither needs a GPU or a network call.

| reader | model | time | output |
|---|---|---|---|
| tone | MediaPipe Selfie Multiclass | **149 ms** | median Lab of face-skin → ITA → one of eight colour words |
| framing | MediaPipe Pose Landmarker Lite | **36 ms** | which joints are confident and in frame → `full_body / knee_up / waist_up / chest_up` |

The tone statistic is the **median**, not the mean: a face carries shadow, specular
highlight and often makeup, and the median survives all three. The word is what reaches
the prompt; the hex is recorded for checking only.

Over all 56 test_set3 images: framing `full_body` 33, `waist_up` 17, `knee_up` 3,
`chest_up` 2, `unknown` 1 — **23 of 56 are not full-body, so the invention condition in
§3b.2 is common rather than a corner case.** Tone: `tan` 17, `light brown` 14, `brown` 7,
`dark brown` 7, `beige` 5, `black` 5, `cream` 1.

Reader page, with the pixels each median was taken from shown tinted so the mask can be
checked: `v3/report/v31_skin_reader.html`.

### 3c.2 `p7.1.3` — the CPU framing reader works

**Reviewer verdict: `p7.1.3` is good.** Cited: `dualuse_man_black_suit_studio_nonceleb`
and `g024` — the garment is maintained and the mannequin stops where the photograph
stops.

`.3` reads the pose landmarks and injects the extent it found
(*"Show the mannequin from the head to the hip only, cut off below the hip"*), rather than
asking the model to work the extent out for itself as `.1` and `.2` do. **The reader's
verdict is printed above every row on the page**, because a CPU reader that is wrong makes
the prompt confidently wrong — that is the standing risk of this route and the reason `.1`
and `.2` were run alongside it.

One disagreement already visible: `p029` is tagged `framing = waist_up` in test-set-1's
manifest and the pose reader calls it `chest_up`, having found shoulders and no hips.
Neither has been adjudicated against the image.

### 3c.3 A chromatic mannequin colour bleeds into the garment — p7.2 fails

**Reviewer verdict: the colour prompt does not work.** Checked and it is not a tint, it is
garment substitution:

| reference | word | what happened to the garment |
|---|---|---|
| `p029` | tan | **the white button-down became a tan polo shirt** — different colour *and* different garment type; the trousers went tan too |
| `dualuse_emma_watson_black_blazer_armscrossed` | tan | **the black blazer came back brown** |
| `g024` | tan | garment survived — only the mannequin is tan |

So it does not bleed every time, but when it bleeds it destroys the reference.

The drift statistics agree in direction. Mean absolute drift against the subtractive crop,
8 references:

| arm | \|dL\| | \|dC\| | dHue | edge |
|---|---|---|---|---|
| `p7.2.white` | 52.9 | 5.6 | 35.2&deg; | 0.83 |
| `p7.2.grey` | 45.8 | 6.0 | 34.9&deg; | 1.01 |
| **`p7.2.matched`** | 44.0 | **7.6** | **39.0&deg;** | 1.11 |
| `p7.2.contrast` | **38.1** | **5.5** | **30.8&deg;** | 0.97 |

`matched` has the worst chroma and hue drift of the four. `contrast` has the best — and
`contrast` picked **black or white on every one of the eight**, because it maximises
lightness distance from the garment and the tone ladder's extremes are achromatic.

**The pattern is achromatic versus chromatic, not matched versus unmatched.** `white`,
`grey` and `black` leave the garment alone. `tan` and `brown` contaminate it. The model
appears to apply the colour word to the image rather than to the mannequin.

**Caveat on those numbers, stated rather than buried:** the statistics run over non-white
pixels, so **a coloured mannequin raises chroma by construction** — the form itself is
counted as garment. The numbers therefore *corroborate* the reviewer's observation; they
do not independently prove it. The evidence that the garment changed is the frames.

### 3c.4 A defect in the p7.1 arms of this run

**All 24 p7.1 extractions were generated with the word "mannequin" duplicated** —
`"on a mannequin mannequin against pure white"`. The colour slot was fed the literal
word `mannequin` for those arms instead of being left empty, and the suffix supplies the
noun already. Found by printing the prompts as sent, not by inspecting the frames.

What it does and does not compromise:

- **The comparison between `.1`, `.2` and `.3` is unaffected** — all three carry the same
  duplication, so the framing clause is still the only thing that differs between them,
  and `p7.1.3` beating the other two stands.
- **The comparison against the `p7` baseline is confounded.** The baseline has
  `"on a mannequin"`; the p7.1 arms have `"on a mannequin mannequin"`. Any difference
  between p7.1 and baseline carries that extra word.

**Re-run 2026-08-27.** The builder is fixed and all 24 p7.1 frames were regenerated
clean. The defective frames are kept on disk as `{ref}__p7.1.n-dup.jpg` rather than
deleted, so the confounded comparison can be re-checked if anyone doubts this note.
Everything on `v3/report/v31_p7n.html` is now the clean run.

### 3c.5 What that does to the skin-tone proposal

**Skin-tone matching is dead in this form.** Skin tones are chromatic by definition, so
the mechanism that makes them plausible as a body is the same one that contaminates the
garment.

Two things survive:

1. **`grey` is the cheap answer.** It is non-white, it is achromatic, it does not bleed,
   and it requires no reader at all. If grey is sufficient to give the garment an edge,
   the whole skin-tone apparatus is unnecessary — which was the result worth watching for.
2. **The binding may be a prompt problem, not a colour problem.** The colour word sits in
   an adjective slot (`"on a tan mannequin"`) that the model is free to read as applying
   to the whole picture. **Tested as `p7.2b` below.**

### 3c.6 `p7.2b` — the colour named as *skin*

The binding test. Same slot, same sentence, but the word becomes `"tan skin"` rather than
`"tan"` — which says the colour is the mannequin's complexion rather than the picture's
palette. Five arms over the same 8 references, 40 extractions, no failures:

| arm | word |
|---|---|
| `p7.2b.white` | `white skin` |
| `p7.2b.beige` | `beige skin` |
| `p7.2b.tan` | `tan skin` |
| `p7.2b.black` | `black skin` |
| `p7.2b.grey` | `grey` — left bare, because a grey mannequin is a material and not a complexion, and it is the control that needs no reader at all |

**Reviewer verdict 2026-08-27: `p7.2b` solves it.** Naming the colour as *skin* keeps it
on the mannequin where the bare adjective leaked. **The failure was a binding failure, not
a colour failure** — the fix is one word, and it is free.

That is the third time in this investigation the same shape of fault has appeared: the
model does exactly what the words permit. `"the garment"` permitted one garment.
`"bag, belt, hat"` permitted invention. `"tan"` permitted a tan picture. `"tan skin"`
permits only a tan mannequin.

### 3c.7 `p7.2b+` — the wider ladder

Ten steps instead of four, every one an ordinary phrase carrying the word *skin*:
`pale · light beige · beige · dark beige · light tan · tan · light brown · brown ·
dark brown · black`. `grey` is deliberately **not** on this ladder — it is the achromatic
control and it is not a complexion.

Over all 56 test_set3 images the CPU reader spreads across nine of the ten steps:
`dark beige` 16, `tan` 10, `light brown` 5, `black` 5, `beige` 5, `dark brown` 5,
`light tan` 5, `brown` 4, `light beige` 1, `pale` 0.

Run: the full ladder on **4 references** — a light garment that bled, a dark garment that
bled, a multi-piece that survived, and a dark full-body control — plus the reader's own
pick on the **paired person** for all 8. 48 extractions, no failures.

**Reviewer verdict 2026-08-27: colours approved — "mostly good enough".** The swatches are
right and the range is visibly covered. Approved as *sufficient*, not as perfect: the
qualifier is recorded because it is the honest strength of the claim, and because
"mostly" is what licenses stopping here rather than tuning further. **The enum structure
is adopted** — the mannequin colour is chosen
from a fixed ladder of named phrases, never a free-form value and never a hex.

That settles the shape of the colour component:

> a CPU reader measures the person, the measurement is **quantised to one of ten named
> phrases**, and the phrase is concatenated into the prompt.

Nothing downstream ever sees a continuous value. The ladder is the interface, which means
the reader can be replaced or made coarser without touching the prompt, and the prompt can
be rewritten without touching the reader.

**Still open:** whether ten steps are distinguishable *by the model*, or whether it
collapses them into three or four. If neighbouring steps are indistinguishable the ladder
is finer than the model, and the reader can be made coarser and cheaper. That is a
question about the model, not about the reader, and it does not block adoption of the
structure.

### 3c.7b Enumeration — what the word means here

The term recurs, so it is defined once. **Enumeration means naming specific items in the
prompt as a list** — `"bag, belt, hat, scarf, glasses and jewellery"` — rather than
describing a rule that covers them.

It has appeared twice and behaved the same way both times:

- `p4`/`p5` enumerated accessory slots **to include them**. The model produced every named
  item whether or not the photograph contained it. Every mannequin came back wearing a
  hat.
- `p7`'s working guard does the opposite and describes a rule instead of a list:
  *"only what the person is wearing and nothing else"*.

**Positive direction** means enumerating to *include*: "keep the bag, the hat, the belt".
**Negative direction** means enumerating to *exclude*: "no bag, no hat, no belt".

The asymmetry expected is mechanical rather than stylistic. **An instruction to include a
named item can be satisfied by generating it** — the model can always produce a hat, and
producing one is a valid way of obeying. **An instruction to exclude a named item cannot
be satisfied by generating anything**; the worst case is that it removes something already
absent, which changes nothing. So the same list is a licence in one direction and a
constraint in the other.

### There is a third kind of clause, between a rule and a list

Added 2026-08-27 after the question *"is there something like keep all accessories?"* —
and it is a real gap in the original four variants.

| kind | example | what the model can do with it |
|---|---|---|
| **rule** | *"only what the person is wearing and nothing else"* | nothing to produce; describes a constraint |
| **enumeration of instances** | *"bag, hat, belt, scarf"* | **each noun is individually producible** |
| **category term** | *"all accessories"* | **no canonical instantiation** — there is no default accessory to generate |

That middle column is the whole mechanism. A list of instances is a licence in the
positive direction *because each item can be produced*; a class name cannot be satisfied
by producing anything in particular, so it has to be bound to what is in the image.

Three more variants test it:

| | intent | clause |
|---|---|---|
| `e` | keep, **category, bare** | *"Keep all accessories."* |
| `f` | keep, **category, grounded** | *"Keep every accessory the person is wearing or carrying, and add none they do not have."* |
| `g` | **drop, category** | *"Remove all accessories."* |

**`f` should be the safest keep-instruction of the seven** if the reasoning holds: it names
the class rather than the instances, *and* it is grounded in the photograph, which is the
rule link 1 arrived at — tell the model what is there. 24 more extractions, no failures.

That is a **prediction, not yet a result.** `p7.1.3.b` enumerates to include and
`p7.1.3.c` enumerates to exclude, on the same eight references, and all seven are
generated but unjudged. If `b` invents and `c` strips cleanly, the rule holds and it becomes a usable
one: *never enumerate to add; enumerate freely to remove.* If `b` behaves, the guard is
stronger than expected and enumeration is safe in both directions — which would be the
more useful outcome, because listing is easier to write than a rule.

### 3c.9 Accessories — descoped

**Decision 2026-08-27: out of scope.** `p7.1.3` stays as it is, with its one existing
sentence that forbids addition and says nothing about retention. Accessories will be
dropped inconsistently and that is accepted.

The seven variants are generated and stay on disk (`{ref}__p7.1.3.{a..g}.jpg`) with their
clauses in `ACCESSORY` in `v3/build/run_phase2.py`. **The rule-vs-enumeration-vs-category
distinction is kept** — it is a general finding about prompt wording, not an accessory
finding, and it applies to any future clause. What is dropped is the accessory question,
not the lesson.

### 3c.10 `p7.3` — what it is, and a duplication on one reference

**Composition, confirmed:**

```
PREFIX                    "Show this person's outfit on a "
  + <ladder phrase>       from p7.2b+ — the CPU skin reader on the PAIRED PERSON,
                          quantised to one of the ten named steps
  + SUFFIX                " mannequin against pure white. … there is no bag."
  + <framing clause>      from p7.1.3 — the CPU pose reader on the GARMENT reference,
                          one of five extent sentences
```

Two readers, two different inputs. **The colour comes from the person being dressed; the
framing comes from the photograph being extracted.** That asymmetry is deliberate and easy
to get wrong: reading the colour off the garment reference would give the mannequin the
*donor's* complexion, not the wearer's.

Worked example, `dualuse_emma_watson_black_blazer_armscrossed` — colour `dark beige skin`
read from person `p003`, framing `waist_up` read from the reference:

> Show this person's outfit on a **dark beige skin** mannequin against pure white. The
> mannequin wears every piece the person is actually wearing, exactly as they wear it,
> keeping its shape and drape - and the person themself is gone, no face, no skin, no
> hair. Copy each piece exactly - the same colour, print, texture and cut. The mannequin
> wears only what the person is wearing and nothing else: if they are not carrying a bag,
> there is no bag. **Show the mannequin from the head to the hip only, cut off below the
> hip.**

**The duplication.** `dualuse_emma_watson_black_blazer_armscrossed` came back with **two
mannequins side by side**, not identical — one in a black blazer, one in grey. It is
**1 of 8**; the other seven are single figures.

What is established:

- The same reference under `p7.1.3` alone and under `p7.2b+` alone produced **one**
  mannequin each. Only the combined prompt duplicated.
- It is the **only landscape source in the probe set** — 1290×891, where every other probe
  reference is portrait or square.

The likely mechanism, stated as a hypothesis: **a waist-up figure on a landscape canvas
leaves most of the width empty, and the model fills it.** The output is not a copy but a
*variant* — a second blazer in a different colour — which is the same behaviour `p8`
produced when it was told "side by side": the prompt starts reading like a product
listing, and product listings show more than one view.

**The caveat that stops this being a finding:** one sample per arm at one seed. That
`p7.1.3` and `p7.2b+` each produced a single figure and `p7.3` did not is **not enough to
attribute the duplication to the combination.** This reference may simply be marginal, and
any of the three could tip on a different seed.

Two fixes, both free, neither tried:

1. **Pad the reference to portrait before sending.** CPU, no generation. Removes the empty
   width rather than asking the model to leave it alone.
2. **Say "a single mannequin".** One word in a slot that already exists. This is the
   negative-direction instruction the enumeration finding says should be safe — there is
   nothing for the model to produce in order to satisfy "single".

### 3c.11 Prompt-length ablation — most of `p7.3` is doing nothing, and some of it hurts

`p7.3` reached 94 words and five sentences **by accretion**: every clause was added
because removing it caused a specific failure. That is a reasonable way to arrive at a
prompt and a bad reason to believe the result is minimal. Four nested levels, each a
strict superset of the one before, so the difference between adjacent columns is exactly
one clause. Same 8 references, same seed, same CPU readers.

| level | words | adds |
|---|---|---|
| `L1` | **27** | mannequin, colour, white ground, extent |
| `L2` | 39 | + *the person is gone* |
| `L3` | 51 | + *copy each piece exactly* |
| `L4` | **94** | + *wears every piece* + the no-addition guard — this is `p7.3` |

32 extractions, no failures.

**Result: on 5 of the 8 references all four levels are indistinguishable.** `g013`,
`g015`, `g029`, `dualuse_man_black_suit_studio_nonceleb` and `g024` look the same at 27
words as at 94. **The extra 67 words buy nothing visible on them.**

**On `p029` the longer prompt actively harms** — and the literature names this axis.
Complex-Edit measures that compound instructions cost **identity preservation** (−1.8 to
−2.4 of 10) far more than instruction-following (−0.11 to −0.81)
([INVESTIGATION.md §4.2](../INVESTIGATION.md#42-compound-instructions-cost-fidelity-not-compliance-and-that-is-our-result)).
Every level here obeyed — mannequin, cropped correctly, on white. What the longer prompt
lost was **fidelity**. The source is a white button-down shirt.
At `L1` and `L2` the shirt comes back **white**. At `L3` and `L4` it comes back **beige** —
it has taken the mannequin's colour. So the colour bleed documented in §3c.3 is **not
purely a phrasing problem: it is length-dependent.** The same `"... skin"` binding that
held at 27 words fails at 51 and 94. That is a genuinely new fact and it was not
predicted.

**On `dualuse_emma_watson_black_blazer_armscrossed` the duplication is unstable across
levels, not monotonic in length:** `L1` single, `L2` **two**, `L3` single, `L4` **two**.
A simple "longer is worse" story does not fit it. **Resolved by §3c.12: the cause is the
landscape canvas, not any clause.** The instability across levels is what a
canvas-driven failure looks like when you vary the prompt instead of the canvas — which
is a useful reminder that a variable moving with your intervention is not the same as
your intervention causing it.

**The caveat that stops `L1` being adopted.** The probe cohort was chosen for the *framing
and colour* defects — it is not the cohort on which `EVERY` and `GUARD` were earned.
Those two clauses were added because pieces were being dropped and items invented, and
**the eight references here do not contain the cases that motivated them.** That five
references look identical at 27 words is evidence that the clauses are inert *on these
five*, not evidence that they are inert. Testing `L1` against the references that
originally failed — the multi-piece and accessory-carrying ones — is what would settle it,
and has not been run.

### 3c.12 Aspect ratio causes the duplication, and padding fixes it

The literature says subject duplication follows from sampling at an aspect ratio away from
training, but only measures it for U-Net text-to-image models and never for an editing
model ([INVESTIGATION.md §4.5](../INVESTIGATION.md#45-aspect-ratio-drives-subject-duplication)).
So it was tested directly on the one reference that duplicated.

**Method.** `dualuse_emma_watson_black_blazer_armscrossed`, 1290×891 landscape, padded on
white to 1:1 and to 3:4 portrait. **The content is byte-identical** — same pixels, centred,
with white added. Same prompt, same seed 46. The canvas is the only variable.

| canvas | result |
|---|---|
| 1290×891 landscape (original) | **two mannequins**, one black blazer and one grey |
| padded to 1:1 | **one mannequin** |
| padded to 3:4 portrait | **one mannequin** |

**The duplication is caused by the canvas, not by the prompt.** Every clause-level
hypothesis in §3c.10 and §3c.11 — that it was the combination, or the length, or a
particular sentence — is superseded. The prompt never mattered.

**The fix is free and CPU-side:** pad the reference to portrait or square before sending.
No generation, no prompt change, and it does not consume the second call.

Two things this also settles:

1. **The prompt-side fix would have failed.** Adding "exactly one mannequin" is the
   intervention T2ICountBench measures as ineffective — "prompt refinement … generally
   do[es] not improve counting accuracy". It was the obvious next thing to try and it was
   the wrong one.
2. **It generalises past this reference.** 2 of 28 run-B references are landscape, and 23
   of 56 test_set3 images are not full-body — a short figure on a wide canvas is the
   condition, and it is common. **Padding should be applied to every reference, not to
   the ones observed to fail.**

**Caveat.** n = 1 reference, 3 canvases, one seed. The direction is clean and the
mechanism has published support for other architectures, but the rate is unmeasured.

### 3c.13 The minimum prompt wins — `p7.3.1` adopted

**Reviewer verdict 2026-08-27: the fewest words is the best.** `p7.3.1` is adopted:

> *This person's outfit on a **dark beige skin** mannequin, **shown from the head to the
> chest**, on a plain white background.*

Roughly 20 words carrying exactly the three irreducibles — colour, extent, white ground —
with the colour and extent spans filled by the CPU readers. Everything `p7.3` added over
six phases of accretion is deleted: the person's absence, the completeness clause, the
fidelity clause and the no-addition guard.

**Reviewer's evidence, verbatim:** *"dualuse_emma_watson_black_blazer_armscrossed seems to
have duplication errors with more words, otherwise it's basically the same with more or
less words."*

Both halves check out, and the second half is the more important one.

**"Basically the same with more or less words."** Across the ladder, on 7 of 8 references
all six levels are indistinguishable. The 74 extra words of `p7.3.6` buy nothing visible.
That agrees with the earlier ablation (§3c.11) on a different set of prompts, and with
Complex-Edit's measurement that compound instructions cost fidelity rather than compliance
([INVESTIGATION.md §4.2](../INVESTIGATION.md#42-compound-instructions-cost-fidelity-not-compliance-and-that-is-our-result)).

**"Duplication with more words."** On `emma_watson`, pooling the ladder and the earlier
ablation — ten samples on one reference:

| words | samples | duplicated |
|---|---|---|
| **≤ 36** | 4 | **0** |
| ≥ 39 | 6 | 4 |

The three shortest ladder levels and the shortest ablation level are all clean; the
duplications sit at 39, 49, 94 and 95 words.

**But word count is not the cause, and this is worth getting right.** §3c.12 showed that
**padding the same reference to 1:1 or 3:4 eliminated the duplication entirely** — same
94-word prompt, same seed, three canvases, and only the landscape one duplicated. So:

> **The landscape canvas creates the susceptibility. Word count modulates whether it
> fires.** Padding removes the condition; a short prompt avoids tripping it.

Both are worth having, and they are independent: padding is a CPU fix that works
regardless of prompt, and the short prompt is better for the fidelity reason anyway. **Do
both; do not treat either as the explanation.**

**Caveat:** n = 10 on one reference, one seed, and the 62-word level was clean while the
49-word level duplicated — so the relationship is not monotonic and the threshold is not
established.

### 3c.14 `p7.3.1acc` — buying accessory retention for two words

`p7.3.1` with one modifier: *"This person's **entire outfit including accessories** on a
{colour} mannequin, {extent}, on a plain white background."* 22 words instead of 20.

This is the accessory question from §3c.9 reopened at a price that makes it worth asking —
not a clause, not an enumeration, **a category term inside the noun phrase**. Per §3c.7b
that is the form least likely to invent: *accessories* has no canonical instantiation, so
there is nothing the model can produce to satisfy the word.

8 extractions, no failures.

**Reviewer verdict: worse.** Rejected. **[inferred]** The likely reason is that
*accessories* still names a thing to have, even as a class — it is an inventory
instruction, and the failure mode of inventory instructions throughout this investigation
has been that the model supplies the inventory.

**`p7.3.1exact` replaces it with one word rather than four:** *"This person's **exact**
outfit on a {colour} mannequin, {extent}, on a plain white background."* 21 words.

That is a different kind of modifier and the distinction is the point: *"including
accessories"* tells the model **what to have**; *"exact"* tells it **how faithful to be**.
The first can be satisfied by producing something, the second cannot. 8 extractions, no
failures, not yet judged.

### 3c.15 Cropping also fixes the duplication — three fixes, one variable

`dualuse_emma_watson_black_blazer_armscrossed` under `p7.3` with the input cropped:

| input | result |
|---|---|
| raw 1290×891 landscape | **two mannequins** |
| `CROPB` background removed | **one** |
| `CROPH` background + head removed | **one** |

**Reviewer's read, and it is right: crop and pad are the same fix.** Both normalise the
canvas around the subject — padding adds white until the frame is square, cropping removes
frame until it is not landscape. Either way the empty width the model was filling is gone.

So there are three interventions and only two mechanisms:

| fix | mechanism | cost |
|---|---|---|
| pad to 1:1 or 3:4 | canvas geometry | CPU, trivial |
| **crop to the subject** | canvas geometry **+ more garment per token** | CPU, ~60 s for the matte |
| shorten the prompt | modulates whether the condition fires | free, and better for fidelity anyway |

**Cropping strictly dominates padding**: same geometric effect, and it also raises the
garment's share of the token budget instead of spending tokens on white. Padding remains
the fallback where a matte is unavailable or too slow.

### 3c.16 The high-hair cohort, through cropping and regeneration

The six references V2 measured as worst for hair over the garment — `p021` 19.5%,
`p023` 16.9%, `zendaya` 14.4%, `p019` 13.5%, `p028` 11.9%, `p009` 7.2%. **This is the
cohort BC_klein's entire bald pass exists to handle, and none of it had ever been through
the regeneration path**, because run B's fold put these on the person side or left them
out.

Three inputs each — raw, `CROPB`, `CROPH` — prompt held at `p7.3.1`. 18 extractions, no
failures.

**Why `CROPH` is the question worth asking.** On a *subtractive* consumer, cutting the
head produces the jagged boundary that
[v3.0](../v3.0/EXPERIMENT.md#2-why-does-the-references-boundary-propagate-into-the-output)
showed klein copies into its output — it is the origin of the entire investigation. On a
*regenerative* consumer the model is not bound to reproduce what it was shown, so the cut
may cost nothing.

**If `CROPH` is clean on this cohort, the CPU mask stack and the regeneration arm solve
each other's problem** — the mask stack removes the hair that regeneration cannot see
past, and regeneration absorbs the cut boundary that the mask stack cannot avoid leaving.
They have never been run together. Not yet judged.

### 3c.17 The minimum prompt is only sufficient for some inputs — `zendaya` under `CROPB`

**Reviewer observation, checked and confirmed:** `dualuse_zendaya_white_blazer_skirt`
under `CROPB` came back as **a woman with hair and a face** — not a mannequin at all.

| input | what came back |
|---|---|
| raw | a headless mannequin form — correct |
| **`CROPB`** background removed, **head kept** | **the person, with hair and face** |
| `CROPH` background + head removed | a clean mannequin — correct |

The cause is not the crop. **`p7.3.1` contains no instruction to remove the person.** That
clause — *"the person themself is gone, no face, no skin, no hair"* — was deleted in §3c.13
as one of the 74 words that bought nothing. On the raw photographs of the probe cohort it
bought nothing. **Handed a background-removed image that still has a head in it, the model
has no reason to remove one.**

So the finding in §3c.13 needs qualifying rather than withdrawing:

> **The minimum prompt's sufficiency is conditional on the input.** `p7.3.1` is sufficient
> for a raw photograph and for a head-removed crop. It is *not* sufficient for a
> background-removed crop that keeps the head.

That points at two coherent pairings rather than one winner, and they are not the same
cost:

| input | prompt | why it holds together |
|---|---|---|
| `CROPH` head removed upstream | **minimum** | the head is already gone; saying so is redundant |
| `CROPB` head kept | **needs the removal clause back** | the head is present and nothing says to drop it |

**[inferred]** This is the same principle as everything else in this investigation —
*tell the model what is true of the image in front of it.* A clause is not globally
necessary or globally redundant; it is necessary **when the input contains the thing it
addresses.**

### 3c.18 What `p7.3` actually says, and the crop's real cost

**`p7.3.6` is the original**, unchanged from phase 2. As sent for `emma_watson`:

> Show this person's outfit on a dark beige skin mannequin against pure white. The
> mannequin wears every piece the person is actually wearing, exactly as they wear it,
> keeping its shape and drape - and the person themself is gone, no face, no skin, no
> hair. Copy each piece exactly - the same colour, print, texture and cut. The mannequin
> wears only what the person is wearing and nothing else: **if they are not carrying a
> bag, there is no bag.** Show the mannequin from the head to the **hip** only, cut off
> below the **hip**.

96 words. Two differences from the version quoted in review: the bag sentence is **still
in it**, and the extent phrase reads *hip* rather than *chest* — the extent is written per
reference by the pose reader, so it differs row to row.

**The crop's cost, measured.** Timed on `p021`, 684×1024:

| stage | time |
|---|---|
| MediaPipe pose landmarks | **40 ms** |
| MediaPipe Selfie Multiclass (256²) | **151 ms** |
| **BiRefNet_lite @1024²** | **48.9 s** |
| full `masks()` stack as `crops()` calls it | **121.7 s** |

**BiRefNet is the entire cost.** Everything else is rounding error, and the extra 70 s
beyond BiRefNet is the guided-filter refinement of three separate class bands.

**And a bounding box does not need any of it.** A bbox needs to know roughly where the
subject is, not where its edges are to the pixel. Pose landmarks give that in 40 ms;
Selfie Multiclass gives a subject mask in 151 ms. **Cropping to the subject is ~325×
cheaper than what is currently being run**, because what is currently being run is
computing a matte in order to throw it away.

The matte is only needed for **background removal**, which is a different operation from
cropping and has not been shown to be necessary.

**[inferred] — and this is the interesting one.** V2 rejected the cheap 256² matte because
it is *"a staircase by construction"* and klein copied the staircase into its output. **QX
regenerates.** The same argument that says a regenerative consumer may absorb `CROPH`'s cut
boundary says it may absorb a cheap matte's stair-stepped edge. If so, background removal
drops from 49 s to 151 ms. **Untested, and it is the cheapest thing left to test.**

### 3c.19 The crop-quality ladder — measured cost, and no middle rung

Six high-hair references × five preparations, one prompt (the full `p7.3`) held fixed.
30 extractions, no failures. Page: `v3/report/v31_croplad.html`.

**The intended middle arm cannot exist.** `A3` was to be BiRefNet at 512² — the same model
at a quarter of the pixels, interpolating between 151 ms and 49 s.
**`BiRefNet_lite.onnx` is exported with static 1024×1024 input dimensions** and
onnxruntime rejects any other shape. There is no resolution knob without re-exporting from
the PyTorch weights. **The real choice is sub-second or ~100 seconds, with nothing in
between.**

**Measured cost per reference**, on a 4-core machine:

| arm | preparation | CPU |
|---|---|---|
| `A0 raw` | none | — |
| `A1 bbox` | pose bounding box, background kept | **0.50 s** |
| `A2 mask256` | Selfie Multiclass 256², background removed | **0.28 s** |
| `A4 biref1024` | BiRefNet @1024², background removed | **99.3 s** |
| `A5 biref1024h` | as A4 plus head removed | **107.2 s** |

`A4` measures at 99 s here against the 48.9 s timed for BiRefNet alone in §3c.18 — the
difference is `drop_specks` and the uncached recompute. Either way it is **two orders of
magnitude** more than the cheap arms, and `A2` is the cheapest of all: background removal
via Selfie Multiclass is *faster* than a pose bounding box.

**Edge roughness** — subject contour perimeter over its own convex-hull perimeter, median
over the six:

| arm | roughness |
|---|---|
| `A2 mask256` | **1.27** |
| `A4 biref1024` | **1.24** |
| `A5 biref1024h` | 1.22 |

`A0` and `A1` read 1.00 because they keep the background: there is no silhouette to
measure, only the frame.

**The staircase measures 2% rougher than the 99-second matte.** That is the whole
observable difference by this metric.

**And that metric should not be over-read.** Perimeter over hull perimeter is dominated by
overall shape complexity rather than by fine stair-stepping, so it **under-reports exactly
the defect it is being used to look for**. It establishes that the two mattes are in the
same range; it does not establish that they are equivalent. The frames are the evidence
and they are not yet judged.

**Reviewer verdict 2026-08-27:**

- **`A2 mask256` rejected.** It *"misreads the clothes to be cropped out"* — the cheap map
  does not merely round the silhouette, it removes garment. That is a different and worse
  defect than the staircase V2 rejected it for: **V2's objection was edge quality, this is
  a segmentation error.**
- **`A5 biref1024h` rejected, and it is worse than `A4`.** Removing the head *"doesn't give
  context for hair"*. Note this **inverts the expectation** the arm was built on: the guess
  was that a regenerative consumer would absorb the cut boundary for free. It does not —
  it loses the information the head provided about how the hair sits over the garment.
- **`A1 bbox` and `A4 biref1024` are the two live options.** Running with `A4` for now.

So the outcome is neither of the two the cheap arms were hoping for. **The 99 seconds is
not obviously wasted**, and the cheap matte fails for a reason the roughness metric could
never have caught — §3c.19's own caveat about that metric under-reporting is borne out,
though not in the direction expected.

### 3c.20 The 99 seconds is a laptop artefact — and V2's "1.9 s" figure is wrong

**The machine.** Intel **Core i3-8100 @ 3.6 GHz, 4 cores / 4 threads, AVX2 only**, ONNX
Runtime 1.19.2 on `CPUExecutionProvider`. That is a 2017 entry-level desktop part. Every
timing in §3c.19 is from it.

**Would a server CPU be faster? Yes, and for three separable reasons.** **[inferred]**

1. **Cores.** 4 threads here against 32–128 on a server part. ONNX Runtime parallelises
   convolution across threads. Not linear, but a large multiple.
2. **Vector width.** The i3-8100 is AVX2 — 256-bit. Ice Lake, Sapphire Rapids and Zen 4
   have **AVX-512**, twice the FMA throughput per core per clock, and Sapphire Rapids adds
   AMX on top for quantised inference.
3. **Memory bandwidth.** A 1024² feature map through a segmentation network is
   bandwidth-bound, and server memory subsystems are far wider.

**[speculative]** A modern many-core server CPU plausibly brings 99 s to single-digit
seconds. Order of magnitude, not a measurement.

**But the real answer is that the deployment target has a GPU.** V3's constraint is a
production server running FLUX.2 klein, which requires one. **BiRefNet_lite on any modern
GPU is tens of milliseconds.** The 99 seconds is an artefact of benchmarking a GPU model on
a CPU that has no GPU path — not a property of the pipeline.

**That reframes §3c.19 entirely.** The choice between 0.28 s and 99 s is a
**development-loop problem, not a production problem.** In deployment both are sub-second
on hardware that is already there for other reasons. Cost is the wrong axis on which to
reject `A4`; **quality is the only axis that matters**, and on quality the reviewer picked
`A4`.

**[documented] — and this is a correction to V3's brief.** [`prd/v3/README.md`](../README.md)
states the CPU mask stack is *"~1.9s, no GPU, no API call"* and prices the pipeline as
"~10.6s of generation plus ~1.9s of CPU preprocessing".
[`prd/v2/LOCK.md`](../../v2/LOCK.md) repeats it.

**That figure excludes the BiRefNet inference.** Every row of
`v2/runs/crop_screen/crop_log.csv` carries the note **`birefnet_cached`**, and
`runtime_s` has a median of **0.50 s** and a maximum of 1.90 s. The 1.9 s is the
refinement stages measured **with the matte already computed and read from disk.**

The cold cost on this machine is ~49 s of inference before any of that. **The preprocessing
figure in the brief is wrong by one to two orders of magnitude**, and any latency or cost
claim resting on it needs restating — either as a GPU number, or as a cold-CPU number, but
not as the cached one.

### 3c.21 The arm, assembled and run end to end

Everything v3.1 established, run over the whole 28-pair fold so it can be compared with
BC_klein and QX on identical inputs. **28/28 through both calls, no failures.**

| stage | | cost |
|---|---|---|
| crop | `A4` — BiRefNet_lite @1024², background removed, **head kept**, cropped to subject bbox | CPU |
| read | pose → extent clause; skin → colour phrase from the **paired person**, quantised to the ten-step ladder | CPU, ~190 ms |
| extract | Qwen-Image-Edit-2511, full `p7.3` | **call 1** |
| edit | klein, the V2 AMT prompt, seed 46 | **call 2** |

**Two calls, which is the production budget.** Everything before the extraction is CPU.
Outputs at `v3/runs/v3.0b/gen/{set_id}__MQ.jpg`, beside `BC` and `QX` from the same fold;
all three arms are on `v3/report/v30b_review.html`, 84 cells.

**A note on the crops.** 21 of the 28 BiRefNet mattes were reused from the cache written by
the earlier ladder runs under different stem names, which skipped roughly 40 minutes of
inference. The cache is keyed on stem, so identical work had been done three times under
three names — worth knowing before anyone budgets CPU for a rerun.

### 3c.22 What this comparison can and cannot claim

Written before scoring, so the limits are fixed in advance rather than discovered in the
reading.

**Can claim:** whether the v3.1 arm, as a whole, beats BC_klein and QX on the same 28
pairs at the same seed with the same edit prompt.

**Cannot claim, and this is the one that matters:** **which half of the arm is responsible.**
BC and QX were run on the **raw** reference path; MQ runs on the **A4 crop**. MQ therefore
differs from them in two ways at once — the crop *and* the extraction prompt. A win belongs
to the arm, not to either component. Separating them needs a fourth arm — MQ's prompt on an
uncropped reference — at 28 more calls.

**Also open at the moment of running:**

1. **Nothing in v3.1 has been tier-scored.** Every verdict so far — the prompt ladder, the
   colour ladder, the crop ladder — was by eye against a named defect. That was the right
   way to iterate and it is not a number.
2. **An eight-reference probe cohort drove nearly every decision.** This run is the first
   time those choices meet the full fold, and a choice that was right for eight references
   chosen for their defects need not be right for twenty-eight.
3. **The blank-terminations defect (§3b.3) was parked behind the framing fix and never
   re-checked.** The framing fix landed; nobody looked at whether the feet resolved.
4. **Accessories will drop inconsistently**, by decision (§3c.9).
5. **`p7.3.1exact` was never judged**, and the minimal prompt is cheaper on fidelity than
   the full one. Moot while the full prompt ships, but it is an open loop.
6. **n = 28, one seed, one reviewer, unblinded.** The standing debt, unchanged since V2.

### 3c.22b The scored result — MQ leads

First tier-scored data in v3.1. Reviewer pass over the 84-cell grid, exported to
`v30b_review.csv`. **80 of 84 cells marked**; four MQ cells left blank (pairs 8, 9, 25,
26), so the comparison below is over the **24 pairs where all three arms are scored.**

| arm | perfect | ok | fail | perfect rate |
|---|---|---|---|---|
| BC_klein | 19 | 5 | 0 | 79% |
| QX | 14 | 7 | 3 | 58% |
| **MQ** | **22** | **0** | 2 | **92%** |

Head-to-head on the same 24 pairs:

| | better | worse | tie |
|---|---|---|---|
| MQ vs BC | 3 | 2 | 19 |
| **MQ vs QX** | **9** | 1 | 14 |
| BC vs QX | 10 | 3 | 11 |

**MQ has the highest perfect rate and no `ok` at all** — it is either right or it is
broken, where BC degrades gracefully through five `ok`s and never fails. That shape
matters for a production choice: BC's floor is higher, MQ's ceiling is higher.

**`p019+g011` is the only pair no arm gets perfect** — BC `ok`, QX `fail`, MQ `fail`.

**Read the head-to-head before the rate.** MQ beats BC on 3 pairs and loses on 2, with 19
ties. **On this evidence MQ is not clearly better than BC** — the perfect-rate gap of 13
points rests on a net of one pair. Against QX the margin is real: 9 better, 1 worse.

And the standing confound in §3c.22 applies to all of it: MQ ran on the A4 crop while BC
and QX ran raw, so any part of this belongs to the arm and not to the mannequin prompt.

### 3c.23 First review of the assembled arm

Reviewer pass over the 28-pair grid, 2026-08-28. Not tier-scored — named observations.

**Improvements attributed to the arm:**

| pair | person | what got better |
|---|---|---|
| 10 | `p010` | the belly region of the design is corrected |
| 19 | `p019` | **improvement over QX**, which returned only a sweater; MQ transfers the dress |
| 22 | `p022` | no shirt where there should not be one |
| 28 | `p028` | the entire outfit transfers |
| 6 | `p006` | correct shoes |

Four of those five are the things the mannequin was built to fix — completeness,
footwear, and not inventing a layer. `p019` is worth separating: **the arm improves the
transfer and damages the person in the same frame**, which is why it appears in both
lists.

**Two failures: `p019` and `p021` morph the individual into the clothes.**

### 3c.24 The pose hypothesis — I tested the wrong pose, and it holds for `p021`

**Correction.** The proposal was about **the mannequin's pose**. I tested the *subject's*
pose against `test_set3`'s tags and reported that the hypothesis failed. That answered a
question nobody asked.

**Re-checked against the mannequin references themselves:**

| reference | outcome | mannequin stance |
|---|---|---|
| **`g013`** | **MQ fail — "extra leg"** | **stepping stance: one leg forward, one behind, a sandalled foot visible** |
| `g011` | MQ fail — morph | upright, feet together, neutral |
| `g014` | perfect | upright, neutral |
| `g030` | perfect | upright, neutral |
| `zendaya` | perfect | upright, neutral |

**On `g013` the hypothesis is right and the mechanism is direct.** The mannequin is in a
contrapposto stride with a forward leg, and the output has **an extra leg** — the
reviewer's own note. A non-neutral mannequin gives the edit a second leg position to
reconcile, and it reconciles by keeping both.

**On `g011` it does not apply** — that mannequin is upright and neutral, and its failure
is the colour one in §3c.25.

So the two MQ failures have **two different causes**, and only one is pose:

- `p021+g013` — **mannequin stance.** Fixable by asking for a neutral stance in the
  extraction prompt, which is a positive instruction and therefore the safe kind.
- `p019+g011` — **colour**, below.

**Superseded.** The subject-pose table that stood here is withdrawn: `sitting` appearing
on both sides was a true observation about an irrelevant variable.

### 3c.24b The subject-pose table, withdrawn

The proposed cause was that the mannequin is in a non-neutral pose and should be upright.
Checked against the `pose` tags in `test_set3/manifest.csv`:

| person | pose | outcome |
|---|---|---|
| `p019` | **side_profile** | morph |
| `p021` | sitting | morph |
| `p022` | **sitting** | better |
| `p010` | arms_crossed | better |
| `p028` | arms_raised | better |
| `p006` | neutral_standing | better |

**`sitting` appears on both sides**, and `arms_crossed` and `arms_raised` are both wins.
Non-neutral pose is **not sufficient** to explain the failures.

Two qualifications, because the hypothesis is not dead:

1. **`side_profile` is unique to `p019`** and appears nowhere among the wins. n = 1, so it
   is a candidate rather than a finding.
2. **It is the *person's* pose that varies here, not the mannequin's.** The mannequins in
   both failing references are upright and neutral — that was checked. If the pose that
   matters is the person's, the intervention is not "make the mannequin upright" but
   something on the person side, and the arm has no person-side stage.

### 3c.25 `p019`'s colour: the read is right and the render is not

Traced end to end.

**The measurement is defensible.** The face mask is clean — inspected directly, no bleed
onto the beige turtleneck collar sitting under her chin, which was the obvious suspect.
14,582 face pixels, L\* median 69, measured `#D49C83`. Warm, because the photograph is
warmly lit and the mask spans both the lit and shadowed sides of a three-quarter face.

**The word is right too.** L\* 69 quantises to **`dark beige skin`**, whose ladder swatch
is `#D3AF8B` at **L\* 74** — close to the measurement.

**The render is not.** The mannequin in `g011__MQ.jpg` measures **L\* 51** in the head
region: **23 points darker than the swatch its own word names.** That is the discrepancy
the review spotted, and it is downstream of everything the reader does.

> **The ladder's words were never calibrated against what the model renders.** §3c.7
> established that the reader picks a sensible word and §3c.6 that the word stays on the
> mannequin. **Neither checked that the model renders the word at the lightness the word
> means.** `g013` renders `light brown skin` at L\* 49 against a swatch of 50 — accurate.
> `g011` is 23 points out. The mapping is not uniformly wrong, which is worse than if it
> were: it cannot be corrected by an offset.

**And this is what causes `p019`'s morph.** A mannequin far darker than the wearer, under
a black dress, transferred onto a pale elderly woman: her arms come back in a mid-brown
that is neither her skin nor her coat. **The mannequin's tone leaked into the person** —
the same class of failure as §3c.3's colour bleed, one stage further down the pipeline.

**Reviewer's correction, and it is the better description:** `p019` is **not** a profile
problem. It is a **texture mix-up between the mannequin's skin and the original person's
clothing** — the beige coat and the mid-brown mannequin arm are close enough in value that
the edit resolves them into one surface. That is the low-amplitude boundary of
[§3.4](../INVESTIGATION.md#34-why-p023-specifically-amplitude-not-contrast) once more,
and it is the third time it has appeared: first between a nude garment and bare skin, then
between a white garment and a white mannequin, now between a beige coat and a brown
mannequin.

**The rule that keeps being violated:** the mannequin's colour is chosen against the
*person's face* and never checked against **anything else in either image.** It was
flagged as unbuilt when the colour design was written and it is still unbuilt.

**A separate problem on `p021`, noted while checking.** Its face mask is also clean, but
L\* runs from 20 at the 10th percentile to 72 at the 90th — half the face is in shadow.
The median of 49 is pulled up by the lit side and quantises to `light brown skin`, which
is **lighter than the person actually is**. So the two failures are not the same failure:
`p019` is a render that ignores a correct word, `p021` is a word that a bimodal
lighting distribution made wrong. **The median survives shadow better than the mean; it
does not survive a face that is half-lit.**

**Neither has a fix yet.** Both are recorded before any is attempted.

### 3c.26 How the skin colour is actually grabbed

Asked directly, so written out exactly.

```
person photograph
  └─ MediaPipe Selfie Multiclass, 256×256, CPU, 149 ms
       └─ FACE class at confidence > 0.6          ← face only, no fallback
            └─ every pixel in that mask → L*a*b*
                 └─ MEDIAN of each channel independently
                      └─ nearest ladder step BY L* ALONE
                           └─ the word, e.g. "dark beige skin"
                                └─ concatenated into the prompt
```

**It is a median, not an average.** The median is the middle value: half the face pixels
are lighter, half darker. A mean would be dragged by a specular highlight on the nose or a
dark shadow under the jaw; the median ignores both, because moving an extreme value does
not move the middle one. That choice is why a hard-lit face still reads sensibly.

**Only L\* picks the word.** `a` and `b` — the colour axes — are measured, recorded, and
**not used to choose.** The ladder is a lightness ladder. So a warm face and a cool face of
the same lightness get the same word, and the measured hex that would distinguish them is
kept only for the audit. **[inferred]** This is defensible for skin, which varies far more
in lightness than in hue, but it has never been tested.

**The hex never reaches the model.** It exists only so the mapping can be checked.
`p7.2` established that a chromatic word bleeds into the garment and that binding it with
*"skin"* stops it; nothing suggested a hex code would be read at all.

**And it is measured on the face of a whole photograph** — 5,000 to 15,000 pixels out of
roughly a million, typically 0.5% to 2% of the frame. It is a small, specific sample, which
is the point, and also the reason a half-lit face breaks it (§3c.25).

**The body-skin fallback is removed** (2026-08-28). It fired on 1 of 56 images and
substituted a different surface while reporting it identically. The reader now returns
nothing instead; `p016` is the one image that now has no read.

### 3c.27 Colour through klein — the test that should have come first

**Every colour experiment so far compared references.** `p7.2`, `p7.2b` and `p7.2b+`
produced **120 colour variants on disk, none of which had ever been through an edit.** The
reader, the ladder and the calibration work in §3c.25 all rest on a premise that was never
checked: that the mannequin's colour changes the *output*.

Six references × five colours, both calls each, colour word the only variable.
30 extractions + 30 edits, no failures. Page: `v3/report/v31_colour_klein.html`.

Arms: `matched` (what ships), `white` (the old default), `grey` (achromatic and
**person-independent**), `black`, and `opposite` — the ladder step furthest in lightness
from matched, included **so that a null result cannot be dismissed as two similar colours
being compared.**

**Not scored.** The reading is fixed in advance:

- **Five columns indistinguishable** → the whole colour apparatus is machinery attached to
  something that does not affect the product, and collapses to one fixed word. **The
  largest simplification available to v3.1.**
- **`grey` ≈ `matched`** → the reader is unnecessary; keep the colour, drop the person
  dependency.
- **`matched` clearly best** → the reader earns its place, and the calibration defect in
  §3c.25 becomes worth fixing rather than worth deleting.
- **`opposite` visibly worse** → colour matters and lightness is the axis it matters on.

### 3c.28 The colour word does not only set colour — it decides what kind of object is rendered

Reviewer findings on the colour-through-klein run, 2026-08-28, with the mechanism checked
against the references.

**1. Mannequin colour matters.** Reviewer: *"if they are similar it reduces attention
deficit or chance of fucking it up."* The premise the reader was built on survives the
test it should have had first.

**2. Mannequin pose matters, and the colour word controls it.** Reviewer: *"in g013 the
black and grey models are neutral but the others have movement — the movement ones have an
extra leg sticking out."* Checked directly across `g013`'s five colours:

| word | what came back |
|---|---|
| `light brown skin` (matched) | **a person's legs** — visible skin, sandals, mid-stride |
| `pale skin` (opposite) | organic legs, slight asymmetry |
| `white skin` | neutral mannequin, feet together |
| `grey` | neutral mannequin, feet together |
| `black skin` | neutral mannequin, feet together |

**The mechanism is naming, not colour.** *"grey mannequin"*, *"white mannequin"* and
*"black mannequin"* all name **plausible mannequin materials** — the model renders an
object. *"Light brown skin mannequin"* names something that does not exist as a
manufactured object, so the model renders **a person**. And people have poses; objects
stand still.

That is the same rule as everywhere else in this investigation, one level up:
**the model does exactly what the words permit.** A mid-tone skin word permits a human,
and a human brings a stride, a weight shift and a second leg position for the edit to
reconcile. `p021`'s "extra leg" is downstream of a colour word.

**3. White is the wrong default.** Reviewer: *"best not white because it will mix with the
clothing too much."* That is the low-amplitude boundary again — the failure mode that has
now appeared four times (nude on skin, white garment on white form, beige coat on brown
arm, and this).

**Where that leaves the colour design.** `grey` and `black` satisfy every constraint found
so far at once:

| constraint | source | `grey`/`black` |
|---|---|---|
| does not bleed into the garment | §3c.3 | achromatic — passes |
| does not merge with a pale garment | above | non-white — passes |
| renders a neutral, static pose | above | names a material, not a person — passes |
| needs no reader, no ladder, no calibration | §3c.26 | person-independent — passes |

**This is a strong argument for deleting the entire colour apparatus and fixing one
achromatic word.** It is not yet the conclusion: nobody has checked whether a grey
mannequin under a *grey* garment reintroduces the merge that white does under a white one,
and `black` under the black suit is the same question. **The reader's remaining
justification would be exactly that case** — picking an achromatic value that contrasts
with *the garment*, which is what §3c.25 said the rule should have been all along, and
which needs no face at all.

**4. `g011` is not solved by colour.** Reviewer: *"I don't know why the skin texture is so
strange."* Confirmed unexplained. Colour was the leading hypothesis in §3c.25 and the
colour sweep does not fix it, so that hypothesis is **weakened, not confirmed**. Open, with
no candidate cause.

### 3c.29 The klein prompt, unchanged since V2

Asked directly. Call 2 uses the V2 AMT prompt verbatim and **V3 has never varied it**:

> Dress the person in image 1 in the clothing shown in image 2. Keep the person's face,
> identity, body and the background exactly as they are.

Endpoint `fal-ai/flux-2/klein/4b/distilled/edit`, seed 46, 4 steps, guidance 1.0.

**Two things worth noticing now rather than later.** It says *"keep the person's … body …
exactly as they are"* — which is precisely the instruction the morph failures violate, so
the failing cases are already being told not to do the thing they do. And **every prompt
experiment in v3.1 has been on call 1.** Call 2 has been a constant since V2, which makes
it the largest untouched surface in the pipeline.

### 3c.30 A pose word fixes the stride — and quietly overrides the extent clause

Two phrasings appended to the full prompt, on the four references whose matched colour
rendered a moving figure. **A positive instruction naming what is wanted**, which is the
form that has worked throughout.

| reference | no pose word | `+ neutral upright pose, feet together` |
|---|---|---|
| **`g013`** | **stride, legs apart, sandalled foot forward** | **feet together, neutral, headless form** |
| `g014` | legs slightly apart | feet together |
| `g011` | already neutral | unchanged |
| `g030` | already neutral | unchanged |

**It works, and it costs eight words.** `g013` — the reference behind the "extra leg"
failure — comes back neutral. Both phrasings behave the same; *"stands straight and faces
forward, weight even on both feet"* is not better than *"neutral upright pose, feet
together"*.

**A side effect worth catching before it becomes a mystery.** On `g030` the pose sentence
also **changed the framing**: without it the mannequin was cropped near the waist, with it
the full length including the skirt appears. *"Feet together"* implies feet are in frame,
which contradicts an extent clause that says to cut above them. **Two clauses in the same
prompt now disagree about how much body to show**, and the pose clause wins.

That is a real interaction and it means the pose word is not free: it can silently undo
`p7.1.3`, which was the fix for the invention defect. **Either the pose phrasing has to
avoid naming feet, or the two clauses have to be written as one.** Not yet done.

### 3c.31 `g011`'s cooked texture — it is neither the person nor the prompt

Three questions, separated so the answer names a stage.

| test | what was run | result |
|---|---|---|
| **B1 — is it the person?** | klein on `p019` **alone**, text-only clothing edits, **no reference at all** | **clean.** Black tee, red dress, blue shirt — all with natural arm skin |
| **B2 — is it the reference?** | klein on `p019` with **other** mannequin references | `g014` (sleeveless blue dress) **cooks**. `g030` (long-sleeved gold jacket) is **fine** |
| **B3 — is it the prompt?** | `p019` + `g011`, four different edit instructions including one that explicitly says the person's skin tone and texture are unchanged | **all four cook.** The prompt is not a lever |

**The pattern is sleeves.** Every reference that leaves the arms bare cooks; the one that
covers them does not. And it is not the person — without a reference, klein renders her
arms perfectly well.

**The mechanism, and it is V2's own finding inverted.** `p019` wears a **long-sleeved
coat**. Her arms have never been observed — those pixels do not exist in the input. A
sleeveless garment demands arm skin the photograph never contained.

> V2: *"subtraction cannot recover a garment region that hair was covering — the pixels
> were never observed."*
>
> Here: **the edit cannot recover skin that clothing was covering.** Same missing-pixel
> problem, on the person's side instead of the garment's.

**And the reference decides what fills the gap.** Given no reference (B1), klein invents
plausible skin from its prior and gets it right. Given a reference (B2, B3), it fills from
the nearest available content in the attention sequence — **the mannequin's arms** — which
is a manufactured surface in a colour chosen from her face. The result is skin-shaped, the
wrong tone, and the wrong texture. That is
[§3.1's mechanism](../INVESTIGATION.md#31-image-2-is-not-conditioning-it-is-clean-tokens-in-the-same-attention-sequence)
operating on a region the prompt never mentions.

**Why colour did not fix it (§3c.28).** The mannequin's tone is a *secondary* cue. The
primary problem is that information is missing, and changing the colour of the thing being
copied from does not stop it being copied from.

**What this predicts, and it is testable:** the defect should appear whenever
**target garment exposes a region the source photograph covered** — bare arms under long
sleeves, bare legs under trousers, an open neckline under a high collar. It is a property
of the *pairing*, not of either image, and **nothing in the pipeline currently detects
it.** The CPU stack knows what the garment reference shows; it does not know what the
person's photograph hides.

### 3c.32 Dynamic prompting — one read, one table, both clauses

The extent and pose clauses were written separately and **contradicted each other**
(§3c.30): a fixed pose sentence naming *"feet together"* told the model feet were in frame
while the extent clause told it to cut above them, and the pose clause won.

**They now come from one table keyed on the framing read**, so they cannot disagree by
construction. `FRAME_CLAUSE` in `v3/build/skin_tone.py`:

| framing read | extent | pose |
|---|---|---|
| `chest_up` | head to the chest only, cut off below the chest | upright and square to the camera, shoulders level |
| `waist_up` | head to the hip only, cut off below the hip | upright and square to the camera, shoulders level |
| `knee_up` | head to the knee only, cut off below the knee | neutral upright, **legs** together, facing forward |
| `full_body` | the whole mannequin, head to feet | neutral upright, **feet** together, facing forward |
| `unknown` | only the part the photograph shows | upright and square to the camera |

**The rule that makes them consistent: never name a body part the crop excludes.** Below
the hip there are no feet to put together, so neutrality is expressed with something still
in frame. That is the whole schema, and it is why the pose column changes with the category
instead of being a constant.

**How the framing is decided**, since it drives both halves: MediaPipe Pose Landmarker on
the crop, 36 ms CPU, reporting which joints are **confident and inside the frame** —
shoulder → hip → knee → ankle. Ankle present is `full_body`; knee without ankle is
`knee_up`; hip without knee is `waist_up`; shoulders only is `chest_up`. It reads a
coordinate the detector already returns, which is a much weaker question than the eight
head-detection heuristics V2 burned through trying to *locate* a boundary.

**Run:** 8 references chosen to cover **every category the reader produces** — 3
`waist_up`, 1 `chest_up`, 1 `knee_up`, 3 `full_body` — so the schema is exercised rather
than sampled. 8 extractions + 8 edits, no failures. Page: `v3/report/v31_dynamic.html`,
showing crop → previous reference → new reference → klein output.

**Distribution over the 28 A4 crops**, which is why this matters beyond the probe:
`full_body` 19, `waist_up` 7, `knee_up` 1, `chest_up` 1. **Nine of 28 are cropped**, so
the clause that must not mention feet fires on a third of the set.

**Not scored.**

### 3c.33 `g011` — parked

The cooked-texture case is **out of scope for now**, by decision. The diagnosis stands and
is worth keeping because it generalises past this reference: the defect fires whenever the
target garment exposes a region the source photograph covered, it is a property of the
*pairing*, and **nothing in the pipeline detects it** (§3c.31). Parked, not solved.

### 3c.8 The two fixes have not been combined

`p7.1.3` carries a framing clause and **no colour word**. `p7.2b` and `p7.2b+` carry a
colour word and **no framing clause**. Verified against the prompts as sent, not from
memory.

That is deliberate — one variable at a time — but it means **nothing yet exists that has
both fixes**, and the combination is not entailed by the two results separately.

**Both components are now accepted on their own**: `p7.1.3` for framing, `p7.2b+` for
colour. Their combination is **`p7.3`**, and it is the first thing in this investigation
that should go through a klein edit — everything so far is a reference, and a better
reference is not yet a better try-on.

## 4. Measurements that are not trustworthy yet

- **The mannequin lightness figure is inflated by the mannequin.** The form renders light
  grey, which is not white enough to be excluded by the 244 threshold, so the statistics
  count it as garment. V2's finding that the mannequin prompt "makes it pale and simple"
  may be measuring the form rather than the clothing. **Do not quote a mannequin `dL`
  until it is re-measured with the form masked out.**
- **Drift against the raw photograph is meaningless** and was computed that way first: the
  statistics run over non-white pixels, so against a raw frame they compare the garment to
  the whole scene and return ~90 lightness drift for every shape. The baseline of record
  is the subtractive crop.
- **Nothing here is tier-scored.** n = 28, one seed, one reviewer, unblinded.

## 5. Next

The three arms are generated and side by side on `v3/report/v31_arms_vs.html`. What is
missing is the scoring, and `EXPERIMENT.md` — which should be written against what the
scoring says, not before it.
