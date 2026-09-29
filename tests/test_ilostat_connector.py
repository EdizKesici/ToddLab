"""ILOSTAT connector tests — the v25 harmonized provider (the ILO's own
SDMX wire).

The fixtures are the REAL full-flow responses as the API served them
(carved byte-for-byte by scripts/make_v25_fixtures.py, never typed): the
class-decomposition rate flows in their post-2026-09-24 shape — the
CITIZEN/NONCIT and NATIVE/FOREIGN class prints, both sexes' rows, the
KOS->XKX quirk, the OBS_STATUS quality codes, the TOTAL/X class drops.
Anchor values are the live-probed numbers (the v25 probe record).
"""
import json
import logging
from pathlib import Path

import pytest

from src.connectors.ilostat import (
    IlostattConnector,
    build_url,
    parse_ilostat,
)
from src.pipeline.fetch import CONNECTORS
from src.schema.indicator import Provider

FIXTURES = Path(__file__).parent / "fixtures"
CCT = (FIXTURES / "ilostat_cct_sample.json").read_text(encoding="utf-8")
CBR = (FIXTURES / "ilostat_cbr_sample.json").read_text(encoding="utf-8")
CCT_REF = "DF_UNE_DEAP_SEX_AGE_CCT_RT"
CBR_REF = "DF_UNE_DEAP_SEX_AGE_CBR_RT"


def test_connector_is_registered():
    # v25 wires the ilostat Provider — the harmonized tier's direct door
    # (the segment layers' witness, the same ilo_lfs root the WB
    # witness redistributes).
    assert isinstance(CONNECTORS[Provider.ilostat], IlostattConnector)


def test_build_url_pins_the_frame_key():
    # The bare-flow ref grammar (the DF_MIG_POPF pattern): the frame pins
    # live in the key, never in the ref — FREQ/MEASURE/AGE pinned at
    # their positions over the flow's own dimension order (REF_AREA,
    # FREQ, MEASURE, SEX, AGE, CCT|CBR), REF_AREA and SEX and the class
    # dimension OPEN.
    for flow in (CCT_REF, CBR_REF):
        url = build_url(flow)
        assert url == (
            f"https://sdmx.ilo.org/rest/data/ILO,{flow}/"
            ".A.UNE_DEAP_RT..AGE_AGGREGATE_YGE15.?format=jsondata"
        )


@pytest.mark.parametrize("bad_ref", ["", "DF_UNE_DEAP_SEX_AGE_CCT", "UNE_RT", "DF_MIG_POPF"])
def test_ref_format_is_the_two_flows_this_connector_speaks(bad_ref):
    with pytest.raises(ValueError, match="bare flow id"):
        build_url(bad_ref)


def test_parse_cct_reads_the_class_cross_section(caplog):
    # The citizenship flow's own shape (the 2026-09-24 restructure's
    # residue, read live): the CITIZEN/NONCIT classes across the world
    # cross-section, both sexes' rows riding the sex field, the FR 2025
    # anchors verified live.
    with caplog.at_level(logging.INFO):
        records = parse_ilostat(CCT, expected_ref=CCT_REF)
    assert len(records) == 822
    classes = {r.population_class for r in records}
    assert classes == {"nationals", "foreigners"}
    assert {r.segment_axis for r in records} == {"citizenship"}
    sexes = {r.sex for r in records}
    assert sexes == {None, "male", "female"}
    areas = {r.iso3_raw for r in records}
    assert len(areas) == 137
    # THE LIVE ANCHORS: FR 2025 the étrangers-vs-nationaux contrast.
    got = {
        (r.iso3_raw, r.population_class, r.year, r.sex): r.value
        for r in records if r.iso3_raw == "FRA" and r.year == 2025
    }
    assert got[("FRA", "nationals", 2025, None)] == pytest.approx(7.162)
    assert got[("FRA", "foreigners", 2025, None)] == pytest.approx(13.902)
    assert got[("FRA", "foreigners", 2025, "male")] == pytest.approx(12.961)
    assert got[("FRA", "foreigners", 2025, "female")] == pytest.approx(15.058)
    # THE KOS QUIRK: the ILO's own Kosovo code mapped to the
    # user-assigned XKX (the v21 decision, the WB's own code).
    assert any(r.iso3_raw == "XKX" and r.year == 2024 for r in records)
    # THE TOTAL/X DROPS: logged per class with the door's own labels.
    drop_logs = " ".join(r.message for r in caplog.records)
    assert "CCT_CIT_TOTAL" in drop_logs
    assert "CCT_CIT_X" in drop_logs


def test_parse_cbr_reads_the_birth_twin(caplog):
    # The birth flow's own shape: NATIVE/FOREIGN across 145 areas, the
    # FR 2025 anchors verified live.
    with caplog.at_level(logging.INFO):
        records = parse_ilostat(CBR, expected_ref=CBR_REF)
    assert len(records) == 867
    classes = {r.population_class for r in records}
    assert classes == {"natives", "foreign_born"}
    assert {r.segment_axis for r in records} == {"birth"}
    got = {
        (r.iso3_raw, r.population_class, r.year, r.sex): r.value
        for r in records if r.iso3_raw == "FRA" and r.year == 2025
    }
    assert got[("FRA", "natives", 2025, None)] == pytest.approx(7.023)
    assert got[("FRA", "foreign_born", 2025, None)] == pytest.approx(12.003)
    # Kosovo's CBR rows print 2000 (the pre-independence era) — the
    # connector emits them; normalize's covers_year guard drops them
    # honestly (the entity's valid_from floor, asserted in the
    # integration test).
    assert any(r.iso3_raw == "XKX" and r.year == 2000 for r in records)


def test_parse_transports_obs_status_as_reported():
    # OBS_STATUS rides quality_code as-reported (U "Unreliable" / B
    # "Break in series" — 19 of 105 FRA observations carry one on the
    # live slice; the fixture carries the flow's own flags).
    records = parse_ilostat(CCT, expected_ref=CCT_REF)
    flagged = [r for r in records if r.quality_code is not None]
    assert flagged  # the cross-section carries some
    assert {r.quality_code for r in flagged} <= {"U", "B"}


def test_parse_refuses_a_restructured_layout():
    # The pin-guard discipline: a response whose series dimensions are
    # not exactly [REF_AREA, FREQ, MEASURE, SEX, AGE, CCT|CBR] is a loud
    # failure — the 2026-09-24 restructure is exactly the change class
    # this guard exists to catch.
    payload = json.loads(CCT)
    dims = payload["data"]["structures"][0]["dimensions"]["series"]
    dims[0], dims[1] = dims[1], dims[0]  # swap REF_AREA and FREQ
    mangled = json.dumps(payload)
    with pytest.raises(ValueError, match="restructured"):
        parse_ilostat(mangled, expected_ref=CCT_REF)


def test_parse_refuses_an_unknown_class_code():
    # An unknown class code is a loud failure, never a guess — extending
    # the map is a deliberate registry edit.
    payload = json.loads(CBR)
    st = payload["data"]["structures"][0]
    cbr_dim = next(d for d in st["dimensions"]["series"] if d["id"] == "CBR")
    cbr_dim["values"].append({"id": "CBR_BIR_MARS", "name": "Mars-born"})
    # re-key one series onto the new class code
    series = payload["data"]["dataSets"][0]["series"]
    some_key = next(iter(series))
    idx = [int(x) for x in some_key.split(":")]
    idx[5] = len(cbr_dim["values"]) - 1
    series[":".join(str(i) for i in idx)] = series.pop(some_key)
    mangled = json.dumps(payload)
    with pytest.raises(ValueError, match="neither the class map nor the drop table"):
        parse_ilostat(mangled, expected_ref=CBR_REF)


def test_parse_refuses_non_json_and_empty_payloads():
    with pytest.raises(ValueError, match="Not ILOSTAT SDMX-JSON"):
        parse_ilostat("<html>not json</html>", expected_ref=CCT_REF)
    empty = json.dumps({"meta": {}, "data": {"dataSets": [], "structures": []}})
    with pytest.raises(ValueError, match="without a structures block"):
        parse_ilostat(empty, expected_ref=CCT_REF)
    # zero series AFTER a valid structure — the soft-miss pattern (a
    # flow id that stops answering must fail the fetch loudly).
    payload = json.loads(CCT)
    payload["data"]["dataSets"][0]["series"] = {}
    with pytest.raises(ValueError, match="zero series"):
        parse_ilostat(json.dumps(payload), expected_ref=CCT_REF)


def test_parse_refuses_a_bad_expected_ref():
    with pytest.raises(ValueError):
        parse_ilostat(CCT, expected_ref="NOT_A_FLOW")


def test_a_field_param_is_refused_the_frame_pins_live_in_the_key():
    connector = IlostattConnector()
    with pytest.raises(ValueError, match="frame pins"):
        connector.fetch_raw(CCT_REF, "unemployment_rate", field="rate")


def test_the_odd_italian_vintage_rides_as_reported():
    # ITA 2001 prints 73.8-78.5 on every class — the ILO flow's own
    # outlier vintage, transported as-reported, never corrected (the
    # plausible bound was widened to 90 for exactly this tail; the
    # divergence display shows the seam).
    records = parse_ilostat(CCT, expected_ref=CCT_REF)
    ita = {(r.population_class, r.sex): r.value for r in records if r.iso3_raw == "ITA" and r.year == 2001}
    assert ita[("foreigners", "female")] == pytest.approx(78.508)
    assert ita[("nationals", None)] == pytest.approx(75.445)
