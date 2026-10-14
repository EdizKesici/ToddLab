"""WHO/Europe Data Warehouse connector (dw.euro.who.int, API v5) - the
European Health for All database (HFA-DB), collector tier.

WHAT THIS SOURCE IS
Since the mid-1980s the Member States of the WHO European Region report
health statistics to WHO/Europe; the Data Warehouse (DW) redistributes them,
country by country, as reported (its per-country notes name the national
ministry or statistical office behind each series). That is a collector
tier: national official figures republished by an international collector,
the same judgment as Eurostat, the OECD DF_COM entry and the UN DYB - never
a model (the DW also holds population-weighted GROUP averages, which this
connector refuses to read as countries).

API SHAPE (verified live 2026-10-14):
    GET https://dw.euro.who.int/api/v5/measures/HFA_586
    {"code": "HFA_586", "short_name": "Abortions per 1000 live births",
     "metadata": [{"code": "UNIT_TYPE", "value": {"code": "PROC_1000LBIRTH"}}],
     "dimensions": [{"code": "COUNTRY", "values": [{"code": "ALB", "iso3": "ALB",
                     "short_name": "Albania"}, ...]}, ...],
     "data": [{"attributes": {"MEASURE_TYPE": "RATE"},
               "dimensions": {"COUNTRY": "ALB", "COUNTRY_GRP": "", "SEX": "ALL",
                              "YEAR": "1980"},
               "value": {"display": "225", "numeric": 225.13}}, ...]}

- COUNTRY rows carry MEASURE_TYPE RATE and an empty COUNTRY_GRP; group rows
  (COUNTRY empty, COUNTRY_GRP e.g. EU_MEMBERS, MEASURE_TYPE AVG_PW) are
  population-weighted averages, not countries: dropped and counted;
- the response's `code` must equal the measure asked for, and its UNIT_TYPE
  must be the unit the project registered for it (the pin-guards: never
  ingest another measure, never ingest a silently re-united one);
- the numeric value is read, never the rounded display string.

TLS NOTE (verified live 2026-10-14): the DW server sends its leaf
certificate WITHOUT the intermediate (Sectigo Public Server Authentication
CA DV R36), so a default client stops with "unable to get local issuer
certificate". The fix keeps full verification: the intermediate (public,
sha256 8C:54:C3:34:...:22:E0, expires 2036-03-21, issued by Sectigo Public
Server Authentication Root R46 which the system / certifi stores trust) is
shipped in src/connectors/certs/ and added as an extra trust anchor for THIS
host only. Chain and hostname checks stay on; if the server ever changes
issuer, the fetch fails loudly rather than downgrading to verify=False.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from src.connectors.base import Connector, RawFetchResult, RawRecord

DW_API_URL = "https://dw.euro.who.int/api/v5/measures"
DW_HOST = "https://dw.euro.who.int"
_INTERMEDIATE_PEM = Path(__file__).parent / "certs" / "sectigo_dv_r36.pem"

# measure code -> the UNIT_TYPE the project registered for it (pin-guard)
EXPECTED_UNITS: dict[str, str] = {
    "HFA_586": "PROC_1000LBIRTH",  # Abortions per 1000 live births
}
_REF_RE = re.compile(r"^HFA_[0-9]+$")
_COUNTRY_RE = re.compile(r"^[A-Z]{3}$")


def build_url(ref: str) -> str:
    if not _REF_RE.match(ref):
        raise ValueError(f"Invalid WHO/Europe DW source_ref {ref!r} (expected HFA_<number>, e.g. HFA_586)")
    return f"{DW_API_URL}/{ref}"


def _unit_of(payload: dict) -> str | None:
    for attr in payload.get("metadata") or []:
        if isinstance(attr, dict) and attr.get("code") == "UNIT_TYPE":
            value = attr.get("value")
            return value.get("code") if isinstance(value, dict) else None
    return None


def parse_who_euro(text: str, expected_ref: str) -> list[RawRecord]:
    """Pure function: one DW measure response -> RawRecords."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Not WHO/Europe DW JSON: {exc}") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("WHO/Europe DW response without a 'data' list: unexpected API shape")
    if payload.get("code") != expected_ref:
        raise ValueError(
            f"WHO/Europe DW answered measure {payload.get('code')!r} where {expected_ref!r} "
            "was requested - refusing to ingest a slice we did not ask for."
        )
    expected_unit = EXPECTED_UNITS.get(expected_ref)
    if expected_unit is None:
        raise ValueError(f"No registered unit for measure {expected_ref!r}: add it to EXPECTED_UNITS first")
    unit = _unit_of(payload)
    if unit != expected_unit:
        raise ValueError(f"WHO/Europe DW unit for {expected_ref} is {unit!r}, expected {expected_unit!r} - refusing to ingest")

    names: dict[str, tuple[str, str]] = {}
    for dim in payload.get("dimensions") or []:
        if isinstance(dim, dict) and dim.get("code") == "COUNTRY":
            for v in dim.get("values") or []:
                iso3 = v.get("iso3")
                if isinstance(iso3, str) and _COUNTRY_RE.match(iso3):
                    names[v["code"]] = (iso3, v.get("short_name") or iso3)
    if not names:
        raise ValueError("WHO/Europe DW response without a COUNTRY dimension table")

    out: list[RawRecord] = []
    seen: set[tuple[str, int]] = set()
    for row in payload["data"]:
        if not isinstance(row, dict):
            raise ValueError(f"WHO/Europe DW row is not an object: {row!r}")
        dims = row.get("dimensions") or {}
        attrs = row.get("attributes") or {}
        if dims.get("COUNTRY") in (None, "") or dims.get("COUNTRY_GRP") not in (None, ""):
            continue  # a country-group aggregate (population-weighted average), not a country
        if attrs.get("MEASURE_TYPE") != "RATE":
            raise ValueError(f"Unexpected MEASURE_TYPE on a country row: {attrs!r}")
        if dims.get("SEX") != "ALL":
            raise ValueError(f"Unexpected SEX on a country row: {dims!r}")
        code = dims["COUNTRY"]
        if code not in names:
            raise ValueError(f"Country code {code!r} missing from the response's COUNTRY table")
        try:
            year = int(dims["YEAR"])
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"WHO/Europe DW row with a non-integer YEAR: {row!r}") from None
        value = (row.get("value") or {}).get("numeric")
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise ValueError(f"WHO/Europe DW numeric value is neither number nor null: {value!r}")
        if (code, year) in seen:
            raise ValueError(f"Duplicate WHO/Europe DW observation for {code} {year}")
        seen.add((code, year))
        iso3, short_name = names[code]
        out.append(
            RawRecord(
                entity_raw_name=short_name,
                iso3_raw=iso3,
                year=year,
                value=float(value) if value is not None else None,
            )
        )
    if not out:
        raise ValueError(f"WHO/Europe DW answered no country rows for {expected_ref!r}")
    return out


def make_session():
    """A requests session whose DW host trusts the shipped intermediate (see TLS NOTE)."""
    import ssl

    import certifi  # a requests dependency, always present
    import requests
    from requests.adapters import HTTPAdapter

    pem = _INTERMEDIATE_PEM.read_text(encoding="ascii")

    class _DwAdapter(HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            ctx = ssl.create_default_context(cafile=certifi.where())
            ctx.load_verify_locations(cadata=pem)
            kwargs["ssl_context"] = ctx
            super().init_poolmanager(*args, **kwargs)

    session = requests.Session()
    session.mount(DW_HOST, _DwAdapter())
    return session


class WhoEuroConnector(Connector):
    provider = "who_euro"

    def __init__(self, session=None, timeout: int = 180):
        self._session = session
        self._timeout = timeout

    def fetch_raw(self, source_ref: str, indicator_id: str, field: str | None = None) -> RawFetchResult:
        session = self._session or make_session()
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
            records=parse_who_euro(response.text, expected_ref=source_ref),
        )
