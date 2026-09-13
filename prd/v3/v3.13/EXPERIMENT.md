# v3.13 — EXPERIMENT

**Status: open — measured locally, awaiting its confirming run.** One question: **what should
the person-gate test?** Post-synthesis conclusions only, per [SCHEMA.md](../SCHEMA.md); the
per-image detail is `v3/report/v313.html` and `meta/v313_measurements.json`.

---

## Why this arm

v3.12 established that a garment photograph with no person in it must not reach the bald pass:
there is no head to remove, and klein **invents a wearer** instead. Measured there — the hip
read fires on **1 of 10** uploaded product shots but **6 of 10** of their bald frames. So
production gained a gate that runs on the upload, before call 1.

The gate shipped testing for a **face** — Selfie Multiclass's `FACE` channel at ≥500 px, which
is `v3lib.tone`'s own test — with the Pose nose landmark as a tie-break. Ray asked the obvious
question: **a face is small in a full-body photograph, so should the gate look for a head?**

## The chain

### 1 — Does a face test have enough margin? **← landed, no**

**How.** Every candidate over 73 photographs whose answer is known from
`test_set1/manifest.csv`: 56 with a person wearing the garment, 17 flat-lay or ghost-mannequin.
→ [TEST.md](TEST.md)

**Result. It is one image from failing, and the failure is the dangerous kind.** `FACE` alone
misses **p016**, a genuinely worn garment measuring **469 face pixels** — 31 short of the
threshold. A miss in that direction sends a worn garment down the route that never removes its
wearer's head. The nose tie-break exists to catch exactly this, and it does, which is why the
gate as shipped is not wrong; but the face half of it is deciding on a 6% margin.

### 2 — Does the nose tie-break cost anything? **← landed, yes**

**Result.** It buys p016 and pays for **g010**, a ghost-mannequin tee whose hollow shoulders
read as a nose at **0.96 confidence**. So the shipped gate is right on 72 of 73 and wrong on a
flat-lay — the safe direction, since that image simply keeps today's behaviour.

### 3 — Is a head better than a face? **← landed, and it is the answer**

**Result. `FACE + HAIR` ≥ 500 px is right on all 73.** It fixes both known errors at once: p016
scores **1,622 px** once hair counts, and g010 scores **0** because there is no head on it to
find. It needs no pose call at all, so it is simpler and cheaper than the gate it replaces —
one measurement from one model, no tie-break.

**And the margin is the point, not the score.** The two classes are three orders apart, not
adjacent: the highest-scoring person-free photograph reaches **138 px**, the lowest worn
photograph **1,622 px**. The 500 px threshold sits in a gap of **11.8×** with nothing in it.
`FACE` alone has no such gap — p016 at 469 px sits below the line it is supposed to clear.

### 4 — Would the parser's head class do it? **← landed, no, and it answers a standing worry**

**How.** SCHP's ATR head classes (hat, hair, sunglasses, face) as a share of everything the
parser labels, ≥2%.

**Result. It is the worst of the six, and it is wrong in the dangerous direction on nothing but
in the safe direction twice** — `g006` and `g019` are flat-lays it paints a head onto. The
standing worry it settles is real but smaller than feared: `phase3_variants` records that ATR's
face class *bleeds down the body on bald frames*, and the question was whether it also
hallucinates a head on a hanging garment. It does, on 2 of 17 — median head fraction on
person-free photographs is **0.000**, so it is not systematic, but it is not clean either.

---

## Conclusion

*Reached locally; the confirming run is `v3/colab/v313_gate.ipynb`.* **The gate should test for a
head, as `FACE + HAIR` ≥ 500 px.** It is right on all 73 photographs, it drops the pose call the
current gate needs, and its threshold sits in an 11.8× gap rather than on a 6% margin.

**What this does not establish.** 73 photographs from one project's test sets are not a
distribution of what customers upload. The gap is wide enough that the threshold is not
delicate, but nothing here measures a hoodie photographed head-on with the hood up, a garment
shot from behind, or a mannequin with a sculpted head — that last is the case most likely to
score like a person, and none of the 17 is one.

**A second lesson, carried from v3.12.** A landmark is not evidence of a body: `g010` produces a
nose at 0.96 confidence on a photograph containing no person. Confidence is a statement about
the model's own output, not about the world.
