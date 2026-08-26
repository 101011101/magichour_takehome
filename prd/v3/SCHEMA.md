# V3 document schema

Written 2026-08-26. This file is the contract for how V3's documents are laid out and
what each one is allowed to contain. It exists so that anyone — or any agent — picking
up V3 mid-flight can add to it without guessing, and so that a document cannot quietly
turn into a different kind of document.

V2 grew organically and ended with fifteen top-level files whose boundaries were
learned rather than stated. V3 states them first.

---

## 1. The layout

```
prd/v3/
├── README.md            MAIN — the question, the constraint, the goals
├── SCHEMA.md            this file
├── INVESTIGATION.md     GENERAL — the shared diagnosis, and the map of sub-investigations
├── SOLUTION.md          FINAL — the assembled architecture (written last)
│
├── v3.0/
│   ├── EXPERIMENT.md    what is investigated + how → result → next
│   ├── RESULTS.md       every case, every number, the analysis methodology
│   └── SOLUTION.md      the architecture this investigation yielded, if any
├── v3.1/  same three
└── v3.x/  …
```

Code, evidence bundles and generated pages live in [`v3/`](../../v3/README.md), not
here. `prd/v3/` is prose and decisions; `v3/` is artefacts and the scripts that build
them. The numbering is shared: an investigation `v3.1` puts its runs in
`v3/runs/v3.1/` and its pages at `v3/report/v3.1_*.html`.

## 2. What each document is, and is not

### `README.md` — the main document

The question V3 is answering, the constraint it is answering it under, what is being
tackled, and the index of everything below.

- **Contains:** the objective, the production constraint, the baseline to beat, the
  measurement protocol, inherited debts, and a status table linking every other
  document.
- **Never contains:** findings, per-case detail, or the argument for a solution. If a
  number appears here it is a *target* or a *baseline*, not a result.

### `INVESTIGATION.md` — the general investigation

The diagnosis every sub-investigation stands on: what is actually wrong, at the level
of mechanism, and therefore what the sub-investigations are. It is the document that
turns "V3's job is the four failures" into a set of separable questions.

- **Contains:** the failure taxonomy, the mechanism shared across failures, the
  evidence paths, corrections to the inherited record, and the map of which `v3.x`
  owns which question.
- **Never contains:** the outcome of any sub-investigation. It defines them; it does
  not report them. When a `v3.x` lands, this file gains a link, not a result.

### `v3.x/EXPERIMENT.md` — one sub-investigation

One behaviour, investigated in isolation. The body is a **chain**, and the chain is the
schema:

> **What is investigated** → **how** → **result** → **next: what is investigated** →
> **how** → **result** → …

Each link states the question, the method that answers it, and what came back — then
what that outcome made worth asking next. The chain is the honest record of how the
investigation actually moved, including the links that went nowhere.

- **Contains:** post-synthesis conclusions only. The evaluated, concluded form of each
  result — one or two sentences and the headline number.
- **Never contains:** per-case tables, individual outputs, raw metrics, or the
  methodology of the analysis. Every link in the chain **links to the relevant section
  of its `RESULTS.md`** for those.
- **Ends with:** a conclusion, and a statement of whether the investigation yielded a
  solution. If it did, `SOLUTION.md` exists. If it did not, say so — a negative result
  is a result and it stays in the tree.

### `v3.x/RESULTS.md` — the evidence layer

Everything the experiment document is not allowed to carry.

- **Contains:** the specific cases, per-case verdicts and numbers, the methodology of
  the analysis (what was measured, how, with what instrument, at what threshold),
  evidence paths into `v3/`, and the failure modes of the measurements themselves.
- **Never contains:** the decision. It reports what was observed and how it was
  established; what to do about it belongs in `EXPERIMENT.md`.
- **Verbose by design.** This is the document a sceptic reads.

### `v3.x/SOLUTION.md` — what to build, if anything

Written only when an investigation yields something worth assembling.

- **Contains:** the architecture, and why it works. Enough that it can be built later
  without re-reading the investigation.
- **Never contains:** the argument that established it. It **links** to
  `EXPERIMENT.md` and `RESULTS.md` for the evidence rather than restating it.
- **Assumes nothing about the others.** Each is self-isolated, so two solutions can be
  read independently and composed — or one dropped — without unpicking the other.

### `SOLUTION.md` — the final document

The culmination: the assembled architecture, built from the `v3.x` solutions that
landed, under the one-model two-call constraint.

- **Contains:** the shipped shape, the call budget, the measured cost and latency, and
  a link to each contributing `v3.x/SOLUTION.md`.
- **Never contains:** investigation narrative. If a reader wants to know *why* a
  component is there, the link takes them to it.

## 3. Rules that hold across all of them

1. **A number appears in exactly one place as evidence.** Everywhere else it is a
   citation. If a figure is quoted in two documents and later corrected, it will be
   corrected in one of them.
2. **Cite the file, not the memory.** Every claim that rests on data names the CSV,
   run directory or image path it came from. Paths are repo-relative.
3. **Withdrawn numbers are struck, not deleted.** V2 kept a list of figures that turned
   out to be wrong and it is one of the more useful things in it. Same practice here.
4. **A measurement that fails is reported.** An instrument that turned out to carry no
   signal belongs in `RESULTS.md` alongside the ones that worked — it tells the next
   person not to try it.
5. **Sub-investigations are self-isolated.** A `v3.x` may cite `INVESTIGATION.md` and
   its own files. It should not depend on another `v3.x` having happened; if two
   genuinely interlock, that is one investigation, not two.
6. **Status is stated, not implied.** Every `v3.x` says at its top whether it is open,
   concluded, or abandoned, and every conclusion says whether it yielded a solution.

## 4. Provenance for external work

Where an investigation rests on research rather than on runs — published mechanisms,
model documentation, prior art — claims are labelled **[documented]** with a source
URL, **[inferred]**, or **[speculative]**, and the labels survive into whichever
document quotes them. V2's most expensive mistakes were reasoning that read like
measurement; the labels are there to keep the two apart.
