# ToddLab

## The hard indicators of societies.

ToddLab is an open-source tool for comparing countries using hard social indicators such as mortality, health, education or demography rather than monetary aggregates or opinion surveys.

## Why?

GDP, rankings and composite scores tell us what is declared or monetized, not necessarily what is real. ToddLab is built on a simple idea: some things cannot lie.

The project takes inspiration from the method of historian-demographer Emmanuel Todd, who famously predicted the collapse of the USSR in 1976 by tracking a single hard indicator: rising infant mortality.

## What it does

Compare countries side by side on hard indicators (infant mortality, life
expectancy, fertility, homicides, education...).

## The score layer (v27, amended v27.1, v28, v28.1 and v28.2)

Beside the indicators, a DERIVED layer: two composite scores per
country-year — **official** (canonical-tier sources, 18 indicators —
Todd's illégitimité among them since v28) and **modelled**
(widest-coverage single source per component) — built on a frozen
absolute scale (p1/p99 bounds, versioned — the official fertility
scale regenerated worldwide in v28.2), one source per component
never mixed, no interpolation, coverage displayed with every value.
The rebuild refuses loudly when a frozen source name or a bounds
sample's size and entity count drifts beyond the configured tolerance
(v28.2's hardened drift guard). Since v28 a component's value is the
latest real observation at most
3 years old, its age recorded and displayed ("data from YYYY") — a
reuse of a real measurement, never an invented value. The two scores
stay side by side, never merged (ADR-0011); the exact frontend
contract is `docs/score-contract.md`. The indicator layer's three
prohibitions are untouched — the derivation lives in its own layer and
is labelled as derived everywhere. `incarceration_rate` and
`gini_index` stay indicators but sit OUTSIDE the score (no defensible
direction).

## Principles

- Measured, not declared. Outcome indicators (deaths, measurements, test results) over survey data.
- Never hide missing data. Gaps in coverage are displayed, not interpolated away.


## Data sources

### All free and open

- **UN Demographic Yearbook** (collector tier) — national official vital
  statistics as reported to the UN, with quality codes and honest gaps.
  Wired as an edition loop: 13 editions (2011-2015 + 2017-2024 — the
  2015 vintage recovered through the legacy URL pattern), three file
  formats, covering 2007-2024 as-reported for infant mortality
  (Table 15), life expectancy at birth (Table 4, sex-split as printed),
  maternal mortality (Table 17, 2001-2022, the "♦" small-numbers marker
  and the UNSD-computed ratios as published), — since v12 — the SAME
  table's Number block as a second indicator, maternal_deaths (the
  registered counts: the collector refuses ratios, never counts, so the
  counts block serves 131 countries where the ratio block serves 97 —
  Libya's 12 registered deaths in 2016 exist only here), — since v10 —
  life expectancy at age 60 (Tables 21/22, the renumbering zone: latest-
  available-year cross-sections, printed reference periods, beside the
  first GHO witness), and — since v15 — the crude birth rate (Table 9,
  the collector's natalité print: the same wide layout as Table 15
  through its own dispatch branch, the SAME births Table 17's maternal
  ratios are computed from; the '*NN' star-plus-ref marker — a
  provisional count citing its own note in one cell — rides the
  connector's grammar since v15). Since
  v8 the collector's own annotations ride every point: quality codes,
  footnote texts, life-expectancy reference ranges; since v9 the
  printed-but-empty cells surface as explicit canonical gap points
  ("counts published, no ratio computed" is data, not absence).
- **WHO Mortality Database, via the OECD "Causes of mortality" dataflow**
  (collector tier) — cause-of-death registrations as submitted by member
  states (ICD-coded; Assault for the homicide rate, intentional
  self-harm for the suicide rate — v13, the corpus's #2 by citations,
  and chronic liver diseases and cirrhosis for the alcohol-mortality
  indicator — v18, La Chute finale's calibration pair printing itself:
  FRA 1979 = 29.0 vs SWE 12.2), 49 countries on homicide / 46 on
  suicide / 45 on cirrhosis, 1960-2024, crude rates (the
  age-standardized variant is a derived measure and deliberately not
  used as canonical). The three causes share one architecture: the OECD
  dataflow carries 50 death-cause codes, each one config away — and
  the v18 wiring corrected the v13 probe record on the way: "RUS
  absent from the cirrhosis slice" was a probe artifact (the v13 probe
  omitted the Accept header; the full slice answers 7,089 records
  through the production machinery). The honest finding instead:
  Russia genuinely does not ride this cause's collector slice (its
  alcohol deaths live under different ICD codes — the WHO-MDB coding
  story), so the Russian claim rides the GHE witness (modeled,
  age-standardized) and the book tables.
- **OECD, THREE MORE DATAFLOWS** (collector tier, v19 — the
  three-flow connector, the eurostat precedent applied: one connector,
  one grammar + pin guard per dataset) — the Income Distribution Database
  (DSD_WISE_IDD@DF_IDD, the gini canonical: national household-survey
  microdata as submitted, equivalized disposable income, 45 areas
  1974-2025, USA 1995 = 0.361 on L'illusion économique's own year) and
  the ITF/IRTAD Transport safety indicators (DSD_INDICATORS@
  DF_SAFETY, the road-mortality canonical: police-reported crash
  registrations, 55 areas 1994-2025, FRA 15.2 -> 4.7 the
  sécurité-routière arc, LVA 1994 = 28.44 the post-Soviet tail, RUS
  absent from the whole flow — the honest limit the witness covers).
  THE IDD STITCHING (the version's display case): the flow prints the
  same country-year under METHODOLOGY x DEFINITION vintages, so the
  gini config wires FOUR doors in a priority chain (METH2012-current >
  its definition back-series with and without the overlap year >
  METH2011 history) — the OECD explorer's own chained display made
  explicit, France sewing three times (0.277 in 1996 -> 0.309 in 2011
  -> 0.278 in 2020), every collision a logged provenance discard. The
  road flow prints THREE denominators — the per-100k population rate
  is wired (the mortality family's unit), the per-vehicle face
  (10P4VEH_MOT_ROAD — the exact denominator of Todd's own 1974 WHO
  table in Le Fou et le Prolétaire) and the per-vehicle-km face stay
  registered non-wired doors, one config line away.
- **World Inequality Database, via OWID's chart door** (research-
  harmonization tier serving as CANONICAL, v19) — the corpus NAMES the
  source for La Défaite de l'Occident's own inequality board
  ("Russia/USA/France, WID data"), and no collector anywhere prints a
  top-fractile income share: the metric is by construction a
  constructed series (fiscal microdata + surveys + national accounts,
  the DINA guidelines), so the compilation the corpus names IS the
  origin tier — the consanguinity_studies constitution. The direct
  WID API refuses this environment on every extractor shape (the
  CloudFront 403 record in sources.yaml), so the machine-readable
  face is OWID's chart door — incomes-of-the-richest, 165 entities,
  1820-2024, attribution "WID.world (2026)" read live from the chart
  metadata — the same door-relation the OECD Family Database holds.
  The top-1% indicator stands canonical-ALONE (no cross-root witness
  door exists — the honest absence, the probe record), the sibling
  extrapolations chart refused by the anti-derivation line, and the
  gini's WID pre-tax witness rides the same door family (the concept
  seam: France 2022 = 0.299 disposable canonical vs 0.4592 pre-tax
  witness — the redistribution IS the gap, displayed never
  reconciled).
- **The v20 queue doors — five compilations, one corpus closed**
  (24/24 at v20; 22/22 since v26's withdrawal of immigration_stock and
  agricultural_employment_share — counts, not rates; the closure
  discipline itself unchanged) — the final five metrics each found their machine
  face on a compilation's chart door or the provider's own wire:
  the ICPR World Prison Brief via OWID's prison-population-rate (225
  entities 1993-2026, the Défaite six-country board printing itself:
  USA 683 -> 542, RUS 729 -> 300, FRA 82 -> 126 — the UNODC collector
  portal is a client-rendered SPA with no machine door, the WPB's own
  site answers 404 on /api, the chart IS the wire), the OECD PISA
  Database via the average-performance chart door with the
  Mathematics column pinned (90 entities, 2003-2022 — the SDMX
  registry carries NO PISA dataflow; Todd's own TIMSS table has no
  machine door at all, the assessment seam documented), the UNAIDS
  Global AIDS Update via the share-of-the-population-infected chart
  door (161 entities 1990-2024 — aidsinfo a SPA, api.unaids.org
  DNS-dead; the compilation's own universe excludes the USA, Russia
  and China, verified identically on the GHO redistribution), the
  NCD-RisC height compilation via the average-height-of-men chart
  door (200 entities, birth cohorts 1896-1996, FRA +13.3cm — the
  book's +10cm printing bigger) with the Baten-Blum/Clio-Infra
  historical record as the CROSS-ROOT witness (the pre-1896 tail on
  the witness tier, the barro_lee relation), and — the one door on a
  provider's OWN wire — the NCD-RisC adult BMI pooled analysis as WHO
  GHO's NCD_BMI_30C (199 countries, 1980-2024, full sex split, the
  FIRST GHO-canonical indicator; the OWID chart redistributes it
  bit-identically, its own evidence for the auto-witness refusal).
  The GHO connector gained the PER-CODE AGE PIN for it: a door whose
  every row carries one age frame (YEARS18-PLUS, not SDGSUICIDE's
  YEARSALL) declares that frame, and the parser accepts exactly it —
  anything else stops the parse loudly. One GHO witness rides the
  collection tier — the WHO Health in Prisons coupe (36 European
  countries at the single 2020 vintage, the RS_198 pattern) — while
  three of the five stand canonical-alone, the top_income precedent
  for the honest absence of any cross-root machine door.
- **Curated tables** (in-repo, cited per point) — official or scholarly
  series no machine-readable collector redistributes. Three families
  since v17: collector-shaped series (the Soviet official infant-
  mortality series, entered because the machine-readable collectors
  stopped at 2007), MARKERS — dated institutional events, one point
  per country, the citation the statute or the scholarly dating itself:
  same-sex marriage legalization (33 countries, 2001-2025, the
  'religion zero' chain of La Défaite de l'Occident) and universal
  suffrage introduction (16 countries, 1848-1946, L'invention de
  l'Europe's anthropological fingerprint, the male/female
  decomposition riding every row's note), and — v17 — the
  CONSENSUS-LITERATURE SERIES: consanguineous_marriage_rate, 102
  published readings across 69 countries, 1943-2021, one citation per
  point (the Bittles consang.net compilation's national surveys and
  dispensation registries plus the directly-verified DHS final reports
  and journal studies — Pakistan's four DHS vintages, Iran's national
  38.6 over 306,343 couples, the European sub-1% registry belt, the
  Maghreb trio; the sparse-panel shape is the metric's own honest
  form, the scope discipline — national first, the largest study
  otherwise — riding every row's note), and — v21 — the TRANSCRIPTION
  SERIES: the DYB 1978 vanished-entity tables, the UN's own
  as-reported prints of states the modern XLS loop cannot reach (the
  USSR, the Byelorussian and Ukrainian SSR — three distinct UN member
  seats, each its own rows — plus Czechoslovakia, Yugoslavia SFR and
  the GDR), every value READ from the archived text layer and
  arithmetically cross-checked before entering the catalog (the Table
  15 count over the printed rate reproduces Table 9's births within
  0.4%; Table 4's LE equals Table 22's age-0 column), the Soviet
  live-birth definition and the Berlin footnote riding their rows'
  notes, the '*' prints and the C row-codes carried as structured
  fields (the curated format's v21 extension). The Yemen gate applied
  in reverse: the 1978 prints are Population Division ESTIMATES
  (footnote 4) — witness-class by constitution, the rows excluded,
  the entities honest and data-less. The curation gate's probe
  record: no OWID chart, no collector wire — the curated tier is not
  competing with a door, it is the only tier.
- **Our World in Data / UN IGME, UNODC, UN MMEIG** (harmonized tier) — model
  estimates for cross-country comparability, displayed as witnesses
  beside the as-reported series, never blended with it. The maternal
  witness (MMEIG) exists precisely where registration cannot serve — the
  canonical/witness spread on that indicator measures where official
  maternal-death statistics degrade below the modeled reality.
- **WHO Global Health Observatory** (harmonized tier, first indicator
  wired v10) — WPP-derived life expectancy at age 60 (WHOSIS_000015),
  the LE-60 witness: the collector's cross-sections freeze where a
  country stops submitting life tables (Russia 2012), while the model
  keeps estimating — the spread and the freeze are both signal. Since
  v11 it also carries MDG_0000000001, the IGME infant-mortality
  redistribution — the third door of the founding triangle. Since v13
  it carries SDGSUICIDE, the GHE crude suicide rates — the suicide
  witness and the first who_ghe root: the model re-distributes the
  ill-defined causes the collectors left unassigned (Russia male 2000:
  69.8 as-reported vs 95.2 modeled), so the two tiers of that indicator
  diverge systematically instead of episodically — the cleanest display
  of reclassification sensitivity in the project. Since v19 it also
  carries RS_198, the Global status report on road safety's modeled
  death rate — the road-mortality witness and the first who_roadsafety
  root (a DIFFERENT WHO estimate family from the GHE: the biennial
  report's own cross-section, 197 countries at its single 2021 vintage,
  Russia 10.6 included where the ITF collector never carried it — the
  coupe pattern the cirrhosis witness set).
- **Eurostat, Fertility indicators** (collector tier, v14 — the
  fertility canonical; v16 — the illégitimité too) — the series the
  national statistical offices themselves compute and publish,
  collected by Eurostat via its own questionnaire. TWO Todd metrics
  ride the one dataset now: the total fertility rate (demo_find's
  TOTFERRT, "births per woman" — v14; and since v28.1 the UN DYB
  Table 4's PRINTED TFR as the second canonical door, priority-merged
  under Eurostat, the worldwide fill + the UK's post-Brexit years —
  ADR-0011 decision 17) and the
  share of live births outside marriage (demo_find's NMARPCT,
  "Proportion of live births outside marriage" — v16, printed
  DIRECTLY by the collector, no ratio derivation; the OECD Family
  Database carries the share but no SDMX wire, and its compilation
  rides the OWID chart door as the witness). 47+ country codes,
  1960-2024, with the collector's own per-observation flags (b =
  break, e = estimated, p = provisional) riding the points
  as-reported; the codelist's own quirks (EL, UK, the FX metropolitan
  France series code, XK, DE_TOT) handled explicitly. TWO display
  cases live here: THE FRANCE VARIANT PAIR (FX Metropolitan France
  1960-2012 vs whole France 1998-2024, wired as separate sources so
  the merge arbitrates the overlap by vintage with every discarded
  value logged — the same seam on both indicators) and — v16's own —
  THE GERMAN SEAM: on the illegitimacy share the codelist's DE_TOT
  ("Germany including former GDR") is the FULL 65-year series while
  DE's pre-reunification benchmarks are FRG-only prints that DIVERGE
  (1980: 7.6 FRG vs 11.9 all-Germany — the GDR's high non-marital
  share), so DE_TOT rides its own geo-pinned source ABOVE the main
  slice and every DE collision becomes a logged provenance discard —
  the France seam's architecture applied to a definitional seam (the
  TFR case, where DE_TOT was a verified duplicate, stays dropped).
- **Eurostat, Unemployment by sex and age - annual data** (collector
  tier, v17 — the unemployment canonical) — the project's SECOND
  Eurostat dataset, wired as the connector's second dispatch decision
  (its own ref grammar `une_rt_a/{age}/{unit}/{sex}`, its own layout
  pin-guard). The probe verdict that earned the wiring: NO other wire
  prints the plain national rate at the collector tier — ILOSTAT is
  wholesale ILO-processed material (ILOEST modeled on 2EAP, 19th-ICLS
  WORK harmonized on 5EAP, LFS/ILMS microdata-reprocessed on DEAP —
  Germany's own rows are the EU-LFS and its adjusted variant), the
  OECD doors are OECD-harmonized or registered-unemployment counts.
  The pins are the indicator: age Y15-74 (the codelist carries NO
  TOTAL — Y15-74 is the LFS's own labour-force window), unit PC_ACT
  (the rate's own denominator), sex T (the M/F splits are unwired
  doors one ref away), freq A only (the monthly companion refused:
  annualising is a derivation). 38 geos (EU + EFTA + Western Balkans
  + Türkiye; no UK — post-Brexit), 2003-2025, 1-decimal as
  published, the collector's b/d flags riding as-reported (d on FR
  and ES 2021-2025: the LFS questionnaire redesign — a DEFINITIONAL
  seam, surfaced not stitched; FX does not exist in this codelist,
  the French series is one continuous line). Witness: WB
  SL.UEM.TOTL.NE.ZS, the national-estimate line the probe
  fingerprinted as the ILOSTAT DEAP family redistributed by WDI —
  the root pair eurostat_lfs/ilo_lfs keeping the COVERAGE CLIFF
  (Germany 1991-2008 lives only on the witness; the collector starts
  DE at 2009) and the rounding seam (FRA 2024: 7.436 vs 7.4) reading
  as two doors, never a contradiction.
- **Eurostat, THREE MORE QUESTIONNAIRES** (collector tier, v18 — the
  connector that grew to eight datasets by v25, v26 leaving it at six)
  — the national accounts (nama_10_a10_e) and the LFS attainment
  table (edat_lfse_03), each wired as its own dispatch decision with
  its own ref grammar and layout pin-guard. (The v18 migration
  collection and its citizenship twin withdrew with their indicator
  in v26; the v25 class-decomposition twins — lfsa_urgan/urgacob —
  carry the same Todd question as rates.) THE INDUSTRIAL FINDING (the
  version's headline): the accounts door PRINTS the share of total
  employment by industry directly (unit PC_TOT_PER, na_item EMP_DC,
  nace_r2 B-E — the door's own aggregate, "Industry (except
  construction)"; FR 1995 = 16.4 -> 2024 = 10.1, DE 23.1 -> 17.5) —
  the finding that dissolved the composite-derived-layer question the
  backlog's head had waited on since v15: no derivation is needed
  because the collector prints the share. (v26 withdrew the
  agricultural twin — the nace-A pin, FR 4.4 -> 2.3 — with its
  indicator: a share without a defended direction; the door grammar
  keeps its A-pin test fixture.) The education pair rides the LFS
  attainment table (tertiary ED5-8, secondary ED3_4 the completed-
  secondary face, age Y25-64 — one questionnaire carrying three Todd
  metrics: unemployment, tertiary, secondary; UNESCO UIS, the world's
  education collector, has no live API, the probe record in
  sources.yaml). (The migration door that printed the foreign-born
  stock per country also withdrew with its indicator.) THE EA EDGE:
  nama's geo codelist carries
  the Euro-area aggregate as the bare two-letter code "EA" — the only
  two-letter aggregate in any wired Eurostat codelist, dropped logged
  by the connector's per-dataset table. Witnesses: the ILOEST modeled
  sector shares (WB, the compound seam — industry including
  construction on a modeled employment concept — displayed, never
  reconciled), the Barro-Lee/Lee-Lee long-run attainment panel via
  OWID's chart door (tertiary only — the corpus's own named source),
  and the UN DESA migrant-stock estimates (WB SM.POP.TOTL: FR 2024 =
  9.19M DESA vs 9.36M collector, the estimation seam).
- **World Bank Open Data / WDI** (harmonized tier, v11 — the phase-5
  provider) — UN IGME child-mortality codes and UN WPP life-expectancy
  codes as WITNESS series, sex-split through the provider's own code
  convention (SP.DYN.LE00.MA.IN / .FE.IN). WDI does not collect: it
  redistributes the modeling families' estimates, rounded to at most one
  decimal — the same roots through different doors, which is exactly
  what the `root` genealogy field (v11) makes visible: every source in
  the dist now declares its ultimate origin, and the catalog computes
  how many INDEPENDENT roots an indicator has (infant mortality: one
  harmonized root — UN IGME — behind four doors; life expectancy: two
  different roots, OWID's mixed long-run compilation vs pure WPP).
  Since v14 it also carries the fertility witness — SP.DYN.TFRT.IN,
  the WPP door beside the Eurostat collector: for the EU it anchors on
  the national series (FR 2022 prints 1.78 on both tiers), elsewhere
  it models what the collector never asked — the worldwide face of
  the corpus's #1 rides the modeled layer, next to a collector that
  never polled those countries.
  Since v12 it also carries the maternal bloc's MMEIG doors —
  SH.STA.MMRT (ratio) on maternal_mortality_ratio and SH.MMR.DTHS
  (modeled counts) on maternal_deaths, both bare codes (no sex
  dimension), integer print, annual 1985-2023: the ratio's witness tier
  is now TWO doors of ONE root carrying DIFFERENT ROUNDS of the model
  (OWID: the 2020 round, 1751-2020; WDI: the 2023 round) — the doors'
  divergence on overlapping years (South Sudan 1987: 6,774.7 vs 8,045)
  is the model's own revision, displayed, with the root field saying
  why they still agree in structure.

Layer model and sourcing rules: `docs/the-measurement-problem.md`,
`docs/adr/0007`, `docs/adr/0008`, `docs/adr/0009`.

# Status

🚧 Early stage.