"""Eurostat dissemination-API connector — the collector tier.

WHAT THIS SOURCE IS
Eurostat's questionnaire collections republish the SERIES THE NATIONAL
STATISTICAL OFFICES THEMSELVES COMPUTE AND PUBLISH, as reported by each
country — no modeling, no cross-country harmonization of definitions.
The same collector judgment as un_dyb (national official statistics
republished as reported) and OECD DF_COM (registrations as submitted);
the contrast with who_gho/worldbank (WPP/ILOEST redistributions) marks
the collector/harmonized line. Layer: collector.

FIVE DATASETS, FIVE QUESTIONNAIRES (one dispatch decision each — the
one-block-at-a-time scope of the DYB tables; the v14 design said
"another Eurostat dataset is another dispatch decision", and v17/v18
make exactly that decision three more times):

- demo_find, "Fertility indicators" (v14): the DEMOGRAPHY questionnaire.
  v14 wired the total fertility rate (indic_de=TOTFERRT, "births per
  woman" — the corpus's #1, 111 citations); v16 wired the second Todd
  metric this dataset carries: NMARPCT, "Proportion of live births
  outside marriage" (the corpus's illegitimate_births), printed
  DIRECTLY by the collector (no ratio derivation: the counts-based
  datasets demo_cnia carry no share, and the OECD Family Database is
  not on SDMX — the v14 finding). Root: eurostat_demo.

- une_rt_a, "Unemployment by sex and age - annual data" (v17): the
  LABOUR-FORCE questionnaire — the national official unemployment
  RATES as each statistical office computes them from its own LFS,
  printed at Eurostat's 1-decimal face. The corpus's unemployment_rate
  (20 citations, 7 books — L'invention de l'Europe's interwar Austria,
  Qui est Charlie ?'s France >10% structural claim, Les Luttes de
  classes' France-vs-Germany board). The v17 probe verdict that earned
  the wiring: NO other wire prints the plain national rate at the
  collector tier — ILOSTAT is wholesale ILO-processed (2EAP/2UNE =
  ILOEST modeled; 5EAP = 19th-ICLS WORK harmonized; DEAP/TUNE = the
  LFS/ILMS databases with "Repository: ILO-STATISTICS - Micro data
  processing" and LFS-ADJ adjusted series — verified live 2026-09-20),
  and the OECD doors are OECD-harmonized (DF_LFS_INDIC / IALFS
  re-timing) or registered-unemployment counts ("not comparable across
  countries" per their own description). Root: eurostat_lfs; witness =
  WB SL.UEM.TOTL.NE.ZS (root ilo_lfs, the ILO-processed LFS family
  redistributed by WDI).

- nama_10_a10_e, "Employment by main industry (NACE Rev.2) - national
  accounts - annual data" (v18): the NATIONAL-ACCOUNTS questionnaire —
  employment by industry AS EACH COUNTRY PRINTS IT IN ITS OWN NATIONAL
  ACCOUNTS, and (the finding that earned the wiring) the share of total
  employment PRINTED DIRECTLY at unit PC_TOT_PER — no ratio derivation
  anywhere. This DISSOLVES the composite-derived-layer question the
  backlog's head (industrial_employment_share, 30 citations, 5 books)
  had waited on since v15: the v15/v16 probe record said "no collector
  prints the %, ILO/OECD print counts" — true then, but the
  national-accounts door was never probed; v18 probed it and the
  collector tier stands (canonical B-E = the door's own "Industry
  (except construction)" aggregate; agricultural_employment_share
  rides the same door at nace A). Root: eurostat_na; witnesses = WB
  SL.IND.EMPL.ZS / SL.AGR.EMPL.ZS (root ilo_modelled — the ILOEST
  modeled shares, worldwide; the definitional seam B-E vs
  industry-including-construction displayed by the pair, never hidden).
  PINS (verified live 2026-09-21): na_item EMP_DC ("Total employment
  domestic concept" — the door also prints SAL_DC employees and
  SELF_DC self-employed, unwired), unit PC_TOT_PER ("percentage of
  total" — the door's OWN share unit; THS_PER is the counts face,
  I15_* the index face), nace_r2 the aggregate of the metric (B-E / A;
  the F construction share and the lfsa_egan2 counts door recorded
  unwired in sources.yaml). NO sex dimension in this cube (the layouts
  of the other datasets all carry one): nama employment is
  both-sexes-by-construction, every record sex=None. THE EA EDGE: this
  dataset's geo codelist carries the Euro-area aggregate as the bare
  TWO-LETTER code "EA" (44 geos probed live: EU27_2020, EA, EA21,
  EA20, EA19, EA12 + 38 countries incl. XK) — the only two-letter
  aggregate in any wired Eurostat codelist; it is dropped logged (see
  _DATASET_TWO_LETTER_AGGREGATES), the same aggregate treatment the
  longer codes get everywhere.

- edat_lfse_03, "Population in private households by educational
  attainment level" (v18): the LABOUR-FORCE questionnaire AGAIN (the
  LFS's attainment table — one questionnaire, three Todd metrics: the
  unemployment rate v17, the tertiary and secondary attainment shares
  v18). The corpus's education pair (tertiary_education_share 13
  citations — La Défaite de l'Occident's Barro-Lee reads; secondary
  8 — Qui est Charlie ?'s c.1945 US-vs-Europe comparison) waited on a
  collector door because the world's education collector (UNESCO UIS)
  has NO live API (probed live 2026-09-21: api.uis.unesco.org is a
  dead JSON shell, every SDMX path 404s; the old bulk endpoints
  DNS-dead — the probe record in sources.yaml). The LFS attainment
  table IS a collector print: the share of the adult population at
  each attainment level, from each country's own survey. PINS
  (verified live): isced11 ED5-8 (tertiary) / ED3_4 (upper secondary
  and post-secondary non-tertiary as HIGHEST attainment — the
  Barro-Lee "secondary" bucket's closest LFS face; ED3-8 "at least
  upper secondary" and the ED34_44/ED35_45 variants unwired, recorded
  in sources.yaml), age Y25-64 (the LFS's adult band; the Todd claim's
  70-74 cohort face rides the witness), sex T, unit PC (the dataset's
  ONLY unit — pinned in the URL and verified by the guard). Root:
  eurostat_lfs (the LFS questionnaire's own table); tertiary's
  witness = OWID's long-run attainment chart (root barro_lee, the
  Barro-Lee 2015 + Lee-Lee 2016 panels — the corpus's own named
  source; secondary has NO machine-readable witness: the OWID door
  exposes tertiary and mean-years only, probed 2026-09-21).

- migr_pop3ctb, "Population on 1 January by age group, sex and country
  of birth" (v18): the MIGRATION questionnaire — the foreign-born
  STOCK each country's own registration prints, pinned c_birth=FOR
  ("Foreign country" — the foreign-born total; the NAT/TOTAL and the
  300-code by-birth detail doors unwired, recorded in sources.yaml
  with the Todd by-origin question — Le Destin des immigrés'
  Maghreb/Turkish/Portuguese board — as the recorded future door:
  FR-by-MA/DZ/TN/TR/PT probed live, the codes exist and print,
  2015-2018 for the detailed French slices). The codelist's 45 geos
  (EU27_2020 + 44 countries incl. TR/UA/GE/AM/AZ/AD/MC — RICHER than
  the LFS door's, no EA-type edge, no XK). PINS (verified live):
  c_birth FOR, age TOTAL, sex T, unit NR (the dataset's only unit,
  pinned and guarded). Root: eurostat_migr; witness = WB SM.POP.TOTL
  (root un_desa — the UN DESA Trends in International Migrant Stock
  estimates, worldwide 1990-2024, the same harmonized-estimate relation
  WPP/GHE hold to their collectors).

THE une_rt_a PINS (verified live 2026-09-20, the probe record):
- age: the codelist carries SEVEN bands (Y15-24 ... Y55-74) and NO
  TOTAL — a query for age=TOTAL returns HTTP 200 with an EMPTY value
  object (the soft-miss pattern). Y15-74 is the broadest band, the
  LFS's own labour-force age window, and therefore the de-facto
  "total" rate. Pinning anything else would be a different indicator.
- unit: PC_ACT ("Percentage of population in the labour force") — the
  rate's own denominator; PC_POP exists (FR 2015 = 6.6, the wrong
  denominator), THS_PER is thousands of persons.
- sex: T (the both-sexes rate; M and F exist — the sex-split doors,
  probed live: FR M 2015 = 10.8, FR F = 9.9 — unwired, one ref away).
- freq: A only in this cube (the monthly companion une_rt_m exists and
  is refused: annualising monthly data is a derivation).

API SHAPE (verified live 2026-09-19/2026-09-20):
    GET {API}/{dataset}?format=JSON&lang=EN&<dataset's pin params>
    {"version": "1.0", "class": "dataset", "label": "...",
     "id": ["freq", <pinned dims...>, "geo", "time"],
     "size": [1, ..., 38, 23],
     "dimension": {...}, "value": {"0": 2.73, ...},
     "status": {"54": "b", ...}, "updated": "..."}

- Flat positions decode by strides over `id`'s dimension order (row-
  major). Cells with no observation are simply ABSENT from `value`
  (unlike the World Bank's grid, which prints explicit nulls) — both
  datasets contribute valued points only, no explicit gap rows.
- `status` carries the collector's own per-observation flags,
  documented by Eurostat: b = break in series, e = estimated,
  p = provisional, d = definition differs (see metadata), u = low
  reliability (combos occur). Transported AS-REPORTED: quality_code =
  the printed flag string, provisional = 'p' among its letters. Live
  slices: demo_find/TOTFERRT carries b/e/p (95 flagged cells over
  2,126); une_rt_a/Y15-74/PC_ACT/T carries b/d (34 flagged over 635 —
  d on FR and ES 2021-2025: the 2021 LFS questionnaire redesign, a
  DEFINITIONAL seam the connector surfaces, not a geo seam; no 'p' in
  this dataset).

THE GEO CODES (the provider's own codelist, quirks included):
- Two-letter country codes — mostly ISO2, EXCEPT: EL (Greece, Eurostat
  never adopted ISO's GR), UK (the UK never adopted ISO's GB), FX
  (Metropolitan France, Eurostat's series-variant code). pycountry
  knows none of the three (verified live) — the connector carries the
  explicit override table. In une_rt_a the codelist is EU+EFTA+Western
  Balkans+Türkiye (no UK: post-Brexit the LFS door stopped carrying
  it; no FX: probed empty).
- Longer codes are the codelist's aggregates and series variants:
  EU27_2020/EU28/EU27_2007/EA21/EA20/EEA31/EEA30_2007/EFTA (aggregates
  — dropped logged on every dataset) and DE_TOT ("Germany including
  former GDR" — a CODE-SPECIFIC case, both directions verified live:
  on TOTFERRT (2026-09-19) DE_TOT prints values IDENTICAL to DE on
  every one of the 25 overlapping years, so DE rides the unpinned
  slice and DE_TOT is the dropped duplicate; on NMARPCT (2026-09-20)
  the relationship REVERSES — DE_TOT is the FULL 65-year series while
  DE's 39 points include five pre-reunification FRG-only benchmarks
  that DIVERGE (1960: 6.3 vs 7.6; 1970: 5.5 vs 7.2; 1980: 7.6 vs
  11.9; 1985: 9.4 vs 16.2; 1990: 10.5 vs 15.3 — the GDR's high
  non-marital share the all-Germany print carries), so DE_TOT rides
  its own geo-pinned source (demo_find/NMARPCT/DE_TOT) and the merge
  arbitrates the German seam by priority, the FX/FR seam's exact
  architecture. une_rt_a carries NO German variant: its codelist has
  no DE_TOT (probed empty — the LFS questionnaire's Germany is one
  door, DE 2009-2025, the pre-2009 years living only on the witness).
- XK = Kosovo (v21): overridden to XKX, the user-assigned code the kosovo
  entity now carries as its iso3 — the v1-era pending product decision
  resolved; pre-2008 rows still drop on the entity's valid_from. (In
  une_rt_a the code is simply absent from the codelist: probed empty.)

THE FRANCE VARIANT PAIR (the demo_find FX/FR seam, the v14/v16 display
case): Eurostat prints TWO French series — FX "Metropolitan France"
1960-2012 (INSEE stopped the metro-only series) and FR "France"
1998-2024 (whole France including the overseas departments; values
differ slightly in the overlap: 2000 prints 1.87 metro vs 1.89 total).
Both are the collector's own prints; neither is a duplicate of the
other. The unpinned demo_find slice therefore DROPS FX and FR at parse
(logged — each rides its own geo-pinned source_ref), and the indicator
configs wire them separately with distinct priorities so merge.py
arbitrates the 1998-2012 overlap by vintage with every discarded value
logged in provenance — the standard vintage discipline. une_rt_a has
NO seam: FX does not exist in the codelist and FR is one continuous
2003-2025 series (the only discontinuity marker is the d flag from
2021, the LFS redesign, which rides quality_code as-reported).

SOURCE_REF FORMAT (one grammar per dataset — the OECD dataflow/cause
convention extended):
    demo_find/TOTFERRT           -> the whole all-countries slice
    demo_find/TOTFERRT/{geo}     -> one geo-pinned series (FX or FR)
    demo_find/NMARPCT            -> the NMARPCT all-countries slice
    demo_find/NMARPCT/{geo}      -> one geo-pinned series (DE_TOT/FR/FX)
    une_rt_a/{age}/{unit}/{sex}  -> the LFS rate slice (e.g.
                                    une_rt_a/Y15-74/PC_ACT/T; the M/F
                                    splits are the unwired sex doors)
    nama_10_a10_e/{na_item}/{unit}/{nace}
                                 -> the national-accounts share slice
                                    (e.g. nama_10_a10_e/EMP_DC/
                                    PC_TOT_PER/B-E; no sex dim)
    edat_lfse_03/{isced11}/{age}/{sex}
                                 -> the LFS attainment slice (e.g.
                                    edat_lfse_03/ED5-8/Y25-64/T; unit
                                    PC is the dataset's only unit, pinned
                                    in the URL and verified by the guard)
    migr_pop3ctb/{c_birth}/{age}/{sex}
                                 -> the foreign-born stock slice (e.g.
                                    migr_pop3ctb/FOR/TOTAL/T; unit NR
                                    pinned and verified)
    migr_pop3ctb/ROW/{geo}       -> v22: the BILATERAL row of one
                                    destination (e.g. migr_pop3ctb/ROW/FR
                                    — geo pinned, c_birth UNPINNED: the
                                    full by-birth codelist as printed,
                                    307 codes, age=TOTAL/sex=T/unit=NR
                                    pinned and verified). Each record
                                    carries the origin axis (RawRecord
                                    origin_raw_name/origin_iso3_raw); the
                                    64 non-country codes and the diagonal
                                    drop logged per class.
The dataset part selects the dispatch; the pins are validated against
the response (a pinned request must return EXACTLY what it asked for —
never ingest a slice we didn't ask for).

WHAT THE PARSER REFUSES (pin-guards, the OECD discipline):
- a response whose dimensions are not exactly the dataset's layout
  ([freq, indic_de, geo, time] / [freq, age, unit, sex, geo, time] /
  [freq, unit, nace_r2, na_item, geo, time] / [freq, sex, age, unit,
  isced11, geo, time] / [freq, c_birth, age, unit, sex, geo, time]) —
  a different dataset or layout is a loud failure, never a silent
  misparse;
- freq other than exactly {A: 0} (this connector serves annual series;
  the monthly une_rt_m family is refused by design);
- any pinned dimension not exactly the requested code;
- a geo-pinned response carrying any geo besides the pin;
- a time entry that is not a 4-digit year;
- zero country records after parse (unexpected API shape — this is
  also what catches the soft-miss pattern: an unknown geo code in the
  QUERY returns HTTP 200 with an empty value object, so a pinned ref
  for a code the codelist does not carry fails here, loudly).
SEX: demo_find and nama_10_a10_e have no sex dimension by construction
(TFR is a synthetic measure of women's lifetime fertility; NMARPCT is
a population-level share; the national-accounts employment cube is
both-sexes by construction) — every record carries sex=None. On
une_rt_a, edat_lfse_03 and migr_pop3ctb the pin IS the sex: T (the
both-sexes series) maps to sex=None (the project's both-sexes
convention — (entity, year, sex) is the merge key, so the sex-split
doors M/F, when ever wired, coexist without colliding).

"""
from __future__ import annotations

import json
import logging
import re

from src.connectors.base import Connector, RawFetchResult, RawRecord

EUROSTAT_API_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

# The one-ref grammar per dataset (v17: the second dispatch decision;
# v18: three more — nama, edat, migr).
# demo_find: {indic_de}[/{geo}]           une_rt_a: {age}/{unit}/{sex}
# nama_10_a10_e: {na_item}/{unit}/{nace}  edat_lfse_03: {isced11}/{age}/{sex}
# migr_pop3ctb: {c_birth}/{age}/{sex}
_EUROSTAT_DATASETS = ("demo_find", "une_rt_a", "nama_10_a10_e", "edat_lfse_03", "migr_pop3ctb")

# v18 (nama_10_a10_e): the Euro-area aggregate prints as the bare
# two-letter code "EA" in this dataset's geo codelist (verified live
# 2026-09-21 — the ONLY two-letter aggregate in any wired Eurostat
# codelist: demo_find/une_rt_a/edat/migr carry EU27_2020/EA21-class
# long codes only, probed). The generic country-code test
# (two uppercase letters) would mis-classify it and the pycountry
# lookup would fail loudly; instead it is dropped LOGGED here as the
# aggregate it is — the same treatment the longer aggregate codes get
# everywhere, with this table as the deliberate, per-dataset record.
_DATASET_TWO_LETTER_AGGREGATES: dict[str, frozenset[str]] = {
    "nama_10_a10_e": frozenset({"EA"}),
}

# The datasets whose grammar pins a SEX code (T/M/F) mapped through the
# shared table below: une_rt_a (v17), edat_lfse_03 and migr_pop3ctb (v18).
_SEXED_DATASETS = frozenset({"une_rt_a", "edat_lfse_03", "migr_pop3ctb"})

# The provider's own geo codelist quirks pycountry cannot answer (verified
# live 2026-09-19: pycountry returns nothing for FX/UK/EL/XK). XK (Kosovo)
# maps to XKX (v21): the USER-ASSIGNED ISO 3166-1 code the WB also prints —
# the pending product decision (v1-era) resolved on the kosovo entity,
# which now carries iso3: XKX. Pre-2008 rows still drop on valid_from.
EUROSTAT_GEO_TO_ISO3: dict[str, str] = {
    "EL": "GRC",  # Greece: Eurostat's own code, never ISO's GR
    "UK": "GBR",  # the UK: Eurostat's own code, never ISO's GB
    "FX": "FRA",  # Metropolitan France: Eurostat's series-variant code
    "XK": "XKX",  # Kosovo (v21): no ISO 3166-1 proper; XKX is the
    # user-assigned code (the WB's own countryiso3code for Kosovo) — the
    # kosovo entity declares iso3: XKX, so this lands on it exactly.
    "DE_TOT": "DEU",  # v16 (NMARPCT): "Germany including former GDR" —
    # a geo-pinned series door in its own right (NOT the TFR case's
    # verified duplicate: on NMARPCT DE_TOT is the FULLER 65-year series
    # and diverges from DE on the five pre-reunification benchmark years
    # — 1980: 11.9 all-Germany vs 7.6 FRG-only, the GDR's high
    # non-marital share; verified live 2026-09-20). Both German doors
    # resolve to Germany; the merge arbitrates them by priority.
}

# v22: migr_pop3ctb's own SUMMARY c_birth codes — the door's totals and
# residuals (FOR = the foreign-born total, the canonical v18 door's own
# pin; NAT = the native face; TOTAL; OTH/UNK/RNC = other/unknown/recent-
# non-classified). They drop from the ROW slice LOGGED: the totals already
# ride the pinned c_birth=FOR door, and the ROW slice exists to carry the
# per-origin decomposition, never to duplicate the total.
_MIGR_SUMMARY_CODES = frozenset({"FOR", "NAT", "TOTAL", "OTH", "UNK", "RNC"})

# v22: the ORIGIN-axis override (the c_birth codelist's own country quirks
# pycountry cannot answer — the same discipline as EUROSTAT_GEO_TO_ISO3
# on the destination axis): AN = the Netherlands Antilles, the ISO 3166-1
# alpha-2 code WITHDRAWN at the 2010 dissolution. Eurostat keeps printing
# it as a birth place (people born in the former entity, counted in the
# stock wherever they live now) — the netherlands_antilles entity carries
# its withdrawn alpha-3 ANT so the ISO3-first resolution lands on it
# exactly (the v21 kosovo/XKX precedent, the vanished-entity class).
_MIGR_ORIGIN_TO_ISO3: dict[str, str] = {
    "AN": "ANT",  # Netherlands Antilles (dissolved 2010; code withdrawn)
}

# The France variant pair, dropped from the demo_find all-countries slice
# because each rides its own geo-pinned source_ref (see module docstring).
_FRANCE_VARIANT_GEOS = ("FX", "FR")

# une_rt_a's sex pin -> the project's sex vocabulary (T = the both-sexes
# rate, the merge key's None; the M/F splits are the unwired sex doors).
_UNE_RT_A_SEX_TO_PROJECT: dict[str, str | None] = {"T": None, "M": "male", "F": "female"}

_DEMO_REF_RE = re.compile(
    r"^(?P<dataset>demo_find)/(?P<code>[A-Z0-9]+)(?:/(?P<geo>[A-Z0-9_]+))?$"
)
_UNE_REF_RE = re.compile(
    r"^(?P<dataset>une_rt_a)/(?P<age>Y[0-9]{1,2}-[0-9]{1,2})/(?P<unit>[A-Z_]+)/(?P<sex>[TMF])$"
)
# v18: nama's nace codes carry hyphens (B-E, G-I) and underscores (M_N);
# edat's isced11 codes carry hyphens (ED5-8, ED3-8) and underscores
# (ED3_4, ED34_44); migr's c_birth codes are plain (FOR/NAT/TOTAL) and
# its age pin reuses the TOTAL/Y25-64 shape (TOTAL is not matched by
# the Y..-.. pattern, hence its own class).
# v22: the ROW grammar — migr_pop3ctb/ROW/{geo}, the bilateral row of one
# destination (geo pinned, c_birth OPEN). Three segments, so it cannot
# collide with the four-segment pinned-c_birth grammar above; checked
# first so a future codelist code literally named 'ROW' (none exists —
# the codelist is countries + the 64 printed non-country codes) would
# never shadow the door.
_MIGR_ROW_REF_RE = re.compile(
    r"^(?P<dataset>migr_pop3ctb)/ROW/(?P<geo>[A-Z0-9_]+)$"
)
_NAMA_REF_RE = re.compile(
    r"^(?P<dataset>nama_10_a10_e)/(?P<na_item>[A-Z_]+)/(?P<unit>[A-Z_]+)/(?P<nace>[A-Z0-9][A-Z0-9_\-]*)$"
)
_EDAT_REF_RE = re.compile(
    r"^(?P<dataset>edat_lfse_03)/(?P<isced>[A-Z0-9][A-Z0-9_\-]*)/(?P<age>[A-Z0-9][A-Z0-9_\-]*)/(?P<sex>[TMF])$"
)
_MIGR_REF_RE = re.compile(
    r"^(?P<dataset>migr_pop3ctb)/(?P<c_birth>[A-Z0-9_]+)/(?P<age>[A-Z0-9][A-Z0-9_\-]*)/(?P<sex>[TMF])$"
)

logger = logging.getLogger(__name__)


def _parse_ref(source_ref: str) -> dict:
    """'demo_find/TOTFERRT' -> {dataset, pins: {indic_de: TOTFERRT}, geo: None};
    'demo_find/TOTFERRT/FX' -> the geo-pinned variant;
    'une_rt_a/Y15-74/PC_ACT/T' -> {dataset, pins: {age, unit, sex}, geo: None};
    'nama_10_a10_e/EMP_DC/PC_TOT_PER/B-E' -> {dataset, pins: {na_item,
    unit, nace_r2}, geo: None};
    'edat_lfse_03/ED5-8/Y25-64/T' -> {dataset, pins: {isced11, age, sex,
    unit(PC — the dataset's only unit, pinned deliberately)}, geo: None};
    'migr_pop3ctb/FOR/TOTAL/T' -> {dataset, pins: {c_birth, age, sex,
    unit(NR — the dataset's only unit)}, geo: None}.
    Raises on any other shape — including an unknown dataset, which this
    connector refuses by design (one dispatch decision per dataset)."""
    m = _DEMO_REF_RE.match(source_ref)
    if m:
        return {
            "dataset": "demo_find",
            "pins": {"indic_de": m.group("code")},
            "geo": m.group("geo"),
        }
    m = _UNE_REF_RE.match(source_ref)
    if m:
        return {
            "dataset": "une_rt_a",
            "pins": {"age": m.group("age"), "unit": m.group("unit"), "sex": m.group("sex")},
            "geo": None,
        }
    m = _NAMA_REF_RE.match(source_ref)
    if m:
        return {
            "dataset": "nama_10_a10_e",
            "pins": {
                "na_item": m.group("na_item"),
                "unit": m.group("unit"),
                "nace_r2": m.group("nace"),
            },
            "geo": None,
        }
    m = _EDAT_REF_RE.match(source_ref)
    if m:
        return {
            "dataset": "edat_lfse_03",
            "pins": {
                "isced11": m.group("isced"),
                "age": m.group("age"),
                "sex": m.group("sex"),
                # the dataset's ONLY unit (verified live 2026-09-21):
                # pinned in the URL and verified by the layout guard —
                # an API change that introduces a second unit is a loud
                # failure, never a silent re-interpretation.
                "unit": "PC",
            },
            "geo": None,
        }
    m = _MIGR_ROW_REF_RE.match(source_ref)
    if m:
        return {
            "dataset": "migr_pop3ctb",
            "pins": {
                # the ROW frame (verified live 2026-09-22, the v22 probe):
                # age=TOTAL, sex=T, unit=NR — pinned in the URL and verified
                # by the layout guard; c_birth is deliberately UNPINNED (the
                # by-birth codelist as printed, 307 codes).
                "age": "TOTAL",
                "sex": "T",
                "unit": "NR",
            },
            "geo": m.group("geo"),
            "bilateral": True,
        }
    m = _MIGR_REF_RE.match(source_ref)
    if m:
        return {
            "dataset": "migr_pop3ctb",
            "pins": {
                "c_birth": m.group("c_birth"),
                "age": m.group("age"),
                "sex": m.group("sex"),
                # the dataset's ONLY unit (verified live 2026-09-21).
                "unit": "NR",
            },
            "geo": None,
        }
    raise ValueError(
        f"Invalid Eurostat source_ref {source_ref!r}: expected "
        f"'demo_find/<indic_de code>' (all countries) or "
        f"'demo_find/<code>/<geo>' (one geo-pinned series), or "
        f"'une_rt_a/<age>/<unit>/<sex>' (the LFS rate slice, e.g. "
        f"une_rt_a/Y15-74/PC_ACT/T), or "
        f"'nama_10_a10_e/<na_item>/<unit>/<nace>' (the national-accounts "
        f"share slice, e.g. nama_10_a10_e/EMP_DC/PC_TOT_PER/B-E), or "
        f"'edat_lfse_03/<isced11>/<age>/<sex>' (the LFS attainment slice, "
        f"e.g. edat_lfse_03/ED5-8/Y25-64/T), or "
        f"'migr_pop3ctb/<c_birth>/<age>/<sex>' (the foreign-born stock "
        f"slice, e.g. migr_pop3ctb/FOR/TOTAL/T), or "
        f"'migr_pop3ctb/ROW/<geo>' (the bilateral by-origin row of one "
        f"destination, e.g. migr_pop3ctb/ROW/FR — v22)."
    )


def build_url(source_ref: str) -> str:
    ref = _parse_ref(source_ref)
    params = "?format=JSON&lang=EN"
    if ref["dataset"] == "demo_find":
        params += f"&indic_de={ref['pins']['indic_de']}"
        if ref["geo"]:
            params += f"&geo={ref['geo']}"
    elif ref["dataset"] == "une_rt_a":
        params += f"&age={ref['pins']['age']}&unit={ref['pins']['unit']}&sex={ref['pins']['sex']}"
    elif ref["dataset"] == "nama_10_a10_e":
        params += (
            f"&na_item={ref['pins']['na_item']}"
            f"&unit={ref['pins']['unit']}"
            f"&nace_r2={ref['pins']['nace_r2']}"
        )
    elif ref["dataset"] == "edat_lfse_03":
        params += (
            f"&isced11={ref['pins']['isced11']}"
            f"&age={ref['pins']['age']}"
            f"&sex={ref['pins']['sex']}"
            f"&unit={ref['pins']['unit']}"
        )
    elif ref.get("bilateral"):  # migr_pop3ctb/ROW/{geo}: geo PINNED in the
        # URL, c_birth deliberately absent (the by-birth codelist as
        # printed) — verified live 2026-09-22: 32,976 bytes for FR, 1,450
        # non-empty cells, the 307-code c_birth dimension riding along.
        params += (
            f"&geo={ref['geo']}"
            f"&age={ref['pins']['age']}"
            f"&sex={ref['pins']['sex']}"
            f"&unit={ref['pins']['unit']}"
        )
    else:  # migr_pop3ctb
        params += (
            f"&c_birth={ref['pins']['c_birth']}"
            f"&age={ref['pins']['age']}"
            f"&sex={ref['pins']['sex']}"
            f"&unit={ref['pins']['unit']}"
        )
    return f"{EUROSTAT_API_URL}/{ref['dataset']}{params}"


def _strides(dim_order: list[str], sizes: dict[str, int]) -> dict[str, int]:
    """Flat-position strides for the response's own dimension order
    (row-major over `id`)."""
    strides: dict[str, int] = {}
    mult = 1
    for dim in reversed(dim_order):
        strides[dim] = mult
        mult *= sizes[dim]
    return strides


def _validate_layout(payload: dict, ref: dict) -> dict:
    """The dataset-specific pin-guards: exact dimension order, annual
    freq, every pinned dimension exactly the requested code, and (for
    geo-pinned refs) the geo dimension exactly the pin. Returns the
    parsed dimension indexes/labels the record loop needs."""
    dataset = ref["dataset"]
    _DATASET_LAYOUTS: dict[str, list[str]] = {
        "demo_find": ["freq", "indic_de", "geo", "time"],
        "une_rt_a": ["freq", "age", "unit", "sex", "geo", "time"],
        "nama_10_a10_e": ["freq", "unit", "nace_r2", "na_item", "geo", "time"],
        "edat_lfse_03": ["freq", "sex", "age", "unit", "isced11", "geo", "time"],
        "migr_pop3ctb": ["freq", "c_birth", "age", "unit", "sex", "geo", "time"],
    }
    expected_dims = _DATASET_LAYOUTS[dataset]
    dim_order = payload.get("id")
    if dim_order != expected_dims:
        raise ValueError(
            f"Eurostat response dimensions {dim_order!r} are not the {dataset} "
            f"layout {expected_dims} — refusing to guess the slice."
        )
    size = payload.get("size")
    if not isinstance(size, list) or len(size) != len(expected_dims):
        raise ValueError(
            f"Eurostat response without a {len(expected_dims)}-entry size: {size!r}"
        )

    dimension = payload.get("dimension")
    if not isinstance(dimension, dict):
        raise ValueError("Eurostat response without a 'dimension' object: unexpected API shape")
    try:
        freq_index = dimension["freq"]["category"]["index"]
        geo_index = dimension["geo"]["category"]["index"]
        geo_labels = dimension["geo"]["category"]["label"]
        time_index = dimension["time"]["category"]["index"]
        pinned_indexes = {d: dimension[d]["category"]["index"] for d in ref["pins"]}
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Eurostat response with an incomplete dimension block: {exc}") from None

    if freq_index != {"A": 0}:
        raise ValueError(
            f"Eurostat freq dimension {freq_index!r} is not exactly annual (A) — "
            "this connector serves annual series only."
        )
    for dim, code in ref["pins"].items():
        if pinned_indexes[dim] != {code: 0}:
            raise ValueError(
                f"Eurostat {dim} dimension {pinned_indexes[dim]!r} does not match the requested "
                f"code {code!r} — refusing to ingest a slice we did not ask for."
            )
    geo_pin = ref["geo"]
    if geo_pin is not None and geo_index != {geo_pin: 0}:
        raise ValueError(
            f"Geo-pinned request returned geo dimension {geo_index!r} — "
            "refusing a slice carrying more (or less) than the pinned series."
        )
    return {
        "dim_order": dim_order,
        "size": size,
        "geo_index": geo_index,
        "geo_labels": geo_labels,
        "time_index": time_index,
    }


def parse_eurostat(json_text: str, expected_ref: str) -> list[RawRecord]:
    """Pure function: one Eurostat JSON response -> RawRecords (countries
    only; aggregates, the German variant door and — on the demo_find
    unpinned slice — the French variant pair dropped, each with a log
    line). `expected_ref` is the pin: the response's pinned dimensions
    must BE the requested codes, and a geo-pinned ref must receive
    exactly its own geo.

    v22 (the ROW grammar): a `migr_pop3ctb/ROW/{geo}` response instead
    yields the BILATERAL row of the pinned destination — every record
    carrying the origin axis (origin_raw_name/origin_iso3_raw), with the
    door's own non-country c_birth classes dropped logged per class
    (aggregates/regions, the FOR/NAT/TOTAL/OTH/UNK/RNC summary codes,
    and the c_birth == geo diagonal — the native face)."""
    ref = _parse_ref(expected_ref)
    bilateral = bool(ref.get("bilateral"))

    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Not Eurostat JSON: {exc}") from None
    if not isinstance(payload, dict):
        raise ValueError("Eurostat response is not an object: unexpected API shape")

    layout = _validate_layout(payload, ref)
    dim_order, size = layout["dim_order"], layout["size"]
    geo_index, geo_labels = layout["geo_index"], layout["geo_labels"]
    time_index = layout["time_index"]

    inv_geo = {position: code for code, position in geo_index.items()}
    inv_time = {position: year for year, position in time_index.items()}
    for year in inv_time.values():
        if not (isinstance(year, str) and len(year) == 4 and year.isdigit()):
            raise ValueError(f"Eurostat time entry {year!r} is not a 4-digit year.")

    values = payload.get("value")
    if not isinstance(values, dict):
        raise ValueError("Eurostat response without a 'value' object: unexpected API shape")
    status = payload.get("status") or {}
    if not isinstance(status, dict):
        raise ValueError(f"Eurostat 'status' is not an object: {status!r}")

    sizes = dict(zip(dim_order, size))
    strides = _strides(dim_order, sizes)
    # v18: the sex pin rides une_rt_a, edat_lfse_03 and migr_pop3ctb alike
    # (T -> None, the both-sexes convention; M/F the unwired sex doors).
    sex_from_pin = (
        _UNE_RT_A_SEX_TO_PROJECT.get(ref["pins"].get("sex"))
        if ref["dataset"] in _SEXED_DATASETS
        else None
    )

    # v22 (the ROW grammar): the c_birth dimension is OPEN (the by-birth
    # codelist as printed — 307 codes on the FR row, verified live
    # 2026-09-22). Its index/labels are read here with the same loud-
    # failure discipline as the shared dimensions; the record loop then
    # decodes the origin axis per cell (row-major over the response's own
    # dimension order — the general (position // stride) % size decode,
    # required here because c_birth and geo sit at DIFFERENT strides than
    # the pinned-c_birth layout the historical arithmetic assumed).
    inv_cb: dict[int, str] = {}
    cb_labels: dict[str, str] = {}
    if bilateral:
        try:
            c_birth_index = payload["dimension"]["c_birth"]["category"]["index"]
            cb_labels = payload["dimension"]["c_birth"]["category"]["label"]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Eurostat response with an incomplete c_birth block: {exc}") from None
        inv_cb = {position: code for code, position in c_birth_index.items()}

    records: list[RawRecord] = []
    dropped_aggregates = 0
    dropped_german_variant = 0
    dropped_france_variants = 0
    # v22: the ROW slice's own drop classes (per-cell, see the classification
    # below — each logged with its own count after the loop).
    dropped_origin_aggregates = 0
    dropped_origin_summary = 0
    dropped_diagonal = 0
    for position_text, value in values.items():
        try:
            position = int(position_text)
        except (TypeError, ValueError):
            raise ValueError(f"Eurostat value position {position_text!r} is not an integer.") from None
        if bilateral:
            # The ROW layout is [freq, c_birth, age, unit, sex, geo, time]
            # with ONLY c_birth open besides time — the general row-major
            # decode below is exact for it (and equivalent to the pinned
            # layout's arithmetic on every pre-v22 grammar, which keeps its
            # own historical branch below untouched).
            c_birth = inv_cb.get((position // strides["c_birth"]) % sizes["c_birth"])
            geo = inv_geo.get((position // strides["geo"]) % sizes["geo"])
            year = inv_time.get((position // strides["time"]) % sizes["time"])
            if geo is None or year is None or c_birth is None:
                raise ValueError(f"Eurostat value position {position} decodes to no (geo, c_birth, time).")
        else:
            geo = inv_geo.get(position // strides["geo"])
            year = inv_time.get((position % strides["geo"]) // strides["time"])
            c_birth = None
            if geo is None or year is None:
                raise ValueError(f"Eurostat value position {position} decodes to no (geo, time).")

        # The provider's own codelist shape: exactly two uppercase letters
        # = a country code; anything longer = aggregate or series variant.
        # v18 exception (nama_10_a10_e): the Euro-area aggregate prints as
        # the bare two-letter code "EA" — the per-dataset aggregate table
        # catches it BEFORE the country test mis-classifies it (see
        # _DATASET_TWO_LETTER_AGGREGATES for the live-verified record).
        two_letter_aggregates = _DATASET_TWO_LETTER_AGGREGATES.get(ref["dataset"], frozenset())
        is_country_code = (
            len(geo) == 2 and geo.isalpha() and geo.isupper() and geo not in two_letter_aggregates
        )
        if ref["geo"] is None:
            if not is_country_code:
                if geo == "DE_TOT":
                    # Dropped from the UNPINNED slice on every dataset where
                    # the code exists — the REASON is code-specific per
                    # dataset/code (verified live):
                    # - demo_find/TOTFERRT (2026-09-19): DE_TOT is the
                    #   duplicate — values identical to DE on all 25
                    #   overlapping years; DE rides the unpinned slice.
                    # - demo_find/NMARPCT (2026-09-20): DE_TOT is the SERIES
                    #   DOOR — the full 65-year "including former GDR" print
                    #   that DIVERGES from DE's FRG-only pre-1991 benchmarks
                    #   — it rides its own geo-pinned source_ref
                    #   (demo_find/NMARPCT/DE_TOT) and wins by priority.
                    # - une_rt_a (2026-09-20): the code does not exist in
                    #   this codelist at all (probed empty — one German
                    #   door, DE 2009-2025), so this branch never fires.
                    dropped_german_variant += 1
                else:
                    dropped_aggregates += 1
                continue
            if ref["dataset"] == "demo_find" and geo in _FRANCE_VARIANT_GEOS:
                # FX/FR ride their own geo-pinned source_refs; the log line
                # is the record of the drop (v11.1 discipline). une_rt_a
                # carries neither code (FX probed empty; FR is the only
                # French series, 2003-2025, no seam).
                dropped_france_variants += 1
                continue

        # v22 (the ROW grammar): classify the ORIGIN axis before emitting.
        # The three drop classes are the door's own printed vocabulary
        # (verified live 2026-09-22, the 64 non-country codes enumerated in
        # the probe): aggregates/regions (EUR, EU*, EFTA, AFR_*, AME_*,
        # ASI_*, OCE_*, the FR91-94 French regions, the *_FOR variants,
        # CC*/EXT/EX_* constructions), the summary codes (FOR/NAT/TOTAL/
        # OTH/UNK/RNC — the totals ride the pinned c_birth=FOR door), and
        # the diagonal (c_birth == geo — the native-born face: FR<-FR is
        # NAT's mirror per origin, 58,610,164 at FR 2016, verified live).
        origin_raw_name: str | None = None
        origin_iso3: str | None = None
        if bilateral:
            if c_birth == geo:
                dropped_diagonal += 1
                continue
            is_origin_country = (
                len(c_birth) == 2 and c_birth.isalpha() and c_birth.isupper()
                and c_birth not in two_letter_aggregates
            )
            if not is_origin_country:
                if c_birth in _MIGR_SUMMARY_CODES:
                    dropped_origin_summary += 1
                else:
                    dropped_origin_aggregates += 1
                continue
            origin_label = cb_labels.get(c_birth)
            if not isinstance(origin_label, str) or not origin_label:
                raise ValueError(f"Eurostat c_birth code {c_birth!r} without a label: unexpected API shape.")
            origin_iso3 = _MIGR_ORIGIN_TO_ISO3.get(c_birth) or EUROSTAT_GEO_TO_ISO3.get(c_birth)
            if origin_iso3 is None:
                import pycountry  # local import: same discipline as the geo axis

                origin_country = pycountry.countries.get(alpha_2=c_birth)
                origin_iso3 = origin_country.alpha_3 if origin_country else None
            if origin_iso3 is None:
                # A two-letter origin code neither table nor pycountry
                # answers is a codelist surprise (AN rides the origin
                # override table, v22; EL/UK/XK ride the shared geo table)
                # — loud failure, never a guess.
                raise ValueError(
                    f"Eurostat c_birth code {c_birth!r} is neither in the origin override tables "
                    "nor resolvable by pycountry — extend _MIGR_ORIGIN_TO_ISO3 deliberately."
                )
            origin_raw_name = origin_label

        iso3 = EUROSTAT_GEO_TO_ISO3.get(geo)
        raw_name = geo_labels.get(geo)
        if not isinstance(raw_name, str) or not raw_name:
            raise ValueError(f"Eurostat geo code {geo!r} without a label: unexpected API shape.")
        if iso3 is None:
            import pycountry  # local import: keep this module importable in pure-parsing tests

            country = pycountry.countries.get(alpha_2=geo)
            iso3 = country.alpha_3 if country else None
            if iso3 is None:
                # A two-letter code neither table nor pycountry answers is a
                # codelist surprise (Kosovo XK now rides the override table,
                # v21) — loud failure, never a guessed mapping.
                raise ValueError(
                    f"Eurostat geo code {geo!r} is neither in the override table nor "
                    "resolvable by pycountry — extend EUROSTAT_GEO_TO_ISO3 deliberately."
                )

        flag = status.get(position_text)
        if flag is not None and not isinstance(flag, str):
            raise ValueError(f"Eurostat status flag {flag!r} is not a string.")
        if value is not None and not isinstance(value, (int, float)):
            raise ValueError(f"Eurostat value is neither number nor null: {value!r}")

        records.append(
            RawRecord(
                entity_raw_name=raw_name,
                iso3_raw=iso3,
                year=int(year),
                value=float(value) if value is not None else None,
                origin_raw_name=origin_raw_name,
                origin_iso3_raw=origin_iso3,
                sex=sex_from_pin,
                quality_code=flag or None,
                provisional=bool(flag) and "p" in flag,
            )
        )

    if ref["geo"] is None:
        if dropped_aggregates:
            logger.info(
                "Eurostat: dropped %d aggregate row(s) (EU/EA/EEA/EFTA — the provider's "
                "own codelist codes that are not two-letter country codes; v18 note: on "
                "nama_10_a10_e this INCLUDES the bare two-letter code 'EA', the Euro-area "
                "aggregate — see _DATASET_TWO_LETTER_AGGREGATES).",
                dropped_aggregates,
            )
        if dropped_german_variant:
            if ref["dataset"] == "demo_find" and ref["pins"]["indic_de"] == "TOTFERRT":
                logger.info(
                    "Eurostat: dropped %d DE_TOT row(s) from the unpinned slice (the TFR case: "
                    "values identical to DE on every overlapping year, verified live 2026-09-19; "
                    "DE is the wired German door).",
                    dropped_german_variant,
                )
            elif ref["dataset"] == "demo_find":
                logger.info(
                    "Eurostat: dropped %d DE_TOT row(s) from the unpinned slice (%s: the German "
                    "series door rides its own geo-pinned source_ref, demo_find/%s/DE_TOT — "
                    "verified live 2026-09-20 to be the FULLER series, diverging from DE on the "
                    "pre-reunification benchmark years; the merge arbitrates by priority, the "
                    "FX/FR seam's architecture).",
                    dropped_german_variant,
                    ref["pins"]["indic_de"],
                    ref["pins"]["indic_de"],
                )
        if dropped_france_variants:
            logger.info(
                "Eurostat: dropped %d France variant row(s) (FX metropolitan / FR whole — "
                "each series rides its own geo-pinned source_ref, "
                "demo_find/%s/FX and demo_find/%s/FR).",
                dropped_france_variants,
                ref["pins"].get("indic_de", "?"),
                ref["pins"].get("indic_de", "?"),
            )
    if bilateral:
        # v22: the ROW slice's own drop record — one line per class, the
        # destination's geo pinned in each (the counts are CELLS, not codes:
        # one aggregate code can print on many years).
        if dropped_origin_aggregates:
            logger.info(
                "Eurostat: dropped %d aggregate/region origin cell(s) from the ROW slice of "
                "geo %s (the c_birth codelist's own non-country codes: EUR/EU*/EFTA, AFR_*/"
                "AME_*/ASI_*/OCE_* regions, the FR91-94 French regions, the *_FOR variants, "
                "CC*/EXT/EX_* constructions — verified live 2026-09-22).",
                dropped_origin_aggregates,
                ref["geo"],
            )
        if dropped_origin_summary:
            logger.info(
                "Eurostat: dropped %d summary-code cell(s) from the ROW slice of geo %s "
                "(FOR/NAT/TOTAL/OTH/UNK/RNC — the door's own totals; the foreign-born "
                "total already rides the pinned c_birth=FOR door, migr_pop3ctb/FOR/TOTAL/T).",
                dropped_origin_summary,
                ref["geo"],
            )
        if dropped_diagonal:
            logger.info(
                "Eurostat: dropped %d diagonal cell(s) from the ROW slice of geo %s "
                "(c_birth == geo — the native-born face of the destination, NAT's mirror "
                "per origin; the by-origin layer carries the FOREIGN-born decomposition only).",
                dropped_diagonal,
                ref["geo"],
            )
    if not records:
        raise ValueError(
            "Eurostat payload yielded zero country rows: unexpected API shape "
            "(or the geo pin swallowed everything — the soft-miss pattern: a "
            "codelist code the dataset does not carry answers HTTP 200 with "
            "an empty value object)."
        )
    return records


class EurostatConnector(Connector):
    provider = "eurostat"

    def __init__(self, session=None, timeout: int = 120):
        self._session = session
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": "toddlab-pipeline/0.1 (contact: see README)"}

    def fetch_raw(self, source_ref: str, indicator_id: str, field: str | None = None) -> RawFetchResult:
        import requests  # local import: keep this module importable in pure-parsing tests

        if field is not None:
            raise ValueError(
                f"Eurostat source_ref {source_ref!r} carries a 'field' ({field!r}) — this "
                "provider selects series through the ref's pins, never through field."
            )
        session = self._session or requests
        url = build_url(source_ref)
        response = session.get(url, headers=self._headers(), timeout=self._timeout)
        response.raise_for_status()
        records = parse_eurostat(response.text, expected_ref=source_ref)
        return RawFetchResult(
            provider=self.provider,
            source_ref=source_ref,
            indicator_id=indicator_id,
            fetched_at=RawFetchResult.now_iso(),
            source_url=url,
            records=records,
        )
