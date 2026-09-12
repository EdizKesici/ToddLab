from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.config_loader import load_entities, load_indicators
from src.connectors.base import RawFetchResult
from src.connectors.curated import CuratedConnector
from src.connectors.dyb import parse_dyb, parse_dyb_footnotes, parse_table15, parse_table4
from src.connectors.owid import parse_csv

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


def _write_snapshot(raw_dir: Path, result: RawFetchResult, timestamp: str = FIXED_SNAPSHOT_TIMESTAMP) -> Path:
    """Test-side twin of fetch.py's snapshot writer, with the same layout:
    data/raw/{provider}/{indicator_id}/{source_ref with / -> _}/{timestamp}.json.
    Imported logic would create a circular-ish dependency on private helpers,
    so it is re-declared here — the integration tests assert on the layout
    itself, which keeps the twin honest."""
    from src.pipeline.fetch import _write_snapshot as production_write

    result.fetched_at = timestamp
    return production_write(result, raw_dir)


def seed_owid_snapshot(raw_dir: Path, indicator_id: str, source_ref: str, csv_fixture_name: str) -> Path:
    """Simulates the result of `fetch` for an OWID source WITHOUT touching
    the network. Reuses the real OWID parser so the test exercises the real
    parsing logic, not a reimplementation of it."""
    csv_text = (FIXTURES_DIR / csv_fixture_name).read_text(encoding="utf-8")
    records = parse_csv(csv_text)
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


def seed_curated_snapshot(raw_dir: Path, indicator_id: str, source_ref: str = "ussr_infant_mortality_official") -> Path:
    """Same for a curated source: runs the REAL connector against the REAL
    committed catalog (deterministic, network-free by construction) and
    snapshots it through the production writer."""
    connector = CuratedConnector(catalog_dir=CATALOG_CURATED_DIR)
    result = connector.fetch_raw(source_ref, indicator_id)
    return _write_snapshot(raw_dir, result)


def seed_oecd_snapshot(raw_dir: Path, indicator_id: str, source_ref: str = "DF_COM/CICDHOCD") -> Path:
    """oecd DF_COM (WHO Mortality Database redistribution): the SDMX-CSV
    fixture mirrors a real response slice (RUS 1994 crisis with the sex
    split, honest empty OBS_VALUE gap)."""
    from src.connectors.oecd import parse_sdmx_csv

    csv_text = (FIXTURES_DIR / "oecd_homicide_sdmx.csv").read_text(encoding="utf-8")
    records = parse_sdmx_csv(csv_text, field="rate")
    result = RawFetchResult(
        provider="oecd",
        source_ref=source_ref,
        indicator_id=indicator_id,
        fetched_at=FIXED_SNAPSHOT_TIMESTAMP,
        source_url="test://fixture-oecd",
        records=records,
    )
    return _write_snapshot(raw_dir, result)
