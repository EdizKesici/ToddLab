"""ILOSTAT connector — the ILO's own SDMX wire (sdmx.ilo.org), v25.

THE DOOR (verified live 2026-09-27, the v25 probe — every fact below read
from the live responses, never typed): the DEAP class-decomposition rate
flows,
    DF_UNE_DEAP_SEX_AGE_CCT_RT  "Unemployment rate by sex, age and citizenship"
    DF_UNE_DEAP_SEX_AGE_CBR_RT  "Unemployment rate by sex, age and place of birth"
read directly as SDMX-JSON 2.0 — the SAME ILO-processed LFS family the
WB witness (SL.UEM.TOTL.NE.ZS) redistributes (root ilo_lfs), here on the
ILO's own wire with no WDI step in between.

THE FLOW RESTRUCTURE THE PROBE FOUND (the registry's own verdict, the
v17 record's "THE FUTURE Destin des immigrés by-nationality door"
settled): the flows' LAST_UPDATE annotation reads 24/09/2026 07:07:04 —
the restructure took the PER-COUNTRY citizenship/birth detail away
(enumerated on the FULL live CCT flow at SEX_T/AGE_AGGREGATE_YGE15: the
class dimension carries exactly {CCT_CIT_TOTAL, CCT_CIT_CITIZEN,
CCT_CIT_NONCIT, CCT_CIT_X} across all 137 printing REF_AREAs, 460
series / 461 observations 1995-2025 — a world cross-section, ~1
observation per series, the coupe pattern) and left the CLASS
decomposition only. The per-country face now lives exclusively in the
COUNT families (DF_EMP_MFRB/MFRC, DF_POP_MFRB/MFRC — employed and
working-age foreign populations by country of birth/citizenship);
unemployed-by-country counts do not exist, so a per-country RATE cannot
be assembled without a derivation — the anti-derivation line refuses it
(the record in config/sources.yaml).

THE FRAME PINS (verified live on the FRA inventories, both flows): the
6-position key REF_AREA.FREQ.MEASURE.SEX.AGE.CCT|CBR —
    REF_AREA  open (137 areas print on the CCT cross-section; the CBR
              twin carries its own; the codes are ISO3 with ONE quirk:
              KOS = Kosovo, mapped to the user-assigned XKX the kosovo
              entity declares — the v21 code, the WB's own for it)
    FREQ      A pinned (annual)
    MEASURE   UNE_DEAP_RT pinned (the flow's only measure — the rate)
    SEX       open (SEX_T/SEX_M/SEX_F — the by-sex ventilations ride the
              same layers under the merge key's sex component, the v24
              pattern)
    AGE       AGE_AGGREGATE_YGE15 pinned (15+ — the flow's broadest
              aggregate; the canonical Eurostat face pins Y15-74, the
              age-base seam the pair displays and the config documents)
    CCT|CBR   open (the class codelist as printed: CCT_CIT_TOTAL /
              CCT_CIT_CITIZEN / CCT_CIT_NONCIT / CCT_CIT_X on the
              citizenship flow, CBR_BIR_TOTAL / CBR_BIR_NATIVE /
              CBR_BIR_FOREIGN / CBR_BIR_X on the birth flow)

THE CLASS VOCABULARY -> the project's segment vocabulary (the mapping
declared once here, applied nowhere else): CITIZEN -> "nationals",
NONCIT -> "foreigners" (citizenship face); NATIVE -> "natives",
FOREIGN -> "foreign_born" (birth face). TOTAL drops (the total rate
rides the single-axis faces — une_rt_a canonical / the WB witness; one
door per face, the v22 rule) and X drops ("unreported class", the
questionnaire's own residual) — each logged with the door's own label.

THE ANNOTATION EVIDENCE the flow's own attributes carry (read live on
the world cross-section's 461 observations): SOURCE "LFS - Enquête sur
l'emploi" (the v17 probe's own fingerprint, on every observation), and
the NOTE_SOURCE repository mix — 309 "Repository: ILO-STATISTICS -
Micro data processing" (the ILMS harmonization), 63 "Repository:
Eurostat special tabulation" (the European prints republished by the
ILO), the rest national-institution notes — the harmonized tier's own
heterogeneous genealogy, carried in the config notes, never interpreted
by the pipeline. OBS_STATUS prints U ("Unreliable") and B ("Break in
series") on some observations — transported as-reported on quality_code
(19 of 105 FRA observations carry one).

WHAT THE PARSER REFUSES (the pin-guard discipline, loud failures only):
- a response whose series dimensions are not exactly [REF_AREA, FREQ,
  MEASURE, SEX, AGE, CCT|CBR] (a restructured flow is a loud failure,
  never a silent re-interpretation — the CCT/CBR restructure of
  2026-09-24 is exactly the class of change this guard exists to catch);
- any series whose FREQ is not A, MEASURE is not UNE_DEAP_RT, or AGE is
  not AGE_AGGREGATE_YGE15 (the frame the URL asked for);
- a class code in neither the map nor the drop table;
- a TIME_PERIOD value that is not a 4-digit year;
- zero records after parse (the soft-miss pattern: a flow id that stops
  answering must fail the fetch loudly, never pass silently).
"""
from __future__ import annotations

import json
import logging
import re

from src.connectors.base import Connector, RawFetchResult, RawRecord

ILO_SDMX_API_URL = "https://sdmx.ilo.org/rest/data"

# v25: the two class-decomposition rate flows (the wired doors). The ref
# grammar is the BARE flow id — the DF_MIG_POPF pattern: the frame pins
# (FREQ/MEASURE/AGE) and the open positions (REF_AREA/SEX/class) live in
# build_url's key, never in the ref.
_ILO_FLOWS: dict[str, dict] = {
    "DF_UNE_DEAP_SEX_AGE_CCT_RT": {
        "class_dim": "CCT",
        "segment_axis": "citizenship",
        "class_map": {
            "CCT_CIT_CITIZEN": "nationals",
            "CCT_CIT_NONCIT": "foreigners",
        },
    },
    "DF_UNE_DEAP_SEX_AGE_CBR_RT": {
        "class_dim": "CBR",
        "segment_axis": "birth",
        "class_map": {
            "CBR_BIR_NATIVE": "natives",
            "CBR_BIR_FOREIGN": "foreign_born",
        },
    },
}
_ILO_FLOW_REF_RE = re.compile(r"^(?P<flow>DF_UNE_DEAP_SEX_AGE_(?:CCT|CBR)_RT)$")

# v25: the classes that DROP, each with the door's own label and the
# reason (the per-class log discipline).
_ILO_CLASS_DROPS: dict[str, str] = {
    "CCT_CIT_TOTAL": "Total — the total rate rides the single-axis faces (une_rt_a / the WB witness)",
    "CBR_BIR_TOTAL": "Total — the total rate rides the single-axis faces (une_rt_a / the WB witness)",
    "CCT_CIT_X": "X — the unreported-citizenship residual (the questionnaire's own bucket)",
    "CBR_BIR_X": "X — the unreported-place-of-birth residual (the questionnaire's own bucket)",
}

# v25: the REF_AREA quirks — the ILO's own codes that are not the ISO3
# the registry declares (verified live on the 137-area cross-section:
# every code resolves by ISO3 except KOS, the ILO's code for Kosovo; the
# kosovo entity declares the user-assigned XKX, the v21 decision).
_ILO_AREA_TO_ISO3: dict[str, str] = {
    "KOS": "XKX",  # Kosovo (the ILO's own code; XKX is the user-assigned ISO)
}

# The frame pins (verified live 2026-09-27, both flows): the only
# measure, the broadest age aggregate, the annual frequency.
_ILO_FREQ_PIN = "A"
_ILO_MEASURE_PIN = "UNE_DEAP_RT"
_ILO_AGE_PIN = "AGE_AGGREGATE_YGE15"

_ILO_SEX_TO_PROJECT: dict[str, str | None] = {
    "SEX_T": None,  # the both-sexes rate — the merge key's None
    "SEX_M": "male",
    "SEX_F": "female",
}

logger = logging.getLogger(__name__)


def build_url(source_ref: str) -> str:
    m = _ILO_FLOW_REF_RE.match(source_ref or "")
    if not m:
        raise ValueError(
            f"Invalid ILOSTAT source_ref {source_ref!r}: expected a bare flow id, "
            "'DF_UNE_DEAP_SEX_AGE_CCT_RT' (unemployment rate by citizenship) or "
            "'DF_UNE_DEAP_SEX_AGE_CBR_RT' (by place of birth) — the frame pins live "
            "in the connector's key, never in the ref."
        )
    flow = m.group("flow")
    # 6 key positions over the flow's own dimension order
    # (REF_AREA, FREQ, MEASURE, SEX, AGE, CCT|CBR): REF_AREA and SEX OPEN
    # (the whole universe, both sexes' rows), FREQ/MEASURE/AGE pinned,
    # the class dimension OPEN (the codelist as printed). Verified live:
    # partial keys with empty (wildcard) positions answer; short keys
    # answer HTTP 422 "Not enough key values in query, expecting 6 got 2".
    key = f".{_ILO_FREQ_PIN}.{_ILO_MEASURE_PIN}..{_ILO_AGE_PIN}."
    return f"{ILO_SDMX_API_URL}/ILO,{flow}/{key}?format=jsondata"


def _parse_flow_ref(source_ref: str) -> dict:
    m = _ILO_FLOW_REF_RE.match(source_ref or "")
    if not m:
        raise ValueError(
            f"Invalid ILOSTAT source_ref {source_ref!r} — see build_url's error for the grammar."
        )
    flow = m.group("flow")
    return {"flow": flow, **_ILO_FLOWS[flow]}


def parse_ilostat(json_text: str, expected_ref: str) -> list[RawRecord]:
    """Pure function: one ILOSTAT SDMX-JSON 2.0 response -> RawRecords.

    Every record carries the population-segment fields
    (population_class in the project vocabulary, segment_axis naming the
    legality) and the sex ventilation when the series prints one; the
    class drops (TOTAL / X) are logged per class with the door's own
    labels; OBS_STATUS rides quality_code as-reported.
    """
    flow_meta = _parse_flow_ref(expected_ref)
    class_dim = flow_meta["class_dim"]

    try:
        envelope = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Not ILOSTAT SDMX-JSON: {exc}") from None
    if not isinstance(envelope, dict) or "data" not in envelope:
        raise ValueError("ILOSTAT response is not an SDMX-JSON data message: unexpected API shape")
    data = envelope["data"]
    structures = data.get("structures") or []
    if not structures:
        raise ValueError("ILOSTAT response without a structures block: unexpected API shape")
    structure = structures[0]
    try:
        series_dims = structure["dimensions"]["series"]
        obs_dims = structure["dimensions"]["observation"]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"ILOSTAT response with an incomplete dimensions block: {exc}") from None

    dim_ids = [d.get("id") for d in series_dims]
    expected_dims = ["REF_AREA", "FREQ", "MEASURE", "SEX", "AGE", class_dim]
    if dim_ids != expected_dims:
        raise ValueError(
            f"ILOSTAT series dimensions {dim_ids!r} are not the {flow_meta['flow']} "
            f"layout {expected_dims} — the flow was restructured; refusing to guess "
            "the slice (the v25 wiring froze this layout live, 2026-09-27)."
        )
    if len(obs_dims) != 1 or obs_dims[0].get("id") != "TIME_PERIOD":
        raise ValueError(
            f"ILOSTAT observation dimensions {[d.get('id') for d in obs_dims]!r} — expected "
            "exactly [TIME_PERIOD]: unexpected API shape."
        )

    # The per-dimension value tables (index -> {id, name}).
    dim_values: dict[str, list[dict]] = {}
    for d in series_dims:
        dim_values[d["id"]] = d.get("values") or []
    time_values = obs_dims[0].get("values") or []
    for tv in time_values:
        year = tv.get("id") if isinstance(tv, dict) else tv
        if not (isinstance(year, str) and len(year) == 4 and year.isdigit()):
            raise ValueError(f"ILOSTAT TIME_PERIOD value {year!r} is not a 4-digit year.")
    inv_time = {i: int(v["id"]) for i, v in enumerate(time_values)}

    # The observation-level attribute layout — OBS_STATUS rides quality_code.
    obs_attrs = (structure.get("attributes") or {}).get("observation") or []
    obs_attr_ids = [a.get("id") for a in obs_attrs]
    status_pos = obs_attr_ids.index("OBS_STATUS") + 1 if "OBS_STATUS" in obs_attr_ids else None
    status_values = (
        [v.get("id") for v in obs_attrs[status_pos - 1].get("values", [])] if status_pos else []
    )

    data_sets = data.get("dataSets") or []
    if not data_sets:
        raise ValueError("ILOSTAT response without a dataSets block: unexpected API shape")
    series_map = data_sets[0].get("series") or {}
    if not series_map:
        raise ValueError(
            "ILOSTAT payload yielded zero series — the soft-miss pattern (a flow id "
            "that stops answering must fail the fetch loudly)."
        )

    records: list[RawRecord] = []
    dropped_classes: dict[str, int] = {}
    n_frame_refusals = 0
    for series_key, series_data in series_map.items():
        try:
            indices = [int(part) for part in series_key.split(":")]
        except (TypeError, ValueError):
            raise ValueError(f"ILOSTAT series key {series_key!r} is not an index tuple.") from None
        if len(indices) != len(expected_dims):
            raise ValueError(
                f"ILOSTAT series key {series_key!r} has {len(indices)} positions — "
                f"the layout declares {len(expected_dims)}."
            )
        labels: dict[str, dict] = {}
        for pos, dim_id in enumerate(expected_dims):
            values = dim_values[dim_id]
            if indices[pos] >= len(values):
                raise ValueError(
                    f"ILOSTAT series key {series_key!r} indexes {dim_id} beyond its values."
                )
            labels[dim_id] = values[indices[pos]]
        # The frame guards: the URL's pins must BE what the series prints.
        if labels["FREQ"].get("id") != _ILO_FREQ_PIN or labels["MEASURE"].get("id") != _ILO_MEASURE_PIN \
                or labels["AGE"].get("id") != _ILO_AGE_PIN:
            n_frame_refusals += 1
            continue
        area_code = labels["REF_AREA"].get("id")
        area_name = labels["REF_AREA"].get("name") or area_code
        if not area_code:
            raise ValueError(f"ILOSTAT REF_AREA value without an id: {labels['REF_AREA']!r}")
        sex = _ILO_SEX_TO_PROJECT.get(labels["SEX"].get("id"))
        if sex is None and labels["SEX"].get("id") not in ("SEX_T",):
            raise ValueError(
                f"ILOSTAT SEX code {labels['SEX'].get('id')!r} is not in the flow's own "
                "vocabulary — layout change?"
            )
        class_code = labels[class_dim].get("id")
        class_label = labels[class_dim].get("name") or class_code
        if class_code in _ILO_CLASS_DROPS:
            dropped_classes[class_code] = dropped_classes.get(class_code, 0) + 1
            continue
        population_class = flow_meta["class_map"].get(class_code)
        if population_class is None:
            raise ValueError(
                f"ILOSTAT {class_dim} code {class_code!r} is in neither the class map nor "
                "the drop table — extend _ILO_FLOWS' class_map or _ILO_CLASS_DROPS "
                "deliberately (never guess a class)."
            )

        iso3 = _ILO_AREA_TO_ISO3.get(area_code, area_code)
        for obs_key, obs in (series_data.get("observations") or {}).items():
            if not isinstance(obs, list) or not obs:
                raise ValueError(f"ILOSTAT observation {obs_key!r} is not a [value, attrs] list.")
            value = obs[0]
            if value is not None and not isinstance(value, (int, float)):
                raise ValueError(f"ILOSTAT observation value is neither number nor null: {value!r}")
            try:
                year = inv_time[int(obs_key)]
            except (KeyError, ValueError, TypeError):
                raise ValueError(f"ILOSTAT observation key {obs_key!r} does not index TIME_PERIOD.") from None
            quality = None
            if status_pos and len(obs) > status_pos and obs[status_pos] is not None:
                idx = obs[status_pos]
                if 0 <= idx < len(status_values):
                    quality = status_values[idx]
            records.append(
                RawRecord(
                    entity_raw_name=area_name,
                    iso3_raw=iso3,
                    year=year,
                    value=float(value) if value is not None else None,
                    population_class=population_class,
                    segment_axis=flow_meta["segment_axis"],
                    sex=sex,
                    quality_code=quality,
                )
            )

    if n_frame_refusals:
        logger.warning(
            "ILOSTAT: skipped %d series outside the wired frame (FREQ!=%s or MEASURE!=%s "
            "or AGE!=%s) — the URL pins should have filtered these; a layout change?",
            n_frame_refusals, _ILO_FREQ_PIN, _ILO_MEASURE_PIN, _ILO_AGE_PIN,
        )
    for code, n_cells in sorted(dropped_classes.items()):
        logger.info(
            "ILOSTAT: dropped %d %s series cell(s) from %s (%s).",
            n_cells, code, flow_meta["flow"], _ILO_CLASS_DROPS[code],
        )
    if not records:
        raise ValueError(
            "ILOSTAT payload yielded zero records after the frame pins and class "
            "classification — unexpected API shape (or every series rides a dropped class)."
        )
    return records


class IlostattConnector(Connector):
    provider = "ilostat"

    def __init__(self, session=None, timeout: int = 300):
        self._session = session
        # The flow-wide downloads are the connector's own heaviest class
        # (the CCT cross-section measures ~600 KB at SEX_T/YGE15; the
        # full both-sexes frame a few MB) — the 300 s default rides the
        # OECD migration doors' own timeout discipline.
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": "toddlab-pipeline/0.1 (contact: see README)"}

    def fetch_raw(self, source_ref: str, indicator_id: str, field: str | None = None) -> RawFetchResult:
        import requests  # local import: keep this module importable in pure-parsing tests

        if field is not None:
            raise ValueError(
                f"ILOSTAT source_ref {source_ref!r} carries a 'field' ({field!r}) — this "
                "provider selects series through the flow's frame pins, never through field."
            )
        session = self._session or requests
        url = build_url(source_ref)
        response = session.get(url, headers=self._headers(), timeout=self._timeout)
        response.raise_for_status()
        records = parse_ilostat(response.text, expected_ref=source_ref)
        return RawFetchResult(
            provider=self.provider,
            source_ref=source_ref,
            indicator_id=indicator_id,
            fetched_at=RawFetchResult.now_iso(),
            source_url=url,
            records=records,
        )
