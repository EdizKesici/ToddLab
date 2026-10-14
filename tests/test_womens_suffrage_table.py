"""The curated women's-suffrage table (v30): equal-terms rule, known anchors."""
import csv
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROWS = {r["entity_id"]: r for r in csv.DictReader((ROOT / "catalog/curated/womens_suffrage_introduction.csv").open(encoding="utf-8"))}


def test_every_row_resolves_to_a_known_entity_and_is_cited():
    ids = {e["entity_id"] for e in yaml.safe_load((ROOT / "config/entities.yaml").read_text(encoding="utf-8"))}
    assert set(ROWS) <= ids
    for r in ROWS.values():
        assert "archive.ipu.org/wmn-e/suffrage.htm" in r["citation"]
        assert r["year"] == r["value"] and 1893 <= int(r["year"]) <= 2005


def test_equal_terms_anchors():
    # restrictions lifted, not the first (restricted) grant (decision 24)
    assert {k: int(ROWS[k]["year"]) for k in ("united_kingdom", "belgium", "switzerland", "france", "australia", "canada", "south_africa")} == {
        "united_kingdom": 1928, "belgium": 1948, "switzerland": 1971, "france": 1944, "australia": 1962, "canada": 1950, "south_africa": 1994,
    }
    assert "1918" in ROWS["united_kingdom"]["definition_note"]  # the first grant rides the note
