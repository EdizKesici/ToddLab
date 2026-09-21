"""World Bank (WDI v2) connector tests — the phase-5 provider.

The fixture mirrors a real response slice: the [meta, rows] page shape,
the /country metadata's own aggregate classification, the trailing-2025
null (an honest gap, not a skip), the .MA.IN suffix convention. Values
are synthetic by the fixtures README rule — never quoted as live data.
"""
from pathlib import Path

import pytest

from src.connectors.base import RawFetchResult
from src.connectors.worldbank import (
    WB_COUNTRY_META_URL,
    WorldbankConnector,
    build_url,
    parse_country_meta,
    parse_wb,
)
from src.pipeline.fetch import CONNECTORS
from src.schema.indicator import Provider

FIXTURES = Path(__file__).parent / "fixtures"
PAGE = (FIXTURES / "wb_imrt_ma_sample.json").read_text(encoding="utf-8")
META = (FIXTURES / "wb_country_meta_sample.json").read_text(encoding="utf-8")
CODE = "SP.DYN.IMRT.MA.IN"


def _aggregate_ids() -> set[str]:
    return parse_country_meta(META)


def test_build_url_pins_the_query_shape():
    assert build_url(CODE) == (
        "https://api.worldbank.org/v2/country/all/indicator/SP.DYN.IMRT.MA.IN"
        "?format=json&per_page=5000"
    )


def test_connector_is_registered():
    # worldbank was the phase-5 Provider enum value with no connector since
    # phase 1 ("deliberately absent"); v11 wires it.
    assert isinstance(CONNECTORS[Provider.worldbank], WorldbankConnector)


def test_parse_country_meta_extracts_the_providers_own_classification():
    # region.id == "NA" is the provider's own "Aggregates" bucket, in BOTH
    # joinable forms: the metadata id (regional aggregates join on it via
    # countryiso3code) and the iso2Code (the income groups join on it via
    # country.id — their data rows print an EMPTY iso3). Kosovo is NOT an
    # aggregate (a real territory in the provider's classification).
    assert _aggregate_ids() == {"WLD", "1W", "AFE", "ZH", "HIC", "XD"}


def test_parse_wb_keeps_countries_only():
    records = parse_wb([PAGE], _aggregate_ids(), expected_code=CODE)
    # World (by iso3), AFE (by iso3) and High income (by the two-letter
    # id — its empty-iso3 path, the live-verified leak) are dropped;
    # Kosovo flows through to normalize's unresolved report.
    assert [(r.iso3_raw, r.year) for r in records] == [
        ("RUS", 1990), ("RUS", 2025), ("FRA", 2020), ("ZWE", 1990), ("XKX", 2020), ("FRA", 1960),
    ]
    assert all(r.entity_raw_name for r in records)  # the printed name rides along


def test_parse_wb_kosovo_flows_to_the_unresolved_report():
    # NOT an aggregate in the provider's own classification: a pending
    # product decision (same class as OWID's OWID_KOS pseudo-codes), so
    # the parser keeps the row — normalize will report it unresolved.
    records = parse_wb([PAGE], _aggregate_ids(), expected_code=CODE)
    kosovo = [r for r in records if r.entity_raw_name == "Kosovo"]
    assert len(kosovo) == 1
    assert kosovo[0].iso3_raw == "XKX"
    assert kosovo[0].value == pytest.approx(9.9)


def test_parse_wb_null_value_is_an_explicit_gap():
    # The trailing-2025 slot exists with no estimate: value=None, never a
    # skip (the same honest treatment as a GHO null estimate).
    rus_2025 = next(r for r in parse_wb([PAGE], _aggregate_ids(), expected_code=CODE) if r.year == 2025)
    assert rus_2025.value is None


def test_parse_wb_sex_comes_from_the_code_suffix():
    # .MA.IN -> male; .FE.IN -> female; the bare code -> both sexes (None).
    records = parse_wb([PAGE], _aggregate_ids(), expected_code=CODE)
    assert all(r.sex == "male" for r in records)

    female = PAGE.replace("SP.DYN.IMRT.MA.IN", "SP.DYN.IMRT.FE.IN").replace(", male (", ", female (")
    assert all(r.sex == "female" for r in parse_wb([female], _aggregate_ids(), expected_code="SP.DYN.IMRT.FE.IN"))

    both = PAGE.replace("SP.DYN.IMRT.MA.IN", "SP.DYN.IMRT.IN").replace(", male (", " (")
    assert all(r.sex is None for r in parse_wb([both], _aggregate_ids(), expected_code="SP.DYN.IMRT.IN"))


def test_parse_wb_refuses_a_name_suffix_sex_mismatch():
    # The bidirectional pin-guard: a .MA.IN code whose printed name says
    # something else (here: the name still says male after the code was
    # swapped to the bare code) must raise, never ingest a mislabeled slice.
    swapped = PAGE.replace("SP.DYN.IMRT.MA.IN", "SP.DYN.IMRT.IN")
    with pytest.raises(ValueError, match="code/name sex mismatch"):
        parse_wb([swapped], _aggregate_ids(), expected_code="SP.DYN.IMRT.IN")

    reverse = PAGE.replace(", male (per 1,000 live births)", ", female (per 1,000 live births)")
    with pytest.raises(ValueError, match="code/name sex mismatch"):
        parse_wb([reverse], _aggregate_ids(), expected_code=CODE)


def test_parse_wb_bare_maternal_codes_carry_no_sex():
    # v12: the maternal bloc's two WDI codes are BARE (no .MA.IN/.FE.IN
    # suffix — the series has no sex dimension) and their printed names
    # carry no sex slice either. The bidirectional cross-check must pass
    # with sex=None on BOTH: these are the real names the live API prints
    # (verified 2026-09-13), pinned here so a future name change that
    # introduces a slice raises instead of silently mislabeling.
    for code, name in (
        ("SH.STA.MMRT", "Maternal mortality ratio (modeled estimate, per 100,000 live births)"),
        ("SH.MMR.DTHS", "Number of maternal deaths"),
    ):
        page = PAGE.replace(
            "Mortality rate, infant, male (per 1,000 live births)", name
        ).replace("SP.DYN.IMRT.MA.IN", code)
        records = parse_wb([page], _aggregate_ids(), expected_code=code)
        assert records
        assert all(r.sex is None for r in records), code


def test_parse_wb_refuses_a_row_of_another_indicator():
    with pytest.raises(ValueError, match="refusing to ingest a slice we did not ask for"):
        parse_wb([PAGE], _aggregate_ids(), expected_code="SP.DYN.LE00.MA.IN")


def test_parse_wb_refuses_a_non_annual_date():
    quarterly = PAGE.replace('"date": "1990"', '"date": "1990Q1"')
    with pytest.raises(ValueError, match="non-annual date"):
        parse_wb([quarterly], _aggregate_ids(), expected_code=CODE)


def test_parse_wb_refuses_a_string_value():
    dotted = PAGE.replace('"date": "1990", "value": 17.5', '"date": "1990", "value": ".."')
    with pytest.raises(ValueError, match="neither number nor null"):
        parse_wb([dotted], _aggregate_ids(), expected_code=CODE)


def test_parse_wb_refuses_non_json():
    with pytest.raises(ValueError, match="Not World Bank JSON"):
        parse_wb(["<html>error page</html>"], _aggregate_ids(), expected_code=CODE)


def test_parse_wb_refuses_a_payload_without_the_meta_rows_pair():
    with pytest.raises(ValueError, match=r"without the \[meta, rows\] pair"):
        parse_wb(['{"message": "error"}'], _aggregate_ids(), expected_code=CODE)


def test_parse_wb_aggregates_pages():
    # Two pages, each with its own [meta, rows] — the parser concatenates
    # and the total set is the union.
    import json as _json

    rows = _json.loads(PAGE)[1]
    page1 = _json.dumps(
        [{"page": 1, "pages": 2, "per_page": 5000, "total": 8}, rows[:-1]]
    )
    page2 = _json.dumps([{"page": 2, "pages": 2, "per_page": 5000, "total": 8}, [rows[-1]]])
    records = parse_wb([page1, page2], _aggregate_ids(), expected_code=CODE)
    assert len(records) == 6
    assert {r.year for r in records} == {1960, 1990, 2020, 2025}


class _MockResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class _MockSession:
    """Serves the /country metadata once + the data pages of each requested
    code, in page order (routed by code so several codes can coexist)."""

    def __init__(self, pages_by_code: dict[str, list[str]]):
        self._pages_by_code = pages_by_code
        self._seen_urls: list[str] = []

    def get(self, url, headers=None, timeout=None):
        self._seen_urls.append(url)
        if url.startswith(WB_COUNTRY_META_URL):
            return _MockResponse(META)
        code = url.split("/indicator/")[1].split("?")[0]
        page = int(url.rsplit("page=", 1)[1])
        return _MockResponse(self._pages_by_code[code][page - 1])


def test_fetch_raw_paginates_and_wraps():
    # pages=1 in the fixture meta: exactly ONE data request (plus the
    # country metadata fetch), then the parsed records are wrapped.
    session = _MockSession({CODE: [PAGE]})
    connector = WorldbankConnector(session=session)
    result = connector.fetch_raw(CODE, "infant_mortality")
    assert isinstance(result, RawFetchResult)
    assert result.provider == "worldbank"
    assert result.source_url == build_url(CODE)
    assert len(result.records) == 6
    data_requests = [u for u in session._seen_urls if "indicator" in u]
    assert len(data_requests) == 1
    assert data_requests[0] == build_url(CODE) + "&page=1"


def test_fetch_raw_requests_every_page():
    # A pages=2 response: the connector must come back for page 2.
    import json as _json

    rows = _json.loads(PAGE)[1]
    page1 = _json.dumps([{"page": 1, "pages": 2, "per_page": 3, "total": 7}, rows[:3]])
    page2 = _json.dumps([{"page": 2, "pages": 2, "per_page": 3, "total": 7}, rows[3:]])
    session = _MockSession({CODE: [page1, page2]})
    result = WorldbankConnector(session=session).fetch_raw(CODE, "infant_mortality")
    assert len(result.records) == 6
    data_requests = [u for u in session._seen_urls if "indicator" in u]
    assert [u.rsplit("page=", 1)[1] for u in data_requests] == ["1", "2"]


def test_fetch_raw_reuses_the_cached_aggregate_classification():
    # The /country metadata is request metadata, not indicator data: the
    # second fetch on the same connector must not re-request it (its page
    # carries the FE code — the pin-guard would reject an MA response).
    fe_page = PAGE.replace("SP.DYN.IMRT.MA.IN", "SP.DYN.IMRT.FE.IN").replace(", male (", ", female (")
    session = _MockSession({CODE: [PAGE], "SP.DYN.IMRT.FE.IN": [fe_page]})
    connector = WorldbankConnector(session=session)
    connector.fetch_raw(CODE, "infant_mortality")
    connector.fetch_raw("SP.DYN.IMRT.FE.IN", "infant_mortality")
    meta_requests = [u for u in session._seen_urls if u.startswith(WB_COUNTRY_META_URL)]
    assert len(meta_requests) == 1
