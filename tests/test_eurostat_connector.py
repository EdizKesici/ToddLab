"""Eurostat demo_find connector tests — the v14 collector provider.

The fixtures mirror real response slices (see fixtures/README.md): the
main miniature carries the geo codelist's own quirks (EL/UK/FX codes,
the EU27_2020 aggregate, the DE_TOT identical duplicate, XK's no-ISO3
path) and the FX/FR miniatures the geo-pinned single-series shape with
the seam's own status flags. Anchor values are the live-probed numbers;
fills are synthetic.
"""
import json
import logging
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
    # (via the override), XK (v21: Kosovo -> XKX, the user-assigned code
    # the kosovo entity now carries — the resolved path).
    iso3s = {r.iso3_raw for r in records}
    assert iso3s == {"DEU", "GRC", "GBR", "IRL", "RUS", "XKX"}
    # EL/UK/FX/XK ride the explicit override table (pycountry answers none
    # of them, verified live). v16 adds DE_TOT (the German series door —
    # pinned, not duplicated, on NMARPCT); v21 adds XK (Kosovo).
    assert EUROSTAT_GEO_TO_ISO3 == {"EL": "GRC", "UK": "GBR", "FX": "FRA", "DE_TOT": "DEU", "XK": "XKX"}

    assert got[("DEU", 2023)].value == pytest.approx(1.39)
    assert got[("GRC", 1994)].value == pytest.approx(1.33)
    assert got[("GBR", 2012)].value == pytest.approx(1.92)
    assert got[("IRL", 1960)].value == pytest.approx(3.78)
    assert got[("RUS", 2008)].value == pytest.approx(1.49)

    # Kosovo: the provider prints it (XK, label "Kosovo*"); v21 resolves
    # it to XKX — the pending product decision closed on the entity.
    xk = [r for r in records if r.iso3_raw == "XKX"]
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

    # The kept countries: DE, EL, MD, TR, UK, XK (v21: resolved to XKX) —
    # the aggregate, DE_TOT and the France variant pair are dropped.
    iso3s = {r.iso3_raw for r in records}
    assert iso3s == {"DEU", "GRC", "MDA", "TUR", "GBR", "XKX"}

    # The live anchors: the FRG-only German benchmarks (the seam's
    # discarded side), the collector's questionnaire tail.
    assert got[("DEU", 1960)].value == pytest.approx(6.3)
    assert got[("DEU", 1980)].value == pytest.approx(7.6)  # the FRG print DE_TOT's 11.9 beats
    assert got[("TUR", 2024)].value == pytest.approx(3.4)
    assert got[("GBR", 1960)].value == pytest.approx(5.2)
    # Kosovo 2002/2012 print and resolve to XKX (v21 — the 2002 row will
    # drop on the entity's valid_from=2008 at normalize, the honest shape).
    xk = [r for r in records if r.iso3_raw == "XKX"]
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


# ---------------------------------------------------------------------------
# v18 — the three new dispatch decisions: nama_10_a10_e (the national-
# accounts share door), edat_lfse_03 (the LFS attainment table),
# migr_pop3ctb (the foreign-born stock door).

NAMA_BE = (FIXTURES / "eurostat_nama_be_sample.json").read_text(encoding="utf-8")
NAMA_A = (FIXTURES / "eurostat_nama_a_sample.json").read_text(encoding="utf-8")
EDAT_58 = (FIXTURES / "eurostat_edat_ed58_sample.json").read_text(encoding="utf-8")
EDAT_34 = (FIXTURES / "eurostat_edat_ed34_sample.json").read_text(encoding="utf-8")
MIGR_FOR = (FIXTURES / "eurostat_migr_for_sample.json").read_text(encoding="utf-8")
NAMA_BE_REF = "nama_10_a10_e/EMP_DC/PC_TOT_PER/B-E"
NAMA_A_REF = "nama_10_a10_e/EMP_DC/PC_TOT_PER/A"
EDAT_58_REF = "edat_lfse_03/ED5-8/Y25-64/T"
EDAT_34_REF = "edat_lfse_03/ED3_4/Y25-64/T"
MIGR_FOR_REF = "migr_pop3ctb/FOR/TOTAL/T"


def test_build_url_pins_the_v18_query_shapes():
    # nama: the three pins (na_item, unit, nace_r2) ride the query — the
    # share's own selector grammar; the nace aggregate with its hyphen.
    assert build_url(NAMA_BE_REF) == (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
        "/nama_10_a10_e?format=JSON&lang=EN&na_item=EMP_DC&unit=PC_TOT_PER&nace_r2=B-E"
    )
    assert build_url(NAMA_A_REF).endswith("na_item=EMP_DC&unit=PC_TOT_PER&nace_r2=A")
    # edat: the ISCED pin (hyphen and underscore shapes both grammar-true)
    # + the implicit unit=PC pin (the dataset's only unit, guarded).
    assert build_url(EDAT_58_REF) == (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
        "/edat_lfse_03?format=JSON&lang=EN&isced11=ED5-8&age=Y25-64&sex=T&unit=PC"
    )
    assert build_url(EDAT_34_REF).endswith("isced11=ED3_4&age=Y25-64&sex=T&unit=PC")
    # migr: c_birth/age/sex + unit=NR pinned.
    assert build_url(MIGR_FOR_REF) == (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
        "/migr_pop3ctb?format=JSON&lang=EN&c_birth=FOR&age=TOTAL&sex=T&unit=NR"
    )
    # the unwired doors ride the same grammars one pin away.
    assert build_url("nama_10_a10_e/EMP_DC/PC_TOT_PER/F").endswith("nace_r2=F")
    assert "sex=M" in build_url("edat_lfse_03/ED5-8/Y25-64/M")
    assert "c_birth=NAT" in build_url("migr_pop3ctb/NAT/TOTAL/T")


@pytest.mark.parametrize(
    "bad_ref",
    [
        "nama_10_a10_e/B-E",              # missing na_item/unit
        "nama_10_a10_e/EMP_DC/PC_TOT_PER",  # missing nace
        "edat_lfse_03/ED5-8",             # missing age/sex
        "edat_lfse_03/ED5-8/Y25-64",      # one pin short
        "migr_pop3ctb/FOR",               # missing age/sex
        "migr_pop3ctb/FOR/TOTAL",         # one pin short
        "unknown_ds/anything",            # one dispatch decision per dataset
    ],
)
def test_v18_ref_formats_are_the_one_grammar_each_dataset_speaks(bad_ref):
    with pytest.raises(ValueError, match="Invalid Eurostat source_ref"):
        build_url(bad_ref)


def test_parse_nama_be_keeps_countries_drops_the_two_letter_aggregate(caplog):
    import logging

    with caplog.at_level(logging.INFO, logger="src.connectors.eurostat"):
        records = parse_eurostat(NAMA_BE, expected_ref=NAMA_BE_REF)
    got = {(r.iso3_raw, r.year): r for r in records}

    # THE LIVE ANCHORS (the fixture was generated from the live cube,
    # 2026-09-21): the de-industrialization slopes as the collector
    # prints them — FR 1995 = 16.4 -> 2024 = 10.1, DE 23.1 -> 17.5.
    assert got[("FRA", 1995)].value == pytest.approx(16.4)
    assert got[("FRA", 2024)].value == pytest.approx(10.1)
    assert got[("DEU", 1995)].value == pytest.approx(23.1)
    assert got[("DEU", 2024)].value == pytest.approx(17.5)
    # the 'p' flags ride as-reported (the accounts' own provisional
    # markers on the freshest years).
    assert got[("FRA", 2024)].quality_code == "p"
    assert got[("FRA", 2024)].provisional is True
    # THE EA EDGE: the Euro-area aggregate prints as the bare two-letter
    # code "EA" — dropped logged as the aggregate it is (the only
    # two-letter aggregate in any wired codelist, verified live).
    assert all(r.iso3_raw != "EA" for r in records)
    logs = "\n".join(r.message for r in caplog.records)
    assert "dropped" in logs and "aggregate" in logs
    # no sex dimension in this cube: both-sexes by construction.
    assert all(r.sex is None for r in records)
    # Kosovo rides the codelist (XK) but prints NO valued cells in the
    # employment cube — its absence is the collector's own answer (the
    # unresolved-name path is exercised by the demo_find fixtures).


def test_parse_nama_a_reads_the_same_door_one_nace_pin_away():
    records = parse_eurostat(NAMA_A, expected_ref=NAMA_A_REF)
    got = {(r.iso3_raw, r.year): r.value for r in records}
    # the agrarian-exodus baseline as printed: FR 1995 = 4.4 -> 2.3.
    assert got[("FRA", 1995)] == pytest.approx(4.4)
    assert got[("FRA", 2024)] == pytest.approx(2.3)
    assert got[("DEU", 2024)] == pytest.approx(1.2)


def test_parse_edat_anchors_and_flags():
    records = parse_eurostat(EDAT_58, expected_ref=EDAT_58_REF)
    got = {(r.iso3_raw, r.year): r for r in records}
    # THE LIVE ANCHORS: the tertiary-attainment climb as the LFS prints
    # it — FR 2004 = 24.5 -> 2024 = 43.2; the 'b' break flags ride
    # quality_code (the survey redesigns).
    assert got[("FRA", 2004)].value == pytest.approx(24.5)
    assert got[("FRA", 2024)].value == pytest.approx(43.2)
    assert got[("FRA", 2024)].quality_code == "b"
    assert got[("FRA", 2024)].provisional is False  # 'b' is a break, not 'p'
    # sex=T: the merge key's None.
    assert all(r.sex is None for r in records)


def test_parse_edat_ed34_is_the_completed_secondary_face():
    records = parse_eurostat(EDAT_34, expected_ref=EDAT_34_REF)
    got = {(r.iso3_raw, r.year): r.value for r in records}
    # the ISCED choice pinned by its own anchors: ED3_4 (highest
    # attainment = secondary, tertiary EXCLUDED) reads in the 40s-50s —
    # the at-least-secondary face (ED3-8) would run ~20 points higher,
    # a misload this pin would catch.
    assert got[("FRA", 2004)] == pytest.approx(41.4)
    assert got[("DEU", 1996)] == pytest.approx(56.7)


def test_parse_migr_for_reads_the_stock_door():
    records = parse_eurostat(MIGR_FOR, expected_ref=MIGR_FOR_REF)
    got = {(r.iso3_raw, r.year): r for r in records}
    # THE LIVE ANCHORS: FR's foreign-born stock, annual and
    # census-aligned as the registration prints it — 2008 = 7,076,824
    # -> 2024 = 9,362,105; the 'b'/'e'/'p' flags ride as-reported.
    assert got[("FRA", 2008)].value == pytest.approx(7076824)
    assert got[("FRA", 2024)].value == pytest.approx(9362105)
    assert got[("FRA", 2024)].quality_code == "p"
    # Germany's own stock (the 2011 census break flag era).
    assert got[("DEU", 2010)].value == pytest.approx(9812263)
    # sex=T: the merge key's None.
    assert all(r.sex is None for r in records)


def test_v18_pin_guards_refuse_slices_we_did_not_ask_for():
    # Cross-dataset payloads: wrong layouts, loud failures.
    with pytest.raises(ValueError, match="not the nama_10_a10_e layout"):
        parse_eurostat(UNERT, expected_ref=NAMA_BE_REF)
    with pytest.raises(ValueError, match="not the edat_lfse_03 layout"):
        parse_eurostat(NAMA_BE, expected_ref=EDAT_58_REF)
    with pytest.raises(ValueError, match="not the migr_pop3ctb layout"):
        parse_eurostat(EDAT_58, expected_ref=MIGR_FOR_REF)
    # The nace pin the payload does not carry: refused.
    with pytest.raises(ValueError, match="does not match the requested"):
        parse_eurostat(NAMA_BE, expected_ref="nama_10_a10_e/EMP_DC/PC_TOT_PER/A")
    # The ISCED pin swapped: refused (ED3_4 payload under an ED5-8 ref).
    with pytest.raises(ValueError, match="does not match the requested"):
        parse_eurostat(EDAT_34, expected_ref=EDAT_58_REF)
    # The c_birth pin swapped: refused.
    with pytest.raises(ValueError, match="does not match the requested"):
        parse_eurostat(MIGR_FOR, expected_ref="migr_pop3ctb/NAT/TOTAL/T")


def test_v18_soft_miss_is_a_loud_failure():
    # The same soft-miss pattern on every new dataset: an empty value
    # object answers HTTP 200 — the parse must fail loudly.
    for text, ref in ((NAMA_BE, NAMA_BE_REF), (EDAT_58, EDAT_58_REF), (MIGR_FOR, MIGR_FOR_REF)):
        payload = json.loads(text)
        payload["value"] = {}
        with pytest.raises(ValueError, match="zero country rows"):
            parse_eurostat(json.dumps(payload), expected_ref=ref)


# --- v22: the bilateral ROW door (migr_pop3ctb/ROW/{geo}) --------------------

ROW_FR = (FIXTURES / "eurostat_migr_row_fr_sample.json").read_text(encoding="utf-8")
ROW_FR_REF = "migr_pop3ctb/ROW/FR"


def test_build_url_pins_the_row_query_shape():
    # geo PINNED in the URL, c_birth deliberately ABSENT (the by-birth
    # codelist as printed — the whole point of the ROW door), the frame
    # pins age/sex/unit riding beside.
    assert build_url(ROW_FR_REF) == (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
        "migr_pop3ctb?format=JSON&lang=EN&geo=FR&age=TOTAL&sex=T&unit=NR"
    )


@pytest.mark.parametrize(
    "bad_ref",
    [
        "migr_pop3ctb/ROW/",           # no geo
        "migr_pop3ctb/ROW/fr",         # lowercase geo
        "migr_pop3ctb/ROW/FR/extra",   # four segments = the pinned grammar
    ],
)
def test_row_ref_format_is_the_one_grammar_the_door_speaks(bad_ref):
    with pytest.raises(ValueError, match="Invalid Eurostat source_ref"):
        build_url(bad_ref)


def test_parse_row_reads_the_bilateral_face_with_the_drop_classes(caplog):
    with caplog.at_level(logging.INFO):
        records = parse_eurostat(ROW_FR, expected_ref=ROW_FR_REF)
    # THE ARITHMETIC OF THE DOOR, exact: 1,450 non-empty cells =
    # 1,220 emitted + 150 aggregate/region + 76 summary codes + 4 diagonal
    # (read live 2026-09-22, the fixture IS the live response).
    assert len(records) == 1220
    logged = " ".join(rec.getMessage() for rec in caplog.records)
    assert "dropped 150 aggregate/region origin cell(s)" in logged
    assert "dropped 76 summary-code cell(s)" in logged
    assert "dropped 4 diagonal cell(s)" in logged
    # every emitted record carries BOTH axes (the destination pinned FR).
    assert all(r.iso3_raw == "FRA" and r.entity_raw_name == "France" for r in records)
    assert all(r.origin_raw_name and r.origin_iso3_raw for r in records)
    assert all(r.sex is None for r in records)  # the T pin


def test_parse_row_carries_the_todd_board_anchors():
    records = parse_eurostat(ROW_FR, expected_ref=ROW_FR_REF)
    got = {(r.origin_iso3_raw, r.year): r.value for r in records}
    # THE BOOK'S OWN BOARD (Le Destin des immigrés): the Maghreb/Turkish/
    # Portuguese stocks IN France, as the registration prints them.
    assert got[("MAR", 2015)] == pytest.approx(954742)
    assert got[("MAR", 2018)] == pytest.approx(992120)
    assert got[("DZA", 1999)] == pytest.approx(1246706)
    assert got[("DZA", 2018)] == pytest.approx(1390284)
    assert got[("TUN", 2018)] == pytest.approx(415642)
    assert got[("TUR", 2018)] == pytest.approx(256684)
    assert got[("PRT", 1999)] == pytest.approx(579465)
    assert got[("PRT", 2025)] == pytest.approx(599492)
    # the census-round coverage cliff, as-printed: the Maghreb slices stop
    # at 2018 while Portugal prints the full 14-round series.
    assert not any(y > 2018 for (o, y) in got if o in ("MAR", "DZA", "TUN", "TUR"))
    # THE VANISHED ORIGIN, admitted (v22): the withdrawn alpha-2 AN rides
    # the origin override table onto the netherlands_antilles entity's ANT.
    assert got[("ANT", 1999)] == pytest.approx(78)
    assert got[("ANT", 2005)] == pytest.approx(450)
    # THE SHARED-OVERRIDE PATH: EL (Greece, Eurostat's own code) resolves
    # through the geo table onto GRC — the origin axis inherits it.
    assert got[("GRC", 1999)] == pytest.approx(11872)


def test_parse_row_carries_the_flags_as_reported():
    records = parse_eurostat(ROW_FR, expected_ref=ROW_FR_REF)
    flagged = [r for r in records if r.quality_code]
    assert flagged  # the 'b'/'e'/'p' flags ride the by-origin cells too
    assert {r.quality_code for r in flagged} <= {"b", "e", "p", "be", "bp", "ep", "bep"}
    assert any(r.provisional for r in records)  # 'p'-carrying cells flag


def test_row_pin_guards_refuse_slices_we_did_not_ask_for():
    # the geo pin: a DE row under an FR ref — refused (the soft-miss
    # pattern guards the pinned destination).
    payload = json.loads(ROW_FR)
    payload["dimension"]["geo"]["category"]["index"] = {"DE": 0}
    with pytest.raises(ValueError, match="refusing a slice carrying more"):
        parse_eurostat(json.dumps(payload), expected_ref=ROW_FR_REF)
    # the age pin: swapped — refused (the ROW frame is TOTAL, always).
    payload = json.loads(ROW_FR)
    payload["dimension"]["age"]["category"]["index"] = {"Y15-64": 0}
    with pytest.raises(ValueError, match="does not match the requested"):
        parse_eurostat(json.dumps(payload), expected_ref=ROW_FR_REF)
    # the sex pin: swapped — refused.
    payload = json.loads(ROW_FR)
    payload["dimension"]["sex"]["category"]["index"] = {"F": 0}
    with pytest.raises(ValueError, match="does not match the requested"):
        parse_eurostat(json.dumps(payload), expected_ref=ROW_FR_REF)


def test_row_soft_miss_is_a_loud_failure():
    payload = json.loads(ROW_FR)
    payload["value"] = {}
    with pytest.raises(ValueError, match="zero country rows"):
        parse_eurostat(json.dumps(payload), expected_ref=ROW_FR_REF)


def test_row_requires_a_resolvable_origin_codelist(caplog=None):
    # a two-letter c_birth code neither override table answers is a
    # codelist surprise — loud failure, never a guessed mapping.
    payload = json.loads(ROW_FR)
    cb = payload["dimension"]["c_birth"]["category"]
    # swap a real origin code (AD) for an unresolvable two-letter code
    ad_idx = cb["index"]["AD"]
    cb["index"]["XX"] = cb["index"].pop("AD")
    cb["label"]["XX"] = "Codelist surprise"
    values = {k: v for k, v in payload["value"].items()}
    payload["value"] = {
        str(0 + int(k) if int(k) // 28 == ad_idx and False else k): v for k, v in values.items()
    }
    # place a value on the XX origin at 2015 (position = ad_idx*28 + t2015)
    t2015 = payload["dimension"]["time"]["category"]["index"]["2015"]
    payload["value"][str(ad_idx * 28 + t2015)] = 1234
    with pytest.raises(ValueError, match="neither in the origin override tables"):
        parse_eurostat(json.dumps(payload), expected_ref=ROW_FR_REF)


# --- v23: the bilateral citizenship ROW door (migr_pop1ctz/ROW/{geo}) --------

CTZ_FR = (FIXTURES / "eurostat_migr1ctz_row_fr_sample.json").read_text(encoding="utf-8")
CTZ_FR_REF = "migr_pop1ctz/ROW/FR"


def test_ctz_build_url_pins_the_row_query_shape():
    # The citizenship twin of the ROW grammar: geo PINNED in the URL,
    # citizen deliberately ABSENT (the by-citizenship codelist as printed
    # — 287 codes), the same frame pins age/sex/unit riding beside.
    assert build_url(CTZ_FR_REF) == (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
        "migr_pop1ctz?format=JSON&lang=EN&geo=FR&age=TOTAL&sex=T&unit=NR"
    )


@pytest.mark.parametrize(
    "bad_ref",
    [
        "migr_pop1ctz/ROW/",           # no geo
        "migr_pop1ctz/ROW/fr",         # lowercase geo
        "migr_pop1ctz/FOR/TOTAL/T",    # the single-axis ctz door: unwired, refused
        "migr_pop1ctz/ROW/FR/extra",   # four segments = the pinned grammar
    ],
)
def test_ctz_row_ref_format_is_the_one_grammar_the_door_speaks(bad_ref):
    # The citizenship face speaks the ROW grammar ONLY — the single-axis
    # foreigners-total door stays unwired, recorded in sources.yaml (the
    # refusal message says so).
    with pytest.raises(ValueError, match="Invalid Eurostat source_ref"):
        build_url(bad_ref)


def test_parse_ctz_row_reads_the_bilateral_face_with_the_drop_classes(caplog):
    with caplog.at_level(logging.INFO):
        records = parse_eurostat(CTZ_FR, expected_ref=CTZ_FR_REF)
    # THE ARITHMETIC OF THE DOOR, exact: 927 non-empty cells =
    # 714 emitted + 143 aggregate/region + 53 summary codes + 12 STLS
    # stateless + 5 diagonal (read live 2026-09-25, the fixture IS the
    # live response — every count the v23 probe measured).
    assert len(records) == 714
    logged = " ".join(rec.getMessage() for rec in caplog.records)
    assert "dropped 143 aggregate/region origin cell(s)" in logged
    assert "dropped 53 summary-code cell(s)" in logged
    assert "dropped 5 diagonal cell(s)" in logged
    # every emitted record carries BOTH axes (the destination pinned FR)
    # and the FACE routing key: origin_axis="citizenship", never None.
    assert all(r.iso3_raw == "FRA" and r.entity_raw_name == "France" for r in records)
    assert all(r.origin_raw_name and r.origin_iso3_raw for r in records)
    assert all(r.origin_axis == "citizenship" for r in records)
    assert all(r.sex is None for r in records)  # the T pin
    assert len({r.origin_iso3_raw for r in records}) == 127  # the FR row's origins


def test_ctz_stateless_is_its_own_drop_class(caplog):
    # STLS is the citizenship axis's own residual — a nationality without
    # a state, 12 cells on the FR row — dropped LOGGED as its own class
    # (the birth face's codelist never printed the code).
    with caplog.at_level(logging.INFO):
        parse_eurostat(CTZ_FR, expected_ref=CTZ_FR_REF)
    logged = " ".join(rec.getMessage() for rec in caplog.records)
    assert "dropped 12 stateless cell(s)" in logged
    assert "STLS" in logged


def test_parse_ctz_row_carries_the_v18_anchor_disambiguation():
    records = parse_eurostat(CTZ_FR, expected_ref=CTZ_FR_REF)
    got = {(r.origin_iso3_raw, r.year): r.value for r in records}
    # THE v18 ANCHORS, landed on the face they always belonged to: the
    # "MA 2015 = 458,561" of the v18 probe record was the CITIZENSHIP
    # print — re-read live 2026-09-25, the four-year series exact.
    assert got[("MAR", 2015)] == pytest.approx(458561)
    assert got[("MAR", 2016)] == pytest.approx(465230)
    assert got[("MAR", 2017)] == pytest.approx(472843)
    assert got[("MAR", 2018)] == pytest.approx(480600)
    # THE CONTRAST PAIR (§5.4, labels corrected): the birth face prints
    # FR<-PT 2015 = 648,112; the citizenship face prints 541,867 —
    # CONVERGE, the Portuguese rarely naturalizing before the census.
    assert got[("PRT", 2015)] == pytest.approx(541867)
    # THE SHARED-OVERRIDE PATH: EL (Greece, Eurostat's own code) resolves
    # through the geo table onto GRC — the origin axis inherits it, on
    # the citizenship face exactly as on the birth face.
    assert got[("GRC", 2015)] == pytest.approx(7565)
    # the census-round coverage cliff rides this face too: the Maghreb
    # citizenship slices stop at 2018 while Portugal prints through 2025.
    assert not any(y > 2018 for (o, y) in got if o == "MAR")
    assert any(y == 2025 for (o, y) in got if o == "PRT")


def test_ctz_row_pin_guards_refuse_slices_we_did_not_ask_for():
    # the layout guard: the citizen dimension renamed to c_birth — the
    # response is not the migr_pop1ctz layout, refused loudly (a door
    # change is never silently re-interpreted).
    payload = json.loads(CTZ_FR)
    payload["id"] = ["freq", "c_birth", "age", "unit", "sex", "geo", "time"]
    payload["dimension"]["c_birth"] = payload["dimension"].pop("citizen")
    with pytest.raises(ValueError, match="not the migr_pop1ctz layout"):
        parse_eurostat(json.dumps(payload), expected_ref=CTZ_FR_REF)
    # the age pin: swapped — refused (the ROW frame is TOTAL, always).
    payload = json.loads(CTZ_FR)
    payload["dimension"]["age"]["category"]["index"] = {"Y15-64": 0}
    with pytest.raises(ValueError, match="does not match the requested"):
        parse_eurostat(json.dumps(payload), expected_ref=CTZ_FR_REF)
    # the sex pin: swapped — refused.
    payload = json.loads(CTZ_FR)
    payload["dimension"]["sex"]["category"]["index"] = {"F": 0}
    with pytest.raises(ValueError, match="does not match the requested"):
        parse_eurostat(json.dumps(payload), expected_ref=CTZ_FR_REF)


def test_ctz_soft_miss_is_a_loud_failure():
    payload = json.loads(CTZ_FR)
    payload["value"] = {}
    with pytest.raises(ValueError, match="zero country rows"):
        parse_eurostat(json.dumps(payload), expected_ref=CTZ_FR_REF)


def test_the_shared_row_grammar_routes_the_face_by_dataset():
    # ONE grammar, TWO faces: the dataset part of the capture chooses the
    # origin dimension (c_birth vs citizen) and the routing key
    # (origin_axis) — the birth face parses with "birth", the citizenship
    # face with "citizenship", never confused, never merged.
    birth = parse_eurostat(ROW_FR, expected_ref=ROW_FR_REF)
    ctz = parse_eurostat(CTZ_FR, expected_ref=CTZ_FR_REF)
    assert {r.origin_axis for r in birth} == {"birth"}
    assert {r.origin_axis for r in ctz} == {"citizenship"}
    # the same pair, two faces, two values: FR<-MA 2015 prints 954,742
    # born and 458,561 citizens — the two legalities of the same stock,
    # the ADR-0010 discipline in one assertion.
    birth_got = {(r.origin_iso3_raw, r.year): r.value for r in birth}
    ctz_got = {(r.origin_iso3_raw, r.year): r.value for r in ctz}
    assert birth_got[("MAR", 2015)] == pytest.approx(954742)
    assert ctz_got[("MAR", 2015)] == pytest.approx(458561)


# --- v24: the by-sex ROW doors (migr_pop{3ctb,1ctz}/ROW/{geo}/{sex}) ----------

ROW_FR_M = (FIXTURES / "eurostat_migr3ctb_row_fr_m_sample.json").read_text(encoding="utf-8")
CTZ_FR_F = (FIXTURES / "eurostat_migr1ctz_row_fr_f_sample.json").read_text(encoding="utf-8")


def test_row_sex_build_url_pins_the_query_shape():
    # The BY-SEX twin of the ROW grammar: the sex pin swapped from T to M/F,
    # everything else identical — geo PINNED, the origin dimension ABSENT.
    assert build_url("migr_pop3ctb/ROW/FR/M") == (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
        "migr_pop3ctb?format=JSON&lang=EN&geo=FR&age=TOTAL&sex=M&unit=NR"
    )
    assert build_url("migr_pop1ctz/ROW/FR/F") == (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
        "migr_pop1ctz?format=JSON&lang=EN&geo=FR&age=TOTAL&sex=F&unit=NR"
    )


@pytest.mark.parametrize(
    "bad_ref",
    [
        # (note: 'migr_pop3ctb/ROW/FR/T' is NOT refused here — the 4-segment
        # space is shared with the pre-v22 pinned-c_birth grammar, whose
        # c_birth position accepts any uppercase code: ROW/FR/T parses as
        # c_birth=ROW, age=FR, sex=T, a nonsense ref whose fetch fails the
        # soft-miss guard loudly. The ROW-SEX grammar itself speaks M/F
        # only — T rides the BARE form.)
        "migr_pop3ctb/ROW/FR/X",    # an unknown sex code (the sex class is [TMF])
        "migr_pop1ctz/ROW/FR/M/X",  # five segments
        "migr_pop1ctz/ROW/fr/M",    # lowercase geo
    ],
)
def test_row_sex_ref_is_the_one_grammar_the_ventilation_speaks(bad_ref):
    with pytest.raises(ValueError, match="Invalid Eurostat source_ref"):
        build_url(bad_ref)


def test_parse_row_sex_reads_the_male_ventilation_of_the_birth_face():
    records = parse_eurostat(ROW_FR_M, expected_ref="migr_pop3ctb/ROW/FR/M")
    # 1,220 records — the same row as the _T door, ventilated: every record
    # carries sex="male" and the birth-face routing key.
    assert len(records) == 1220
    assert all(r.sex == "male" for r in records)
    assert all(r.origin_axis == "birth" for r in records)
    got = {(r.origin_iso3_raw, r.year): r.value for r in records}
    # THE ARITHMETIC ANCHOR (verified live 2026-09-25): M + F = the _T print
    # to the unit — 479,354 + 475,388 = 954,742, the v22 fixture's own
    # FR<-MA 2015 anchor.
    assert got[("MAR", 2015)] == pytest.approx(479354)
    assert got[("MAR", 2018)] == pytest.approx(492723)
    assert got[("PRT", 2015)] == pytest.approx(331297)
    # the vanished-origin admission rides the ventilation too (the M row's
    # own print — read live: 32; the _T face's 78 = M 32 + F 46, the same
    # arithmetic coherence at the vanished origin).
    assert got[("ANT", 1999)] == pytest.approx(32)


def test_parse_row_sex_reads_the_female_ventilation_of_the_citizenship_face():
    records = parse_eurostat(CTZ_FR_F, expected_ref="migr_pop1ctz/ROW/FR/F")
    assert len(records) == 714
    assert all(r.sex == "female" for r in records)
    assert all(r.origin_axis == "citizenship" for r in records)
    got = {(r.origin_iso3_raw, r.year): r.value for r in records}
    # THE SEAM ON THE F FACE (verified live): the OECD B15 F print agrees
    # to the unit — FR<-MAR F 2015 = 226,668 on both doors; and M + F =
    # the _T print: 231,893 + 226,668 = 458,561.
    assert got[("MAR", 2015)] == pytest.approx(226668)
    assert got[("MAR", 2018)] == pytest.approx(243044)
    assert got[("PRT", 2015)] == pytest.approx(252472)
