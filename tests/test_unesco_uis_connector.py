"""UNESCO UIS connector: pure parsing, the pin-guard and the loud failures."""
import json
from pathlib import Path

import pytest

from src.connectors.unesco_uis import build_url, parse_uis

FIXTURE = (Path(__file__).parent / "fixtures" / "uis_mys.json").read_text(encoding="utf-8")
CODE = "MYS.1T8.AG25T99"


def test_parse_uis_records():
    records = parse_uis(FIXTURE, CODE)
    assert len(records) == 5
    fra = [r for r in records if r.iso3_raw == "FRA"]
    assert [(r.year, r.value) for r in fra] == [(2015, 11.33), (2019, 11.61)]
    assert all(r.sex is None for r in records)  # both sexes: the bare code
    assert records[0].entity_raw_name == "FRA"


def test_sex_comes_from_the_code_suffix():
    payload = json.loads(FIXTURE)
    for rec in payload["records"]:
        rec["indicatorId"] = CODE + ".F"
    records = parse_uis(json.dumps(payload), CODE + ".F")
    assert {r.sex for r in records} == {"female"}


def test_pin_guard_refuses_another_indicator():
    with pytest.raises(ValueError, match="refusing to ingest"):
        parse_uis(FIXTURE, "MYS.1T8.AG25T99.F")


def test_unknown_indicator_is_a_loud_failure_not_an_empty_series():
    empty = json.dumps(
        {"hints": [{"code": "UIS::HINT::001", "message": "The indicator could not be found"}], "records": []}
    )
    with pytest.raises(ValueError, match="zero records"):
        parse_uis(empty, "NOPE")


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r.update(geoUnit="WORLD"),
        lambda r: r.update(year="2015"),
        lambda r: r.update(value="11.3"),
    ],
)
def test_malformed_rows_raise(mutation):
    payload = json.loads(FIXTURE)
    mutation(payload["records"][0])
    with pytest.raises(ValueError):
        parse_uis(json.dumps(payload), CODE)


def test_null_value_stays_an_explicit_gap():
    payload = json.loads(FIXTURE)
    payload["records"][0]["value"] = None
    records = parse_uis(json.dumps(payload), CODE)
    assert records[0].value is None


def test_build_url_pins_national_level():
    url = build_url(CODE)
    assert "indicator=MYS.1T8.AG25T99" in url and "geoUnitType=NATIONAL" in url
