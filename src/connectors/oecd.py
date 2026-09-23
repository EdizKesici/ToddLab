"""OECD SDMX connector — the collector-tier routes (FOUR dataflows).

WHAT THIS SOURCE IS
The OECD Data Explorer's SDMX API (no key, CSV responses). v10 wired the
first flow; v19 adds two more — one per new Todd metric; v22 adds the
fourth, the migration questionnaire's bilateral face. Each flow has its
own dimension grammar and its own pin guard: trust the URL, verify the
response (the v8.1 rule, applied per-flow).

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
- DF_MIG_POPF   (v22, 8 dims) "International migration database - stocks
  of foreign-born population" (OECD.ELS.IMD, DSD_MIG_F@DF_MIG_POPF):
  the OECD migration questionnaire's own BILATERAL matrix — REF_AREA
  (38 destinations, ISO3) x BIRTH_COUNTRY (242 origin codes), the
  foreign-born stock by country of birth. THE ACCESS QUIRK (verified
  live 2026-09-22, the v22 probes): the flow refuses positional keys
  (every dotted key 404s — the observation dimension carries TIME), so
  the door serves ONLY through the empty-key /all download — the FULL
  dataset in one 18.2 MB CSV, already the pinned frame (MEASURE=B14
  only, FREQ=A only, BIRTH_PLACE=_Z, EDUCATION_LEV=_Z, UNIT=PS only:
  the flow's whole vocabulary, hard-verified per row). SEX: the download
  carries _T AND F — the wiring pins _T (the both-sexes face; the F
  rows drop logged, the by-sex door recorded unwired). THE SEAM,
  verified to the unit: OECD FR<-MAR _T 2015 = 954,742 = the Eurostat
  c_birth print EXACTLY; the OECD face extends the FR Maghreb series
  past the Eurostat 2018 cutoff (2019-2021) and carries the world's
  non-European destinations (US<-MEX 12,383,868 in 2024) the Eurostat
  universe structurally cannot print — the compilation seam displayed,
  never reconciled.

ACCESS: SDMX 3.0-style REST, no key, CSV responses. NOTE (learned live
2026-09-21, the v19 probes): the /public/rest/data endpoint REFUSES
"latest" as the version token ("Invalid version string provided") —
every flow reference carries its explicit version from the registry.

ENTITY RESOLUTION: REF_AREA codes ARE ISO3 — they ride
RawRecord.iso3_raw and resolve through the registry's ISO3-first path.
The SDMX observation-status attributes (OBS_STATUS*) ride quality_code
when the dataflow prints one (STFAT prints 'P' on its annual rows —
carried, not interpreted). DF_COM/DF_IDD/DF_SAFETY carry no SEX
dimension (every row both-sexes, sex=None, documented per indicator);
DF_MIG_POPF DOES carry one — the pinned _T face maps to sex=None, the
F rows drop logged before it. On the bilateral record the ORIGIN axis
rides origin_raw_name/origin_iso3_raw (BIRTH_COUNTRY; the OECD
origin-code overrides — XKV, the _F vanished-entity codes — documented
at _MIGF_ORIGIN_TO_ISO3 below).
"""
from __future__ import annotations

import csv
import io
import logging
import re

from src.connectors.base import Connector, RawFetchResult

logger_migf = logging.getLogger(__name__)

OECD_SDMX_BASE = "https://sdmx.oecd.org/public/rest/data"
OECD_DF_COM_FLOW = "OECD.ELS.HD,DSD_HEALTH_STAT@DF_COM,1.1"
OECD_DF_IDD_FLOW = "OECD.WISE.INE,DSD_WISE_IDD@DF_IDD,1.0"
OECD_DF_SAFETY_FLOW = "OECD.ITF,DSD_INDICATORS@DF_SAFETY,1.0"
# v22: the migration questionnaire's foreign-born matrix (the bilateral
# face — the OECD side of the immigration_stock by-origin pair).
OECD_DF_MIGF_FLOW = "OECD.ELS.IMD,DSD_MIG_F@DF_MIG_POPF,1.0"
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
# v22: the bare-flow grammar — the door serves only through the empty-key
# /all download (positional keys 404, verified live), so the ref carries
# no key parts at all; the frame pins live in the parser (parse_migf_csv).
_OECD_MIGF_REF_RE = re.compile(r"^DF_MIG_POPF$")
_SDMX_SEX = {"M": "male", "F": "female", "_T": None}

# v22: the BIRTH_COUNTRY codelist's own origin quirks — the codes that are
# neither plain ISO3 nor the drop vocabulary (verified live against the
# DSD codelist and the full /all download, 2026-09-22):
# - XKV: the OECD's own code for Kosovo (Eurostat prints XK, the WB XKX —
#   the kosovo entity declares iso3: XKX, v21);
# - the _F suffix: the OECD's vanished-entity prints, "Former ..." —
#   ANT_F Former Netherlands Antilles, CSK_F Former Czechoslovakia,
#   SCG_F Former Serbia and Montenegro, SUN_F Former USSR, YUG_F Former
#   Yugoslavia. Each maps to its WITHDRAWN ISO 3166-1 alpha-3 (ANT/CSK/
#   SCG/SUN/YUG), which the corresponding vanished entity now declares
#   (the v21 kosovo/XKX precedent — the by-origin face of the v21
#   vanished-entity admission: people born in the former entity, counted
#   in the stock wherever they live now, exactly as the questionnaire
#   prints them).
_MIGF_ORIGIN_TO_ISO3: dict[str, str] = {
    "XKV": "XKX",
    "ANT_F": "ANT",
    "CSK_F": "CSK",
    "SCG_F": "SCG",
    "SUN_F": "SUN",
    "YUG_F": "YUG",
}

# v22: the BIRTH_COUNTRY residual vocabulary — codes that are neither a
# resolvable origin nor an override: the World aggregates (W, W_X "World
# unspecified"), the supra-national aggregates (EEA, EU15), the region
# print (A4 "Caribbean") and the stateless residual (STLS "Stateless",
# nationality/citizenship without a state — a population, not a place of
# birth the entity table could ever carry). Dropped LOGGED per class.
_MIGF_ORIGIN_DROPS: dict[str, str] = {
    "W": "the World-total row (the door's own FOR-equivalent)",
    "W_X": "World unspecified",
    "EEA": "the European Economic Area aggregate",
    "EU15": "the EU15 aggregate",
    "A4": "the Caribbean region print",
    "STLS": "the stateless residual (a nationality, not a birth place)",
}

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
    - 'DF_MIG_POPF' -> the migration questionnaire's FULL foreign-born
      matrix (the empty-key /all download: 38 ISO3 destinations x the
      BIRTH_COUNTRY origin codelist, both sexes' rows — the parser pins
      the _T face and drops the F rows logged).
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

    if _OECD_MIGF_REF_RE.match(source_ref or ""):
        # v22: the EMPTY-KEY download — positional keys 404 on this flow
        # (verified live 2026-09-22: every dotted key returns 404, the
        # observation dimension carries TIME under the repo's
        # dimensionAtObservation=AllDimensions convention), so the door
        # serves its data through /all: the FULL dataset (197,570 rows,
        # 18.2 MB) — already the pinned frame (MEASURE=B14/FREQ=A/
        # BIRTH_PLACE=_Z/EDUCATION_LEV=_Z/UNIT_MEASURE=PS are the flow's
        # whole vocabulary), carrying both sexes' rows for the parser to
        # split (the _T face kept, F dropped logged).
        return f"{OECD_SDMX_BASE}/{OECD_DF_MIGF_FLOW}/all?dimensionAtObservation=AllDimensions"

    raise ValueError(
        f"Invalid OECD source_ref {source_ref!r}: expected 'DF_COM/<death cause code>' "
        "(e.g. 'DF_COM/CICDHOCD' — Assault), 'DF_IDD/<measure>/<methodology>/<definition>' "
        "(e.g. 'DF_IDD/INC_DISP_GINI/METH2012/D_CUR'), "
        "'DF_SAFETY/<measure>/<unit>' (e.g. 'DF_SAFETY/FATALITIES/10P5HB'), or "
        "'DF_MIG_POPF' (the foreign-born bilateral matrix's empty-key download — v22)."
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


def parse_migf_csv(csv_text: str) -> list:
    """Pure function: the DF_MIG_POPF empty-key /all download -> RawRecords
    (v22, the bilateral WITNESS face of immigration_stock).

    One record per (REF_AREA destination, BIRTH_COUNTRY origin, year) on
    the SEX=_T frame, the origin axis riding origin_raw_name/
    origin_iso3_raw. The discipline, per class:

    - HARD pins (a row that disagrees is a LOUD failure — the flow's whole
      vocabulary, verified live 2026-09-22 on the full 197,570-row
      download): FREQ=A, MEASURE=B14, BIRTH_PLACE=_Z, EDUCATION_LEV=_Z,
      UNIT_MEASURE=PS. An API change that introduces a second measure or
      unit is never a silent re-interpretation.
    - SEX: the /all download structurally carries BOTH faces (_T 100,973
      rows + F 96,597); the wiring pins _T — the F rows drop LOGGED (the
      by-sex face recorded unwired, never fetched-and-discarded silently).
      A code outside {_T, F} is a loud failure (layout change).
    - The origin drops, LOGGED per class: the residual vocabulary
      (_MIGF_ORIGIN_DROPS: W/W_X/EEA/EU15/A4/STLS) and the DIAGONAL
      (BIRTH_COUNTRY == REF_AREA — the native-born face, the same class
      the Eurostat ROW slice drops).
    - The origin overrides (_MIGF_ORIGIN_TO_ISO3: XKV Kosovo, the _F
      vanished-entity prints) map the questionnaire's own codes onto the
      ISO3 the entity table declares; every other origin code IS ISO3
      (the codelist's own convention) and rides origin_iso3_raw as-is.
    """
    from src.connectors.base import RawRecord

    reader = csv.DictReader(io.StringIO(csv_text))
    required = {"REF_AREA", "BIRTH_COUNTRY", "SEX", "OBS_VALUE"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError(
            "Not an SDMX-CSV DF_MIG_POPF response (missing "
            f"{sorted(required - set(reader.fieldnames or []))} columns): "
            "layout change, or an error page was fetched?"
        )
    # The frame pins — hard-verified per row (see docstring).
    frame_pins = {
        "FREQ": "A",
        "MEASURE": "B14",
        "BIRTH_PLACE": "_Z",
        "EDUCATION_LEV": "_Z",
        "UNIT_MEASURE": "PS",
    }
    records: list[RawRecord] = []
    dropped_bysex = 0
    dropped_origin_residuals: dict[str, int] = {}
    dropped_diagonal = 0
    for row in reader:
        ref_area = (row.get("REF_AREA") or "").strip()
        if not ref_area or ref_area == "REF_AREA":  # preamble/echo rows, never data
            continue
        birth_country = (row.get("BIRTH_COUNTRY") or "").strip()
        sex_raw = (row.get("SEX") or "").strip()
        year_raw = (row.get("TIME_PERIOD") or "").strip()
        if not year_raw:
            # Attribute-only rows (SDMX-CSV dataset/series-level attributes
            # on observation-less rows): metadata residue, skipped.
            continue
        if not re.fullmatch(r"\d{4}", year_raw):
            raise ValueError(f"Unexpected SDMX TIME_PERIOD {year_raw!r}: layout change?")
        # THE FRAME PIN GUARD (loud — trust the URL, verify the response):
        for col, want in frame_pins.items():
            got = (row.get(col) or "").strip()
            if got != want:
                raise ValueError(
                    f"OECD DF_MIG_POPF data row REF_AREA={ref_area} {year_raw} has "
                    f"{col}={got!r} but the flow's pinned frame is {want!r}: the API "
                    "returned a slice we did not ask for — refusing to ingest it. "
                    "Endpoint behavior change?"
                )
        # THE SEX SPLIT: _T kept (the both-sexes face, sex=None), F dropped
        # LOGGED (the by-sex door, recorded unwired); anything else is a
        # layout change, loudly refused.
        if sex_raw == "F":
            dropped_bysex += 1
            continue
        if sex_raw != "_T":
            raise ValueError(
                f"Unexpected SDMX SEX code {sex_raw!r} on DF_MIG_POPF (expected _T or F): "
                "layout change?"
            )
        # THE ORIGIN AXIS: the diagonal and the residual vocabulary drop
        # logged; the overrides map the questionnaire's own codes onto the
        # entity table's ISO3; everything else rides as the ISO3 it is.
        if birth_country == ref_area:
            dropped_diagonal += 1
            continue
        if birth_country in _MIGF_ORIGIN_DROPS:
            dropped_origin_residuals[birth_country] = dropped_origin_residuals.get(birth_country, 0) + 1
            continue
        origin_iso3 = _MIGF_ORIGIN_TO_ISO3.get(birth_country, birth_country)
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
                origin_raw_name=birth_country,
                origin_iso3_raw=origin_iso3,
                sex=None,
                quality_code=status,
            )
        )
    if not records:
        raise ValueError("No data rows in the DF_MIG_POPF response: refusing an empty fetch.")
    if dropped_bysex:
        logger_migf.info(
            "OECD DF_MIG_POPF: dropped %d by-sex row(s) (SEX=F — the flow's female face, "
            "recorded unwired; the wiring pins the _T both-sexes frame, the same class "
            "as the Eurostat M/F sex doors).",
            dropped_bysex,
        )
    for code, count in sorted(dropped_origin_residuals.items()):
        logger_migf.info(
            "OECD DF_MIG_POPF: dropped %d origin row(s) carrying code %r (%s).",
            count,
            code,
            _MIGF_ORIGIN_DROPS[code],
        )
    if dropped_diagonal:
        logger_migf.info(
            "OECD DF_MIG_POPF: dropped %d diagonal row(s) (BIRTH_COUNTRY == REF_AREA — "
            "the native-born face; the by-origin layer carries the FOREIGN-born "
            "decomposition only, the same class the Eurostat ROW slice drops).",
            dropped_diagonal,
        )
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
        elif _OECD_MIGF_REF_RE.match(source_ref or ""):
            # v22: the DF_MIG_POPF empty-key download (the timeout rides the
            # connector's own 120 s default — the full 18.2 MB body arrives
            # as one stream; the parser splits the sexes and drops the
            # residual vocabulary logged).
            records = parse_migf_csv(response.text)
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
