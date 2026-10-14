"""UNESCO Institute for Statistics (UIS) connector - the harmonized tier.

WHAT THIS SOURCE IS
The UIS Data API (api.uis.unesco.org, public, no auth, JSON) serves the
education indicators the UIS compiles: educational attainment rates, mean
years of schooling, literacy... The numbers come from national population
censuses and household surveys (national statistical offices, MICS, DHS),
mapped by the UIS to the ISCED classification; the UIS completes them with
its own calculations. It is therefore a harmonized-tier source (an
international institution recalculating national material), never a
collector of figures "as published": the project classifies `unesco_uis` as
`harmonized` in PROVIDER_LAYER and the indicators it feeds as
`canonical_nature: modelled` when it is their source of record (decision 20's
rule: anything an international institution recalculates is an estimate).

LICENSE: the UIS terms of use state CC BY-SA 4.0 with a mandatory credit
line (UNESCO Institute for Statistics, URL, date of extraction).

API SHAPE (verified live 2026-10-14):
    GET https://api.uis.unesco.org/api/public/data/indicators
        ?indicator={code}&geoUnitType=NATIONAL&start=1970&end=2030
    {"hints": [], "records": [
        {"indicatorId": "MYS.1T8.AG25T99", "geoUnit": "ABW", "year": 1991,
         "value": 6.92, "magnitude": null, "qualifier": null}, ...],
     "indicatorMetadata": []}

- geoUnitType=NATIONAL keeps the country level (ISO3 codes, no aggregates);
- an unknown indicator code is NOT an HTTP error: it answers
  {"hints": [{"code": "UIS::HINT::001", "message": "The indicator could not
  be found, X"}], "records": []} - the parser raises on it (loud failure);
- the sex split lives in the code suffix (.F female, .M male), the bare
  code is both sexes; every row's indicatorId must equal the code asked for
  (the pin-guard: never ingest a slice we did not request);
- `magnitude` and `qualifier` are null on every row of the wired indicators
  (the UIS prints no per-point provenance on this wire - a documented limit,
  not an oversight): a non-null one is carried nowhere and logged.
"""
from __future__ import annotations

import json
import logging

from src.connectors.base import Connector, RawFetchResult, RawRecord

UIS_API_URL = "https://api.uis.unesco.org/api/public/data/indicators"
UIS_START, UIS_END = 1970, 2030

logger = logging.getLogger(__name__)


def build_url(code: str) -> str:
    return f"{UIS_API_URL}?indicator={code}&geoUnitType=NATIONAL&start={UIS_START}&end={UIS_END}"


def _sex_from_code(code: str) -> str | None:
    if code.endswith(".F"):
        return "female"
    if code.endswith(".M"):
        return "male"
    return None


def parse_uis(text: str, expected_code: str) -> list[RawRecord]:
    """Pure function: one UIS data response -> RawRecords."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Not UIS JSON: {exc}") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise ValueError("UIS response without a 'records' list: unexpected API shape")
    records_in = payload["records"]
    if not records_in:
        hints = payload.get("hints")
        raise ValueError(
            f"UIS answered zero records for {expected_code!r} (hints: {hints!r}) - "
            "unknown indicator code or an empty slice."
        )

    sex = _sex_from_code(expected_code)
    out: list[RawRecord] = []
    n_flagged = 0
    for row in records_in:
        if not isinstance(row, dict):
            raise ValueError(f"UIS record is not an object: {row!r}")
        if row.get("indicatorId") != expected_code:
            raise ValueError(
                f"UIS record carries indicator {row.get('indicatorId')!r} where "
                f"{expected_code!r} was requested - refusing to ingest a slice we did not ask for."
            )
        geo = row.get("geoUnit")
        if not isinstance(geo, str) or len(geo) != 3 or not geo.isalpha():
            raise ValueError(f"UIS record without an ISO3 geoUnit: {row!r}")
        year = row.get("year")
        if not isinstance(year, int) or isinstance(year, bool):
            raise ValueError(f"UIS record with a non-integer year: {row!r}")
        value = row.get("value")
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise ValueError(f"UIS value is neither number nor null: {value!r}")
        if row.get("magnitude") is not None or row.get("qualifier") is not None:
            n_flagged += 1
        out.append(
            RawRecord(
                entity_raw_name=geo,
                iso3_raw=geo,
                year=year,
                value=float(value) if value is not None else None,
                sex=sex,
            )
        )
    if n_flagged:
        logger.warning("UIS %s: %d record(s) carry a magnitude/qualifier flag (not transported)", expected_code, n_flagged)
    return out


class UnescoUisConnector(Connector):
    provider = "unesco_uis"

    def __init__(self, session=None, timeout: int = 120):
        self._session = session
        self._timeout = timeout

    def fetch_raw(self, source_ref: str, indicator_id: str, field: str | None = None) -> RawFetchResult:
        import requests  # local import: keep this module importable in pure-parsing tests

        session = self._session or requests
        response = session.get(
            build_url(source_ref),
            headers={"User-Agent": "toddlab-pipeline/0.1 (contact: see README)"},
            timeout=self._timeout,
        )
        response.raise_for_status()
        return RawFetchResult(
            provider=self.provider,
            source_ref=source_ref,
            indicator_id=indicator_id,
            fetched_at=RawFetchResult.now_iso(),
            source_url=build_url(source_ref),
            records=parse_uis(response.text, expected_code=source_ref),
        )
