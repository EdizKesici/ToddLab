"""The curated abortion and divorce legalization tables (v30)."""
import csv
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _rows(name):
    return {r["entity_id"]: r for r in csv.DictReader((ROOT / "catalog/curated" / name).open(encoding="utf-8"))}


ABORTION = _rows("abortion_legalization.csv")
DIVORCE = _rows("divorce_legalization.csv")


def test_rows_resolve_cited_and_dated():
    ids = {e["entity_id"] for e in yaml.safe_load((ROOT / "config/entities.yaml").read_text(encoding="utf-8"))}
    for table in (ABORTION, DIVORCE):
        assert set(table) <= ids
        for r in table.values():
            assert "en.wikipedia.org/wiki/" in r["citation"] and r["year"] == r["value"]
            assert 1900 <= int(r["year"]) <= 2022


def test_anchors_and_deliberate_absences():
    assert {k: int(ABORTION[k]["year"]) for k in ("france", "united_kingdom", "russian_federation", "ireland", "switzerland")} == {
        "france": 1975, "united_kingdom": 1968, "russian_federation": 1955, "ireland": 2019, "switzerland": 2002,
    }
    assert {k: int(DIVORCE[k]["year"]) for k in ("italy", "spain", "ireland", "malta", "chile")} == {
        "italy": 1970, "spain": 1981, "ireland": 1996, "malta": 2011, "chile": 2004,
    }
    # reversed or narrow regimes and countries where divorce is not legal stay absent, never guessed
    assert not {"poland", "germany", "malta"} & set(ABORTION)
    assert not {"philippines", "holy_see", "france", "united_kingdom"} & set(DIVORCE)
