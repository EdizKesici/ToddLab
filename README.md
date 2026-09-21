# ToddLab

## The hard indicators of societies.

ToddLab is an open-source tool for comparing countries using hard social indicators such as mortality, health, education or demography rather than monetary aggregates or opinion surveys.

## Why?

GDP, rankings and composite scores tell us what is declared or monetized, not necessarily what is real. ToddLab is built on a simple idea: some things cannot lie.

The project takes inspiration from the method of historian-demographer Emmanuel Todd, who famously predicted the collapse of the USSR in 1976 by tracking a single hard indicator: rising infant mortality.

## What it does

Compare countries side by side on hard indicators (infant mortality, life expectancy, fertility, homicides, education...).

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
  self-harm for the suicide rate — v13, the corpus's #2 by citations),
  49 countries on homicide / 46 on suicide, 1960-2024, crude rates (the
  age-standardized variant is a derived measure and deliberately not
  used as canonical). The two causes share one architecture: the OECD
  dataflow carries 50 death-cause codes, each one config away.
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
  otherwise — riding every row's note). The curation gate's probe
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
  of reclassification sensitivity in the project.
- **Eurostat, Fertility indicators** (collector tier, v14 — the
  fertility canonical; v16 — the illégitimité too) — the series the
  national statistical offices themselves compute and publish,
  collected by Eurostat via its own questionnaire. TWO Todd metrics
  ride the one dataset now: the total fertility rate (demo_find's
  TOTFERRT, "births per woman" — v14, the one collector wire that
  prints a national TFR, verified live before any config) and the
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