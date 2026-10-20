# Licenses and credits

Mandatory to display in the frontend for any data coming from these
sources (cross-cutting brief requirement). Filled in as providers get
added — only OWID is active in phase 1.

## Our World in Data (active)

- License: CC BY 4.0 (data). OWID's text and visualizations sometimes carry
  a different license — not relevant here since we only pull raw data CSVs.
- Credit to display: `dist/indicators/{id}.json` doesn't yet embed the full
  original-author citation (e.g. "UN IGME (2025) - processed by Our World
  in Data") — **to add in phase 2** as a `citation_text` field on
  `Indicator` (flagged in the initial architecture review, not yet
  implemented in this pilot). For now, `license: CC-BY-4.0` is the only
  available field.
- Source page link to display: easy to reconstruct from `source_ref` (e.g.
  `infant-mortality` -> `https://ourworldindata.org/grapher/infant-mortality`).

## UNESCO Institute for Statistics (active)

- License: CC BY-SA 4.0 (UIS terms of use, databrowser.uis.unesco.org).
  ShareAlike: the dist files carrying UIS data (`mean_years_of_schooling`)
  are published under the same terms.
- Credit to display: "UNESCO Institute for Statistics (UIS), URL, date of
  extraction" - the indicator file's `sources[]` block carries the citation
  and the license.

## WHO/Europe Data Warehouse, Health for All database (active)

- License: CC BY-NC-SA 3.0 IGO - **an inference**: the Gateway footer's
  "Data sharing license" link leads to the WHO copyright page, where WHO
  materials are CC BY-NC-SA 3.0 IGO; the HFA-DB dataset page states no license
  of its own. NonCommercial and ShareAlike apply: the `abortion_rate` dist
  file must stay non-commercial and under the same terms. The owner decided on
  2026-10-14 (decision 23) that ToddLab will never be commercial, so the
  NonCommercial condition holds; were that ever to change, this source needs a
  permission request to WHO/Europe.
- Credit to display: WHO/Europe, European Health for All database, measure
  `HFA_586`, and the national source named in the Data Warehouse's country
  notes - the indicator file's `sources[]` block carries the citation.

## World Bank, WHO GHO (active)

- World Bank Open Data: CC BY 4.0. WHO Global Health Observatory: CC BY 3.0
  IGO (the licenses carried by `PROVIDER_LICENSE` in `src/schema/indicator.py`).
  Each indicator file's `sources[]` block carries the citation.

## HMD (dropped), CLIO-INFRA (set aside for now)

HMD: dropped on 2026-10-09 — Ediz will not create an account, so it is
no longer a planned source; nothing to license or credit.
CLIO-INFRA: deliberately set aside — see the conversation: its specific
licensing/redistribution questions were not investigated.
