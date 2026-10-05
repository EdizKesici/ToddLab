# Architecture Decision Records

One file per significant, hard-to-reverse decision: context, decision,
consequences. Written *before* the consequences arrive, so future changes
of mind can be argued against the recorded reasoning instead of folklore.

## Numbering

**ADR-0007 is the first ADR written as an ADR.** Numbers 0001-0006 are
reserved for decisions that were already taken during the conversation and
are recorded in `CHANGELOG.md`. They can be backfilled into full ADRs if
they ever need revisiting:

| Reserved | Decision (where it lives today) |
|---|---|
| 0001 | Storage Option A: `data/dist` committed, `data/raw` + `data/processed` + `reports/` gitignored (CHANGELOG 2026-09-04) |
| 0002 | English-only labels: `label_fr` dropped from schema and configs (CHANGELOG 2026-09-04) |
| 0003 | Board taxonomy: "Todd" and "Extra" as curated views over one pipeline, not separate datasets (conversation; `docs/emmanuel_todd.md`) |
| 0004 | Ex-Soviet republics keep continuous series across 1991 + `formerly_part_of` warning instead of a fabricated USSR series (CHANGELOG 2026-09-03, "USSR tracer resolved") |
| 0005 | Snapshot selection by parsed timestamp, never lexical filename sort (CHANGELOG 2026-09-03, live-audit fix) |
| 0006 | `homicide_rate` source selection: `homicide-rate-unodc` + `field` for the multi-variable CSV (CHANGELOG 2026-09-04) |

## Register

| ADR | Title | Status |
|---|---|---|
| [0007](0007-source-of-record-and-witnesses.md) | Source-of-record per layer, witnesses, and the curation gate | Accepted (2026-09-06) |
| [0008](0008-todd-board-canonical-layer.md) | The Todd board's canonical layer is the as-reported tier (Technique A) | Accepted (2026-09-06) |
| [0009](0009-todd-corpus-as-first-class-metadata.md) | The Todd corpus as first-class metadata (todd_refs) | Accepted (2026-09-19) |
| [0010](0010-bilateral-faces-parallel-never-merged.md) | The two bilateral faces (birth / citizenship) are parallel layers, never merged | Moot since v26 (the faces' only indicator withdrawn; the discipline lives on in the segment layers) |
| [0011](0011-score-layer-derived-composites.md) | The score layer: two derived composites (official / modelled), frozen bounds, never merged | Accepted (v27) — the project's first and only derived product; the indicator layer untouched but for decision 10's direction flip |

## Format

```markdown
# ADR-NNNN: <short title>

- **Status**: Proposed | Accepted | Superseded by ADR-MMMM
- **Scope**: what this decision constrains
- <one-paragraph context: the question, the verified facts>

## Decision
1. <numbered, testable statements>

## Consequences
**Positive** / **Negative (accepted)** / **Neutral**
```

ADRs cite their evidence (live audits, docs, CHANGELOG entries) rather
than restating it. They are never deleted: superseding an ADR means
writing a new one that references it.
