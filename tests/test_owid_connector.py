from pathlib import Path

import pytest

from src.connectors.owid import build_url, parse_csv


def test_build_url_contains_the_slug():
    url = build_url("infant-mortality")
    assert url.startswith("https://ourworldindata.org/grapher/infant-mortality.csv")


def test_parse_csv_simple():
    csv_text = "Entity,Code,Year,Life expectancy\nFrance,FRA,2000,79.3\n"
    records = parse_csv(csv_text)
    assert len(records) == 1
    r = records[0]
    assert r.entity_raw_name == "France"
    assert r.iso3_raw == "FRA"
    assert r.year == 2000
    assert r.value == 79.3


def test_parse_csv_blank_code_becomes_none():
    csv_text = "Entity,Code,Year,X\nUSSR,,1980,10.0\n"
    records = parse_csv(csv_text)
    assert records[0].iso3_raw is None


def test_parse_csv_owid_prefixed_code_is_kept_as_is():
    # OWID uses "OWID_"-prefixed pseudo-codes for aggregates/historical
    # entities rather than leaving Code blank (see connector docstring).
    csv_text = "Entity,Code,Year,X\nUSSR,OWID_USS,1980,10.0\n"
    records = parse_csv(csv_text)
    assert records[0].iso3_raw == "OWID_USS"


def test_parse_csv_missing_value_becomes_none_not_zero():
    csv_text = "Entity,Code,Year,X\nFrance,FRA,1900,\n"
    records = parse_csv(csv_text)
    assert records[0].value is None


def test_parse_csv_multi_column_without_field_raises():
    csv_text = "Entity,Code,Year,A,B\nFrance,FRA,2000,1.0,2.0\n"
    with pytest.raises(ValueError, match="Multi-variable"):
        parse_csv(csv_text)


def test_parse_csv_multi_column_with_field_works():
    csv_text = "Entity,Code,Year,A,B\nFrance,FRA,2000,1.0,2.0\n"
    records = parse_csv(csv_text, value_field="B")
    assert records[0].value == 2.0


def test_parse_csv_missing_column_raises():
    csv_text = "Entity,Year,X\nFrance,2000,1.0\n"  # no Code column
    with pytest.raises(ValueError, match="Expected columns missing"):
        parse_csv(csv_text)


def test_real_infant_mortality_fixture_parses_without_error():
    csv_text = (Path(__file__).parent / "fixtures" / "owid_infant_mortality.csv").read_text(encoding="utf-8")
    records = parse_csv(csv_text)
    assert len(records) == 12
    # Reflects confirmed live reality (see CHANGELOG): this OWID indicator
    # has no standalone "USSR" rows, Russia carries a continuous series.
    russia_rows = [r for r in records if r.entity_raw_name == "Russia"]
    assert len(russia_rows) == 6
    assert all(r.iso3_raw == "RUS" for r in russia_rows)
    assert all(r.entity_raw_name != "USSR" for r in records)
