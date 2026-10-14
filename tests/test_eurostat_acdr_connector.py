"""Eurostat hlth_cd_acdr2 (causes-of-death crude rate by age, v30): the ref
grammar, the layout pin-guard and the country filter (NUTS-2 codes drop)."""
import json

import pytest

from src.connectors.eurostat import build_url, parse_eurostat

REF = "hlth_cd_acdr2/X60-X84_Y870/Y15-24/T"


def _payload(geos, years=("2022", "2023"), values=None, **overrides):
    """A minimal response in the live layout [freq, unit, sex, age, icd10, geo, time]."""
    dims = {
        "freq": {"category": {"index": {"A": 0}, "label": {"A": "Annual"}}},
        "unit": {"category": {"index": {"RT": 0}, "label": {"RT": "Rate"}}},
        "sex": {"category": {"index": {"T": 0}, "label": {"T": "Total"}}},
        "age": {"category": {"index": {"Y15-24": 0}, "label": {"Y15-24": "From 15 to 24 years"}}},
        "icd10": {"category": {"index": {"X60-X84_Y870": 0}, "label": {"X60-X84_Y870": "Intentional self-harm"}}},
        "geo": {
            "category": {
                "index": {g: i for i, g in enumerate(geos)},
                "label": {g: f"label {g}" for g in geos},
            }
        },
        "time": {"category": {"index": {y: i for i, y in enumerate(years)}, "label": {y: y for y in years}}},
    }
    dims.update(overrides)
    n = len(geos) * len(years)
    payload = {
        "id": ["freq", "unit", "sex", "age", "icd10", "geo", "time"],
        "size": [1, 1, 1, 1, 1, len(geos), len(years)],
        "dimension": dims,
        "value": values if values is not None else {str(i): 1.5 + i for i in range(n)},
    }
    return json.dumps(payload)


def test_build_url_pins_cause_age_sex_and_unit():
    url = build_url(REF)
    assert "hlth_cd_acdr2?" in url
    assert "icd10=X60-X84_Y870" in url and "age=Y15-24" in url and "sex=T" in url and "unit=RT" in url


def test_parse_keeps_countries_and_drops_regions_and_aggregates():
    # FR + DE are countries; FR10 is a NUTS-2 region; EU27_2020 an aggregate;
    # EL / UK are Eurostat's own codes for Greece / the United Kingdom
    text = _payload(["FR", "FR10", "EU27_2020", "DE", "EL", "UK"])
    records = parse_eurostat(text, REF)
    assert {r.iso3_raw for r in records} == {"FRA", "DEU", "GRC", "GBR"}
    assert all(r.sex is None for r in records)  # sex T = both sexes
    assert {r.year for r in records} == {2022, 2023}


def test_values_land_on_the_right_geo_and_year():
    text = _payload(["FR", "DE"], values={"0": 4.0, "1": 5.0, "2": 6.0, "3": 7.0})
    by = {(r.iso3_raw, r.year): r.value for r in parse_eurostat(text, REF)}
    assert by == {("FRA", 2022): 4.0, ("FRA", 2023): 5.0, ("DEU", 2022): 6.0, ("DEU", 2023): 7.0}


def test_pin_guard_refuses_a_slice_we_did_not_ask_for():
    text = _payload(["FR"], age={"category": {"index": {"Y15-19": 0}, "label": {"Y15-19": "x"}}})
    with pytest.raises(ValueError, match="refusing to ingest"):
        parse_eurostat(text, REF)


def test_layout_guard_refuses_another_dimension_order():
    payload = json.loads(_payload(["FR"]))
    payload["id"] = ["freq", "sex", "unit", "age", "icd10", "geo", "time"]
    with pytest.raises(ValueError, match="layout"):
        parse_eurostat(json.dumps(payload), REF)


@pytest.mark.parametrize(
    "bad_ref",
    ["hlth_cd_acdr2/X60-X84_Y870/Y15-24", "hlth_cd_acdr2/x60/Y15-24/T", "hlth_cd_acdr2/X60/15-24/T", "hlth_cd_acdr2/X60/Y15-24/Z"],
)
def test_bad_refs_are_refused(bad_ref):
    with pytest.raises(ValueError, match="Invalid Eurostat source_ref"):
        build_url(bad_ref)
