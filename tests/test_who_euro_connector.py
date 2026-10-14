"""WHO/Europe Data Warehouse connector (v30): pure parsing, the pin-guards,
the group-average filter and the TLS adapter's trust setup."""
import json
import ssl

import pytest

from src.connectors.who_euro import (
    _INTERMEDIATE_PEM,
    build_url,
    make_session,
    parse_who_euro,
)

REF = "HFA_586"


def _row(country, year, value, grp="", measure="RATE", sex="ALL"):
    return {
        "attributes": {"MEASURE_TYPE": measure},
        "dimensions": {"COUNTRY": country, "COUNTRY_GRP": grp, "SEX": sex, "YEAR": str(year)},
        "value": {"display": str(value), "numeric": value},
    }


def _payload(rows=None, code=REF, unit="PROC_1000LBIRTH"):
    return json.dumps(
        {
            "code": code,
            "metadata": [{"code": "UNIT_TYPE", "value": {"code": unit}}],
            "dimensions": [
                {
                    "code": "COUNTRY",
                    "values": [
                        {"code": "FRA", "iso3": "FRA", "short_name": "France"},
                        {"code": "BEL", "iso3": "BEL", "short_name": "Belgium"},
                    ],
                }
            ],
            "data": rows
            if rows is not None
            else [_row("FRA", 2018, 292.49), _row("FRA", 2019, 305.77), _row("BEL", 2019, 153.17)],
        }
    )


def test_parse_keeps_country_rows():
    records = parse_who_euro(_payload(), REF)
    by = {(r.iso3_raw, r.year): r.value for r in records}
    assert by == {("FRA", 2018): 292.49, ("FRA", 2019): 305.77, ("BEL", 2019): 153.17}
    assert records[0].entity_raw_name == "France" and records[0].sex is None


def test_group_averages_are_not_countries():
    rows = [_row("FRA", 2019, 305.77), _row("", 2019, 99.0, grp="EU_MEMBERS", measure="AVG_PW")]
    records = parse_who_euro(_payload(rows), REF)
    assert [r.iso3_raw for r in records] == ["FRA"]


def test_pin_guard_other_measure():
    with pytest.raises(ValueError, match="refusing to ingest"):
        parse_who_euro(_payload(code="HFA_588"), REF)


def test_pin_guard_changed_unit():
    with pytest.raises(ValueError, match="unit"):
        parse_who_euro(_payload(unit="NUM_ABORT"), REF)


def test_unregistered_measure_is_refused():
    with pytest.raises(ValueError, match="No registered unit"):
        parse_who_euro(_payload(code="HFA_587"), "HFA_587")


@pytest.mark.parametrize(
    "bad_row",
    [
        _row("FRA", 2019, 1.0, sex="F"),
        _row("FRA", 2019, 1.0, measure="COUNT"),
        _row("XXX", 2019, 1.0),
        {**_row("FRA", 2019, 1.0), "dimensions": {"COUNTRY": "FRA", "COUNTRY_GRP": "", "SEX": "ALL", "YEAR": "n/a"}},
    ],
)
def test_malformed_country_rows_raise(bad_row):
    with pytest.raises(ValueError):
        parse_who_euro(_payload([bad_row]), REF)


def test_duplicate_observation_raises():
    with pytest.raises(ValueError, match="Duplicate"):
        parse_who_euro(_payload([_row("FRA", 2019, 1.0), _row("FRA", 2019, 2.0)]), REF)


def test_null_numeric_stays_an_explicit_gap():
    row = _row("FRA", 2019, 1.0)
    row["value"] = {"display": "", "numeric": None}
    assert parse_who_euro(_payload([row]), REF)[0].value is None


def test_no_country_rows_is_a_loud_failure():
    with pytest.raises(ValueError, match="no country rows"):
        parse_who_euro(_payload([_row("", 2019, 9.0, grp="CIS", measure="AVG_PW")]), REF)


@pytest.mark.parametrize("bad_ref", ["586", "HFA_", "hfa_586", "HFA_586/x"])
def test_bad_refs_are_refused(bad_ref):
    with pytest.raises(ValueError, match="Invalid WHO/Europe DW source_ref"):
        build_url(bad_ref)


def test_build_url():
    assert build_url(REF) == "https://dw.euro.who.int/api/v5/measures/HFA_586"


def test_tls_adapter_keeps_full_verification_and_trusts_the_shipped_intermediate():
    session = make_session()
    adapter = session.get_adapter("https://dw.euro.who.int/api/v5/measures/HFA_586")
    ctx = adapter.poolmanager.connection_pool_kw["ssl_context"]
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname is True
    assert "BEGIN CERTIFICATE" in _INTERMEDIATE_PEM.read_text()
    # other hosts keep requests' default adapter (no extra trust anchor)
    assert "ssl_context" not in session.get_adapter("https://example.org/").poolmanager.connection_pool_kw
