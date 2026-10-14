"""extra_core.csv: the metrics that are NOT in Todd's books (todd_core.csv).

Same layout as todd_core.csv minus the book / citation_count columns (one row
per metric). The two files must never overlap, and every catalogued indicator
flagged todd_core: false must be listed here.
"""
import csv
from pathlib import Path

from src.config_loader import load_indicators
from src.schema.indicator import Family

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = {f.value for f in Family}


def _rows(name: str) -> list[dict]:
    with open(ROOT / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_extra_core_layout_and_values():
    with open(ROOT / "extra_core.csv", encoding="utf-8", newline="") as f:
        assert next(csv.reader(f)) == ["id", "label", "family", "notes"]
    rows = _rows("extra_core.csv")
    ids = [r["id"] for r in rows]
    assert ids and len(ids) == len(set(ids)), "one row per metric, ids unique"
    for r in rows:
        assert r["id"] == r["id"].strip().lower() and " " not in r["id"]
        assert r["label"].strip() and r["notes"].strip()
        assert r["family"] in FAMILIES, (r["id"], r["family"])


def test_extra_core_never_overlaps_todd_core():
    extra = {r["id"] for r in _rows("extra_core.csv")}
    todd = {r["id"] for r in _rows("todd_core.csv")}
    assert not extra & todd


def test_every_non_todd_indicator_is_listed_in_extra_core():
    extra = {r["id"] for r in _rows("extra_core.csv")}
    indicators = load_indicators(ROOT / "config")
    non_todd = {i for i, ind in indicators.items() if not ind.todd_core}
    assert non_todd <= extra, sorted(non_todd - extra)
    # and an extra metric that IS an indicator is never flagged todd_core
    assert all(not indicators[i].todd_core for i in extra if i in indicators)
