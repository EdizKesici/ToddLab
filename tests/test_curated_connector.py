from pathlib import Path

import pytest

from src.connectors.base import RawFetchResult
from src.connectors.curated import CuratedConnector, parse_curated_csv
from src.pipeline.fetch import CONNECTORS
from src.schema.entity import EntityRegistry
from src.schema.indicator import Provider

ROOT = Path(__file__).resolve().parent.parent
REAL_CATALOG = ROOT / "catalog" / "curated"
REAL_CSV = REAL_CATALOG / "ussr_infant_mortality_official.csv"


def _valid_csv(rows: str) -> str:
    header = "entity_id,year,value,citation,definition_note\n"
    return header + rows


# --- Pure parsing: the strict format contract ---------------------------------


def test_real_catalog_file_parses_with_the_expected_series():
    records = parse_curated_csv(REAL_CSV.read_text(encoding="utf-8"))
    assert len(records) == 21  # 1970-1990, complete
    years = [r.year for r in records]
    assert years == list(range(1970, 1991))
    by_year = {r.year: r.value for r in records}
    assert by_year[1971] == 22.9
    assert by_year[1974] == 27.9
    assert by_year[1976] == 31.4  # the Todd-method peak
    assert by_year[1990] == 21.8


def test_every_curated_row_carries_a_citation_and_a_definition_note():
    # Curation gate condition (c), mechanically enforced: no citation, no
    # entry. The definition note carries the Soviet live-birth caveat.
    records = parse_curated_csv(REAL_CSV.read_text(encoding="utf-8"))
    assert all(r.citation and r.citation.strip() for r in records)
    assert all(r.definition_note for r in records)
    # The 1974 row documents the DYB institutional carrier and the
    # 27.9-vs-27.7 (official series vs UNSD-recomputed rate) nuance.
    row_1974 = next(r for r in records if r.year == 1974)
    assert "Demographic Yearbook 1978" in row_1974.citation
    assert "125,908" in row_1974.citation
    # The blackout years say so in their note.
    row_1976 = next(r for r in records if r.year == 1976)
    assert "blackout" in row_1976.definition_note


def test_wrong_header_raises():
    text = "entity,year,value,source,note\nussr,1974,27.9,x,y\n"
    with pytest.raises(ValueError, match="header"):
        parse_curated_csv(text)


def test_empty_value_raises_because_a_curated_gap_is_an_absent_row():
    text = _valid_csv("ussr,1974,,some citation,some note\n")
    with pytest.raises(ValueError, match="empty value"):
        parse_curated_csv(text)


def test_empty_citation_raises_per_the_curation_gate():
    text = _valid_csv("ussr,1974,27.9,,some note\n")
    with pytest.raises(ValueError, match="citation"):
        parse_curated_csv(text)


def test_duplicate_entity_year_raises():
    text = _valid_csv("ussr,1974,27.9,c1,n1\nussr,1974,27.9,c1,n1\n")
    with pytest.raises(ValueError, match="duplicate"):
        parse_curated_csv(text)


def test_non_numeric_value_raises_with_line_number():
    text = _valid_csv("ussr,1974,twenty-seven,c1,n1\n")
    with pytest.raises(ValueError, match="line 2"):
        parse_curated_csv(text)


def test_non_integer_year_raises():
    text = _valid_csv("ussr,1974a,27.9,c1,n1\n")
    with pytest.raises(ValueError, match="year"):
        parse_curated_csv(text)


def test_definition_note_is_optional_and_becomes_none():
    text = _valid_csv("ussr,1974,27.9,a citable source,\n")
    records = parse_curated_csv(text)
    assert records[0].definition_note is None
    assert records[0].citation == "a citable source"


# --- Entity resolution: curated resolves by canonical entity_id ---------------


def test_curated_entity_ids_resolve_against_the_real_registry(real_entities: EntityRegistry):
    records = parse_curated_csv(REAL_CSV.read_text(encoding="utf-8"))
    for r in records:
        entity = real_entities.resolve_from_source("curated", r.entity_raw_name, None)
        assert entity is not None, f"curated entity_id {r.entity_raw_name!r} must resolve by id"
        assert entity.entity_id == "ussr"
        assert entity.covers_year(r.year)  # 1922-1991 covers the whole series


def test_curated_typo_lands_in_unresolved_not_silently_dropped(real_entities: EntityRegistry):
    assert real_entities.resolve_from_source("curated", "ussrr", None) is None


# --- Connector behaviour -------------------------------------------------------


def test_connector_is_registered_for_fetch():
    assert Provider.curated in CONNECTORS
    assert CONNECTORS[Provider.curated].provider == "curated"


def test_fetch_raw_reads_the_real_catalog_without_network():
    connector = CuratedConnector(catalog_dir=REAL_CATALOG)
    result = connector.fetch_raw("ussr_infant_mortality_official", "infant_mortality")
    assert isinstance(result, RawFetchResult)
    assert result.provider == "curated"
    assert result.source_ref == "ussr_infant_mortality_official"
    assert result.source_url.endswith("ussr_infant_mortality_official.csv")
    assert len(result.records) == 21
    assert all(r.citation for r in result.records)


def test_fetch_raw_rejects_path_fragments_in_source_ref(tmp_path):
    connector = CuratedConnector(catalog_dir=tmp_path)
    for bad in ("../escape", "a/b", "a\\b", ".."):
        with pytest.raises(ValueError, match="Invalid curated source_ref"):
            connector.fetch_raw(bad, "infant_mortality")


def test_fetch_raw_rejects_field_selection():
    connector = CuratedConnector(catalog_dir=REAL_CATALOG)
    with pytest.raises(ValueError, match="does not support field"):
        connector.fetch_raw("ussr_infant_mortality_official", "infant_mortality", field="rate")


def test_fetch_raw_missing_table_raises_loudly(tmp_path):
    connector = CuratedConnector(catalog_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match="Curated table not found"):
        connector.fetch_raw("nonexistent_series", "infant_mortality")


def test_snapshot_round_trip_through_the_production_writer(tmp_path):
    # The curated source flows through the exact same raw-snapshot path as
    # the network sources: fetch -> data/raw/curated/{indicator}/{ref}/{ts}.json
    from src.pipeline.fetch import _write_snapshot

    connector = CuratedConnector(catalog_dir=REAL_CATALOG)
    result = connector.fetch_raw("ussr_infant_mortality_official", "infant_mortality")
    path = _write_snapshot(result, tmp_path)
    assert path.parent == tmp_path / "curated" / "infant_mortality" / "ussr_infant_mortality_official"

    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["provider"] == "curated"
    assert payload["source_ref"] == "ussr_infant_mortality_official"
    assert payload["records"][0]["citation"]  # provenance survives the round-trip


# --- v21: the extended transcription format (the DYB 1978 tables) -------------


def _extended_csv(rows: str) -> str:
    header = (
        "entity_id,year,value,citation,definition_note,"
        "sex,provisional,quality_code,reference_range\n"
    )
    return header + rows


def test_v21_real_transcription_tables_parse():
    for name, n in (
        ("dyb1978_vanished_crude_birth_rate", 27),
        ("dyb1978_vanished_infant_mortality", 17),
        ("dyb1978_vanished_life_expectancy", 12),
    ):
        records = parse_curated_csv((REAL_CATALOG / f"{name}.csv").read_text(encoding="utf-8"))
        assert len(records) == n


def test_v21_extended_columns_ride_the_record():
    text = _extended_csv(
        'ussr,1972,64,"UN DYB 1978 Table 4","Text-layer read verified",male,false,,1971-1972\n'
        'ussr,1972,74,"UN DYB 1978 Table 4","Text-layer read verified",female,false,,1971-1972\n'
    )
    records = parse_curated_csv(text)
    m, f = records
    assert (m.sex, m.provisional, m.quality_code, m.reference_range) == ("male", False, None, "1971-1972")
    assert (f.sex, f.provisional) == ("female", False)
    # The male/female pair on the same year is legitimate: the duplicate
    # key is (entity, year, SEX) — the merge key downstream.
    assert len(records) == 2


def test_v21_sex_column_validated_loudly():
    text = _extended_csv('ussr,1972,64,"cite","note",both,false,,\n')
    with pytest.raises(ValueError, match="sex 'both'"):
        parse_curated_csv(text)


def test_v21_provisional_column_validated_loudly():
    text = _extended_csv('ussr,1972,64,"cite","note",male,maybe,,\n')
    with pytest.raises(ValueError, match="provisional 'maybe'"):
        parse_curated_csv(text)


def test_v21_duplicate_key_gains_sex():
    # Twice the SAME sex on one (entity, year) is the collision; the pair
    # is not (covered above).
    text = _extended_csv(
        'ussr,1972,64,"cite","note",male,false,,\n'
        'ussr,1972,65,"cite","note",male,false,,\n'
    )
    with pytest.raises(ValueError, match=r"duplicate \(ussr, 1972, male\)"):
        parse_curated_csv(text)


def test_v21_legacy_duplicate_still_raises_with_the_new_key():
    # A 5-column file cannot express sex: two rows on one (entity, year)
    # remain the collision they always were.
    text = _valid_csv('ussr,1972,64,"cite","note"\nussr,1972,65,"cite","note"\n')
    with pytest.raises(ValueError, match=r"duplicate \(ussr, 1972, None\)"):
        parse_curated_csv(text)


def test_v21_a_short_header_between_the_two_forms_raises():
    text = "entity_id,year,value,citation,definition_note,sex\nussr,1972,64,cite,note,male\n"
    with pytest.raises(ValueError, match="header"):
        parse_curated_csv(text)


def test_v21_the_real_tables_resolve_against_the_real_registry(real_entities: EntityRegistry):
    # Every entity_id the three transcription tables carry must exist in
    # the registry — the curated tier resolves by exact id, a typo lands
    # in unresolved.json, so the registry is the gate.
    for name in (
        "dyb1978_vanished_crude_birth_rate",
        "dyb1978_vanished_infant_mortality",
        "dyb1978_vanished_life_expectancy",
    ):
        records = parse_curated_csv((REAL_CATALOG / f"{name}.csv").read_text(encoding="utf-8"))
        for r in records:
            entity = real_entities.resolve_from_source("curated", r.entity_raw_name, None)
            assert entity is not None, (name, r.entity_raw_name)
            # covers_year: every curated year sits inside the entity's
            # lifetime (the vanished entities' dissolution years honored).
            assert entity.covers_year(r.year), (name, r.entity_raw_name, r.year)
