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


# ---------------------------------------------------------------------------
# v18 — cirrhosis (CICDCIRR, "Chronic liver diseases and cirrhosis"): the
# third cause-code config on the same connector. The fixture was generated
# from the LIVE slice (2026-09-21) — the v13 probe's "404 NoRecordsFound"
# note was a probe artifact: the full slice answers 7,089 records.

CIRRHOSIS = (Path(__file__).parent / "fixtures" / "oecd_cicdcirr_sdmx.csv").read_text(encoding="utf-8")


def test_parse_cirrhosis_carries_the_todd_benchmark_pair():
    records = parse_sdmx_csv(CIRRHOSIS, field="rate", death_cause="CICDCIRR")
    got = {(r.iso3_raw, r.year, r.sex): r for r in records}

    # LA CHUTE FINALE'S OWN CALIBRATION PAIR, as the collector prints it:
    # France vs Sweden 1979 — the cirrhosis rates that scale the Soviet
    # alcoholism estimate. The both-sexes rate 2.4x Sweden's while the
    # male rates nearly match: the class-and-gender structure the book
    # reads is IN the numbers themselves. (France 1979 prints NO sex
    # split — the both-sexes row is the era's own face; Sweden's split
    # rides from 1960.)
    assert got[("FRA", 1979, None)].value == pytest.approx(29.0)
    assert got[("SWE", 1979, None)].value == pytest.approx(12.2)
    assert got[("SWE", 1979, "male")].value == pytest.approx(17.5)
    assert got[("SWE", 1979, "female")].value == pytest.approx(7.0)
    # Le Fou et le Prolétaire's Mediterranean pole: Italy's cohort-memory
    # tail, the live slice's own maximum.
    assert got[("ITA", 1979, None)].value == pytest.approx(34.7)
    assert got[("ITA", 1979, "male")].value == pytest.approx(50.0)
    # Germany's post-reunification face (the door starts DEU at 1990;
    # the sex split prints from 1994 everywhere).
    assert got[("DEU", 1994, None)].value == pytest.approx(24.4)
    assert got[("DEU", 1994, "male")].value == pytest.approx(32.9)
    # the flag rows the live slice carries (KOR 1995 'B' break, TUR
    # 2010/2015 'D' definition-differs) ride quality_code as-reported.
    assert got[("KOR", 1995, None)].quality_code == "B"
    assert got[("TUR", 2010, None)].quality_code == "D"
    # RUSSIA IS ABSENT FROM THIS CAUSE'S SLICE (probed live: RUS rides
    # the dataflow for CICDHARM/CICDHOCD but not CICDCIRR — the WHO-MDB
    # coding fact that IS the Russian alcohol story; the GHE witness
    # carries the modeled redistribution that covers Russia).
    assert all(r.iso3_raw != "RUS" for r in records)


def test_parse_cirrhosis_refuses_the_wrong_cause_pin():
    # The death-cause pin (v8.1 guard): a CICDCIRR payload under a
    # CICDHARM ref is refused loudly, never silently ingested.
    import re

    with pytest.raises(ValueError, match=re.escape("DEATH_CAUSE='CICDCIRR'")):
        parse_sdmx_csv(CIRRHOSIS, field="rate", death_cause="CICDHARM")


# ---------------------------------------------------------------------------
# v19: the two new dataflows — DF_IDD (the Income Distribution Database,
# the gini canonical) and DF_SAFETY (the ITF/IRTAD road-safety statistics,
# the road-mortality canonical). Fixtures live-carved 2026-09-21 through
# the connector's own build_url (the discipline: anchors are READ, never
# typed). Neither flow carries a SEX dimension — every record sex=None.
# ---------------------------------------------------------------------------
from src.connectors.oecd import parse_idd_csv, parse_safety_csv  # noqa: E402

IDD_CUR = (Path(__file__).parent / "fixtures" / "oecd_idd_gini_cur.csv").read_text(encoding="utf-8")
IDD_PREVDEF = (Path(__file__).parent / "fixtures" / "oecd_idd_gini_prevdef.csv").read_text(encoding="utf-8")
IDD_INCDEF = (Path(__file__).parent / "fixtures" / "oecd_idd_gini_incdef.csv").read_text(encoding="utf-8")
IDD_M2011 = (Path(__file__).parent / "fixtures" / "oecd_idd_gini_m2011.csv").read_text(encoding="utf-8")
SAFETY = (Path(__file__).parent / "fixtures" / "itf_safety_road_mortality.csv").read_text(encoding="utf-8")


def test_build_url_pins_the_idd_gini_slice():
    # 9 positions: all countries, annual, INC_DISP_GINI, SO=_Z, unit
    # 0_TO_1, AGE=_T, the vintage door's METHODOLOGY and DEFINITION,
    # POVERTY_LINE=_Z. The explicit version token (the v19 lesson: the
    # endpoint REFUSES "latest" — "Invalid version string provided").
    url = build_url("DF_IDD/INC_DISP_GINI/METH2012/D_CUR")
    assert url.startswith("https://sdmx.oecd.org/public/rest/data/OECD.WISE.INE,DSD_WISE_IDD@DF_IDD,1.0/")
    assert url.endswith("/.A.INC_DISP_GINI._Z.0_TO_1._T.METH2012.D_CUR._Z?dimensionAtObservation=AllDimensions")
    # The back-series door carries its own DEFINITION pin.
    assert ".METH2012.D_PREV._Z" in build_url("DF_IDD/INC_DISP_GINI/METH2012/D_PREV")
    assert ".METH2011.D_CUR._Z" in build_url("DF_IDD/INC_DISP_GINI/METH2011/D_CUR")


def test_build_url_pins_the_safety_road_slice():
    # 8 positions: all countries, annual (the flow also prints monthly
    # and quarterly rows — pinned out), FATALITIES, the per-100k unit,
    # TRANSPORT_MODE=ROAD, the three _Z tail positions.
    url = build_url("DF_SAFETY/FATALITIES/10P5HB")
    assert url.startswith("https://sdmx.oecd.org/public/rest/data/OECD.ITF,DSD_INDICATORS@DF_SAFETY,1.0/")
    assert url.endswith("/.A.FATALITIES.10P5HB.ROAD._Z._Z._Z?dimensionAtObservation=AllDimensions")
    # The registered non-wired doors build their own URLs (the Todd
    # 1974 per-vehicle face among them).
    assert "10P4VEH_MOT_ROAD" in build_url("DF_SAFETY/FATALITIES/10P4VEH_MOT_ROAD")
    assert "10P9VEHKM" in build_url("DF_SAFETY/FATALITIES/10P9VEHKM")


def test_build_url_rejects_malformed_v19_refs():
    for bad in [
        "DF_IDD/INC_DISP_GINI",                 # missing vintage parts
        "DF_IDD/INC_DISP_GINI/METH2012",        # missing DEFINITION
        "DF_IDD/GINI/METH2012/D_CUR",           # unknown measure: no unit declared
        "DF_IDD/INC_DISP_GINI/meth2012/D_CUR",  # lowercase vintage
        "DF_SAFETY/FATALITIES",                 # missing unit
        "DF_SAFETY/FATALITIES/10P5HB/EXTRA",    # too many parts
        "DF_OTHER/THING",
    ]:
        with pytest.raises(ValueError, match="Invalid OECD source_ref|no unit declared"):
            build_url(bad)


def test_parse_idd_gini_cur_carries_the_current_print_anchors():
    records = parse_idd_csv(IDD_CUR, measure="INC_DISP_GINI", methodology="METH2012", definition="D_CUR")
    got = {(r.iso3_raw, r.year): r for r in records}
    # THE CURRENT PRINT, read live at fixture-carve time: France's
    # post-2020 current-definition years (the EU-SILC income concept
    # break — the D_CUR door only carries FRA from 2020), the USA's
    # 2023 survey print, ZAF the world tail.
    assert got[("FRA", 2020)].value == pytest.approx(0.278)
    assert got[("FRA", 2023)].value == pytest.approx(0.29899999499321)
    assert got[("USA", 2023)].value == pytest.approx(0.3944025)
    assert got[("ZAF", 2015)].value == pytest.approx(0.625602135)
    # No sex dimension on the flow: every record sex=None.
    assert all(r.sex is None for r in records)


def test_parse_idd_seam_doors_carry_the_vintage_anchors():
    # THE BACK-SERIES (previous definition, with the overlap year):
    # France 2011-2020 — the years the D_CUR door does not carry.
    prev = parse_idd_csv(IDD_PREVDEF, measure="INC_DISP_GINI", methodology="METH2012", definition="D_PREV")
    got_prev = {(r.iso3_raw, r.year): r for r in prev}
    assert got_prev[("FRA", 2011)].value == pytest.approx(0.309)
    assert got_prev[("FRA", 2019)].value == pytest.approx(0.292)

    # THE WITHOUT-OVERLAP VARIANT: Brazil's back-series rides D_INC.
    inc = parse_idd_csv(IDD_INCDEF, measure="INC_DISP_GINI", methodology="METH2012", definition="D_INC")
    got_inc = {(r.iso3_raw, r.year): r for r in inc}
    assert got_inc[("BRA", 2006)].value == pytest.approx(0.50879539)

    # THE METH2011 HISTORY: France 1996-2011, USA 1993-2012 — the
    # pre-revision computation vintage the chain's fourth door carries.
    m11 = parse_idd_csv(IDD_M2011, measure="INC_DISP_GINI", methodology="METH2011", definition="D_CUR")
    got_m11 = {(r.iso3_raw, r.year): r for r in m11}
    assert got_m11[("FRA", 1996)].value == pytest.approx(0.277)
    assert got_m11[("USA", 1993)].value == pytest.approx(0.369)
    assert got_m11[("USA", 1995)].value == pytest.approx(0.361)  # L'illusion économique's own year
    assert got_m11[("DEU", 1985)].value == pytest.approx(0.251)


def test_parse_idd_refuses_vintage_and_slice_flips():
    # The per-flow pin guard: a response from another vintage, another
    # definition, another unit, or an age slice is refused loudly.
    for measure, methodology, definition, text, needle in [
        ("INC_DISP_GINI", "METH2012", "D_CUR", IDD_CUR.replace(",METH2012,", ",METH2011,", 1), "METHODOLOGY='METH2011'"),
        ("INC_DISP_GINI", "METH2012", "D_CUR", IDD_CUR.replace(",D_CUR,", ",D_PREV,", 1), "DEFINITION='D_PREV'"),
        ("INC_DISP_GINI", "METH2012", "D_CUR", IDD_CUR.replace(",0_TO_1,", ",PT_POP,", 1), "UNIT_MEASURE='PT_POP'"),
        ("INC_DISP_GINI", "METH2012", "D_CUR", IDD_CUR.replace(",_T,METH2012,", ",Y_GT65,METH2012,", 1), "AGE='Y_GT65'"),
        ("INC_DISP_GINI", "METH2012", "D_PREV", IDD_PREVDEF, "DEFINITION='D_PREV' is pinned"),
    ]:
        if needle.endswith("is pinned"):
            # the D_PREV fixture under a D_CUR ref: the DEFINITION pin
            # catches the first data row's vintage.
            with pytest.raises(ValueError, match="DEFINITION='D_PREV'"):
                parse_idd_csv(text, measure=measure, methodology=methodology, definition="D_CUR")
            continue
        with pytest.raises(ValueError, match=re.escape(needle)):
            parse_idd_csv(text, measure=measure, methodology=methodology, definition=definition)


def test_parse_safety_carries_the_road_anchors():
    records = parse_safety_csv(SAFETY, measure="FATALITIES", unit="10P5HB")
    got = {(r.iso3_raw, r.year): r for r in records}
    # THE TODD ARC (Le Fou et le Prolétaire's metric on its modern
    # face): France's sécurité-routière threefold fall, the USA's
    # never-halved divergence, and the post-Soviet crisis at the tail.
    assert got[("FRA", 1994)].value == pytest.approx(15.20273212)
    assert got[("FRA", 2024)].value == pytest.approx(4.657801614)
    assert got[("USA", 1994)].value == pytest.approx(15.47395544)
    assert got[("USA", 2023)].value == pytest.approx(12.1702024)
    assert got[("LVA", 1994)].value == pytest.approx(28.44400577)  # the live tail
    assert got[("DEU", 1994)].value == pytest.approx(12.05083384)
    # RUSSIA IS ABSENT FROM THE ENTIRE ITF FLOW (verified live on the
    # full slice — the honest coverage limit; the GHO witness carries
    # Russia's modeled face).
    assert all(r.iso3_raw != "RUS" for r in records)
    # No sex dimension on the flow.
    assert all(r.sex is None for r in records)


def test_parse_safety_refuses_slice_flips():
    # The per-flow pin guard: monthly rows, the per-vehicle unit, a
    # non-road mode — every other slice the flow carries is refused.
    for text, needle in [
        (SAFETY.replace(",A,FATALITIES,10P5HB,", ",M,FATALITIES,10P5HB,", 1), "FREQ='M'"),
        (SAFETY.replace(",10P5HB,", ",10P4VEH_MOT_ROAD,", 1), "UNIT_MEASURE='10P4VEH_MOT_ROAD'"),
        (SAFETY.replace(",10P5HB,ROAD,", ",10P5HB,RAIL,", 1), "TRANSPORT_MODE='RAIL'"),
        (SAFETY.replace(",FATALITIES,10P5HB,", ",INJURED,10P5HB,", 1), "MEASURE='INJURED'"),
    ]:
        with pytest.raises(ValueError, match=re.escape(needle)):
            parse_safety_csv(text, measure="FATALITIES", unit="10P5HB")


def test_parse_idd_and_safety_share_the_dfcom_body_rules():
    # The shared walker keeps DF_COM's body rules on the new flows: an
    # attribute-only row (no TIME_PERIOD) is skipped, a non-SDMX body
    # and an empty response are refused.
    header = IDD_CUR.splitlines()[0]
    with pytest.raises(ValueError, match="No data rows"):
        parse_idd_csv(header + "\n", measure="INC_DISP_GINI", methodology="METH2012", definition="D_CUR")
    with pytest.raises(ValueError, match="Not an SDMX-CSV data response"):
        parse_safety_csv("Entity,Code,Year,Value\nFrance,FRA,2000,1.0\n", measure="FATALITIES", unit="10P5HB")


# --- v22: the DF_MIG_POPF bilateral matrix (the by-origin witness) -----------

from src.connectors.oecd import parse_migf_csv  # noqa: E402

MIGF = (Path(__file__).parent / "fixtures" / "oecd_migf_sample.csv").read_text(encoding="utf-8")


def test_build_url_pins_the_migf_empty_key_download():
    # THE ACCESS QUIRK (probed live 2026-09-22): the flow refuses
    # positional keys (every dotted key 404s), so the door serves only
    # through the empty-key /all download — no key parts, the frame pins
    # live in the parser.
    assert build_url("DF_MIG_POPF") == (
        "https://sdmx.oecd.org/public/rest/data/"
        "OECD.ELS.IMD,DSD_MIG_F@DF_MIG_POPF,1.0/all?dimensionAtObservation=AllDimensions"
    )


@pytest.mark.parametrize("bad_ref", ["DF_MIG_POPF/", "DF_MIG_POPF/FR", "df_mig_popf"])
def test_migf_ref_is_the_bare_flow(bad_ref):
    with pytest.raises(ValueError, match="Invalid OECD source_ref"):
        build_url(bad_ref)


def test_parse_migf_pins_the_t_frame_and_drops_the_classes_logged(caplog):
    import logging

    with caplog.at_level(logging.INFO):
        records = parse_migf_csv(MIGF)
    # v24: THE BY-SEX DOOR WIRED — the flow's F rows are KEPT (sex="female")
    # instead of dropped: the fixture yields 9,175 both-sexes + 8,779 female
    # records, the residual vocabulary and the diagonals dropped logged per
    # class (the F rows' own residual/diagonal rows dropping with them).
    logged = " ".join(rec.getMessage() for rec in caplog.records)
    assert "kept 8779 female-face record(s)" in logged
    assert "dropped 34 diagonal row(s)" in logged
    assert all(r.sex in (None, "female") for r in records)
    assert sum(1 for r in records if r.sex == "female") == 8779
    assert len(records) == 17954

def test_parse_migf_carries_the_seam_and_the_world_face():
    records = parse_migf_csv(MIGF)
    got = {(r.iso3_raw, r.origin_iso3_raw, r.year): r.value for r in records}
    # THE SEAM, verified to the unit: the OECD questionnaire prints the
    # SAME number the Eurostat c_birth face prints (FR<-MAR 2015 =
    # 954,742 on both doors) — the agreement the root field exists to
    # explain (both doors walk back to the same national registrations).
    assert got[("FRA", "MAR", 2015)] == pytest.approx(954742)
    assert got[("FRA", "MAR", 2018)] == pytest.approx(992120)
    # THE EXTENSION: the OECD face carries the FR Maghreb series PAST the
    # Eurostat 2018 cutoff (the compilation seam displayed, never
    # reconciled).
    assert got[("FRA", "MAR", 2019)] == pytest.approx(1009605)
    assert got[("FRA", "MAR", 2021)] == pytest.approx(1036133)
    # THE WORLD FACE the Eurostat universe structurally cannot print.
    assert got[("USA", "MEX", 2024)] == pytest.approx(12383867.87)


def test_parse_migf_lands_the_overrides_and_the_vanished_origins():
    records = parse_migf_csv(MIGF)
    origins = {r.origin_iso3_raw for r in records}
    # XKV (the OECD's own Kosovo code) -> XKX, the kosovo entity's
    # user-assigned ISO3 (the v21 precedent).
    assert "XKX" in origins
    # THE _F VANISHED-ENTITY PRINTS -> their withdrawn ISO3 codes, the
    # by-origin face of the v21 admission (each lands on its entity).
    for code in ("ANT", "CSK", "SCG", "SUN", "YUG"):
        assert code in origins
    # the raw codes never leak through the override table
    assert not any(r.origin_raw_name == "XKV" and r.origin_iso3_raw == "XKV" for r in records)


def test_parse_migf_refuses_frame_flips():
    # THE FRAME PIN GUARD (loud): a row with MEASURE swapped is a slice we
    # did not ask for — refused, never silently re-interpreted.
    lines = MIGF.splitlines()
    header, first = lines[0], lines[1].split(",")
    assert "MEASURE" in header.split(",")
    idx = header.split(",").index("MEASURE")
    first[idx] = "B15"
    with pytest.raises(ValueError, match="the flow's pinned frame"):
        parse_migf_csv("\n".join([header, ",".join(first)]))
    # an unknown SEX code is a layout change, loudly refused
    first[idx] = "B14"
    sex_idx = header.split(",").index("SEX")
    first[sex_idx] = "M"
    with pytest.raises(ValueError, match="Unexpected SDMX SEX code"):
        parse_migf_csv("\n".join([header, ",".join(first)]))


def test_parse_migf_refuses_non_sdmx_bodies():
    with pytest.raises(ValueError, match="Not an SDMX-CSV DF_MIG_POPF response"):
        parse_migf_csv("Entity,Code,Year,Value\nFrance,FRA,2000,1.0\n")
    with pytest.raises(ValueError, match="No data rows"):
        parse_migf_csv(MIGF.splitlines()[0] + "\n")


# --- v23: the bilateral citizenship matrix (DF_MIG/B15, the keyed wildcard) ---

from src.connectors.oecd import build_url as oecd_build_url  # noqa: E402
from src.connectors.oecd import parse_mig_csv  # noqa: E402

MIG_B15 = (Path(__file__).parent / "fixtures" / "oecd_mig_b15_sample.csv").read_text(encoding="utf-8")


def test_build_url_pins_the_mig_keyed_wildcard_shape():
    # The ACCESS MIRROR of the B14 quirk: DSD_MIG@DF_MIG refuses /all but
    # serves the positional wildcard — REF_AREA and CITIZENSHIP open, the
    # frame pinned at FREQ/MEASURE/BIRTH_PLACE/EDUCATION_LEV/UNIT_MEASURE,
    # SEX open for the parser to split.
    assert oecd_build_url("DF_MIG/B15") == (
        "https://sdmx.oecd.org/public/rest/data/"
        "OECD.ELS.IMD,DSD_MIG@DF_MIG,1.0/..A.B15.._Z._Z.PS"
        "?dimensionAtObservation=AllDimensions"
    )


@pytest.mark.parametrize(
    "bad_ref",
    [
        "DF_MIG",        # the bare flow: this door refuses /all — the keyed grammar only
        "DF_MIG/B14",    # the birth measure lives on DF_MIG_POPF, not here
        "DF_MIG/B16",    # an unwired measure — wire it deliberately, never guess
        "DF_MIG/B15/x",  # trailing segment
    ],
)
def test_mig_ref_is_the_keyed_b15_grammar(bad_ref):
    with pytest.raises(ValueError, match="Invalid OECD source_ref"):
        oecd_build_url(bad_ref)


def test_parse_mig_pins_the_t_frame_and_drops_the_classes_logged(caplog):
    import logging

    with caplog.at_level(logging.INFO):
        records = parse_mig_csv(MIG_B15)
    # v24: THE BY-SEX DOOR WIRED — the V23 pull's F rows un-blocked: the
    # fixture yields 6,115 both-sexes + 5,999 female records (the 8,002 F
    # lines minus the 10 attribute-only rows and the F rows' own residual/
    # diagonal drops), the residual vocabulary and the diagonals dropped
    # logged per class.
    logged = " ".join(rec.getMessage() for rec in caplog.records)
    assert "kept 5999 female-face record(s)" in logged
    # the fixture carries the diagonals of FRA/USA (inside their complete
    # rows) + the four v22 destinations: 59 _T+F diagonal rows drop logged.
    assert "dropped 59 diagonal row(s)" in logged
    # the residual classes, each with the FULL download's own count (the
    # fixture carries every residual row of the keyed download):
    assert "dropped 896 origin row(s) carrying code 'STLS'" in logged
    assert "dropped 1564 origin row(s) carrying code 'W'" in logged
    assert "dropped 784 origin row(s) carrying code 'W_X'" in logged
    assert "dropped 226 origin row(s) carrying code 'EEA'" in logged
    assert "dropped 392 origin row(s) carrying code 'EU15'" in logged
    assert "dropped 224 origin row(s) carrying code 'A4'" in logged
    # every kept record carries the routing key of the citizenship face,
    # and the female face rides the SAME routing (sex="female" beside
    # sex=None on the same series).
    assert all(r.origin_axis == "citizenship" for r in records)
    assert all(r.origin_raw_name and r.origin_iso3_raw for r in records)
    assert all(r.sex in (None, "female") for r in records)
    assert len(records) == 12114

def test_parse_mig_carries_the_seam_and_the_contrast_anchors():
    records = parse_mig_csv(MIG_B15)
    got = {(r.iso3_raw, r.origin_iso3_raw, r.year): r.value for r in records}
    # THE SEAM, verified to the unit: the questionnaire prints the SAME
    # number the Eurostat ctz door prints — FR<-MAR _T 2015 = 458,561
    # (and the 2016-2018 series beside it, both doors exact).
    assert got[("FRA", "MAR", 2015)] == pytest.approx(458561)
    assert got[("FRA", "MAR", 2016)] == pytest.approx(465230)
    assert got[("FRA", "MAR", 2017)] == pytest.approx(472843)
    assert got[("FRA", "MAR", 2018)] == pytest.approx(480600)
    # THE WORLD FACE the Eurostat universe cannot print, on the pair the
    # naturalization gap widens: US<-MEX 2024 = 8,226,106 citizens vs
    # 12,383,868 born (the B14 witness's own print, the divergence the
    # two faces exist to display).
    assert got[("USA", "MEX", 2024)] == pytest.approx(8226106.247)
    # THE CONTRAST (§5.4): FR<-PRT citizens = 541,867 at 2015, the
    # CONVERGE face of the pair.
    assert got[("FRA", "PRT", 2015)] == pytest.approx(541867)


def test_parse_mig_lands_the_vanished_origins_on_their_entities():
    # The vanished-entity codes ride the SHARED override table (the same
    # admission as the birth face): XKV -> XKX Kosovo, the _F prints ->
    # their withdrawn ISO3 entities — people still holding the former
    # nationality, counted exactly as the questionnaire prints them.
    records = parse_mig_csv(MIG_B15)
    origins = {r.origin_iso3_raw for r in records}
    for iso3 in ("XKX", "ANT", "CSK", "SCG", "SUN", "YUG"):
        assert iso3 in origins, iso3
    # the residual vocabulary never enters the layer (STLS is a drop, not
    # a mapping — a nationality without a state has no entity to carry it).
    assert "STLS" not in origins
    assert "W" not in origins


def test_mig_frame_pin_guards_refuse_slices_we_did_not_ask_for():
    # trust the URL, verify the response: a row from another measure
    # (B14) under the B15 door is refused loudly, never ingested.
    lines = MIG_B15.splitlines()
    header, first = lines[0], lines[1].split(",")
    swapped = first[:]
    for i, col in enumerate(header.split(",")):
        if col == "MEASURE":
            swapped[i] = "B14"
    doctored = "\n".join([header, ",".join(swapped)] + lines[2:])
    with pytest.raises(ValueError, match="MEASURE='B14'.*pinned frame is 'B15'"):
        parse_mig_csv(doctored)
    # the UNIT_MEASURE pin: swapped — refused.
    swapped2 = first[:]
    for i, col in enumerate(header.split(",")):
        if col == "UNIT_MEASURE":
            swapped2[i] = "PS_"
    doctored2 = "\n".join([header, ",".join(swapped2)] + lines[2:])
    with pytest.raises(ValueError, match="UNIT_MEASURE='PS_'.*pinned frame is 'PS'"):
        parse_mig_csv(doctored2)


def test_mig_sex_guard_refuses_unknown_codes():
    # the download structurally carries _T AND F; a third code is a
    # layout change, loudly refused.
    lines = MIG_B15.splitlines()
    header, first = lines[0], lines[1].split(",")
    doctored_row = first[:]
    for i, col in enumerate(header.split(",")):
        if col == "SEX":
            doctored_row[i] = "M"
    doctored = "\n".join([header, ",".join(doctored_row)] + lines[2:])
    with pytest.raises(ValueError, match="Unexpected SDMX SEX code 'M'"):
        parse_mig_csv(doctored)

