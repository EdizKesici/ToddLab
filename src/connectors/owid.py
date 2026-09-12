"""Our World in Data connector.

Uses OWID's public grapher CSV URLs (no auth, no API key). This is the
simplest, best-documented entry point into OWID; the `owid-catalog` library
(richer indicators/tables API with structured metadata) is a candidate for
a future iteration if the number of indicators grows — see docs/architecture.md.

Expected CSV format (confirmed against the live OWID API/CSV at time of
writing, including via a real network audit — see CHANGELOG):
    Entity,Code,Year,<Human-readable variable name>
    France,FRA,1950,52.0
    USSR,OWID_USS,1950,168.0
`Code` is a real ISO3 for actual countries. For aggregates, regions, income
groups, and historical/disputed entities without a formal ISO3 (USSR,
Kosovo, "World"...), OWID uses "OWID_"-prefixed pseudo-codes (e.g.
OWID_USS, OWID_KOS, OWID_WRL) rather than leaving the field empty — this
was wrong in an earlier version of this docstring. Either way, `Code` may
still be blank for some rows; both cases are handled identically by
`parse_csv` (iso3_raw = the raw string, or None if blank), and entity
resolution falls back to matching by name when there is no ISO3 hit — see
`EntityRegistry.resolve_from_source`.
"""
from __future__ import annotations

import csv
import io

from src.connectors.base import Connector, RawFetchResult, RawRecord

GRAPHER_CSV_URL = "https://ourworldindata.org/grapher/{slug}.csv?v=1&csvType=full&useColumnShortNames=false"


def build_url(slug: str) -> str:
    return GRAPHER_CSV_URL.format(slug=slug)


def parse_csv(csv_text: str, *, value_field: str | None = None) -> list[RawRecord]:
    """Pure function: CSV text -> list of RawRecord. No network access.

    Raises ValueError if the value column can't be determined unambiguously
    — better to fail loudly here than guess the wrong column in a
    multi-variable CSV.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        raise ValueError("Empty or unreadable CSV")

    fixed_cols = {"Entity", "Code", "Year"}
    missing_fixed = fixed_cols - set(reader.fieldnames)
    if missing_fixed:
        raise ValueError(f"Expected columns missing from OWID CSV: {missing_fixed}")

    value_cols = [c for c in reader.fieldnames if c not in fixed_cols]
    if value_field:
        if value_field not in value_cols:
            raise ValueError(f"Column '{value_field}' not found. Available value columns: {value_cols}")
        target_col = value_field
    elif len(value_cols) == 1:
        target_col = value_cols[0]
    else:
        raise ValueError(
            f"Multi-variable CSV ({value_cols}): set 'field' in the indicator config to resolve the ambiguity."
        )

    records: list[RawRecord] = []
    for row in reader:
        raw_value = row.get(target_col, "").strip()
        value = float(raw_value) if raw_value not in ("", "..", "NA", "N/A") else None
        year_raw = row["Year"].strip()
        if not year_raw:
            continue  # row with no usable year: skip it rather than aborting the whole fetch
        records.append(
            RawRecord(
                entity_raw_name=row["Entity"].strip(),
                iso3_raw=(row["Code"].strip() or None),
                year=int(float(year_raw)),
                value=value,
            )
        )
    return records


class OwidConnector(Connector):
    provider = "owid"

    def __init__(self, session=None, timeout: int = 30):
        self._session = session
        self._timeout = timeout

    def fetch_raw(self, source_ref: str, indicator_id: str, field: str | None = None) -> RawFetchResult:
        import requests  # local import: keep this module importable even if `requests` is absent in pure-parsing tests

        url = build_url(source_ref)
        session = self._session or requests
        response = session.get(
            url,
            headers={"User-Agent": "toddlab-pipeline/0.1 (contact: see README)"},
            timeout=self._timeout,
        )
        response.raise_for_status()
        records = parse_csv(response.text, value_field=field)
        return RawFetchResult(
            provider=self.provider,
            source_ref=source_ref,
            indicator_id=indicator_id,
            fetched_at=RawFetchResult.now_iso(),
            source_url=url,
            records=records,
        )
