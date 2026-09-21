"""Regression tests for bugs caught by a live-network audit (see CHANGELOG):
- fetch isolation (one source failing must not block the others)
- snapshot selection by real timestamp, not lexical filename sort
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.connectors.base import RawFetchResult, RawRecord
from src.pipeline import fetch as fetch_module
from src.pipeline.normalize import _latest_snapshot
from src.schema.indicator import Indicator, Provider


def _minimal_indicator(indicator_id: str, ref: str) -> Indicator:
    return Indicator.model_validate(
        {
            "id": indicator_id,
            "label": "Test",
            "family": "mortality",
            "unit": "test_unit",
            "higher_is_better": False,
            "todd_core": True,
            "sources": [{"provider": "owid", "ref": ref, "priority": 1, "root": "un_igme"}],
            "reliability": "high",
            "reliability_criteria": "Justification long enough to pass the validator.",
            "license": "CC-BY-4.0",
        }
    )


class _FakeConnector:
    provider = "owid"

    def fetch_raw(self, source_ref, indicator_id, field=None):
        if source_ref == "fails":
            raise RuntimeError("simulated HTTP 403")
        return RawFetchResult(
            provider="owid",
            source_ref=source_ref,
            indicator_id=indicator_id,
            fetched_at="2026-01-01T000000Z",
            source_url="test://fake",
            records=[RawRecord(entity_raw_name="France", iso3_raw="FRA", year=2000, value=1.0)],
        )


def test_fetch_all_isolates_a_failing_source_from_the_rest(tmp_path, monkeypatch):
    # Regression test: an earlier version let one source's exception
    # propagate out of fetch_indicator, aborting fetch_all entirely — the
    # indicator processed AFTER the failing one was never even attempted.
    monkeypatch.setitem(fetch_module.CONNECTORS, Provider.owid, _FakeConnector())

    indicators = {
        "indicator_that_fails": _minimal_indicator("indicator_that_fails", "fails"),
        "indicator_that_works": _minimal_indicator("indicator_that_works", "ok-slug"),
    }

    outcome = fetch_module.fetch_all(indicators, tmp_path)

    assert len(outcome.failures) == 1
    assert outcome.failures[0].indicator_id == "indicator_that_fails"
    assert len(outcome.written) == 1
    # Per-source_ref snapshot layout (v6): raw/{provider}/{indicator}/{source_ref}/{ts}.json
    assert (tmp_path / "owid" / "indicator_that_works" / "ok-slug" / "2026-01-01T000000Z.json").exists()
    # The critical assertion: the second indicator was reached at all.
    assert not (tmp_path / "owid" / "indicator_that_fails").exists()


def test_latest_snapshot_picks_the_true_latest_by_parsed_timestamp(tmp_path):
    source_dir = tmp_path / "owid" / "some_indicator" / "some-ref"
    source_dir.mkdir(parents=True)

    # Correct format (matches RawFetchResult.now_iso()).
    (source_dir / "2026-01-01T000000Z.json").write_text("{}")
    (source_dir / "2026-03-15T120000Z.json").write_text("{}")
    # Malformed / inconsistent format (no dashes) — this is what an earlier
    # buggy test fixture accidentally used, and a naive lexical sort would
    # have ranked it ABOVE the real 2026-03-15 snapshot despite being
    # unparseable and of unknown actual date.
    (source_dir / "20260601T000000Z.json").write_text("{}")

    result = _latest_snapshot(tmp_path, "owid", "some_indicator", "some-ref")
    assert result.name == "2026-03-15T120000Z.json"


def test_latest_snapshot_scopes_to_the_source_ref_directory(tmp_path):
    # v6 regression guard: two sources of the SAME provider for one
    # indicator (the planned DYB editions loop) must read their OWN
    # snapshot directories, never compete for one shared directory.
    for ref in ("2024/table15", "2023/table15"):
        source_dir = tmp_path / "un_dyb" / "imr" / ref.replace("/", "_")
        source_dir.mkdir(parents=True)
        (source_dir / "2026-01-01T000000Z.json").write_text("{}")

    result = _latest_snapshot(tmp_path, "un_dyb", "imr", "2024/table15")
    assert result is not None
    assert result.parent.name == "2024_table15"


def test_latest_snapshot_returns_none_when_only_malformed_files_exist(tmp_path):
    source_dir = tmp_path / "owid" / "some_indicator" / "some-ref"
    source_dir.mkdir(parents=True)
    (source_dir / "not_a_timestamp.json").write_text("{}")

    assert _latest_snapshot(tmp_path, "owid", "some_indicator", "some-ref") is None


def test_latest_snapshot_returns_none_when_directory_is_missing(tmp_path):
    assert _latest_snapshot(tmp_path, "owid", "nonexistent_indicator", "some-ref") is None


# --- v9: the QC/footnote plumbing audit ---------------------------------------


def test_witness_points_with_footnote_refs_join_without_keyerror(tmp_path):
    # The v9 audit of the QC/footnote plumbing found a LATENT crash: build.py's
    # _referenced_refs accessed p["provider"] directly, but WITNESS points
    # inherit provider/source_ref from their series (merge.py's witness
    # payload omits them per point). No current witness carried footnote_refs,
    # so it slept — the first DYB-style witness would have raised a KeyError
    # at build time. Regression: a witness point WITH refs joins its note
    # under the witness's own source.
    import json

    from src.pipeline.build import build_indicator_file
    from src.schema.entity import EntityRegistry

    indicator = Indicator.model_validate(
        {
            "id": "test_mmr",
            "label": "Test MMR",
            "family": "mortality",
            "unit": "test_unit",
            "higher_is_better": False,
            "todd_core": False,
            "sources": [
                {"provider": "un_dyb", "ref": "2024/table17", "priority": 1, "root": "unsd_dyb"},
                {"provider": "owid", "ref": "maternal-mortality", "priority": 2, "role": "witness",
                 "field": "Maternal mortality ratio", "root": "un_mmeig"},
            ],
            "reliability": "high",
            "reliability_criteria": "Justification long enough to pass the validator.",
            "license": "CC-BY-4.0",
        }
    )
    processed = tmp_path / "processed"
    processed.mkdir()
    # Canonical: one plain point. Witness: one point CARRYING footnote refs
    # (no provider/source_ref keys — inherited from the series, the shape
    # merge.py actually writes).
    (processed / "test_mmr.merged.json").write_text(
        json.dumps([
            {"entity_id": "france", "year": 2020, "value": 5.2, "provider": "un_dyb",
             "source_ref": "2024/table17", "priority": 1, "role": "canonical"},
        ]),
        encoding="utf-8",
    )
    (processed / "test_mmr.witnesses.json").write_text(
        json.dumps([
            {
                "provider": "owid",
                "source_ref": "maternal-mortality",
                "data": [
                    {"entity_id": "france", "year": 2020, "value": 4.6,
                     "footnote_refs": ["7"]},
                ],
            }
        ]),
        encoding="utf-8",
    )
    # The witness source's snapshot carries a note 7.
    (processed / "test_mmr.footnotes.json").write_text(
        json.dumps({"owid:maternal-mortality": {"legend": {}, "notes": {"7": "Modeled estimate caveat."}}}),
        encoding="utf-8",
    )

    entities = EntityRegistry(entities=[])
    payload = build_indicator_file(indicator, processed, tmp_path / "dist")

    witness = payload["witnesses"][0]
    assert witness["data"][0]["footnote_refs"] == ["7"]
    # The note text joined under the WITNESS source, not a KeyError.
    sources = {(s["provider"], s["source_ref"]): s for s in payload["sources"]}
    witness_notes = sources[("owid", "maternal-mortality")]["footnotes"]["notes"]
    assert witness_notes["7"] == "Modeled estimate caveat."
