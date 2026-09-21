import logging
from pathlib import Path

import pytest

from src.connectors.base import RawFetchResult
from src.connectors.gho import GhoConnector, build_url, parse_gho
from src.pipeline.fetch import CONNECTORS
from src.schema.indicator import Provider

FIXTURE = Path(__file__).parent / "fixtures" / "gho_whosis_000015_sample.json"


def test_build_url():
    assert build_url("WHOSIS_000015") == "https://ghoapi.azureedge.net/api/WHOSIS_000015"


def test_connector_is_registered():
    # who_gho was a Provider enum value with no connector since phase 1;
    # v10 wires it (the LE-60 witness) — the SKIP path is gone.
    assert isinstance(CONNECTORS[Provider.who_gho], GhoConnector)


def test_parse_gho_keeps_country_rows_only():
    # The provider's own SpatialDimType classification separates countries
    # from REGION / WORLDBANKINCOMEGROUP / GLOBAL rows: only COUNTRY rows
    # become records (the dropped aggregates are stored nowhere — the log
    # line is the record of the drop).
    records = parse_gho(FIXTURE.read_text(encoding="utf-8"))
    assert {(r.entity_raw_name, r.year, r.sex) for r in records} == {
        ("FRA", 2020, "male"),
        ("FRA", 2020, "female"),
        ("FRA", 2020, None),
        ("FRA", 2021, "male"),
        ("RUS", 2012, "male"),
        ("RUS", 2012, "female"),
        ("JPN", 2019, None),
    }
    # iso3_raw carries the code: GHO resolution goes through _by_iso3.
    assert all(r.iso3_raw == r.entity_raw_name for r in records)


def test_parse_gho_drop_log_line_is_the_record_of_the_drop(caplog):
    # v11.1 regression guard: the log line that runs at every fetch must
    # say what the module docstring says — the dropped aggregate rows are
    # not stored anywhere, THIS line is the record of the drop. (The v11
    # fix reworded the docstring but left the log line claiming they "stay
    # in the raw snapshot" — the two contradicted each other in the same
    # file, and no check was looking at the log text.)
    with caplog.at_level(logging.INFO, logger="src.connectors.gho"):
        parse_gho(FIXTURE.read_text(encoding="utf-8"))
    drop_lines = [r for r in caplog.records if "non-COUNTRY" in r.getMessage()]
    assert len(drop_lines) == 1
    message = drop_lines[0].getMessage()
    assert "not stored anywhere" in message
    assert "stay in the raw snapshot" not in message


def test_parse_gho_sex_dimension_mapping():
    # SEX_MLE / SEX_FMLE / SEX_BTSX -> the project's vocabulary; BTSX (both
    # sexes) is sex=None so the (entity, year, sex) merge key keeps the
    # three series apart — a both-sexes witness never collides with the
    # sex-split canonical.
    by_key = {(r.entity_raw_name, r.year, r.sex): r.value for r in parse_gho(FIXTURE.read_text(encoding="utf-8"))}
    assert by_key[("FRA", 2020, "male")] == pytest.approx(22.4444444444444)
    assert by_key[("FRA", 2020, "female")] == pytest.approx(26.2345678901234)
    assert by_key[("FRA", 2020, None)] == pytest.approx(24.3456789012345)


def test_parse_gho_null_numeric_value_is_an_explicit_gap():
    # A null estimate stays a value=None point (the honest gap), never a
    # skip and never a zero.
    jpn = [r for r in parse_gho(FIXTURE.read_text(encoding="utf-8")) if r.entity_raw_name == "JPN"]
    assert len(jpn) == 1
    assert jpn[0].value is None


def test_parse_gho_refuses_a_non_year_time_dimension():
    text = FIXTURE.read_text(encoding="utf-8").replace('"TimeDimType": "YEAR"', '"TimeDimType": "MONTH"')
    with pytest.raises(ValueError, match="non-YEAR TimeDim"):
        parse_gho(text)


def test_parse_gho_refuses_an_unknown_dim1_type():
    text = FIXTURE.read_text(encoding="utf-8").replace('"Dim1Type": "SEX"', '"Dim1Type": "AGEGROUP"')
    with pytest.raises(ValueError, match="Dim1Type.*SEX dimension"):
        parse_gho(text)


# --- Dim2 (v13, SDGSUICIDE): the age-disaggregation rule --------------------


SDGSUICIDE_FIXTURE = Path(__file__).parent / "fixtures" / "gho_sdgsuicide_sample.json"


def test_parse_gho_keeps_yearsall_and_drops_the_age_slices(caplog):
    # SDGSUICIDE prints 11 age bands BESIDE the all-ages record on the
    # latest year (verified live: 6,105 slice rows over 12,210 all-ages
    # keys). The connector keeps AGEGROUP_YEARSALL, drops the slices, and
    # the drop is recorded by the log line — never a silent disappearance.
    import logging

    with caplog.at_level(logging.INFO):
        records = parse_gho(SDGSUICIDE_FIXTURE.read_text(encoding="utf-8"))
    by_key = {(r.entity_raw_name, r.year, r.sex): r.value for r in records}
    # the all-ages series: RUS 2000 sex-split (the real live values)...
    assert by_key[("RUS", 2000, "male")] == pytest.approx(95.20444591)
    assert by_key[("RUS", 2000, "female")] == pytest.approx(16.04984872)
    assert by_key[("RUS", 2000, None)] == pytest.approx(53.05820987)
    # ...RUS 2021 (the disaggregated year) resolves to the YEARSALL record
    assert by_key[("RUS", 2021, "male")] == pytest.approx(36.68325073)
    # the two slice rows in the fixture (50-69, 15-29) are gone: the key
    # count proves no duplicate slipped through as a second record
    assert len(records) == 7  # RUS: 3x2000 + M/BTSX 2021, LTU: 2x2000; dropped: 2 slices + 1 REGION
    drop_lines = [r for r in caplog.records if "age-disaggregated" in r.getMessage()]
    assert len(drop_lines) == 1
    assert "2" in drop_lines[0].getMessage()  # the dropped count rides the log line


def test_parse_gho_refuses_an_unknown_dim2_type():
    # AGEGROUP is the only Dim2 disaggregation this connector interprets;
    # anything else (WEALTHQUINTILE, RESIDENCE...) is a layout surprise
    # that must fail loudly, never be silently ingested or re-interpreted.
    text = SDGSUICIDE_FIXTURE.read_text(encoding="utf-8").replace('"Dim2Type": "AGEGROUP"', '"Dim2Type": "WEALTHQUINTILE"')
    with pytest.raises(ValueError, match="Dim2Type.*WEALTHQUINTILE.*AGEGROUP"):
        parse_gho(text)


def test_parse_gho_dim2_less_indicators_still_parse():
    # The pre-v13 shape (WHOSIS_000015, MDG_0000000001: Dim2 absent) is
    # untouched by the rule — the guard only fires when a Dim2 is present.
    records = parse_gho(FIXTURE.read_text(encoding="utf-8"))
    assert records  # the LE-60 fixture parses exactly as before v13


def test_parse_gho_refuses_non_json():
    with pytest.raises(ValueError, match="Not GHO JSON"):
        parse_gho("<html>error page</html>")


def test_parse_gho_refuses_a_payload_without_value_array():
    with pytest.raises(ValueError, match="without a 'value' array"):
        parse_gho('{"error": "not found"}')


class _MockResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class _MockSession:
    def get(self, url, headers=None, timeout=None):
        assert url == "https://ghoapi.azureedge.net/api/WHOSIS_000015"
        return _MockResponse(FIXTURE.read_text(encoding="utf-8"))


def test_fetch_raw_parses_and_wraps():
    connector = GhoConnector(session=_MockSession())
    result = connector.fetch_raw("WHOSIS_000015", "life_expectancy_60")
    assert isinstance(result, RawFetchResult)
    assert result.provider == "who_gho"
    assert result.source_url == "https://ghoapi.azureedge.net/api/WHOSIS_000015"
    assert len(result.records) == 7
