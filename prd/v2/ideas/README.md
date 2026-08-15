# Ideas — proposals not yet committed to a workstream

Design proposals and candidate features. Nothing here is scheduled or measured;
an idea graduates by being adopted into a workstream (`../v2.1`, `../v2.2`,
`../v2.3`), where it gets an experiment, a plan, a test and results.

| Doc | What it is | Feeds |
|---|---|---|
| [INTENTION_AWARE_FIDELITY.md](INTENTION_AWARE_FIDELITY.md) | Deterministic post-generation guardrail: register + normalize the candidate, decompose the scene semantically, group changed pixels into regions, score each region as `accept` / `restore` / `repair`, composite through a gradient acceptance map. No new trained models. | **v2.2** (protecting face/hands/background from accidental regeneration) and **v2.3** (the `repair` band and seam-only repair) |
| [TRY_APPROACH_ITERATIVE_IMAGE_TEXT_EDITING.md](TRY_APPROACH_ITERATIVE_IMAGE_TEXT_EDITING.md) | An alternative generation approach: convert the garment image into a structured text spec, edit image+text instead of image+image, then loop — evaluate, and either retry from the original or repair a local crop. **Depends on the guardrail above**, which it uses as its preservation stage. | **v2.2** (attention: text avoids a second image competing for reference tokens) and **v2.3** (local-crop repair) |
| [POTENTIAL_FEATURES.md](POTENTIAL_FEATURES.md) | Three unscheduled features: (1) garment image cropper — production path, segment + white fill + tight crop; (2) quick VLM gross-failure check — evals only; (3) predicted-warp garment fidelity metric — evals only, distinguishes a transferred garment from a hallucinated lookalike. | **v2.2** (all three: 1 attacks attention leakage directly, 2 reduces failures, 3 measures accuracy) |

## Notes

- The first two docs are one coherent proposal, not independent ideas: the
  iterative approach references the guardrail as a required component.
- POTENTIAL_FEATURES §1 (garment cropper) is the idea most directly aimed at a
  measured weakness — klein's attention leakage on `duo` pairs, where the
  garment reference is a whole person. It is specced with a mandated fallback
  chain and a "done when" bar, so it is ready to adopt.
- These docs predate the klein decision (V2.1) and the bucket split
  (SCORING_CRITERIA), so their model references may be stale. The mechanisms are
  the durable part; re-check any named model against `CONDITIONS.md` before
  building.
