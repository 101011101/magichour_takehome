# PROD — taking `ER` to production

Written 2026-09-11. This folder is the handoff for the system v3.8 locked — `ER`: klein bald
pass → head-subtracting crop → klein edit with the *replace* verb. The evidence and the full
build specification stay where they were made, in `prd/v3/v3.8/`; this folder holds what is
needed to hand the system to the people building the product around it, and the ledger of
what has and has not been confirmed.

## The files

| file | what it is | changes when |
|---|---|---|
| `README.md` | this map | a file is added or its role changes |
| [`SKELETON.md`](SKELETON.md) | the skeletal structure: the system's parts, its input/output contract, what is exposed and what is fixed, and the section layout of the production Colab | the design changes |
| [`TICKET.md`](TICKET.md) | the Linear ticket, **content only** — built field by field with Ray, from `SKELETON.md` and `BUILD.md` | a field is filled or corrected |
| [`TICKET_TEMPLATE.md`](TICKET_TEMPLATE.md) | the ticket template and three past tickets, verbatim — the format to follow | never; it is a record |
| [`TODO.md`](TODO.md) | Runbo's brief, verbatim; the ledger of every inquiry with its status and where its evidence is; the work left | an inquiry closes or work lands |
| [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) | inquiries still open — what is known, the evidence, what would close each | a question opens or closes |

**The code** lives in [`vp/`](../../vp/README.md) at the repo root — the production
counterpart of `v1/`–`v3/` — starting with the production Colab, `vp/tryon_er.ipynb`.

## Rules

1. **Cite, do not restate.** Numbers live as evidence in `prd/v3/` and `v3/`. The one
   exception is `TICKET.md`, which is written for a reader outside the project; every value
   in it traces to a row of `TODO.md` → *Ticket sources*.
2. **An inquiry is closed only when its evidence is in the tree.** It moves from
   `OPEN_QUESTIONS.md` to the ledger in `TODO.md` with the path that closes it.
3. **Decisions are dated and attributed** (Ray, Runbo), so a later reader can tell a
   measurement from a choice.

## Where the depth is

- [`prd/v3/v3.8/BUILD.md`](../v3/v3.8/BUILD.md) — every weight, revision, setting, rule and
  acceptance test.
- [`prd/v3/v3.8/SOLUTION.md`](../v3/v3.8/SOLUTION.md) — the architecture and why each stage
  is there.
- [`prd/v3/v3.8/RESULTS.md`](../v3/v3.8/RESULTS.md) — the numbers.
