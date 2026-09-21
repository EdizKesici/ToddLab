"""World Bank Open Data (WDI) connector — the harmonized tier (P5).

WHAT THIS SOURCE IS
The World Bank's World Development Indicators, served by the v2 REST API
(no auth, JSON). Its content is LAYER-3 harmonized estimates — WDI does
not collect: it redistributes the modeling families' series (UN IGME for
the child-mortality codes, UN WPP for the life-expectancy codes). The
project therefore classifies `worldbank` as `harmonized` in
PROVIDER_LAYER and uses it as a WITNESS, never as a canonical source
(ADR-0007/0008). The `root` genealogy field (v11) exists precisely for
this provider: three doors (OWID, WDI, GHO) can carry ONE root.

API SHAPE (verified live 2026-09-13):
    GET https://api.worldbank.org/v2/country/all/indicator/{code}
        ?format=json&per_page=5000&page=N
    [ {"page": 1, "pages": 4, "per_page": 5000, "total": 17490},
      [ {"indicator": {"id": "SP.DYN.IMRT.MA.IN",
           "value": "Mortality rate, infant, male (per 1,000 live births)"},
         "country": {"id": "RU", "value": "Russian Federation"},
         "countryiso3code": "RUS", "date": "1990", "value": 17.5,
         "unit": "", "obs_status": "", "decimal": 0}, ... ] ]

- Pagination: meta[0].pages; per_page=5000 verified accepted live (the
  wired codes answer ~17.5k rows in 4 pages). The documented default is
  50 — every page must be requested explicitly.
- /country/all includes the 78 AGGREGATE entities (World, regions,
  income groups) beside the 217 countries. Data rows carry no region
  field: the provider's own classification lives in the /country
  metadata endpoint (region.id == "NA" == "Aggregates"). The join needs
  BOTH keys: regional aggregates carry their ISO3-like code in
  countryiso3code, but the income groups print an EMPTY iso3 and join on
  the two-letter country.id instead (verified live: 'High income' = HIC
  arrives as id 'XD' with countryiso3code ''). The connector fetches the
  classification once and the parser drops the rows matching either
  key, with counts logged — the same judgment as GHO's SpatialDimType
  filter (the provider's classification, not ours). Kosovo and the
  Channel Islands are NOT aggregates in that classification: they flow
  to normalize's unresolved report by name — a pending product decision,
  the same class as OWID's OWID_KOS pseudo-codes, not a bug. The dropped
  aggregate rows are not kept anywhere: the classification is
  re-fetchable from source_url, and the honest record of what was
  dropped is the log line.
- countryiso3code is the real ISO3 (RUS) — normalize resolves through
  the registry's ISO3 index; the printed name rides entity_raw_name for
  the unresolved report.
- SEX BY CODE SUFFIX (the WDI convention): the split lives in separate
  codes — SP.DYN.LE00.MA.IN male, SP.DYN.LE00.FE.IN female, the bare
  code both sexes. The parser derives the sex from the suffix AND
  cross-checks it against the indicator NAME every row carries
  ("..., male (per 1,000 live births)"): a mismatch raises (the OECD
  pin-guard precedent — never ingest a slice we didn't ask for, never
  mislabel a both-sexes row as sex-split). Bidirectional: a name that
  prints a sex the suffix doesn't declare raises too.
- A null value (the WDI year slot exists, no estimate yet — the trailing
  2025 rows) stays an explicit gap point: value=None, never a skip, the
  same honest treatment as a GHO null estimate.
- The date field is the year as a 4-char string; anything else raises
  (this connector serves annual series only).
- PRECISION (verified live, the genealogy footnote that earns the
  witness's keep): WDI redistributes IGME/WPP ROUNDED to at most one
  decimal — France 2020 female IMR prints 3 where OWID/GHO carry
  3.3304706/3.330470548; Russia 1990 prints 17.5 where GHO carries
  17.461960157. Same root, coarser print: the divergence display will
  show it, and the catalog's root field says why they agree anyway.
"""
from __future__ import annotations

import json
import logging

from src.connectors.base import Connector, RawFetchResult, RawRecord

WB_API_URL = "https://api.worldbank.org/v2"
WB_COUNTRY_META_URL = WB_API_URL + "/country?format=json&per_page=1000"
# Verified live 2026-09-13: accepted, and answers the wired codes (~17.5k
# rows) in 4 pages. A polite request count, not a stress on the API.
PER_PAGE = 5000

logger = logging.getLogger(__name__)


def build_url(code: str) -> str:
    return f"{WB_API_URL}/country/all/indicator/{code}?format=json&per_page={PER_PAGE}"


def _wb_payload(text: str, what: str) -> tuple[dict, list]:
    """One WB v2 page text -> (meta, rows), validated. The API answers a
    2-element array [meta, rows]; anything else (including its error
    object {"message": [...]}) is a shape surprise — loud failure."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Not World Bank JSON ({what}): {exc}") from None
    if not isinstance(payload, list) or len(payload) != 2 or not isinstance(payload[0], dict) or not isinstance(payload[1], list):
        raise ValueError(f"World Bank {what} without the [meta, rows] pair: unexpected API shape")
    return payload[0], payload[1]


def _pages_of(meta: dict) -> int:
    try:
        return int(meta["pages"])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"World Bank meta without an integer 'pages': {meta!r}") from None


def parse_country_meta(page_text: str) -> set[str]:
    """Pure function: one /country metadata page -> the identifiers of
    the entities the provider itself classifies as AGGREGATES
    (region.id == "NA"), in BOTH joinable forms: the metadata `id` (the
    ISO3-like code the regional aggregates carry in the data rows'
    countryiso3code) AND the metadata `iso2Code` (which the income-group
    aggregates join on instead — their data rows print an EMPTY
    countryiso3code, verified live: 'High income' HIC arrives as
    country.id 'XD' with iso3 '')."""
    _, rows = _wb_payload(page_text, "country metadata")
    aggregates: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"World Bank country metadata row is not an object: {row!r}")
        region = row.get("region")
        if isinstance(region, dict) and region.get("id") == "NA":
            for key in ("id", "iso2Code"):
                value = row.get(key)
                if not isinstance(value, str) or not value:
                    raise ValueError(f"Aggregate row without a {key}: {row!r}")
                aggregates.add(value)
    return aggregates


def _sex_from_code(code: str) -> str | None:
    """The WDI code-suffix convention: .MA.IN = male, .FE.IN = female,
    anything else (the bare code, a non-.IN code) = no sex declared."""
    if code.endswith(".MA.IN"):
        return "male"
    if code.endswith(".FE.IN"):
        return "female"
    return None


def _sex_printed_in_name(name: str) -> str | None:
    # The indicator names print the split as ", male (...)" / ", female (...)"
    # (verified live on the SP.DYN.* family). ", female (" does NOT contain
    # ", male (" — the check is unambiguous.
    for sex in ("male", "female"):
        if f", {sex} (" in name:
            return sex
    return None


def parse_wb(page_texts: list[str], aggregate_ids: set[str], expected_code: str) -> list[RawRecord]:
    """Pure function: all data page texts + the aggregate classification ->
    RawRecords (countries only, aggregates dropped with a log count).

    `expected_code` is the pin-guard: every row's indicator.id must equal
    the code we asked for — a response for any other indicator raises
    (never ingest a slice we didn't request)."""
    records: list[RawRecord] = []
    skipped_aggregates = 0
    seen_code: set[str] = set()
    for page_text in page_texts:
        _, rows = _wb_payload(page_text, "data page")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"World Bank data row is not an object: {row!r}")
            indicator = row.get("indicator")
            if not isinstance(indicator, dict) or not isinstance(indicator.get("id"), str):
                raise ValueError(f"World Bank row without an indicator id: {row!r}")
            code = indicator["id"]
            if code != expected_code:
                raise ValueError(
                    f"World Bank row carries indicator {code!r} where {expected_code!r} was "
                    "requested — refusing to ingest a slice we did not ask for."
                )
            seen_code.add(code)

            country = row.get("country")
            if not isinstance(country, dict) or not isinstance(country.get("value"), str):
                raise ValueError(f"World Bank row without a country name: {row!r}")
            country_id = country.get("id")
            if not isinstance(country_id, str) or not country_id:
                raise ValueError(f"World Bank row without a country id: {row!r}")
            iso3 = row.get("countryiso3code")
            if not isinstance(iso3, str):
                raise ValueError(f"World Bank row without a string countryiso3code: {row!r}")
            # The provider's own aggregate classification, in both joinable
            # forms: regional aggregates join on their ISO3-like code, the
            # income groups join on the two-letter id (their data rows print
            # an EMPTY countryiso3code — verified live, that is how 'High
            # income' reaches this parser). Kosovo and the Channel Islands
            # are NOT aggregates (real territories in the provider's own
            # classification): they flow on to normalize's unresolved report
            # — a product decision, not a parse decision.
            if iso3 in aggregate_ids or country_id in aggregate_ids:
                skipped_aggregates += 1
                continue

            date = row.get("date")
            if not isinstance(date, str) or len(date) != 4 or not date.isdigit():
                raise ValueError(
                    f"World Bank row with non-annual date {date!r}: this connector "
                    "places rows in years only (4-digit strings)."
                )

            sex = _sex_from_code(code)
            name = indicator.get("value")
            if not isinstance(name, str):
                raise ValueError(f"World Bank row without an indicator name: {row!r}")
            printed = _sex_printed_in_name(name)
            if sex != printed:
                raise ValueError(
                    f"World Bank code/name sex mismatch on {code!r} ({name!r}): the suffix "
                    f"says {sex!r} where the printed name says {printed!r} — refusing to "
                    "guess which one is the truth about this slice."
                )

            value = row.get("value")
            if value is not None and not isinstance(value, (int, float)):
                raise ValueError(f"World Bank value is neither number nor null: {value!r}")

            records.append(
                RawRecord(
                    entity_raw_name=country["value"],
                    iso3_raw=iso3 or None,
                    year=int(date),
                    value=float(value) if value is not None else None,
                    sex=sex,
                )
            )

    if skipped_aggregates:
        logger.info(
            "World Bank: skipped %d aggregate row(s) (World/regions/income groups — the "
            "provider's own /country classification, region 'Aggregates').",
            skipped_aggregates,
        )
    if not records:
        raise ValueError(
            "World Bank payload yielded zero country rows: unexpected API shape "
            "(or the aggregate classification swallowed everything)."
        )
    return records


class WorldbankConnector(Connector):
    provider = "worldbank"

    def __init__(self, session=None, timeout: int = 120):
        self._session = session
        self._timeout = timeout
        # The provider's aggregate classification, fetched once per connector
        # instance (it is request metadata, not indicator data).
        self._aggregate_ids: set[str] | None = None

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": "toddlab-pipeline/0.1 (contact: see README)"}

    def _fetch_aggregate_ids(self, session) -> set[str]:
        aggregate_ids: set[str] = set()
        page = 1
        while True:
            response = session.get(
                WB_COUNTRY_META_URL + f"&page={page}", headers=self._headers(), timeout=self._timeout
            )
            response.raise_for_status()
            meta, _ = _wb_payload(response.text, "country metadata")
            aggregate_ids |= parse_country_meta(response.text)
            pages = _pages_of(meta)
            if page >= pages:
                return aggregate_ids
            page += 1

    def fetch_raw(self, source_ref: str, indicator_id: str, field: str | None = None) -> RawFetchResult:
        import requests  # local import: keep this module importable in pure-parsing tests

        session = self._session or requests
        if self._aggregate_ids is None:
            self._aggregate_ids = self._fetch_aggregate_ids(session)

        page_texts: list[str] = []
        page = 1
        while True:
            url = build_url(source_ref) + f"&page={page}"
            response = session.get(url, headers=self._headers(), timeout=self._timeout)
            response.raise_for_status()
            page_texts.append(response.text)
            meta, _ = _wb_payload(response.text, "data page")
            pages = _pages_of(meta)
            if page >= pages:
                break
            page += 1

        records = parse_wb(page_texts, self._aggregate_ids, expected_code=source_ref)
        return RawFetchResult(
            provider=self.provider,
            source_ref=source_ref,
            indicator_id=indicator_id,
            fetched_at=RawFetchResult.now_iso(),
            source_url=build_url(source_ref),
            records=records,
        )
