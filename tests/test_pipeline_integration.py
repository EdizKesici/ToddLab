import json
from pathlib import Path

import pytest

from tests.conftest import (
    seed_curated_snapshot,
    seed_dyb_snapshot,
    seed_dyb_table17_snapshot,
    seed_dyb_table21_snapshot,
    seed_dyb_table4_snapshot,
    seed_dyb_table9_snapshot,
    seed_eurostat_snapshot,
    seed_gho_snapshot,
    seed_oecd_snapshot,
    seed_owid_snapshot,
    seed_wb_snapshot,
)

from src.config_loader import cross_validate_todd_core, load_todd_refs
from src.pipeline.build import build_all
from src.pipeline.merge import merge_all
from src.pipeline.normalize import normalize_all
from src.pipeline.validate import validate_all
from tests.conftest import CONFIG_DIR


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
    # maternal_mortality_ratio seeds its two tiers (P3b) + the v12
    # additions: un_dyb Table 17 canonical (fixture) + the two MMEIG
    # witness doors (owid fixture + worldbank SH.STA.MMRT).
    # maternal_deaths (v12, the counts half) seeds the SAME Table 17
    # fixture at the number block + its worldbank SH.MMR.DTHS witness.
    # life_expectancy_60 seeds its two tiers (v10): un_dyb Table 21
    # canonical (the age-column selector on "60") + who_gho witness (the
    # first GHO connector, WHOSIS_000015).
    seed_curated_snapshot(raw_dir, "infant_mortality")
    seed_dyb_snapshot(raw_dir, "infant_mortality")
    seed_dyb_table4_snapshot(raw_dir, "life_expectancy")
    seed_dyb_table17_snapshot(raw_dir, "maternal_mortality_ratio")
    seed_dyb_table17_snapshot(raw_dir, "maternal_deaths", block="number")
    seed_dyb_table21_snapshot(raw_dir, "life_expectancy_60")
    seed_gho_snapshot(raw_dir, "life_expectancy_60")
    seed_owid_snapshot(raw_dir, "infant_mortality", "infant-mortality", "owid_infant_mortality.csv")
    seed_owid_snapshot(raw_dir, "life_expectancy", "life-expectancy", "owid_life_expectancy.csv")
    seed_owid_snapshot(raw_dir, "homicide_rate", "homicide-rate-unodc", "owid_homicide_rate.csv")
    seed_owid_snapshot(
        raw_dir, "maternal_mortality_ratio", "maternal-mortality", "owid_maternal_mortality.csv",
        value_field="Maternal mortality ratio",
    )
    # homicide_rate: the P3 two-tier wiring — OECD DF_COM (WHO Mortality
    # Database, collector) canonical + UNODC via OWID witness.
    seed_oecd_snapshot(raw_dir, "homicide_rate")
    # suicide_rate (v13, the corpus's #2): the homicide architecture one
    # cause-code away — OECD CICDHARM canonical (as-reported, sex-split,
    # RUS 1994 M 73.9 / F 13.2, RUS 2000 M 69.8, LTU 1994 M 83.5) + the
    # GHE witness through GHO SDGSUICIDE (Dim2 AGEGROUP: all-ages kept,
    # age slices dropped — RUS 2000 M 95.2 modeled vs 69.8 as-reported,
    # the ill-defined redistribution made visible).
    seed_oecd_snapshot(raw_dir, "suicide_rate", "DF_COM/CICDHARM", fixture="oecd_suicide_sdmx.csv")
    seed_gho_snapshot(raw_dir, "suicide_rate", "SDGSUICIDE", fixture="gho_sdgsuicide_sample.json")
    # v11 (P5): the World Bank doors — IMR sex-split (MA/FE) + LE
    # sex-split (MA/FE), and the third IGME door on IMR (GHO
    # MDG_0000000001, seeded through the same GHO fixture: the connector
    # is code-agnostic, the rows are).
    seed_wb_snapshot(raw_dir, "infant_mortality", "SP.DYN.IMRT.MA.IN")
    seed_wb_snapshot(raw_dir, "infant_mortality", "SP.DYN.IMRT.FE.IN")
    seed_wb_snapshot(raw_dir, "life_expectancy", "SP.DYN.LE00.MA.IN")
    seed_wb_snapshot(raw_dir, "life_expectancy", "SP.DYN.LE00.FE.IN")
    seed_gho_snapshot(raw_dir, "infant_mortality", "MDG_0000000001")
    # v12 (the maternal bloc): the two WDI maternal doors.
    seed_wb_snapshot(raw_dir, "maternal_mortality_ratio", "SH.STA.MMRT")
    seed_wb_snapshot(raw_dir, "maternal_deaths", "SH.MMR.DTHS")
    # v14 (the corpus's #1): birth_rate_fertility seeds its four sources —
    # the Eurostat collector main slice (the codelist quirks, the DE_TOT
    # duplicate, the aggregate drop) + the two geo-pinned French series
    # (FX metro 1960-2012, FR whole 1998-2024 — the seam the merge
    # arbitrates by priority) + the WPP witness through WDI's TFRT door
    # (the dedicated TFR-plausible page fixture).
    seed_eurostat_snapshot(raw_dir, "birth_rate_fertility")
    seed_eurostat_snapshot(raw_dir, "birth_rate_fertility", "demo_find/TOTFERRT/FR", fixture="eurostat_totferrt_fr_sample.json")
    seed_eurostat_snapshot(raw_dir, "birth_rate_fertility", "demo_find/TOTFERRT/FX", fixture="eurostat_totferrt_fx_sample.json")
    seed_wb_snapshot(raw_dir, "birth_rate_fertility", "SP.DYN.TFRT.IN")
    # v15 (the CBR companion + the markers): crude_birth_rate seeds its
    # two tiers — DYB Table 9 canonical (the collector's natalité print,
    # the Table 15 wide layout through the v15 dispatch branch: the
    # '*NN' star-plus-ref marker, the '+U' honest rate gaps, the second
    # Total row under a different quality code) + the WPP witness through
    # WDI's CBRT door (the dedicated CBR-plausible page fixture — the
    # shared IMRT page's per-1,000 prints would read as plausible CBR
    # and contaminate silently). The two markers seed through the REAL
    # committed curated tables (the connector reads catalog/curated/,
    # network-free by construction) — same_sex (33 countries, the
    # 'religion zero' chain's own dating) and universal_suffrage (16
    # countries, the historiography's own dating).
    seed_dyb_table9_snapshot(raw_dir, "crude_birth_rate")
    seed_wb_snapshot(raw_dir, "crude_birth_rate", "SP.DYN.CBRT.IN")
    seed_curated_snapshot(raw_dir, "same_sex_marriage_legalization_year", "same_sex_marriage_legalization")
    seed_curated_snapshot(raw_dir, "universal_suffrage_introduction_year", "universal_suffrage_introduction")
    # v16 (the corpus's illégitimité): illegitimate_births seeds its five
    # sources — the DE_TOT geo-pinned German series door (the seam that
    # outranks the main slice: the all-Germany print wins, every DE
    # collision a logged discard — the FX/FR architecture applied to a
    # definitional seam) + the Eurostat main slice (the variant drops,
    # the EL 'b' / MD 'p' flags) + the two geo-pinned French series (the
    # TFR seam's mirror) + the OECD Family Database witness through
    # OWID's chart door (the 42-entity worldwide-OECD face).
    seed_eurostat_snapshot(raw_dir, "illegitimate_births", "demo_find/NMARPCT", fixture="eurostat_nmarpct_sample.json")
    seed_eurostat_snapshot(raw_dir, "illegitimate_births", "demo_find/NMARPCT/DE_TOT", fixture="eurostat_nmarpct_de_tot_sample.json")
    seed_eurostat_snapshot(raw_dir, "illegitimate_births", "demo_find/NMARPCT/FR", fixture="eurostat_nmarpct_fr_sample.json")
    seed_eurostat_snapshot(raw_dir, "illegitimate_births", "demo_find/NMARPCT/FX", fixture="eurostat_nmarpct_fx_sample.json")
    seed_owid_snapshot(raw_dir, "illegitimate_births", "share-of-births-outside-marriage", "owid_nmarpct_sample.csv")
    # v17 (the corpus's #6, the backlog's head): consanguineous_marriage_rate
    # seeds through the REAL committed curated table (102 rows, 69
    # countries — the Bittles-compilation prints plus the directly-verified
    # DHS/journal readings), network-free by construction like the markers.
    seed_curated_snapshot(raw_dir, "consanguineous_marriage_rate", "consanguineous_marriage_rate")
    # v17 (the economy family's first indicator): unemployment_rate seeds
    # its two tiers — the Eurostat LFS collector (une_rt_a pinned
    # Y15-74/PC_ACT/T: the FR full-length series with the 2021-2025 'd'
    # definitional seam, the DE coverage cliff 2009, the ES/EL 2013
    # crisis peaks, the ME stop at 2020, the EU27 aggregate drop) + the
    # WB national-estimate witness (the dedicated page carrying the
    # 1990-2002 years the collector lacks and the rounding seam).
    seed_eurostat_snapshot(raw_dir, "unemployment_rate", "une_rt_a/Y15-74/PC_ACT/T", fixture="eurostat_unert_sample.json")
    seed_wb_snapshot(raw_dir, "unemployment_rate", "SL.UEM.TOTL.NE.ZS")

    # v13: the corpus loads exactly like cmd_rebuild's _load_config does
    # (load + cross-validate) — the integration tests therefore exercise
    # the REAL committed config surface, cross-validation included.
    todd_refs = load_todd_refs(CONFIG_DIR)
    cross_validate_todd_core(real_indicators, todd_refs)

    normalize_all(real_indicators, raw_dir, processed_dir, real_entities)
    merge_all(list(real_indicators.keys()), processed_dir)
    validate_results = validate_all(real_indicators, processed_dir, real_entities, reports_dir)
    build_all(real_indicators, processed_dir, dist_dir, real_entities, todd_refs=todd_refs)

    return processed_dir, dist_dir, reports_dir, validate_results


def test_full_pipeline_produces_the_expected_dist_files(tmp_path, real_indicators, real_entities):
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)

    assert (dist_dir / "catalog.json").exists()
    assert (dist_dir / "entities.json").exists()
    assert (dist_dir / "todd_corpus.json").exists()
    assert (dist_dir / "indicators" / "infant_mortality.json").exists()
    assert (dist_dir / "indicators" / "life_expectancy.json").exists()
    assert (dist_dir / "indicators" / "homicide_rate.json").exists()
    assert (dist_dir / "indicators" / "maternal_mortality_ratio.json").exists()
    assert (dist_dir / "indicators" / "maternal_deaths.json").exists()
    assert (dist_dir / "indicators" / "life_expectancy_60.json").exists()
    assert (dist_dir / "indicators" / "suicide_rate.json").exists()
    assert (dist_dir / "indicators" / "birth_rate_fertility.json").exists()
    assert (dist_dir / "indicators" / "crude_birth_rate.json").exists()
    assert (dist_dir / "indicators" / "same_sex_marriage_legalization_year.json").exists()
    assert (dist_dir / "indicators" / "universal_suffrage_introduction_year.json").exists()
    assert (dist_dir / "indicators" / "illegitimate_births.json").exists()
    assert (dist_dir / "indicators" / "consanguineous_marriage_rate.json").exists()
    assert (dist_dir / "indicators" / "unemployment_rate.json").exists()

    catalog = json.loads((dist_dir / "catalog.json").read_text())
    assert {c["id"] for c in catalog} == {
        "infant_mortality", "life_expectancy", "homicide_rate", "maternal_mortality_ratio",
        "maternal_deaths", "life_expectancy_60", "suicide_rate", "birth_rate_fertility",
        "crude_birth_rate", "same_sex_marriage_legalization_year",
        "universal_suffrage_introduction_year", "illegitimate_births",
        "consanguineous_marriage_rate", "unemployment_rate",
    }


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
    # Algeria reported counts but no rates (quality "U"): v9 merge
    # semantics — the canonical series carries ONE explicit gap point per
    # year (value=None, the collector's own code riding it), never a
    # fabricated value and never a silent absence.
    algeria = {d["year"]: d for d in dyb_points if d["entity_id"] == "algeria"}
    assert algeria
    assert all(d["value"] is None for d in algeria.values())
    assert all(d["quality_code"] == "U" for d in algeria.values())


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
    # A year row with no printed LE now produces explicit gap POINTS in
    # the canonical series (v9 merge semantics — same honesty the witness
    # tier always had): Algeria 2021 "..." for both sexes -> value=None
    # points, never a fabricated value, never a silent absence.
    algeria = {(d["year"], d["sex"]): d["value"] for d in canonical if d["entity_id"] == "algeria"}
    assert algeria[(2021, "male")] is None
    assert algeria[(2021, "female")] is None
    assert algeria[(2020, "male")] == pytest.approx(74.2)

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
    # (Russia 1994: male 52.5 vs female 14.3 — the crisis peak, crude).
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
    assert russia[(1994, "male")] == pytest.approx(52.5)
    assert russia[(1994, "female")] == pytest.approx(14.3)
    # The empty 2021 French OBS_VALUE: v9 — an explicit gap POINT appears
    # (value=None, nothing fabricated), distinct from absent years.
    france_years = {(d["year"], d.get("sex")): d["value"] for d in canonical if d["entity_id"] == "france"}
    assert france_years[(2021, None)] is None
    assert france_years[(2020, None)] == pytest.approx(0.6)
    # No harmonized point in the canonical series.
    assert all(d["provider"] != "owid" for d in canonical)

    witness = next(w for w in payload["witnesses"] if w["provider"] == "owid")
    assert witness["layer"] == "harmonized"
    assert witness["unit"] == "deaths_per_100000_population"


# --- P3b: maternal_mortality_ratio, the fourth indicator (v9) -----------------


def test_maternal_mortality_is_two_tier_with_honest_degradation(tmp_path, real_indicators, real_entities):
    # P3b: canonical = DYB Table 17 (as-reported counts + the UNSD-computed
    # ratio the collector publishes), witness = UN MMEIG modeled estimates
    # via OWID. The fixture's Libya prints counts but NO ratio row (the
    # collector's editorial rule): v9 keeps those keys as explicit gap
    # points carrying the printed "+U" code — "reported, but no ratio
    # computed" is data, not absence.
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "maternal_mortality_ratio.json").read_text())

    sources = {(s["provider"], s["source_ref"]): s for s in payload["sources"]}
    assert sources[("un_dyb", "2024/table17")]["role"] == "canonical"
    assert sources[("un_dyb", "2024/table17")]["layer"] == "collector"
    assert sources[("owid", "maternal-mortality")]["role"] == "witness"
    assert "Demographic Yearbook" in sources[("un_dyb", "2024/table17")]["citation"]

    canonical = [d for d in payload["data"]]
    assert all(d["provider"] == "un_dyb" for d in canonical)

    # France: valued ratios, the 2023 one ♦-marked (small base) with its
    # footnote joined from the Footnotes worksheet.
    france = {d["year"]: d for d in canonical if d["entity_id"] == "france"}
    assert france[2019]["value"] == pytest.approx(4.86)
    assert france[2023]["small_base"] is True
    assert france[2023]["footnote_refs"] == ["1"]
    notes = sources[("un_dyb", "2024/table17")]["footnotes"]["notes"]
    assert "The code is C" in notes["1"]

    # Russia 2019: the Chechnya-style territorial caveat rides the point.
    russia = {d["year"]: d for d in canonical if d["entity_id"] == "russian_federation"}
    assert russia[2019]["value"] == pytest.approx(11.39)
    assert russia[2019]["footnote_refs"] == ["5"]
    assert "cause of death do not include" in notes["5"]

    # Printed-but-empty rate cells ("...") become explicit gap points with
    # the collector's own code riding them — "reported, but no ratio
    # computed" is data, not absence. Algeria 2022 and Russia 2023-24 print
    # "..." in the fixture's Rate rows. (Nuance: a Number-ONLY country like
    # Libya — the collector publishes counts and no rate row at all —
    # leaves NO point in the ratio indicator, the same counts-block scope
    # limit as infant_mortality's Table 15.)
    algeria_gap = {d["year"]: d for d in canonical if d["entity_id"] == "algeria" and d["value"] is None}
    assert 2022 in algeria_gap
    assert algeria_gap[2022]["quality_code"] == "C"
    assert algeria_gap[2022]["missing_marker"] == "..."
    russia_gap = {d["year"]: d for d in canonical if d["entity_id"] == "russian_federation" and d["value"] is None}
    assert {2023, 2024} <= set(russia_gap)
    assert all(d["quality_code"] == "+C" for d in russia_gap.values())

    # The witness rides beside: MMEIG estimates, Libya INCLUDED (the
    # modeled tier exists precisely where registration cannot serve).
    witness = next(w for w in payload["witnesses"] if w["provider"] == "owid")
    witness_libya = {p["year"]: p["value"] for p in witness["data"] if p["entity_id"] == "libya"}
    assert witness_libya[2020] == pytest.approx(71.1)


def test_maternal_witness_high_values_do_not_trip_the_shared_bound(tmp_path, real_indicators, real_entities):
    # The plausible_range (0-4000) is deliberately wide: the canonical
    # as-reported band and the MMEIG modeled band differ by construction
    # (Chad 1194 in the witness fixture is a REAL modeled value). A tighter
    # bound would flag thousands of legitimate witness points on every
    # build — cry-wolf; the net exists for conversion errors, not tier
    # divergence.
    _, _, _, validate_results = _run_pipeline(tmp_path, real_indicators, real_entities)
    maternal = next(r for r in validate_results if r["indicator_id"] == "maternal_mortality_ratio")
    assert maternal["range_violations"] == []
    assert all(w["range_violations"] == [] for w in maternal["witnesses"])


def test_maternal_diamond_small_base_reaches_the_witness_payload_shape(tmp_path, real_indicators, real_entities):
    # The witnesses[] point dicts omit provider/source_ref (inherited from
    # the series) — the small_base transport must not depend on them.
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "maternal_mortality_ratio.json").read_text())
    canonical_mauritius = [
        d for d in payload["data"] if d["entity_id"] == "mauritius" and d.get("small_base")
    ]
    assert canonical_mauritius  # every Mauritius ratio is ♦-marked in the fixture


def test_maternal_deaths_is_two_tier_and_serves_the_number_only_countries(tmp_path, real_indicators, real_entities):
    # v12, the counts half of the maternal bloc: canonical = the Table 17
    # Number rows (registered maternal deaths), witness = the MMEIG modeled
    # counts via the World Bank. The indicator exists BECAUSE of the
    # Number-ONLY countries: Libya prints counts but no ratio row (the
    # collector's editorial rule) and therefore leaves NO point in the
    # ratio indicator — here it finally has a series. The v9 yaml note
    # ("wiring the counts as a second indicator is a separate decision")
    # is closed by this test's existence.
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "maternal_deaths.json").read_text())

    sources = {(s["provider"], s["source_ref"]): s for s in payload["sources"]}
    assert sources[("un_dyb", "2024/table17")]["role"] == "canonical"
    assert sources[("worldbank", "SH.MMR.DTHS")]["role"] == "witness"
    assert sources[("worldbank", "SH.MMR.DTHS")]["root"] == "un_mmeig"
    assert sources[("un_dyb", "2024/table17")]["native_unit"] is None  # counts are the canonical unit
    assert "Demographic Yearbook" in sources[("un_dyb", "2024/table17")]["citation"]

    # Libya — THE Number-only country of the fixture — materializes here
    # with its registered count, quality code and all, where the ratio
    # indicator keeps it absent.
    libya = {d["year"]: d for d in payload["data"] if d["entity_id"] == "libya"}
    assert libya[2022]["value"] == pytest.approx(12.0)
    assert libya[2022]["quality_code"] == "+U"
    ratio_payload = json.loads(
        (dist_dir / "indicators" / "maternal_mortality_ratio.json").read_text()
    )
    assert not any(d["entity_id"] == "libya" for d in ratio_payload["data"])

    # The counts carry the collector's annotations like the ratios do:
    # Russia 2019 rides footnote ref 5 (the Chechnya-style caveat).
    russia = {d["year"]: d for d in payload["data"] if d["entity_id"] == "russian_federation"}
    assert russia[2019]["value"] == pytest.approx(216.0)
    assert russia[2019]["footnote_refs"] == ["5"]

    # No sex dimension: the table prints one Number row per country, so no
    # canonical point carries a sex key.
    assert all("sex" not in d for d in payload["data"])

    # The witness rides beside: WDI's modeled counts, root un_mmeig.
    witness = next(w for w in payload["witnesses"] if w["provider"] == "worldbank")
    assert witness["root"] == "un_mmeig"
    assert witness["unit"] == "maternal_deaths"
    assert witness["data"]


def test_maternal_mortality_ratio_gains_the_wb_second_witness_and_the_2015_edition(tmp_path, real_indicators, real_entities):
    # v12: the ratio's witness tier becomes TWO doors of one root (un_mmeig,
    # the 2020 round via OWID + the 2023 round via WDI), and the canonical
    # loop becomes 13 editions with 2015/table17 wired at priority 9 —
    # the recovered edition (legacy URL pattern, verified live in v10).
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "maternal_mortality_ratio.json").read_text())

    by_ref = {(s["provider"], s["source_ref"]): s for s in payload["sources"]}
    # 13 canonical editions: 2015 sits between 2017 (prio 8) and 2014 (prio 10).
    dyb_refs = [s for s in payload["sources"] if s["provider"] == "un_dyb"]
    assert len(dyb_refs) == 13
    assert by_ref[("un_dyb", "2015/table17")]["role"] == "canonical"
    # payload["sources"] is emitted in priority order (sources_by_priority).
    refs_by_priority = [s["source_ref"] for s in dyb_refs]
    assert refs_by_priority == [f"{e}/table17" for e in (2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2015, 2014, 2013, 2012, 2011)]

    # Two witness doors, one root, both riding beside the canonical series.
    witness_doors = {(w["provider"], w["source_ref"]): w for w in payload["witnesses"]}
    assert set(witness_doors) == {("owid", "maternal-mortality"), ("worldbank", "SH.STA.MMRT")}
    for door in witness_doors.values():
        assert door["root"] == "un_mmeig"
        assert door["layer"] == "harmonized"
        assert door["unit"] == "maternal_deaths_per_100k_live_births"
    # The WDI door prints no sex (bare code) — its points carry no sex key.
    wb_door = witness_doors[("worldbank", "SH.STA.MMRT")]
    assert all("sex" not in p for p in wb_door["data"])

    # The catalog's roots summary says the genealogy from the data:
    # canonical = unsd_dyb through 13 doors, witness = un_mmeig through 2.
    catalog = {c["id"]: c for c in json.loads((dist_dir / "catalog.json").read_text())}
    maternal_roots = catalog["maternal_mortality_ratio"]["roots"]
    assert {r["root"]: r["doors"] for r in maternal_roots["canonical"]} == {"unsd_dyb": 13}
    assert {r["root"]: r["doors"] for r in maternal_roots["witness"]} == {"un_mmeig": 2}
    deaths_roots = catalog["maternal_deaths"]["roots"]
    assert {r["root"]: r["doors"] for r in deaths_roots["canonical"]} == {"unsd_dyb": 13}
    assert {r["root"]: r["doors"] for r in deaths_roots["witness"]} == {"un_mmeig": 1}


# --- v10: life_expectancy_60, the fifth indicator -----------------------------


def test_life_expectancy_60_is_two_tier_end_to_end(tmp_path, real_indicators, real_entities):
    # The LE-60 pilot: un_dyb Table 21 canonical (age-column selector on
    # "60", sex-split rows, reference periods, explicit gaps, Sup footnote
    # refs joined to their texts) + the first GHO witness (sex-carrying
    # points on the (entity, year, sex) merge key, both-sexes series
    # included without colliding with the split ones).
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "life_expectancy_60.json").read_text())

    by_key = {(d["entity_id"], d["year"], d.get("sex")): d for d in payload["data"]}
    # Canonical: sex-split as printed, age-60 values, the 2024 dual-block
    # degradation materialized as explicit gap points.
    assert by_key[("france", 2020, "male")]["value"] == 21.9
    assert by_key[("france", 2020, "female")]["value"] == 26.5
    assert by_key[("algeria", 2023, "male")]["value"] == 16.4
    assert by_key[("france", 2024, "male")]["value"] is None
    assert by_key[("france", 2024, "male")]["missing_marker"] == "..."
    # The reference period rides the Mauritius points (year = END of period).
    mauritius = by_key[("mauritius", 2024, "male")]
    assert mauritius["value"] == pytest.approx(16.1123456789012)
    assert mauritius["reference_range"] == "2022 - 2024"
    # The Sup footnote ref is carried AND its text joined into the source's
    # footnotes block (the note lives in the fixture's Footnotes sheet).
    assert mauritius["footnote_refs"] == ["12"]
    t21_source = next(s for s in payload["sources"] if s["source_ref"] == "2024/table21")
    assert t21_source["footnotes"]["notes"]["12"].startswith("Data refer to a three-year reference period")

    # Witness: the GHO series rides BESIDE the canonical one, never merged
    # (same merge key, different tiers) — the sex-carrying points and the
    # both-sexes series coexist without collision.
    assert len(payload["witnesses"]) == 1
    witness = payload["witnesses"][0]
    assert witness["provider"] == "who_gho"
    assert witness["source_ref"] == "WHOSIS_000015"
    assert witness["layer"] == "harmonized"
    assert witness["unit"] == "years"
    assert witness["citation"] == "WHO Global Health Observatory (GHO) API, indicator 'WHOSIS_000015'"
    assert witness["url"] == "https://ghoapi.azureedge.net/api/WHOSIS_000015"
    assert witness["license"] == "CC-BY-3.0-IGO"
    w_by_key = {(d["entity_id"], d["year"], d.get("sex")): d for d in witness["data"]}
    assert w_by_key[("france", 2020, "male")]["value"] == pytest.approx(22.4444444444444)
    assert w_by_key[("france", 2020, None)]["value"] == pytest.approx(24.3456789012345)
    assert w_by_key[("russian_federation", 2012, "male")]["value"] == pytest.approx(15.4567890123456)
    # The canonical France 2020 male point and the witness's both survive:
    # same key space, different tiers, never blended.
    assert ("france", 2020, "male") in by_key
    assert ("france", 2020, "male") in w_by_key
    assert by_key[("france", 2020, "male")]["value"] != w_by_key[("france", 2020, "male")]["value"]

    # Sources meta: 13 DYB canonical editions + 1 GHO witness, each with its
    # role and the age selector visible in the config (field flows to the
    # connector; the dist's citation names the edition/table).
    roles = {(s["provider"], s["role"]) for s in payload["sources"]}
    assert roles == {("un_dyb", "canonical"), ("who_gho", "witness")}
    assert sum(1 for s in payload["sources"] if s["provider"] == "un_dyb") == 13


def test_le60_canonical_gaps_are_kept_as_points_not_absences(tmp_path, real_indicators, real_entities):
    # The dist v4 contract on the new indicator: every (entity, year, sex)
    # the collector printed with "..." at the selected age is ONE explicit
    # gap point carrying its printed marker — never dropped, never zero.
    # (Algeria/Mauritius's "..." live at ages 90-100, other columns of the
    # same file: age-60 IS valued for them; only France's not-yet-computed
    # 2024 block gaps at 60.)
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "life_expectancy_60.json").read_text())
    gaps = [d for d in payload["data"] if d["value"] is None]
    assert {(d["entity_id"], d["year"], d["sex"]) for d in gaps} == {
        ("france", 2024, "male"),
        ("france", 2024, "female"),
    }
    assert all(d["missing_marker"] == "..." for d in gaps)


def test_v11_worldbank_witnesses_ride_beside_with_their_genealogy(tmp_path, real_indicators, real_entities):
    # The P5 wiring end-to-end: the World Bank's sex-split codes land as
    # witness series (never merged), their points carrying the sex the
    # code suffix declares, the WDI trailing-null as an explicit gap, and
    # every series carrying its ROOT — the genealogy field that says the
    # four agreeing IMR witnesses are one UN IGME root behind four doors.
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    imr = json.loads((dist_dir / "indicators" / "infant_mortality.json").read_text())

    witness_by_ref = {w["source_ref"]: w for w in imr["witnesses"]}
    assert set(witness_by_ref) == {"infant-mortality", "SP.DYN.IMRT.MA.IN", "SP.DYN.IMRT.FE.IN", "MDG_0000000001"}

    # The triangle claim, executable: all four doors declare the same root.
    for ref in witness_by_ref:
        assert witness_by_ref[ref]["root"] == "un_igme"
        assert "Inter-agency Group for Child Mortality" in witness_by_ref[ref]["root_label"]

    wb_male = witness_by_ref["SP.DYN.IMRT.MA.IN"]
    assert wb_male["provider"] == "worldbank"
    assert wb_male["layer"] == "harmonized"
    assert wb_male["native_unit"] is None  # WDI prints per-1,000 = the canonical unit
    assert wb_male["citation"] == "World Bank Open Data API, indicator 'SP.DYN.IMRT.MA.IN'"
    assert wb_male["url"].startswith("https://api.worldbank.org/v2/country/all/indicator/SP.DYN.IMRT.MA.IN")
    assert wb_male["license"] == "CC-BY-4.0"
    wb_by_key = {(d["entity_id"], d["year"], d.get("sex")): d for d in wb_male["data"]}
    assert wb_by_key[("russian_federation", 1990, "male")]["value"] == pytest.approx(17.5)
    # The WDI trailing-2025 slot: an explicit gap point, never a skip.
    assert wb_by_key[("russian_federation", 2025, "male")]["value"] is None
    assert wb_by_key[("france", 2020, "male")]["value"] == pytest.approx(3.2)
    # The provider's own aggregate classification: World/AFE never landed.
    assert all(d["entity_id"] not in {"world", "africa_eastern_and_southern"} for d in wb_male["data"])

    wb_female = witness_by_ref["SP.DYN.IMRT.FE.IN"]
    assert all(d.get("sex") == "female" for d in wb_female["data"])

    # The GHO MDG door: sex-split rows beside the both-sexes ones, all on
    # the (entity, year, sex) merge key, same root as the OWID witness.
    mdg = witness_by_ref["MDG_0000000001"]
    mdg_sexes = {(d["entity_id"], d["year"], d.get("sex")) for d in mdg["data"]}
    assert ("france", 2020, "male") in mdg_sexes
    assert ("france", 2020, None) in mdg_sexes

    # sources[] carries the root on every declared source (canonical too).
    sources_by_ref = {s["source_ref"]: s for s in imr["sources"]}
    assert sources_by_ref["ussr_infant_mortality_official"]["root"] == "soviet_official"
    assert sources_by_ref["2024/table15"]["root"] == "unsd_dyb"
    assert sources_by_ref["SP.DYN.IMRT.FE.IN"]["root"] == "un_igme"
    assert "TsSU yearbooks" in sources_by_ref["ussr_infant_mortality_official"]["root_label"]


def test_v11_life_expectancy_witnesses_carry_two_different_roots(tmp_path, real_indicators, real_entities):
    # LE is the counter-case: its witnesses deliberately carry DIFFERENT
    # roots (OWID's mixed long-run compilation vs the World Bank's pure
    # UN WPP) — the genealogy that explains WHY they diverge, displayed
    # instead of reconciled.
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    le = json.loads((dist_dir / "indicators" / "life_expectancy.json").read_text())

    by_ref = {w["source_ref"]: w for w in le["witnesses"]}
    assert set(by_ref) == {"life-expectancy", "SP.DYN.LE00.MA.IN", "SP.DYN.LE00.FE.IN"}
    assert by_ref["life-expectancy"]["root"] == "owid_longrun_composite"
    assert by_ref["SP.DYN.LE00.MA.IN"]["root"] == "un_wpp"
    assert by_ref["SP.DYN.LE00.FE.IN"]["root"] == "un_wpp"
    assert all(d.get("sex") == "male" for d in by_ref["SP.DYN.LE00.MA.IN"]["data"])


def test_v11_catalog_carries_the_roots_summary(tmp_path, real_indicators, real_entities):
    # The catalog computes what the UI should say: IMR = 2 canonical roots
    # (curated Soviet + the DYB collector, 13 doors) and ONE harmonized
    # root (IGME) behind FOUR doors — "one, not three", per section 5.1.
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    catalog = {c["id"]: c for c in json.loads((dist_dir / "catalog.json").read_text())}

    imr_roots = catalog["infant_mortality"]["roots"]
    assert [(r["root"], r["doors"]) for r in imr_roots["canonical"]] == [
        ("soviet_official", 1),
        ("unsd_dyb", 13),
    ]
    assert [(r["root"], r["doors"]) for r in imr_roots["witness"]] == [("un_igme", 4)]
    assert all("label" in r for r in imr_roots["canonical"] + imr_roots["witness"])

    le_roots = catalog["life_expectancy"]["roots"]
    assert [r["root"] for r in le_roots["canonical"]] == ["unsd_dyb"]
    assert [r["root"] for r in le_roots["witness"]] == ["owid_longrun_composite", "un_wpp"]


# --- v13: suicide_rate (the corpus's #2) + the todd_refs emission ----------


def test_suicide_rate_is_two_tier_with_the_ill_defined_divergence(tmp_path, real_indicators, real_entities):
    # The homicide architecture one cause-code away: canonical = WHO-MDB
    # as-submitted (OECD CICDHARM), witness = GHE modeled (GHO SDGSUICIDE,
    # crude, sex-split). The display case the homicide pair does NOT carry:
    # the two tiers diverge SYSTEMATICALLY — GHE re-distributes the
    # ill-defined causes the collectors left unassigned (RUS male 2000:
    # 69.8 as-reported vs 95.2 modeled, both live-verified 2026-09-19).
    _, dist_dir, _, validate_results = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "suicide_rate.json").read_text())

    canon = {(d["entity_id"], d["year"], d.get("sex")): d["value"] for d in payload["data"]}
    assert canon[("russian_federation", 1994, "male")] == pytest.approx(73.9)
    assert canon[("russian_federation", 1994, "female")] == pytest.approx(13.2)  # the 5.6x sex split
    assert canon[("russian_federation", 2000, "male")] == pytest.approx(69.8)
    assert canon[("lithuania", 1994, "male")] == pytest.approx(83.5)  # the live slice's as-reported max
    assert all(d["provider"] == "oecd" for d in payload["data"])

    assert len(payload["witnesses"]) == 1
    witness = payload["witnesses"][0]
    assert witness["provider"] == "who_gho"
    assert witness["root"] == "who_ghe"  # the registry root v13 added for this config
    wit = {(d["entity_id"], d["year"], d.get("sex")): d["value"] for d in witness["data"]}
    assert wit[("russian_federation", 2000, "male")] == pytest.approx(95.20444591)
    assert wit[("russian_federation", 2021, "male")] == pytest.approx(36.68325073)  # YEARSALL, not a slice

    # THE DIVERGENCE, side by side on the same key: +36% modeled uplift on
    # the exact point the collector printed — displayed, never reconciled.
    assert wit[("russian_federation", 2000, "male")] > canon[("russian_federation", 2000, "male")]

    # No range violation on the new indicator (LTU 83.5 sits inside 0-100)
    suicides = [r for r in validate_results if r["indicator_id"] == "suicide_rate"]
    assert suicides and suicides[0]["range_violations"] == []


def test_todd_refs_ride_the_matching_indicators_only(tmp_path, real_indicators, real_entities):
    # The corpus joins BY ID: the four todd_core=true indicators (IMR, LE,
    # homicide, suicide) carry their "why this metric exists" block; the
    # three Extra-board indicators (maternal x2, LE-60) carry nothing —
    # honest absence, the cross-validation guarantees the flag side.
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)

    for iid, citations, books in [
        ("infant_mortality", 52, 13),
        ("life_expectancy", 26, 11),
        ("homicide_rate", 25, 10),
        ("suicide_rate", 80, 11),
        ("birth_rate_fertility", 111, 16),
    ]:
        payload = json.loads((dist_dir / "indicators" / f"{iid}.json").read_text())
        tr = payload["todd_refs"]
        assert tr["citations"] == citations
        assert tr["books"] == books
        assert len(tr["refs"]) == books
        # every ref carries its book, year, count and usage note
        assert all(r["book"] and r["year"] and r["note"] is not None for r in tr["refs"])
        assert sum(r["citations"] for r in tr["refs"]) == citations

    for iid in ("maternal_mortality_ratio", "maternal_deaths", "life_expectancy_60"):
        payload = json.loads((dist_dir / "indicators" / f"{iid}.json").read_text())
        assert "todd_refs" not in payload

    # suicide's heaviest book is Le Fou et le Prolétaire (38 citations) —
    # the corpus's own flagship row
    suicide = json.loads((dist_dir / "indicators" / "suicide_rate.json").read_text())
    heaviest = max(suicide["todd_refs"]["refs"], key=lambda r: r["citations"])
    assert (heaviest["book"], heaviest["citations"]) == ("Le Fou et le Prolétaire", 38)
    # the dual-edition book keeps its bare year sortable + its raw form
    chute = [r for r in suicide["todd_refs"]["refs"] if r["book"] == "La Chute finale"]
    assert chute[0]["year"] == 1976 and chute[0]["year_raw"] == "1976/1990"


def test_todd_corpus_json_is_the_executable_roadmap(tmp_path, real_indicators, real_entities):
    # dist/todd_corpus.json carries ALL 24 metrics — implemented AND
    # unimplemented — ranked by the corpus's own citation weight: the
    # "what to build next" question becomes a data statement.
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    corpus = json.loads((dist_dir / "todd_corpus.json").read_text())

    assert corpus["meta"]["metrics"] == 24
    assert corpus["meta"]["implemented_metrics"] == 10  # 8 previous + consanguineous_marriage_rate + unemployment_rate (v17); crude_birth_rate is todd_core=false (no corpus id of its own)
    assert corpus["meta"]["total_citations"] == 483
    assert len(corpus["meta"]["source_csv_sha256"]) == 64
    assert "todd_core.csv" in corpus["source"]

    metrics = corpus["metrics"]
    assert [m["id"] for m in metrics[:3]] == [
        "birth_rate_fertility",  # 111 citations, 16/16 books — the #1, implemented in v14
        "suicide_rate",           # 80 — implemented in v13
        "infant_mortality",       # 52 — implemented since v3
    ]
    implemented = {m["id"] for m in metrics if m["implemented"]}
    assert implemented == {
        "birth_rate_fertility", "suicide_rate", "infant_mortality", "life_expectancy", "homicide_rate",
        "same_sex_marriage_legalization_year", "universal_suffrage_introduction_year",
        "illegitimate_births",  # v16 — the corpus's illégitimité, 16 citations
        "consanguineous_marriage_rate",  # v17 — the backlog's head, 34 citations
        "unemployment_rate",  # v17 — the economy family's first indicator, 20 citations
        # crude_birth_rate is todd_core=false by design (the CBR companion —
        # no corpus metric carries the crude rate as its own id; the
        # 19th-century CBR rows live under birth_rate_fertility's umbrella)
    }
    # the ranking is non-increasing in citations
    cits = [m["citations"] for m in metrics]
    assert cits == sorted(cits, reverse=True)

    # the catalog entries carry the same block (frontend renders "why"
    # from the catalog without loading every indicator file)
    catalog = {c["id"]: c for c in json.loads((dist_dir / "catalog.json").read_text())}
    assert catalog["suicide_rate"]["todd_refs"]["citations"] == 80
    assert "todd_refs" not in catalog["maternal_deaths"]


def test_stats_renders_the_corpus_lines(tmp_path, real_indicators, real_entities):
    # `cli stats` closes with the corpus block: implemented share + the
    # citation-weighted backlog; and every todd_core indicator carries its
    # todd refs line. The numbers changelogs quote stay emitted by command.
    from src.pipeline.stats import render_stats

    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    out = render_stats(dist_dir)

    assert "suicide_rate: canonical" in out
    assert "birth_rate_fertility: canonical" in out
    assert "todd refs: 80 citations across 11 book(s) (heaviest: Le Fou et le Prolétaire 1979, 38)" in out
    assert "todd refs: 111 citations across 16 book(s)" in out
    assert "todd refs: 52 citations across 13 book(s)" in out
    assert "todd corpus: 24 metrics, 483 citations, 16 books" in out
    assert "implemented 10/24" in out
    assert "top unimplemented: industrial_employment_share 30" in out
    assert "todd refs: 34 citations across 10 book(s) (heaviest: Le Destin des immigrés 1994, 16)" in out
    assert "todd refs: 20 citations across 7 book(s) (heaviest: Les Luttes de classes en France 2019, 6)" in out
    # the Extra-board indicators carry no todd refs line
    assert "maternal_deaths" in out
    maternal_block = out.split("maternal_deaths:")[1].split("\n")[0] + next(
        l for l in out.split("maternal_deaths:")[1].splitlines()[1:] if "witness" in l or "witnesses" in l
    )
    assert "todd refs" not in maternal_block


# --- v14: birth_rate_fertility (the corpus's #1) + the FX/FR seam ----------


def test_birth_rate_fertility_is_two_tier_with_the_fx_fr_seam(tmp_path, real_indicators, real_entities):
    # The corpus's #1 (111 citations, 16/16 books): canonical = Eurostat's
    # collection of the national official TFRs (the one collector wire
    # that prints a TFR — the finding the config documents), witness =
    # WPP through WDI's TFRT door. The display case this pair carries
    # that no other indicator has: the FX/FR SEAM — Eurostat prints TWO
    # French series (metropolitan 1960-2012, whole-France 1998-2024) and
    # the merge stitches the canon by vintage with the definitional
    # difference logged, never reconciled.
    processed_dir, dist_dir, _, validate_results = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "birth_rate_fertility.json").read_text())

    canon = {(d["entity_id"], d["year"]): d for d in payload["data"]}
    # The seam, exactly as the config documents it: FX 1960-1997 + FR
    # 1998-2024, the two overlap years arbitrated to FR (later vintage).
    assert canon[("france", 1960)]["value"] == pytest.approx(2.73)  # metro-only
    assert canon[("france", 1994)]["value"] == pytest.approx(1.66)  # metro-only (the trough)
    assert canon[("france", 2000)]["value"] == pytest.approx(1.89)  # FR wins over FX 1.87
    assert canon[("france", 2012)]["value"] == pytest.approx(2.01)  # FR wins over FX 1.99
    assert canon[("france", 2023)]["value"] == pytest.approx(1.66)
    assert all(d["provider"] == "eurostat" for d in payload["data"])
    # TFR has no sex split BY CONSTRUCTION (a synthetic measure over
    # women's lifetimes) — every point rides sex=None.
    assert all(d.get("sex") is None for d in payload["data"])

    # The codelist quirks resolve through the override table: Greece
    # (EL, never ISO's GR) and the UK (UK, never ISO's GB).
    assert canon[("greece", 1994)]["value"] == pytest.approx(1.33)
    assert canon[("united_kingdom", 2012)]["value"] == pytest.approx(1.92)
    # The Eastern-partnership window the collector actually got (Russia
    # answered 2006-2010, then stopped).
    assert canon[("russian_federation", 2008)]["value"] == pytest.approx(1.49)
    # The collector's own per-observation flag rides as-reported: DE 2023
    # prints 'b' (break in series).
    germany = canon[("germany", 2023)]
    assert germany["value"] == pytest.approx(1.39)
    assert germany["quality_code"] == "b"
    # Kosovo prints (XK, 2016-2019) but resolves to no ISO3 and no
    # eurostat name fallback: the SAME pending product decision as the
    # WB's Kosovo — the point does not land.
    assert all(e != "kosovo" for e, _ in canon)

    # THE ARBITRATION TRAIL: each overlap year logs the discarded FX
    # value — the vintage discipline, never a silent blend.
    provenance = json.loads((processed_dir / "birth_rate_fertility.provenance.json").read_text())
    fra = [e for e in provenance if e.get("entity_id") == "france" and e["role"] == "canonical"]
    discarded = {e["year"]: [d["value"] for d in e["discarded"]] for e in fra}
    assert discarded == {2000: [pytest.approx(1.87)], 2012: [pytest.approx(1.99)]}
    retained = {e["year"]: e["retained"]["source_ref"] for e in fra}
    assert retained == {2000: "demo_find/TOTFERRT/FR", 2012: "demo_find/TOTFERRT/FR"}

    # The witness: WDI's WPP door, worldwide — one door, the v13 minimal
    # discipline. Root un_wpp: for the EU it anchors on the national
    # series, elsewhere it models what the collector never collected.
    assert len(payload["witnesses"]) == 1
    witness = payload["witnesses"][0]
    assert witness["provider"] == "worldbank"
    assert witness["root"] == "un_wpp"
    wit = {(d["entity_id"], d["year"]): d for d in witness["data"]}
    assert wit[("russian_federation", 1990)]["value"] == pytest.approx(1.892)
    assert wit[("russian_federation", 2025)]["value"] is None  # the trailing-grid honest gap
    assert wit[("france", 2020)]["value"] == pytest.approx(1.79)

    # The catalog's roots genealogy: ONE collector root (3 doors, one
    # provider) + ONE witness root — two independent origins, stated.
    catalog = {c["id"]: c for c in json.loads((dist_dir / "catalog.json").read_text())}
    roots = catalog["birth_rate_fertility"]["roots"]
    assert [r["root"] for r in roots["canonical"]] == ["eurostat_demo"]
    assert roots["canonical"][0]["doors"] == 3
    assert [r["root"] for r in roots["witness"]] == ["un_wpp"]

    # v16: the companion link is declared on BOTH sides now — the TFR
    # points back at the CBR (the symmetry cross_validate_companions
    # enforces; the v15 one-way asymmetry repaired).
    assert payload["companion_indicators"] == ["crude_birth_rate"]
    assert catalog["birth_rate_fertility"]["companion_indicators"] == ["crude_birth_rate"]

    # No range violation on the new indicator (every seeded value sits
    # inside 0-10; the witness's real-world tail peaks at Yemen 8.86).
    tfr = [r for r in validate_results if r["indicator_id"] == "birth_rate_fertility"]
    assert tfr and tfr[0]["range_violations"] == []


def test_birth_rate_fertility_todd_refs_and_corpus_ranking(tmp_path, real_indicators, real_entities):
    # The corpus's #1 finally implemented: the todd_refs block rides the
    # indicator (16/16 books — the only metric Todd uses in every book),
    # and todd_corpus.json's roadmap flips it to implemented with the
    # backlog's new head (consanguineous_marriage_rate 34).
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "birth_rate_fertility.json").read_text())
    tr = payload["todd_refs"]
    assert (tr["citations"], tr["books"]) == (111, 16)
    # the heaviest book: Après l'Empire (2002, 20 citations — the world
    # TFR decline tables)
    heaviest = max(tr["refs"], key=lambda r: r["citations"])
    assert (heaviest["book"], heaviest["citations"]) == ("Après l'Empire", 20)
    # the corpus's own family resolution rides the metric (society, the
    # weighted-majority call the normalizer displays at regen)
    corpus = json.loads((dist_dir / "todd_corpus.json").read_text())
    top = corpus["metrics"][0]
    assert top["id"] == "birth_rate_fertility" and top["implemented"] is True
    assert top["family"] == "society"


def test_crude_birth_rate_is_two_tier_with_the_collector_natalite_print(tmp_path, real_indicators, real_entities):
    # The CBR companion (v15): canonical = DYB Table 9's rate block (the
    # collector's own natalité print — the same births Table 17's maternal
    # ratios are computed from), witness = WPP through WDI's CBRT door.
    # todd_core=false by design: no corpus metric carries the crude rate
    # as its own id; the companion_indicators link carries the relationship.
    processed_dir, dist_dir, _, validate_results = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "crude_birth_rate.json").read_text())

    assert payload["todd_core"] is False
    assert payload["companion_indicators"] == ["birth_rate_fertility"]
    assert "todd_refs" not in payload  # the corpus block joins BY ID — honestly absent here

    canon = {(d["entity_id"], d["year"]): d for d in payload["data"]}
    # The live anchors the fixture carries: Algeria's CBR series as the
    # collector prints it (the 10-digit precision as carried), the '+U'
    # honest degradation kept as explicit gap points (never zero).
    assert canon[("algeria", 2020)]["value"] == pytest.approx(22.3369498881)
    assert canon[("algeria", 2023)]["value"] == pytest.approx(19.3150537642)
    assert canon[("burundi", 2020)]["value"] is None
    assert canon[("burundi", 2020)]["missing_marker"] == "..."
    # France's row = the live DYB 2024 bytes: the '*' provisional marker
    # rides 2022/2023/2024 (rates AND counts); 2020 prints UNFLAGGED —
    # the v16 anchor repair (v15's fixture fabricated 11.7 with '*' on
    # 2020; the real bytes are 10.6579082599 with no marker).
    assert canon[("france", 2020)]["value"] == pytest.approx(10.6579082599)
    assert not canon[("france", 2020)].get("provisional")
    assert canon[("france", 2022)]["value"] == pytest.approx(10.4267737019)
    assert canon[("france", 2022)]["provisional"] is True
    assert canon[("france", 2023)]["value"] == pytest.approx(9.6873422054)
    assert canon[("france", 2023)]["provisional"] is True
    # The collector's quality code rides every point.
    assert canon[("algeria", 2020)]["quality_code"] == "C"
    assert canon[("burundi", 2020)]["quality_code"] == "+U"

    # THE WITNESS: WPP through WDI's bare CBRT code — the worldwide face,
    # sex=None by construction (a population-level rate has no split).
    witnesses = payload["witnesses"]
    assert len(witnesses) == 1
    w = witnesses[0]
    assert (w["provider"], w["source_ref"]) == ("worldbank", "SP.DYN.CBRT.IN")
    assert w["root"] == "un_wpp"
    wpts = {(p["entity_id"], p["year"]): p for p in w["data"]}
    assert wpts[("france", 2024)]["value"] == pytest.approx(9.7)   # the live WDI print
    assert wpts[("russian_federation", 1960)]["value"] == pytest.approx(23.881)
    assert wpts[("niger", 1960)]["value"] == pytest.approx(57.613)  # the WPP tail's peak
    assert wpts[("russian_federation", 2025)]["value"] is None      # the honest trailing gap

    # No range violation on either tier (every seeded value sits inside
    # 0-60; Niger 57.613 is the bound's own reason).
    cbr = [r for r in validate_results if r["indicator_id"] == "crude_birth_rate"]
    assert cbr and cbr[0]["range_violations"] == []
    assert all(not wv["range_violations"] for wv in cbr[0]["witnesses"])


def test_illegitimate_births_is_two_tier_with_the_german_seam(tmp_path, real_indicators, real_entities):
    # The TWELFTH INDICATOR (v16), the corpus's illégitimité (16
    # citations, 6 books): canonical = Eurostat demo_find/NMARPCT — the
    # collector prints the SHARE directly ("Proportion of live births
    # outside marriage", no derivation), the same dataset as the TFR —
    # witness = the OECD Family Database through OWID's chart door.
    # THE DISPLAY CASE THIS PAIR CARRIES: the GERMAN SEAM — on NMARPCT
    # DE_TOT ("Germany including former GDR") is the fuller 65-year
    # series and DIVERGES from DE's FRG-only pre-reunification
    # benchmarks (the TFR case's duplicate, REVERSED), so DE_TOT rides
    # its own geo-pinned source at the highest priority and every DE
    # collision becomes a logged discard — the FX/FR seam's architecture
    # applied to a definitional seam.
    processed_dir, dist_dir, _, validate_results = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "illegitimate_births.json").read_text())

    assert payload["todd_core"] is True
    tr = payload["todd_refs"]
    assert (tr["citations"], tr["books"]) == (16, 6)
    assert payload["companion_indicators"] == []  # no companion: a share, not a paired measure
    assert payload["unit"] == "percent_of_live_births"

    canon = {(d["entity_id"], d["year"]): d for d in payload["data"]}
    # THE GERMAN SEAM: the all-Germany series wins every collision —
    # 1960/1980 (and 1970/1985/1990, the pin-only years) print
    # DE_TOT's values, never DE's FRG-only benchmarks.
    assert canon[("germany", 1960)]["value"] == pytest.approx(7.6)   # DE_TOT, not DE's 6.3
    assert canon[("germany", 1970)]["value"] == pytest.approx(7.2)   # pin-only year
    assert canon[("germany", 1980)]["value"] == pytest.approx(11.9)  # THE divergence: FRG printed 7.6
    assert canon[("germany", 1985)]["value"] == pytest.approx(16.2)  # the GDR's high share
    assert canon[("germany", 2022)]["value"] == pytest.approx(33.5)  # main-slice year (no collision)
    assert canon[("germany", 2024)]["value"] == pytest.approx(32.4)
    # THE FX/FR SEAM (the TFR architecture, mirrored): FX metro
    # 1960-1997 + FR whole 1998-2024, the overlap arbitrated to FR.
    assert canon[("france", 1960)]["value"] == pytest.approx(6.1)    # metro-only
    assert canon[("france", 1998)]["value"] == pytest.approx(41.7)   # FR wins over FX 40.7
    assert canon[("france", 2000)]["value"] == pytest.approx(43.6)   # FR wins over FX 42.6
    assert canon[("france", 2012)]["value"] == pytest.approx(56.7)   # FR wins over FX 55.8
    assert canon[("france", 2020)]["value"] == pytest.approx(62.2)
    assert canon[("france", 2024)]["value"] == pytest.approx(59.7)
    # The collector's per-observation flags ride as-reported: Greece's
    # 2023 series break 'b', Moldova's 2022 provisional 'p'.
    assert canon[("greece", 2023)]["quality_code"] == "b"
    assert canon[("moldova_republic_of", 2022)]["provisional"] is True
    assert canon[("moldova_republic_of", 2022)]["value"] == pytest.approx(18.3)
    # Kosovo prints (XK, 2002 in the fixture grid) but resolves to no
    # ISO3: the pending class, the same product decision as every XK row.
    assert all(e != "kosovo" for e, _ in canon)
    # No sex split by construction (a population-level share).
    assert all(d.get("sex") is None for d in payload["data"])

    # THE ARBITRATION TRAIL: the German seam's discards are the story —
    # every DE collision logs the FRG-only benchmark it dropped against
    # the all-Germany print (1960: 6.3 discarded; 1980: 7.6 discarded),
    # and the French seam logs its FX discards exactly like the TFR's.
    provenance = json.loads((processed_dir / "illegitimate_births.provenance.json").read_text())
    deu = {e["year"]: ([d["value"] for d in e["discarded"]], e["retained"]["source_ref"])
           for e in provenance if e.get("entity_id") == "germany" and e["role"] == "canonical"}
    assert deu[1960] == ([pytest.approx(6.3)], "demo_find/NMARPCT/DE_TOT")
    assert deu[1980] == ([pytest.approx(7.6)], "demo_find/NMARPCT/DE_TOT")  # the FRG-only benchmark, logged
    assert deu[1998] == ([pytest.approx(20.0)], "demo_find/NMARPCT/DE_TOT")  # identical print, still logged
    fra = {e["year"]: [d["value"] for d in e["discarded"]] for e in provenance
           if e.get("entity_id") == "france" and e["role"] == "canonical"}
    assert fra == {1998: [pytest.approx(40.7)], 2000: [pytest.approx(42.6)], 2012: [pytest.approx(55.8)]}

    # THE WITNESS: the OECD Family Database through OWID's chart door —
    # the worldwide-OECD face (Japan, Chile...) the Eurostat
    # questionnaire never polled; on the co-covered entities the OECD
    # anchors on the national series (France 2020 = 62.2 on BOTH doors).
    assert len(payload["witnesses"]) == 1
    witness = payload["witnesses"][0]
    assert (witness["provider"], witness["source_ref"]) == ("owid", "share-of-births-outside-marriage")
    assert witness["root"] == "oecd_family"
    wit = {(d["entity_id"], d["year"]): d for d in witness["data"]}
    assert wit[("france", 2020)]["value"] == pytest.approx(62.2)   # = the collector's own FR print
    assert wit[("germany", 1960)]["value"] == pytest.approx(7.6)   # = DE_TOT's print (the OECD rides the all-Germany series too)
    assert wit[("japan", 2020)]["value"] == pytest.approx(2.4)     # witness-only entity
    assert wit[("chile", 2019)]["value"] == pytest.approx(75.08)   # the questionnaire tail's peak

    # The catalog's roots genealogy: ONE collector root (4 doors, one
    # provider) + ONE witness root — and the corpus's ranking carries
    # the flip (implemented 8/24, the backlog's head unchanged).
    catalog = {c["id"]: c for c in json.loads((dist_dir / "catalog.json").read_text())}
    roots = catalog["illegitimate_births"]["roots"]
    assert [r["root"] for r in roots["canonical"]] == ["eurostat_demo"]
    assert roots["canonical"][0]["doors"] == 4
    assert [r["root"] for r in roots["witness"]] == ["oecd_family"]
    corpus = json.loads((dist_dir / "todd_corpus.json").read_text())
    metric = next(m for m in corpus["metrics"] if m["id"] == "illegitimate_births")
    assert metric["implemented"] is True and metric["citations"] == 16

    # No range violation on either tier (a 0-100 share; Chile 75.08 the
    # witness tail's peak).
    ill = [r for r in validate_results if r["indicator_id"] == "illegitimate_births"]
    assert ill and ill[0]["range_violations"] == []
    assert all(not wv["range_violations"] for wv in ill[0]["witnesses"])


def test_same_sex_marriage_marker_is_one_point_per_country_with_citations(tmp_path, real_indicators, real_entities):
    # The FIRST MARKER (v15): Todd's 'religion zero' dating instrument —
    # one point per country, the point's year = the legalization year =
    # the value, every point carrying its own citation (the statute or
    # nationwide ruling) and its dating convention note. The gate's
    # condition (b) finding rides the config: NO machine-readable door
    # carries the series — the curated tier is not competing with a wire.
    _, dist_dir, _, validate_results = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "same_sex_marriage_legalization_year.json").read_text())

    assert payload["family"] == "markers"
    assert payload["todd_core"] is True
    tr = payload["todd_refs"]
    assert (tr["citations"], tr["books"]) == (13, 1)
    assert tr["refs"][0]["book"] == "La Défaite de l'Occident" and tr["refs"][0]["year"] == 2024

    # THE MARKER SHAPE: 33 countries, ONE point each, year == value.
    data = payload["data"]
    assert len(data) == 33
    assert len({d["entity_id"] for d in data}) == 33
    assert all(d["year"] == d["value"] for d in data)
    # No witnesses can exist for the marker tier (nothing upstream to
    # witness — the citation IS the origin, the root says so).
    assert payload["witnesses"] == []
    # Every point carries its citation and its dating note — the curation
    # gate's mechanical condition, verified on the dist payload itself.
    assert all(d.get("citation") for d in data)
    assert all(d.get("definition_note") for d in data)

    # The chain Todd reads: Ireland's referendum and Obergefell both 2015
    # (the hinge), France 2013 (mariage pour tous), the Orthodox world's
    # first only 2024 (Greece — the marker family's own divergence).
    pts = {d["entity_id"]: d for d in data}
    assert pts["france"]["value"] == 2013
    assert pts["ireland"]["value"] == 2015
    assert pts["united_states"]["value"] == 2015
    assert pts["germany"]["value"] == 2017
    assert pts["greece"]["value"] == 2024
    assert pts["netherlands"]["value"] == 2001  # the world's first national law
    assert pts["taiwan_province_of_china"]["value"] == 2019  # Asia's first
    # The statute citation rides the point (the dist's rendering of the
    # curated citation column).
    assert "2013-404" in pts["france"]["citation"]
    assert "Obergefell" in pts["united_states"]["citation"]

    # The sources block: one curated source, the national_legislation root.
    assert payload["sources"][0]["root"] == "national_legislation"
    assert payload["sources"][0]["role"] == "canonical"

    # No range violation: every year sits inside 1990-2030.
    ssm = [r for r in validate_results if r["indicator_id"] == "same_sex_marriage_legalization_year"]
    assert ssm and ssm[0]["range_violations"] == []


def test_universal_suffrage_marker_carries_todds_own_dating(tmp_path, real_indicators, real_entities):
    # The SECOND MARKER (v15): L'invention de l'Europe's anthropological
    # fingerprint — the franchise's arrival dated as the historiography
    # dates it (which for the 19th-century introductions IS the male
    # grant, exactly as Todd dates Austria 1907 / Belgium 1919 / Sweden
    # '1911/1921'), the male/female decomposition riding every note.
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "universal_suffrage_introduction_year.json").read_text())

    tr = payload["todd_refs"]
    assert (tr["citations"], tr["books"]) == (7, 1)
    assert tr["refs"][0]["book"] == "L'invention de l'Europe" and tr["refs"][0]["year"] == 1990

    # 16 countries, one point each, year == value, 1848-1946.
    data = payload["data"]
    assert len(data) == 16
    assert all(d["year"] == d["value"] for d in data)
    assert all(d.get("citation") and d.get("definition_note") for d in data)

    pts = {d["entity_id"]: d for d in data}
    # The cases the corpus label itself names: Sweden's dual dating (the
    # marker = the male grant 1911, the note carries the female half
    # 1921 — Todd prints the pair), Austria 1907, Belgium 1919.
    assert pts["sweden"]["value"] == 1911
    assert "1921" in pts["sweden"]["definition_note"]
    assert pts["austria"]["value"] == 1907
    assert pts["belgium"]["value"] == 1919
    # The founding grants and the famous latecomers.
    assert pts["france"]["value"] == 1848
    assert pts["germany"]["value"] == 1871
    assert pts["switzerland"]["value"] == 1848
    assert "1971" in pts["switzerland"]["definition_note"]  # the women's half, in the note
    assert pts["italy"]["value"] == 1946
    assert pts["norway"]["value"] == 1913  # the standard dating here IS the women's grant

    # The catalog carries the markers family and the todd_refs block.
    catalog = {c["id"]: c for c in json.loads((dist_dir / "catalog.json").read_text())}
    assert catalog["same_sex_marriage_legalization_year"]["family"] == "markers"
    assert catalog["universal_suffrage_introduction_year"]["todd_refs"]["citations"] == 7


# --- v17: consanguineous_marriage_rate + unemployment_rate ----------------


def test_consanguineous_marriage_rate_is_the_curated_backlog_head(tmp_path, real_indicators, real_entities):
    # The THIRTEENTH INDICATOR (v17), the corpus's #6 (34 citations, 10
    # books — Le Destin des immigrés alone carries 16): the backlog's
    # head, entering through the CURATED tier (the gate finding: no
    # machine-readable door anywhere — GHO 0 hit, WDI 0/25000, OWID 404).
    # The table's own shape: one row per (country, study year), 102
    # rows, 69 countries, 1943-2021 — the Bittles-compilation prints
    # plus the directly-verified DHS/journal readings, one citation per
    # point, the SUBNATIONAL scopes flagged in every note they ride.
    processed_dir, dist_dir, _, validate_results = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "consanguineous_marriage_rate.json").read_text())

    assert payload["todd_core"] is True
    tr = payload["todd_refs"]
    assert (tr["citations"], tr["books"]) == (34, 10)
    assert payload["unit"] == "percent"
    assert payload["family"] == "society"
    assert payload["witnesses"] == []  # no witness tier can exist: nothing upstream to witness

    canon = {(d["entity_id"], d["year"]): d for d in payload["data"]}
    assert len(canon) == 102  # every curated row survives its own merge (arbitration-free by construction)
    assert len({e for e, _ in canon}) == 69
    assert min(y for _, y in canon) == 1943  # the Spanish dispensation window 1940/43
    assert max(y for _, y in canon) == 2021  # the India NFHS-5 pooling window's end

    # THE EUROPEAN REGISTRY BELT (the sub-1% exogamous North): France
    # 1958 over 510,000 dispensations — Sutter & Goux, the classic INED
    # source; Norway's three registry vintages (the million-marriage
    # decline 0.6 -> 0.7 -> 0.1); the two Masterson island readings.
    assert canon[("france", 1958)]["value"] == pytest.approx(0.8)
    assert "Sutter & Goux" in canon[("france", 1958)]["citation"]
    assert canon[("france", 1958)]["definition_note"].startswith("National (All-France)")
    assert canon[("norway", 1972)]["value"] == pytest.approx(0.6)
    assert canon[("norway", 1981)]["value"] == pytest.approx(0.7)
    assert canon[("norway", 1993)]["value"] == pytest.approx(0.1)
    assert canon[("ireland", 1968)]["value"] == pytest.approx(0.5)     # the Republic's own arm
    assert canon[("united_kingdom", 1968)]["value"] == pytest.approx(0.4)  # the NI arm, UK-scoped

    # THE MUSLIM-WORLD BELT (the corpus's heart): Pakistan's four DHS
    # vintages (Todd's Après l'Empire early-1990s face and the 2017-18
    # reading read directly from FR354 Table 4.5), Iran's national
    # 38.6 over 306,343 couples, Saudi Arabia's 56.0 national survey,
    # the Maghreb trio, the world maximum.
    for year, value in [(1991, 61.2), (2007, 60.5), (2013, 56.4), (2018, 63.9)]:
        assert canon[("pakistan", year)]["value"] == pytest.approx(value)
    assert "Table 4.5" in canon[("pakistan", 2018)]["citation"]  # the directly-read DHS print
    assert canon[("iran_islamic_republic_of", 2001)]["value"] == pytest.approx(38.6)
    assert canon[("saudi_arabia", 2005)]["value"] == pytest.approx(56.0)
    assert canon[("algeria", 1979)]["value"] == pytest.approx(22.6)
    assert canon[("morocco", 1992)]["value"] == pytest.approx(19.9)
    assert canon[("tunisia", 2008)]["value"] == pytest.approx(29.8)
    assert canon[("burkina_faso", 2001)]["value"] == pytest.approx(65.8)  # the table's world maximum
    assert canon[("turkiye", 2013)]["value"] == pytest.approx(18.5)       # the Kaplan national survey
    assert canon[("palestine_state_of", 2004)]["value"] == pytest.approx(27.7)

    # THE CULTURAL PIVOTS: the two Israels are the Arab community's own
    # national surveys (the scope is the study's, the note says so);
    # Todd's own Sudan 57% vs the entered Khartoum 52.0 — as-reported
    # on both ends, the divergence documented on the row.
    assert canon[("israel", 1977)]["value"] == pytest.approx(34.2)
    assert canon[("israel", 1977)]["definition_note"].startswith("Scope: the Arab community of Israel")
    assert canon[("sudan", 1988)]["value"] == pytest.approx(52.0)
    assert "57%" in canon[("sudan", 1988)]["definition_note"]

    # THE CURATION GATE'S MECHANICAL ARM: every point carries its
    # citation (the connector rejects empty ones at parse — this
    # asserts the dist end of the same guarantee) and its scope note.
    assert all(d["citation"] for d in payload["data"])
    assert all(d["definition_note"] for d in payload["data"])

    # No range violation (the as-reported zero Panama 1957 and the
    # 65.8 Fulani maximum both sit inside the corpus's own 0-70 scale).
    cons = [r for r in validate_results if r["indicator_id"] == "consanguineous_marriage_rate"]
    assert cons and cons[0]["range_violations"] == []

    # THE ROOT: the consanguinity-studies literature — the study IS the
    # origin, no upstream redistributor to disclose.
    catalog = {c["id"]: c for c in json.loads((dist_dir / "catalog.json").read_text())}
    roots = catalog["consanguineous_marriage_rate"]["roots"]
    assert roots["canonical"] == [{
        "root": "consanguinity_studies",
        "label": "The consanguinity-studies literature (national surveys and dispensation registries; "
                 "Bittles' consang.net compilation + DHS final reports, cited per point)",
        "doors": 1,
    }]
    assert "witness" not in roots or roots["witness"] == []


def test_unemployment_rate_is_two_tier_with_the_coverage_cliff(tmp_path, real_indicators, real_entities):
    # The FOURTEENTH INDICATOR (v17), the economy family's first (20
    # citations, 7 books): canonical = Eurostat une_rt_a pinned
    # Y15-74/PC_ACT/T — the LFS questionnaire's own national rates at
    # the 1-decimal as-published face (the probe verdict: ILOSTAT is
    # wholesale ILO-processed, OECD OECD-harmonized, NO other collector
    # prints the plain rate) — witness = the WB national-estimate line
    # (the ILOSTAT DEAP family redistributed by WDI, byte-identical on
    # the co-covered core). THE DISPLAY CASES: the COVERAGE CLIFF (DE
    # 1991-2008 lives only on the witness; the collector starts DE at
    # 2009) and the LFS-2021 DEFINITIONAL SEAM ('d' on FR 2021-2025 —
    # quality_code carries it, the series is one continuous line).
    processed_dir, dist_dir, _, validate_results = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "unemployment_rate.json").read_text())

    assert payload["todd_core"] is True
    tr = payload["todd_refs"]
    assert (tr["citations"], tr["books"]) == (20, 7)
    assert payload["unit"] == "percent"
    assert payload["family"] == "economy"  # the family's first indicator

    canon = {(d["entity_id"], d["year"]): d for d in payload["data"]}
    # THE LIVE ANCHORS: France the door's own start (2003), the 2015
    # print both tiers carry (collector 10.4, witness 10.354 — the
    # rounding seam the root pair explains), the 2023 'd' flag.
    assert canon[("france", 2003)]["value"] == pytest.approx(8.5)
    assert canon[("france", 2015)]["value"] == pytest.approx(10.4)
    assert canon[("france", 2023)]["value"] == pytest.approx(7.4)
    assert canon[("france", 2023)]["quality_code"] == "d"
    assert "provisional" not in canon[("france", 2023)]  # 'd' is definitional, not provisional
    assert canon[("france", 2024)]["quality_code"] == "d"
    assert canon[("germany", 2009)]["value"] == pytest.approx(7.3)
    assert canon[("germany", 2023)]["value"] == pytest.approx(3.1)
    assert canon[("spain", 2013)]["value"] == pytest.approx(26.1)   # the crisis peak, as published
    assert canon[("greece", 2013)]["value"] == pytest.approx(27.8)
    assert canon[("montenegro", 2020)]["value"] == pytest.approx(17.9)  # the short series' last year
    # THE COVERAGE CLIFF: DE 2005 is ABSENT on the collector (the door
    # starts DE at 2009 — absence is information, no patch).
    assert ("germany", 2005) not in canon
    # sex=None: the T pin IS the both-sexes rate (the M/F doors are one
    # ref away, unwired).
    assert all(d.get("sex") is None for d in payload["data"])

    # THE WITNESS: the WB national-estimate line — worldwide, and
    # carrying the years the collector lacks.
    assert len(payload["witnesses"]) == 1
    witness = payload["witnesses"][0]
    assert (witness["provider"], witness["source_ref"]) == ("worldbank", "SL.UEM.TOTL.NE.ZS")
    assert witness["root"] == "ilo_lfs"
    wit = {(d["entity_id"], d["year"]): d for d in witness["data"]}
    assert wit[("france", 1990)]["value"] == pytest.approx(9.36)     # the pre-collector year
    assert wit[("germany", 1991)]["value"] == pytest.approx(5.316)   # DE 1991: witness-only
    assert wit[("germany", 2005)]["value"] == pytest.approx(11.193)  # THE CLIFF'S other side
    assert wit[("france", 2015)]["value"] == pytest.approx(10.354)   # the same rate, the finer print
    assert wit[("france", 2024)]["value"] == pytest.approx(7.436)    # the rounding seam
    assert wit[("united_states", 1991)]["value"] == pytest.approx(6.8)
    assert wit[("spain", 2013)]["value"] == pytest.approx(26.094)
    # Kosovo prints on the witness (XKX 2001 = 57.0, the post-war
    # break) but resolves to no entity: the pending class, as ever.
    assert all(e != "kosovo" for e, _ in wit)

    # No range violation on either tier (the crisis peaks and XKX's
    # post-war break all sit inside 0-60).
    une = [r for r in validate_results if r["indicator_id"] == "unemployment_rate"]
    assert une and une[0]["range_violations"] == []
    assert all(not wv["range_violations"] for wv in une[0]["witnesses"])

    # THE ROOT PAIR: eurostat_lfs (the collector) vs ilo_lfs (the
    # ILO-processed family) — two doors over the same national surveys,
    # one harmonization step apart.
    catalog = {c["id"]: c for c in json.loads((dist_dir / "catalog.json").read_text())}
    roots = catalog["unemployment_rate"]["roots"]
    assert {r["root"] for r in roots["canonical"]} == {"eurostat_lfs"}
    assert {r["root"] for r in roots["witness"]} == {"ilo_lfs"}
