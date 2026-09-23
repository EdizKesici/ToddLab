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


# ---------------------------------------------------------------------------
# v20 — the PISA door (the math canonical): a THREE-column chart door
# (Mathematics/Science/Reading) whose mathematics column is pinned by
# the config's field. The v20 fixtures generated from the live API
# 2026-09-22 (anchors read, never typed).

PISA = (Path(__file__).parent / "fixtures" / "owid_pisa_math.csv").read_text(encoding="utf-8")


def test_parse_pisa_door_with_the_mathematics_field_pin():
    records = parse_csv(PISA, value_field="Mathematics")
    got = {(r.entity_raw_name, r.year): r for r in records}

    # THE LIVE ANCHORS: the French slide's endpoints, the American
    # mid-band, Japan's stable top, the scale's own ceiling/floor.
    assert got[("France", 2003)].value == pytest.approx(510.79947)
    assert got[("France", 2022)].value == pytest.approx(473.94443)
    assert got[("United States", 2003)].value == pytest.approx(482.88278)
    assert got[("Singapore", 2022)].value == pytest.approx(574.6638)
    assert got[("Qatar", 2006)].value == pytest.approx(317.95566)
    assert got[("Japan", 2003)].value == pytest.approx(534.1365)
    # THE 2000 READING-ONLY ROW arrives as an EXPLICIT GAP (the door's
    # own shape — PISA 2000's major domain was reading, no math mean).
    assert got[("France", 2000)].value is None
    # RUSSIA's six cycles parse; the 2022 absence is the door's own
    # coverage gap (no row at all — the cycle Russia did not sit).
    assert got[("Russia", 2018)].value == pytest.approx(487.78653)
    assert ("Russia", 2022) not in got
    # No sex column on the door — every record both-sexes.
    assert all(r.sex is None for r in records)


def test_parse_pisa_door_without_field_raises():
    # The chart is multi-variable (Mathematics/Science/Reading + none
    # fixed): the unpinned call refuses loudly, never guesses a column.
    with pytest.raises(ValueError, match="Multi-variable"):
        parse_csv(PISA)


def test_parse_pisa_door_with_wrong_field_raises():
    # A typo'd field pin refuses with the available columns named —
    # the guard that keeps the pin honest.
    with pytest.raises(ValueError, match="Column 'Mathematic' not found"):
        parse_csv(PISA, value_field="Mathematic")
