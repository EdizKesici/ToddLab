# ADR-0008: The Todd board's canonical layer is the as-reported tier
(Technique A)

- **Status**: Accepted (2026-09-06)
- **Scope**: which sourcing layer feeds an indicator's canonical series;
  the dist contract; unit policy
- **Supersedes**: the open question §6.1 of
  `docs/the-measurement-problem.md` (closed by this ADR)
- **Depends on**: ADR-0007 (three-tier model, witnesses, curation gate)

## Context

ADR-0007 left one decision explicitly open: for the Todd board — the one
whose purpose is reading anomalies in hard indicators — which layer is
**canonical** (the series the board actually displays as "the" data), and
which layer rides as witness?

Two options were on the table (asked as "Technique A vs B"):

- **Technique A (as-reported first)**: canonical = curated (L0-L2) +
  collectors (L1-collector, e.g. UN DYB as reported); harmonized (L3,
  e.g. UN IGME via OWID) as witness.
- **Technique B (status quo)**: canonical = harmonized L3; curated and
  collector series as witnesses around it.

The decision was made by the project owner in conversation, with a
rationale this ADR records because it is the correct articulation of the
project's whole point:

> "A is more logical — with B, we fall back into the same smoothing
> problem."

With B, the canonical series remains the re-modeled, definition-adjusted
L3 output: the layer whose documented *purpose* is to erase exactly the
definitional breaks and publication-gap signals the Todd method reads.
Witnesses would then only ever *measure* the distortion — never remove it
from the board's primary reading. The divergence display would be an
admission of permanent defeat rather than a choice.

## Decision

1. **Technique A.** For `todd_core` indicators (the Todd board), the
   canonical series is the **as-reported tier**: curated sources
   (priority within the tier by `priority`) plus collectors. Harmonized
   sources are **witnesses**: stored, validated, displayed beside the
   canonical series as divergence — never merged into it, never averaged
   with it (ADR-0007 decision 2).
2. **The Extra board reads the same dist, differently.** Comparability
   vs authenticity is a per-board *display* choice, not two pipelines:
   the dist carries both series, so the Extra board can show the
   harmonized witness as its main series with the as-reported series as
   the authenticity witness. One dataset, two readings.
3. **Canonical unit = per-1,000 for infant mortality** (the field's
   native unit: DYB, official series and IGME all publish per-1,000; the
   OWID chart is the outlier in percent). Each source declares its
   native `unit` in the indicator config; normalize converts through the
   declared `UNIT_CONVERSIONS` table — never a guessed factor — so the
   conversion burden sits on the *witness* (x10), not on every
   as-reported source. The phase-1 percentage declaration was a
   single-source stopgap, always marked "to fix in phase 2".
4. **Per-point provenance is part of the canonical contract.** A
   canonical series that is multi-source by construction (curated +
   collectors) must label every point with its `provider`/`source_ref`,
   and curated points additionally with `citation`/`definition_note`
   (the curation gate's condition (c), mechanically enforced by the
   connector). The anti-bricolage guarantee is reviewable per point.
5. **Witness gaps and holes are data.** Witness points with `value=None`
   ("reported to the collector, no rate computed", e.g. DYB quality-"U"
   rows) are kept as explicit gap points; collector holes (Russia, US,
   China, UK absent from DYB Table 15 2024) leave the canonical series
   honestly absent for those entities, with the witness carrying the
   harmonized series meanwhile — the coverage report shows both facts.

## Implementation (v6)

- `SourceRole` (canonical/witness) + `SourceRef.role` and
  `SourceRef.unit` in the indicator schema; `Provider.curated` +
  `PROVIDER_LAYER` (curated / collector / harmonized).
- `src/connectors/curated.py` + `catalog/curated/` (first series:
  `ussr_infant_mortality_official`, 21 points 1970-1990, the founding
  tracer) — strict parser, curation gate enforced, no network.
- `normalize`: declared unit conversions (the old
  `NotImplementedError` stub is now a real lookup); raw snapshots move
  to a per-`source_ref` directory so several sources of the same
  provider can coexist (the DYB editions loop).
- `merge`: canonical arbitration (within tier, by priority, logged) +
  witness series construction (per-source, gap-preserving, duplicate
  reductions logged).
- `build`: dist v2 — `sources` (role + layer + native unit),
  per-point provenance on `data`, `witnesses` block with converted
  values.
- `config/indicators/infant_mortality.yaml`: curated (canonical, p1) +
  un_dyb 2024/table15 (canonical, p2) + owid (witness, p3, percent
  native). `entities.yaml`: 12 `source_ids.un_dyb` name overrides
  verified against the live 2024 table (144/145 names resolve;
  "Saint Helena ex. dep." deliberately left unresolved — sub-territory
  granularity is an open mapping question, visible in
  `infant_mortality.unresolved.json`).

Live-verified on the real data: canonical USSR 1974 = 27.9‰ (curated,
cited; DYB 1978 institutional carrier on the row) vs witness Russia
1974 = 21.91‰ (IGME, converted to per-1,000) — the founding §1
divergence is now carried by the data layer itself.

## Consequences

**Positive**

- The Todd board reads official-as-reported series as its primary data;
  the founding tracer (USSR 1970-1990, +27% rise, 1976 peak, blackout
  notes) is finally *representable* — it enters through a cited,
  PR-reviewable table, not through any smoothing pipeline.
- The smoothing problem is not "detected and lamented" — it is
  structurally displaced out of the canonical path.
- The divergence display (canonical rise vs witness plateau) becomes
  the board's core feature, with both series in one file and one unit.

**Negative / costs (accepted)**

- Canonical coverage for infant mortality is now honest but partial:
  ~90 countries (2020-2024, DYB rates for C/"|" completeness) + the
  USSR tracer; the 1991-2019 as-reported gap and the four big
  questionnaire holes await the DYB editions loop (2014-2023 tables)
  and the HMD/national routes. The Extra board keeps near-global
  coverage via the witness.
- Two series per indicator in the dist: the frontend contract grows
  (roles, layers, native units, per-point provenance). Breaking change
  vs v5's `sources_used`/single-series format — documented in the
  CHANGELOG; no frontend exists yet.
- The canonical unit change (percent -> per-1,000) rescales every
  published infant-mortality value by x10 — deliberate, documented, and
  the price of putting the conversion where the outlier is.

**Neutral**

- Priorities remain unique per indicator but only arbitrate within the
  canonical tier; a witness's priority is inert ordering information.

## References

- ADR-0007 (three-tier sourcing, witnesses, curation gate)
- `docs/the-measurement-problem.md` §1 (the founding case), §5, §6
  (questions now closed), §7.2
- `catalog/curated/README.md` (gate, provenance, cross-checks for the
  USSR series)
- CHANGELOG 2026-09-06, v6 entry (implementation + live verification)

---

2026-10-09 — HMD is dropped: Ediz will not create an account. The
"the HMD/national routes" phrase in the negative-costs list above is
retired as to HMD — the infant-mortality gap it named still awaits the
DYB editions loop and the national-office routes, which are unchanged;
HCD is unchanged. See ADR-0007's same-day note for the full
retirement.
