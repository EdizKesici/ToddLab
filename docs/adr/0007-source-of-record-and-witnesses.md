# ADR-0007: Source-of-record per layer, witnesses, and the curation gate

- **Status**: Accepted (2026-09-06); the wiring deferred in decision 5
  was completed the same day by ADR-0008 (un_dyb + curated are now
  infant_mortality's canonical sources)
- **Scope**: sourcing strategy for every indicator; connector roadmap
- **Formalizes**: §3 (layer model) and §7 (collector tier) of
  `docs/the-measurement-problem.md`

## Context

After the layer analysis, the practical question remained: if every
harmonized source (OWID included) smooths the signals the Todd method
reads, and the "real" figures live in national publications, does ToddLab
have to scrape 193 national statistical offices — and wouldn't stitching
several sources together be "bricolage" (patchwork engineering)?

Live investigation during this audit (details and artifacts in the
CHANGELOG, 2026-09-06 entry):

1. **No universal "raw" database exists, or can exist.** "Raw" is a rank in
   a production chain (register → national publication → international
   collection → harmonization → derivative), not a property of a database.
   Every rank makes documented choices; a "universal raw base" would be a
   base without choices — a contradiction.
2. **The collector tier already does the per-country work.** The UN
   Demographic Yearbook republishes national official vital statistics *as
   reported* (~230 areas, since 1948); the WHO Mortality Database does the
   same for causes of death by ICD revision; UN IGME publishes the inputs
   behind its child-mortality estimates; HMD co-publishes raw counts,
   methods protocol, and constructed series. Scraping national sites
   ourselves would rebuild the UNSD's job with a fraction of its staff.
3. **The founding tracer has an institutional carrier.** DYB 1978, Table
   15, USSR row: 125,908 infant deaths / 27.7‰ for 1974 (the official
   series — not the IGME plateau), footnote 33 spelling out the Soviet
   live-birth definition, blank cells from 1975 on (the publication
   blackout). Value, definition, and gap preserved in one collector row.
4. **Precedent: tiered sourcing is the industry pattern.** HMD (3
   co-published layers), IGME (inputs + estimates), OWID (multi-source ETL
   with per-chart provenance) all do exactly this. The difference between
   architecture and bricolage is not the number of sources — it is the
   formalization: declared layers, per-point provenance, deterministic
   fusion rules, a written decision record. This ADR is that record.

## Decision

1. **Three-tier sourcing model** (operationalizing the L0-L4 stack):
   - **curated** (L0-L2): small hand-entered tables, one citation per
     point, committed in git (`catalog/curated/*.csv` with `entity_id,
     year, value, citation, definition_note`);
   - **collectors** (L1-collector): national official figures as reported
     by an international collector — DYB (implemented as `un_dyb`), WHO
     Mortality Database, UN IGME inputs, HMD/HCD (planned);
   - **harmonized** (L3): IGME/GHE/UNODC/WPP model estimates — the
     comparability backbone;
   - derivatives (L4) without documented provenance stay rejected
     (Macrotrends, Statista).
2. **Source-of-record per layer.** Each indicator declares its canonical
   source *per layer*; the merge layer arbitrates duplicate (entity, year)
   points *within one layer family only* (the existing `priority` field).
   Cross-layer series are **witnesses**: stored, validated, displayed
   beside the canonical series as divergence — never merged into it, never
   averaged with it.
3. **Curation gate.** A curated point may enter the catalog only if all
   three hold: (a) a `todd_ref` demands it (the claim the data must carry);
   (b) the distortion vs the collector/harmonized layer is demonstrated
   and documented; (c) a citable source exists for the point. The curated
   set is therefore finite, enumerable, and reviewable in pull requests —
   the anti-bricolage guarantee.
4. **Collector holes are data.** Reporting gaps (e.g. Russia, the US,
   China, the UK absent from DYB Table 15 2024) appear in coverage maps as
   "not reported to collector", with the named alternative route (HMD,
   national office) — never silently patched from another layer.
5. **`un_dyb` now, wiring later.** The DYB connector is implemented,
   tested (16 tests) and verified against the live 2024 Table 15 (755
   records, 90 countries with rates, France 2020-2024 exact). It is
   registered in the connector registry but deliberately **not referenced
   by any indicator config yet**: wiring it as `infant_mortality`'s
   witness source requires per-point unit conversion first (DYB is
   per-1,000; the OWID chart is a percentage — the exact trap the earlier
   unit bug came from). Prototyping ahead of wiring follows the same
   discipline as the phase-2 worldbank/gho connectors. *(Wired the same
   day, with the unit conversion implemented, as canonical source #2 —
   see ADR-0008.)*

## Consequences

**Positive**

- The Todd board can read official-as-reported series without scraping a
  single national site; the founding tracer has a citable institutional
  carrier (plus the curated series from the digitized yearbooks).
- Comparability (L3) vs authenticity (L1) becomes a user-visible choice
  per board, instead of a hidden mix inside one series.
- Curation stays a bounded, citable, PR-reviewable set — tens of points,
  not thousands.
- Collector quality codes, footnotes and gaps become design inputs for
  the per-point provenance extension, not surprises.

**Negative / costs (accepted)**

- Phase-2 schema work: `layer`/`role` fields on sources, witness
  semantics in merge + build, per-point provenance (quality codes,
  footnotes), and a unit-conversion lookup per source (never a guessed
  factor).
- Collector coverage holes force per-indicator alternative routes (HMD
  for Russia, national offices for the US/UK) — documented work, not free.
- More connectors to maintain: UN SpreadsheetML layouts (already
  version-fragile: the parser derives positions from the merged year
  header, and raises loudly on layout drift), WHO per-part files, HMD
  authentication.

**Neutral**

- Raw collector snapshots stay gitignored (Option A); curated CSVs are
  committed as text, reviewed like code.

## References

- `docs/the-measurement-problem.md` §3 (layers), §7 (collector tier +
  paradigm case), §7.2 (consequences)
- CHANGELOG 2026-09-06 (live verifications: DYB 1978 Table 15, DYB 2024
  Table 15 end-to-end, WHO Mortality Database inventory, IGME portal,
  HMD/HCD)
- Precedents: HMD Methods Protocol; UN IGME "estimates and the data used
  to derive them"; OWID per-chart provenance model.
- Numbering note: ADR-0001..0006 are reserved for decisions already taken
  and recorded in the CHANGELOG (see `docs/adr/README.md`).
