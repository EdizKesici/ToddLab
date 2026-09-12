from pathlib import Path

import pytest

from src.connectors.dyb import (
    DybConnector,
    _english_name,
    _parse_table15_rows,
    _parse_table4_rows,
    build_url,
    parse_dyb,
    parse_dyb_footnotes,
    parse_table15,
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


def test_build_url_2015_refused_loudly():
    # The 2015 per-table XLS links are dead on the live site (HTML 404s);
    # fetching them would feed an error page to a lenient parser.
    with pytest.raises(ValueError, match="2015"):
        build_url("2015/table15")


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
