import re
from pathlib import Path

import pytest

from src.connectors.oecd import OecdConnector, build_url, parse_sdmx_csv
from src.pipeline.fetch import CONNECTORS
from src.schema.indicator import Provider

FIXTURE = Path(__file__).parent / "fixtures" / "oecd_homicide_sdmx.csv"


def test_build_url_pins_the_df_com_slice():
    url = build_url("DF_COM/CICDHOCD")
    assert url.startswith("https://sdmx.oecd.org/public/rest/data/OECD.ELS.HD,DSD_HEALTH_STAT@DF_COM,1.1/")
    # 13 positions: all countries, annual, mortality, per-100k rate, total
    # age, sex open, ..., cause pinned, CRUDE methodology pinned.
    assert url.endswith("/.A.CSEM.DT_10P5HB._T...CICDHOCD.CRUDE....?dimensionAtObservation=AllDimensions")


def test_build_url_field_selects_the_count_unit():
    assert "DT_10P5HB" not in build_url("DF_COM/CICDHOCD", field="number")
    assert ".A.CSEM.DT._T..." in build_url("DF_COM/CICDHOCD", field="number")


def test_build_url_rejects_malformed_refs():
    for bad in ["CICDHOCD", "DF_COM", "df_com/CICDHOCD", "DF_COM/", "DF_COM/CICD HOCD"]:
        with pytest.raises(ValueError, match="Invalid OECD source_ref"):
            build_url(bad)


def test_parse_sdmx_csv_maps_sexes_and_carries_iso3():
    records = parse_sdmx_csv(FIXTURE.read_text(encoding="utf-8"))
    by = {(r.iso3_raw, r.year, r.sex): r.value for r in records}
    # The sex split rides the records (_T -> None, M/F -> male/female) and
    # the REF_AREA code rides BOTH name and iso3 (it IS an ISO3).
    assert by[("RUS", 1994, None)] == pytest.approx(32.3)
    # 52.5 = the CRUDE rate the pinned URL returns (63.3 is the
    # age-standardized variant — see the pin-guard tests below).
    assert by[("RUS", 1994, "male")] == pytest.approx(52.5)
    assert by[("RUS", 1994, "female")] == pytest.approx(14.3)
    assert all(r.entity_raw_name == r.iso3_raw for r in records)
    # A modern OECD country code resolves through the registry's ISO3 path.
    assert by[("USA", 1980, "male")] == pytest.approx(12.9)


def test_parse_sdmx_csv_keeps_empty_observations_as_explicit_gaps():
    records = parse_sdmx_csv(FIXTURE.read_text(encoding="utf-8"))
    gaps = [r for r in records if r.value is None]
    # The 2021 empty OBS_VALUE is a gap, never a zero, never dropped at
    # parse time (dropping all-None keys is merge.py's canonical policy).
    assert {(r.iso3_raw, r.year, r.sex) for r in gaps} == {("FRA", 2021, None)}


def test_parse_sdmx_csv_skips_attribute_only_rows():
    # SDMX-CSV carries series-level attributes on observation-less rows
    # (seen live: IDN rows with DECIMALS/UNIT_MULT but no TIME_PERIOD):
    # metadata residue, skipped without being mistaken for data or errors.
    text = FIXTURE.read_text(encoding="utf-8")
    attribute_row = (
        "DATAFLOW,OECD.ELS.HD:DSD_HEALTH_STAT@DF_COM(1.1),I,IDN,A,CSEM,DT_10P5HB,"
        "_T,F,_Z,CICDHOCD,CRUDE,_Z,_Z,_Z,_Z,,,1,,,,0\n"
    )
    records = parse_sdmx_csv(text + attribute_row)
    assert all(r.iso3_raw != "IDN" for r in records)
    assert len(records) == 8


def test_parse_sdmx_csv_refuses_non_sdmx_bodies():
    with pytest.raises(ValueError, match="Not an SDMX-CSV data response"):
        parse_sdmx_csv("Entity,Code,Year,Value\nFrance,FRA,2000,1.0\n")


def test_parse_sdmx_csv_refuses_empty_responses():
    header = FIXTURE.read_text(encoding="utf-8").splitlines()[0]
    with pytest.raises(ValueError, match="No data rows"):
        parse_sdmx_csv(header + "\n")


@pytest.mark.parametrize(
    ("old", "new", "needle"),
    [
        # the methodology flip: DF_COM also carries the age-standardized
        # variant of the same keys — it must never slip in as canonical
        (",CRUDE,", ",STANDARD,", "CALC_METHODOLOGY='STANDARD'"),
        # the unit flip: death counts (DT) where rates were asked for
        (",DT_10P5HB,", ",DT,", "UNIT_MEASURE='DT'"),
        # the frequency flip: anything but annual observations
        (",RUS,A,", ",RUS,M,", "FREQ='M'"),
    ],
)
def test_parse_sdmx_csv_refuses_slices_the_url_did_not_pin(old, new, needle):
    # The v8 review's guard: build_url() pins FREQ/MEASURE/UNIT_MEASURE/AGE/
    # CALC_METHODOLOGY, but the v8 parser trusted the URL and never looked
    # at those columns — a response mixing in another slice would have been
    # ingested as as-reported data. Every data row is now verified against
    # the pins and refused loudly.
    sabotaged = FIXTURE.read_text(encoding="utf-8").replace(old, new, 1)
    with pytest.raises(ValueError, match=re.escape(needle)):
        parse_sdmx_csv(sabotaged)


def test_parse_sdmx_csv_refuses_the_literal_v8_fixture_row():
    # The exact row that shipped in v8's fixture, frozen as the regression:
    # STANDARD-labeled, reading the age-standardized 63.3 where the crude
    # 52.5 belongs — the copy-paste the review traced through the
    # docstring, the config and the fixture. The parser must refuse it.
    v8_row = (
        "DATAFLOW,OECD.ELS.HD:DSD_HEALTH_STAT@DF_COM(1.1),I,RUS,A,CSEM,"
        "DT_10P5HB,_T,M,_Z,CICDHOCD,STANDARD,_Z,_Z,_Z,_Z,1994,63.3,1,,,,0\n"
    )
    header = FIXTURE.read_text(encoding="utf-8").splitlines()[0]
    with pytest.raises(ValueError, match=re.escape("CALC_METHODOLOGY='STANDARD'")):
        parse_sdmx_csv(header + "\n" + v8_row)


def test_parse_sdmx_csv_verifies_the_death_cause_when_given():
    text = FIXTURE.read_text(encoding="utf-8")
    # A response answering a DIFFERENT cause's question is refused when the
    # caller says which cause it asked for (fetch_raw always does).
    wrong_cause = text.replace(",CICDHOCD,", ",CIHDHOCD,", 1)
    with pytest.raises(ValueError, match=re.escape("DEATH_CAUSE='CIHDHOCD'")):
        parse_sdmx_csv(wrong_cause, death_cause="CICDHOCD")
    # ...and the honest response parses cleanly under the same pin.
    assert len(parse_sdmx_csv(text, death_cause="CICDHOCD")) == 8


def test_connector_is_registered_and_declared_collector():
    assert Provider.oecd in CONNECTORS
    assert CONNECTORS[Provider.oecd].provider == "oecd"
    from src.schema.indicator import PROVIDER_LAYER

    assert PROVIDER_LAYER[Provider.oecd] == "collector"


def test_connector_fetch_raw_parses_the_response():
    class FakeResponse:
        status_code = 200
        text = FIXTURE.read_text(encoding="utf-8")

        def raise_for_status(self):
            pass

    class FakeSession:
        def get(self, url, headers=None, timeout=None):
            assert "CICDHOCD" in url and "DT_10P5HB" in url
            assert headers["Accept"].startswith("application/vnd.sdmx.data+csv")
            return FakeResponse()

    result = OecdConnector(session=FakeSession()).fetch_raw("DF_COM/CICDHOCD", "homicide_rate")
    assert result.provider == "oecd"
    assert result.source_url.endswith("?dimensionAtObservation=AllDimensions")
    assert len(result.records) == 8
    # OBS_STATUS is empty across the assault series as of 2026-09: the
    # connector carries the flag when printed, never invents one.
    assert all(r.quality_code is None for r in result.records)
