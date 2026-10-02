"""OECD SDMX connector — the collector-tier routes (THREE dataflows).

WHAT THIS SOURCE IS
The OECD Data Explorer's SDMX API (no key, CSV responses). v10 wired the
first flow; v19 adds two more — one per new Todd metric. Each flow has
its own dimension grammar and its own pin guard: trust the URL, verify
the response (the v8.1 rule, applied per-flow).

(v26: the TWO MIGRATION dataflows — DSD_MIG_F@DF_MIG_POPF and
DSD_MIG@DF_MIG — were withdrawn with their indicator; their access
quirks and origin-override tables are history in the CHANGELOG. The
flows still print on the OECD's registry — the withdrawal record lives
in config/sources.yaml.)

FLOWS (ref grammar -> agency,dsd@df,version -> dimension layout):
- DF_COM/{cause}       (v10, 13 dims) "Causes of mortality": the WHO
  Mortality Database as submitted by member states (ICD-coded), OECD's
  cross-ICD cause groupings. Wires homicide (CICDHOCD, v8), suicide
  (CICDSCIDE, v13), cirrhosis (CICDCIRR, v18). UNIT via field=rate/number.
- DF_IDD/{measure}/{methodology}/{definition}   (v19, 9 dims) "Income
  distribution database" (OECD.WISE.INE): the national household-survey
  microdata AS SUBMITTED by member statistical offices (equivalized
  disposable income; MEASURE=INC_DISP_GINI prints the Gini, UNIT 0_TO_1).
  Wires gini_index's canonical — the collector judgment: survey
  tabulations redistributed, not modeled (the contrast with the WID
  witness's DINA research harmonization is the indicator's own story).
  THE STITCHING GRAMMAR: the flow prints the same (country, year) under
  several METHODOLOGY x DEFINITION vintages — METH2012 (the current IDD
  computation) vs METH2011 (the pre-revision history), D_CUR ("current
  definition") vs D_PREV ("previous definition - with overlap year") vs
  D_INC ("previous definition - without overlap year" — the same
  back-series minus the overlap print). The gini config wires FOUR doors
  in a priority chain (the NMARPCT quatuor pattern): the merge stitches
  the current print, back-fills through the definition vintages, and
  logs every collision as provenance — the OECD Data Explorer's own
  chained display, made explicit. AGE pinned _T (the flow also prints
  Y18T65/Y_GT65 age slices — never fetched, cleaner than dropped).
- DF_SAFETY/{measure}/{unit}   (v19, 8 dims) "Transport safety
  indicators" (OECD.ITF): the IRTAD road-safety statistics —
  police-reported crash registrations as submitted by the member
  countries. Wires road_accident_mortality's canonical:
  FATALITIES/10P5HB = road deaths per 100,000 population (the
  family-consistent face; the flow ALSO prints 10P4VEH_MOT_ROAD, per
  10,000 registered motor vehicles — the denominator of Todd's own 1974
  WHO table in Le Fou et le Prolétaire — and 10P9VEHKM, per billion
  vehicle-kilometres; those doors stay registered non-wired). RUS is
  absent from the whole ITF flow (verified live on the full slice:
  1994-2025, 55 areas, zero RUS rows) — the honest coverage limit the
  coverage report displays, while the GHO witness carries Russia's
  modeled face.

ACCESS: SDMX 3.0-style REST, no key, CSV responses. NOTE (learned live
2026-09-21, the v19 probes): the /public/rest/data endpoint REFUSES
"latest" as the version token ("Invalid version string provided") —
every flow reference carries its explicit version from the registry.

ENTITY RESOLUTION: REF_AREA codes ARE ISO3 — they ride
RawRecord.iso3_raw and resolve through the registry's ISO3-first path.
The SDMX observation-status attributes (OBS_STATUS*) ride quality_code
when the dataflow prints one (STFAT prints 'P' on its annual rows —
carried, not interpreted). DF_COM/DF_IDD/DF_SAFETY carry no SEX
dimension (every row both-sexes, sex=None, documented per indicator).
"""
from __future__ import annotations

import csv
import io
import logging
import re

from src.connectors.base import Connector, RawFetchResult


OECD_SDMX_BASE = "https://sdmx.oecd.org/public/rest/data"
OECD_DF_COM_FLOW = "OECD.ELS.HD,DSD_HEALTH_STAT@DF_COM,1.1"
OECD_DF_IDD_FLOW = "OECD.WISE.INE,DSD_WISE_IDD@DF_IDD,1.0"
OECD_DF_SAFETY_FLOW = "OECD.ITF,DSD_INDICATORS@DF_SAFETY,1.0"
# 13 dimension positions of DSD_HEALTH_STAT, pinned to the mortality-by-cause
# slice: everything empty except FREQ=A, MEASURE=CSEM (mortality), AGE=_T
# (total), DEATH_CAUSE=<from source_ref>. UNIT_MEASURE is the field selector
# (rate per 100k = DT_10P5HB, deaths count = DT); SEX stays open (all three).
_UNIT_BY_FIELD = {"rate": "DT_10P5HB", "number": "DT"}
_OECD_REF_RE = re.compile(r"^DF_COM/(?P<cause>[A-Z0-9_]+)$")
_OECD_IDD_REF_RE = re.compile(
    r"^DF_IDD/(?P<measure>[A-Z0-9_]+)/(?P<methodology>METH[0-9]+)/(?P<definition>D_[A-Z]+)$"
)
_OECD_SAFETY_REF_RE = re.compile(r"^DF_SAFETY/(?P<measure>[A-Z0-9_]+)/(?P<unit>[A-Z0-9_]+)$")
_SDMX_SEX = {"M": "male", "F": "female", "_T": None}

# The IDD's Gini is printed on the 0_TO_1 unit (the flow's own codelist);
# the grammar derives the unit from the measure so a future IDD measure
# must declare its unit here before it can be wired — a deliberate gate.
_IDD_UNIT_BY_MEASURE = {"INC_DISP_GINI": "0_TO_1"}


def build_url(source_ref: str, field: str | None = None) -> str:
    """Three ref grammars -> three SDMX REST URLs.

    - 'DF_COM/CICDHOCD' -> every country's as-reported mortality series for
      that death cause (all sexes, annual, total age). `field` selects the
      unit: "rate" (default; deaths per 100,000 inhabitants, DT_10P5HB) or
      "number" (death counts, DT).
    - 'DF_IDD/INC_DISP_GINI/METH2012/D_CUR' -> the Gini of equivalized
      disposable income for every country, annual, total age, at the pinned
      methodology x definition vintage.
    - 'DF_SAFETY/FATALITIES/10P5HB' -> the ITF road-fatality rate (per
      100,000 population) for every country, annual, road mode, all
      vehicle types.
    """
    match = _OECD_REF_RE.match(source_ref or "")
    if match:
        unit = _UNIT_BY_FIELD.get(field or "rate")
        if unit is None:
            raise ValueError(f"field must be 'rate' or 'number', got {field!r}")
        # Positions 6 (SEX) and 7 (SOCIO_ECON_STATUS) stay EMPTY -> two empty
        # segments between AGE and DEATH_CAUSE. CALC_METHODOLOGY is PINNED to
        # CRUDE: the dataflow also carries age-standardized rates (STANDARD)
        # for the same country-years — a derived comparability measure,
        # deliberately NOT fetched (anti-derivation).
        key = f".A.CSEM.{unit}._T...{match['cause']}.CRUDE...."
        return f"{OECD_SDMX_BASE}/{OECD_DF_COM_FLOW}/{key}?dimensionAtObservation=AllDimensions"

    idd = _OECD_IDD_REF_RE.match(source_ref or "")
    if idd:
        unit = _IDD_UNIT_BY_MEASURE.get(idd["measure"])
        if unit is None:
            raise ValueError(
                f"IDD measure {idd['measure']!r} has no unit declared in this connector's "
                "grammar (see _IDD_UNIT_BY_MEASURE) — wire it deliberately, never guess."
            )
        # 9 positions: REF_AREA open, FREQ=A, MEASURE, STATISTICAL_OPERATION=_Z,
        # UNIT, AGE=_T, METHODOLOGY, DEFINITION, POVERTY_LINE=_Z.
        key = (
            f".A.{idd['measure']}._Z.{unit}._T.{idd['methodology']}.{idd['definition']}._Z"
        )
        return f"{OECD_SDMX_BASE}/{OECD_DF_IDD_FLOW}/{key}?dimensionAtObservation=AllDimensions"

    safety = _OECD_SAFETY_REF_RE.match(source_ref or "")
    if safety:
        # 8 positions: REF_AREA open, FREQ=A (the flow also prints monthly and
        # quarterly rows — never fetched), MEASURE, UNIT, TRANSPORT_MODE=ROAD
        # (the road-mortality face), VEHICLE_TYPE/INFRASTRUCTURE_TYPE/
        # PRICE_BASE=_Z (the as-printed totals).
        key = f".A.{safety['measure']}.{safety['unit']}.ROAD._Z._Z._Z"
        return f"{OECD_SDMX_BASE}/{OECD_DF_SAFETY_FLOW}/{key}?dimensionAtObservation=AllDimensions"

    raise ValueError(
        f"Invalid OECD source_ref {source_ref!r}: expected 'DF_COM/<death cause code>' "
        "(e.g. 'DF_COM/CICDHOCD' — Assault), 'DF_IDD/<measure>/<methodology>/<definition>' "
        "(e.g. 'DF_IDD/INC_DISP_GINI/METH2012/D_CUR'), "
        "'DF_SAFETY/<measure>/<unit>' (e.g. 'DF_SAFETY/FATALITIES/10P5HB')."
    )


def _walk_sdmx_csv(csv_text: str, pins: dict[str, str]) -> list:
    """Shared SDMX-CSV walker (the three flows share one response shape).

    One RawRecord per (country, year[, sex]); ISO3 rides both
    entity_raw_name and iso3_raw; OBS_STATUS rides quality_code when the
    dataflow prints one. Raises ValueError on a malformed body — or on any
    DATA row that disagrees with the pins build_url() made for its flow
    (the v8.1 guard, generalized in v19): a response mixing in another
    slice is refused loudly, never silently ingested.
    """
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
        # THE PIN GUARD (v8.1, one per flow since v19): trust the URL, but
        # verify the response. Each flow carries other slices for the same
        # keys — a row from any of them is refused loudly, never ingested
        # as the requested data.
        for col, want in pins.items():
            got = (row.get(col) or "").strip()
            if got != want:
                raise ValueError(
                    f"OECD SDMX data row REF_AREA={ref_area} {year_raw} has "
                    f"{col}={got!r} but the fetch URL pins {want!r}: the API "
                    "returned a slice we did not ask for — refusing to "
                    "ingest it. Endpoint behavior change?"
                )
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


def parse_sdmx_csv(csv_text: str, *, field: str = "rate",
                   death_cause: str | None = None) -> list:
    """Pure function: SDMX-CSV text of the DF_COM dataflow -> RawRecords.

    No network access. Kept verbatim-signature from v10/v18 (the DF_COM
    tests pin it); the v19 generalization lives in _walk_sdmx_csv.
    """
    unit = _UNIT_BY_FIELD.get(field or "rate")
    if unit is None:
        raise ValueError(f"field must be 'rate' or 'number', got {field!r}")
    pins = {
        "FREQ": "A",
        "MEASURE": "CSEM",
        "UNIT_MEASURE": unit,
        "AGE": "_T",
        "CALC_METHODOLOGY": "CRUDE",
    }
    if death_cause:
        pins["DEATH_CAUSE"] = death_cause
    return _walk_sdmx_csv(csv_text, pins)


def parse_idd_csv(csv_text: str, *, measure: str, methodology: str, definition: str) -> list:
    """Pure function: SDMX-CSV text of the DF_IDD dataflow -> RawRecords.

    The pins mirror the key build_url() wrote for this vintage door —
    the response must BE that slice (age slices, other measures, other
    methodology/definition vintages: all refused loudly).
    """
    unit = _IDD_UNIT_BY_MEASURE.get(measure)
    if unit is None:
        raise ValueError(
            f"IDD measure {measure!r} has no unit declared (see _IDD_UNIT_BY_MEASURE): "
            "wire it deliberately, never guess."
        )
    pins = {
        "FREQ": "A",
        "MEASURE": measure,
        "STATISTICAL_OPERATION": "_Z",
        "UNIT_MEASURE": unit,
        "AGE": "_T",
        "METHODOLOGY": methodology,
        "DEFINITION": definition,
        "POVERTY_LINE": "_Z",
    }
    return _walk_sdmx_csv(csv_text, pins)


def parse_safety_csv(csv_text: str, *, measure: str, unit: str) -> list:
    """Pure function: SDMX-CSV text of the DF_SAFETY dataflow -> RawRecords.

    The pins mirror the key build_url() wrote — monthly/quarterly rows,
    non-road modes, other units or measures: all refused loudly.
    """
    pins = {
        "FREQ": "A",
        "MEASURE": measure,
        "UNIT_MEASURE": unit,
        "TRANSPORT_MODE": "ROAD",
        "VEHICLE_TYPE": "_Z",
        "INFRASTRUCTURE_TYPE": "_Z",
        "PRICE_BASE": "_Z",
    }
    return _walk_sdmx_csv(csv_text, pins)


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
        com = _OECD_REF_RE.match(source_ref or "")
        idd = _OECD_IDD_REF_RE.match(source_ref or "")
        if com:
            records = parse_sdmx_csv(
                response.text, field=field or "rate", death_cause=com["cause"]
            )
        elif idd:
            records = parse_idd_csv(
                response.text,
                measure=idd["measure"],
                methodology=idd["methodology"],
                definition=idd["definition"],
            )
        else:
            safety = _OECD_SAFETY_REF_RE.match(source_ref or "")
            records = parse_safety_csv(
                response.text, measure=safety["measure"], unit=safety["unit"]
            )
        return RawFetchResult(
            provider=self.provider,
            source_ref=source_ref,
            indicator_id=indicator_id,
            fetched_at=RawFetchResult.now_iso(),
            source_url=url,
            records=records,
        )
