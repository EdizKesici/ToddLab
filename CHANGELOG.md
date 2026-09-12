# Changelog

All notable changes to this repo are listed here, most recent first. Free-
form, suited to tracking an in-progress conversational project rather than
formal Git version tags.

House rules (adopted with v8; past entries are vintages — never edited
after the fact, corrections land in a new entry):
- An entry carries a vX label if and only if that delivery produced a
  reviewable artifact (zip/patch); otherwise it is date-only.
- Recurring sections: Context (the why, incl. decisions taken in
  conversation), Investigated (live findings that justify the change),
  Added, Changed, Fixed, Verified (live numbers, frozen at delivery
  time), Known limitations. One-off named sections are allowed when an
  entry carries a distinct sub-project (e.g. the P1b spike).
- Contract-breaking changes get a bold "Breaking" line right under the
  entry title; additive contract changes are noted as such in Verified.
- The numbers in an entry are frozen at delivery time (docs/
  the-measurement-problem.md carries the current state).

## 2026-09-11 — v8: the collector's own voice (P2): DYB quality codes,
footnote texts and LE reference ranges end-to-end; witness citations;
homicide two-tier via the OECD/WHO Mortality Database route (P3); LICENSE

**Breaking — dist contract v3 (additive): every `sources[]` entry and every
`witnesses[]` entry now carries a full citation block (`citation`, `url`,
`license`); points may carry `quality_code`, `footnote_refs`,
`reference_range`, `missing_marker`, `provisional` when the source prints
them; `sources[]` entries may carry a `footnotes` block (legend + the texts
of the refs the emitted points actually use). No field is removed — a v2
consumer ignores the new fields safely.**

### Context
The v7 external review (approved) left five accepted notes; two of them
were this delivery's mandate, agreed in conversation: (1) the collector's
quality annotations — the DYB's codes, footnotes and LE reference ranges —
were parsed away, kept in the source file one snapshot away; (2)
homicide_rate was still the review's standing gap, mono-OWID with no
canonical/witness treatment. The other three notes map to later phases
(WB/GHO stubs = P5, the metrics/predictions workstream = separate layer,
HMD = P4 gated) and a LICENSE file was missing entirely.

### Investigated (live, 2026-09-11)
- Where the DYB's quality annotations physically live, verified against
  every cached edition (2011-2024, both file families): the row quality
  code in the column right of the residence label (C, U, |, +C, +U, ... —
  the "+" prefix = tabulated by registration date rather than occurrence);
  per-value footnote refs and the "*" provisional flag in the columns
  immediately right of each value cell; the footnote TEXTS and the code
  legend on a second worksheet ("Footnotes") of every file.
- The Table 4 Roman numerals next to the LE values are NOT footnote refs:
  legend b says they are the WIDTH OF THE REFERENCE PERIOD ("a reference
  year of 2005 and a range of V years means the reference period is
  2001-2005") — 580 real canonical LE points carry one, the modal value
  III (a 3-year period). A Todd-relevant as-reported nuance: an LE "2012"
  with range III was computed over 2010-2012.
- The BIFF editions glue footnote digits to the bilingual names — the
  digits can ride the FRENCH part ("Algeria - Algérie1", "Norfolk Island
  - Île Norfolk128"): captured from the raw string's end, whichever part
  they sit on.
- The WHO Mortality Database itself has no documented public API: the
  platform.who.int/mortality portal is a JS app with obfuscated endpoints
  (its api/mdb route 404s; the widget bundles are compiled WebResource
  blobs), the classic who.int/healthinfo bulk paths are dead, the dthub
  gateway is DNS-dead. GHO's homicide indicators (VIOLENCE_HOMICIDERATE)
  are literally named "Estimates of ..." — harmonized tier, not a
  collector. The OECD "Causes of mortality" dataflow (DSD_HEALTH_STAT@
  DF_COM) redistributes the WHO MDB over a clean public SDMX REST API
  (no key): that is the route wired here. Verified against it live:
  21,898 assault rows, 49 countries (incl. RUS, CHN, BRA, ZAF, IND),
  1960-2024, sexes _T/M/F.
- The DF_COM dataflow carries TWO methodologies for the same keys
  (CALC_METHODOLOGY): CRUDE and age-standardized STANDARD — Russia 1994
  male reads 52.5 crude vs 63.3 standardized. Standardization adjusts
  for age structure: a derived comparability measure, not the as-reported
  rate. The connector pins CRUDE.

### Added
- The DYB quality annotations ride RawRecord -> NormalizedPoint ->
  MergedPoint -> dist, as-reported and never interpreted:
  `quality_code` (row code), `footnote_refs` (country-, row- and
  cell-level, reading order), `reference_range` (Table 4's Roman numeral
  — LE only), `missing_marker` (which of "..."/"-" was printed where the
  value is absent), `provisional` ("*"). Table 4 LE points deliberately
  carry NO quality_code: the C/U/| codes on that table describe the
  births/deaths/infant-deaths columns, and attaching them to the LE
  columns would be an interpretation.
- The Footnotes worksheet is extracted into the snapshot (`footnotes`
  block: legend + numbered texts, both file grammars: SpreadsheetML
  'marker\ntext' cells and BIFF 'marker text'), and the dist joins, per
  source, the texts of the refs the emitted points actually carry —
  e.g. Armenia's IMR 2017 carries ref 19 whose text ships beside it
  ("Excluding infants born alive of less than 28 weeks' gestation...",
  the Armenian live-birth definition — the as-reported nuance the project
  exists to surface).
- Citation blocks on EVERY source (the review's witness-citation gap):
  `citation` (PROVIDER_CITATION in src/schema/indicator.py — e.g.
  "United Nations Statistics Division, Demographic Yearbook 2024, Table
  15"), `url` (the real fetch URL), `license` — in `sources[]` AND on
  each `witnesses[]` entry.
- The OECD DF_COM connector (src/connectors/oecd.py): SDMX REST,
  13-dimension key with everything pinned except REF_AREA and SEX;
  CALC_METHODOLOGY pinned to CRUDE; attribute-only CSV rows (no
  TIME_PERIOD) skipped as metadata residue; REF_AREA rides iso3_raw
  (it IS an ISO3) so entity resolution goes through the ISO3-first path.
- homicide_rate two-tier (P3): canonical = OECD DF_COM Assault
  (CICDHOCD) — WHO Mortality Database registrations as submitted;
  witness = UNODC via OWID (criminal-justice + imputation). The two
  count homicide DIFFERENTLY — the divergence is signal to display.
  Canonical carries the sex split end-to-end like life_expectancy.
- LICENSE (MIT) — the repo had docs/licenses.md (data-source licences)
  but no licence for the code itself.
- 23 tests over the new surface (marker grammar, both footnote
  grammars, the French-part digits, the dist joins, the OECD connector,
  the homicide two-tier): 130/130.

### Verified (live, full pipeline)
- Fetch: 29 snapshots, 0 failures (12 DYB editions x 2 tables + curated
  + 3 OWID + 1 OECD). Rebuild clean.
- infant_mortality 1419 canonical points (v7: 1419 — unchanged);
  life_expectancy 3018 (v7: 3018 — unchanged); homicide_rate 7193
  canonical points, 46 entities, 1960-2024, sex-split (2426 _T / 2387
  male / 2380 female) — v7: 0 canonical.
- Real as-reported payload spot-checks: Armenia IMR 2017 = 8.25, code C,
  fn 19 joined to its text; Russia LE 2012 male 64.56 vs female 75.86
  (the 11.3-year sex gap, canonical); Russia homicide 1994 crisis peak
  male 52.5 vs female 14.3 crude as-reported; Russia 2019 homicide
  canonical (vital registration, crude) 4.9 vs UNODC witness 7.6 — a
  real collector-vs-compilation divergence now displayable.
- Colombia 1991-93 (158-163 per 100k, the Escobar-era peak as the
  registrar counted it) tripped the old 150 bound: kept in the dist on
  purpose, the bound widened to 200 with the reason commented in the
  config (the safety net reports, it does not censor).

### Known limitations
- The DYB footnotes block ships only the notes referenced by emitted
  points: a ref with no text in the snapshot's sheet is logged and kept
  as an explicit null (never silently dropped).
- The OECD/WHO-MDB homicide canonical covers 49 countries (OECD + key
  partners): NOT near-global; Russia ends 2019 (the WHO MDB's own lag).
  2020+ Russia is witness-only — a divergence to display, not a gap to
  patch. The age-standardized rates are deliberately not fetched.
- P3's second half (DYB Table 17, maternal mortality as a NEW indicator)
  is deliberately NOT in this delivery: it needs its own layout probe,
  parser and indicator config — v9 scope, not smuggled in half-done.
- The italic-print convention (incomplete-registration caveat in the
  DYB's printed tables) is not carried: the XLS files carry no
  machine-readable italics flag, and the C/U/| code column is its
  equivalent.

## 2026-09-06 — v7: the edition loop (P1): 12 DYB editions wired, 2007-2024 as-reported; life_expectancy two-tier with the sex dimension; P1b PDF spike

### Context
The P1 plan (agreed in conversation after the review of the multi-entity
coverage): wire the DYB edition loop so the canonical as-reported tier
covers more than the 2024 window, and give life_expectancy the same
two-tier treatment as infant_mortality. The loop's promised scope was
"editions 2014-2023"; live probing found both less and more (see below).
P1b ran in parallel: a one-edition PDF spike measuring whether a PDF-era
connector is viable at all.

### Investigated (live, 2026-09-06)
- The per-table XLS files exist for editions 2011-2024, but in THREE
  different shapes: 2011-2014 on the legacy site
  (/unsd/demographic/products/dyb/dyb{ed}/Table{NN}.xls) as SpreadsheetML;
  2016/2017/2021-2023 on the modern site as BINARY BIFF .xls; 2018-2020 +
  2024 as SpreadsheetML. All three shapes verified by parsing the actual
  downloaded files.
- Edition 2015: the index page's per-table links are dead (HTML 404) —
  PDF-only edition; build_url() refuses "2015/..." loudly.
- Edition 2016: the files are FILEPASS-encrypted (RC4; msoffcrypto-tool
  confirms it is not the empty password) — a broken artifact of that era
  of the site. Not wired; zero coverage loss (2012-2016 covered by
  editions 2014 + 2017).
- BIFF-era quirks normalized on ingestion: years/counts as floats
  (2018.0), footnote references glued to country names ("Botswana2") and
  to residence labels ("Total11"), '\xa0' footnote cells.
- The SpreadsheetML year-header row places years via a first ss:Index +
  MergeAcross pairs: row extraction now honours merge spans (a latent
  positional bug for any row whose cells rely on implicit positions).

### Added
- `parse_dyb()` dispatch: the connector now decides HOW to parse from the
  file's OWN title (self-describing), cross-checked against the
  configured table number — a "2024/table15" ref pointing at a file whose
  title says table 4 raises instead of mis-parsing. Tables wired: 15
  (infant deaths + IMR) and 4 (vital statistics summary + life
  expectancy at birth).
- Table 4 parser: life expectancy at birth, sex-split (Male/Female in
  columns 17/19, verified stable across all XLS editions 2011-2024) —
  the collector prints no "both sexes" column, and averaging would be a
  derivation (the canonical tier reports, it does not derive). New
  `sex` field end-to-end: RawRecord, NormalizedPoint, MergedPoint, the
  merge key (entity, year, sex), the dist points, and the
  duplicate check. Non-sex-split sources carry sex=None; the witness
  (both-sexes) and the canonical (sex-split) series coexist without
  colliding.
- Edition loop in the configs: infant_mortality now carries 12 canonical
  DYB sources (editions 2011-2014 + 2017-2024, later edition = higher
  priority = later vintage wins, every arbitration logged in
  provenance.json) + curated + OWID witness; life_expectancy now carries
  the same 12 DYB Table 4 editions as canonical + OWID witness (its
  first two-tier wiring — the ADR-0008 treatment asked for in review).
- 15 entity overrides for the UN's own official/vintage names across
  editions (Czech Republic, Turkey, TFYR of Macedonia, Swaziland, Cape
  Verde, long-form Bolivia/Venezuela, Faeroe spelling, ...) + 3 defunct-
  entity overrides prepared for the PDF route (USSR, Yugoslavia SFR,
  Germany F.R. — vintage names verified in the 1978 text; zero coverage
  in the XLS loop by construction, as the P1 correction established).
  The "Yemen" override is deliberately ABSENT: the vintage North and the
  modern unified entity share the printed name, and an override would
  hijack modern rows (documented in entities.yaml).
- xlrd as a declared dependency (the BIFF editions are wired in the
  default configs); tests for the dispatch, the Table 4 parser, the sex
  semantics, the vintage arbitration, the 2015 refusal, the '-' marker
  and the BIFF-era normalizations (row-level, no binary fixture needed).

### Verified (live, full pipeline)
- Fetch: 28 snapshots, 0 failures (12 editions x 2 tables + curated + 3
  OWID). Rebuild + dist: infant_mortality 1419 canonical points, 118
  entities, 1970-2024 (v6: 363); life_expectancy 3018 canonical points,
  182 entities, 2007-2024 (v6: 0 — witness only). France's IMR series
  is now reconstructed from six different edition vintages (2007-2024).
  The Russia hole is visible and honest: 10 canonical LE points
  (2007-2012, then the questionnaire gap), with the sex gap as-reported
  (male 61.4-64.6 vs female 73.9-75.9 in 2007-2012 — a Todd-relevant
  signal now carried canonically). USSR curated series intact (21 points,
  1976 = 31.4). 107/107 tests.

### P1b spike (DYB 1978 PDF, Table 15 — the reliability measurement)
- Token-level extraction from the PDF text reaches 5/6 known values
  exactly (USSR 125908/27.7, France, GDR, FRG, Yugoslavia; the UK miss
  is the footnote-digit-after-code ambiguity, irreducible at token
  level). Reliability: 47% of country lines parse with full confidence,
  15% print counts without rates (the collector's own "U" rule —
  expected), 21% carry OCR corruptions (refused, not guessed), 17% are
  data-less rows (expected).
- Verdict: a full PDF-era connector is VIABLE but REVIEWED, not fully
  automatic (~60% auto, per-edition eyeball for the flagged subset).
  For the defunct entities (the P1b target: ~10-20 rows per edition),
  the honest route is the CURATED gate (minutes per edition, mechanism
  already exists) rather than a connector. Decision recorded for the
  next review; no PDF connector written.

### Known limitations
- Canonical LE is sex-split only (no both-sexes canonical series — a
  derived product, explicitly out of scope until a separate decision).
- The pre-2007 as-reported history and the defunct entities remain
  outside the loop (PDF-era, gated per the spike's verdict).
- dist v2 contract: `sex` appears on points when the source prints it;
  the frontend (not yet built) must handle sex-split series for LE.

## 2026-09-06 — v6.1: identity hygiene (rename carried through the code)

### Changed
- `pyproject.toml` project name: `interface-todd` -> `toddlab`. The
  historical working title had survived every rename of the repo, the zips
  and the docs. Nothing imports the distribution name (all modules are
  imported as `src.*`), so the change is inert for the pipeline and the
  test suite.
- HTTP `User-Agent` in `owid.py` and `dyb.py`:
  `interface-todd-pipeline/0.1` -> `toddlab-pipeline/0.1`. This is the
  string external providers (OWID, UNSD) see in their access logs — it
  should carry the project's actual name. Same version token as before
  (matches `version = "0.1.0"` in `pyproject.toml`).

### Verified
- Full suite re-run after the change: 92/92.

## 2026-09-06 — v6: ADR-0008 wired (Technique A): curated tier + collectors canonical, harmonized witness, unit conversion real

### Context
ADR-0007 had left one decision open: which layer is canonical for the Todd
board. Asked as "Technique A vs B", the owner chose A, with the rationale
recorded in ADR-0008: *"with B, we fall back into the same smoothing
problem"* — a harmonized-canonical board keeps the re-modeled series as
its primary reading, and the witnesses would only ever measure the
distortion. This entry is the implementation of that choice, end to end,
on real data.

### Added
- **ADR-0008** (`docs/adr/0008-todd-board-canonical-layer.md`) — the
  decision record: as-reported tier (curated + collectors) canonical,
  harmonized witness; Extra board reads the same dist differently;
  canonical unit = per-1,000; per-point provenance as part of the
  canonical contract. ADR-0007's status updated (its deferred wiring is
  done).
- **The curated tier**: `src/connectors/curated.py` (strict parser: exact
  column contract, no empty values — a curated gap is an ABSENT row —
  empty `citation` rejected per the curation gate, duplicate
  (entity, year) rejected, path-fragment source_refs rejected) +
  `catalog/curated/` with its README (gate conditions, provenance,
  cross-checks) and the first series:
  **`ussr_infant_mortality_official.csv`** — the founding tracer, 21
  points 1970-1990, one citation per point (Kalabekov compilation of the
  TsSU/Goskomstat yearbooks; institutional carrier for 1974 = UN DYB 1978
  Table 15; by-republic aggregation reproduces 1970/1980/1985/1986;
  Kingkade & Arriaga for the retrospective series), per-row
  `definition_note` carrying the Soviet live-birth definition and the
  1976-87 blackout.
- **Schema**: `Provider.curated`, `SourceRole` (canonical/witness),
  `SourceRef.role` + `SourceRef.unit` (native unit, declared),
  `PROVIDER_LAYER` (curated/collector/harmonized), `RawRecord.citation`/
  `definition_note` (per-point provenance), validator: at least one
  canonical source per indicator.
- **Entity resolution for the new tiers**: curated resolves by canonical
  `entity_id` (typos land in unresolved.json — no silent forgiveness);
  `un_dyb` resolves by `source_ids.un_dyb` override then exact label. 12
  overrides added to `entities.yaml`, verified against the live 2024
  Table 15 (144/145 names resolve; "Saint Helena ex. dep." deliberately
  unresolved — sub-territory granularity, visible in
  `infant_mortality.unresolved.json`).
- **Witness semantics in the pipeline**: merge splits on `role`
  (canonical arbitration by priority stays WITHIN the tier, logged;
  witnesses built as per-source series, gap-preserving — value=None
  points kept — duplicate reductions logged with role=witness);
  validate applies plausibility bounds and duplicate checks to every
  witness series; the coverage report gets a witness summary line each.
- **34 tests** (`tests/test_curated_connector.py`, 17;
  `tests/test_witness_semantics.py`, 13; 3 new integration cases; bugfix
  tests extended with a per-source_ref scoping guard). Total: 92, all
  passing.

### Changed
- **`infant_mortality.yaml` v2**: three sources — curated
  (canonical, p1), `un_dyb 2024/table15` (canonical, p2), owid
  (witness, p3) — with `role` and native `unit` declared. Canonical unit
  is now **per-1,000** (the field's native unit; the phase-1 percentage
  was a single-source stopgap, always marked for phase 2): every
  published value is x10 vs v5, and the x10 conversion burden sits on the
  OWID witness (declared `UNIT_CONVERSIONS` table, never a guessed
  factor). Plausible range rescaled 0-400.
- **`normalize.py`**: `_convert_unit` is real (declared lookup, loud
  `NotImplementedError` on unknown pairs, 1e-10 float-artifact rounding);
  raw snapshots move to a per-`source_ref` directory
  (`raw/{provider}/{indicator}/{source_ref}/{ts}.json`) — a latent-bug
  fix: two sources of the same provider (the planned DYB editions loop)
  previously competed for one directory and only the latest fetch
  survived into normalize.
- **Dist v2 (breaking for the frontend contract, documented here)**:
  `sources_used` replaced by `sources` (role + layer + native unit);
  canonical `data` points carry `provider`/`source_ref` and, for curated,
  `citation`/`definition_note`; new `witnesses` block (per source:
  layer, unit, converted data); `catalog.json` gains `n_witness_points`.
- **Docs**: the-measurement-problem.md §6 (both open questions closed),
  §4/§7.2 updated to "implemented"; architecture.md phase list updated;
  dyb.py/sources.yaml wiring notes updated.

### Verified live (2026-09-06, real network fetch + rebuild)
- Full fetch: 5 snapshots, 0 failures (21 curated rows; 755 DYB records;
  13,944 OWID IMR rows; life expectancy + homicide).
- The founding divergence is now carried by the data layer itself:
  canonical USSR 1974 = **27.9‰** (curated, cited, DYB-1978 carrier on
  the row; peak 31.4‰ in 1976) vs witness Russia 1974 = **21.91‰**
  (UN IGME via OWID, converted to per-1,000 — the plateau).
- Canonical coverage: 363 points = 342 DYB (90 countries, 2020-2024,
  0 violations, 0 duplicates) + 21 curated USSR. Russia/US/China/UK
  honestly absent from the canonical tier (collector holes); the IGME
  witness carries 200 entities / 13,202 points; the pre-1991 South Sudan
  point (484‰) stays flagged in the witness bounds check, on purpose.

### Known limitations (deliberate)
- Canonical as-reported coverage is 2020-2024 + the USSR tracer: the
  1991-2019 gap awaits the DYB editions loop (2014-2023 tables) and the
  HMD/national routes (ADR-0007 decision 4).
- DYB quality codes and footnote markers still not carried into
  `RawRecord` (per-point provenance for the collector tier, phase 2).
- The `family` root-genealogy field (§5.1) deferred until the
  worldbank/gho connectors make multi-root indicators real.
- Witness points with `value=None` are kept as explicit gaps, but no
  current witness source emits them (DYB is canonical here); the
  semantics are tested at unit level.

---

## 2026-09-06 — The collector tier: `un_dyb` connector (prototype), ADR-0007, doc §7

### Context
The question that closed the sourcing loop: if harmonized sources (OWID
included) smooth the signals the Todd method reads, is there a universal
"raw figures" database — or must we scrape 193 national statistical
offices, and wouldn't multi-source stitching be bricolage? Answer (ADR-0007):
no universal raw base can exist ("raw" is a rank in a production chain, not
a property of a database), but the *collector tier* — international
databases republishing national official statistics as reported — already
does the per-country work once, centrally, machine-readably, with quality
annotations.

### Investigated (live)
- **Demographic Yearbook 1978, Table 15** (downloaded from the UNSD PDF
  archive): USSR row = 125,908 infant deaths and **27.7‰ for 1974** (the
  official Soviet rising series, not the UN IGME 21.9‰ plateau), **footnote
  33** spelling out the Soviet live-birth definition (under 28 weeks /
  1,000 g / 35 cm, dying within 7 days), and **blank cells 1975-1978** —
  the publication blackout preserved as first-class missingness by the
  collector itself. Value + definition + gap in one institutional row:
  the founding tracer has a citable carrier.
- **DYB 2024, Table 15** (XLS, SpreadsheetML 2003): structure decoded
  (merged year-header cells give the value columns; footnote-reference
  cells alternate with values and can hold digits — a real trap for naive
  value filtering); quality codes C/U/|/...; the table's own editorial
  rule (rates computed only for C/| data) explains why ~90 of ~151
  reporting countries have rates; Tonga carries two Total rows under
  different quality regimes; Russia, the US, China and the UK are absent
  (questionnaire gaps — coverage data, not errors to patch).
- WHO Mortality Database ("as reported annually by Member States", per-part
  files), UN IGME inputs (childmortality.org, "the data used to derive
  them"), HMD + HCD: inventoried as the collector tier for causes and
  child mortality (§7 table). UNdata's ASP.NET portal probed and found
  not curl-friendly: documented as a phase-2 alternative, not a blocker.

### Added
- **`src/connectors/dyb.py`** — `un_dyb` connector: positional SpreadsheetML
  parser (stdlib ElementTree, no xlrd/openpyxl), `source_ref` format
  `{edition}/table{NN}` (e.g. `2024/table15`), `field` selects the value
  block (`rate` = IMR per 1,000 — the DYB's native unit; `number` =
  registered deaths). Loud failures on layout drift per the house rule.
- **`Provider.un_dyb`** registered in `CONNECTORS` — fetchable today, but
  deliberately not referenced by any indicator yet: wiring it as
  `infant_mortality`'s witness needs per-point unit conversion first
  (per-1,000 vs percentage — the exact trap the unit bug came from).
- **`config/sources.yaml`**: `un_dyb` block (collector-tier notes, quality
  codes, coverage holes, licensing posture).
- **`docs/the-measurement-problem.md` §7** — the collector tier: the
  two-part answer (no universal raw base / the collector tier), the
  verified inventory table, the paradigm case upgraded with the DYB 1978
  row, and four architecture consequences. §4 route list updated with the
  institutional carrier.
- **`docs/adr/`** — ADR register born: `0007-source-of-record-and-
  witnesses.md` (three-tier sourcing, source-of-record per layer,
  witnesses never merged, curation gate, collector holes as data) +
  `README.md` explaining the register and reserving 0001-0006 for
  decisions already recorded in this changelog.
- **16 tests** (`tests/test_dyb_connector.py`) + fixture
  `tests/fixtures/dyb_table15_sample.xls` (faithful SpreadsheetML replica:
  bilingual names, quality codes, "..." markers, digit-bearing footnote
  cells, Tonga's double Total rows). Total: 58 tests, all passing.
- Live smoke test through the pipeline's own snapshot writer: 755 records
  from the real DYB 2024 Table 15, 342 non-missing rate points, 90
  countries, France 2020-2024 exact (3.37 → 3.84‰).

### Known limitations (deliberate, see ADR-0007)
- Urban/Rural rows not emitted (needs a dimension field in the raw
  schema, phase 2); quality codes and footnote markers not carried into
  `RawRecord` yet (per-point provenance, phase 2).
- Table 16 (age/sex detail) and pre-2014 PDF-only editions not parsed;
  iterating editions 2014+ to build the full as-reported series is a
  phase-2 loop around the existing connector.

---

## 2026-09-04 — `label_fr` dropped (English-only labels), Option A for `data/`, full translation pass

### Changed
- **`label_fr` removed everywhere** (decided in conversation): the schema
  now carries a single English `label` field for both `Indicator` and
  `Entity` (`label_en` renamed to `label`, `label_fr` deleted). The
  public-facing project is English-first; if a French UI is ever wanted,
  labels can be reintroduced later as a separate locale layer without
  touching the pipeline. `label_source` values updated accordingly
  (`babel_fr` -> `pycountry`). Tests updated to match English labels
  (e.g. "Russie"/"Tchécoslovaquie" assertions -> "Russia"/"Czechoslovakia").
- **Git strategy for data (Option A, decided in conversation)**:
  `data/dist` stays committed (offline development, reviewable data
  revisions); `data/raw`, `data/processed` and `reports/` are now
  gitignored as regenerable artifacts. The demo fixtures currently in
  `data/dist` must be replaced by a real `fetch` + `rebuild` before the
  first public data commit.
- Full English pass completed on the remaining French: `.gitignore`
  comments, `pyproject.toml` description, `docs/emmanuel_todd.md`
  (typography, book-title glosses).
- `homicide_rate`: added the missing `field: "Homicide rate per 100,000
  population"` — without it, the live UNODC CSV (two value columns) fails
  to parse and the indicator yields zero data (found during the live
  re-audit).
- **New doc: `docs/the-measurement-problem.md`** — the deep analysis of the
  data problem behind the founding tracer (Soviet infant mortality 1970s):
  why the UN IGME family (OWID/WDI/GHO — one root, three redistributions)
  shows a plateau while the official Soviet series showed a +27% rise;
  the layer model (register / official / scholarly / harmonized /
  derivative); where the real data lives (Davis & Feshbach 1980, late-1980s
  retrospective series, HMD 1959-2014, Rosstat); and seven concrete
  architecture consequences (source `family`/`layer` genealogy fields,
  `curated` source type for hand-entered cited tables, canonical+witness
  divergence display, composite layer guard, reclassification case study,
  publication gaps as events, HMD data ops). Triggered by a live
  investigation after Macrotrends' Russia series was found to be an
  interpolated derivative of undocumented provenance.


## 2026-09-03 — USSR tracer resolved: `formerly_part_of` field added

### Context
Following up on the audit's gap finding (see entry below), asked directly:
"are you sure OWID has no USSR data at all?" rather than take the report on
faith. Investigated live against the OWID API instead of guessing.

### Investigated
- Fetched the live entity list for the `infant-mortality` indicator
  (`api.ourworldindata.org/v1/indicators/1271815.metadata.json`): no
  "USSR" entity present. Also confirms the percentage-unit bug fixed
  earlier (`"unit": "deaths per 100 live births"`, `"shortUnit": "%"`) —
  first-party confirmation, not just cross-referenced estimates.
- As a candidate alternative source (per conversation), checked OWID's
  deepest long-run child-mortality series, Gapminder + UN IGME,
  1751-2024 (`indicators/1271844.metadata.json`): still no "USSR" entity,
  despite 274 years of history. Gapminder's own documentation explains why:
  historical estimates are attached to *current* country boundaries, not
  preserved as defunct political unions.
- Conclusion: this isn't a "wrong slug" problem fixable by picking a
  different OWID chart — it's how this entire family of datasets is built.
  Russia's own entry already carries a continuous series through the
  Soviet period under the "Russia" label.

### Decided (in conversation, not unilaterally)
Each of the 15 former Soviet republics shows one continuous data series
across 1991 (not split into a separate fabricated "ussr" series, since
the underlying numbers are identical either way — this isn't a "proxy," OWID
simply never separated them). The pre-1991 portion carries an explicit
warning via a new `formerly_part_of` field.

### Added
- `FormerUnionMembership` model + `Entity.formerly_part_of` field
  (`src/schema/entity.py`): `{union_entity_id, until_year, note}`. Kept
  deliberately distinct from `predecessor`/`successor`, which model a real
  discontinuity (e.g. Czechia genuinely didn't exist before 1993) — the 15
  republics existed continuously before, during, and after the USSR, only
  their sovereign status changed.
- All 15 ex-Soviet republics in `config/entities.yaml` now carry
  `formerly_part_of: {union_entity_id: ussr, until_year: 1991, note: ...}`.
- `build.py` now includes `formerly_part_of` in `dist/entities.json`, so
  the frontend can render the warning without needing per-datapoint
  annotations in each indicator's JSON.
- The `ussr` entity's `notes` field updated to point at this resolution
  instead of describing it as an open question. Kept in `entities.yaml`
  for reference and in case a future source (e.g. HMD) does carry a real
  standalone series.
- `docs/methodology.md`: new "On the USSR tracer" section with the full
  reasoning.
- Test fixtures (`tests/fixtures/owid_infant_mortality.csv`) updated to
  match the confirmed live reality: no standalone USSR rows; Russia's
  fixture rows now span 1958-2023 continuously instead of being split
  into separate USSR (1950-1990) and Russia (1992-2023) blocks.
- New tests: `test_ex_soviet_republics_carry_formerly_part_of`,
  `test_unrelated_entity_has_no_formerly_part_of`,
  `test_russia_carries_one_continuous_series_across_1991`,
  `test_entities_json_flags_soviet_era_data`.
- Total: 42 tests, all passing (was 39).

## 2026-09-03 — Live-network audit: 3 bugs fixed, 1 gap surfaced, full English pass

### Context
An external AI with real network access audited the phase 0/1 deliverable
against live OWID data (this sandbox has no outbound access to
`ourworldindata.org`). Full findings in the conversation. Summary of what
was independently re-verified by re-reading this repo's own code (not just
trusted from the report) and what was fixed as a result:

### Fixed
- **Fetch isolation (critical).** `fetch_indicator` didn't catch exceptions
  around `connector.fetch_raw(...)`: one source failing (the audit hit a
  live HTTP 403) aborted the entire `fetch_all` loop, so indicators queued
  *after* the failing one were never even attempted. Confirmed by
  re-reading `src/pipeline/fetch.py` directly. Fixed: each source is now
  wrapped in try/except, failures are collected into a `FetchOutcome`
  instead of propagating, and the CLI reports them without stopping the
  run (partial success = exit 0 by default; `--strict` opts into
  fail-on-any-error for CI). Regression test:
  `tests/test_pipeline_bugfixes.py::test_fetch_all_isolates_a_failing_source_from_the_rest`.
- **Snapshot selection by lexical filename sort (critical, silent).**
  `_latest_snapshot` used `sorted(glob(...))[-1]` on filenames. Production
  timestamps (`RawFetchResult.now_iso()`) look like `2026-09-03T084822Z`
  (dashes in the date part); this repo's own test/demo seeding helper used
  `20260101T000000Z` (no dashes at all). Because `-` (0x2D) sorts before
  `0` (0x30) in ASCII, the compact mock filename could lexically outrank a
  genuinely newer real fetch — confirmed by direct inspection of both
  format strings in this repo. Fixed: `_latest_snapshot` now parses each
  filename with `datetime.strptime` and picks the true max by parsed time,
  excluding unparseable filenames instead of trusting their raw string
  order. Also fixed the root cause: `tests/conftest.py`'s
  `seed_raw_snapshot` now writes fixture snapshot filenames in the same
  format production actually uses. Regression tests:
  `tests/test_pipeline_bugfixes.py::test_latest_snapshot_*`.
- **Stale `unresolved.json` (minor).** `write_normalized` only wrote
  `{indicator}.unresolved.json` when non-empty, so a stale file from an
  earlier run with junk entities could survive a later, clean run. Fixed:
  the file is now always written, empty or not.
- **Unit bug in `infant_mortality` (critical, data-integrity).** The OWID
  `infant-mortality` chart reports the rate as a **percentage** of live
  births, not per-1000 as originally assumed when this indicator was
  configured; no conversion is applied in phase 1 (single source, pass-
  through), so the declared `unit: deces_pour_1000_naissances` was
  factually wrong for the values actually stored, and the old
  `plausible_range: [0, 500]` (calibrated for per-mille) was blind to the
  real ~0–10 scale. Independently sanity-checked against known real-world
  figures (France, Japan, Soviet-era Russia infant mortality) — internally
  consistent with the audit's reported values, though not re-fetched
  directly by me given the sandbox's network restriction. Fixed the
  minimal way, consistent with this project's "never guess a conversion
  factor" principle: relabeled `unit: deaths_per_100_births` and tightened
  `plausible_range` to `[0, 40]`, rather than silently multiplying stored
  values by 10. A canonical per-mille unit with an explicit, documented
  conversion is left for phase 2 (`_convert_unit`, already stubbed).
  Regression test: `tests/test_pipeline_integration.py::test_no_violation_for_infant_mortality_with_corrected_unit`.
- **`owid.py` docstring inaccuracy.** Claimed OWID leaves `Code` blank for
  non-ISO3 entities. In reality OWID uses `"OWID_"`-prefixed pseudo-codes
  (`OWID_USS`, `OWID_KOS`, `OWID_WRL`...). Resolution logic wasn't actually
  broken by this (name-based fallback already handled it), but the
  docstring was corrected, and the `OWID_` prefix is now used as a
  heuristic in `normalize.py::classify_unresolved` to split unresolved
  names into `owid_special` (aggregates/regions/historical-but-uncataloged
  entities — expected, needs individual judgement) vs.
  `possible_mapping_gap` (more likely a real naming bug in
  `entities.yaml`). Regression tests in `tests/test_pipeline_integration.py`
  and `tests/test_owid_connector.py`.
- **Missing `homicide-rate` slug (critical, source unusable).** The
  original slug returns HTTP 403 on direct CSV download (confirmed live).
  Swapped to `homicide-rate-unodc` (verified reachable via search,
  UNODC-sourced, CC-BY, timespan 1990-2024) — also a better match for this
  project's stated preference for raw registry compilations over modeled
  estimates, so `reliability` was bumped from `medium` to `high` and
  `reliability_criteria` updated accordingly.
- **Kosovo missing from `entities.yaml`.** Absent from ISO 3166-1 so
  absent from the pycountry-generated base list; confirmed by the audit as
  a real data gap (not an expected aggregate) once it showed up unresolved
  in live income/region-group indicators. Added by hand: `iso3: null`,
  `valid_from: 2008`, `source_ids.worldbank: "XKX"`.

### Investigated, resolved in the entry above (2026-09-03, "USSR tracer resolved")
- **The USSR/infant-mortality tracer — this project's founding example —
  turns out to be close to unrepresentable with the currently selected
  OWID slugs.** Reported near-zero usable USSR rows once `covers_year`
  (`valid_from=1922`) excludes pre-1922 rows OWID also tags "USSR" in the
  long-run life-expectancy series, and the `infant-mortality` slug appears
  to carry no USSR rows at all. Russia's own OWID entry does cover the
  Soviet period continuously (1958 onward) under the "Russia" label. See
  the entry above for the live-data follow-up investigation and decision.
- Sub-national UK entities (England and Wales, Scotland, Northern Ireland),
  flagged by the audit as potentially relevant to Todd's family-systems
  anthropology — noted in `docs/architecture.md` as a deferred question,
  not decided on.

### Changed — full English pass
- All Python code (identifiers were already English; comments and
  docstrings were mostly French) translated to English throughout
  `src/` and `tests/`.
- All YAML config comments (`config/*.yaml`) translated to English.
  `label_fr` values (and only those) deliberately kept in French — they're
  the explicitly French-facing frontend label field, not incidental
  documentation.
- `Family` enum values changed from French (`mortalite`,
  `anthropometrie_sante`, `societe`) to English (`mortality`,
  `anthropometry_health`, `society`) for consistency — this is a breaking
  config change; the 3 pilot indicator files were updated accordingly.
- `unit` string values changed from French to English
  (`deces_pour_1000_naissances` -> `deaths_per_1000_births`, etc.).
- `README.md`, `docs/architecture.md` translated in place;
  `docs/methodologie.md` -> `docs/methodology.md` and `docs/licences.md`
  -> `docs/licenses.md` (renamed + translated).
- This changelog: earlier French entries translated to English rather than
  left as a mixed-language history.

### New tests
- `tests/test_pipeline_bugfixes.py` (4 tests): fetch isolation, snapshot
  selection by real timestamp vs. lexical sort, malformed-filename
  handling.
- Additional cases added to `tests/test_entity_resolution.py` (OWID-
  prefixed code resolution, Kosovo), `tests/test_owid_connector.py`
  (OWID-prefixed code parsing), `tests/test_pipeline_integration.py`
  (unresolved-name classification, East/West Germany resolution despite
  `OWID_`-prefixed codes, corrected infant-mortality unit).
- Total: 39 tests, all passing (was 29).

---

## 2026-09-03 — Changelog added

### Added
- This file (`CHANGELOG.md`), to track the project's evolution across the
  conversation.

---

## 2026-09-03 — Phase 0 + Phase 1: foundations + end-to-end OWID connector

### Added
- **Schema** (`src/schema/`): `Indicator` and `Entity` Pydantic models,
  with business validators (unique source priorities, mandatory
  justification for `reliability: low`, temporal consistency between
  `valid_from`/`valid_to`).
- **`config/entities.yaml`**: 257 geographic entities at the time — 249
  current countries generated via `pycountry` + `Babel` (automatic French
  labels), plus 8 historical entities added by hand (USSR, Czechoslovakia,
  Yugoslavia/SFRY, Serbia and Montenegro, East Germany, West Germany, North
  Yemen, South Yemen), each with explicitly declared successors. (Kosovo
  added later — see the entry above.)
- **OWID connector** (`src/connectors/owid.py`): pure `parse_csv()`
  function (testable offline) separate from the network fetch
  (`fetch_raw()`), so all business logic could be tested without depending
  on network availability.
- **5-step pipeline**, each independently replayable (`src/pipeline/`):
  - `fetch.py` — network -> timestamped raw snapshots in `data/raw/`
  - `normalize.py` — entity resolution (never interpolates or guesses by
    name proximity; an unresolved name is logged in
    `{indicator}.unresolved.json`, never silently dropped)
  - `merge.py` — multi-source merge by declared priority, with a
    provenance log of every arbitration (`{indicator}.provenance.json`)
  - `validate.py` — plausible-bounds check + coverage report
    (`reports/coverage_report.md`: entities with no data, internal gaps
    per entity)
  - `build.py` — generates `data/dist/{catalog,entities}.json` and
    `data/dist/indicators/{id}.json`
- **3 pilot indicators** (`config/indicators/`): `infant_mortality`,
  `life_expectancy`, `homicide_rate`, all `todd_core: true`.
- **CLI** (`src/cli.py`): `check-config`, `fetch`, `rebuild`, `all`.
- **29 tests** (`pytest`), all passing, including an end-to-end integration
  test via realistic CSV fixtures that explicitly checks the USSR/modern-
  Russia distinction is preserved.
- **Docs**: `docs/architecture.md`, `docs/methodologie.md` (principle-to-
  code translation table), `docs/licences.md`.
- A demo build in `data/` and `reports/`, generated from test fixtures —
  **not real OWID data** (see limitation below).

### Known limitations (not resolved in this delivery)
- **Network fetch never exercised against the real server**: the
  development environment has no outbound access to `ourworldindata.org`
  (firewall restricted to PyPI/GitHub). The code used a public OWID CSV
  URL verified via web search, but never actually executed. (Resolved by
  the live-network audit above.)
- `entities.yaml`: `source_ids.owid` is a bet (pycountry English name =
  OWID entity name), not verified country by country.
- Kosovo missing from `entities.yaml` (outside ISO 3166-1). (Fixed above.)
- No inter-source unit conversion (pointless while only one provider is
  active per indicator — a stub that raises `NotImplementedError`, planned
  for phase 2).
- No fine-grained anomaly detection (suspicious jumps, definition breaks)
  — only declared min/max bounds.
- No per-indicator `citation_text` (just `license`) — to add before
  displaying mandatory frontend credits.

### Notable decisions
- HMD and CLIO-INFRA dropped from scope at explicit request (their
  licensing/authentication questions weren't investigated).
- World Bank and GHO OData connectors pushed to phase 2: chose to validate
  the whole pipeline on a single provider before adding others, rather
  than parallelizing all 3 connectors from the start.
