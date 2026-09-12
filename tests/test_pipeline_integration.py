import json
from pathlib import Path

import pytest

from tests.conftest import (
    seed_curated_snapshot,
    seed_dyb_snapshot,
    seed_dyb_table4_snapshot,
    seed_oecd_snapshot,
    seed_owid_snapshot,
)

from src.pipeline.build import build_all
from src.pipeline.merge import merge_all
from src.pipeline.normalize import normalize_all
from src.pipeline.validate import validate_all


def _run_pipeline(tmp_path: Path, real_indicators, real_entities):
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    dist_dir = tmp_path / "dist"
    reports_dir = tmp_path / "reports"

    # infant_mortality seeds all three tiers (ADR-0008): curated (real
    # committed catalog), un_dyb (fixture), owid witness (fixture).
    # life_expectancy seeds its two tiers: un_dyb Table 4 canonical (the
    # sex-split as-reported collector) + owid witness (both-sexes, long
    # historical span including the defunct entities).
    seed_curated_snapshot(raw_dir, "infant_mortality")
    seed_dyb_snapshot(raw_dir, "infant_mortality")
    seed_dyb_table4_snapshot(raw_dir, "life_expectancy")
    seed_owid_snapshot(raw_dir, "infant_mortality", "infant-mortality", "owid_infant_mortality.csv")
    seed_owid_snapshot(raw_dir, "life_expectancy", "life-expectancy", "owid_life_expectancy.csv")
    seed_owid_snapshot(raw_dir, "homicide_rate", "homicide-rate-unodc", "owid_homicide_rate.csv")
    # homicide_rate: the P3 two-tier wiring — OECD DF_COM (WHO Mortality
    # Database, collector) canonical + UNODC via OWID witness.
    seed_oecd_snapshot(raw_dir, "homicide_rate")

    normalize_all(real_indicators, raw_dir, processed_dir, real_entities)
    merge_all(list(real_indicators.keys()), processed_dir)
    validate_results = validate_all(real_indicators, processed_dir, real_entities, reports_dir)
    build_all(real_indicators, processed_dir, dist_dir, real_entities)

    return processed_dir, dist_dir, reports_dir, validate_results


def test_full_pipeline_produces_the_expected_dist_files(tmp_path, real_indicators, real_entities):
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)

    assert (dist_dir / "catalog.json").exists()
    assert (dist_dir / "entities.json").exists()
    assert (dist_dir / "indicators" / "infant_mortality.json").exists()
    assert (dist_dir / "indicators" / "life_expectancy.json").exists()
    assert (dist_dir / "indicators" / "homicide_rate.json").exists()

    catalog = json.loads((dist_dir / "catalog.json").read_text())
    assert {c["id"] for c in catalog} == {"infant_mortality", "life_expectancy", "homicide_rate"}


def test_ussr_official_series_is_canonical_with_per_point_citations(tmp_path, real_indicators, real_entities):
    # ADR-0008 (Technique A): the founding tracer enters the canonical
    # series through the CURATED tier — the official Soviet series, one
    # citation per point — not through any harmonized source.
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "infant_mortality.json").read_text())

    ussr = [d for d in payload["data"] if d["entity_id"] == "ussr"]
    assert len(ussr) == 21  # 1970-1990, complete official series
    by_year = {d["year"]: d for d in ussr}
    assert by_year[1971]["value"] == pytest.approx(22.9)
    assert by_year[1974]["value"] == pytest.approx(27.9)
    assert by_year[1976]["value"] == pytest.approx(31.4)  # the peak
    assert by_year[1990]["value"] == pytest.approx(21.8)
    assert all(d["provider"] == "curated" for d in ussr)
    assert all(d["citation"] for d in ussr)  # curation gate (c): no citation, no entry
    assert all(d["definition_note"] for d in ussr)

    # The canonical series contains NO harmonized point: witnesses never
    # merge into it (the whole point of Technique A).
    assert all(d["provider"] != "owid" for d in payload["data"])

    # The dist declares the three sources with roles and layers.
    sources = {(s["provider"], s["source_ref"]): s for s in payload["sources"]}
    assert sources[("curated", "ussr_infant_mortality_official")]["role"] == "canonical"
    assert sources[("curated", "ussr_infant_mortality_official")]["layer"] == "curated"
    assert sources[("un_dyb", "2024/table15")]["role"] == "canonical"
    assert sources[("un_dyb", "2024/table15")]["layer"] == "collector"
    assert sources[("owid", "infant-mortality")]["role"] == "witness"
    assert sources[("owid", "infant-mortality")]["layer"] == "harmonized"
    assert sources[("owid", "infant-mortality")]["native_unit"] == "deaths_per_100_births"


def test_owid_witness_series_is_converted_to_per_1000(tmp_path, real_indicators, real_entities):
    # The witness rides BESIDE the canonical series (never merged) and is
    # unit-converted through the declared table: the OWID fixture is a
    # percentage, the canonical unit is per-1,000 (x10).
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "infant_mortality.json").read_text())

    witness = next(w for w in payload["witnesses"] if w["provider"] == "owid")
    assert witness["source_ref"] == "infant-mortality"
    assert witness["layer"] == "harmonized"
    assert witness["unit"] == "deaths_per_1000_births"
    assert witness["native_unit"] == "deaths_per_100_births"

    russia = {p["year"]: p["value"] for p in witness["data"] if p["entity_id"] == "russian_federation"}
    assert russia[1970] == pytest.approx(24.7)  # 2.47 percent x 10
    assert russia[2023] == pytest.approx(4.0)  # 0.40 percent x 10


def test_dyb_canonical_points_come_from_the_collector_tier(tmp_path, real_indicators, real_entities):
    # Canonical source #2: the as-reported DYB rates (fixture: France
    # 2020-2024, Algeria rates explicitly absent per the UN's own
    # completeness rule — an honest gap, not a zero).
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "infant_mortality.json").read_text())

    dyb_points = [d for d in payload["data"] if d["provider"] == "un_dyb"]
    france = {d["year"]: d["value"] for d in dyb_points if d["entity_id"] == "france"}
    assert france[2020] == pytest.approx(3.3746540657)
    assert france[2024] == pytest.approx(3.8378378378)
    # Algeria reported counts but no rates (quality "U"): no canonical
    # point is fabricated for it.
    assert all(d["entity_id"] != "algeria" for d in payload["data"])


def test_russia_continuity_moves_to_the_witness_series(tmp_path, real_indicators, real_entities):
    # Decision made in conversation, after confirming live that OWID has no
    # standalone USSR entity in this indicator's data: pre- and post-1991
    # Russia data is shown as a single continuous series (not split into a
    # fabricated separate "ussr" series), with a warning carried on the
    # entity metadata (see test_entities_json_flags_soviet_era_data).
    # Under ADR-0008 the OWID series is the WITNESS: Russia's continuity
    # across 1991 lives there, while the canonical tier honestly shows the
    # DYB 2024 hole (Russia absent from the collector's questionnaire —
    # coverage data, not an error to patch).
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "infant_mortality.json").read_text())

    # Canonical: the collector hole stays visible — no Russia point.
    assert all(d["entity_id"] != "russian_federation" for d in payload["data"])

    witness = next(w for w in payload["witnesses"] if w["provider"] == "owid")
    russia_years = {p["year"] for p in witness["data"] if p["entity_id"] == "russian_federation"}
    assert russia_years == {1958, 1970, 1990, 1992, 2000, 2023}

    # No "ussr" entity_id appears in the witness either: this source never
    # emits USSR-labeled rows (confirmed live).
    assert all(p["entity_id"] != "ussr" for p in witness["data"])


def test_entities_json_flags_soviet_era_data(tmp_path, real_indicators, real_entities):
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    entities = json.loads((dist_dir / "entities.json").read_text())
    by_id = {e["entity_id"]: e for e in entities}

    russia = by_id["russian_federation"]
    assert russia["formerly_part_of"] is not None
    assert russia["formerly_part_of"]["union_entity_id"] == "ussr"
    assert russia["formerly_part_of"]["until_year"] == 1991

    # Unrelated entities must not carry the flag.
    assert by_id["france"]["formerly_part_of"] is None


def test_unknown_entity_wakanda_absent_from_dist_but_logged(tmp_path, real_indicators, real_entities):
    processed_dir, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)

    payload = json.loads((dist_dir / "indicators" / "infant_mortality.json").read_text())
    assert all(d["entity_id"] != "wakanda" for d in payload["data"])

    unresolved = json.loads((processed_dir / "infant_mortality.unresolved.json").read_text())
    assert "Wakanda" in unresolved["infant-mortality"]["possible_mapping_gap"]


def test_unresolved_names_are_classified_owid_special_vs_mapping_gap(tmp_path, real_indicators, real_entities):
    processed_dir, _, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)

    unresolved = json.loads((processed_dir / "homicide_rate.unresolved.json").read_text())
    bucket = unresolved["homicide-rate-unodc"]
    # "World" has Code=OWID_WRL in the fixture: an OWID aggregate, expected.
    assert "World" in bucket["owid_special"]
    # "Freedonia" has no code: most likely a real mapping gap, not an aggregate.
    assert "Freedonia" in bucket["possible_mapping_gap"]


def test_east_and_west_germany_resolve_despite_owid_prefixed_codes(tmp_path, real_indicators, real_entities):
    # Regression test for the docstring/behaviour fix: OWID_-prefixed codes
    # must not prevent name-based fallback resolution. Since P3 the OWID
    # series is homicide's WITNESS: the defunct German entities live there,
    # while the canonical OECD tier honestly has no 1988 DDR/FRG rows.
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "homicide_rate.json").read_text())
    canonical_ids = {d["entity_id"] for d in payload["data"]}
    witness = next(w for w in payload["witnesses"] if w["provider"] == "owid")
    witness_ids = {p["entity_id"] for p in witness["data"]}
    assert "east_germany" in witness_ids
    assert "west_germany" in witness_ids
    assert "east_germany" not in canonical_ids


def test_out_of_range_value_detected_for_homicide_rate(tmp_path, real_indicators, real_entities):
    # The fixture's 999.0 (France 1975) rides the OWID series, homicide's
    # WITNESS since P3 — and validate checks witnesses exactly like the
    # canonical tier (a bad witness is as damaging as a bad canonical).
    _, _, _, validate_results = _run_pipeline(tmp_path, real_indicators, real_entities)

    homicide_result = next(r for r in validate_results if r["indicator_id"] == "homicide_rate")
    assert homicide_result["range_violations"] == []
    witness = next(w for w in homicide_result["witnesses"] if w["provider"] == "owid")
    assert len(witness["range_violations"]) == 1
    violation = witness["range_violations"][0]
    assert violation["entity_id"] == "france"
    assert violation["value"] == 999.0


def test_no_violation_for_infant_mortality_with_corrected_unit(tmp_path, real_indicators, real_entities):
    # Regression test for the unit bug: fixture values are now expressed as
    # a percentage (matching config), so none should trip plausible_range.
    _, _, _, validate_results = _run_pipeline(tmp_path, real_indicators, real_entities)
    im_result = next(r for r in validate_results if r["indicator_id"] == "infant_mortality")
    assert im_result["range_violations"] == []
    assert im_result["duplicate_entity_year"] == []


def test_coverage_report_generated_and_readable(tmp_path, real_indicators, real_entities):
    _, _, reports_dir, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    report = (reports_dir / "coverage_report.md").read_text(encoding="utf-8")
    assert "infant_mortality" in report
    # Canonical coverage table: entity labels flow into the readable report.
    # Under ADR-0008 the canonical entities are the as-reported tier —
    # "Soviet Union" (curated ussr series) and "Czechia" (life expectancy,
    # the DYB Table 4 fixture); "Russia" is witness-only now (the DYB 2024
    # collector hole), so it appears in the witness summary.
    assert "Soviet Union" in report
    assert "Czechia" in report
    # The witness series get their own summary lines.
    assert "Witness `owid:infant-mortality`" in report
    assert "Witness `owid:life-expectancy`" in report


def test_life_expectancy_canonical_is_sex_split_witness_is_both_sexes(tmp_path, real_indicators, real_entities):
    # The two-tier life_expectancy wiring (P1): canonical = un_dyb Table 4,
    # as-reported, sex-split (Male/Female as PRINTED — averaging would be a
    # derivation); witness = OWID both-sexes long-run series. Historical
    # entities (Czechoslovakia) live in the WITNESS tier now — the collector
    # windows 2007-2024 cannot contain them by construction.
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "life_expectancy.json").read_text())

    # Canonical: DYB points only, every point sex-split, both sexes present.
    canonical = [d for d in payload["data"]]
    assert canonical
    assert all(d["provider"] == "un_dyb" for d in canonical)
    assert all(d["sex"] in ("male", "female") for d in canonical)
    france = {(d["year"], d["sex"]): d["value"] for d in canonical if d["entity_id"] == "france"}
    assert france[(2020, "male")] == pytest.approx(79.1)
    assert france[(2020, "female")] == pytest.approx(85.6)
    # A year row with no printed LE produces NO canonical point (the
    # canonical tier carries actual values only; explicit gap-POINTS are a
    # witness-tier concept — see merge.py). Algeria 2021: "..." for both
    # sexes -> nothing is fabricated, nothing is kept as a fake point.
    algeria_years = {(d["year"], d["sex"]) for d in canonical if d["entity_id"] == "algeria"}
    assert (2021, "male") not in algeria_years
    assert (2021, "female") not in algeria_years
    assert (2020, "male") in algeria_years

    # Defunct + successor entities coexist in the WITNESS series.
    witness = next(w for w in payload["witnesses"] if w["provider"] == "owid")
    witness_entities = {p["entity_id"] for p in witness["data"]}
    assert "czechoslovakia" in witness_entities
    assert "czechia" in witness_entities
    assert "slovakia" in witness_entities


# --- P2: quality annotations + citation blocks in the dist contract ----------

def test_dist_sources_carry_citation_blocks(tmp_path, real_indicators, real_entities):
    # The external review's gap: witness sources had no citation/url/licence.
    # Now every declared source (witnesses included) carries the block.
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "infant_mortality.json").read_text())

    sources = {(s["provider"], s["source_ref"]): s for s in payload["sources"]}
    dyb = sources[("un_dyb", "2024/table15")]
    assert dyb["citation"] == (
        "United Nations Statistics Division, Demographic Yearbook 2024, Table 15"
    )
    assert dyb["url"].endswith("DYB2024/table15.xls")
    assert "UN data reuse policy" in dyb["license"]

    owid = sources[("owid", "infant-mortality")]
    assert owid["citation"] == "Our World in Data, grapher dataset 'infant-mortality'"
    assert owid["url"] == "https://ourworldindata.org/grapher/infant-mortality"
    assert owid["license"] == "CC-BY-4.0"

    curated = sources[("curated", "ussr_infant_mortality_official")]
    assert "catalog/curated" in curated["citation"]

    # The WITNESS series entries carry their own citation block too.
    witness = next(w for w in payload["witnesses"] if w["provider"] == "owid")
    assert witness["citation"] == "Our World in Data, grapher dataset 'infant-mortality'"
    assert witness["url"] == "https://ourworldindata.org/grapher/infant-mortality"
    assert witness["license"] == "CC-BY-4.0"


def test_dist_points_carry_the_collectors_quality_annotations(tmp_path, real_indicators, real_entities):
    # The as-reported tier's payload: France's canonical IMR point carries
    # the DYB's own quality code + provisional flag + footnote refs.
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "infant_mortality.json").read_text())

    france = {d["year"]: d for d in payload["data"] if d["entity_id"] == "france"}
    assert france[2020]["quality_code"] == "C"
    assert france[2020]["provisional"] is True
    assert france[2021]["footnote_refs"] == ["1"]
    assert france[2021].get("provisional") is None  # optional field: absent when unset
    assert france[2022]["quality_code"] == "C"  # rides every DYB point

    # The footnote TEXT of the ref the point carries ships per source, with
    # the legend that decodes the quality codes.
    dyb_source = next(s for s in payload["sources"] if s["provider"] == "un_dyb")
    assert "Civil registration" in dyb_source["footnotes"]["legend"]["a"]
    assert dyb_source["footnotes"]["notes"]["1"] == "Data refer to the de facto population."
    assert set(dyb_source["footnotes"]["notes"]) == {"1"}  # restricted to referenced refs


def test_dist_life_expectancy_points_carry_reference_ranges(tmp_path, real_indicators, real_entities):
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "life_expectancy.json").read_text())

    algeria = {(d["year"], d["sex"]): d for d in payload["data"] if d["entity_id"] == "algeria"}
    assert algeria[(2020, "male")]["reference_range"] == "III"
    france = {(d["year"], d["sex"]): d for d in payload["data"] if d["entity_id"] == "france"}
    assert france[(2021, "male")]["reference_range"] == "V"
    assert france[(2021, "male")]["footnote_refs"] == ["5"]

    dyb_source = next(s for s in payload["sources"] if s["provider"] == "un_dyb")
    assert "reference period" in dyb_source["footnotes"]["legend"]["b"]
    assert "de facto population present" in dyb_source["footnotes"]["notes"]["5"]


def test_homicide_rate_is_two_tier_with_the_sex_split(tmp_path, real_indicators, real_entities):
    # P3: the third pilot gets the ADR-0008 treatment — canonical = OECD
    # DF_COM (WHO Mortality Database registrations, collector), witness =
    # UNODC via OWID. The canonical carries the as-reported sex split
    # (Russia 1994: male 63.3 vs female 14.3 — the crisis peak).
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "homicide_rate.json").read_text())

    sources = {(s["provider"], s["source_ref"]): s for s in payload["sources"]}
    assert sources[("oecd", "DF_COM/CICDHOCD")]["role"] == "canonical"
    assert sources[("oecd", "DF_COM/CICDHOCD")]["layer"] == "collector"
    assert sources[("owid", "homicide-rate-unodc")]["role"] == "witness"
    assert "WHO Mortality Database" in sources[("oecd", "DF_COM/CICDHOCD")]["citation"]
    assert sources[("oecd", "DF_COM/CICDHOCD")]["url"].startswith("https://sdmx.oecd.org/")

    canonical = [d for d in payload["data"]]
    assert all(d["provider"] == "oecd" for d in canonical)
    russia = {(d["year"], d.get("sex")): d["value"] for d in canonical if d["entity_id"] == "russian_federation"}
    assert russia[(1994, None)] == pytest.approx(32.3)
    assert russia[(1994, "male")] == pytest.approx(63.3)
    assert russia[(1994, "female")] == pytest.approx(14.3)
    # The empty 2021 French OBS_VALUE: no canonical point fabricated.
    france_years = {(d["year"], d.get("sex")) for d in canonical if d["entity_id"] == "france"}
    assert (2021, None) not in france_years
    assert (2020, None) in france_years
    # No harmonized point in the canonical series.
    assert all(d["provider"] != "owid" for d in canonical)

    witness = next(w for w in payload["witnesses"] if w["provider"] == "owid")
    assert witness["layer"] == "harmonized"
    assert witness["unit"] == "deaths_per_100000_population"
