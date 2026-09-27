"""WHO Global Health Observatory (GHO) connector — the harmonized tier.

WHAT THIS SOURCE IS
The GHO is the WHO's data portal: OData-style JSON APIs, no auth. Its
content is LAYER-3 harmonized estimates (the indicator names say so
openly — "Estimates of..."), which is why the project classifies it as
`harmonized` in PROVIDER_LAYER and uses it as a WITNESS, never as a
canonical source (ADR-0007/0008: the witness models the whole world
including the countries the collectors cannot serve).

The connector was built for LE-60's witness (WHOSIS_000015, "Life
expectancy at age 60 (years)", WPP-derived) — the piece of phase 5 pulled
forward because the fifth indicator needed a witness and OWID has no
age-60 chart (verified against the live sitemap: by-age charts jump
45 -> 65). Since v11 it also carries MDG_0000000001 ("Infant mortality
rate", the IGME redistribution — the third door of the measurement-
problem triangle): that wiring needed NO new dims handling, the
SEX-only shape held. Since v13 it carries SDGSUICIDE ("Crude suicide
rates (per 100 000 population)", the GHE redistribution — the suicide
witness): that indicator disaggregates by AGE on Dim2, which needed a
Dim2 rule (below).

API SHAPE (verified live 2026-09-13, WHOSIS_000015: 12,936 rows):
    GET https://ghoapi.azureedge.net/api/{code}
    {"value": [{"SpatialDimType": "COUNTRY", "SpatialDim": "FRA",
                "TimeDimType": "YEAR", "TimeDim": 2020,
                "Dim1Type": "SEX", "Dim1": "SEX_MLE",
                "Value": "15.9 [15.3-16.8]", "NumericValue": 15.92,
                "Low": 15.29, "High": 16.77, ...}, ...]}

- SpatialDim is an ISO3 code for COUNTRY rows; the provider's own
  SpatialDimType field classifies the rest (REGION, GLOBAL,
  WORLDBANKINCOMEGROUP — 726 rows in WHOSIS_000015). The parser keeps
  COUNTRY rows only: the provider's classification is authoritative
  metadata, not our judgement call. The dropped aggregate rows are not
  stored anywhere (the snapshot holds the parsed COUNTRY records, same
  as every connector here): the log line is the record of the drop, and
  the classification is re-fetchable from source_url.
- Dim1Type "SEX" carries the breakdown: SEX_MLE -> "male", SEX_FMLE ->
  "female", SEX_BTSX -> None (both sexes — the project's sex semantics:
  the merge key (entity, year, sex) keeps the three apart, and a
  both-sexes witness series never collides with the sex-split canonical).
- Dim2, when the indicator disaggregates (SDGSUICIDE does, by age):
  the connector keeps the ALL-AGES series only (Dim2 =
  AGEGROUP_YEARSALL) and drops the age slices at parse — verified live
  (2026-09-19): 19,041 COUNTRY records = 12,210 all-ages keys (185
  countries x 2000-2021 x 3 sexes, each carrying Low/High intervals)
  + 6,105 age-slice records concentrated on the latest year (2021:
  11 overlapping bands — 10-19, 15-19, 15-29, 20-29, 30-39, 30-49,
  40-49, 50-59, 50-69, 60-69, 70PLUS — printed beside the YEARSALL row
  for every key). An age slice would be a different indicator ("suicide
  rate among 50-69"), one no Todd metric calls for; the dropped slices
  are stored nowhere — the log line is the record of the drop,
  re-fetchable from source_url. A Dim2Type OTHER than AGEGROUP is not
  silently interpreted: it raises (layout change → a human decides).
  Dim2-less indicators (WHOSIS_000015, PRISON_A2_*) pass untouched.
- v20 — the per-code AGE pin: NCD_BMI_30C (the obesity canonical)
  disaggregates by AGE too, but as a SINGLE population face printed on
  every row (Dim2 = AGEGROUP_YEARS18-PLUS — the 18+ adult frame, read
  live 2026-09-22: 28,350 rows, 199 countries x 1980-2024 x 3 sexes,
  every row carrying the same 18+ tag — no slices beside it to drop).
  The YEARSALL default would refuse that whole payload, so the pin
  table below declares the door's own face per code: a pinned code
  ACCEPTS exactly its pinned Dim2 and raises on anything else (a
  row from another age frame = a door change, a human decides); an
  unpinned code keeps the YEARSALL rule verbatim (SDGSUICIDE's
  drop-the-slices grammar — bit-compat with every pre-v20 parse).
- v23 — the MDG_0000000001 DOOR CHANGE, pinned: on 2026-09-25 the live
  payload recoded its age frame — every one of the 39,279 COUNTRY rows
  now carries Dim2 = AGEGROUP_MONTHS0-11 (the 0-11-months frame, the
  door's own semantically-exact face for an under-1 mortality rate;
  the Indicator metadata still declares Dim2Type null, out of sync with
  the data). At v22 the rows rode Dim2-less and passed untouched; the
  YEARSALL default would now refuse the WHOLE payload as age slices.
  Verified live before any fix: the 39,210 dist-point keys are all
  present with ZERO value divergence, and the 69 extra rows are all
  Kosovo pre-2008 (dropped by the entity validity guard in normalize —
  the same rows the v22 build dropped). The pin is therefore the v20
  machinery applied to a door change: MDG_0000000001 ACCEPTS exactly
  AGEGROUP_MONTHS0-11 now, and raises on anything else (a future
  re-coding is a door change again, a human decides — never a silent
  re-interpretation).
- NumericValue is the estimate; "Value" is its formatted string
  ("15.9 [15.3-16.8]") and Low/High the uncertainty interval. The
  RawRecord schema carries only the estimate: the formatted string and
  the intervals are dropped at parse, stored nowhere, re-fetchable
  from source_url. The dist schema does not carry witness uncertainty
  intervals either (a schema decision for later; this bullet, not a
  snapshot, is the record of what is not carried).
- Zero null NumericValues in the live payload, but a null is handled
  the honest way: an explicit gap point, never a skip.
"""
from __future__ import annotations

import json
import logging

from src.connectors.base import Connector, RawFetchResult, RawRecord

GHO_API_URL = "https://ghoapi.azureedge.net/api/{code}"

logger = logging.getLogger(__name__)

# Dim1 values of the SEX dimension -> the project's sex vocabulary.
_SEX_DIM = {"SEX_MLE": "male", "SEX_FMLE": "female", "SEX_BTSX": None}

# v20: the per-code AGE pin — a door whose every row carries ONE age
# frame (no slices beside it) declares that frame here, and the parser
# accepts exactly it (anything else raises). Codes not listed keep the
# YEARSALL drop-the-slices grammar (SDGSUICIDE) or the Dim2-less pass
# (WHOSIS_000015, PRISON_A2_*). v23: MDG_0000000001 joins the pin table
# — the provider recoded its frame (see the docstring above); the pin
# keeps the door's own face explicit instead of letting the YEARSALL
# default silently refuse the whole payload.
_CODE_AGE_PIN: dict[str, str] = {
    "NCD_BMI_30C": "AGEGROUP_YEARS18-PLUS",  # read live 2026-09-22 on the full 28,350-row slice
    # v23: read live 2026-09-25 on the full 44,424-row payload (39,279
    # COUNTRY rows, every one carrying the 0-11-months frame; the v22
    # dist reproduced bit-identically through the pin — see CHANGELOG).
    "MDG_0000000001": "AGEGROUP_MONTHS0-11",
}


def build_url(code: str) -> str:
    return GHO_API_URL.format(code=code)


def parse_gho(json_text: str, *, code: str | None = None) -> list[RawRecord]:
    """Pure function: GHO API JSON text -> RawRecords (COUNTRY rows only).

    `code` (the GHO indicator code being parsed, passed by fetch_raw)
    selects the per-code Dim2 grammar: a code pinned in _CODE_AGE_PIN
    accepts exactly its pinned age frame; any other code keeps the
    YEARSALL rule (drop the slices) or passes Dim2-less rows untouched.
    Unpinned callers (tests) keep the pre-v20 behavior bit-identical.

    Raises ValueError on any shape surprise — the loud-failure rule."""
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Not GHO JSON: {exc}") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("value"), list):
        raise ValueError("GHO JSON without a 'value' array: unexpected API shape")

    records: list[RawRecord] = []
    skipped_non_country = 0
    dropped_age_slices = 0
    for row in payload["value"]:
        if not isinstance(row, dict):
            raise ValueError(f"GHO row is not an object: {row!r}")
        dim_type = row.get("SpatialDimType")
        if dim_type != "COUNTRY":
            skipped_non_country += 1
            continue
        spatial = row.get("SpatialDim")
        if not spatial or not isinstance(spatial, str):
            raise ValueError(f"GHO COUNTRY row without a SpatialDim code: {row!r}")
        year = row.get("TimeDim")
        if row.get("TimeDimType") != "YEAR" or not isinstance(year, int):
            raise ValueError(
                f"GHO row with non-YEAR TimeDim {row.get('TimeDimType')!r}: "
                "this connector does not know how to place that in time."
            )
        dim1_type = row.get("Dim1Type")
        if dim1_type is None:
            sex = None
        elif dim1_type == "SEX":
            dim1 = row.get("Dim1")
            if dim1 not in _SEX_DIM:
                raise ValueError(f"Unknown SEX dim value {dim1!r}: GHO API change?")
            sex = _SEX_DIM[dim1]
        else:
            raise ValueError(
                f"GHO row with Dim1Type {dim1_type!r}: this connector only handles the "
                "SEX dimension (built for WHOSIS_000015; other dims are phase-5 work)."
            )
        # Dim2 (v13, SDGSUICIDE): age disaggregation printed beside the
        # all-ages series on the latest year. The ALL-AGES record is the
        # series this connector serves; the age slices are a different
        # indicator nobody asked for — dropped at parse, stored nowhere,
        # the log line below is the record of the drop. A Dim2Type other
        # than AGEGROUP is a layout surprise, never silently re-interpreted.
        # v20: a code pinned in _CODE_AGE_PIN carries its age frame on
        # EVERY row (no slices) — the pin is the door's own face, and any
        # deviation from it is a door change that must stop the parse.
        dim2_type = row.get("Dim2Type")
        dim2 = row.get("Dim2")
        pinned_age = _CODE_AGE_PIN.get(code) if code is not None else None
        if pinned_age is not None:
            if dim2 != pinned_age:
                raise ValueError(
                    f"GHO code {code!r} is age-pinned to {pinned_age!r} but a row "
                    f"carries Dim2={dim2!r} (Dim2Type={dim2_type!r}) — a door change, "
                    "never silently re-interpreted (the pin is the door's own face)."
                )
        elif dim2_type is not None or dim2 is not None:
            if dim2_type != "AGEGROUP":
                raise ValueError(
                    f"GHO row with Dim2Type {dim2_type!r}: this connector only knows the "
                    "AGEGROUP disaggregation (keep YEARSALL, drop the slices) — a new "
                    "dimension needs a deliberate parser decision."
                )
            if dim2 != "AGEGROUP_YEARSALL":
                dropped_age_slices += 1
                continue
        value = row.get("NumericValue")
        if value is not None and not isinstance(value, (int, float)):
            raise ValueError(f"GHO NumericValue is neither number nor null: {value!r}")
        records.append(
            RawRecord(
                entity_raw_name=spatial,  # the API prints no country name, only the code
                iso3_raw=spatial,
                year=year,
                value=float(value) if value is not None else None,
                sex=sex,
            )
        )

    if skipped_non_country:
        logger.info(
            "GHO: skipped %d non-COUNTRY row(s) (REGION/GLOBAL/income groups — the "
            "provider's own SpatialDimType classification; not stored anywhere, this "
            "log line is the record of the drop, re-fetchable from source_url).",
            skipped_non_country,
        )
    if dropped_age_slices:
        logger.info(
            "GHO: dropped %d age-disaggregated row(s) (Dim2 AGEGROUP slices beside the "
            "ALL-AGES series, latest-year explosion; the all-ages series is what this "
            "connector serves — an age slice would be a different indicator; not stored "
            "anywhere, this log line is the record of the drop, re-fetchable from source_url).",
            dropped_age_slices,
        )
    if not records:
        raise ValueError("GHO payload yielded zero COUNTRY rows: unexpected API shape")
    return records


class GhoConnector(Connector):
    provider = "who_gho"

    def __init__(self, session=None, timeout: int = 60):
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
        return RawFetchResult(
            provider=self.provider,
            source_ref=source_ref,
            indicator_id=indicator_id,
            fetched_at=RawFetchResult.now_iso(),
            source_url=url,
            records=parse_gho(response.text, code=source_ref),
        )
