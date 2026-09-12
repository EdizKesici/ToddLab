# catalog/curated/ — the curated tier (L0-L2)

Small hand-entered tables, one citation per point, committed in git and
reviewed like code. This directory implements the `curated` source type
decided in `docs/adr/0007-source-of-record-and-witnesses.md` and wired as
the canonical tier of the Todd board by
`docs/adr/0008-todd-board-canonical-layer.md`.

## Why this tier exists

The Todd method reads signals that harmonized (L3) sources smooth away by
design — and some of those signals live in official or scholarly series
that no machine-readable collector redistributes today. The curated tier
is the honest answer to that gap: enter the point, cite the point, and
make every entry individually reviewable in a pull request. It is the
opposite of scraping-and-stitching: a bounded, enumerable, auditable set.

## The curation gate (mandatory, ADR-0007 condition 3)

A point may enter a curated table only if **all three** hold:

1. **a `todd_ref` demands it** — the claim (from Todd's work or the
   project's brief) that the data must carry;
2. **the distortion is demonstrated** — the divergence vs the
   collector/harmonized layer is documented (not assumed);
3. **a citable source exists** — enforced mechanically: the connector
   (`src/connectors/curated.py`) rejects any row with an empty
   `citation` column.

If a point fails any condition, it does not enter — the gap stays
visible in the coverage report instead.

## File format

One CSV per series, named exactly as the `source_ref` used in
`config/indicators/*.yaml` (e.g. `ussr_infant_mortality_official.csv`):

    entity_id,year,value,citation,definition_note

- `entity_id` — OUR canonical id from `config/entities.yaml` (resolution
  happens by exact id; a typo surfaces in `{indicator}.unresolved.json`).
- `value` — in the indicator's canonical unit; **a gap is an absent row**,
  never an empty cell (we only enter points we can cite).
- duplicate `(entity_id, year)` rows are rejected by the parser: the
  curated tier must be arbitration-free by construction.
- `definition_note` carries the comparability caveat that travels to the
  dist next to the value (e.g. the Soviet live-birth definition).

## Current series

### `ussr_infant_mortality_official.csv` — the founding tracer

The official Soviet infant-mortality series (per-1,000 live births,
Soviet definition), 1970-1990, 21 points. This is the series at the
heart of `docs/the-measurement-problem.md` §1: the rise 22.9‰ (1971) →
peak 31.4‰ (1976) that UN IGME re-models into a 21.9‰ plateau.

**Gate check for this series:**

- (a) `todd_ref`: THE founding claim — Todd read this series *as
  published* (plus the 1976+ blackout itself) as a hard signal of
  systemic decomposition when writing *La Chute finale* (1976).
- (b) distortion demonstrated: IGME family (OWID `infant-mortality`) shows
  a flat 21.9‰ plateau for 1974-1978 where the official series shows
  27.9 → 30.6‰; documented in the-measurement-problem.md §1, verified
  during this project's live audits.
- (c) citable sources: see the per-row `citation` column.

**Provenance and cross-checks (all verified during this project's
audits, September 2026):**

- Primary compilation: the Kalabekov-style compilation of TsSU/
  Goskomstat yearbook series (su90.ru/death.html, tables [3]/[7]) — the
  "as-published family" for 1970-1974, the retrospective series (released
  late 1980s) for 1975-1990.
- Institutional carrier for 1974: **UN Demographic Yearbook 1978, Table
  15** — 125,908 infant deaths, footnote 33 spelling out the Soviet
  live-birth definition, blank cells from 1975 on (the blackout, preserved
  by the collector). Note the 27.9 (official series) vs 27.7 (DYB) nuance
  for 1974: the DYB republishes the death *count* as reported but
  recomputes the *rate* on its own births denominator — a mini-lesson in
  reading collectors carefully, recorded on the 1974 row itself.
- Arithmetic cross-check: republic-level data (IMR + births by republic,
  Narkhoz *Za 70 let* 1987) re-aggregated as
  Σ(deaths)/Σ(births) reproduces the official union figures within
  rounding — 24.66 vs 24.7 (1970), 27.26 vs 27.3 (1980), and matching
  1985/1986 points. Artifacts: `scripts/` analysis from the September
  2026 session.
- Literature anchors: Davis & Feshbach (1980, Series P-95) for the
  as-published 1970s series; Kingkade & Arriaga (1997) for the
  retrospective series; the peak 31.4‰ (1976) matches the value quoted
  in the project's founding analysis.

**Deliberately NOT done here:** no attempt to convert the series to the
WHO live-birth definition (that is an L2 scholarly reconstruction —
Anderson & Silver, Andreev-Darski-Kharkova — a separate curated series
if ever needed, with its own citations); no interpolation of anything;
the 1976-87 publication blackout is carried per-row in
`definition_note` rather than papered over.

## Adding a new curated series

1. Check the gate (all three conditions — write them in the PR).
2. Add `catalog/curated/{name}.csv` with the exact column format above.
3. Reference it in the indicator's `sources` with
   `provider: curated, ref: {name}` (and `role`/`unit` per ADR-0008).
4. The connector, snapshot, normalize, merge and dist plumbing is
   already generic — no code change needed.
