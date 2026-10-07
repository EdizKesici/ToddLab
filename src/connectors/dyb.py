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
- 2015: RECOVERED (v10): the edition page's own per-table links are dead
  (tiny HTML error pages — that is what kept 2015 out of the v7 loop), but
  the LEGACY pattern /dyb2015/TableNN.xls is alive on the live site
  (verified 2026-09-13 by direct download: Table04 2.2 MB, Table15 716 KB,
  Table21 468 KB, Table22 1.3 MB, all parse clean). build_url() routes
  2015 to the legacy era like 2011-2014.
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

Iterating the 13 wired editions (2011-2015 + 2017-2024) reconstructs a
per-country as-reported series over 2007-2024; consecutive editions overlap
(2017 covers 2013-2017, 2018 covers 2014-2018, ...) and merge.py arbitrates
overlaps WITHIN the collector tier by priority (config rule: later edition =
later vintage = higher priority, the standard vintage discipline).

WHAT THE PARSER ACCEPTS (dispatch is on the file's OWN title, not the
config's claim): a file whose title row says "15." goes to the Table 15
parser (infant deaths + IMR, wide layout: year-header of merged cells,
alternating number/rate blocks), "9." to the same wide layout through the
Table 9 branch (live births + crude birth rates — v15, with a content
guard on the title's own words like the 21/22 zone), "4." to the Table 4
parser (vital-statistics
summary + life expectancy at birth, long layout: one row per country-year).
The requested table number from the source_ref is cross-checked against the
title — a mismatch raises. Any other layout surprise raises: the project
rule is to fail loudly rather than silently mis-parse.

TABLE 9 / LIVE BIRTHS + CRUDE BIRTH RATES (v15, the CBR companion). The
same wide layout as Table 15 — a "Total" row per country (Urban/Rural
dropped, logged, the phase-2 residence dimension), quality-code column,
then (Number, footnote-ref) pairs for live births and (Rate, ref) pairs
for the crude birth rate per 1,000 population. Table number verified
STABLE across all 13 wired editions (2011-2015 + 2017-2024, probed live
2026-09-20) — no renumbering zone like 21/22, but the content guard keys
on the title's words anyway ("Live births and crude birth rates"): the
title is the ground truth, the number the cross-check. One marker-cell
form is Table-9-specific in practice: "*" glued to a footnote ref
("*47") on live-birth COUNT cells — the collector flags a provisional
birth count and cites its note in one cell; the grammar (and
_parse_marker_cell) accepts it as provisional + refs since v15 (26 live
occurrences across editions 2011/2017-2022, zero on rate cells). The
editorial rule for rates is the collector's own: CBR is computed only
where the completeness code allows (the same C/U/| discipline as Table
15), so "U"-coded countries print counts with "..." rates — explicit
gaps, kept as printed. NOTE the boundaries: the window is 5 years per
edition exactly like Table 15, and Table 17's maternal RATES are
COMPUTED by the UNSD from these same Table 9 births — the collector's
own cross-table dependency, one reason this table is the canonical CBR
source (the other: the WDI CBR door is a WPP-derived series, witness
material by constitution).

TABLE 4 / LIFE EXPECTANCY — the sex dimension (ADR-0008 discipline)
Table 4 prints life expectancy at birth for Male and Female separately
(columns 17 and 19, stable across all XLS editions 2011-2024) — there is NO
"both sexes" column. Averaging the two printed values would be a derivation,
and the canonical tier reports, it does not derive. So every Table 4 record
carries sex="male"|"female" through RawRecord/NormalizedPoint/merged/dist;
the (entity, year, sex) triple is the merge key. The harmonized witness
(OWID, both-sexes) stays comparable at the series level, not pointwise.

TABLE 21/22 — LIFE EXPECTANCY AT SPECIFIED AGES (v10, the renumbering
zone). "Life expectancy at specified ages for each sex: latest available
year" swaps table numbers with the 5qx probabilities depending on edition
parity (verified across all 13 wired editions): LE-by-age is table 21 in
EVEN editions, table 22 in ODD ones. The dispatch therefore keys on the
file's OWN title TEXT ("Life expectancy at specified ages"), never on the
number alone: a config that asks for table 21 in an odd edition fetches
the 5qx file, which shares the exact same layout (country -> year ->
Male/Female rows, ages across columns) — a number-only dispatch would
mis-parse it silently. The content guard raises with a pointer to the
correct number for that edition's parity.

Layout (identical in both file formats): an age-header row (ages 0, 5,
..., 100 across 21 columns — asserted EXACTLY, not trusted), then
per-country blocks: a country row, a reference-year row (a single year,
or an explicit period "2012 - 2015"), a Male row and a Female row (sex
in ROWS on this table, unlike Table 4's columns). The year of a reference
period is its END year — the same convention as Table 4's Roman-numeral
legend ("a reference year of 2005 and a range of V years means the
reference period is 2001-2005") — and the printed period rides the
points' reference_range. `field` selects the AGE column ("60" for
LE-60); the snapshot holds that column's records only — the other 20
ages are in the fetched XLS and nowhere else, so wiring one is another
indicator + config + a re-fetch of the same stable URL (the same
one-block-at-a-time scope as Table 15's rate/number and Table 17's).

THE CROSS-SECTION SEMANTICS: each edition prints each country's LATEST
available year only. The canonical series is therefore a STACK OF
CROSS-SECTIONS across the 13 editions, not an annual panel: a country
that stops responding to the questionnaire freezes (Russia's last
LE-by-age row is 2012 in every edition 2013-2024 — the merge collapses
those repeats into ONE point, later edition wins), and a country
responding annually contributes one newer year per edition. A block
whose age column prints "..." is an explicit gap kept as printed — e.g.
France in the 2024 edition carries TWO blocks: the full 2020 life table
and a 2024 block where only age 0 is published (the rest "..." — the
collector's own not-yet-computed degradation, materialized as a 2024 gap
for LE-60). Like Table 4, this table prints NO quality code and NO
marker cells next to the values: the C/U/| legend does not apply to it,
and an unexpected marker in a value cell raises (loud failure).

The BIFF editions glue a footnote reference to the YEAR row ("20103" =
2010 + note 3 — DYB years are always exactly 4 digits, so the split is
deterministic) and to country names (the shared _split_name_footnotes
path); both ride the records' footnote_refs.

TABLE 17 / MATERNAL MORTALITY (P3b) — the same collector, one more measure
pair. Per country: a "Number - Nombre" row (registered maternal deaths —
provided to the UNSD via the WHO, cause-of-death statistics) and, where the
collector's editorial rule allows it, a "Rate - Taux" row (maternal
mortality ratio per 100 000 live births, COMPUTED by the UN Statistics
Division from the counts and Table 9 births — we republish the collector's
published figure, we do not re-derive it). The printed rule is the
collector's own honest degradation: no ratio where the counts are judged
incomplete (the "U"/"..." codes) or births unavailable — those rows print
counts with "..." rates, and the parser keeps them as explicit gaps. Two
Table-17-specific as-reported annotations travel with the points: the
"\u2666" marker (ratio based on 30 or fewer maternal deaths — small_base)
and the per-year footnote refs (which for this table often restate the
quality code, e.g. Russia's Chechnya-exclusion note on its 2001-2003
ratios). `field` selects the block exactly like Table 15: "rate" (default)
or "number". The table number is STABLE across editions 2011-2024 — the
21/22 renumbering zone does not reach this far down the DYB table order.

KNOWN SCOPE LIMITS (deliberate — see docs/adr/0007-source-of-record-and-witnesses.md):
- Table 15: only "Total" residence rows are emitted; the Urban/Rural
  breakdown needs a dimension field in the raw schema (phase 2);
- Table 21/22: `field` selects the AGE column ("60" for LE-60); the 20
  other ages stay unwired until another indicator asks for them — the
  snapshots hold the selected column's records only, so wiring another
  age means re-fetching the same table (the same one-measure-at-a-time
  scope as Table 15's Urban/Rural and Table 17's Number block);
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
  1,000 live births) or "number" (registered infant deaths); on Table 4
  it selects the printed measure — "tfr" (v28.1: the total fertility
  rate column, sex=None) or anything else (the historical Male/Female
  life-expectancy pair);
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
# digits = both at once ("II 39", "X\xa026" — seen in real editions); the
# diamond "\u2666" = Table 17's small-numbers marker (ratio based on 30
# or fewer maternal deaths), alone or glued to a footnote ref ("♦",
# "♦1" — both verified in every wired edition); and "*" + digits glued
# = provisional AND a footnote ref at once ("*47", "*25" — found on
# Table 9's live-birth COUNT cells in the 2026-09-20 Table 9 loop probe,
# 26 occurrences across editions 2011/2017-2022: the collector flags a
# provisional birth count AND points at its note in the same cell). The
# starred form mirrors the diamond form exactly: provisional=True with
# the digits riding footnote_refs.
_ROMAN_RANGE_RE = re.compile(r"^([IVXL]+)(?:[\s\xa0]+(\d+))?$")
_DIAMOND_REF_RE = re.compile(r"^♦[\s\xa0]*(\d+)?$")
_STAR_REF_RE = re.compile(r"^\*[\s\xa0]*(\d+)?$")
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
# v28.1: the Total fertility rate column of the SAME Table 4 ("Vital
# statistics summary and life expectancy at birth") — immediately right
# of the LE pair's own marker columns. The TFR is PRINTED by the collector
# ("Total fertility rate / L'indice synthétique de fécondité", verified
# live at column 21 in every wired edition 2011-2024, SpreadsheetML and
# BIFF alike — the same era-proof layout the LE map documents), which is
# the same printed-value status as Table 17's maternal ratios and Table
# 9's crude birth rates: the collector computes it from the registered
# births by mother's age, and the anti-derivation rule holds on our side
# (summing Table 10's age-specific rates would be the forbidden
# derivation — v14's finding, which probed Table 10 and missed that
# Table 4 prints the finished rate; corrected in v28.1). The marker cell
# at col 22 carries footnote refs (Japan 2020-2023: '85', Korea
# 2020-2023: '102' — read live on the 2024 edition) and, where a small
# population's rate covers a multi-year reference period, the Roman
# range rides as on the LE columns.
_T4_TFR_COL = 21
_T4_TFR_FN_COL = 22


def build_url(source_ref: str) -> str:
    """'{edition}/table{NN}' -> the live file URL for that edition's era.

    2011-2015 use the legacy pattern: 2015's own index links are dead
    (tiny HTML error pages) but the legacy /dyb2015/TableNN.xls files are
    alive — recovered in v10, verified by direct download 2026-09-13."""
    match = _SOURCE_REF_RE.match(source_ref)
    if not match:
        raise ValueError(
            f"Invalid DYB source_ref '{source_ref}': expected '{{edition}}/table{{number}}' "
            "(e.g. '2024/table15')."
        )
    edition = int(match["edition"])
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
        # itertext(), not .text: the SpreadsheetML editions 2011-2015 + 2024
        # wrap their country-level (and t21 year-row) footnote references in
        # <html:Sup>NN</html:Sup> child elements — plain .text stops at the
        # first child and silently DROPPED them (65 Sup in t21 2024, 90 in
        # t15 2024, 26 in t4 2024, 6 in t17 2024; found via the v10 fixture
        # never lying the way a summary can). The captured text becomes
        # "Algeria - Algérie1", exactly the BIFF glued form downstream
        # code already knows how to split.
        out.append("".join(data.itertext()).strip() if data is not None else None)
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


def _parse_marker_cell(cell: str | None) -> tuple[list[str] | None, str | None, bool | None, bool | None]:
    """A marker cell (immediately right of a value cell) ->
    (footnote_refs, reference_range, provisional, small_base), as printed.

    Grammar verified against every cached edition (see _ROMAN_RANGE_RE):
    ""/None -> nothing; "*" -> provisional; digits -> footnote ref(s);
    Roman numeral -> LE reference-period width; Roman + digits -> both;
    "\u2666" -> the Table 17 small-numbers marker ("Ratios based on 30 or
    fewer maternal deaths are identified by the symbol ♦" — Notes17),
    alone or with a footnote ref glued ("♦", "♦1" — 3336 + 501 real
    occurrences across the 12 wired Table 17 editions).
    Anything else raises — an unknown marker is a layout change to
    investigate, never something to swallow (the loud-failure rule)."""
    if cell in (None, ""):
        return None, None, None, None
    text = _FN_SPACES.sub(" ", cell).strip()
    if not text:
        return None, None, None, None
    if text == "*":
        return None, None, True, None
    if text == "\u2666":
        return None, None, None, True
    diamond_match = _DIAMOND_REF_RE.match(text)
    if diamond_match:
        refs = [diamond_match.group(1)] if diamond_match.group(1) else None
        return refs, None, None, True
    star_match = _STAR_REF_RE.match(text)
    if star_match:
        # "*47" on a live-birth count: the collector marks the value
        # provisional AND cites its footnote in one cell — provisional=True
        # with the digits riding footnote_refs, the diamond form's mirror.
        refs = [star_match.group(1)] if star_match.group(1) else None
        return refs, None, True, None
    if text.isdigit():
        return [text], None, None, None
    match = _ROMAN_RANGE_RE.match(text)
    if match:
        refs = [match.group(2)] if match.group(2) else None
        return refs, match.group(1), None, None
    raise ValueError(
        f"Unexpected marker cell {cell!r} next to a value: not a footnote ref, not '*' (alone or with refs), "
        "not '♦' (alone or with refs), not a Roman reference range — "
        "DYB layout change? Investigate before trusting this snapshot."
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


def _title_row_value(rows: list[list[str | None]]) -> str:
    """The table's own title row ('15. Infant deaths and ...') — the
    dispatch ground truth, number AND text (the 21/22 renumbering zone
    keys on the title's WORDS: the same number holds the LE-by-age table
    in one edition and the 5qx probabilities in the next)."""
    for values in rows[:6]:
        for v in values:
            if v:
                if re.match(r"^\d+\.\s", v):
                    return v.strip()
    raise ValueError("No table-number title row found: not a DYB per-table file?")


def _title_table_number(rows: list[list[str | None]]) -> int:
    """The table's own title number — the file says what it is, we don't
    trust the config's claim blindly."""
    title = _title_row_value(rows)
    return int(re.match(r"^(\d+)\.", title).group(1))


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
                cell_refs, _, provisional, _small = _parse_marker_cell(marker_cell)
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
# Table 17 — maternal deaths + maternal mortality ratios (one "Number" row
# and/or one "Rate" row per country, years across columns).
# ---------------------------------------------------------------------------


# Bilingual row labels of the two measure blocks ("Number - Nombre",
# "Rate - Taux"): the English half selects the block.
_T17_LABELS = frozenset({"number", "rate"})


def _parse_table17_rows(rows: list[list[str | None]], *, block: str) -> list[RawRecord]:
    """DYB Table 17 rows -> RawRecords for the selected block.

    Layout (verified against every wired edition, 2011-2024 — the table
    number is STABLE across editions, unlike the 21/22 zone): a country row
    (single non-empty cell), then up to two data rows labeled "Number -
    Nombre" (registered maternal deaths) and "Rate - Taux" (maternal
    mortality ratio per 100 000 live births — the ratio is computed by the
    UN Statistics Division from the country's counts and Table 9 births,
    per the printed Notes17; we republish the collector's own published
    figure, we do not re-derive it). Column 1 carries the row's quality
    code (same C/U/|/+ legend as Table 15; "..." = code not available,
    kept as printed), then (value, footnote-ref) pairs across the year
    columns. The "\u2666" marker on rate cells = ratio based on 30 or
    fewer maternal deaths (small_base). Rates are printed only where the
    collector judges the data reliable enough — the missing rate rows are
    the collector's honest degradation, kept as explicit gaps.
    """
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

        # Year-header row: the Table 17 header carries label cells
        # ("Continent and country or area", "Co-de") BESIDE the years, so
        # Table 15's all-years _is_year_header() gate does not apply — a
        # row with at least six 4-digit cells IS the year header (its
        # positions are the value columns, the merged-cell convention).
        year_cells = _year_header_columns(values)
        if len(year_cells) >= 6:
            if year_columns is None:
                year_columns = year_cells
            # A repeated page header mid-table is skipped, not an error.
            continue

        if year_columns is None:
            # Title / column-label preamble before the year header.
            continue

        # BIFF editions can glue a footnote digit to the label too —
        # capture it (row-level refs) before matching the block.
        label_raw = (values[0] or "").split(" - ")[0].strip().lower()
        label_match = _FOOTNOTE_SUFFIX.search(label_raw)
        row_refs = [label_match.group()] if label_match else None
        label = _FOOTNOTE_SUFFIX.sub("", label_raw).strip()
        if label in _T17_LABELS:
            if current_name is None:
                raise ValueError(f"Data row '{values[0]}' appears with no country row above it")
            if label != block:
                continue  # the other measure's rows: not wired for this source
            quality_code = (values[1] or "").strip() or None if len(values) > 1 else None
            for year, column in year_columns:
                cell = values[column] if column < len(values) else None
                marker_cell = values[column + 1] if column + 1 < len(values) else None
                cell_refs, _range, provisional, small_base = _parse_marker_cell(marker_cell)
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
                        small_base=small_base,
                    )
                )
        elif len(non_empty) == 1:
            # Country/continent label row; continent rows are overwritten
            # by the next country row before any data row can attach.
            current_name, country_refs = _split_name_footnotes(non_empty[0])
        else:
            raise ValueError(
                f"Unexpected row shape {non_empty[:4]!r}: neither a data row, a country row, "
                "nor a header — DYB layout change?"
            )

    if year_columns is None:
        raise ValueError("No year-header row found: this is not a DYB Table 17 layout")
    if not records:
        raise ValueError("No country data rows found after the year header: unexpected DYB layout")
    return records


def parse_table17(xml_text: str, *, block: str = "rate") -> list[RawRecord]:
    """Pure function: SpreadsheetML text of a DYB Table 17 -> RawRecords
    (maternal mortality ratio by default, registered counts with
    block='number')."""
    return _parse_table17_rows(_rows_from_spreadsheetml(xml_text), block=block)


# ---------------------------------------------------------------------------
# Table 21/22 — life expectancy at specified ages, by sex (the renumbering
# zone: one country block = reference-year row + Male row + Female row,
# the 21 age columns 0, 5, ..., 100 across).
# ---------------------------------------------------------------------------

# The 21 age columns, asserted exactly (verified across all 13 wired
# editions, both file formats): a deviation is a layout change to
# investigate, never something to reinterpret.
_T21_AGES = tuple(range(0, 101, 5))
# The reference-year row: a 4-digit year, optionally an explicit period
# "2012 - 2015". The BIFF editions glue a footnote reference to it
# ("20103" = 2010 + note 3): a DYB year is always exactly 4 digits, so the
# year/ref split is deterministic. The year of a period is its END year
# (Table 4's Roman-numeral convention).
_T21_YEAR_RE = re.compile(
    r"(?P<y1>(?:19|20)\d{2})(?P<g1>\d{1,2})?"
    r"(?:\s*-\s*(?P<y2>(?:19|20)\d{2})(?P<g2>\d{1,2})?)?"
)


def _t21_age_columns(values: list[str | None]) -> dict[int, int] | None:
    """The row's age map {age: 0-based column} when the row IS the age
    header (its non-empty cells past column 0 are exactly the ages
    0, 5, ..., 100); None otherwise. Used to LOCATE the header (once, near
    the top) and to SKIP its mid-table repeats (the same repeated-page-
    header leniency as Tables 15/17). A data row cannot match: LE values
    would have to reproduce the exact 0, 5, ..., 100 arithmetic sequence."""
    ages: list[int] = []
    columns: list[int] = []
    for j, cell in enumerate(values[1:]):
        label = (cell or "").strip()
        if not label:
            continue
        if not label.isdigit():
            return None
        ages.append(int(label))
        columns.append(j + 1)
    if tuple(ages) != _T21_AGES:
        return None
    return dict(zip(_T21_AGES, columns))


def _sex_label(cell: str | None) -> str | None:
    """'Male\n-\nHommes' (SpreadsheetML) or 'Male - Hommes' (BIFF) ->
    'male' / 'female'; None for anything else (the caller decides what a
    non-sex row is). 'Female' is matched on its own head token, never by
    substring, so it can never collide with 'Male'."""
    if not cell:
        return None
    head = str(cell).split("\n")[0].split(" - ")[0].strip()
    return head.lower() if head in ("Male", "Female") else None


def _parse_table21_rows(rows: list[list[str | None]], *, age: str) -> list[RawRecord]:
    """DYB Table 21/22 rows -> RawRecords for the selected `age` column.

    Layout and cross-section semantics: see the module docstring's TABLE
    21/22 section. One record per (country block, sex row): the value at
    the requested age's column, the block's reference year (END year of a
    printed period), the printed period on reference_range, the country-
    and year-level footnote refs (BIFF gluing), and '...' kept as an
    explicit gap. No quality_code, no marker cells on this table — an
    unexpected marker in a value cell raises (loud failure)."""
    age_header: dict[int, int] | None = None
    header_index: int | None = None
    for i, values in enumerate(rows):
        columns = _t21_age_columns(values)
        if columns is not None:
            age_header = columns
            header_index = i
            break
    if age_header is None:
        raise ValueError("No age-header row (0, 5, ..., 100) found: not a DYB Table 21/22 layout")
    try:
        age_value = int(age)
    except (TypeError, ValueError):
        age_value = -1
    if age_value not in age_header:
        raise ValueError(
            f"Table 21/22 selects its value column by AGE ('60', '65', ... — the "
            f"indicator config's `field`); got {age!r}. Available ages: "
            f"{', '.join(str(a) for a in _T21_AGES)}."
        )
    column = age_header[age_value]

    records: list[RawRecord] = []
    current_name: str | None = None
    country_refs: list[str] | None = None
    current_year: int | None = None
    current_range: str | None = None
    year_refs: list[str] | None = None

    for values in rows[header_index + 1 :]:
        non_empty = [v for v in values if v not in (None, "")]
        if not non_empty:
            continue
        if _t21_age_columns(values) is not None:
            # A repeated page header mid-table is skipped, not an error.
            continue

        first = values[0]
        year_match = _T21_YEAR_RE.fullmatch((first or "").strip()) if first else None
        if year_match:
            if current_name is None:
                raise ValueError(f"Year row {first!r} appears with no country row above it")
            if len(non_empty) != 1:
                raise ValueError(
                    f"Year row {first!r} carries unexpected extra cells "
                    f"{non_empty[1:3]!r}: DYB layout change?"
                )
            if year_match["y2"] is not None:
                current_year = int(year_match["y2"])  # END of the reference period
                current_range = f"{year_match['y1']} - {year_match['y2']}"
            else:
                current_year = int(year_match["y1"])
                current_range = None
            year_refs = [ref for ref in (year_match["g1"], year_match["g2"]) if ref] or None
            continue

        sex = _sex_label(first)
        if sex is not None:
            if current_name is None:
                raise ValueError(f"Sex row {first!r} appears with no country row above it")
            if current_year is None:
                raise ValueError(f"Sex row {first!r} appears with no year row above it")
            cell = values[column] if column < len(values) else None
            value = _cell_to_value(cell)
            records.append(
                RawRecord(
                    entity_raw_name=current_name,
                    iso3_raw=None,
                    year=current_year,
                    value=value,
                    sex=sex,
                    footnote_refs=_merge_refs(country_refs, year_refs),
                    reference_range=current_range,
                    missing_marker=_missing_marker(value, cell),
                )
            )
            continue

        # Neither a year row nor a sex row: a country/continent label row
        # (continent rows are overwritten by the next country row before
        # any sex row can attach to them).
        if len(non_empty) != 1:
            raise ValueError(
                f"Unexpected row shape {non_empty[:4]!r}: neither a data row, a country row, "
                "nor a header — DYB layout change?"
            )
        current_name, country_refs = _split_name_footnotes(non_empty[0])
        # A new country row invalidates any year waiting for its sex rows.
        current_year = None
        current_range = None
        year_refs = None

    if not records:
        raise ValueError("No sex data rows found after the age header: unexpected DYB layout")
    return records


def parse_table21(xml_text: str, *, age: str) -> list[RawRecord]:
    """Pure function: SpreadsheetML text of a DYB Table 21/22 (life
    expectancy at specified ages) -> RawRecords for the selected age."""
    return _parse_table21_rows(_rows_from_spreadsheetml(xml_text), age=age)


# ---------------------------------------------------------------------------
# Table 4 — vital statistics summary + life expectancy at birth (long layout,
# one row per country-year, LE split Male/Female in fixed columns).
# ---------------------------------------------------------------------------


def _parse_table4_rows(rows: list[list[str | None]], *, measure: str = "le") -> list[RawRecord]:
    # Assert the header signature BEFORE trusting the fixed column map:
    # a row whose col 17 starts with "Life expectancy" and a row whose
    # cols 17/19 start with "Male"/"Female". Both must be found near the
    # top of the file; otherwise this is not the layout we know. For the
    # TFR measure (v28.1) the col-21 "Total fertility" header is asserted
    # as well — a future renumbering that drops the fertility column must
    # refuse loudly, not silently emit gaps.
    header_signature = False
    tfr_header_signature = False
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
        tfr = values[_T4_TFR_COL] if _T4_TFR_COL < len(values) else None
        if tfr and str(tfr).split("\n")[0].startswith("Total fertility"):
            tfr_header_signature = True
    if not header_signature:
        raise ValueError(
            "Table 4 header signature not found (Male/Female at columns "
            f"{_T4_LE_MALE_COL}/{_T4_LE_FEMALE_COL}): layout change? Investigate."
        )
    if measure == "tfr" and not tfr_header_signature:
        raise ValueError(
            "Table 4 TFR header signature not found (\"Total fertility\" at column "
            f"{_T4_TFR_COL}): this edition's Table 4 does not print the fertility "
            "column — check the edition before wiring it."
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
                cell_refs, reference_range, provisional, _small = _parse_marker_cell(marker_cell)
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

            def _tfr_record() -> RawRecord:
                """One printed TFR point (v28.1): sex=None by construction
                (a synthetic measure over women's reproductive lifetimes
                has no split to report — the same discipline the Eurostat
                TOTFERRT records follow), the marker cell immediately
                right of the value carrying its footnote refs (and the
                Roman reference range where the collector prints one), the
                printed missing marker, and the country-level refs. NO
                quality_code by design — the C/U/| codes describe the
                births/deaths/infant-deaths blocks, not the fertility
                column (the LE columns' own precedent)."""
                cell = values[_T4_TFR_COL] if _T4_TFR_COL < len(values) else None
                marker_cell = values[_T4_TFR_FN_COL] if _T4_TFR_FN_COL < len(values) else None
                cell_refs, reference_range, provisional, _small = _parse_marker_cell(marker_cell)
                value = _cell_to_value(cell)
                return RawRecord(
                    entity_raw_name=current_name,
                    iso3_raw=None,
                    year=year,
                    value=value,
                    sex=None,
                    footnote_refs=_merge_refs(country_refs, cell_refs),
                    reference_range=reference_range,
                    missing_marker=_missing_marker(value, cell),
                    provisional=provisional,
                )

            if measure == "tfr":
                # One record per year row, value=None included — a year the
                # collector prints with "..." (rates only computed for
                # C/"|"-grade registration) is an explicit gap, and the
                # (entity, year) key with sex=None is the merge key
                # downstream, exactly the Table 15 discipline.
                records.append(_tfr_record())
            else:
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


def parse_table4(xml_text: str, *, measure: str = "le") -> list[RawRecord]:
    """Pure function: SpreadsheetML text of a DYB Table 4 -> RawRecords.

    measure="le" (the default): life expectancy at birth, one record per
    (country, year, sex). measure="tfr" (v28.1): the printed total
    fertility rate, one record per (country, year) with sex=None."""
    return _parse_table4_rows(_rows_from_spreadsheetml(xml_text), measure=measure)


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
    requested table number when given; raises on anything unknown.

    For Tables 15/17 `block` selects the measure ("rate"/"number"); for
    Table 21/22 it selects the AGE column ("60", "65", ...); for Table 4
    (v28.1) it selects the printed measure — "tfr" for the total
    fertility rate column, anything else (the historical default
    "rate"/None) for the Male/Female life-expectancy pair."""
    rows = _rows_from_bytes(data)
    title = _title_row_value(rows)
    title_number = int(re.match(r"^(\d+)\.", title).group(1))
    if expected_table is not None and title_number != expected_table:
        raise ValueError(
            f"source_ref asks for table {expected_table:02d} but the file's title says "
            f"table {title_number}: refusing to parse a different table than configured."
        )
    if title_number == 15:
        return _parse_table15_rows(rows, block=block)
    if title_number == 9:
        # TABLE 9 — live births and crude birth rates (v15): the same wide
        # Total/Urban/Rural layout as Table 15 (Number then Rate blocks,
        # quality code column, 5-year window per edition), verified live on
        # all 13 wired editions 2026-09-20. The content guard keys on the
        # title's OWN words exactly like the 21/22 zone: a number-only
        # dispatch would silently accept any other table that happens to
        # carry the number 9 in some future renumbering — the title is the
        # ground truth, the number the cross-check.
        if "live births and crude birth rates" not in title.lower():
            raise ValueError(
                f"DYB table {title_number} in this file is NOT the live-births/CBR "
                f"table (title: {title[:90]!r}). Refusing to parse it as Table 9 — "
                "check the edition's table numbering."
            )
        return _parse_table15_rows(rows, block=block)
    if title_number == 4:
        return _parse_table4_rows(rows, measure=block)
    if title_number == 17:
        return _parse_table17_rows(rows, block=block)
    if title_number in (21, 22):
        if "life expectancy at specified ages" not in title.lower():
            raise ValueError(
                f"DYB table {title_number} in this file is NOT the life-expectancy-by-age "
                f"table (title: {title[:90]!r}). The renumbering zone alternates by edition "
                "parity: LE-by-age is table 21 in EVEN editions, table 22 in ODD ones (the "
                "other number holds the 5qx probabilities of dying, same layout, different "
                "measure). Fix the source_ref's table number for this edition."
            )
        return _parse_table21_rows(rows, age=block)
    raise ValueError(
        f"DYB table {title_number} is not wired in this connector yet "
        "(supported: 15 = infant deaths/IMR, 9 = live births/crude birth rates, "
        "4 = life expectancy at birth + total fertility rate (block: tfr), "
        "17 = maternal deaths/mortality ratios, 21/22 = life expectancy at "
        "specified ages)."
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
