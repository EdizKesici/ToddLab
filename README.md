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
  Wired as an edition loop: 12 editions (2011-2014 + 2017-2024), three
  file formats, covering 2007-2024 as-reported for infant mortality
  (Table 15) and life expectancy at birth (Table 4, sex-split as
  printed). Since v8 the collector's own annotations ride every point:
  quality codes, footnote texts, life-expectancy reference ranges.
- **WHO Mortality Database, via the OECD "Causes of mortality" dataflow**
  (collector tier) — cause-of-death registrations as submitted by member
  states (ICD-coded; Assault for the homicide rate), 49 countries,
  1960-2024, crude rates (the age-standardized variant is a derived
  measure and deliberately not used as canonical).
- **Curated tables** (in-repo, cited per point) — official or scholarly
  series no machine-readable collector redistributes (e.g. the Soviet
  official infant-mortality series).
- **Our World in Data / UN IGME, UNODC** (harmonized tier) — model
  estimates for cross-country comparability, displayed as witnesses
  beside the as-reported series, never blended with it.

Layer model and sourcing rules: `docs/the-measurement-problem.md`,
`docs/adr/0007`, `docs/adr/0008`.

# Status

🚧 Early stage.