# ADR-0009: The Todd corpus as first-class metadata (todd_refs)

- **Status**: Accepted (2026-09-19)
- **Scope**: how Ediz's OCR compilation of Todd's metrics (todd_core.csv)
  enters the repo; what makes the `todd_core` flag evidence-backed; how
  the corpus is emitted to the dist
- **Depends on**: ADR-0003 (board taxonomy — Todd/Extra as views over one
  pipeline), ADR-0008 (the Todd board's canonical layer)

## Context

Since the project's first week, the "Todd board" has been defined by a
hand-curated list of metrics (10 drafted in conversation, refined to the
six indicators built by v12). The selection rationale lived in
conversation and in `docs/emmanuel_todd.md` — defensible, but not
*checkable*, and not *weighted*: nothing in the repo could say how much
a metric matters to Todd's work, or what to build next.

In September 2026 Ediz delivered the compilation: `todd_core.csv`, an
OCR-derived census of every metric Todd uses across his 16 books
(1976-2024), one row per metric x book, with a citation count — 117
rows, 24 distinct metrics, 483 citations. It is the corpus the project
was implicitly working from all along, now explicit. The question this
ADR answers: how does an external, evolving, human-authored CSV become
an executable part of the pipeline without losing its provenance and
without the repo silently overriding it (or it overriding the repo)?

## Decision

1. **The CSV stays outside the repo and is never modified by it.** It is
   Ediz's source of truth. The repo carries a one-way transform:
   `scripts/normalize_todd_refs.py` reads the CSV and writes the
   generated `config/todd_refs.yaml` (deterministic: same CSV bytes ->
   same YAML bytes; the CSV's SHA-256 rides the meta block so every
   regeneration is tied to an exact upstream vintage).
2. **The transform validates loudly.** Duplicate (metric, book) rows,
   non-integer citation counts, unparseable book years and exact family
   ties are refused (an OCR artifact is resolved in the CSV, never
   averaged over). The one tolerated inconsistency — the compilation
   labels a handful of rows' `family` by book context (e.g.
   consanguineous marriage is `demography` in *Le Destin des immigrés*
   but `society` elsewhere) — is resolved by citation-weighted majority
   and *printed as a disagreement* at regeneration, never silently.
3. **The CSV's `status` column is deliberately ignored.**
   Implemented-ness is the repo's own state, derived by
   `cross_validate_todd_core` against `config/indicators/*.yaml` — a
   stale flag in the compilation must never override the config's truth.
4. **The `todd_core` flag becomes evidence-backed (the bijection).** An
   indicator flagged `todd_core: true` MUST have a corpus entry with the
   same id (the flag now cites its source); a corpus metric sharing an
   indicator's id MUST find `todd_core: true` (an implemented corpus
   metric is Todd-core by construction). Violations fail config load —
   the same fail-loudly contract as every other config rule. New
   indicators implementing corpus metrics keep the corpus's metric id
   verbatim (suicide_rate is suicide_rate in both).
5. **The dist emits the corpus in two shapes, both additive**: a
   `todd_refs` block on every indicator (and catalog entry) whose id
   joins a corpus metric — books, citation totals, per-book usage — and
   a new `dist/todd_corpus.json` carrying ALL metrics, implemented AND
   unimplemented, ranked by the corpus's own citation weight: the
   executable roadmap ("what to build next" becomes a data statement,
   e.g. birth_rate_fertility 111 citations, 16/16 books, unimplemented).
6. **`cli stats` closes with the corpus block** (implemented share +
   citation-weighted backlog), and every Todd-core indicator line
   carries its citations/books — numbers quoted in changelogs stay
   emitted by command.

## Consequences

**Positive**: the board's membership stops being a preference; the
cross-validation makes the todd_core flag checkable against the
compilation; the corpus ranking gives the roadmap an objective order;
regenerating after an upstream CSV update is one command with a
deterministic diff.

**Negative (accepted)**: the bijection makes `todd_core: true` a
breaking flag to set without corpus backing (deliberate: that is the
point); the corpus's metric ids become a naming constraint on future
indicators (the join is by id); a CSV update that *removes* a metric
behind a todd_core indicator will fail the build until either the flag
or the CSV is fixed — loud, per the project's contract.

**Neutral**: the family vocabulary of the corpus (society / mortality /
economy / demography / markers / education) is wider than the Indicator
schema's Family enum; it stays a free string at the corpus level and is
narrowed only when a metric becomes an indicator.
