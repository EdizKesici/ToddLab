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

## World Bank, WHO GHO (phase 2, not active yet)

To fill in once the connectors are written.

## HMD (dropped), CLIO-INFRA (set aside for now)

HMD: dropped on 2026-10-09 — Ediz will not create an account, so it is
no longer a planned source; nothing to license or credit.
CLIO-INFRA: deliberately set aside — see the conversation: its specific
licensing/redistribution questions were not investigated.
