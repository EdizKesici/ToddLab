"""United Nations Demographic Yearbook (DYB) connector — the collector tier.

WHAT THIS SOURCE IS
The DYB is what docs/the-measurement-problem.md calls a *collector*: national
official statistics, republished by the UN Statistics Division as reported by
each country — no re-modeling, no cross-country harmonization of definitions.
The collector's own quality annotations travel WITH the numbers (per the
Table 15 technical notes, 2024 edition):

- a per-country quality code: "C" = at least 90 per cent complete,
  "U" = incomplete, "|" = reliable but not from civil registration,
  "..." = completeness unknown;
- footnote markers per row, with the footnote texts in a second worksheet
  (or, in the binary editions, glued to the country name: "Botswana2");
- missing values shown as "..." or "-" — never interpolated, never zero;
- an editorial rule the notes state openly: rates are only computed for
  "C"/"|" data; "U"/"..." data appears with counts but no rate.

That rule is why, e.g., Algeria's row carries infant-death counts with "..."
in every rate cell. The collector degrades honestly instead of inventing.
Its coverage is also honestly partial (Russia, the US, China and the UK are
absent from Table 15 2024 — questionnaire responses, not data gaps); the
coverage report is expected to expose this, not hide it.

THE EDITION LOOP (P1, verified live 2026-09-06)
Per-edition, per-table files exist for editions 2011-2024 — but not in one
place, format or URL. Three eras, all verified against the live servers:

- 2011-2014: legacy site, SpreadsheetML XML disguised as .xls
  https://unstats.un.org/unsd/demographic/products/dyb/dyb{edition}/Table{NN}.xls
  Windows: 2010-2014, 2009-2013, 2008-2012, 2007-2011.
- 2015: the index page's per-table links are DEAD (they return an HTML 404 —
  the edition exists as a PDF only). build_url() refuses "2015/..." loudly
  rather than letting a config silently fetch an error page.
- 2016, 2017, 2021, 2022, 2023: modern site, BINARY BIFF .xls (OLE2 magic)
  https://unstats.un.org/unsd/demographic-social/products/dyb/documents/DYB{edition}/table{NN}.xls
  Parsed with xlrd (optional dependency, imported lazily): the only BIFF-era
  quirks are years/counts arriving as floats (2018.0) and footnote
  references glued to country names ("Botswana2") — both normalized here.
  The 2016 files specifically are FILEPASS-encrypted (RC4, unknown
  password — verified with msoffcrypto-tool: not the empty password;
  probably a broken artifact of that era of the site, like 2015's dead
  links): unusable as served, and deliberately NOT wired. Zero coverage
  loss: its 2012-2016 window is covered by editions 2014 (2010-2014) and
  2017 (2013-2017); only that one vintage's re-report is absent.
- 2018, 2019, 2020, 2024: modern site, SpreadsheetML XML with UTF-8 BOM.

Iterating the 12 wired editions (2011-2014 + 2017-2024) reconstructs a
per-country as-reported series over 2007-2024; consecutive editions overlap
(2017 covers 2013-2017, 2018 covers 2014-2018, ...) and merge.py arbitrates
overlaps WITHIN the collector tier by priority (config rule: later edition =
later vintage = higher priority, the standard vintage discipline).

WHAT THE PARSER ACCEPTS (dispatch is on the file's OWN title, not the
config's claim): a file whose title row says "15." goes to the Table 15
parser (infant deaths + IMR, wide layout: year-header of merged cells,
alternating number/rate blocks), "4." to the Table 4 parser (vital-statistics
summary + life expectancy at birth, long layout: one row per country-year).
The requested table number from the source_ref is cross-checked against the
title — a mismatch raises. Any other layout surprise raises: the project
rule is to fail loudly rather than silently mis-parse.

TABLE 4 / LIFE EXPECTANCY — the sex dimension (ADR-0008 discipline)
Table 4 prints life expectancy at birth for Male and Female separately
(columns 17 and 19, stable across all XLS editions 2011-2024) — there is NO
"both sexes" column. Averaging the two printed values would be a derivation,
and the canonical tier reports, it does not derive. So every Table 4 record
carries sex="male"|"female" through RawRecord/NormalizedPoint/merged/dist;
the (entity, year, sex) triple is the merge key. The harmonized witness
(OWID, both-sexes) stays comparable at the series level, not pointwise.

KNOWN SCOPE LIMITS (deliberate — see docs/adr/0007-source-of-record-and-witnesses.md):
- Table 15: only "Total" residence rows are emitted; the Urban/Rural
  breakdown needs a dimension field in the raw schema (phase 2);
- Table 4 life-expectancy points carry NO quality_code: the C/U/| codes
  printed on that table describe the BIRTHS / DEATHS / INFANT-DEATHS
  columns, and attaching them to the LE columns would be an
  interpretation, not a report. The LE's own as-reported markers — the
  Roman-numeral reference range and the footnote refs — ARE carried;
- the DYB's own quality annotations are captured as-reported since P2
  (see RawRecord's field docs): quality codes, footnote refs (+ their
  texts from the Footnotes worksheet, joined into the dist), the LE
  reference range, the printed missing markers, the "*" provisional
  flag. Nothing is normalized away, nothing is interpreted;
- `field` selects the value block on Table 15: "rate" (default; IMR per
  1,000 live births) or "number" (registered infant deaths); ignored on
  Table 4 (both sexes are always emitted);
- entity names in the DYB are bilingual ("Algeria - Algérie") and, in the
  BIFF editions, footnote-suffixed ("Algeria - Algérie1"): the parser
  keeps the English part and CAPTURES the footnote digits (they annotate
  the country's data as printed — they ride the records' footnote_refs).
  Anything that doesn't resolve lands in {indicator}.unresolved.json —
  the pipeline's designed behaviour, not a connector bug.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from src.connectors.base import Connector, RawFetchResult, RawRecord

DYB_TABLE_URL_MODERN = (
    "https://unstats.un.org/unsd/demographic-social/products/dyb"
    "/documents/DYB{edition}/table{table}.xls"
)
DYB_TABLE_URL_LEGACY = (
    "https://unstats.un.org/unsd/demographic/products/dyb"
    "/dyb{edition}/Table{table}.xls"
)

_SSN = "{urn:schemas-microsoft-com:office:spreadsheet}"
_SOURCE_REF_RE = re.compile(r"^(?P<edition>20\d{2})/table(?P<table>\d{2})$")
# DYB's markers for "no value here": "..." = data not available; "-" = not
# applicable/nil (seen in the 2018-2020 editions' count blocks). Both become
# value=None — an explicit gap, never zero, never interpolated — and the
# printed marker itself rides the record (missing_marker) since P2.
_MISSING = frozenset({"...", "-"})
_ROW_LABELS = ("total", "urban", "rural")
# BIFF-era files report years and counts as floats and glue footnote
# references to country names ("Botswana2"): both normalized on ingestion.
_OLE2_MAGIC = b"\xd0\xcf\x11\xe0"
_FOOTNOTE_SUFFIX = re.compile(r"\d+$")
# The grammar of a DYB marker cell (the cell immediately right of a value
# cell): "*" = provisional; bare digits = footnote reference(s); a Roman
# numeral = the reference-period width of the life-expectancy value (Table
# 4 only — legend b: "a reference year of 2005 and a range of V years
# means the reference period is 2001-2005"); a Roman numeral + a space +
# digits = both at once ("II 39", "X\xa026" — seen in real editions).
_ROMAN_RANGE_RE = re.compile(r"^([IVXL]+)(?:[\s\xa0]+(\d+))?$")
# Footnotes-worksheet grammar: one row = one cell whose text starts with
# the marker — legends use "a\n..." / "b\n..." / "*\n..." (SpreadsheetML)
# or "a ..." (BIFF), numbered notes "1\xa0Data..." / "1 Data...".
_FN_NOTE_RE = re.compile(r"^(\d+)\s+(.+)$", re.S)
_FN_SPACES = re.compile(r"[ \t\xa0]+")

# Table 4 column map — verified identical across ALL XLS editions 2011-2024
# (SpreadsheetML and BIFF alike). Derived from the merged header rows, but
# asserted, not trusted: the parser refuses to run if the header signature
# (Life expectancy / Male / Female) is not where 17/19 say it is.
_T4_LE_MALE_COL = 17
_T4_LE_FEMALE_COL = 19
# The marker cells immediately right of the LE values: footnote refs and
# the Roman-numeral reference-period range (legend b).
_T4_LE_MALE_FN_COL = 18
_T4_LE_FEMALE_FN_COL = 20


def build_url(source_ref: str) -> str:
    """'{edition}/table{NN}' -> the live file URL for that edition's era.

    2015 raises instead of building a URL: that edition's per-table XLS links
    are dead on the live site (verified 2026-09-06) and fetching them would
    return an HTML error page that a lenient parser might swallow."""
    match = _SOURCE_REF_RE.match(source_ref)
    if not match:
        raise ValueError(
            f"Invalid DYB source_ref '{source_ref}': expected '{{edition}}/table{{number}}' "
            "(e.g. '2024/table15')."
        )
    edition = int(match["edition"])
    if edition == 2015:
        raise ValueError(
            "DYB edition 2015: the per-table XLS links are dead on the live site (the "
            "edition exists as a PDF only; verified 2026-09-06). Remove this source_ref "
            "or use the PDF route — refusing to fetch an HTML error page."
        )
    if edition >= 2016:
        return DYB_TABLE_URL_MODERN.format(edition=match["edition"], table=match["table"])
    return DYB_TABLE_URL_LEGACY.format(edition=match["edition"], table=match["table"])


def _table_number_from_ref(source_ref: str) -> int:
    match = _SOURCE_REF_RE.match(source_ref)
    if not match:
        raise ValueError(f"Invalid DYB source_ref '{source_ref}'")
    return int(match["table"])


# ---------------------------------------------------------------------------
# Row extraction: bytes -> list of rows, each row a positional cell list
# (list index == true column, in BOTH formats).
# ---------------------------------------------------------------------------


def _rows_from_spreadsheetml(xml_text: str) -> list[list[str | None]]:
    root = ET.fromstring(xml_text.lstrip("\ufeff"))
    worksheet = root.find(_SSN + "Worksheet")
    if worksheet is None:
        raise ValueError("No Worksheet element: not a DYB SpreadsheetML file?")
    table = worksheet.find(_SSN + "Table")
    if table is None:
        raise ValueError("No Table element inside the worksheet")
    return [_row_values(row) for row in table.findall(_SSN + "Row")]


def _row_values(row: ET.Element) -> list[str | None]:
    """Cells of a SpreadsheetML row as a 0-based positional list, honouring
    ss:Index jumps AND MergeAcross spans (a merged cell occupies
    [position, position + MergeAcross], so the next Index-less cell starts
    after the span — the year-header rows rely on exactly this). Positional
    access is mandatory here: value columns and footnote-reference columns
    alternate, and footnote cells may hold digits (footnote numbers) that
    naive value filtering would swallow as data."""
    cells = row.findall(_SSN + "Cell")
    out: list[str | None] = []
    last = 0
    for cell in cells:
        index = cell.get(_SSN + "Index")
        if index:
            last = int(index) - 1
            if last < len(out):
                raise ValueError(
                    f"Malformed SpreadsheetML row: ss:Index {index} jumps backwards "
                    "(position already filled) — not a layout this parser knows."
                )
        # Pad up to the current position: covers BOTH Index jumps and the
        # gap left by a previous cell's MergeAcross span (the year-header
        # rows are exactly this: first cell Indexed, then merged pairs).
        while len(out) < last:
            out.append(None)
        data = cell.find(_SSN + "Data")
        out.append((data.text or "").strip() if data is not None else None)
        last += 1 + int(cell.get(_SSN + "MergeAcross") or 0)
    return out


def _rows_from_biff(data: bytes) -> list[list[str | None]]:
    """Binary .xls (BIFF) editions -> the same positional row lists as the
    XML path. xlrd is an optional dependency (only these editions need it),
    imported lazily with a loud, actionable error when absent."""
    rows, _ = _biff_rows_and_book(data)
    return rows


def _biff_rows_and_book(data: bytes) -> tuple[list[list[str | None]], object]:
    try:
        import xlrd
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise ImportError(
            "This DYB edition is a binary .xls (BIFF) file and needs the `xlrd` "
            "library (editions 2016/2017/2021-2023). Install it: pip install xlrd"
        ) from exc
    try:
        book = xlrd.open_workbook(file_contents=data)
    except Exception as exc:
        if "encrypted" in str(exc).lower():
            raise ValueError(
                "This DYB edition's .xls is FILEPASS-encrypted (the 2016 files, "
                "verified live 2026-09-06: RC4, not the empty password — a broken "
                "artifact of that era of the site, like 2015's dead links). The "
                "edition is deliberately not wired: remove its source_ref; its "
                "window is covered by the neighbouring editions."
            ) from exc
        raise
    sheet = book.sheet_by_index(0)
    rows: list[list[str | None]] = []
    for r in range(sheet.nrows):
        rows.append(_biff_row(sheet, r))
    return rows, book


def _biff_row(sheet, r: int) -> list[str | None]:
    """One BIFF sheet row -> the positional cell list, with the era's
    normalizations (empty -> None, \xa0 -> space, float years/counts -> int
    strings, dates/booleans refused)."""
    import xlrd

    row: list[str | None] = []
    for c in range(sheet.ncols):
        ctype = sheet.cell_type(r, c)
        value = sheet.cell_value(r, c)
        if ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
            row.append(None)
        elif ctype == xlrd.XL_CELL_TEXT:
            text = str(value).replace("\xa0", " ").strip()
            row.append(text or None)
        elif ctype == xlrd.XL_CELL_NUMBER:
            # Years and integral counts arrive as floats (2018.0):
            # normalize to int strings so downstream pattern checks
            # (r"\d{4}" year headers) behave exactly like the XML path.
            if float(value).is_integer():
                row.append(str(int(value)))
            else:
                row.append(str(float(value)))
        else:
            raise ValueError(
                f"Unexpected BIFF cell type {ctype} at row {r} col {c}: "
                "dates/booleans/errors are not expected in DYB data sheets."
            )
    return row


def _rows_from_bytes(data: bytes) -> list[list[str | None]]:
    if data[:4] == _OLE2_MAGIC[:4]:
        return _rows_from_biff(data)
    return _rows_from_spreadsheetml(data.decode("utf-8-sig", errors="replace"))


# ---------------------------------------------------------------------------
# Shared row-level helpers (format-agnostic).
# ---------------------------------------------------------------------------


def _is_year_header(values: list[str | None]) -> bool:
    non_empty = [v for v in values if v not in (None, "")]
    return len(non_empty) >= 6 and all(re.fullmatch(r"\d{4}", v) for v in non_empty)


def _year_header_columns(values: list[str | None]) -> list[tuple[int, int]]:
    """[(year, 0-based value column)] from the year-header row.

    In both formats the year label sits in the merged cell whose start
    position IS the column where that year's value lives in data rows (the
    merged span is [value column, footnote-reference column]). Deriving
    positions from the header (instead of hardcoding them) is what keeps the
    parser honest across editions if the year count or the leading label
    columns ever shift."""
    return [
        (int(v), i) for i, v in enumerate(values) if v is not None and re.fullmatch(r"\d{4}", v)
    ]


def _split_name_footnotes(raw: str) -> tuple[str, list[str] | None]:
    """Bilingual + footnote-suffixed country name -> (English name, refs).

    "Algeria - Algérie1" -> ("Algeria", ["1"]); "France" -> ("France", None).
    The BIFF editions glue the row's footnote reference to the country
    name — and that reference is as-reported metadata (it annotates the
    country's data as printed in that table), not noise: since P2 it is
    captured into the record's footnote_refs instead of discarded. The
    digits ride whichever part of the bilingual name the edition glued
    them to ("Botswana2" monolingual, "Algeria - Algérie1" on the French
    part, "Norfolk Island - Île Norfolk128" three digits), so the trailing
    digits are searched on the RAW string, not on the English part alone.
    """
    match = _FOOTNOTE_SUFFIX.search(raw)
    if match:
        return raw[: match.start()].split(" - ")[0].strip(), [match.group()]
    return raw.split(" - ")[0].strip(), None

def _english_name(raw: str) -> str:
    # Kept for callers that only want the name part (backward-compatible
    # seam; the parsers use _split_name_footnotes to keep the refs).
    return _split_name_footnotes(raw)[0]


def _parse_marker_cell(cell: str | None) -> tuple[list[str] | None, str | None, bool | None]:
    """A marker cell (immediately right of a value cell) ->
    (footnote_refs, reference_range, provisional), as printed.

    Grammar verified against every cached edition (see _ROMAN_RANGE_RE):
    ""/None -> nothing; "*" -> provisional; digits -> footnote ref(s);
    Roman numeral -> LE reference-period width; Roman + digits -> both.
    Anything else raises — an unknown marker is a layout change to
    investigate, never something to swallow (the loud-failure rule)."""
    if cell in (None, ""):
        return None, None, None
    text = _FN_SPACES.sub(" ", cell).strip()
    if not text:
        return None, None, None
    if text == "*":
        return None, None, True
    if text.isdigit():
        return [text], None, None
    match = _ROMAN_RANGE_RE.match(text)
    if match:
        refs = [match.group(2)] if match.group(2) else None
        return refs, match.group(1), None
    raise ValueError(
        f"Unexpected marker cell {cell!r} next to a value: not a footnote ref, "
        "not '*', not a Roman reference range — DYB layout change? Investigate "
        "before trusting this snapshot."
    )


def _merge_refs(*ref_lists: list[str] | None) -> list[str] | None:
    """Country-, row- and cell-level footnote refs, in reading order,
    deduplicated. None when the value carries none at any level."""
    merged: list[str] = []
    for refs in ref_lists:
        for ref in refs or ():
            if ref not in merged:
                merged.append(ref)
    return merged or None


def _missing_marker(value: float | None, cell: str | None) -> str | None:
    """The printed marker when a value is absent ("..." vs "-"), else None —
    the two markers MEAN different things and the difference is data."""
    if value is None and cell in _MISSING:
        return cell
    return None


def _cell_to_value(cell: str | None) -> float | None:
    if cell in (None, "") or cell in _MISSING:
        return None
    try:
        return float(cell)
    except ValueError:
        raise ValueError(
            f"Unexpected cell content {cell!r} at a value position: not a number, not '...' — "
            "DYB layout change? Investigate before trusting this snapshot."
        ) from None


def _title_table_number(rows: list[list[str | None]]) -> int:
    """The table's own title row ('15. Infant deaths and ...') is the dispatch
    ground truth — the file says what it is, we don't trust the config's
    claim blindly."""
    for values in rows[:6]:
        for v in values:
            if v:
                match = re.match(r"^(\d+)\.\s", v)
                if match:
                    return int(match.group(1))
    raise ValueError("No table-number title row found: not a DYB per-table file?")


# ---------------------------------------------------------------------------
# Table 15 — infant deaths + IMR by urban/rural residence (wide layout).
# ---------------------------------------------------------------------------


def _parse_table15_rows(rows: list[list[str | None]], *, block: str) -> list[RawRecord]:
    if block not in ("rate", "number"):
        raise ValueError(f"block must be 'rate' or 'number', got {block!r}")

    year_columns: list[tuple[int, int]] | None = None
    current_name: str | None = None
    country_refs: list[str] | None = None
    records: list[RawRecord] = []

    for values in rows:
        non_empty = [v for v in values if v not in (None, "")]
        if not non_empty:
            continue

        if _is_year_header(values):
            if year_columns is None:
                year_columns = _year_header_columns(values)
                if len(year_columns) % 2 != 0:
                    raise ValueError(
                        f"Odd number of year-header cells {year_columns}: "
                        "expected number + rate blocks"
                    )
            # A repeated page header mid-table is skipped, not an error.
            continue

        if year_columns is None:
            # Title / column-label preamble before the year header.
            continue

        # Some binary editions glue the row's footnote reference to the
        # label too ("Total11"): CAPTURE it (row-level refs) before matching
        # the residence kind.
        label_raw = (values[0] or "").split(" - ")[0].strip().lower()
        label_match = _FOOTNOTE_SUFFIX.search(label_raw)
        row_refs = [label_match.group()] if label_match else None
        label = _FOOTNOTE_SUFFIX.sub("", label_raw).strip()
        if label in _ROW_LABELS:
            if current_name is None:
                raise ValueError(f"Data row '{values[0]}' appears with no country row above it")
            if label != "total":
                continue  # Urban/Rural: needs a dimension field (phase 2), see docstring
            # The row's own quality code ("C"/"U"/"|"/"+"-prefixed...), as
            # printed — stripped of the padding the styles carry.
            quality_code = (values[1] or "").strip() or None if len(values) > 1 else None
            n = len(year_columns) // 2
            block_columns = year_columns[:n] if block == "number" else year_columns[n:]
            for year, column in block_columns:
                cell = values[column] if column < len(values) else None
                # The marker cell sits immediately right of the value cell
                # (the alternating footnote-reference column).
                marker_cell = values[column + 1] if column + 1 < len(values) else None
                cell_refs, _, provisional = _parse_marker_cell(marker_cell)
                value = _cell_to_value(cell)
                records.append(
                    RawRecord(
                        entity_raw_name=current_name,
                        iso3_raw=None,
                        year=year,
                        value=value,
                        quality_code=quality_code,
                        footnote_refs=_merge_refs(country_refs, row_refs, cell_refs),
                        missing_marker=_missing_marker(value, cell),
                        provisional=provisional,
                    )
                )
        else:
            if len(non_empty) != 1:
                raise ValueError(
                    f"Unexpected row shape {non_empty[:4]!r}: neither a data row, a country row, "
                    "nor a header — DYB layout change?"
                )
            current_name, country_refs = _split_name_footnotes(non_empty[0])

    if year_columns is None:
        raise ValueError("No year-header row found: this is not a DYB Table 15 layout")
    if not records:
        raise ValueError("No country data rows found after the year header: unexpected DYB layout")
    return records


def parse_table15(xml_text: str, *, block: str = "rate") -> list[RawRecord]:
    """Pure function: SpreadsheetML text of a DYB Table 15 -> RawRecords.

    No network access. Emits one RawRecord per (country, year, Total row)
    for the selected `block`. Missing cells become value=None — an explicit
    gap, never zero. Raises ValueError on any layout surprise."""
    return _parse_table15_rows(_rows_from_spreadsheetml(xml_text), block=block)


# ---------------------------------------------------------------------------
# Table 4 — vital statistics summary + life expectancy at birth (long layout,
# one row per country-year, LE split Male/Female in fixed columns).
# ---------------------------------------------------------------------------


def _parse_table4_rows(rows: list[list[str | None]]) -> list[RawRecord]:
    # Assert the header signature BEFORE trusting the fixed column map:
    # a row whose col 17 starts with "Life expectancy" and a row whose
    # cols 17/19 start with "Male"/"Female". Both must be found near the
    # top of the file; otherwise this is not the layout we know.
    header_signature = False
    for values in rows[:8]:
        male = values[_T4_LE_MALE_COL] if _T4_LE_MALE_COL < len(values) else None
        female = values[_T4_LE_FEMALE_COL] if _T4_LE_FEMALE_COL < len(values) else None
        if (
            male
            and female
            and male.split("\n")[0].startswith("Male")
            and female.split("\n")[0].startswith("Female")
        ):
            header_signature = True
    if not header_signature:
        raise ValueError(
            "Table 4 header signature not found (Male/Female at columns "
            f"{_T4_LE_MALE_COL}/{_T4_LE_FEMALE_COL}): layout change? Investigate."
        )

    records: list[RawRecord] = []
    current_name: str | None = None
    country_refs: list[str] | None = None
    for values in rows:
        non_empty = [v for v in values if v not in (None, "")]
        if not non_empty:
            continue
        first = values[0] if values else None
        if first and re.fullmatch(r"\d{4}", first):
            if current_name is None:
                raise ValueError(f"Year row {first!r} appears with no country row above it")
            year = int(first)

            def _le_record(sex: str, value_col: int, fn_col: int) -> RawRecord:
                """One LE point with its own as-reported markers: the value,
                the marker cell immediately right of it (footnote ref and/or
                the Roman reference-period range and/or "*"), the printed
                missing marker, and the country-level refs. NO quality_code
                by design: the C/U/| codes on this table describe the
                births/deaths/infant-deaths blocks, not the LE columns."""
                cell = values[value_col] if value_col < len(values) else None
                marker_cell = values[fn_col] if fn_col < len(values) else None
                cell_refs, reference_range, provisional = _parse_marker_cell(marker_cell)
                value = _cell_to_value(cell)
                return RawRecord(
                    entity_raw_name=current_name,
                    iso3_raw=None,
                    year=year,
                    value=value,
                    sex=sex,
                    footnote_refs=_merge_refs(country_refs, cell_refs),
                    reference_range=reference_range,
                    missing_marker=_missing_marker(value, cell),
                    provisional=provisional,
                )

            # Both sexes are always emitted, None included — a year row with
            # no printed LE value is an explicit gap, and the (entity, year,
            # sex) triple is the merge key downstream.
            records.append(_le_record("male", _T4_LE_MALE_COL, _T4_LE_MALE_FN_COL))
            records.append(_le_record("female", _T4_LE_FEMALE_COL, _T4_LE_FEMALE_FN_COL))
        elif len(non_empty) == 1:
            # Country/continent label row ("Algeria - Algérie", "AFRICA -
            # AFRIQUE"; continent rows are overwritten by the next country
            # row before any year row can attach to them).
            current_name, country_refs = _split_name_footnotes(non_empty[0])
        # Multi-cell non-year rows after the header = the bilingual header
        # bands and their repeats: skipped, not an error.

    if not records:
        raise ValueError("No year rows found after the header: unexpected DYB Table 4 layout")
    return records


def parse_table4(xml_text: str) -> list[RawRecord]:
    """Pure function: SpreadsheetML text of a DYB Table 4 -> RawRecords
    (LE at birth, one record per (country, year, sex))."""
    return _parse_table4_rows(_rows_from_spreadsheetml(xml_text))


# ---------------------------------------------------------------------------
# The Footnotes worksheet — the collector's own legend + note texts.
# ---------------------------------------------------------------------------


def _footnotes_from_rows(rows: list[list[str | None]]) -> dict | None:
    """The 'Footnotes' sheet's rows -> {"legend": {...}, "notes": {...}}.

    Grammar (verified against every cached edition, both file families —
    SpreadsheetML cells carry 'marker\ntext', BIFF cells 'marker text',
    numbered notes 'N\xa0text'):
    - legend rows: '*' provisional, 'a' the quality-code legend,
      'b' the Roman-numeral LE reference-range legend, 'italics' the
      incomplete-registration caveat;
    - numbered rows: 'N <text>' — one entry per footnote number;
    - a row that matches none of the above is a CONTINUATION of the
      previous numbered note (multi-line texts), never an error.
    Returns None when the sheet carries nothing recognizable."""
    legend: dict[str, str] = {}
    notes: dict[str, str] = {}
    last_note: str | None = None

    for values in rows:
        line = " ".join(
            str(v).replace("\n", " ") for v in values if v not in (None, "")
        )
        line = _FN_SPACES.sub(" ", line).strip()
        if not line:
            continue
        first_token = line.split()[0].upper().rstrip(":")
        if first_token in ("FOOTNOTES", "NOTES"):
            continue  # the sheet's own header band
        note_match = _FN_NOTE_RE.match(line)
        if note_match:
            last_note = note_match.group(1)
            notes[last_note] = note_match.group(2).strip()
            continue
        if line.startswith("*"):
            legend["*"] = line[1:].strip()
            last_note = None
            continue
        if line.startswith("Italics") or line.startswith("italics"):
            legend["italics"] = line
            last_note = None
            continue
        marker_match = re.match(r"^([ab])\s+(.+)$", line, re.S)
        if marker_match:
            legend[marker_match.group(1)] = marker_match.group(2).strip()
            last_note = None
            continue
        if last_note:
            # A row that is none of the above, right after a numbered note:
            # the printed text of that note continues — append it.
            notes[last_note] = (notes[last_note] + " " + line).strip()

    if not legend and not notes:
        return None
    return {"legend": legend, "notes": notes}


def _footnotes_from_bytes(data: bytes) -> dict | None:
    """Bytes of a DYB table file -> its Footnotes worksheet, or None when
    the file carries no such sheet (the refs on the points are then honest
    refs whose texts live only in the source file)."""
    if data[:4] == _OLE2_MAGIC[:4]:
        rows, book = _biff_rows_and_book(data)
        names = book.sheet_names()
        index = next((i for i, n in enumerate(names) if "footnote" in n.lower()), None)
        if index is None:
            return None
        sheet = book.sheet_by_index(index)
        return _footnotes_from_rows([_biff_row(sheet, r) for r in range(sheet.nrows)])
    root = ET.fromstring(data.decode("utf-8-sig", errors="replace").lstrip("\ufeff"))
    for worksheet in root.findall(_SSN + "Worksheet"):
        name = worksheet.get(_SSN + "Name") or ""
        if "footnote" not in name.lower():
            continue
        table = worksheet.find(_SSN + "Table")
        if table is None:
            continue
        return _footnotes_from_rows([_row_values(row) for row in table.findall(_SSN + "Row")])
    return None


# ---------------------------------------------------------------------------
# Dispatch + connector.
# ---------------------------------------------------------------------------


def parse_dyb(data: bytes, *, expected_table: int | None = None, block: str = "rate") -> list[RawRecord]:
    """Bytes of any wired DYB table file (SpreadsheetML or BIFF, any era)
    -> RawRecords. Dispatches on the file's OWN title; cross-checks the
    requested table number when given; raises on anything unknown."""
    rows = _rows_from_bytes(data)
    title_number = _title_table_number(rows)
    if expected_table is not None and title_number != expected_table:
        raise ValueError(
            f"source_ref asks for table {expected_table:02d} but the file's title says "
            f"table {title_number}: refusing to parse a different table than configured."
        )
    if title_number == 15:
        return _parse_table15_rows(rows, block=block)
    if title_number == 4:
        return _parse_table4_rows(rows)
    raise ValueError(
        f"DYB table {title_number} is not wired in this connector yet "
        "(supported: 15 = infant deaths/IMR, 4 = life expectancy at birth)."
    )


def parse_dyb_footnotes(data: bytes) -> dict | None:
    """Bytes of any wired DYB table file -> its Footnotes worksheet as
    {"legend": {...}, "notes": {...}} (see _footnotes_from_rows), or None
    when the file carries no such sheet. Pure function, no network."""
    return _footnotes_from_bytes(data)


class DybConnector(Connector):
    provider = "un_dyb"

    def __init__(self, session=None, timeout: int = 60):
        self._session = session
        self._timeout = timeout

    def fetch_raw(self, source_ref: str, indicator_id: str, field: str | None = None) -> RawFetchResult:
        import requests  # local import: keep this module importable even if `requests` is absent in pure-parsing tests

        url = build_url(source_ref)
        session = self._session or requests
        response = session.get(
            url,
            headers={"User-Agent": "toddlab-pipeline/0.1 (contact: see README)"},
            timeout=self._timeout,
        )
        response.raise_for_status()
        records = parse_dyb(
            response.content,
            expected_table=_table_number_from_ref(source_ref),
            block=field or "rate",
        )
        return RawFetchResult(
            provider=self.provider,
            source_ref=source_ref,
            indicator_id=indicator_id,
            fetched_at=RawFetchResult.now_iso(),
            source_url=url,
            records=records,
            footnotes=parse_dyb_footnotes(response.content),
        )
