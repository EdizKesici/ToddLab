from pathlib import Path

import pytest

from src.connectors.dyb import (
    DybConnector,
    _english_name,
    _parse_table15_rows,
    _parse_table17_rows,
    _parse_table21_rows,
    _parse_table4_rows,
    build_url,
    parse_dyb,
    parse_dyb_footnotes,
    parse_table15,
    parse_table17,
    parse_table21,
    parse_table4,
)
from src.pipeline.fetch import CONNECTORS
from src.schema.indicator import Provider

FIXTURE = Path(__file__).parent / "fixtures" / "dyb_table15_sample.xls"


def _records(**kwargs):
    return parse_table15(FIXTURE.read_text(encoding="utf-8"), **kwargs)


def test_build_url_valid():
    assert build_url("2024/table15") == (
        "https://unstats.un.org/unsd/demographic-social/products/dyb"
        "/documents/DYB2024/table15.xls"
    )


def test_build_url_rejects_malformed_source_ref():
    for bad in ["table15", "2024", "2024/table", "1799/table15", "2024/table015", "2024/table15/x"]:
        with pytest.raises(ValueError, match="Invalid DYB source_ref"):
            build_url(bad)


def test_fixture_parses_with_expected_shape():
    records = _records()
    # 3 countries x 5 years, Tonga counted twice (two Total rows) = 25.
    assert len(records) == 25
    names = {r.entity_raw_name for r in records}
    assert names == {"Algeria", "Botswana", "France", "Tonga"}


def test_bilingual_name_is_split_to_english_part():
    # "Algeria - Algérie" -> "Algeria" (matches pycountry-derived names).
    records = _records()
    assert any(r.entity_raw_name == "Algeria" for r in records)
    assert all("Algérie" not in r.entity_raw_name for r in records)


def test_rate_block_values_match_the_source_cells():
    rates = {(r.entity_raw_name, r.year): r.value for r in _records(block="rate")}
    assert rates[("France", 2020)] == pytest.approx(3.3746540657)
    assert rates[("France", 2024)] == pytest.approx(3.8378378378)


def test_number_block_selects_registered_deaths():
    numbers = {(r.entity_raw_name, r.year): r.value for r in _records(block="number")}
    assert numbers[("Algeria", 2020)] == pytest.approx(18676.0)
    assert numbers[("France", 2023)] == pytest.approx(2392.0)


def test_missing_marker_becomes_none_not_zero():
    rates = {(r.entity_raw_name, r.year): r.value for r in _records()}
    # Algeria (quality "U"): counts present, every rate cell is "...".
    assert all(rates[("Algeria", y)] is None for y in range(2020, 2025))


def test_footnote_reference_cells_are_never_values():
    # The fixture plants a DIGIT ('2') in a footnote-reference cell next to
    # Algeria's 2021 death count. Naive value filtering would swallow it as
    # a rate; positional parsing must not (see connector docstring).
    algeria_rates = [r.value for r in _records() if r.entity_raw_name == "Algeria"]
    assert algeria_rates == [None] * 5
    numbers = [r.value for r in _records(block="number") if r.entity_raw_name == "Algeria"]
    assert numbers == [18676.0, 19001.0, 18007.0, 17797.0, None]


def test_repeated_total_rows_are_both_emitted():
    # Tonga has one "U" row (2020) and one "|" row (2021): both Total rows
    # are kept; a genuine same-year duplicate is validate.py's alarm to raise.
    tonga_numbers = [r for r in _records(block="number") if r.entity_raw_name == "Tonga"]
    by_year = {}
    for r in tonga_numbers:
        by_year.setdefault(r.year, []).append(r.value)
    # Each Total row emits the whole window (missing years = None), so a
    # repeated row ADDS a second value per year, None where it has none.
    assert by_year[2020] == [8.0, None]  # 8.0 from the "U" row
    assert by_year[2021] == [None, 11.0]  # 11.0 from the "|" row


def test_urban_rural_rows_are_not_emitted_in_phase_1():
    # Urban/Rural needs a dimension field in the raw schema (phase 2):
    # only "Total" rows are emitted, and the Urban rows' values (e.g.
    # France urban rate 3.5443321286) must not leak in.
    rates = {(r.entity_raw_name, r.year): r.value for r in _records()}
    assert rates[("France", 2020)] == pytest.approx(3.3746540657)  # not the urban 3.54


def test_iso3_raw_is_none_dyb_has_no_codes():
    assert all(r.iso3_raw is None for r in _records())


def test_invalid_block_raises():
    with pytest.raises(ValueError, match="block"):
        _records(block="urban")


def test_no_year_header_raises():
    xml = """<?xml version="1.0"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Worksheet ss:Name="Data"><Table>
  <Row><Cell><Data ss:Type="String">France</Data></Cell></Row>
 </Table></Worksheet>
</Workbook>"""
    with pytest.raises(ValueError, match="No year-header row"):
        parse_table15(xml)


def test_unexpected_cell_at_value_position_raises():
    # Hand-built table with garbage where a rate value belongs.
    inner = (
        '<Cell ss:Index="1"><Data ss:Type="String">Total</Data></Cell>'
        '<Cell ss:Index="2"><Data ss:Type="String">C</Data></Cell>'
        '<Cell ss:Index="3"><Data ss:Type="Number">12</Data></Cell>'
        '<Cell ss:Index="5"><Data ss:Type="Number">13</Data></Cell>'
        '<Cell ss:Index="7"><Data ss:Type="Number">14</Data></Cell>'
        '<Cell ss:Index="9"><Data ss:Type="Number">15</Data></Cell>'
        '<Cell ss:Index="11"><Data ss:Type="Number">16</Data></Cell>'
        '<Cell ss:Index="13"><Data ss:Type="String">NOT-A-NUMBER</Data></Cell>'
    )
    header = "".join(
        f'<Cell ss:Index="{c}" ss:MergeAcross="1"><Data ss:Type="Number">{y}</Data></Cell>'
        for c, y in zip((3, 5, 7, 9, 11, 13, 15, 17, 19, 21),
                        ("2020", "2021", "2022", "2023", "2024") * 2)
    )
    xml = f"""<?xml version="1.0"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Worksheet ss:Name="Data"><Table>
  <Row>{header}</Row>
  <Row><Cell><Data ss:Type="String">France</Data></Cell></Row>
  <Row>{inner}</Row>
 </Table></Worksheet>
</Workbook>"""
    with pytest.raises(ValueError, match="Unexpected cell content"):
        parse_table15(xml)


def test_connector_is_registered_for_fetch():
    assert Provider.un_dyb in CONNECTORS
    assert CONNECTORS[Provider.un_dyb].provider == "un_dyb"


def test_connector_fetch_raw_uses_utf8_sig_decoding():
    # A fake session returning BOM-prefixed SpreadsheetML: fetch_raw must
    # decode explicitly (requests would guess ISO-8859-1 for the untyped
    # stream and mangle the bilingual names).
    class FakeResponse:
        status_code = 200
        content = "\ufeff".encode("utf-8") + FIXTURE.read_bytes()

        def raise_for_status(self):
            pass

    class FakeSession:
        def get(self, url, headers=None, timeout=None):
            assert "DYB2024/table15.xls" in url
            return FakeResponse()

    connector = DybConnector(session=FakeSession())
    result = connector.fetch_raw("2024/table15", "infant_mortality_witness")
    assert result.provider == "un_dyb"
    assert result.source_ref == "2024/table15"
    assert result.source_url.endswith("DYB2024/table15.xls")
    assert len(result.records) == 25
    assert any(r.entity_raw_name == "Algeria" for r in result.records)


# --- P1: the edition loop (multi-era URLs, format dispatch, Table 4) ---------

def test_build_url_legacy_era_uses_the_old_site():
    # Editions 2011-2014 live on the pre-migration site with capital-T
    # table files (verified live 2026-09-06).
    assert build_url("2014/table15") == (
        "https://unstats.un.org/unsd/demographic/products/dyb"
        "/dyb2014/Table15.xls"
    )
    assert build_url("2011/table04") == (
        "https://unstats.un.org/unsd/demographic/products/dyb"
        "/dyb2011/Table04.xls"
    )


def test_build_url_2015_uses_the_recovered_legacy_pattern():
    # v10: the 2015 edition is RECOVERED — its own index links are dead
    # (tiny HTML error pages) but the legacy /dyb2015/TableNN.xls pattern
    # is alive on the live site (verified by direct download 2026-09-13).
    # The v8 contract (build_url refusing "2015/..." loudly) is superseded.
    assert (
        build_url("2015/table15")
        == "https://unstats.un.org/unsd/demographic/products/dyb/dyb2015/Table15.xls"
    )


def test_parse_dyb_dispatches_on_the_files_own_title():
    # Bytes in (any era's format family), records out — dispatch on the
    # title the file itself prints, cross-checked against the request.
    records = parse_dyb(FIXTURE.read_bytes(), expected_table=15)
    assert len(records) == 25  # identical to the text-path parser


def test_parse_dyb_refuses_a_table_number_mismatch():
    # The config says table15, the file's title says something else: refuse
    # rather than silently parse the wrong table into the wrong indicator.
    with pytest.raises(ValueError, match="refusing to parse a different table"):
        parse_dyb(FIXTURE.read_bytes(), expected_table=4)


def test_parse_dyb_refuses_unwired_tables():
    text = FIXTURE.read_text(encoding="utf-8").replace(
        "15. Infant deaths and infant mortality rates by urban/rural residence: 2020-2024",
        "16. Infant deaths and infant mortality rates by age and sex: 2020-2024",
    )
    with pytest.raises(ValueError, match="not wired"):
        parse_dyb(text.encode("utf-8"), expected_table=16)


def test_parse_dyb_refuses_files_without_a_title():
    # A structurally valid SpreadsheetML sheet that carries no numbered
    # title row: refused loudly (and empty fragments fail even earlier,
    # at the Worksheet/Table checks — either way, never silently parsed).
    text = (
        '<?xml version="1.0"?>'
        '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet">'
        '<Worksheet><Table><Row><Cell><Data>no title here</Data></Cell></Row></Table></Worksheet>'
        "</Workbook>"
    )
    with pytest.raises(ValueError, match="No table-number title"):
        parse_dyb(text.encode("utf-8"))


T4_FIXTURE = Path(__file__).parent / "fixtures" / "dyb_table4_sample.xls"


def test_table4_fixture_emits_sex_split_records():
    records = parse_table4(T4_FIXTURE.read_text(encoding="utf-8"))
    france = {(r.year, r.sex): r.value for r in records if r.entity_raw_name == "France"}
    assert france[(2020, "male")] == pytest.approx(79.1)
    assert france[(2020, "female")] == pytest.approx(85.6)
    assert france[(2024, "female")] == pytest.approx(86.1)
    # The collector prints Male and Female separately — every Table 4
    # record carries its sex (the merge key is entity-year-SEX).
    assert all(r.sex in ("male", "female") for r in records)


def test_table4_all_missing_year_still_emits_explicit_gap_records():
    records = parse_table4(T4_FIXTURE.read_text(encoding="utf-8"))
    algeria = {(r.year, r.sex): r.value for r in records if r.entity_raw_name == "Algeria"}
    # Algeria 2021: the row exists (births reported) but LE is "..." for
    # both sexes — explicit gap records, never zeros, never dropped here
    # (dropping all-None keys is merge.py's canonical-tier policy).
    assert algeria[(2021, "male")] is None
    assert algeria[(2021, "female")] is None


def test_table4_refuses_a_missing_header_signature():
    # The fixed column map is only trusted after the Male/Female header
    # signature is verified at columns 17/19.
    text = T4_FIXTURE.read_text(encoding="utf-8").replace(">Male<", ">Homme<")
    with pytest.raises(ValueError, match="header signature"):
        parse_table4(text)


def test_connector_fetch_raw_dispatches_table4_with_sex():
    class FakeResponse:
        status_code = 200
        content = T4_FIXTURE.read_bytes()

        def raise_for_status(self):
            pass

    class FakeSession:
        def get(self, url, headers=None, timeout=None):
            assert "DYB2024/table04.xls" in url
            return FakeResponse()

    connector = DybConnector(session=FakeSession())
    result = connector.fetch_raw("2024/table04", "life_expectancy")
    assert result.provider == "un_dyb"
    assert all(r.sex in ("male", "female") for r in result.records)


# --- BIFF-era normalizations (row-level: no xlrd needed in tests) ------------

def test_english_name_strips_glued_footnote_digits():
    assert _english_name("Botswana2") == "Botswana"
    assert _english_name("Algeria - Algérie1") == "Algeria"
    assert _english_name("Burkina Faso3") == "Burkina Faso"
    assert _english_name("France") == "France"


def test_biff_era_glued_footnotes_and_dash_markers_parse_cleanly():
    # The binary editions (2017/2021-2023) glue the row's footnote
    # reference to the country name ("Botswana2") AND to the residence
    # label ("Total11"), and use "-" as a second missing marker. Real BIFF
    # row lists (verified on the cached 2017 edition): values on the EVEN
    # columns with the footnote-reference columns between them, years-as-
    # floats already normalized to int strings.
    rows = [
        ["15. Infant deaths and infant mortality rates: 2013 - 2017"],
        ["Continent, country or area, and urban/rural residence", "Co-de", "Number", "Rate"],
        [None, None, "2013", None, "2014", None, "2015", None, "2016", None, "2017",
         None, "2013", None, "2014", None, "2015", None, "2016", None, "2017"],
        ["AFRICA - AFRIQUE"],
        ["Botswana2"],
        ["Total11", "U", "891", None, "1072", None, "968", None, "-", None, "...",
         None, "...", None, "...", None, "45.6", None, "...", None, "..."],
    ]
    records = _parse_table15_rows(rows, block="rate")
    assert {r.entity_raw_name for r in records} == {"Botswana"}
    rates = {r.year: r.value for r in records}
    assert rates[2015] == pytest.approx(45.6)
    assert rates[2013] is None
    # "-" is an explicit gap, not zero — and the printed marker rides the point.
    numbers = {r.year: r for r in _parse_table15_rows(rows, block="number")}
    assert numbers[2016].value is None
    assert numbers[2016].missing_marker == "-"
    assert numbers[2013].value == pytest.approx(891)
    # P2: the collector's own annotations ride the record — the quality
    # code from the row, the glued footnote refs (country "2" + row "11").
    assert all(r.quality_code == "U" for r in records)
    assert all(r.footnote_refs == ["2", "11"] for r in records)


def test_biff_footnotes_glued_to_the_french_part_are_captured():
    # "Algeria - Algérie1" / "Norfolk Island - Île Norfolk128": the BIFF
    # editions glue the digits to whichever part of the bilingual name they
    # ride — the refs must be captured from the RAW string's end, not lost
    # with the discarded French part.
    rows = [
        ["4. Vital statistics summary and life expectancy at birth: 2013 - 2017"],
        ["Continent, country or area and year", "Live births", "Deaths", "Male", "Female"],
        [None] * 17 + ["Male", None, "Female"],
        ["AFRICA - AFRIQUE"],
        ["Norfolk Island - Île Norfolk128"],
        ["2013", None, None, None, None, None, None, None, None, None, None, None, None,
         None, None, None, None, "71.2", "III", "76.4", None],
    ]
    records = _parse_table4_rows(rows)
    assert {r.entity_raw_name for r in records} == {"Norfolk Island"}
    assert all(r.footnote_refs == ["128"] for r in records)


# --- P2: the collector's own quality annotations ride the records ------------

def test_quality_code_is_captured_from_the_row():
    # The DYB's row code (C/U/|/+"-prefixed) is as-reported metadata:
    # Algeria "U" (incomplete registration), France "C", Tonga's two Total
    # rows "U" then "|".
    codes = {(r.entity_raw_name, r.year): r.quality_code for r in _records()}
    assert codes[("Algeria", 2020)] == "U"
    assert codes[("France", 2020)] == "C"
    tonga = sorted({r.quality_code for r in _records() if r.entity_raw_name == "Tonga"})
    assert tonga == ["U", "|"]


def test_footnote_refs_and_provisional_flag_are_captured():
    # The marker cell immediately right of a value: France's 2021 rate
    # carries footnote ref 1; the 2020/2024 rates carry "*" (provisional).
    rates = {(r.entity_raw_name, r.year): r for r in _records()}
    assert rates[("France", 2021)].footnote_refs == ["1"]
    assert rates[("France", 2021)].provisional is None
    assert rates[("France", 2020)].provisional is True
    assert rates[("France", 2024)].provisional is True
    assert rates[("France", 2022)].provisional is None
    # Algeria's 2021 death count carries the footnote 2 (never a value).
    numbers = {(r.entity_raw_name, r.year): r for r in _records(block="number")}
    assert numbers[("Algeria", 2021)].footnote_refs == ["2"]


def test_missing_marker_distinguishes_the_printed_gaps():
    # "..." (not available) and "-" (nil) MEAN different things: the marker
    # rides the point instead of both collapsing into an anonymous None.
    rates = {(r.entity_raw_name, r.year): r for r in _records()}
    assert rates[("Algeria", 2020)].value is None
    assert rates[("Algeria", 2020)].missing_marker == "..."
    assert rates[("France", 2020)].missing_marker is None


def test_table4_reference_range_and_footnote_markers():
    # Legend b: a Roman numeral next to the LE value = the width of the
    # reference period (III = 3-year period, V = 5). "V 5" = range V AND
    # footnote ref 5 on the same cell.
    records = parse_table4(T4_FIXTURE.read_text(encoding="utf-8"))
    by = {(r.entity_raw_name, r.year, r.sex): r for r in records}
    assert by[("Algeria", 2020, "male")].reference_range == "III"
    assert by[("Algeria", 2020, "female")].reference_range == "III"
    assert by[("France", 2021, "male")].reference_range == "V"
    assert by[("France", 2021, "male")].footnote_refs == ["5"]
    assert by[("France", 2021, "female")].reference_range == "V"
    assert by[("France", 2020, "male")].footnote_refs == ["5"]
    # "*" next to the value = the DYB's own provisional flag.
    assert by[("Czechia", 2022, "female")].provisional is True
    assert by[("Czechia", 2022, "male")].missing_marker == "..."


def test_table4_le_points_carry_no_quality_code():
    # Deliberate: the C/U/| codes on Table 4 describe the births/deaths/
    # infant-deaths blocks — attaching them to the LE columns would be an
    # interpretation. The LE's own markers (range, refs, *) DO ride.
    records = parse_table4(T4_FIXTURE.read_text(encoding="utf-8"))
    assert all(r.quality_code is None for r in records)


def test_footnotes_worksheet_is_extracted_with_legend():
    # The second worksheet carries the code legend + the numbered note
    # texts; the snapshot joins them to the emitted points' refs.
    block = parse_dyb_footnotes(FIXTURE.read_bytes())
    assert set(block["legend"]) == {"italics", "*", "a"}
    assert "Civil registration" in block["legend"]["a"]
    assert block["notes"]["1"] == "Data refer to the de facto population."
    assert block["notes"]["2"] == "Data include deaths registered late."
    t4_block = parse_dyb_footnotes(T4_FIXTURE.read_bytes())
    assert set(t4_block["legend"]) == {"italics", "*", "a", "b"}
    assert "reference period" in t4_block["legend"]["b"]


def test_footnote_rows_glued_biff_style_parse_too():
    # BIFF footnotes carry marker + text in ONE cell, space-separated
    # (SpreadsheetML uses 'marker\ntext' in separate cells): both grammars
    # must produce the same legend/notes dicts.
    from src.connectors.dyb import _footnotes_from_rows

    rows = [
        ["FOOTNOTES\nNOTES"],
        [" Italics: data from civil registers which are incomplete."],
        ["* Provisional. - Donnees provisoires."],
        ["a 'Code' indicates the source of data: C - Civil registration."],
        ["b A Roman number specifies the range of the reference period."],
        ["1 Excluding live-born infants who died before registration."],
        ["Data refer to the de facto population."],  # continuation row
    ]
    block = _footnotes_from_rows(rows)
    assert block["legend"]["*"] == "Provisional. - Donnees provisoires."
    assert "Civil registration" in block["legend"]["a"]
    assert block["notes"]["1"] == (
        "Excluding live-born infants who died before registration. "
        "Data refer to the de facto population."
    )


def test_unknown_marker_cell_raises_loudly():
    # A marker cell whose content is outside the known grammar (refs,
    # "*", Roman ranges) is a layout change: refuse, never swallow.
    # The marker cell next to France's 2021 RATE (the block the default
    # parse emits) is corrupted outside the known grammar: refuse.
    with pytest.raises(ValueError, match="Unexpected marker cell"):
        parse_table15(
            FIXTURE.read_text(encoding="utf-8").replace(
                '<Cell ss:StyleID="sFootnoteReference"><Data ss:Type="String">1</Data></Cell>\n        <Cell ss:StyleID="sDataFloatRoman"><Data ss:Type="String">3.7054083814</Data></Cell>',
                '<Cell ss:StyleID="sFootnoteReference"><Data ss:Type="String">??</Data></Cell>\n        <Cell ss:StyleID="sDataFloatRoman"><Data ss:Type="String">3.7054083814</Data></Cell>',
            )
        )


# ---------------------------------------------------------------------------
# Table 17 — maternal deaths + maternal mortality ratios (P3b, v9)
# ---------------------------------------------------------------------------

FIXTURE17 = Path(__file__).parent / "fixtures" / "dyb_table17_sample.xls"


def _records17(**kwargs):
    return parse_table17(FIXTURE17.read_text(encoding="utf-8"), **kwargs)


def test_table17_fixture_parses_with_expected_shape():
    records = _records17()
    # 6 rate-printing countries x 6 years (Libya prints counts only).
    assert len(records) == 36
    assert {r.entity_raw_name for r in records} == {
        "Algeria", "Mauritius", "France", "Italy", "Russian Federation", "Egypt",
    }


def test_table17_number_block_selects_registered_deaths():
    records = _records17(block="number")
    # Libya exists ONLY here: counts published, no ratio computed — the
    # collector's honest degradation.
    assert {r.entity_raw_name for r in records} == {
        "Algeria", "Libya", "France", "Italy", "Russian Federation",
    }
    libya = {r.year: r for r in records if r.entity_raw_name == "Libya"}
    assert libya[2022].value == pytest.approx(12.0)
    assert libya[2022].quality_code == "+U"


def test_table17_diamond_marker_is_captured_as_small_base():
    # Notes17: "Ratios based on 30 or fewer maternal deaths are identified
    # by the symbol ♦" — as-reported, transported as small_base.
    mauritius = {r.year: r for r in _records17() if r.entity_raw_name == "Mauritius"}
    assert all(r.small_base is True for r in mauritius.values())
    algeria = {r.year: r for r in _records17() if r.entity_raw_name == "Algeria"}
    assert all(r.small_base is None for r in algeria.values())


def test_table17_diamond_plus_footnote_ref_in_one_cell():
    # The real editions glue the marker to a footnote ref ("♦1", 501 real
    # occurrences across the wired editions): BOTH ride the record.
    france = {r.year: r for r in _records17() if r.entity_raw_name == "France"}
    assert france[2023].small_base is True
    assert france[2023].footnote_refs == ["1"]


def test_table17_gap_and_nil_markers_stay_distinct():
    italy = {r.year: r for r in _records17() if r.entity_raw_name == "Italy"}
    assert italy[2022].value is None
    assert italy[2022].missing_marker == "-"  # nil, not "not available"
    algeria = {r.year: r for r in _records17() if r.entity_raw_name == "Algeria"}
    assert algeria[2022].value is None
    assert algeria[2022].missing_marker == "..."


def test_table17_provisional_star_rides_the_rate():
    france = {r.year: r for r in _records17() if r.entity_raw_name == "France"}
    assert france[2024].provisional is True


def test_table17_quality_code_column_is_captured():
    # Column 1, like Table 15 — including the "code not available" case
    # printed as "..." (kept as printed, never interpreted).
    egypt = {r.year: r for r in _records17() if r.entity_raw_name == "Egypt"}
    assert all(r.quality_code == "..." for r in egypt.values())
    russia = {r.year: r for r in _records17() if r.entity_raw_name == "Russian Federation"}
    assert russia[2019].quality_code == "+C"


def test_table17_per_year_footnote_refs_ride_the_values():
    # The footnote annotates the YEAR's value (Russia 2019 carries note 5,
    # the Chechnya-style territorial caveat), not the whole row.
    russia = {r.year: r for r in _records17() if r.entity_raw_name == "Russian Federation"}
    assert russia[2019].footnote_refs == ["5"]
    assert russia[2020].footnote_refs is None


def test_table17_repeated_page_header_is_skipped():
    # The fixture carries a second year-header mid-table: skipped, and the
    # records still parse (36 = 6 countries x 6 years, no duplicates).
    assert len(_records17()) == 36


def test_table17_dispatches_on_the_files_own_title():
    data = FIXTURE17.read_bytes()
    assert parse_dyb(data, expected_table=17)[0].value is not None
    with pytest.raises(ValueError, match="refusing to parse a different table"):
        parse_dyb(data, expected_table=15)


def test_table17_invalid_block_raises():
    with pytest.raises(ValueError, match="block must be"):
        _records17(block="ratio")


def test_table17_biff_style_glued_footnote_digits_on_names():
    # The BIFF editions glue footnote digits to country names; the table 17
    # parser must capture them as country-level refs like the others.
    rows = [
        ["17. Maternal deaths and maternal mortality ratios: 2019 - 2024"],
        ["Mortalité liée à la maternité, nombre de décès et taux : 2019 - 2024"],
        ["Continent and country or area", "Co-de", "2019", None, "2020", None, "2021", None, "2022", None, "2023", None, "2024"],
        [None, None, None, None, None, None, None, None, None, None, None, None, None],
        ["Norfolk Island - Île Norfolk128"],
        ["Number - Nombre", "C", "1", "128", None, None, None, None, None, None, None, None, None],
        ["Rate - Taux", "C", "2.5", None, None, None, None, None, None, None, None, None, None],
    ]
    records = _parse_table17_rows(rows, block="rate")
    assert records[0].entity_raw_name == "Norfolk Island"
    assert records[0].footnote_refs == ["128"]  # the glued digits ride the refs
    assert records[0].value == pytest.approx(2.5)


# --- Table 21/22: life expectancy at specified ages (v10) ---------------------

FIXTURE21 = Path(__file__).parent / "fixtures" / "dyb_table21_sample.xls"


def _records21(**kwargs):
    return parse_table21(FIXTURE21.read_text(encoding="utf-8"), **kwargs)


def test_table21_age_column_selection_and_sex_split():
    # `age` selects the column: age 60 reads the 13th age column, age 0 the
    # first — same file, same blocks, different values (the config's `field`).
    by_key = {(r.entity_raw_name, r.year, r.sex): r.value for r in _records21(age="60")}
    assert by_key[("Algeria", 2023, "male")] == 16.4
    assert by_key[("Algeria", 2023, "female")] == 19.6
    assert by_key[("France", 2020, "male")] == 21.9
    assert by_key[("France", 2020, "female")] == 26.5
    by_key0 = {(r.entity_raw_name, r.year, r.sex): r.value for r in _records21(age="0")}
    assert by_key0[("France", 2020, "male")] == 78.5
    assert by_key0[("Mauritius", 2024, "female")] == 76.0987654321098
    # Every record is sex-split as printed: the table has no both-sexes row.
    assert {r.sex for r in _records21(age="60")} == {"male", "female"}


def test_table21_reference_period_year_is_the_end():
    # "2022 - 2024" -> year 2024 (the END of the printed period, the DYB's
    # own convention — verified against Table 4's Roman-numeral rows) and
    # the printed period rides reference_range. A single-year row keeps
    # year as printed with no range.
    mauritius = [r for r in _records21(age="60") if r.entity_raw_name == "Mauritius"]
    assert all(r.year == 2024 for r in mauritius)
    assert all(r.reference_range == "2022 - 2024" for r in mauritius)
    algeria = [r for r in _records21(age="60") if r.entity_raw_name == "Algeria"]
    assert all(r.year == 2023 for r in algeria)
    assert all(r.reference_range is None for r in algeria)


def test_table21_dual_block_and_explicit_gaps():
    # The 2024-edition degradation: France carries the full 2020 table AND
    # a 2024 block where only age 0 is published — age 60 prints "...", kept
    # as an explicit gap with its printed marker, never dropped.
    france = {(r.year, r.sex): r for r in _records21(age="60") if r.entity_raw_name == "France"}
    assert set(france) == {(2020, "male"), (2020, "female"), (2024, "male"), (2024, "female")}
    assert france[(2020, "male")].value == 21.9
    for sex in ("male", "female"):
        gap = france[(2024, sex)]
        assert gap.value is None
        assert gap.missing_marker == "..."


def test_table21_sup_footnote_refs_ride_the_records():
    # The SpreadsheetML editions 2011-2015 + 2024 wrap country-level footnote
    # references in <html:Sup>NN</html:Sup> child elements: the fixture's
    # "Mauritius - Maurice<SUP>12</SUP>" must arrive as ref ["12"] on every
    # Mauritius point (the v10 itertext fix — plain .text dropped these).
    mauritius = [r for r in _records21(age="60") if r.entity_raw_name == "Mauritius"]
    assert all(r.footnote_refs == ["12"] for r in mauritius)


def test_table21_biff_year_row_glued_footnote_digits():
    # The BIFF editions glue a footnote digit to the YEAR row ("20103" =
    # 2010 + note 3 — deterministic, DYB years are exactly 4 digits): the
    # year splits, the ref rides both sex rows of the block.
    rows = [
        ["21. Life expectancy at specified ages for each sex: latest available year,  2005 - 2024"],
        ["Continent, country or area and date", "Age (in years)"],
        [None] + [str(a) for a in range(0, 101, 5)],
        ["France"],
        ["20103"],
        ["Male - Hommes", "80.1", "75.2", "70.3", "65.4", "60.5", "55.6", "50.7", "45.8", "40.9", "36.1", "31.2", "26.3", "21.4", "17.5", "13.6", "9.7", "5.8", "1.9", "...", "...", "..."],
        ["Female - Femmes", "85.1", "80.2", "75.3", "70.4", "65.5", "60.6", "55.7", "50.8", "45.9", "41.1", "36.2", "31.3", "26.4", "22.5", "18.6", "14.7", "10.8", "6.9", "...", "...", "..."],
    ]
    records = _parse_table21_rows(rows, age="60")
    assert [(r.year, r.sex, r.value, r.footnote_refs) for r in records] == [
        (2010, "male", 21.4, ["3"]),
        (2010, "female", 26.4, ["3"]),
    ]


def test_table21_glued_footnote_on_range_end_year():
    # "2012 - 20153" = the period 2012-2015 + note 3 on the END year: the
    # range string rides clean, the ref rides the points.
    rows = [
        ["22. Life expectancy at specified ages for each sex: latest available year,  1998 - 2017"],
        ["Continent, country or area and date", "Age (in years)"],
        [None] + [str(a) for a in range(0, 101, 5)],
        ["Mauritius - Maurice"],
        ["2012 - 20153"],
        ["Male - Hommes", "70.1", "66.2", "61.3", "56.4", "51.5", "46.6", "41.7", "36.8", "31.9", "27.1", "22.2", "17.3", "12.4", "8.5", "4.6", "3.7", "2.8", "1.9", "...", "...", "..."],
        ["Female - Femmes", "75.1", "71.2", "66.3", "61.4", "56.5", "51.6", "46.7", "41.8", "36.9", "32.1", "27.2", "22.3", "17.4", "13.5", "9.6", "5.7", "3.8", "2.9", "...", "...", "..."],
    ]
    records = _parse_table21_rows(rows, age="60")
    for r in records:
        assert r.year == 2015
        assert r.reference_range == "2012 - 2015"
        assert r.footnote_refs == ["3"]


def test_table21_repeated_age_header_mid_table_is_skipped():
    rows = [
        ["21. Life expectancy at specified ages for each sex: latest available year,  2005 - 2024"],
        [None] + [str(a) for a in range(0, 101, 5)],
        ["France"],
        ["2020"],
        ["Male\n-\nHommes", "78.5", "73.8", "68.9", "63.9", "59.0", "54.1", "49.3", "44.5", "39.8", "35.1", "30.6", "26.3", "21.9", "18.1", "14.6", "11.2", "8.2", "5.6", "3.7", "2.5", "2.0"],
        ["Female\n-\nFemmes", "84.6", "79.9", "74.9", "69.9", "65.0", "60.0", "55.1", "50.2", "45.3", "40.5", "35.7", "31.1", "26.5", "22.2", "18.1", "14.1", "10.4", "7.2", "4.7", "3.1", "2.1"],
        [None] + [str(a) for a in range(0, 101, 5)],  # repeated page header
        ["Algeria - Algérie"],
        ["2023"],
        ["Male\n-\nHommes", "71.3", "67.4", "62.5", "57.6", "52.7", "47.9", "43.1", "38.4", "33.8", "29.3", "24.9", "20.6", "16.4", "12.5", "8.9", "5.6", "3.1", "1.5", "...", "...", "..."],
        ["Female\n-\nFemmes", "74.2", "70.5", "65.7", "60.9", "56.1", "51.3", "46.6", "41.9", "37.2", "32.7", "28.2", "23.9", "19.6", "15.4", "11.6", "7.9", "4.9", "2.6", "...", "...", "..."],
    ]
    records = _parse_table21_rows(rows, age="60")
    assert len(records) == 4  # 2 countries x 2 sexes, header repeat skipped


def test_table21_unknown_age_raises_with_the_available_list():
    with pytest.raises(ValueError, match="AGE.*Available ages.*0, 5"):
        _records21(age="62")


def test_table21_dispatches_on_the_title_text_not_just_the_number():
    # Dispatch on the file's OWN title: the fixture says "21." and parses;
    # the same content re-titled "22." (the odd-edition number of the same
    # table) must parse identically — the renumbering zone keys on WORDS.
    data = FIXTURE21.read_bytes()
    assert len(parse_dyb(data, expected_table=21, block="60")) == 8
    retitled = data.replace(
        b"21. Life expectancy at specified ages",
        b"22. Life expectancy at specified ages",
    )
    assert len(parse_dyb(retitled, expected_table=22, block="60")) == 8


def test_parse_dyb_refuses_the_5qx_table_in_the_renumbering_zone():
    # A table-21-numbered file whose title is the 5qx probabilities (what an
    # odd-edition config would fetch by mistake): same layout, different
    # measure — refusing loudly with the parity rule, never mis-parsing.
    data = FIXTURE21.read_bytes().replace(
        b"21. Life expectancy at specified ages for each sex",
        b"21. Probability of dying in the five year interval following specified age (5qx), by sex",
    )
    with pytest.raises(ValueError, match="renumbering zone alternates by edition parity"):
        parse_dyb(data, expected_table=21, block="60")


def test_table21_default_rate_block_raises_helpfully():
    # parse_dyb's default block is "rate" (the Table 15/17 selector): on
    # Table 21/22 it must fail loudly pointing at the age selector, never
    # guess a column.
    with pytest.raises(ValueError, match="got 'rate'"):
        parse_dyb(FIXTURE21.read_bytes(), expected_table=21)


# ---------------------------------------------------------------------------
# Table 9 — live births + crude birth rates (v15): the CBR companion.
# The Table 15 wide layout through its own dispatch branch, with the
# content guard on the title's own words (the 21/22 lesson applied).
# ---------------------------------------------------------------------------

FIXTURE9 = Path(__file__).parent / "fixtures" / "dyb_table9_sample.xls"


def test_table9_fixture_parses_with_expected_shape():
    records = parse_dyb(FIXTURE9.read_bytes(), expected_table=9, block="rate")
    # Algeria (4 valued + 1 gap) + Botswana (4+1) + Burundi (5 gaps) +
    # France (5 valued — the live 2024 file values all five years) +
    # Tonga (U: 5 gaps; |: 1 valued + 4 gaps) = 30 records
    # across 5 countries, Total rows only.
    assert len(records) == 30
    assert {r.entity_raw_name for r in records} == {"Algeria", "Botswana", "Burundi", "France", "Tonga"}
    assert all(r.iso3_raw is None for r in records)  # the DYB prints names, not codes


def test_table9_rate_values_match_the_live_anchors():
    # The anchor discipline (v13/v14): the fixture reproduces the exact
    # bytes the live DYB 2024 Table 9 prints — Algeria's CBR series, the
    # collector's own 10-digit precision as carried.
    records = parse_dyb(FIXTURE9.read_bytes(), expected_table=9, block="rate")
    algeria = {r.year: r for r in records if r.entity_raw_name == "Algeria"}
    assert algeria[2020].value == pytest.approx(22.3369498881)
    assert algeria[2021].value == pytest.approx(21.1357648315)
    assert algeria[2023].value == pytest.approx(19.3150537642)
    assert algeria[2024].value is None and algeria[2024].missing_marker == "..."
    assert algeria[2020].quality_code == "C"
    assert algeria[2020].footnote_refs == ["1"]  # the glued country footnote "Algérie1"


def test_table9_plus_u_rates_are_explicit_gaps_counts_still_printed():
    # Burundi's live row: quality '+U' → the collector's editorial rule
    # computes no CBR — every rate cell prints '...', an explicit gap
    # never zero, exactly the Table 15 discipline.
    records = parse_dyb(FIXTURE9.read_bytes(), expected_table=9, block="rate")
    burundi = [r for r in records if r.entity_raw_name == "Burundi"]
    assert len(burundi) == 5
    assert all(r.value is None and r.missing_marker == "..." for r in burundi)
    assert all(r.quality_code == "+U" for r in burundi)
    # The counts the same rows print (the number block) stay valued.
    counts = parse_dyb(FIXTURE9.read_bytes(), expected_table=9, block="number")
    burundi_counts = [r for r in counts if r.entity_raw_name == "Burundi" and r.year == 2020]
    assert burundi_counts[0].value == pytest.approx(372795.0)


def test_table9_number_block_star_plus_ref_is_provisional_with_refs():
    # THE v15 GRAMMAR FIND: '*NN' glued on a live-birth COUNT cell — the
    # collector marks the count provisional AND cites its footnote in one
    # cell. provisional=True, the digits ride footnote_refs beside the
    # country's own ref (the diamond form's exact mirror).
    counts = parse_dyb(FIXTURE9.read_bytes(), expected_table=9, block="number")
    algeria_2021 = next(r for r in counts if r.entity_raw_name == "Algeria" and r.year == 2021)
    assert algeria_2021.value == pytest.approx(949799.0)
    assert algeria_2021.provisional is True
    assert algeria_2021.footnote_refs == ["1", "2"]  # country ref + the star's own ref


def test_table9_two_total_rows_under_different_quality_codes_both_emit():
    # Tonga's real Table-15 behaviour, present on Table 9 files too: two
    # Total rows (U and |) covering different years — both emitted, the
    # merge arbitrates by its own rules later.
    records = parse_dyb(FIXTURE9.read_bytes(), expected_table=9, block="rate")
    tonga = [r for r in records if r.entity_raw_name == "Tonga"]
    assert {(r.quality_code, r.year, r.value) for r in tonga} == {
        ("U", 2020, None), ("U", 2021, None), ("U", 2022, None), ("U", 2023, None), ("U", 2024, None),
        ("|", 2020, None), ("|", 2021, 27.8), ("|", 2022, None), ("|", 2023, None), ("|", 2024, None),
    }


def test_table9_content_guard_rejects_a_same_numbered_wrong_table():
    # The 21/22 lesson applied: the title's WORDS are the ground truth, the
    # number the cross-check — a table-9-numbered file whose title is not
    # the live-births/CBR table refuses loudly.
    data = FIXTURE9.read_bytes().replace(
        b"9. Live births and crude birth rates, by urban/rural residence",
        b"9. Some other demographic table by residence",
    )
    with pytest.raises(ValueError, match="NOT the live-births/CBR table"):
        parse_dyb(data, expected_table=9)


def test_table9_dispatches_through_the_shared_wide_layout():
    # The dispatch branch routes the Table 9 file through the Table 15
    # parser family: 'rate' selects the CBR block, 'number' the counts —
    # the same block selector, the same wide layout contract. France's
    # row is the live DYB 2024 bytes: the '*' provisional marker rides
    # 2022/2023/2024 on BOTH blocks, and 2020/2021 print unflagged (the
    # v16 anchor repair — the v15 file's France block was fabricated).
    rate_recs = parse_dyb(FIXTURE9.read_bytes(), expected_table=9, block="rate")
    num_recs = parse_dyb(FIXTURE9.read_bytes(), expected_table=9, block="number")
    france_rates = {r.year: r.value for r in rate_recs if r.entity_raw_name == "France"}
    france_counts = {r.year: r.value for r in num_recs if r.entity_raw_name == "France"}
    assert france_rates[2020] == pytest.approx(10.6579082599)
    assert france_counts[2020] == pytest.approx(696664.0)
    for year in (2022, 2023, 2024):
        rate = next(r for r in rate_recs if r.entity_raw_name == "France" and r.year == year)
        count = next(r for r in num_recs if r.entity_raw_name == "France" and r.year == year)
        assert rate.provisional is True
        assert count.provisional is True
    for year in (2020, 2021):
        rate = next(r for r in rate_recs if r.entity_raw_name == "France" and r.year == year)
        assert rate.provisional is None


def test_table9_repeated_page_header_mid_table_is_skipped():
    # The fixture plants a second year-header mid-table (the repeated page
    # header the real files print): skipped, never an error, never a second
    # header's columns shadowing the first.
    records = parse_dyb(FIXTURE9.read_bytes(), expected_table=9, block="rate")
    assert len(records) == 30  # the full set, no duplication from the repeat


def test_table9_footnotes_worksheet_rides_the_snapshot():
    footnotes = parse_dyb_footnotes(FIXTURE9.read_bytes())
    assert footnotes["notes"]["1"] == "Data refer to the de facto population."
    assert footnotes["notes"]["2"] == "Data include births registered late."


def test_star_plus_ref_marker_cell_grammar():
    # Unit pin on the v15 grammar: the starred form mirrors the diamond
    # form — '*' alone = provisional; '*47' = provisional + ref; the Roman
    # and digit forms unchanged. Each shape pinned in one place.
    from src.connectors.dyb import _parse_marker_cell
    assert _parse_marker_cell("*") == (None, None, True, None)
    assert _parse_marker_cell("*47") == (["47"], None, True, None)
    assert _parse_marker_cell("*\xa025") == (["25"], None, True, None)
    assert _parse_marker_cell("47") == (["47"], None, None, None)
    assert _parse_marker_cell("II 39") == (["39"], "II", None, None)
    # The mirror discipline: an unknown glued marker still raises loudly.
    with pytest.raises(ValueError, match="Unexpected marker cell"):
        _parse_marker_cell("x*47")


# ---------------------------------------------------------------------------
# v28.1 — Table 4's PRINTED total fertility rate (the second canonical door
# of birth_rate_fertility): `field: tfr` selects the fertility column of
# the same file the life_expectancy loop already parses.
# ---------------------------------------------------------------------------


def test_table4_tfr_measure_emits_sex_none_records():
    records = parse_table4(T4_FIXTURE.read_text(encoding="utf-8"), measure="tfr")
    france = {r.year: r.value for r in records if r.entity_raw_name == "France"}
    assert france[2020] == pytest.approx(1.79)
    assert france[2021] == pytest.approx(1.85)
    assert france[2024] == pytest.approx(1.62)
    # TFR is a synthetic measure over women's lifetimes: no split exists
    # to report, exactly the Eurostat TOTFERRT discipline — every record
    # carries sex=None, the (entity, year) merge key.
    assert all(r.sex is None for r in records)
    # one record per year row — France's five years, not ten (no male/female
    # duplication on this measure).
    assert len([r for r in records if r.entity_raw_name == "France"]) == 5


def test_table4_tfr_gap_cells_become_explicit_gap_records():
    records = parse_table4(T4_FIXTURE.read_text(encoding="utf-8"), measure="tfr")
    algeria = {r.year: r for r in records if r.entity_raw_name == "Algeria"}
    # Algeria prints "..." in the fertility column (rates only computed for
    # C/"|"-grade registration): an explicit gap with its printed marker,
    # never a zero, never dropped at parse.
    assert algeria[2020].value is None
    assert algeria[2020].missing_marker == "..."
    assert algeria[2021].value is None


def test_table4_tfr_markers_ride_as_reported():
    records = parse_table4(T4_FIXTURE.read_text(encoding="utf-8"), measure="tfr")
    by_year = {r.year: r for r in records if r.entity_raw_name == "Czechia"}
    # footnote ref beside the value...
    assert by_year[2020].footnote_refs == ["4"]
    # ...the Roman reference range (a multi-year rate period)...
    assert by_year[2021].reference_range == "IV"
    # ...and the "*" provisional flag, all as printed.
    assert by_year[2022].provisional is True
    france = {r.year: r for r in records if r.entity_raw_name == "France"}
    assert france[2021].reference_range == "V"
    assert france[2021].footnote_refs == ["5"]
    # NO quality_code on this measure: the C/U/| codes describe the
    # births/deaths blocks, not the fertility column (the LE precedent).
    assert all(r.quality_code is None for r in records)


def test_table4_tfr_refuses_a_missing_fertility_header():
    # A Table 4 without the "Total fertility" column at 21 must refuse
    # loudly when asked for the tfr measure — a future renumbering that
    # drops the column must never silently emit gaps.
    text = T4_FIXTURE.read_text(encoding="utf-8").replace("Total fertility rate", "Indice di fecondit\u00e0")
    with pytest.raises(ValueError, match="TFR header signature"):
        parse_table4(text, measure="tfr")


def test_table4_le_measure_ignores_the_tfr_column():
    # The default (LE) measure is untouched by the fertility column's
    # presence: same records, same sexes, no TFR value leaks into a
    # life-expectancy point.
    records = parse_table4(T4_FIXTURE.read_text(encoding="utf-8"))
    assert all(r.sex in ("male", "female") for r in records)
    france = {(r.year, r.sex): r.value for r in records if r.entity_raw_name == "France"}
    assert france[(2020, "male")] == pytest.approx(79.1)
    assert france[(2024, "female")] == pytest.approx(86.1)


def test_parse_dyb_dispatches_table4_tfr_block():
    records = parse_dyb(T4_FIXTURE.read_bytes(), expected_table=4, block="tfr")
    assert all(r.sex is None for r in records)
    assert {r.entity_raw_name for r in records} == {"Algeria", "Czechia", "France"}
    # and the historical default (no field / "rate") still parses the LE pair
    le = parse_dyb(T4_FIXTURE.read_bytes(), expected_table=4, block="rate")
    assert all(r.sex in ("male", "female") for r in le)
