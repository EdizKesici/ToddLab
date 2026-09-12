"""ADR-0007/0008 semantics tests: witnesses are stored, validated and
displayed BESIDE the canonical series — never merged into it, never
averaged with it. Priority arbitration happens WITHIN the canonical tier
only. Unit-level tests on the merge functions plus conversion tests.
"""
from __future__ import annotations

import pytest

from src.pipeline.merge import _split_by_role, build_witness_series, merge_indicator, merge_points
from src.pipeline.normalize import UNIT_CONVERSIONS, NormalizedPoint, _convert_unit

import json


def _point(entity_id="france", year=2021, value=3.1, provider="un_dyb", ref="2024/table15",
           priority=2, role="canonical", citation=None, definition_note=None, sex=None) -> NormalizedPoint:
    return NormalizedPoint(
        entity_id=entity_id, year=year, value=value, provider=provider, source_ref=ref,
        priority=priority, role=role, citation=citation, definition_note=definition_note,
        sex=sex,
    )


# --- Role split ---------------------------------------------------------------


def test_witness_points_never_enter_the_canonical_series(tmp_path):
    points = [
        _point(entity_id="france", year=2021, value=3.1, provider="un_dyb", priority=2, role="canonical"),
        _point(entity_id="france", year=2021, value=2.8, provider="owid", priority=3, role="witness"),
    ]
    merged, provenance = merge_points([p for p in points if p.role == "canonical"])
    # The witness value (2.8) must not be arbitratable, averaged, or visible
    # anywhere in the canonical output.
    assert len(merged) == 1
    assert merged[0].value == 3.1
    assert merged[0].provider == "un_dyb"
    assert provenance == []  # no cross-layer arbitration ever happened


def test_canonical_arbitration_stays_within_the_tier_and_is_logged():
    points = [
        _point(entity_id="ussr", year=1974, value=27.9, provider="curated", ref="ussr_series", priority=1, role="canonical"),
        _point(entity_id="ussr", year=1974, value=30.0, provider="un_dyb", ref="1974/table15", priority=2, role="canonical"),
    ]
    merged, provenance = merge_points(points)
    assert merged[0].value == 27.9  # priority 1 wins WITHIN the canonical tier
    assert provenance[0]["role"] == "canonical"
    assert provenance[0]["retained"]["provider"] == "curated"
    assert provenance[0]["discarded"][0]["provider"] == "un_dyb"


def test_all_none_canonical_candidates_produce_nothing():
    # A key where every canonical source explicitly reports no value is
    # absent from the canonical series — nothing is fabricated.
    points = [_point(entity_id="algeria", year=2021, value=None, role="canonical")]
    merged, _ = merge_points(points)
    assert merged == []


# --- Witness series construction ------------------------------------------------


def test_witness_series_preserves_explicit_gap_points():
    # DYB's honest gaps ("reported to the collector, no rate computed")
    # survive as value=None points in the witness series.
    points = [
        _point(entity_id="algeria", year=2020, value=None, role="witness"),
        _point(entity_id="algeria", year=2021, value=None, role="witness"),
        _point(entity_id="france", year=2020, value=3.37, role="witness"),
    ]
    series, _ = build_witness_series(points)
    values = {(p.entity_id, p.year): p.value for p in series.points}
    assert values[("algeria", 2020)] is None  # the gap IS the data
    assert values[("france", 2020)] == 3.37


def test_witness_duplicate_reduction_prefers_first_non_null_and_logs():
    # DYB double "Total" rows under different quality regimes: one value
    # point per (entity, year) in the witness series, reduction logged.
    points = [
        _point(entity_id="tonga", year=2020, value=8.0, role="witness", priority=2),
        _point(entity_id="tonga", year=2020, value=None, role="witness", priority=2),
        _point(entity_id="tonga", year=2021, value=None, role="witness", priority=2),
        _point(entity_id="tonga", year=2021, value=11.0, role="witness", priority=2),
    ]
    series, provenance = build_witness_series(points)
    values = {p.year: p.value for p in series.points}
    assert values[2020] == 8.0
    assert values[2021] == 11.0
    assert len(provenance) == 2
    assert all(entry["role"] == "witness" for entry in provenance)


def test_merge_indicator_writes_both_files(tmp_path):
    points = [
        _point(entity_id="ussr", year=1974, value=27.9, provider="curated", ref="ussr_series",
               priority=1, role="canonical", citation="TsSU yearbooks (Kalabekov)", definition_note="Soviet definition"),
        _point(entity_id="russia", year=1974, value=21.9, provider="owid", ref="infant-mortality",
               priority=3, role="witness"),
    ]
    (tmp_path / "imr.normalized.json").write_text(
        json.dumps([p.__dict__ for p in points]), encoding="utf-8"
    )
    merged, provenance = merge_indicator("imr", tmp_path)

    canonical = json.loads((tmp_path / "imr.merged.json").read_text())
    witnesses = json.loads((tmp_path / "imr.witnesses.json").read_text())

    # Canonical: the curated point with its per-point provenance (the
    # intermediate merged.json serializes the full dataclass, `sex` included
    # as None — the DIST omits it for plain points, see build.py).
    assert canonical == [
        {
            "entity_id": "ussr", "year": 1974, "value": 27.9, "provider": "curated",
            "source_ref": "ussr_series", "citation": "TsSU yearbooks (Kalabekov)",
            "definition_note": "Soviet definition", "sex": None,
            # P2 quality-annotation fields: present-but-None on the wire (the
            # full dataclass is serialized, like sex above); the DIST omits
            # them for plain points, see build.py.
            "quality_code": None, "footnote_refs": None, "reference_range": None,
            "missing_marker": None, "provisional": None,
        }
    ]
    # Witness: the harmonized series beside it, never merged.
    assert len(witnesses) == 1
    assert witnesses[0]["provider"] == "owid"
    assert witnesses[0]["source_ref"] == "infant-mortality"
    assert witnesses[0]["data"] == [{"entity_id": "russia", "year": 1974, "value": 21.9}]
    assert provenance == []


# --- Unit conversion: declared table only, never a guessed factor --------------


def test_conversion_table_has_both_directions_of_the_percent_pair():
    assert UNIT_CONVERSIONS[("deaths_per_100_births", "deaths_per_1000_births")] == 10.0
    assert UNIT_CONVERSIONS[("deaths_per_1000_births", "deaths_per_100_births")] == 0.1


def test_percent_to_per_1000_is_exact_tenth_free():
    assert _convert_unit(2.77, "deaths_per_100_births", "deaths_per_1000_births") == pytest.approx(27.7)
    assert _convert_unit(0.31, "deaths_per_100_births", "deaths_per_1000_births") == 3.1
    # float artifact of 0.31 * 10 cleaned by the 1e-10 rounding:
    assert _convert_unit(0.31, "deaths_per_100_births", "deaths_per_1000_births") == 3.1


def test_identity_conversion_returns_the_value_untouched():
    assert _convert_unit(27.7, "deaths_per_1000_births", "deaths_per_1000_births") == 27.7


def test_unknown_conversion_pair_raises_loudly():
    with pytest.raises(NotImplementedError, match="never guess a factor"):
        _convert_unit(1.0, "deaths_per_100_births", "years")


# --- DYB name resolution with the real registry --------------------------------


def test_dyb_override_names_resolve(real_entities):
    # 12 overrides added from the live 2024 Table 15 file (see
    # scripts/check_dyb_name_resolution.py): exact DYB printing -> entity.
    for dyb_name, entity_id in [
        ("United Kingdom of Great Britain and Northern Ireland", "united_kingdom"),
        ("Iran (Islamic Republic of)", "iran_islamic_republic_of"),
        ("Republic of Korea", "korea_republic_of"),
        ("United States of America", "united_states"),
        ("Netherlands (Kingdom of the)", "netherlands"),
        ("Republic of Moldova", "moldova_republic_of"),
        ("United Republic of Tanzania", "tanzania_united_republic_of"),
        ("State of Palestine", "palestine_state_of"),
        ("China, Hong Kong SAR", "hong_kong"),
        ("China, Macao SAR", "macao"),
        ("Reunion", "reunion"),
        ("Saint-Martin (French part)", "saint_martin_french_part"),
    ]:
        entity = real_entities.resolve_from_source("un_dyb", dyb_name, None)
        assert entity is not None and entity.entity_id == entity_id, dyb_name


def test_dyb_plain_names_resolve_by_exact_label(real_entities):
    assert real_entities.resolve_from_source("un_dyb", "France", None).entity_id == "france"
    assert real_entities.resolve_from_source("un_dyb", "Algeria", None).entity_id == "algeria"


def test_dyb_unknown_name_stays_unresolved(real_entities):
    # 'Saint Helena ex. dep.' (sub-territory granularity) deliberately
    # unresolved: explicit gap, not a guessed attachment.
    assert real_entities.resolve_from_source("un_dyb", "Atlantis", None) is None


# --- The sex dimension (P1: DYB Table 4, life expectancy) ---------------------


def test_sex_split_canonical_and_both_sexes_witness_coexist():
    # The collector prints Male and Female separately (no "both sexes"
    # column): the canonical tier carries two points per entity-year, the
    # both-sexes witness rides BESIDE them — no collision, no averaging.
    points = [
        _point(entity_id="france", year=2020, value=79.1, provider="un_dyb", ref="2024/table04",
               priority=1, role="canonical", sex="male"),
        _point(entity_id="france", year=2020, value=85.6, provider="un_dyb", ref="2024/table04",
               priority=1, role="canonical", sex="female"),
        _point(entity_id="france", year=2020, value=82.3, provider="owid", ref="life-expectancy",
               priority=13, role="witness"),
    ]
    canonical, witness_groups = _split_by_role(points)
    merged, provenance = merge_points(canonical)
    assert [(m.sex, m.value) for m in merged] == [("female", 85.6), ("male", 79.1)]  # merge sorts by (entity, year, sex)
    series, _ = build_witness_series(witness_groups[0])
    assert [(p.sex, p.value) for p in series.points] == [(None, 82.3)]


def test_edition_vintage_arbitration_is_per_sex_and_logged():
    # Same (entity, year, sex) reported by two editions: the LATER edition
    # (higher priority) wins — the standard vintage discipline — and the
    # arbitration names the sex it arbitrated.
    p2024 = _point(entity_id="france", year=2020, value=79.8, provider="un_dyb", ref="2024/table04",
                   priority=1, role="canonical", sex="male")
    p2019 = _point(entity_id="france", year=2020, value=79.4, provider="un_dyb", ref="2019/table04",
                   priority=6, role="canonical", sex="male")
    merged, provenance = merge_points([p2024, p2019])
    assert len(merged) == 1
    assert merged[0].value == 79.8
    assert merged[0].source_ref == "2024/table04"
    assert len(provenance) == 1
    assert provenance[0]["sex"] == "male"
    assert provenance[0]["retained"]["source_ref"] == "2024/table04"


def test_male_female_pair_is_not_a_duplicate_after_merge():
    # merge.py's contract: one value per (entity, year, sex). The
    # duplicate check in validate.py keys on the same triple.
    points = [
        _point(entity_id="france", year=2020, value=79.1, provider="un_dyb", ref="2024/table04",
               priority=1, role="canonical", sex="male"),
        _point(entity_id="france", year=2020, value=85.6, provider="un_dyb", ref="2024/table04",
               priority=1, role="canonical", sex="female"),
    ]
    merged, provenance = merge_points(points)
    assert len(merged) == 2  # not collapsed, not a conflict
    assert provenance == []  # no arbitration needed between the sexes
