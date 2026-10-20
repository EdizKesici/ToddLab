# Architecture

## A 5-step pipeline, each step independently replayable

```
fetch -> normalize -> merge -> validate -> build
(network) (entity        (inter-source  (bounds +   (final JSON
           resolution,     priority)      coverage)   for the
           no unit                                    frontend)
           conversion in
           phase 1)
```

Each step reads the file written by the previous one from disk
(`data/raw/` -> `data/processed/*.normalized.json` -> `*.merged.json` ->
`*.validation.json` -> `data/dist/`). No step keeps in-memory state across
runs: you can stop after any step and resume by rerunning `rebuild`.

## The score layer rides the dist (ADR-0011)

The project's FIRST AND ONLY derived product — two composite scores per
country-year, `official` (canonical-tier sources) and `modelled`
(widest-coverage single source per component), never merged. It is a
SIXTH consumer, not a pipeline step: `src/score/` reads the frozen
`data/dist/indicators/*.json` + `config/score.yaml` (the intent:
directions, transforms, sex handling, basis, `max_age_years`) +
`config/score_bounds.yaml` (the frozen numbers — p1/p99 bounds and the
retained source per component, written ONLY by
`scripts/freeze_score_bounds.py`), and emits `data/dist/score/`
(meta/official/modelled/golden_vectors — the exact frontend contract,
`docs/score-contract.md`). The indicator layer is untouched by all of
this: the three prohibitions stand, the derivation lives in its own
layer, its own config, its own ADR, labelled derived everywhere — with
ONE deliberate exception (decision 10: `industrial_employment_share`'s
`higher_is_better` is true, a breaking change to the indicator layer).
The layer's COMPOSITION: `incarceration_rate` is not in the score
(decision 11: no defensible direction; it stays an indicator). The
remaining directions are confirmed in the books (decisions 12-16: no
`editorial` basis, no provisional flag left), `illegitimate_births` is
in the OFFICIAL score only (decision 15 — the modelled side refuses it
loudly), and THE CARRY RULE (decision 16, amends the ADR's decision 3):
a component's value for year Y is the latest real observation with
obs_year in [Y - max_age_years, Y], its age recorded in the emitted
sparse `age` maps, a score emitted only where coverage >= 0.50 AND at
least one component is fresh (the ghost guard), no year beyond the
score's max_obs_year, and the two-year delta computed on components
whose underlying observation differs — the composition noise fell from
0.86/0.95 to 0.33/0.34 points per year, at the recorded price that the
last years of a series are largely carried values. The bounds
(decision 18) use fresh observations
only — the carry never moves the scale. The official fertility scale is
the worldwide two-collector canonical sample (hi 0.9903 on 2,523
observations / 177 entities). `rebuild` never recomputes bounds: a drift
guard fails the build loudly on EITHER of its two triggers — the frozen
source no longer matching what the §4.4 selection rules would pick on
the current dist, or the bounds sample's `n_sample` / `n_entities`
drifting beyond `bounds_drift_tolerance` (0.25) — re-freezing is a
deliberate `bounds_version` bump, recorded, never an auto-refresh. Every
frozen block is VALIDATED at load (integers, strictly positive counts —
the single implementation both CLI doors share): a malformed file is
refused before any build, and the guard never silently skips a missing
or non-positive count. That validation runs BEFORE any dist file is
written — a bad bounds file fails the rebuild with the dist bytes
untouched.

## The Todd corpus rides as metadata

Ediz's OCR compilation of Todd's metrics (todd_core.csv, tracked at
the repo root) transforms one-way into
`config/todd_refs.yaml` (`scripts/normalize_todd_refs.py`,
deterministic, validating loudly). The CSV has no `status` column and
its notes are what-is-cited-only (a note
may be empty; the published `refs[].note` key stays present).
Config load cross-validates the bijection between `todd_core: true`
indicators and corpus metric ids (ADR-0009) — the flag is
evidence-backed, failing loudly on either side. The build emits the
corpus additively: a `todd_refs` block on matching indicators and
catalog entries, and `dist/todd_corpus.json` — all 22 metrics,
implemented and unimplemented, ranked by the corpus's citation weight
(the executable roadmap: birth_rate_fertility 109 citations, the #1;
suicide_rate 77; infant_mortality 47; consanguineous_marriage_rate 34;
industrial_employment_share 30; life_expectancy 25; homicide_rate 24;
unemployment_rate 20; illegitimate_births 14;
same_sex_marriage_legalization_year 13; tertiary 13; cirrhosis 9;
secondary 8; top_income_share 7; universal_suffrage_introduction_year 7;
gini_index 4; road_accident_mortality 4; incarceration_rate 3;
math_test_scores 3; obesity_rate 3; hiv_prevalence_rate 1;
male_height_trend 1 — the backlog is empty,
"what to build next" is a question of depth, not count). `cli stats`
closes with the corpus block. The GHO connector carries the Dim2
AGEGROUP rule for the suicide witness (all-ages series
kept, latest-year age slices dropped and logged, unknown Dim2 types
refused) — the SDGSUICIDE payload disaggregates 2021 into 11 age bands
beside the all-ages record, a hidden dimension that would otherwise
have ingested duplicates — and a PER-CODE AGE PIN on top of it: a
door whose every row carries ONE age frame (NCD_BMI_30C's
YEARS18-PLUS) declares that frame in a pin table, the parser accepting
exactly it and refusing anything else loudly (a door change is never
silently re-interpreted; unpinned codes keep the YEARSALL grammar
bit-identical).

Why this separation rather than a single fetch-and-build script: the only
step that needs the network is `fetch`. Everything else (`rebuild`) runs
offline — this is what made it possible to develop and test 100% of the
business logic in a sandbox with no access to ourworldindata.org (see
README). It's also what will let CI, later, run `fetch` on an infrequent
cron while iterating on `normalize`/`merge`/`validate` on every commit
without hammering external APIs.

## The most fragile part: `config/entities.yaml`

97% generated by `pycountry` + `Babel` (fr locale), 3% hand-completed for 9
defunct/manually-added entities. Two known limitations, documented at the
top of the file itself:

1. `source_ids.owid` is a bet (pycountry English name = OWID entity name),
   not a verification. `EntityRegistry.resolve_from_source` fails cleanly
   (returns `None`, never a guess) when it doesn't match — and
   `normalize.py` logs every failure into `{indicator}.unresolved.json`
   instead of swallowing it silently. That's the mechanism meant to
   correct the table incrementally. A live-network audit
   confirmed the bulk of "unresolved" names in real data are OWID
   aggregates/regions/income groups, expected by design — not mapping bugs.
2. Sub-national entities OWID tracks separately (England and Wales,
   Scotland, Northern Ireland) are not modeled here. Flagged as potentially
   relevant to Todd's family-systems anthropology, which partly operates at
   sub-national/regional level — deliberately deferred, not decided against.

## Phase 2 extension: adding a provider

1. Write `src/connectors/{provider}.py` with a pure parsing function
   (`parse_xxx(raw_text) -> list[RawRecord]`) separate from the network
   call — same pattern as `owid.py`, to stay testable offline.
2. Register it in `CONNECTORS` (`src/pipeline/fetch.py`).
3. Add an entry to `config/sources.yaml`.
4. Nothing else to change: `normalize`/`merge`/`validate`/`build` are
   already provider-generic (they key off `source.provider.value` to find
   the connector, no hidden `if provider == "owid"` branch elsewhere in the
   pipeline).

The DYB connector is the worked example of a provider serving
MULTIPLE formats, eras and tables: format detection by magic bytes
(SpreadsheetML vs BIFF via xlrd), parser dispatch on the file's own
title (number AND text — the 21/22 renumbering zone keys on the
WORDS: the LE-by-age table alternates numbers with the 5qx
probabilities by edition parity, and a number-only dispatch would have
mis-parsed the same layout into the wrong measure), per-era URL building
(legacy site 2011-2015 — the 2015 edition recovered through the
legacy pattern, its own index links being the dead part,
modern site 2016+), and era-specific normalizations (BIFF
years-as-floats, footnote references glued to names). A source that
reports a demographic breakdown carries it through the whole pipeline:
`(entity, year, sex)` is the merge key.

## What's deliberately absent from this phase (not an oversight)

- **Inter-source unit conversion is no longer absent** (ADR-0008):
  `normalize.py::_convert_unit` now applies the declared
  `UNIT_CONVERSIONS` table (percent <-> per-1,000) — the lookup-table
  discipline planned since the phase-1 unit bug was fixed by declaration
  rather than silent multiplication. Unknown pairs still raise loudly.
  Still open (phase 2): more unit families as new indicators land.
- **Canonical/witness semantics are implemented** (life_expectancy
  included). Per-indicator wiring:
  - homicide_rate: via the OECD/WHO-Mortality-Database route, sex-split,
    CRUDE rates pinned over the dataflow's age-standardized variant.
  - maternal_mortality_ratio: via DYB Table 17 — 13 editions 2001-2022,
    the "♦" small-numbers marker riding the points. maternal_deaths is
    the same table's Number block as its own indicator, so that
    Number-only countries are not left outside every series.
  - life_expectancy_60: via DYB Tables 21/22 — the renumbering zone,
    latest-available-year cross-sections, printed reference periods —
    with the first GHO witness, WHOSIS_000015.
  - suicide_rate: the corpus's #2 by citations, the homicide
    architecture one cause-code away, whose witness is the first who_ghe
    root: the GHE model re-distributes the ill-defined causes over the
    collectors' printed suicides (Russia male 2000: 69.8 as-reported vs
    95.2 modeled), a systematic tier divergence displayed, never
    reconciled.
  - birth_rate_fertility: the corpus's #1, the only metric in all 15
    books — canonical on the Eurostat collector (demo_find/TOTFERRT,
    the one collector wire that prints a national TFR) with its own
    display case: the France variant pair, TWO printed series
    (metropolitan 1960-2012, whole 1998-2024) wired as separate
    geo-pinned sources so the merge arbitrates the overlap by vintage,
    every discarded value logged — and the WPP witness carrying the
    worldwide face the collector never polled.
  - illegitimate_births: Todd's illégitimité, the share the SAME
    Eurostat dataset prints directly (demo_find/NMARPCT, no derivation)
    — carrying the GERMAN SEAM: the codelist's DE_TOT is the fuller
    65-year all-Germany series and DIVERGES from DE's FRG-only
    pre-reunification benchmarks (1980: 7.6 vs 11.9, the GDR's high
    non-marital share), so DE_TOT rides its own geo-pinned source ABOVE
    the main slice and every DE collision is a logged provenance discard
    — the France seam's architecture applied to a definitional seam —
    with the OECD Family Database witness through OWID's chart door, the
    registry's oecd_family root.
  - consanguineous_marriage_rate: the corpus's #4 (34 citations, 10
    books), claimed through the CURATED tier (no machine-readable door
    anywhere), 102 published readings across 69 countries, 1943-2021, one
    citation per point, the third curated family (the consensus-literature
    series) and the root consanguinity_studies — the study IS the origin,
    no witness can ever cross-check it.
  - unemployment_rate: the economy family's FIRST indicator (the Family
    enum has `economy`) — canonical on the project's SECOND Eurostat
    dataset (une_rt_a pinned Y15-74/PC_ACT/T, the connector's second
    dispatch decision with its own ref grammar and layout pin-guard; the
    probe verdict: ILOSTAT wholesale ILO-processed, OECD harmonized — no
    other collector prints the plain national rate) with the WB
    national-estimate witness (root ilo_lfs — the ILOSTAT DEAP family
    redistributed by WDI), the root pair eurostat_lfs/ilo_lfs keeping
    the COVERAGE CLIFF (Germany 1991-2008 witness-only, the collector
    starts DE at 2009) and the LFS-2021 definitional 'd' seam reading
    as two doors, never a contradiction.
  - industrial_employment_share (30 citations): the probe finding is that
    the EU national accounts (nama_10_a10_e, unit PC_TOT_PER) PRINT the
    employment share directly, so the metric is wired with NO derivation
    and the composite-derived-layer ADR is retired unused (root
    eurostat_na; the
    EA two-letter aggregate edge dropped logged).
  - tertiary + secondary_education_share: on the LFS attainment table
    (edat_lfse_03, ED5-8 / ED3_4 — the LFS questionnaire's third metric
    family; UNESCO UIS has no live API, the probe record in
    sources.yaml; tertiary's witness = the Barro-Lee/Lee-Lee panels via
    OWID, the corpus's own named source, root barro_lee; secondary
    canonical-only, its world face the recorded Barro-Lee direct door).
  - cirrhosis_alcohol_mortality: the OECD dataflow's third cause code,
    CICDCIRR; the WHO-MDB coding story, the GHE witness covering Russia.
  - top_income_share (7 citations): canonical on the WID chart door
    through OWID, root wid, the API 403 record in sources.yaml;
    CANONICAL-ALONE, the secondary_education precedent: the IDD's 35
    measures carry no top-share, the extrapolations sibling refused as
    the same root's modeled extension.
  - gini_index: canonical on the OECD IDD, root oecd_idd, wired as the
    FOUR-DOOR vintage chain — METH2012-current > D_PREV > D_INC
    back-series > METH2011 history — the NMARPCT quatuor pattern applied
    to a methodology-definition seam, 906 keys zero unresolved, the WID
    pre-tax witness displaying the concept seam: France 2022 = 0.299
    disposable vs 0.4592 pre-tax.
  - road_accident_mortality: canonical on the ITF/IRTAD flow, root
    itf_irtad, the per-100k face wired and the per-vehicle face of
    Todd's own 1974 table a registered door; witness GHO RS_198, root
    who_roadsafety — the biennial report's single-2021-vintage coupe,
    Russia's only machine face on this metric.
  - OECD connector: it speaks THREE dataflows (DF_COM, DF_IDD,
    DF_SAFETY — one shared SDMX-CSV walker, one pin dict per flow, the
    "latest" version token refused by the endpoint and every flow
    reference carrying its explicit registry version).
  - incarceration_rate: canonical on the ICPR World Prison Brief's OWID
    chart door, root icpr_wpb — the UNODC collector portal a
    client-rendered SPA with no discoverable machine door, the probe
    record; witness the GHO Health in Prisons coupe PRISON_A2, root
    who_prisons, 36 European countries at the single 2020 vintage — the
    RS_198 pattern.
  - math_test_scores: the education Family's first indicator — canonical
    on the OECD PISA chart door with the Mathematics column pinned, root
    oecd_pisa, the SDMX registry carrying no PISA dataflow and TIMSS no
    machine door at all; CANONICAL-ALONE.
  - obesity_rate: canonical on GHO's own wire, NCD_BMI_30C, root
    ncd_risc_bmi — the FIRST GHO-canonical indicator, the per-code AGE
    pin's own door, full sex split riding the canonical tier;
    CANONICAL-ALONE, the OWID chart's bit-identity the auto-witness
    refusal's evidence.
  - hiv_prevalence_rate: canonical on the UNAIDS chart door, root unaids
    — aidsinfo a SPA, api.unaids.org DNS-dead; CANONICAL-ALONE, the
    compilation's own universe excluding the USA, Russia and China,
    verified on both redistributions.
  - male_height_trend: canonical on the NCD-RisC 2016 birth-cohort chart
    door, root ncd_risc_height, the framing seams — birth-year vs
    calendar, age 18 vs the book's 20 — documented; witness the
    Baten-Blum/Clio-Infra historical record, root baten_blum, the
    pre-1896 tail on the witness tier, the barro_lee relation.
  - GHO MDG_0000000001: the door's age frame is AGEGROUP_MONTHS0-11 on
    every row, handled by the per-code AGE PIN, the dist bit-identical
    through it.
  - The class-decomposed RATE faces of Todd's immigration question ride
    unemployment_rate's segment layers (ADR-0010's parallel-faces
    discipline, moot as a standalone layer, lives on there). The corpus
    holds 22 metrics; the demography family value stays in the enum for
    the corpus's own vocabulary.
- **Per-point provenance for the collector tier is implemented**: DYB
  quality codes, footnote texts, LE reference ranges, missing markers,
  provisional flags — as-reported, joined into the dist. Witness
  citation blocks on every source are implemented.
- **Merge semantics keep printed-but-empty cells** as explicit canonical
  gap points ("counts published, no ratio computed").
- **The `family` root-genealogy field is implemented** (§5.1 of the
  measurement problem — `SourceRef.root`, a closed registry in
  `src/schema/indicator.py`), together with the World Bank
  connector (the provider that made it necessary): every source
  declares its ultimate origin, the dist's `sources[]`/`witnesses[]`
  carry `root`+`root_label`, and `catalog.json` computes the per-role
  roots with door counts — infant mortality's four agreeing witnesses
  read as "1 root (UN IGME) via 4 doors", life expectancy's two as
  genuinely different roots (the OWID long-run compilation vs pure
  WPP), and the maternal ratio's two agreeing witnesses read
  as "1 root (UN MMEIG) via 2 doors" — doors carrying DIFFERENT ROUNDS
  of the model (the OWID 2020 round vs the WDI 2023 round), so their
  divergence (South Sudan 1987: 6,774.7 vs 8,045) is the model's own
  revision made visible instead of a contradiction.
- **The PDF-era editions (1948-2010) and the defunct entities** (the P1
  correction: the XLS loop's windows cannot contain them by
  construction). The P1b spike (DYB 1978 Table 15) measured the PDF
  route: 5/6 spot-checks exact, 47% of lines full-confidence, 21%
  OCR-refused — viable but REVIEWED, not fully automatic. For the
  defunct (a few rows per edition) the honest route is the existing
  curated gate; a full PDF connector only pays off for the complete
  pre-2007 backfill and stays gated behind an explicit decision.
- **A both-sexes canonical life expectancy**: the collector prints Male/
  Female separately (no "both sexes" column); averaging would be a
  derivation. The dist carries sex-split canonical points beside the
  both-sexes witness; a both-sexes canonical series would be a derived
  product, named as such, decided separately.
- **Fine-grained anomaly detection** (suspicious jumps, inter-source
  definition breaks): `validate.py` only checks declared min/max bounds
  (now also on witness series) and duplicate rows. Jump detection is a
  standalone phase-4 project.
- **owid-catalog / OWID's structured API**: the current connector scrapes
  the public grapher CSVs (simple, no extra dependency). OWID also exposes
  a richer metadata layer (semantic indicator search, versioned Parquet
  tables) — a migration candidate if the indicator count grows
  significantly; not needed for the pilot indicators.
- **Retry/backoff on transient network errors**: a live-network audit found
  one slug returning a hard HTTP 403 (not a transient failure — the source
  itself needed swapping), so retry logic wasn't the
  priority fix here. Worth adding in phase 2 for genuinely transient
  errors (timeouts, 5xx).
