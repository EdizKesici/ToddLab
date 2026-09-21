"""Eurostat dissemination-API connector — the collector tier.

WHAT THIS SOURCE IS
Eurostat's questionnaire collections republish the SERIES THE NATIONAL
STATISTICAL OFFICES THEMSELVES COMPUTE AND PUBLISH, as reported by each
country — no modeling, no cross-country harmonization of definitions.
The same collector judgment as un_dyb (national official statistics
republished as reported) and OECD DF_COM (registrations as submitted);
the contrast with who_gho/worldbank (WPP/ILOEST redistributions) marks
the collector/harmonized line. Layer: collector.

TWO DATASETS, TWO QUESTIONNAIRES (one dispatch decision each — the
one-block-at-a-time scope of the DYB tables; the v14 design said
"another Eurostat dataset is another dispatch decision", and v17 makes
exactly that decision for the labour-force collection):

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
- XK = Kosovo, no ISO3: deliberately given NO override so it flows to
  normalize's unresolved report by name — the same pending product
  decision class as the World Bank's Kosovo. (In une_rt_a the code is
  simply absent from the codelist: probed empty.)

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
The dataset part selects the dispatch; the pins are validated against
the response (a pinned request must return EXACTLY what it asked for —
never ingest a slice we didn't ask for).

WHAT THE PARSER REFUSES (pin-guards, the OECD discipline):
- a response whose dimensions are not exactly the dataset's layout
  ([freq, indic_de, geo, time] / [freq, age, unit, sex, geo, time]) —
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
SEX: demo_find has no sex split by construction (TFR is a synthetic
measure of women's lifetime fertility; NMARPCT is a population-level
share) — every record carries sex=None. une_rt_a's pin IS the sex: T
(the both-sexes rate) maps to sex=None (the project's both-sexes
convention — (entity, year, sex) is the merge key, so the sex-split
doors M/F, when ever wired, coexist without colliding).
"""
from __future__ import annotations

import json
import logging
import re

from src.connectors.base import Connector, RawFetchResult, RawRecord

EUROSTAT_API_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

# The one-ref grammar per dataset (v17: the second dispatch decision).
# demo_find: {indic_de}[/{geo}]   une_rt_a: {age}/{unit}/{sex}
_EUROSTAT_DATASETS = ("demo_find", "une_rt_a")

# The provider's own geo codelist quirks pycountry cannot answer (verified
# live 2026-09-19: pycountry returns nothing for FX/UK/EL/XK). XK
# (Kosovo) is deliberately ABSENT: it has no ISO3, so it flows to
# normalize's unresolved report by name — the same pending product
# decision as the World Bank's Kosovo, not a parse decision.
EUROSTAT_GEO_TO_ISO3: dict[str, str] = {
    "EL": "GRC",  # Greece: Eurostat's own code, never ISO's GR
    "UK": "GBR",  # the UK: Eurostat's own code, never ISO's GB
    "FX": "FRA",  # Metropolitan France: Eurostat's series-variant code
    "DE_TOT": "DEU",  # v16 (NMARPCT): "Germany including former GDR" —
    # a geo-pinned series door in its own right (NOT the TFR case's
    # verified duplicate: on NMARPCT DE_TOT is the FULLER 65-year series
    # and diverges from DE on the five pre-reunification benchmark years
    # — 1980: 11.9 all-Germany vs 7.6 FRG-only, the GDR's high
    # non-marital share; verified live 2026-09-20). Both German doors
    # resolve to Germany; the merge arbitrates them by priority.
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

logger = logging.getLogger(__name__)


def _parse_ref(source_ref: str) -> dict:
    """'demo_find/TOTFERRT' -> {dataset, pins: {indic_de: TOTFERRT}, geo: None};
    'demo_find/TOTFERRT/FX' -> the geo-pinned variant;
    'une_rt_a/Y15-74/PC_ACT/T' -> {dataset, pins: {age, unit, sex}, geo: None}.
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
    raise ValueError(
        f"Invalid Eurostat source_ref {source_ref!r}: expected "
        f"'demo_find/<indic_de code>' (all countries) or "
        f"'demo_find/<code>/<geo>' (one geo-pinned series), or "
        f"'une_rt_a/<age>/<unit>/<sex>' (the LFS rate slice, e.g. "
        f"une_rt_a/Y15-74/PC_ACT/T)."
    )


def build_url(source_ref: str) -> str:
    ref = _parse_ref(source_ref)
    params = "?format=JSON&lang=EN"
    if ref["dataset"] == "demo_find":
        params += f"&indic_de={ref['pins']['indic_de']}"
        if ref["geo"]:
            params += f"&geo={ref['geo']}"
    else:
        params += f"&age={ref['pins']['age']}&unit={ref['pins']['unit']}&sex={ref['pins']['sex']}"
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
    expected_dims = (
        ["freq", "indic_de", "geo", "time"]
        if dataset == "demo_find"
        else ["freq", "age", "unit", "sex", "geo", "time"]
    )
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
    exactly its own geo."""
    ref = _parse_ref(expected_ref)

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
    sex_from_pin = _UNE_RT_A_SEX_TO_PROJECT.get(ref["pins"].get("sex")) if ref["dataset"] == "une_rt_a" else None

    records: list[RawRecord] = []
    dropped_aggregates = 0
    dropped_german_variant = 0
    dropped_france_variants = 0
    for position_text, value in values.items():
        try:
            position = int(position_text)
        except (TypeError, ValueError):
            raise ValueError(f"Eurostat value position {position_text!r} is not an integer.") from None
        geo = inv_geo.get(position // strides["geo"])
        year = inv_time.get((position % strides["geo"]) // strides["time"])
        if geo is None or year is None:
            raise ValueError(f"Eurostat value position {position} decodes to no (geo, time).")

        # The provider's own codelist shape: exactly two uppercase letters
        # = a country code; anything longer = aggregate or series variant.
        is_country_code = len(geo) == 2 and geo.isalpha() and geo.isupper()
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

        iso3 = EUROSTAT_GEO_TO_ISO3.get(geo)
        raw_name = geo_labels.get(geo)
        if not isinstance(raw_name, str) or not raw_name:
            raise ValueError(f"Eurostat geo code {geo!r} without a label: unexpected API shape.")
        if iso3 is None:
            import pycountry  # local import: keep this module importable in pure-parsing tests

            country = pycountry.countries.get(alpha_2=geo)
            iso3 = country.alpha_3 if country else None
            if iso3 is None and geo != "XK":
                # A two-letter code pycountry cannot answer is a codelist
                # surprise (only Kosovo is expected to take the unresolved
                # path) — loud failure, never a guessed mapping.
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
                sex=sex_from_pin,
                quality_code=flag or None,
                provisional=bool(flag) and "p" in flag,
            )
        )

    if ref["geo"] is None:
        if dropped_aggregates:
            logger.info(
                "Eurostat: dropped %d aggregate row(s) (EU/EA/EEA/EFTA — the provider's "
                "own codelist codes that are not two-letter country codes).",
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
