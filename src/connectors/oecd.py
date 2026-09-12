"""OECD "Causes of mortality" (DF_COM) connector — a collector-tier route
for cause-of-death indicators (homicide first).

WHAT THIS SOURCE IS (investigated live, 2026-09-11)
The OECD Data Explorer's "Causes of mortality" dataflow (DSD_HEALTH_STAT@
DF_COM, agency OECD.ELS.HD) redistributes the WHO Mortality Database:
national civil-registration cause-of-death tables AS SUBMITTED by member
states (ICD-coded; "Assault" = CICDHOCD, the OECD's cross-ICD-version
grouping of the assault codes). The dataflow carries, per country/sex/year:
the mortality rate per 100,000 inhabitants (UNIT_MEASURE=DT_10P5HB) and
the death count (UNIT_MEASURE=DT), MEASURE=CSEM, CALC_METHODOLOGY=STANDARD.

Why this is a COLLECTOR, not a harmonized layer (the layer judgment):
the content is as-reported registrations — no modeling, no imputation,
no cross-country adjustment. The contrast with GHO's VIOLENCE_HOMICIDERATE
("Estimates of rates of homicides", WHO harmonized estimates) is exactly
the project's collector-vs-harmonized line, and the dataflow's own
measure is the honest series the Todd board wants canonically: e.g.
Russia's assault mortality 1980-2019 as reported, the 1994 crisis peak
(male 63.3 vs female 14.3 per 100k) printed as counted.

Honest scope limits (the coverage report exposes them, not hides them):
- 49 countries (OECD members + key partners incl. RUS, CHN, BRA, ZAF,
  IND, COL...): NOT near-global — most of Africa and Central Asia are
  absent; Ukraine and Belarus are absent from this dataflow.
- Russia's series ends in 2019 (the WHO MDB's own lag for it): the 2020+
  window is witness-only (UNODC), a divergence to display, not to patch.
- The classic WHO MDB bulk downloads and its portal's API are NOT
  publicly documented (investigated live: platform.who.int/mortality is
  a JS app with obfuscated endpoints; the old who.int/healthinfo paths
  are dead; dthub gateway DNS-dead) — the OECD SDMX API is the only
  clean programmatic route to this content found in 2026-09.

ACCESS: SDMX 3.0-style REST, no key, CSV responses
https://sdmx.oecd.org/public/rest/data/OECD.ELS.HD,DSD_HEALTH_STAT@DF_COM,1.1/
    {KEY}?dimensionAtObservation=AllDimensions
KEY = 13 dot-separated dimension positions (empty = all values):
    REF_AREA.FREQ.MEASURE.UNIT_MEASURE.AGE.SEX.SOCIO_ECON_STATUS.
    DEATH_CAUSE.CALC_METHODOLOGY.GESTATION_THRESHOLD.HEALTH_STATUS.DISEASE.
    CANCER_SITE
The connector pins everything except REF_AREA and SEX (all three sexes are
fetched: _T/M/F — the sex split is itself Todd-relevant signal) so one
request returns the whole as-reported series for the configured cause.
CALC_METHODOLOGY is pinned to CRUDE — the dataflow ALSO carries
age-standardized rates (STANDARD) for the same keys (live check, RUS
1994 male: crude 52.5 vs standardized 63.3 per 100k): standardization
adjusts for age structure, which is a derived comparability measure,
not the as-reported rate — the anti-derivation discipline excludes it
from the canonical tier. Attribute-only CSV rows (no TIME_PERIOD) are
SDMX metadata residue and are skipped, not parsed.

ENTITY RESOLUTION: OECD REF_AREA codes ARE ISO3 — they ride
RawRecord.iso3_raw and resolve through the registry's ISO3-first path.
The SDMX observation-status attributes (OBS_STATUS*) ride quality_code
when the dataflow prints one (empty for the assault series as of 2026-09:
carried, not invented).
"""
from __future__ import annotations

import csv
import io
import re

from src.connectors.base import Connector, RawFetchResult

OECD_SDMX_BASE = "https://sdmx.oecd.org/public/rest/data"
OECD_DF_COM_FLOW = "OECD.ELS.HD,DSD_HEALTH_STAT@DF_COM,1.1"
# 13 dimension positions of DSD_HEALTH_STAT, pinned to the mortality-by-cause
# slice: everything empty except FREQ=A, MEASURE=CSEM (mortality), AGE=_T
# (total), DEATH_CAUSE=<from source_ref>. UNIT_MEASURE is the field selector
# (rate per 100k = DT_10P5HB, deaths count = DT); SEX stays open (all three).
_UNIT_BY_FIELD = {"rate": "DT_10P5HB", "number": "DT"}
_OECD_REF_RE = re.compile(r"^DF_COM/(?P<cause>[A-Z0-9_]+)$")
_SDMX_SEX = {"M": "male", "F": "female", "_T": None}


def build_url(source_ref: str, field: str | None = None) -> str:
    """'DF_COM/CICDHOCD' -> the SDMX REST URL returning every country's
    mortality series for that death cause (all sexes, annual, total age).

    `field` selects the unit: "rate" (default; deaths per 100,000
    inhabitants, DT_10P5HB) or "number" (death counts, DT)."""
    match = _OECD_REF_RE.match(source_ref or "")
    if not match:
        raise ValueError(
            f"Invalid OECD source_ref {source_ref!r}: expected 'DF_COM/<death cause code>' "
            "(e.g. 'DF_COM/CICDHOCD' — Assault)."
        )
    unit = _UNIT_BY_FIELD.get(field or "rate")
    if unit is None:
        raise ValueError(f"field must be 'rate' or 'number', got {field!r}")
    # Positions 6 (SEX) and 7 (SOCIO_ECON_STATUS) stay EMPTY -> two empty
    # segments between AGE and DEATH_CAUSE: "_T" + three dots + cause.
    # CALC_METHODOLOGY (position 9) is PINNED to CRUDE: the dataflow also
    # carries age-standardized rates (STANDARD) for the same country-years
    # (verified live: RUS 1994 male crude 52.5 vs standardized 63.3) —
    # standardization is a derived comparability measure, not the
    # as-reported rate, so it is deliberately NOT fetched (anti-derivation).
    key = f".A.CSEM.{unit}._T...{match['cause']}.CRUDE...."
    return f"{OECD_SDMX_BASE}/{OECD_DF_COM_FLOW}/{key}?dimensionAtObservation=AllDimensions"


def parse_sdmx_csv(csv_text: str, *, field: str = "rate") -> list:
    """Pure function: SDMX-CSV text of the DF_COM dataflow -> RawRecords.

    No network access. One RawRecord per (country, year, sex); the ISO3
    code rides both entity_raw_name and iso3_raw (REF_AREA IS an ISO3);
    the SDMX observation status rides quality_code when the dataflow
    prints one. Raises ValueError on a malformed body."""
    from src.connectors.base import RawRecord

    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames or "REF_AREA" not in reader.fieldnames or "OBS_VALUE" not in reader.fieldnames:
        raise ValueError(
            "Not an SDMX-CSV data response (no REF_AREA/OBS_VALUE columns): "
            "layout change, or an error page was fetched?"
        )
    records = []
    for row in reader:
        ref_area = (row.get("REF_AREA") or "").strip()
        if not ref_area or ref_area == "REF_AREA":  # preamble/echo rows, never data
            continue
        sex_raw = (row.get("SEX") or "").strip()
        sex = _SDMX_SEX.get(sex_raw)
        if sex is None and sex_raw not in ("_T", ""):
            raise ValueError(f"Unexpected SDMX SEX code {sex_raw!r}: layout change?")
        year_raw = (row.get("TIME_PERIOD") or "").strip()
        if not year_raw:
            # Attribute-only rows (SDMX-CSV carries dataset/series-level
            # attributes on observation-less rows): metadata residue,
            # skipped — not data, not an error.
            continue
        if not re.fullmatch(r"\d{4}", year_raw):
            raise ValueError(f"Unexpected SDMX TIME_PERIOD {year_raw!r}: layout change?")
        value_raw = (row.get("OBS_VALUE") or "").strip()
        if value_raw == "":
            value = None  # an explicit gap in the dataflow, never a zero
        else:
            value = float(value_raw)
        status = (row.get("OBS_STATUS") or "").strip() or None
        records.append(
            RawRecord(
                entity_raw_name=ref_area,
                iso3_raw=ref_area,
                year=int(year_raw),
                value=value,
                sex=sex,
                quality_code=status,
            )
        )
    if not records:
        raise ValueError("No data rows in the SDMX-CSV response: refusing an empty fetch.")
    return records


class OecdConnector(Connector):
    provider = "oecd"

    def __init__(self, session=None, timeout: int = 120):
        self._session = session
        self._timeout = timeout

    def fetch_raw(self, source_ref: str, indicator_id: str, field: str | None = None) -> RawFetchResult:
        import requests  # local import: keep this module importable without `requests`

        url = build_url(source_ref, field=field)
        session = self._session or requests
        response = session.get(
            url,
            headers={
                "User-Agent": "toddlab-pipeline/0.1 (contact: see README)",
                "Accept": "application/vnd.sdmx.data+csv; version=2.0",
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        records = parse_sdmx_csv(response.text, field=field or "rate")
        return RawFetchResult(
            provider=self.provider,
            source_ref=source_ref,
            indicator_id=indicator_id,
            fetched_at=RawFetchResult.now_iso(),
            source_url=url,
            records=records,
        )
