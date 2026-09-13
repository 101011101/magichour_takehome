# v3.15 — EXPERIMENT

**Status: run 2026-09-13 — 42 of 44; one defect found and fixed; re-run pending.** Matrix and
pass rules in [TEST.md](TEST.md); cases, numbers and the fix in [RESULTS.md](RESULTS.md).

## The question

Does **the production notebook itself** — `vp/tryon_er.ipynb`, the file attached to the ticket —
behave as specified when run end to end on a GPU with a region set?

Every piece of it was proven somewhere else first: the region selector in v3.11, the head gate
in v3.13, the product-shot route in the inquiry run. Each was then ported into the production
notebook and verified by compiling it and checking the logic without a GPU. **The ported code
has never executed on a GPU.** That is the gap this closes.

## The rule under test

Ray's formulation: the head gate decides whether a garment goes through the balding pipeline,
and that is what lets upper and lower work.

- **A photo with a person in it** → the gate finds a head → bald pass → head crop → the band cut
  at the hip applies (or falls back, with a reason) → call 2 is sent the sentence naming the half.
- **A product shot** → no head → **no bald pass**, a matte-only reference → the region is
  **forced to full** → call 2 is sent the whole-outfit sentence. Asking for upper or lower here must
  degrade gracefully: never crash, never cut.

## How the shipped code is tested without copying it

The notebook carries no pipeline of its own. At run time it resolves the commit in which
`vp/tryon_er.ipynb` last changed, fetches that exact file, records its sha256, and executes the
file's own **Install, Downloads, Inputs, Load and Pipeline** cells — found by their markdown titles,
unmodified. It skips only the shipped Run and Output cells, because they wait for a browser upload,
and instead calls the shipped `load_image`, `prepare_garment` and `try_on` exactly as those cells do.

The single addition is a pass-through recorder on `klein`, rebound in the namespace the shipped
functions resolve it from. It changes no argument and no return value; it notes which prompt went
in, which is how the test knows whether a bald pass ran and which call-2 sentence was sent. If
the production notebook is restructured so its section titles no longer match, the test stops
rather than guessing.

## Established before the run

Verified locally with the shipped Pipeline cell executed for real and only the model boundaries
stubbed (`klein`, the matte, the gate's segmenter, the head crop):

- the section extraction finds all eight sections in the current production notebook;
- no name the harness defines collides with a name the shipped cells define, other than the
  intended `klein` rebind — and the shipped Inputs cell's `SEED = None` is why the harness seed is
  `TEST_SEED`;
- all 44 cases run and pass under stubs that behave correctly, and the product shots' second region
  is served from the shipped cache as designed, giving the expected 54 klein calls;
- the judge fails each case it exists to catch: a bald pass on a product shot, a product shot cut
  instead of forced to full, the gate seeing a person on a product shot, a worn garment silently
  treated as full, and a call-2 sentence that does not match the applied region.

**One behaviour worth knowing before the run**, surfaced by the harness rather than assumed: on a
product shot the shipped garment record reads `requested: "full"`, not the region the user asked
for. The forcing is visible through `route: "product"` and the Output cell's message, but the
original request is not kept in the record. The test notes it on every product case rather than
failing it, since nothing downstream depends on that field.

## What the run will and will not show

It shows whether the shipped code runs and routes correctly on a GPU — behaviour. It is not a
quality measurement: nothing is marked, and no failure rate comes out of it.
