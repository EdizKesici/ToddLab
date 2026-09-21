"""Eurostat demo_find connector tests — the v14 collector provider.

The fixtures mirror real response slices (see fixtures/README.md): the
main miniature carries the geo codelist's own quirks (EL/UK/FX codes,
the EU27_2020 aggregate, the DE_TOT identical duplicate, XK's no-ISO3
path) and the FX/FR miniatures the geo-pinned single-series shape with
the seam's own status flags. Anchor values are the live-probed numbers;
fills are synthetic.
"""
import json
from pathlib import Path

import pytest

from src.connectors.eurostat import (
    EUROSTAT_GEO_TO_ISO3,
    EurostatConnector,
    build_url,
    parse_eurostat,
)
from src.pipeline.fetch import CONNECTORS
from src.schema.indicator import Provider

FIXTURES = Path(__file__).parent / "fixtures"
MAIN = (FIXTURES / "eurostat_totferrt_sample.json").read_text(encoding="utf-8")
FX = (FIXTURES / "eurostat_totferrt_fx_sample.json").read_text(encoding="utf-8")
FR = (FIXTURES / "eurostat_totferrt_fr_sample.json").read_text(encoding="utf-8")
REF = "demo_find/TOTFERRT"


def test_connector_is_registered():
    # v14 wires the eurostat Provider — the collector the corpus's #1
    # metric needed (no other collector wire prints a national TFR).
    assert isinstance(CONNECTORS[Provider.eurostat], EurostatConnector)


def test_build_url_pins_the_query_shape():
    assert build_url(REF) == (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_find"
        "?format=JSON&lang=EN&indic_de=TOTFERRT"
    )
    assert build_url("demo_find/TOTFERRT/FX") == (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_find"
        "?format=JSON&lang=EN&indic_de=TOTFERRT&geo=FX"
    )


@pytest.mark.parametrize(
    "bad_ref",
    ["demo_gind/TOTFERRT", "TOTFERRT", "demo_find", "demo_find/TOTFERRT/FR/extra", "oecd/DF_COM"],
)
def test_ref_format_is_the_one_dataset_this_connector_speaks(bad_ref):
    # One dataset, one dispatch decision (the DYB-table scope): another
    # dataset or a malformed ref raises BEFORE any request is built.
    with pytest.raises(ValueError, match="Invalid Eurostat source_ref"):
        build_url(bad_ref)


def test_parse_main_slice_keeps_countries_and_drops_the_codelist_variants(caplog):
    import logging

    with caplog.at_level(logging.INFO, logger="src.connectors.eurostat"):
        records = parse_eurostat(MAIN, expected_ref=REF)
    got = {(r.iso3_raw, r.year): r for r in records}

    # The kept countries: DE, EL (Greece via the override), IE, RU, UK
    # (via the override), XK (kept WITH iso3 None — the unresolved path).
    iso3s = {r.iso3_raw for r in records}
    assert iso3s == {"DEU", "GRC", "GBR", "IRL", "RUS", None}
    # EL/UK/FX ride the explicit override table (pycountry answers none
    # of them, verified live); XK deliberately does not. v16 adds DE_TOT
    # (the German series door — pinned, not duplicated, on NMARPCT).
    assert EUROSTAT_GEO_TO_ISO3 == {"EL": "GRC", "UK": "GBR", "FX": "FRA", "DE_TOT": "DEU"}

    assert got[("DEU", 2023)].value == pytest.approx(1.39)
    assert got[("GRC", 1994)].value == pytest.approx(1.33)
    assert got[("GBR", 2012)].value == pytest.approx(1.92)
    assert got[("IRL", 1960)].value == pytest.approx(3.78)
    assert got[("RUS", 2008)].value == pytest.approx(1.49)

    # Kosovo: the provider prints it (XK, label "Kosovo*"), it resolves
    # to no ISO3 and flows to normalize's unresolved report — the SAME
    # pending product decision as the World Bank's Kosovo.
    xk = [r for r in records if r.iso3_raw is None]
    assert len(xk) == 1
    assert (xk[0].entity_raw_name, xk[0].year, xk[0].value) == ("Kosovo*", 2017, pytest.approx(1.65))

    # The drops are LOGGED (the v11.1 discipline: the log line is the
    # record of the drop): the EU27_2020 aggregate, the DE_TOT identical
    # duplicate, and the France variant pair's rows (FX 1960/1994 +
    # FR 2014/2023 — each series rides its own geo-pinned source_ref).
    logs = "\n".join(r.message for r in caplog.records)
    assert "dropped 1 aggregate row" in logs
    assert "dropped 1 DE_TOT row" in logs
    assert "dropped 4 France variant row" in logs

    # Every record: no sex (TFR is a synthetic measure over women's
    # lifetimes), values as floats, the printed names ride along.
    assert all(r.sex is None for r in records)
    assert all(isinstance(r.value, float) for r in records)
    assert got[("DEU", 2023)].entity_raw_name == "Germany"


def test_parse_transports_the_collectors_own_status_flags():
    records = parse_eurostat(MAIN, expected_ref=REF)
    de = [r for r in records if r.iso3_raw == "DEU" and r.year == 2023][0]
    # DE 2023 carries 'b' (break in series) as-printed: quality_code
    # transports the flag verbatim, and 'p'-less means not provisional.
    assert de.quality_code == "b"
    assert de.provisional is False


def test_parse_geo_pinned_series_fx_and_fr():
    fx = parse_eurostat(FX, expected_ref="demo_find/TOTFERRT/FX")
    assert [(r.year, r.value) for r in fx] == [
        (1960, pytest.approx(2.73)),
        (1994, pytest.approx(1.66)),
        (2000, pytest.approx(1.87)),
        (2012, pytest.approx(1.99)),
    ]
    # The series-variant code resolves to France — the metropolitan
    # series the seam's pre-1998 canon is built from.
    assert all(r.iso3_raw == "FRA" for r in fx)
    assert all(r.entity_raw_name == "Metropolitan France" for r in fx)

    fr = parse_eurostat(FR, expected_ref="demo_find/TOTFERRT/FR")
    got = {r.year: r for r in fr}
    assert got[1998].value == pytest.approx(1.78)
    assert got[2012].value == pytest.approx(2.01)
    # FR 2014 carries the French series' own methodological break flag,
    # FR 2023 is provisional — the collector's per-observation letters.
    assert (got[2014].quality_code, got[2014].provisional) == ("b", False)
    assert (got[2023].quality_code, got[2023].provisional) == ("p", True)
    assert all(r.entity_raw_name == "France" for r in fr)


def test_pin_guards_refuse_slices_we_did_not_ask_for():
    payload = json.loads(MAIN)

    # A different dimension layout (a different dataset) is a loud
    # failure, never a silent misparse.
    payload["id"] = ["freq", "indic_de", "geo", "age", "time"]
    with pytest.raises(ValueError, match="not the demo_find layout"):
        parse_eurostat(json.dumps(payload), expected_ref=REF)

    # The requested code must BE the response's indic_de.
    payload = json.loads(MAIN)
    payload["dimension"]["indic_de"]["category"]["index"] = {"TOTFERRA": 0}
    with pytest.raises(ValueError, match="refusing to ingest a slice we did not ask for"):
        parse_eurostat(json.dumps(payload), expected_ref=REF)

    # freq must be exactly annual.
    payload = json.loads(MAIN)
    payload["dimension"]["freq"]["category"]["index"] = {"A": 0, "Q": 1}
    payload["size"][0] = 2
    with pytest.raises(ValueError, match="not exactly annual"):
        parse_eurostat(json.dumps(payload), expected_ref=REF)

    # A geo-pinned request must receive exactly its own geo — the FX
    # miniature asked for FX; the main slice (10 geo) must be refused.
    with pytest.raises(ValueError, match="refusing a slice carrying more"):
        parse_eurostat(MAIN, expected_ref="demo_find/TOTFERRT/FX")

    # A non-annual time entry raises.
    payload = json.loads(MAIN)
    payload["dimension"]["time"]["category"]["index"] = {"1960-1961": 0}
    with pytest.raises(ValueError, match="not a 4-digit year"):
        parse_eurostat(json.dumps(payload), expected_ref=REF)


def test_zero_country_rows_is_an_unexpected_shape():
    payload = json.loads(MAIN)
    payload["value"] = {}  # every cell absent
    with pytest.raises(ValueError, match="zero country rows"):
        parse_eurostat(json.dumps(payload), expected_ref=REF)


def test_a_field_param_is_refused_the_ref_carries_the_geo_pin():
    connector = EurostatConnector()
    with pytest.raises(ValueError, match="carries a 'field'"):
        connector.fetch_raw("demo_find/TOTFERRT", "birth_rate_fertility", field="rate")


# --- v16: NMARPCT — the second Todd metric this dataset carries -------
# ("Proportion of live births outside marriage": the collector prints
# the share DIRECTLY, no derivation — and the German variant pair
# REVERSES: DE_TOT is the fuller series, DE carries the FRG-only
# pre-reunification benchmarks, both ride geo-pinned sources.)

NMAIN = (FIXTURES / "eurostat_nmarpct_sample.json").read_text(encoding="utf-8")
NDE_TOT = (FIXTURES / "eurostat_nmarpct_de_tot_sample.json").read_text(encoding="utf-8")
NFR = (FIXTURES / "eurostat_nmarpct_fr_sample.json").read_text(encoding="utf-8")
NFX = (FIXTURES / "eurostat_nmarpct_fx_sample.json").read_text(encoding="utf-8")


def test_build_url_pins_the_nmarpct_query_shape():
    assert build_url("demo_find/NMARPCT") == (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
        "/demo_find?format=JSON&lang=EN&indic_de=NMARPCT"
    )
    assert build_url("demo_find/NMARPCT/DE_TOT") == (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
        "/demo_find?format=JSON&lang=EN&indic_de=NMARPCT&geo=DE_TOT"
    )


def test_parse_nmarpct_main_slice_drops_variants_with_the_code_aware_log(caplog):
    import logging

    with caplog.at_level(logging.INFO, logger="src.connectors.eurostat"):
        records = parse_eurostat(NMAIN, expected_ref="demo_find/NMARPCT")
    got = {(r.iso3_raw, r.year): r for r in records}

    # The kept countries: DE, EL, MD, TR, UK, XK (unresolved) — the
    # aggregate, DE_TOT and the France variant pair are dropped.
    iso3s = {r.iso3_raw for r in records}
    assert iso3s == {"DEU", "GRC", "MDA", "TUR", "GBR", None}

    # The live anchors: the FRG-only German benchmarks (the seam's
    # discarded side), the collector's questionnaire tail.
    assert got[("DEU", 1960)].value == pytest.approx(6.3)
    assert got[("DEU", 1980)].value == pytest.approx(7.6)  # the FRG print DE_TOT's 11.9 beats
    assert got[("TUR", 2024)].value == pytest.approx(3.4)
    assert got[("GBR", 1960)].value == pytest.approx(5.2)
    # Kosovo 2002/2012 print but resolve to no ISO3 (the pending class).
    xk = [r for r in records if r.iso3_raw is None]
    assert [(r.entity_raw_name, r.year, r.value) for r in xk] == [
        ("Kosovo*", 2002, pytest.approx(6.8)),
        ("Kosovo*", 2012, pytest.approx(46.1)),
    ]

    # THE CODE-AWARE DROP LOG: on NMARPCT the DE_TOT drop's message says
    # the series door rides its own geo-pinned source_ref (NOT the TFR's
    # "identical duplicate" claim — the two codes' relationships with
    # DE are verified OPPOSITE facts, and the log line is the record).
    # The France-variant drop cites THIS code's own pinned refs (the
    # fixture's counts: 6 EU27_2020 aggregate cells, 9 DE_TOT cells,
    # 13 FR/FX cells — FX prints every grid year through 2012 incl.
    # 1980, FR every grid year from 1998).
    logs = "\n".join(r.message for r in caplog.records)
    assert "dropped 6 aggregate row" in logs
    assert "rides its own geo-pinned source_ref, demo_find/NMARPCT/DE_TOT" in logs
    assert "dropped 9 DE_TOT row" in logs
    assert "demo_find/NMARPCT/FX and demo_find/NMARPCT/FR" in logs
    assert "dropped 13 France variant row" in logs
    assert "TOTFERRT" not in logs  # the code-aware messages never cite the other code's refs


def test_parse_nmarpct_flags_ride_as_reported():
    records = parse_eurostat(NMAIN, expected_ref="demo_find/NMARPCT")
    by = {(r.iso3_raw, r.year): r for r in records}
    # EL 2023 'b' (the Greek series' break) and MD 2022 'p' (provisional)
    # — the live slice's only four flagged cells, two of them on
    # countries (the EU27_2020 'i' flags ride the dropped aggregate).
    assert (by[("GRC", 2023)].quality_code, by[("GRC", 2023)].value) == ("b", pytest.approx(9.7))
    assert by[("GRC", 2023)].provisional is False
    assert (by[("MDA", 2022)].quality_code, by[("MDA", 2022)].provisional) == ("p", True)
    assert by[("MDA", 2022)].value == pytest.approx(18.3)


def test_parse_nmarpct_de_tot_pin_is_the_german_series_door():
    records = parse_eurostat(NDE_TOT, expected_ref="demo_find/NMARPCT/DE_TOT")
    got = {r.year: r for r in records}
    # The all-Germany series, live-anchored: the five pre-reunification
    # benchmark years (the GDR's high non-marital share) + the modern
    # prints. The override table resolves DE_TOT -> Germany.
    assert got[1960].value == pytest.approx(7.6)
    assert got[1970].value == pytest.approx(7.2)
    assert got[1980].value == pytest.approx(11.9)
    assert got[1985].value == pytest.approx(16.2)
    assert got[1990].value == pytest.approx(15.3)
    assert got[2024].value == pytest.approx(32.4)
    assert all(r.iso3_raw == "DEU" for r in records)
    assert all(r.entity_raw_name == "Germany including former GDR" for r in records)
    assert all(r.sex is None for r in records)  # a population-level share

    # The pin guard: a DE_TOT-pinned request must receive exactly DE_TOT.
    with pytest.raises(ValueError, match="refusing a slice carrying more"):
        parse_eurostat(NMAIN, expected_ref="demo_find/NMARPCT/DE_TOT")


def test_parse_nmarpct_fr_fx_pins_carry_the_seam():
    fx = parse_eurostat(NFX, expected_ref="demo_find/NMARPCT/FX")
    assert {r.year: r.value for r in fx} == {
        1960: pytest.approx(6.1), 1998: pytest.approx(40.7),
        2000: pytest.approx(42.6), 2012: pytest.approx(55.8),
    }
    assert all(r.iso3_raw == "FRA" and r.entity_raw_name == "Metropolitan France" for r in fx)

    fr = parse_eurostat(NFR, expected_ref="demo_find/NMARPCT/FR")
    got = {r.year: r.value for r in fr}
    assert got == {
        1998: pytest.approx(41.7), 2000: pytest.approx(43.6),
        2012: pytest.approx(56.7), 2020: pytest.approx(62.2), 2024: pytest.approx(59.7),
    }
    assert all(r.iso3_raw == "FRA" and r.entity_raw_name == "France" for r in fr)
    # No status flags on either French pin (the live NMARPCT slice's
    # four flagged cells ride the main slice's other countries).
    assert all(r.quality_code is None for r in fx + fr)


# --- v17: une_rt_a (the labour-force questionnaire's second dispatch) ------

UNERT = (FIXTURES / "eurostat_unert_sample.json").read_text(encoding="utf-8")
UNERT_REF = "une_rt_a/Y15-74/PC_ACT/T"


def test_build_url_pins_the_unert_query_shape():
    # The three pins ride the query (the dataset's own selector grammar:
    # age band, unit denominator, sex) — never a field param.
    assert build_url(UNERT_REF) == (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
        "/une_rt_a?format=JSON&lang=EN&age=Y15-74&unit=PC_ACT&sex=T"
    )
    # The unwired sex doors ride the same grammar one pin away.
    assert build_url("une_rt_a/Y15-74/PC_ACT/M").endswith("age=Y15-74&unit=PC_ACT&sex=M")


@pytest.mark.parametrize(
    "bad_ref",
    [
        "une_rt_a",                    # no pins at all
        "une_rt_a/Y15-74",             # one pin short
        "une_rt_a/Y15-74/PC_ACT",      # two pins short
        "une_rt_a/TOTAL/PC_ACT/T",     # the codelist carries NO TOTAL (soft-miss code)
        "une_rt_a/Y15-74/PC_ACT/Q",    # not a sex code
        "une_rt_a/PC_ACT/T",           # the unit slot does not fit the age pattern
        "demo_find/Y15-74/PC_ACT/T",   # the demo grammar does not fit this dataset
        "une_rt_a/TOTFERRT",           # the demo code does not fit this grammar
        "health_ds/anything",          # unknown dataset: one dispatch decision per dataset
    ],
)
def test_unert_ref_format_is_the_one_grammar_this_dataset_speaks(bad_ref):
    with pytest.raises(ValueError, match="Invalid Eurostat source_ref"):
        build_url(bad_ref)


def test_parse_unert_main_slice_keeps_countries_and_drops_aggregates(caplog):
    import logging

    with caplog.at_level(logging.INFO, logger="src.connectors.eurostat"):
        records = parse_eurostat(UNERT, expected_ref=UNERT_REF)
    got = {(r.iso3_raw, r.year): r for r in records}

    # THE LIVE ANCHORS (the fixture was generated from the live cube):
    # France the only full-length series (2003, the door's own start),
    # the LFS-2021 'd' definitional seam riding quality_code from 2023.
    assert got[("FRA", 2003)].value == pytest.approx(8.5)
    assert got[("FRA", 2015)].value == pytest.approx(10.4)
    assert got[("FRA", 2023)].value == pytest.approx(7.4)
    assert got[("FRA", 2023)].quality_code == "d"
    assert got[("FRA", 2024)].quality_code == "d"
    assert got[("FRA", 2024)].provisional is False  # 'd' is definitional, not provisional
    # THE COVERAGE CLIFF: Germany starts 2009 (DE 2005 lives only on the
    # witness); the crisis peaks print as published.
    assert ("DEU", 2005) not in got
    assert got[("DEU", 2009)].value == pytest.approx(7.3)
    assert got[("DEU", 2023)].value == pytest.approx(3.1)
    assert got[("ESP", 2013)].value == pytest.approx(26.1)
    assert got[("GRC", 2013)].value == pytest.approx(27.8)  # EL -> GRC, the override
    # Montenegro's short series stops 2020 (absence is information).
    assert got[("MNE", 2020)].value == pytest.approx(17.9)
    assert ("MNE", 2021) not in got
    # The aggregate drops with the log line as the record.
    assert all(r.iso3_raw != "EU27" for r in records)
    logs = "\n".join(r.message for r in caplog.records)
    assert "dropped 8 aggregate row(s)" in logs
    # sex=T is the both-sexes rate: the merge key's None (the M/F doors,
    # when ever wired, coexist without colliding).
    assert all(r.sex is None for r in records)


def test_unert_pin_guards_refuse_slices_we_did_not_ask_for():
    # A une_rt_a payload handed to a demo_find ref: wrong layout, loud
    # failure (never a silent misparse across datasets).
    with pytest.raises(ValueError, match="not the demo_find layout"):
        parse_eurostat(UNERT, expected_ref="demo_find/TOTFERRT")
    # A demo_find payload handed to a une_rt_a ref: mirror refusal.
    with pytest.raises(ValueError, match="not the une_rt_a layout"):
        parse_eurostat(MAIN, expected_ref=UNERT_REF)
    # A pinned sex the payload does not carry: refused.
    with pytest.raises(ValueError, match="does not match the requested"):
        parse_eurostat(UNERT, expected_ref="une_rt_a/Y15-74/PC_ACT/M")


def test_unert_soft_miss_is_a_loud_failure():
    # The provider's soft-miss pattern: unknown geo codes answer HTTP
    # 200 with an empty value object — a pinned ref for a code the
    # codelist does not carry (FX here, probed live) must fail loudly,
    # never parse as success. The fixture's grid with every value
    # stripped simulates exactly that response shape.
    payload = json.loads(UNERT)
    payload["value"] = {}
    with pytest.raises(ValueError, match="zero country rows"):
        parse_eurostat(json.dumps(payload), expected_ref=UNERT_REF)
