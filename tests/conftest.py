from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.config_loader import load_entities, load_indicators
from src.connectors.base import RawFetchResult
from src.connectors.curated import CuratedConnector
from src.connectors.dyb import parse_dyb, parse_dyb_footnotes, parse_table15, parse_table4, parse_table17
from src.connectors.eurostat import parse_eurostat
from src.connectors.gho import parse_gho
from src.connectors.owid import parse_csv
from src.connectors.worldbank import parse_country_meta, parse_wb

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
CATALOG_CURATED_DIR = ROOT / "catalog" / "curated"

# Must be parseable by normalize.py's SNAPSHOT_TS_FORMAT ("%Y-%m-%dT%H%M%SZ").
# An earlier version of this fixture used "20260101T000000Z" (no dashes),
# which does NOT match that format and was the root cause of a real bug
# (see CHANGELOG: mock snapshots silently outranking real fetches under a
# naive lexical filename sort). Keep this in sync with production's format.
FIXED_SNAPSHOT_TIMESTAMP = "2026-01-01T000000Z"


@pytest.fixture(scope="session")
def real_indicators():
    return load_indicators(CONFIG_DIR)


@pytest.fixture(scope="session")
def real_entities():
    return load_entities(CONFIG_DIR)


@pytest.fixture(scope="session")
def real_todd_refs():
    # v13: the committed, generated corpus (config/todd_refs.yaml) — the
    # same loader the CLI uses, so integration tests exercise the real
    # cross-validated config surface, not a hand-rolled miniature.
    from src.config_loader import load_todd_refs

    return load_todd_refs(CONFIG_DIR)


def _write_snapshot(raw_dir: Path, result: RawFetchResult, timestamp: str = FIXED_SNAPSHOT_TIMESTAMP) -> Path:
    """Test-side twin of fetch.py's snapshot writer, with the same layout:
    data/raw/{provider}/{indicator_id}/{source_ref with / -> _}/{timestamp}.json.
    Imported logic would create a circular-ish dependency on private helpers,
    so it is re-declared here — the integration tests assert on the layout
    itself, which keeps the twin honest."""
    from src.pipeline.fetch import _write_snapshot as production_write

    result.fetched_at = timestamp
    return production_write(result, raw_dir)


def seed_owid_snapshot(
    raw_dir: Path, indicator_id: str, source_ref: str, csv_fixture_name: str, *, value_field: str | None = None
) -> Path:
    """Simulates the result of `fetch` for an OWID source WITHOUT touching
    the network. Reuses the real OWID parser so the test exercises the real
    parsing logic, not a reimplementation of it. `value_field` selects the
    column on multi-variable charters (the maternal-mortality one)."""
    csv_text = (FIXTURES_DIR / csv_fixture_name).read_text(encoding="utf-8")
    records = parse_csv(csv_text, value_field=value_field)
    result = RawFetchResult(
        provider="owid",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture",
        records=records,
    )
    return _write_snapshot(raw_dir, result)


def seed_dyb_snapshot(raw_dir: Path, indicator_id: str, source_ref: str = "2024/table15") -> Path:
    """Same for a un_dyb source, from the faithful SpreadsheetML fixture.
    Since P2 the snapshot also carries the fixture's Footnotes worksheet
    (legend + note texts) exactly like a real fetch would."""
    data = (FIXTURES_DIR / "dyb_table15_sample.xls").read_bytes()
    records = parse_dyb(data, expected_table=15)
    result = RawFetchResult(
        provider="un_dyb",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture-dyb",
        records=records,
        footnotes=parse_dyb_footnotes(data),
    )
    return _write_snapshot(raw_dir, result)


def seed_dyb_table9_snapshot(raw_dir: Path, indicator_id: str, source_ref: str = "2024/table09") -> Path:
    """un_dyb Table 9 (live births + crude birth rates, v15): same
    seeding pattern from the faithful Table 9 SpreadsheetML fixture —
    the Table 15 wide layout with the '*NN' glued star-plus-ref marker
    on a count cell (the v15 grammar find), '+U'-coded honest rate gaps
    and a second Total row under a different quality code (Tonga)."""
    data = (FIXTURES_DIR / "dyb_table9_sample.xls").read_bytes()
    records = parse_dyb(data, expected_table=9)
    result = RawFetchResult(
        provider="un_dyb",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture-dyb-t9",
        records=records,
        footnotes=parse_dyb_footnotes(data),
    )
    return _write_snapshot(raw_dir, result)


def seed_dyb_table4_snapshot(raw_dir: Path, indicator_id: str, source_ref: str = "2024/table04") -> Path:
    """un_dyb Table 4 (life expectancy at birth, sex-split as printed):
    same seeding pattern, from the faithful Table 4 SpreadsheetML fixture
    (header bands, Male/Female columns at 17/19, honest "..." gaps, P2
    marker cells: Roman reference ranges, footnote refs, "*")."""
    data = (FIXTURES_DIR / "dyb_table4_sample.xls").read_bytes()
    records = parse_dyb(data, expected_table=4)
    result = RawFetchResult(
        provider="un_dyb",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture-dyb-t4",
        records=records,
        footnotes=parse_dyb_footnotes(data),
    )
    return _write_snapshot(raw_dir, result)


def seed_dyb_table17_snapshot(
    raw_dir: Path, indicator_id: str, source_ref: str = "2024/table17", block: str = "rate"
) -> Path:
    """un_dyb Table 17 (maternal deaths + ratios): faithful SpreadsheetML
    fixture — 'Co-de' quality column beside the year header, (value, marker)
    pairs, '♦'/'♦N' small-base markers, Number-only countries (the honest
    degradation), '-' nils, '...' gaps, Footnotes worksheet. `block` selects
    the measure exactly like the indicator config's `field` ("rate" = the
    UNSD-computed ratio, "number" = the registered counts — v12's
    maternal_deaths)."""
    data = (FIXTURES_DIR / "dyb_table17_sample.xls").read_bytes()
    records = parse_dyb(data, expected_table=17, block=block)
    result = RawFetchResult(
        provider="un_dyb",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture-dyb-t17",
        records=records,
        footnotes=parse_dyb_footnotes(data),
    )
    return _write_snapshot(raw_dir, result)


def seed_dyb_table21_snapshot(
    raw_dir: Path, indicator_id: str, source_ref: str = "2024/table21", age: str = "60"
) -> Path:
    """un_dyb Table 21 (life expectancy at specified ages): faithful
    SpreadsheetML fixture — age header 0,5,...,100, single-year and
    "2012 - 2015"-style reference periods, Male/Female ROWS, the 2024
    dual block (age-0-only degradation), '...' gaps, a <html:Sup> footnote
    glued to a country name, Footnotes worksheet. `age` exercises the
    config's `field` column selector."""
    data = (FIXTURES_DIR / "dyb_table21_sample.xls").read_bytes()
    records = parse_dyb(data, expected_table=21, block=age)
    result = RawFetchResult(
        provider="un_dyb",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture-dyb-t21",
        records=records,
        footnotes=parse_dyb_footnotes(data),
    )
    return _write_snapshot(raw_dir, result)


def seed_gho_snapshot(
    raw_dir: Path, indicator_id: str, source_ref: str = "WHOSIS_000015", *, fixture: str = "gho_whosis_000015_sample.json"
) -> Path:
    """who_gho (GHO OData JSON): faithful fixture — COUNTRY rows with the
    three SEX dims, REGION/WORLDBANKINCOMEGROUP/GLOBAL rows the parser
    drops (the provider's own classification), one null NumericValue gap
    (the LE-60 fixture; the SDGSUICIDE one has none, matching the live
    slice). `fixture` selects the payload file: WHOSIS_000015 (Dim1=SEX,
    Dim2-less), SDGSUICIDE (Dim1=SEX + Dim2 AGEGROUP — the all-ages
    rows kept, the age slices dropped, v13), NCD_BMI_30C (Dim1=SEX +
    Dim2 = AGEGROUP_YEARS18-PLUS on EVERY row — the v20 per-code age
    pin's own face) or PRISON_A2 (Dim2-less, the v20 coupe). Runs the
    real parser — v20: with the code passed, exactly as fetch_raw does,
    so the per-code AGE pin applies in tests too (an age-pinned seed
    REFUSES an off-frame row). Snapshots through the production writer."""
    json_text = (FIXTURES_DIR / fixture).read_text(encoding="utf-8")
    records = parse_gho(json_text, code=source_ref)
    result = RawFetchResult(
        provider="who_gho",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture-gho",
        records=records,
    )
    return _write_snapshot(raw_dir, result)


_WB_INDICATOR_NAMES = {
    "SP.DYN.IMRT.MA.IN": "Mortality rate, infant, male (per 1,000 live births)",
    "SP.DYN.IMRT.FE.IN": "Mortality rate, infant, female (per 1,000 live births)",
    "SP.DYN.LE00.MA.IN": "Life expectancy at birth, male (years)",
    "SP.DYN.LE00.FE.IN": "Life expectancy at birth, female (years)",
    # v12 maternal bloc: the two bare codes (no sex dimension — the printed
    # names carry no slice, the cross-check must pass with sex=None).
    "SH.STA.MMRT": "Maternal mortality ratio (modeled estimate, per 100,000 live births)",
    "SH.MMR.DTHS": "Number of maternal deaths",
    # v14 fertility witness: another bare code, but the shared IMRT page
    # retargeted would print per-1,000 values (17.5) far outside the TFR's
    # plausible bound — the code gets its OWN page fixture with
    # TFR-plausible prints (see fixtures/README.md).
    "SP.DYN.TFRT.IN": "Fertility rate, total (births per woman)",
    # v15 CBR witness: bare code again, its own page for the same reason
    # in mirror — the shared page's per-1,000 mortality prints (17.5)
    # would read as a plausible CBR and CONTAMINATE silently (the exact
    # failure mode the plausible bound exists to catch, dodged only by
    # values that cannot be mistaken for the other unit's range).
    "SP.DYN.CBRT.IN": "Birth rate, crude (per 1,000 people)",
    # v17 unemployment witness: bare code, its own page — same dedicated-
    # page discipline (the shared page's per-1,000 prints would sit INSIDE
    # the rate's plausible band and contaminate silently; the dedicated
    # page carries the live anchors: FRA 1990 9.36 / DEU 2005 11.193 /
    # XKX 2001 57.0 the post-war break, plus the WLD aggregate row the
    # classification drops).
    "SL.UEM.TOTL.NE.ZS": "Unemployment, total (% of total labor force) (national estimate)",
    # v18 witnesses, three dedicated pages (the same discipline: each
    # code's own page with its own live anchors — the shared IMRT page's
    # per-1,000 prints would sit inside a share's plausible band and
    # contaminate silently): the employment-by-sector shares and the
    # migrant stock.
    "SL.IND.EMPL.ZS": "Employment in industry (% of total employment) (modeled ILO estimate)",
    "SL.AGR.EMPL.ZS": "Employment in agriculture (% of total employment) (modeled ILO estimate)",
    "SM.POP.TOTL": "International migrant stock, total",
}


def _wb_page_for(code: str) -> str:
    """The shared WB page fixture, retargeted to `code`: every row's
    indicator id/name swapped for the code's own (the pin-guard checks
    BOTH, so the seed must carry the pair the real API would print).
    The v14 fertility code returns its OWN page fixture instead: the
    shared page's per-1,000 values sit far outside the TFR's plausible
    bound and would flag as range violations in the integration harness."""
    if code == "SP.DYN.TFRT.IN":
        return (FIXTURES_DIR / "wb_tfrt_sample.json").read_text(encoding="utf-8")
    if code == "SP.DYN.CBRT.IN":
        return (FIXTURES_DIR / "wb_cbrt_sample.json").read_text(encoding="utf-8")
    if code == "SL.UEM.TOTL.NE.ZS":
        return (FIXTURES_DIR / "wb_uem_ne_sample.json").read_text(encoding="utf-8")
    # v18: the three new dedicated pages (generated from the live API by
    # scripts/make_v18_fixtures.py — every row read, never typed).
    if code == "SL.IND.EMPL.ZS":
        return (FIXTURES_DIR / "wb_sl_ind_empl_sample.json").read_text(encoding="utf-8")
    if code == "SL.AGR.EMPL.ZS":
        return (FIXTURES_DIR / "wb_sl_agr_empl_sample.json").read_text(encoding="utf-8")
    if code == "SM.POP.TOTL":
        return (FIXTURES_DIR / "wb_sm_pop_totl_sample.json").read_text(encoding="utf-8")
    payload = json.loads((FIXTURES_DIR / "wb_imrt_ma_sample.json").read_text(encoding="utf-8"))
    name = _WB_INDICATOR_NAMES[code]
    for row in payload[1]:
        row["indicator"] = {"id": code, "value": name}
    return json.dumps(payload, ensure_ascii=False)


def seed_wb_snapshot(
    raw_dir: Path, indicator_id: str, source_ref: str = "SP.DYN.IMRT.MA.IN"
) -> Path:
    """worldbank (WDI v2 JSON): faithful fixture — the [meta, rows] page
    shape, the trailing-2025 null (the honest gap), two aggregate rows
    (WLD/AFE) the provider's own /country classification drops. Runs the
    real parser (page texts + aggregate classification + the code pin),
    snapshots through the production writer."""
    page_text = _wb_page_for(source_ref)
    meta_text = (FIXTURES_DIR / "wb_country_meta_sample.json").read_text(encoding="utf-8")
    records = parse_wb([page_text], parse_country_meta(meta_text), expected_code=source_ref)
    result = RawFetchResult(
        provider="worldbank",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture-wb",
        records=records,
    )
    return _write_snapshot(raw_dir, result)


def seed_eurostat_snapshot(
    raw_dir: Path,
    indicator_id: str,
    source_ref: str = "demo_find/TOTFERRT",
    *,
    fixture: str = "eurostat_totferrt_sample.json",
) -> Path:
    """eurostat demo_find (JSON): faithful fixtures — the main miniature
    carries the codelist's own quirks (the EL/UK/FX geo codes, the
    EU27_2020 aggregate, the DE_TOT identical duplicate, XK's no-ISO3
    path) and the FX/FR miniatures the geo-pinned single-series shape
    with the seam's own status flags ('b' break, 'p' provisional). Runs
    the real parser (dimension pin-guards + geo pin), snapshots through
    the production writer."""
    json_text = (FIXTURES_DIR / fixture).read_text(encoding="utf-8")
    records = parse_eurostat(json_text, expected_ref=source_ref)
    result = RawFetchResult(
        provider="eurostat",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture-eurostat",
        records=records,
    )
    return _write_snapshot(raw_dir, result)


def seed_curated_snapshot(raw_dir: Path, indicator_id: str, source_ref: str = "ussr_infant_mortality_official") -> Path:
    """Same for a curated source: runs the REAL connector against the REAL
    committed catalog (deterministic, network-free by construction) and
    snapshots it through the production writer."""
    connector = CuratedConnector(catalog_dir=CATALOG_CURATED_DIR)
    result = connector.fetch_raw(source_ref, indicator_id)
    return _write_snapshot(raw_dir, result)


def seed_oecd_snapshot(
    raw_dir: Path, indicator_id: str, source_ref: str = "DF_COM/CICDHOCD", *, fixture: str = "oecd_homicide_sdmx.csv"
) -> Path:
    """oecd DF_COM (WHO Mortality Database redistribution): the SDMX-CSV
    fixtures mirror real response slices — homicide (RUS 1994 crisis
    with the sex split, honest empty OBS_VALUE gap) and suicide (RUS
    1994/2000 sex split + LTU 1994, the live slice carries no nulls).
    The DEATH_CAUSE pin is extracted from the source_ref exactly like
    the production connector does, so a suicide seed pinned to
    DF_COM/CICDHARM would REFUSE a homicide-fixture row."""
    from src.connectors.oecd import parse_sdmx_csv

    csv_text = (FIXTURES_DIR / fixture).read_text(encoding="utf-8")
    cause = source_ref.split("/")[1]
    records = parse_sdmx_csv(csv_text, field="rate", death_cause=cause)
    result = RawFetchResult(
        provider="oecd",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture-oecd",
        records=records,
    )
    return _write_snapshot(raw_dir, result)


def seed_oecd_idd_snapshot(raw_dir: Path, indicator_id: str, source_ref: str, *, fixture: str) -> Path:
    """oecd DF_IDD (v19, the Income Distribution Database): the four Gini
    vintage doors, each seeded from its own live-carved fixture (the pins
    extracted from the source_ref exactly like the production connector —
    a D_CUR seed would REFUSE a D_PREV fixture row). No sex dimension:
    every record rides sex=None, the flow's own shape."""
    from src.connectors.oecd import parse_idd_csv

    csv_text = (FIXTURES_DIR / fixture).read_text(encoding="utf-8")
    _, measure, methodology, definition = source_ref.split("/")
    records = parse_idd_csv(csv_text, measure=measure, methodology=methodology, definition=definition)
    result = RawFetchResult(
        provider="oecd",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture-oecd-idd",
        records=records,
    )
    return _write_snapshot(raw_dir, result)


def seed_oecd_safety_snapshot(raw_dir: Path, indicator_id: str, source_ref: str, *, fixture: str) -> Path:
    """oecd DF_SAFETY (v19, the ITF/IRTAD road-safety statistics): the
    per-100k road-mortality door, seeded from the live-carved fixture
    (the MEASURE/UNIT pins extracted from the source_ref like the
    production connector — a 10P5HB seed would REFUSE a per-vehicle
    fixture row). No sex dimension: the flow prints none."""
    from src.connectors.oecd import parse_safety_csv

    csv_text = (FIXTURES_DIR / fixture).read_text(encoding="utf-8")
    _, measure, unit = source_ref.split("/")
    records = parse_safety_csv(csv_text, measure=measure, unit=unit)
    result = RawFetchResult(
        provider="oecd",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture-oecd-safety",
        records=records,
    )
    return _write_snapshot(raw_dir, result)


def seed_eurostat_row_snapshot(
    raw_dir: Path,
    indicator_id: str,
    source_ref: str = "migr_pop3ctb/ROW/FR",
    *,
    fixture: str = "eurostat_migr_row_fr_sample.json",
) -> Path:
    """eurostat migr_pop3ctb ROW (v22, the bilateral by-origin row): the
    REAL 32,976-byte FR response as the API served it — the 307-code
    c_birth codelist, the 1,450 non-empty cells, the b/e/p flags, the
    three drop classes (aggregates/regions, the FOR/NAT/TOTAL/OTH/UNK/RNC
    summary codes, the FR diagonal) the parser drops logged, and the
    Todd-board anchors (FR<-MA 2015 = 954,742, FR<-DZ 2018 = 1,390,284,
    FR<-PRT 2025 = 599,492, FR<-AN 1999 = 78 the vanished Antilles).
    Runs the real parser (the ROW pin-guards + the origin-axis
    resolution), snapshots through the production writer."""
    json_text = (FIXTURES_DIR / fixture).read_text(encoding="utf-8")
    records = parse_eurostat(json_text, expected_ref=source_ref)
    result = RawFetchResult(
        provider="eurostat",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture-eurostat-row",
        records=records,
    )
    return _write_snapshot(raw_dir, result)


def seed_oecd_migf_snapshot(
    raw_dir: Path,
    indicator_id: str,
    source_ref: str = "DF_MIG_POPF",
    *,
    fixture: str = "oecd_migf_sample.csv",
) -> Path:
    """oecd DF_MIG_POPF (v22, the migration questionnaire's foreign-born
    matrix): a REAL slice of the empty-key /all download (rows copied
    byte-for-byte by scripts/make_v22_fixtures.py, never typed) — the
    complete FR and US rows on both sexes (the F rows exercising the
    logged by-sex drop), every residual code (W/W_X/EEA/EU15/A4/STLS),
    every vanished-entity code (XKV/ANT_F/CSK_F/SCG_F/SUN_F/YUG_F), the
    diagonals. The parser pins the _T frame and drops the classes logged;
    the seam anchors ride it (FR<-MAR 2015 = 954,742 = the Eurostat
    print exactly; the 2019-2021 extension; US<-MEX 2024)."""
    from src.connectors.oecd import parse_migf_csv

    csv_text = (FIXTURES_DIR / fixture).read_text(encoding="utf-8")
    records = parse_migf_csv(csv_text)
    result = RawFetchResult(
        provider="oecd",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture-oecd-migf",
        records=records,
    )
    return _write_snapshot(raw_dir, result)


def seed_oecd_mig_snapshot(
    raw_dir: Path,
    indicator_id: str,
    source_ref: str = "DF_MIG/B15",
    *,
    fixture: str = "oecd_mig_b15_sample.csv",
) -> Path:
    """oecd DF_MIG/B15 (v23, the migration questionnaire's CITIZENSHIP
    matrix): a REAL slice of the keyed wildcard download (rows copied
    byte-for-byte by scripts/make_v23_fixtures.py, never typed — 16,285
    lines = 8,283 _T + 8,002 F) — the complete FR and US rows on both
    sexes (the F rows exercising the logged by-sex drop, the V24 hook),
    every residual code (STLS/W/W_X/EEA/EU15/A4), every vanished-entity
    code (XKV/ANT_F/CSK_F/SCG_F/SUN_F/YUG_F) riding the shared override
    table onto their withdrawn ISO3 entities, the diagonals. The parser
    pins the _T frame and the B15 frame pins, drops the classes logged,
    and stamps origin_axis="citizenship" on every record; the seam
    anchors ride it (FR<-MAR _T 2015 = 458,561 = the Eurostat
    migr_pop1ctz print exactly; US<-MEX 2024 = 8,226,106.247)."""
    from src.connectors.oecd import parse_mig_csv

    csv_text = (FIXTURES_DIR / fixture).read_text(encoding="utf-8")
    records = parse_mig_csv(csv_text)
    result = RawFetchResult(
        provider="oecd",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture-oecd-mig",
        records=records,
    )
    return _write_snapshot(raw_dir, result)


def seed_ilostat_snapshot(
    raw_dir: Path,
    indicator_id: str,
    source_ref: str,
    *,
    fixture: str,
) -> Path:
    """ilostat (v25, the ILO's own SDMX wire — the DEAP
    class-decomposition rate flows): the REAL full-flow responses as
    the API served them (carved byte-for-byte by
    scripts/make_v25_fixtures.py, never typed) — the class prints
    (CITIZEN/NONCIT on CCT, NATIVE/FOREIGN on CBR), both sexes' rows,
    the KOS->XKX quirk, the OBS_STATUS quality codes, the TOTAL/X class
    drops exercising the logged per-class discipline. Runs the real
    parser (the frame guards: FREQ/MEASURE/AGE pins, the dimension
    layout), snapshots through the production writer."""
    from src.connectors.ilostat import parse_ilostat

    json_text = (FIXTURES_DIR / fixture).read_text(encoding="utf-8")
    records = parse_ilostat(json_text, expected_ref=source_ref)
    result = RawFetchResult(
        provider="ilostat",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture-ilostat",
        records=records,
    )
    return _write_snapshot(raw_dir, result)
