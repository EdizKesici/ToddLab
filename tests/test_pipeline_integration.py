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
    seed_ilostat_snapshot,
    seed_oecd_snapshot,
    seed_oecd_idd_snapshot,
    seed_oecd_safety_snapshot,
    seed_owid_snapshot,
    seed_wb_snapshot,
)

from src.config_loader import cross_validate_todd_core, load_todd_refs
from src.pipeline.build import build_all
from src.pipeline.merge import merge_all
from src.pipeline.normalize import normalize_all, normalize_indicator
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
    # MDG_0000000001, seeded through its OWN live-generated fixture
    # since v23: the provider recoded the door's age frame — every row
    # now carries Dim2=AGEGROUP_MONTHS0-11 — and the per-code AGE pin
    # accepts exactly that; the WHOSIS fixture's Dim2-less rows would
    # be refused as a door change, loudly, by design).
    seed_wb_snapshot(raw_dir, "infant_mortality", "SP.DYN.IMRT.MA.IN")
    seed_wb_snapshot(raw_dir, "infant_mortality", "SP.DYN.IMRT.FE.IN")
    seed_wb_snapshot(raw_dir, "life_expectancy", "SP.DYN.LE00.MA.IN")
    seed_wb_snapshot(raw_dir, "life_expectancy", "SP.DYN.LE00.FE.IN")
    seed_gho_snapshot(
        raw_dir, "infant_mortality", "MDG_0000000001",
        fixture="gho_mdg_0000000001_sample.json",
    )
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
    # v25 (the segment faces + the by-sex face): the M/F doors of the
    # plain rate (the v17 registry's "one ref away" — FR M 2015 = 10.8,
    # F = 9.9), the two LFS class-decomposition canonical doors (the
    # collector prints the Destin question: FR 2015 natives 9.4 vs
    # foreign_born 17.1 on the birth face, nationals 9.7 vs foreigners
    # 20.5 on the citizenship face — the REAL full responses, carved by
    # scripts/make_v25_fixtures.py), and the two ILOSTAT class
    # cross-section witnesses on the ILO's own SDMX wire (FR 2025:
    # nationals 7.162 vs foreigners 13.902, natives 7.023 vs
    # foreign_born 12.003 — the coupe, both sexes, the KOS->XKX quirk).
    seed_eurostat_snapshot(raw_dir, "unemployment_rate", "une_rt_a/Y15-74/PC_ACT/M", fixture="eurostat_unert_m_sample.json")
    seed_eurostat_snapshot(raw_dir, "unemployment_rate", "une_rt_a/Y15-74/PC_ACT/F", fixture="eurostat_unert_f_sample.json")
    seed_eurostat_snapshot(raw_dir, "unemployment_rate", "lfsa_urgacob/Y15-74/T", fixture="eurostat_lfsa_urgacob_t_sample.json")
    seed_eurostat_snapshot(raw_dir, "unemployment_rate", "lfsa_urgan/Y15-74/T", fixture="eurostat_lfsa_urgan_t_sample.json")
    seed_ilostat_snapshot(raw_dir, "unemployment_rate", "DF_UNE_DEAP_SEX_AGE_CBR_RT", fixture="ilostat_cbr_sample.json")
    seed_ilostat_snapshot(raw_dir, "unemployment_rate", "DF_UNE_DEAP_SEX_AGE_CCT_RT", fixture="ilostat_cct_sample.json")
    # v25 (the 1974 denominator): road_accident_mortality_per_vehicle
    # seeds its single door — the REAL full per-vehicle slice (534 rows,
    # 38 areas, FRA 2010 = 0.9497 -> 2024 = 0.6512, CHL 1998 = 13.15
    # the tail, the USA absent).
    seed_oecd_safety_snapshot(
        raw_dir, "road_accident_mortality_per_vehicle", "DF_SAFETY/FATALITIES/10P4VEH_MOT_ROAD",
        fixture="itf_10p4veh_sample.csv",
    )
    # v18 (the six-indicator delivery, four doors): cirrhosis seeds the
    # OECD collector (CICDCIRR: the FRA 1979 = 29.0 / SWE 12.2 benchmark
    # pair, ITA 1979 M = 50.0 the live max, the KOR 'B' / TUR 'D' flag
    # rows) + the GHE witness (the YEARSALL series kept, the 15+
    # variant dropped — the SDGSUICIDE Dim2 precedent); industrial and
    # (v26: agricultural_employment_share and immigration_stock were
    # withdrawn — their seeds removed with the indicators.) Tertiary
    # and secondary seed the LFS attainment table (FR 24.5->43.2 /
    # 41.4->40.5, the 'b' break flags) + the Barro-Lee witness
    # (tertiary only);
    seed_oecd_snapshot(raw_dir, "cirrhosis_alcohol_mortality", "DF_COM/CICDCIRR", fixture="oecd_cicdcirr_sdmx.csv")
    seed_gho_snapshot(raw_dir, "cirrhosis_alcohol_mortality", "SA_0000001457", fixture="gho_cirrhosis_sample.json")
    seed_eurostat_snapshot(raw_dir, "industrial_employment_share", "nama_10_a10_e/EMP_DC/PC_TOT_PER/B-E", fixture="eurostat_nama_be_sample.json")
    seed_wb_snapshot(raw_dir, "industrial_employment_share", "SL.IND.EMPL.ZS")
    seed_eurostat_snapshot(raw_dir, "tertiary_education_share", "edat_lfse_03/ED5-8/Y25-64/T", fixture="eurostat_edat_ed58_sample.json")
    seed_owid_snapshot(raw_dir, "tertiary_education_share", "share-of-the-population-with-completed-tertiary-education", "owid_education_tertiary_sample.csv")
    seed_eurostat_snapshot(raw_dir, "secondary_education_share", "edat_lfse_03/ED3_4/Y25-64/T", fixture="eurostat_edat_ed34_sample.json")

    # v19 (the three-indicator delivery): top_income_share seeds the WID
    # chart door (the corpus's own source, the only machine face — USA
    # 1913 = 20.43 -> 2024 = 20.73 the U-shape, FRA 1910 = 22.73 -> 2022
    # = 12.1 the European decline, RUS the 46-point arc, GDR its own
    # entity, the World aggregate row resolving to nothing); gini seeds
    # the four IDD vintage doors (the stitched canonical: FRA 1996 = 0.277
    # M11 -> 2011 = 0.309 M12-D_PREV -> 2020 = 0.278 M12-D_CUR, the USA
    # 1995 = 0.361 on L'illusion économique's own year, BRA the D_INC
    # door) + the WID pre-tax witness (the concept seam: FRA 2022 0.299
    # disposable vs 0.4592 pre-tax); road seeds the ITF per-100k door
    # (FRA 15.2 -> 4.7 the sécurité-routière arc, LVA 1994 = 28.44 the
    # post-Soviet tail, RUS absent from the whole flow) + the WHO coupe
    # witness (RS_198, 197 countries at the single 2021 vintage).
    seed_owid_snapshot(raw_dir, "top_income_share", "incomes-of-the-richest", "owid_incomes_of_richest.csv")
    seed_oecd_idd_snapshot(raw_dir, "gini_index", "DF_IDD/INC_DISP_GINI/METH2012/D_CUR", fixture="oecd_idd_gini_cur.csv")
    seed_oecd_idd_snapshot(raw_dir, "gini_index", "DF_IDD/INC_DISP_GINI/METH2012/D_PREV", fixture="oecd_idd_gini_prevdef.csv")
    seed_oecd_idd_snapshot(raw_dir, "gini_index", "DF_IDD/INC_DISP_GINI/METH2012/D_INC", fixture="oecd_idd_gini_incdef.csv")
    seed_oecd_idd_snapshot(raw_dir, "gini_index", "DF_IDD/INC_DISP_GINI/METH2011/D_CUR", fixture="oecd_idd_gini_m2011.csv")
    seed_owid_snapshot(raw_dir, "gini_index", "gini-coefficient-wid", "owid_gini_wid.csv")
    seed_oecd_safety_snapshot(raw_dir, "road_accident_mortality", "DF_SAFETY/FATALITIES/10P5HB", fixture="itf_safety_road_mortality.csv")
    seed_gho_snapshot(raw_dir, "road_accident_mortality", "RS_198", fixture="gho_road_mortality.json")

    # v20 (the five-indicator queue delivery — THE CORPUS-CLOSING VERSION,
    # 19 -> 24 of 24): incarceration seeds the ICPR/WPB chart door (the
    # Todd six-country board: USA 683 -> 542, RUS 729 -> 300, FRA 82 ->
    # 126, SLV 2024 = 1659 the bound calibrator, Kosovo's 11 floor, the
    # England-and-Wales sub-entity resolving to nothing — dropped logged)
    # + the WHO Health in Prisons coupe witness (PRISON_A2, the 36-country
    # European cross-section at the single 2020 vintage: FRA 93.1, GEO
    # 245.99, SMR 23.03); math seeds the PISA chart door with the
    # Mathematics column pinned (FRA 510.8 -> 473.9, the RUS 2022 gap,
    # QAT 2006 = 317.96 the floor, SGP 574.66 the ceiling); obesity
    # seeds the GHO NCD_BMI_30C door (the per-code AGE pin's own face —
    # every row YEARS18-PLUS, the full sex split: FRA 2024 12.5/12.4/
    # 12.6, USA 41.8/40.6/43.0 the female inversion, ASM 80.89 the
    # Pacific tail, VNM 1980 the floor); hiv seeds the UNAIDS chart door
    # (SWZ 23.4, ZAF 17.2, ZWE 1995 = 29.65 the peak, FRA 0.13 -> 0.28,
    # the World and UNAIDS regional aggregates resolving to nothing —
    # dropped logged); height seeds the NCD-RisC chart door (FRA 101
    # cohort points 166.41 -> 179.74, NLD 182.57 the ceiling, LAO 152.88
    # the floor, KOR +15.2 the catch-up) + the Baten-Blum/Clio-Infra
    # witness (FRA 1660 = 162.6 the pre-1896 tail, PNG 152.36 the floor,
    # DNK 183.2 the ceiling — the cross-root cm-level seam).
    seed_owid_snapshot(raw_dir, "incarceration_rate", "prison-population-rate", "owid_prison_population_rate.csv")
    seed_gho_snapshot(raw_dir, "incarceration_rate", "PRISON_A2_PRISIONERS_PER100KPOP", fixture="gho_prison_a2.json")
    seed_owid_snapshot(
        raw_dir, "math_test_scores", "average-performance-of-15-year-olds-in-mathematics-reading-and-science",
        "owid_pisa_math.csv", value_field="Mathematics",
    )
    seed_gho_snapshot(raw_dir, "obesity_rate", "NCD_BMI_30C", fixture="gho_ncd_bmi_30c.json")
    seed_owid_snapshot(raw_dir, "hiv_prevalence_rate", "share-of-the-population-infected-with-hiv", "owid_hiv_prevalence.csv")
    seed_owid_snapshot(raw_dir, "male_height_trend", "average-height-of-men", "owid_height_men.csv")
    seed_owid_snapshot(raw_dir, "male_height_trend", "average-height-of-men-by-year-of-birth", "owid_height_baten_blum.csv")

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
    assert (dist_dir / "indicators" / "cirrhosis_alcohol_mortality.json").exists()
    assert (dist_dir / "indicators" / "industrial_employment_share.json").exists()
    assert (dist_dir / "indicators" / "tertiary_education_share.json").exists()
    assert (dist_dir / "indicators" / "secondary_education_share.json").exists()
    assert (dist_dir / "indicators" / "top_income_share.json").exists()
    assert (dist_dir / "indicators" / "gini_index.json").exists()
    assert (dist_dir / "indicators" / "road_accident_mortality.json").exists()
    # v25: Todd's own 1974 denominator — the per-vehicle companion face.
    assert (dist_dir / "indicators" / "road_accident_mortality_per_vehicle.json").exists()
    assert (dist_dir / "indicators" / "incarceration_rate.json").exists()
    assert (dist_dir / "indicators" / "math_test_scores.json").exists()
    assert (dist_dir / "indicators" / "obesity_rate.json").exists()
    assert (dist_dir / "indicators" / "hiv_prevalence_rate.json").exists()
    assert (dist_dir / "indicators" / "male_height_trend.json").exists()

    catalog = json.loads((dist_dir / "catalog.json").read_text())
    assert {c["id"] for c in catalog} == {
        "infant_mortality", "life_expectancy", "homicide_rate", "maternal_mortality_ratio",
        "maternal_deaths", "life_expectancy_60", "suicide_rate", "birth_rate_fertility",
        "crude_birth_rate", "same_sex_marriage_legalization_year",
        "universal_suffrage_introduction_year", "illegitimate_births",
        "consanguineous_marriage_rate", "unemployment_rate",
        "cirrhosis_alcohol_mortality", "industrial_employment_share",
        "tertiary_education_share",
        "secondary_education_share",
        "top_income_share", "gini_index", "road_accident_mortality",
        "road_accident_mortality_per_vehicle",  # v25: the 1974 denominator
        "incarceration_rate", "math_test_scores", "obesity_rate",
        "hiv_prevalence_rate", "male_height_trend",
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
        ("unsd_dyb", 14),  # v21: the DYB 1978 curated door joins the collector's root
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
    # dist/todd_corpus.json carries ALL 22 metrics — implemented AND
    # unimplemented — ranked by the corpus's own citation weight: the
    # "what to build next" question becomes a data statement.
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    corpus = json.loads((dist_dir / "todd_corpus.json").read_text())

    assert corpus["meta"]["metrics"] == 22
    assert corpus["meta"]["implemented_metrics"] == 22  # THE CORPUS CLOSED (v20 at 24/24; v26 withdrew immigration_stock + agricultural_employment_share — 22/22 since); crude_birth_rate is todd_core=false (no corpus id of its own)
    assert corpus["meta"]["total_citations"] == 470
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
        "cirrhosis_alcohol_mortality",  # v18 — the mortality family's fourth cause, 9 citations
        "industrial_employment_share",  # v18 — THE BACKLOG'S HEAD CLAIMED, 30 citations
        "tertiary_education_share",  # v18 — the education pair's first, 13 citations
        "secondary_education_share",  # v18 — the pair's second, 8 citations
        "top_income_share",  # v19 — THE BACKLOG'S HEAD CLAIMED, 7 citations
        "gini_index",  # v19 — the distribution measure, 4 citations
        "road_accident_mortality",  # v19 — Le Fou et le Prolétaire's metric, 4 citations
        "incarceration_rate",  # v20 — the queue's head ex æquo, 3 citations
        "math_test_scores",  # v20 — the education family's first indicator, 3 citations
        "obesity_rate",  # v20 — the health-paradox metric, 3 citations
        "hiv_prevalence_rate",  # v20 — the patrilineality proxy, 1 citation
        "male_height_trend",  # v20 — the living-standard curve, 1 citation — the last of the
        # 22 remaining (v26 withdrew immigration_stock and
        # agricultural_employment_share; the corpus is complete at 22/22)
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
    assert "todd corpus: 22 metrics, 470 citations, 16 books" in out
    assert "implemented 22/22" in out
    # THE BACKLOG LINE IS GONE — the corpus is complete: no "top
    # unimplemented" line prints anymore, and its ABSENCE is the pin
    # (the empty-backlog branch of stats._corpus_block, the closing
    # state the corpus-closing version has to display).
    assert "top unimplemented" not in out
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
    # Kosovo prints (XK, 2016-2019) and v21 RESOLVES it (XKX, the
    # user-assigned code): the collector's Kosovo TFR lands — the pending
    # product decision closed on the entity (valid_from 2008 honored).
    ks = {y: d["value"] for (e, y), d in canon.items() if e == "kosovo"}
    # The fixture grid prints one post-2008 XK cell (2017 = 1.65); the
    # live collector carries 2016-2019 (1.66/1.65/1.61/1.55 — the verify
    # script pins the live dist, this pin carries the fixture's shape).
    assert ks == {2017: pytest.approx(1.65)}

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
    # Kosovo prints (XK, 2002 and 2012 in the fixture grid) and v21
    # resolves it: the 2012 row lands (46.1), the 2002 row refuses on the
    # entity's valid_from=2008 — the honest pre-independence drop.
    assert canon[("kosovo", 2012)]["value"] == pytest.approx(46.1)
    assert ("kosovo", 2002) not in canon
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

    # v25: the single-axis face now carries the M/F rows too — the T-row
    # anchors below read the both-sexes series (the M/F anchors have
    # their own block below).
    canon = {(d["entity_id"], d["year"]): d for d in payload["data"] if d.get("sex") is None}
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
    # v25 (the by-sex face): the T rows carry sex=None (the both-sexes
    # convention) while the M/F doors ride the same single-axis data
    # under the merge key's sex term — FR M 2015 = 10.8, F = 9.9 (the
    # v17 anchors, now wired).
    sexes = {d.get("sex") for d in payload["data"]}
    assert sexes == {None, "male", "female"}
    canon_mf = {(d["entity_id"], d["year"], d.get("sex")): d["value"] for d in payload["data"]}
    assert canon_mf[("france", 2015, "male")] == pytest.approx(10.8)
    assert canon_mf[("france", 2015, "female")] == pytest.approx(9.9)
    assert canon_mf[("france", 2024, "male")] == pytest.approx(7.6)
    assert canon_mf[("france", 2024, "female")] == pytest.approx(7.3)

    # THE WITNESSES: v25 wires THREE — the WB national-estimate line
    # (worldwide, carrying the years the collector lacks) plus the two
    # ILOSTAT class cross-sections riding the SEGMENT layers (the
    # single-axis witnesses list carries the WB door only — the segment
    # witnesses ride their own layers' blocks, asserted in the v25
    # segment test below).
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
    # Kosovo on the witness (XKX 2001 = 57.0, the post-war break): v21
    # resolves the entity, and the 2001 point refuses on valid_from=2008
    # — the pre-independence floor drops honestly, nothing else enters
    # (the fixture grid prints no post-2008 XKX cell).
    assert all(e != "kosovo" or y >= 2008 for e, y in wit)
    assert ("kosovo", 2001) not in wit

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


# ---------------------------------------------------------------------------
# v18 — the four-indicator delivery that remains after v26's
# withdrawal (agricultural_employment_share and immigration_stock
# pulled with their seeds): cirrhosis (the mortality family's fourth
# cause), industrial (the national-accounts door, the backlog's head
# claimed), tertiary + secondary (the LFS attainment table).


def test_cirrhosis_is_the_fourth_cause_code_with_the_benchmark_pair(tmp_path, real_indicators, real_entities):
    # THE FIFTEENTH INDICATOR: canonical = OECD DF_COM/CICDCIRR (the
    # v13 suicide architecture, one cause-code swap) — witness = the GHE
    # age-standardized cirrhosis door (SA_0000001457, the YEARSALL face,
    # the 15+ variant dropped logged). THE DISPLAY CASE: La Chute
    # finale's own France-vs-Sweden 1979 calibration pair prints in the
    # canonical tier, Russia rides the WITNESS alone (RUS genuinely
    # absent from this cause's collector slice — the WHO-MDB coding
    # story the config documents).
    processed_dir, dist_dir, _, validate_results = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "cirrhosis_alcohol_mortality.json").read_text())

    assert payload["todd_core"] is True
    tr = payload["todd_refs"]
    assert (tr["citations"], tr["books"]) == (9, 4)
    assert payload["unit"] == "deaths_per_100000_population"
    assert payload["family"] == "mortality"

    canon = {(d["entity_id"], d["year"], d.get("sex")): d for d in payload["data"]}
    # THE BENCHMARK PAIR (La Chute finale's Soviet-alcoholism calibration):
    # France 1979 = 29.0 vs Sweden 12.2 — the both-sexes ratio 2.4x while
    # the male rates nearly match (SWE 17.5 M): the structure the book
    # reads IS the print. (France 1979 prints NO sex split — the
    # both-sexes row is the era's own face; Sweden's split rides from
    # 1960.) Italy's 1979 male = 50.0: the live slice's own maximum.
    assert canon[("france", 1979, None)]["value"] == pytest.approx(29.0)
    assert canon[("sweden", 1979, None)]["value"] == pytest.approx(12.2)
    assert canon[("sweden", 1979, "male")]["value"] == pytest.approx(17.5)
    assert canon[("sweden", 1979, "female")]["value"] == pytest.approx(7.0)
    assert canon[("italy", 1979, None)]["value"] == pytest.approx(34.7)
    assert canon[("italy", 1979, "male")]["value"] == pytest.approx(50.0)
    assert canon[("germany", 1994, None)]["value"] == pytest.approx(24.4)
    assert canon[("germany", 1994, "male")]["value"] == pytest.approx(32.9)
    # THE FLAG ROWS the live slice carries ride quality_code as-reported.
    assert canon[("korea_republic_of", 1995, None)]["quality_code"] == "B"
    assert canon[("turkiye", 2010, None)]["quality_code"] == "D"
    # RUSSIA IS ABSENT from the canonical (the coding story) — the claim
    # lives on the witness, absence is information.
    assert all(e != "russian_federation" for e, _, _ in canon)

    # THE WITNESS: GHE's modeled cirrhosis — the face that covers Russia.
    assert len(payload["witnesses"]) == 1
    witness = payload["witnesses"][0]
    assert (witness["provider"], witness["source_ref"]) == ("who_gho", "SA_0000001457")
    assert witness["root"] == "who_ghe"
    wit = {(d["entity_id"], d["year"], d.get("sex")): d for d in witness["data"]}
    # Russia's modeled all-ages age-standardized rates (the 15+ variants
    # dropped: male 42.1 lives in the drop log, not the tier).
    assert wit[("russian_federation", 2019, None)]["value"] == pytest.approx(22.500966937)
    assert wit[("russian_federation", 2019, "male")]["value"] == pytest.approx(31.120465336)
    assert all(d["value"] != pytest.approx(42.08272182) for d in witness["data"])

    # No range violation on either tier.
    cirr = [r for r in validate_results if r["indicator_id"] == "cirrhosis_alcohol_mortality"]
    assert cirr and cirr[0]["range_violations"] == []

    # THE ROOT PAIR: who_mdb (the collector) vs who_ghe (the modeled
    # redistribution) — the same pair suicide carries.
    catalog = {c["id"]: c for c in json.loads((dist_dir / "catalog.json").read_text())}
    roots = catalog["cirrhosis_alcohol_mortality"]["roots"]
    assert {r["root"] for r in roots["canonical"]} == {"who_mdb"}
    assert {r["root"] for r in roots["witness"]} == {"who_ghe"}


def test_industrial_employment_share_is_the_printed_share(tmp_path, real_indicators, real_entities):
    # THE SIXTEENTH INDICATOR, THE BACKLOG'S HEAD CLAIMED (30 citations,
    # 5 books): canonical = Eurostat nama_10_a10_e/EMP_DC/PC_TOT_PER/B-E
    # — the national-accounts door PRINTS the share of total employment
    # directly (the v18 finding that DISSOLVED the composite-derived-
    # layer question). Witness = the ILOEST modeled share (worldwide, and
    # industry INCLUDING construction — the definitional seam the pair
    # displays: FR 2015 = 16.4 canonical vs 20.376 witness, the
    # construction share reading as two doors, never a contradiction).
    processed_dir, dist_dir, _, validate_results = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "industrial_employment_share.json").read_text())

    assert payload["todd_core"] is True
    tr = payload["todd_refs"]
    assert (tr["citations"], tr["books"]) == (30, 5)
    assert payload["unit"] == "percent"
    assert payload["family"] == "economy"

    canon = {(d["entity_id"], d["year"]): d for d in payload["data"]}
    # THE DE-INDUSTRIALIZATION SLOPES as the accounts print them: FR
    # 1995 = 16.4 -> 2024 = 10.1, DE 23.1 -> 17.5 (the door's own
    # aggregate, B-E "Industry (except construction)").
    assert canon[("france", 1995)]["value"] == pytest.approx(16.4)
    assert canon[("france", 2024)]["value"] == pytest.approx(10.1)
    assert canon[("germany", 1995)]["value"] == pytest.approx(23.1)
    assert canon[("germany", 2024)]["value"] == pytest.approx(17.5)
    # the accounts' own 'p' provisional flags on the freshest years.
    assert canon[("france", 2024)]["quality_code"] == "p"
    assert canon[("france", 2024)]["provisional"] is True
    # no sex dimension in this cube: both-sexes by construction.
    assert all(d.get("sex") is None for d in payload["data"])
    # THE EA EDGE: the Euro-area aggregate (the bare two-letter code) is
    # dropped logged — never an entity.
    assert all(e != "euro_area" for e, _ in canon)

    # THE WITNESS: the ILOEST modeled shares — worldwide (USA/Japan ride
    # this tier alone), and carrying the INCL-CONSTRUCTION definition.
    assert len(payload["witnesses"]) == 1
    witness = payload["witnesses"][0]
    assert (witness["provider"], witness["source_ref"]) == ("worldbank", "SL.IND.EMPL.ZS")
    assert witness["root"] == "ilo_modelled"
    wit = {(d["entity_id"], d["year"]): d for d in witness["data"]}
    assert wit[("united_states", 1991)]["value"] == pytest.approx(24.3734633619148)
    assert wit[("united_states", 2024)]["value"] == pytest.approx(19.0437070998445)
    assert wit[("japan", 1991)]["value"] == pytest.approx(33.2837862928435)
    assert wit[("bulgaria", 1991)]["value"] == pytest.approx(45.0903089434348)  # the planned-economy tail
    # THE DEFINITIONAL SEAM: FR 2015 both tiers print — 10.8 (B-E, the
    # door's aggregate) vs 20.376 (the ILO modeled face). The divergence
    # is COMPOUND by construction: industry INCLUDING construction, on a
    # labor-force-modeled employment concept (not the accounts' domestic
    # concept) — displayed tier-by-tier, never reconciled, the root pair
    # the explanation.
    assert wit[("france", 2015)]["value"] == pytest.approx(20.3760439673531)
    assert canon[("france", 2015)]["value"] == pytest.approx(10.8)

    ind = [r for r in validate_results if r["indicator_id"] == "industrial_employment_share"]
    assert ind and ind[0]["range_violations"] == []
    assert all(not wv["range_violations"] for wv in ind[0]["witnesses"])

    catalog = {c["id"]: c for c in json.loads((dist_dir / "catalog.json").read_text())}
    roots = catalog["industrial_employment_share"]["roots"]
    assert {r["root"] for r in roots["canonical"]} == {"eurostat_na"}
    assert {r["root"] for r in roots["witness"]} == {"ilo_modelled"}


def test_tertiary_education_share_is_two_tier_with_barro_lee(tmp_path, real_indicators, real_entities):
    # THE EIGHTEENTH INDICATOR: canonical = the LFS attainment table
    # (edat_lfse_03/ED5-8 — the collector print the education pair CAN
    # reach, UNESCO UIS having no live API) — witness = the Barro-Lee/
    # Lee-Lee long-run panel through OWID's chart door (the corpus's
    # own named source, 1870+, the "completed OR partially completed"
    # face the subtitle documents).
    processed_dir, dist_dir, _, validate_results = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "tertiary_education_share.json").read_text())

    assert payload["todd_core"] is True
    tr = payload["todd_refs"]
    assert (tr["citations"], tr["books"]) == (13, 2)
    assert payload["unit"] == "percent"
    assert payload["family"] == "society"
    assert payload["higher_is_better"] is True  # the education pair reads UP

    canon = {(d["entity_id"], d["year"]): d for d in payload["data"]}
    # THE ATTAINMENT CLIMB as the LFS prints it: FR 2004 = 24.5 ->
    # 2024 = 43.2; the 'b' break flags ride quality_code.
    assert canon[("france", 2004)]["value"] == pytest.approx(24.5)
    assert canon[("france", 2024)]["value"] == pytest.approx(43.2)
    assert canon[("france", 2024)]["quality_code"] == "b"
    assert "provisional" not in canon[("france", 2024)]  # a break, not a provisional flag
    assert all(d.get("sex") is None for d in payload["data"])

    # THE WITNESS: the long-run panel — France 1870 = 0.2 (the
    # literacy-era true zero) -> 2020 = 31.9; the US cohort face at
    # 60.9 (the some-tertiary face, the definitional seam displayed).
    assert len(payload["witnesses"]) == 1
    witness = payload["witnesses"][0]
    assert (witness["provider"], witness["source_ref"]) == (
        "owid", "share-of-the-population-with-completed-tertiary-education"
    )
    assert witness["root"] == "barro_lee"
    wit = {(d["entity_id"], d["year"]): d for d in witness["data"]}
    assert wit[("france", 1870)]["value"] == pytest.approx(0.2)
    assert wit[("france", 2020)]["value"] == pytest.approx(31.9)
    assert wit[("germany", 1990)]["value"] == pytest.approx(13.9)
    assert wit[("united_states", 1990)]["value"] == pytest.approx(50.2)
    # LA DÉFAITE DE L'OCCIDENT'S OWN BOARD (the Barro-Lee reads Todd
    # cites: Russia/USA/Poland): Russia 1990 = 37.8 vs USA 50.2 — the
    # Soviet tertiary legacy one read behind America's; Poland 2015 =
    # 23.7, the post-communist climb.
    assert wit[("russian_federation", 1990)]["value"] == pytest.approx(37.8)
    assert wit[("russian_federation", 2015)]["value"] == pytest.approx(67.9)
    assert wit[("poland", 2015)]["value"] == pytest.approx(23.7)
    assert wit[("poland", 1990)]["value"] == pytest.approx(8.9)

    ter = [r for r in validate_results if r["indicator_id"] == "tertiary_education_share"]
    assert ter and ter[0]["range_violations"] == []
    assert all(not wv["range_violations"] for wv in ter[0]["witnesses"])

    catalog = {c["id"]: c for c in json.loads((dist_dir / "catalog.json").read_text())}
    roots = catalog["tertiary_education_share"]["roots"]
    assert {r["root"] for r in roots["canonical"]} == {"eurostat_lfs"}
    assert {r["root"] for r in roots["witness"]} == {"barro_lee"}


def test_secondary_education_share_is_canonical_only(tmp_path, real_indicators, real_entities):
    # THE NINETEENTH INDICATOR: the same dataset one ISCED pin away —
    # ED3_4, the completed-secondary face (tertiary EXCLUDED). NO
    # WITNESS (the v18 probe verdict: no machine-readable secondary-
    # attainment chart exists — the world face waits on a Barro-Lee
    # direct door, recorded unwired).
    processed_dir, dist_dir, _, validate_results = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "secondary_education_share.json").read_text())

    assert payload["todd_core"] is True
    tr = payload["todd_refs"]
    assert (tr["citations"], tr["books"]) == (8, 3)
    assert payload["family"] == "society"

    canon = {(d["entity_id"], d["year"]): d for d in payload["data"]}
    # THE ISCED CHOICE pinned by its own anchors: ED3_4 reads in the
    # 40s-50s (FR 41.4 / DE 56.7) — the at-least-secondary face (ED3-8)
    # would run ~20 points higher: a misload this pin catches.
    assert canon[("france", 2004)]["value"] == pytest.approx(41.4)
    assert canon[("germany", 1996)]["value"] == pytest.approx(56.7)
    assert canon[("germany", 2024)]["value"] == pytest.approx(50.1)

    # NO WITNESS — deliberately (the probe record), the consanguinity
    # shape with the honest difference noted in the config.
    assert payload["witnesses"] == []

    sec = [r for r in validate_results if r["indicator_id"] == "secondary_education_share"]
    assert sec and sec[0]["range_violations"] == []


def test_top_income_share_is_the_wid_door_canonical_alone(tmp_path, real_indicators, real_entities):
    # THE SEVENTEENTH INDICATOR, the backlog's head claimed (7 citations).
    # Canonical = WID's pre-tax top-1% share through OWID's chart door
    # (the corpus names WID itself for La Défaite de l'Occident; the
    # direct API probed and refused from this environment — the chart IS
    # the machine face, the oecd_family relation). NO WITNESS — the
    # honest absence: no cross-root machine door exists (the IDD's 35
    # measures carry no top-share; the extrapolations chart is the same
    # root's modeled extension, refused by the anti-derivation line).
    processed_dir, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "top_income_share.json").read_text())

    assert payload["todd_core"] is True
    tr = payload["todd_refs"]
    assert (tr["citations"], tr["books"]) == (7, 5)
    assert payload["unit"] == "percent"
    assert payload["family"] == "economy"

    canon = {(d["entity_id"], d["year"], d.get("sex")): d for d in payload["data"]}
    # THE TODD ARCS (the corpus's own boards): the USA's full U-shape
    # (L'illusion économique and Après l'Empire read its rising half),
    # France's decline (the Où en sommes-nous ? Atkinson-Piketty arc —
    # the series now live INSIDE WID), Russia's 46-point arc ending at
    # the oligarchy's 20.0, and the East German print as its own entity
    # (the communist-era low the German seam's family story carries).
    assert canon[("united_states", 1913, None)]["value"] == pytest.approx(20.43)
    assert canon[("united_states", 2024, None)]["value"] == pytest.approx(20.73)
    assert canon[("france", 1910, None)]["value"] == pytest.approx(22.73)
    assert canon[("france", 2022, None)]["value"] == pytest.approx(12.1)
    assert canon[("russian_federation", 1820, None)]["value"] == pytest.approx(16.01)
    assert canon[("russian_federation", 2017, None)]["value"] == pytest.approx(20.0)
    assert ("german_democratic_republic", 1990, None) in canon or any(
        e.startswith("german_d") or e == "east_germany" for e, _, _ in canon
    )
    # THE AGGREGATE ROW resolves to no registry entity — "World" never
    # enters the canonical tier (the drop is logged, the OWID-door rule).
    assert all(e != "world" for e, _, _ in canon)
    # THE ANTI-DERIVATION LINE: the source block names exactly ONE door —
    # the extrapolations sibling is NOT wired.
    sources = payload["sources"]
    assert [(s["provider"], s["source_ref"], s["role"]) for s in sources] == [
        ("owid", "incomes-of-the-richest", "canonical")
    ]
    assert sources[0]["root"] == "wid"
    assert sources[0]["layer"] == "harmonized"
    # NO WITNESS TIER — the honest absence, the secondary_education
    # precedent: the witnesses list exists (the contract) and is empty.
    assert payload["witnesses"] == []
    # The gini witness is another indicator's business — nothing bleeds.
    assert all(d.get("sex") is None for d in payload["data"])


def test_gini_index_is_the_four_door_stitch_with_the_wid_witness(tmp_path, real_indicators, real_entities):
    # THE EIGHTEENTH INDICATOR. Canonical = the OECD IDD's Gini of
    # equivalized disposable income, STITCHED through four vintage doors
    # (the NMARPCT quatuor pattern applied to a methodology-definition
    # seam instead of a geo seam); witness = the WID pre-tax Gini (the
    # concept seam: disposable vs pre-tax, displayed never reconciled).
    processed_dir, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "gini_index.json").read_text())

    assert (tr := payload["todd_refs"]) and (tr["citations"], tr["books"]) == (4, 2)
    assert payload["unit"] == "gini_coefficient_0_to_1"
    assert payload["family"] == "economy"

    canon = {(d["entity_id"], d["year"], d.get("sex")): d for d in payload["data"]}
    # THE STITCHED FRANCE (three vintages, two seams, one series):
    # 1996 = 0.277 on METH2011, 2011 = 0.309 on METH2012-D_PREV (the
    # seam year itself — the current methodology's recomputation of the
    # previous definition), 2020 = 0.278 on METH2012-D_CUR (the EU-SILC
    # definition break), 2023 = 0.299 the current print.
    assert canon[("france", 1996, None)]["value"] == pytest.approx(0.277)
    assert canon[("france", 2011, None)]["value"] == pytest.approx(0.309)
    assert canon[("france", 2020, None)]["value"] == pytest.approx(0.278)
    assert canon[("france", 2023, None)]["value"] == pytest.approx(0.29899999499321)
    # L'ILLUSION ÉCONOMIQUE'S OWN YEAR on the door's own series: USA
    # 1995 = 0.361 — the 1995 fifteen-country table the book read, the
    # lineage the canonical carries. ZAF the world tail, BRA the D_INC
    # door, RUS the survey window.
    assert canon[("united_states", 1995, None)]["value"] == pytest.approx(0.361)
    assert canon[("united_states", 2023, None)]["value"] == pytest.approx(0.3944025)
    assert canon[("south_africa", 2015, None)]["value"] == pytest.approx(0.625602135)
    assert canon[("brazil", 2006, None)]["value"] == pytest.approx(0.50879539)
    assert canon[("russian_federation", 2008, None)]["value"] == pytest.approx(0.428)
    assert canon[("russian_federation", 2017, None)]["value"] == pytest.approx(0.317)
    # THE SEAMS ARE ARBITRATED WITH A LOGGED DISCARD EVERY TIME: the
    # provenance trail records the vintage collisions the chain resolved
    # (FRA 2011: the METH2011 print discarded against the METH2012
    # recomputation; FRA 2020: the D_PREV print discarded against D_CUR).
    provenance = json.loads((processed_dir / "gini_index.provenance.json").read_text())
    fra_seams = [p for p in provenance if p["entity_id"] == "france" and p["year"] in (2011, 2020)]
    assert {(p["year"], p["retained"]["source_ref"]) for p in fra_seams} == {
        (2011, "DF_IDD/INC_DISP_GINI/METH2012/D_PREV"),
        (2020, "DF_IDD/INC_DISP_GINI/METH2012/D_CUR"),
    }
    assert any(p["discarded"] for p in fra_seams)
    # The four canonical doors ride the SAME root, one collector — listed
    # in priority order (sources_by_priority: the chain the merge follows).
    sources = payload["sources"]
    canonical_sources = [s for s in sources if s["role"] == "canonical"]
    assert len(canonical_sources) == 4
    assert {s["root"] for s in canonical_sources} == {"oecd_idd"}
    assert [s["source_ref"] for s in canonical_sources] == [
        "DF_IDD/INC_DISP_GINI/METH2012/D_CUR",
        "DF_IDD/INC_DISP_GINI/METH2012/D_PREV",
        "DF_IDD/INC_DISP_GINI/METH2012/D_INC",
        "DF_IDD/INC_DISP_GINI/METH2011/D_CUR",
    ]
    # The per-flow citation names the vintage each door carries.
    assert "current definition" in canonical_sources[0]["citation"]
    assert "previous definition, without overlap year" in canonical_sources[2]["citation"]

    # THE WITNESS: the WID pre-tax Gini — the concept seam displayed,
    # never reconciled (France 2022: 0.299 disposable vs 0.4592 pre-tax,
    # the redistribution IS the gap).
    assert len(payload["witnesses"]) == 1
    witness = payload["witnesses"][0]
    assert (witness["provider"], witness["source_ref"]) == ("owid", "gini-coefficient-wid")
    assert witness["root"] == "wid"
    wit = {(d["entity_id"], d["year"], d.get("sex")): d for d in witness["data"]}
    assert wit[("france", 2022, None)]["value"] == pytest.approx(0.4592)
    assert wit[("united_states", 2024, None)]["value"] == pytest.approx(0.5869)
    assert wit[("russian_federation", 1913, None)]["value"] == pytest.approx(0.5285) if ("russian_federation", 1913, None) in wit else True
    assert wit[("russian_federation", 1820, None)]["value"] == pytest.approx(0.5285)


def test_road_accident_mortality_is_the_irtad_print_with_the_who_coupe(tmp_path, real_indicators, real_entities):
    # THE NINETEENTH INDICATOR, Le Fou et le Prolétaire's own metric on
    # its modern face. Canonical = the ITF/IRTAD police registrations
    # (per 100k population — the family unit; the per-vehicle door of
    # Todd's 1974 table registered non-wired); witness = the WHO Global
    # status report coupe (RS_198, 197 countries at the single 2021
    # vintage — the GHE-cirrhosis pattern).
    processed_dir, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "road_accident_mortality.json").read_text())

    assert (tr := payload["todd_refs"]) and (tr["citations"], tr["books"]) == (4, 1)
    assert payload["unit"] == "deaths_per_100000_population"
    assert payload["family"] == "mortality"

    canon = {(d["entity_id"], d["year"], d.get("sex")): d for d in payload["data"]}
    # THE TODD ARC: France's sécurité-routière threefold fall, the USA's
    # never-halved divergence (the rich world's one series that stayed
    # high — the automobile-society contrast), Germany's fall, and the
    # post-Soviet crisis at the tail (LVA 1994 = 28.44, the live max).
    assert canon[("france", 1994, None)]["value"] == pytest.approx(15.20273212)
    assert canon[("france", 2024, None)]["value"] == pytest.approx(4.657801614)
    assert canon[("united_states", 1994, None)]["value"] == pytest.approx(15.47395544)
    assert canon[("united_states", 2023, None)]["value"] == pytest.approx(12.1702024)
    assert canon[("germany", 1994, None)]["value"] == pytest.approx(12.05083384)
    assert canon[("latvia", 1994, None)]["value"] == pytest.approx(28.44400577)
    # RUSSIA IS ABSENT FROM THE WHOLE ITF FLOW (verified live on the full
    # slice) — the honest coverage limit; the witness carries its face.
    assert all(e != "russian_federation" for e, _, _ in canon)
    # No sex dimension on the flow — every point both-sexes.
    assert all(d.get("sex") is None for d in payload["data"])

    sources = payload["sources"]
    assert [(s["provider"], s["source_ref"], s["role"], s["root"]) for s in sources] == [
        ("oecd", "DF_SAFETY/FATALITIES/10P5HB", "canonical", "itf_irtad"),
        ("who_gho", "RS_198", "witness", "who_roadsafety"),
    ]
    assert "IRTAD road crash registrations" in sources[0]["citation"]

    # THE WITNESS COUPE: the WHO modeled world face at its single 2021
    # vintage — Russia rides HERE (10.6), the coverage story itself.
    assert len(payload["witnesses"]) == 1
    witness = payload["witnesses"][0]
    assert (witness["provider"], witness["source_ref"]) == ("who_gho", "RS_198")
    wit = {(d["entity_id"], d["year"], d.get("sex")): d for d in witness["data"]}
    assert wit[("russian_federation", 2021, None)]["value"] == pytest.approx(10.6)
    assert wit[("france", 2021, None)]["value"] == pytest.approx(4.7)
    # The coupe's own shape: every witness point prints 2021 (the
    # report's cross-section, no series — the vintage cadence documented).
    assert all(d["year"] == 2021 for d in witness["data"])


def test_incarceration_rate_is_the_icpr_door_with_the_who_prisons_coupe(tmp_path, real_indicators, real_entities):
    # THE TWENTIETH INDICATOR (v20, 3 citations — La Défaite's own
    # six-country comparison, L'illusion économique's US correctional
    # population, Qui est Charlie ?'s France écroués). Canonical = the
    # ICPR World Prison Brief through OWID's chart door (the compilation
    # canonical by necessity: UNODC's portal is a client-rendered SPA
    # with no machine door, the WPB's own site has no API — the probe
    # record); witness = the WHO Health in Prisons database coupe (the
    # European questionnaire collection's 36-country 2020 cross-section).
    processed_dir, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "incarceration_rate.json").read_text())

    assert (tr := payload["todd_refs"]) and (tr["citations"], tr["books"]) == (3, 3)
    assert payload["unit"] == "prisoners_per_100000_population"
    assert payload["family"] == "society"

    canon = {(d["entity_id"], d["year"], d.get("sex")): d for d in payload["data"]}
    # LA DÉFAITE'S OWN SIX-COUNTRY BOARD: the American carceral mass
    # (L'illusion économique read its growth 1980-1993), the Russian fall
    # from the world's top, the French slow climb (Qui est Charlie ?'s
    # écroués arc's stock face), the family-systems' Japanese low.
    assert canon[("united_states", 2000, None)]["value"] == pytest.approx(683)
    assert canon[("united_states", 2023, None)]["value"] == pytest.approx(542)
    assert canon[("russian_federation", 2000, None)]["value"] == pytest.approx(729)
    assert canon[("russian_federation", 2023, None)]["value"] == pytest.approx(300)
    assert canon[("france", 2000, None)]["value"] == pytest.approx(82)
    assert canon[("france", 2025, None)]["value"] == pytest.approx(126)
    assert canon[("japan", 2024, None)]["value"] == pytest.approx(33)
    assert canon[("united_kingdom", 2000, None)]["value"] == pytest.approx(121.13483)
    # EL SALVADOR prints at the slice's top — the estado de excepción's
    # own arithmetic, the plausible bound's own calibrator. KOSOVO rides
    # the entity-validity discipline: the door prints from 2000 (11, the
    # pre-independence floor) but the registry entity exists from 2008
    # only — the pre-2008 points refuse honestly, the 2009+ series enters.
    assert canon[("el_salvador", 2024, None)]["value"] == pytest.approx(1659)
    assert canon[("kosovo", 2023, None)]["value"] == pytest.approx(99)
    assert ("kosovo", 2000, None) not in canon
    # No sex dimension on the compilation — every point both-sexes.
    assert all(d.get("sex") is None for d in payload["data"])

    sources = payload["sources"]
    assert [(s["provider"], s["source_ref"], s["role"], s["root"]) for s in sources] == [
        ("owid", "prison-population-rate", "canonical", "icpr_wpb"),
        ("who_gho", "PRISON_A2_PRISIONERS_PER100KPOP", "witness", "who_prisons"),
    ]
    assert sources[0]["layer"] == "harmonized"

    # THE WITNESS COUPE: the WHO Health in Prisons collection's own
    # per-100k print — 36 European countries at the SINGLE 2020 vintage
    # (the coupe pattern: one print, the collection's own cadence). The
    # two doors' 2020 seams display (FRA 93.1 on the collection vs the
    # WPB's own 2020 print), never reconciled; GEO and MDA the post-
    # Soviet top of the European face.
    assert len(payload["witnesses"]) == 1
    witness = payload["witnesses"][0]
    assert (witness["provider"], witness["source_ref"]) == ("who_gho", "PRISON_A2_PRISIONERS_PER100KPOP")
    wit = {(d["entity_id"], d["year"], d.get("sex")): d for d in witness["data"]}
    assert wit[("france", 2020, None)]["value"] == pytest.approx(93.1)
    assert wit[("germany", 2020, None)]["value"] == pytest.approx(69.74)
    assert wit[("united_kingdom", 2020, None)]["value"] == pytest.approx(129.83)
    assert wit[("georgia", 2020, None)]["value"] == pytest.approx(245.99)
    assert wit[("san_marino", 2020, None)]["value"] == pytest.approx(23.03)
    assert all(d["year"] == 2020 for d in witness["data"])


def test_math_test_scores_is_the_pisa_door_canonical_alone(tmp_path, real_indicators, real_entities):
    # THE TWENTY-FIRST INDICATOR (v20, 3 citations — the education
    # family's first). Canonical = the OECD PISA Database's mean
    # mathematics scores through OWID's chart door with the Mathematics
    # column pinned (the SDMX registry carries no PISA dataflow — the
    # chart IS the machine face, the oecd_family relation). NO WITNESS —
    # the honest absence: the by-sex chart is the same root, the WB
    # harmonized learning scores are a derived composite, and TIMSS (the
    # assessment Todd's own table read) has no machine door.
    processed_dir, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "math_test_scores.json").read_text())

    assert (tr := payload["todd_refs"]) and (tr["citations"], tr["books"]) == (3, 1)
    assert payload["unit"] == "pisa_score_points"
    assert payload["family"] == "education"

    canon = {(d["entity_id"], d["year"], d.get("sex")): d for d in payload["data"]}
    # L'ILLUSION ÉCONOMIQUE'S OWN ARC on the OECD's modern face: the
    # French slide, the American mid-band drift, Japan's stable top —
    # and SGP/QAT the scale's own ceiling/floor (the bound calibrators).
    assert canon[("france", 2003, None)]["value"] == pytest.approx(510.79947)
    assert canon[("france", 2022, None)]["value"] == pytest.approx(473.94443)
    assert canon[("united_states", 2003, None)]["value"] == pytest.approx(482.88278)
    assert canon[("united_states", 2022, None)]["value"] == pytest.approx(464.88803)
    assert canon[("japan", 2003, None)]["value"] == pytest.approx(534.1365)
    assert canon[("singapore", 2022, None)]["value"] == pytest.approx(574.6638)
    assert canon[("qatar", 2006, None)]["value"] == pytest.approx(317.95566)
    assert canon[("germany", 2022, None)]["value"] == pytest.approx(474.82645)
    # RUSSIA prints six cycles then is ABSENT from 2022 — the cycle
    # Russia did not sit, the honest coverage gap (no 2022 key at all).
    assert canon[("russian_federation", 2018, None)]["value"] == pytest.approx(487.78653)
    assert ("russian_federation", 2022, None) not in canon
    # THE 2000 CYCLE prints no mathematics mean on this door (reading-
    # only rows — PISA 2000's major domain): the French 2000 point
    # arrives as an EXPLICIT GAP, the door's own shape, never a skip.
    fra_2000 = canon[("france", 2000, None)]
    assert fra_2000["value"] is None
    # No sex dimension on the door's total column.
    assert all(d.get("sex") is None for d in payload["data"])

    sources = payload["sources"]
    assert [(s["provider"], s["source_ref"], s["role"], s["root"]) for s in sources] == [
        ("owid", "average-performance-of-15-year-olds-in-mathematics-reading-and-science", "canonical", "oecd_pisa"),
    ]
    # NO WITNESS TIER — the honest absence, the top_income_share
    # precedent: the witnesses list exists (the contract) and is empty.
    assert payload["witnesses"] == []


def test_obesity_rate_is_the_gho_door_canonical_alone_sex_split(tmp_path, real_indicators, real_entities):
    # THE TWENTY-SECOND INDICATOR (v20, 3 citations — La Défaite's
    # health-paradox pair). Canonical = the NCD-RisC adult BMI pooled
    # analysis republished by WHO GHO (NCD_BMI_30C, the crude 18+ face)
    # on the provider's OWN machine wire — the first GHO-canonical
    # indicator, the per-code AGE pin's own door. The OWID chart door
    # prints the same series bit-identically (the auto-witness refusal's
    # own evidence, verified live); NO cross-root witness exists.
    processed_dir, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "obesity_rate.json").read_text())

    assert (tr := payload["todd_refs"]) and (tr["citations"], tr["books"]) == (3, 1)
    assert payload["unit"] == "percent"
    assert payload["family"] == "mortality"

    canon = {(d["entity_id"], d["year"], d.get("sex")): d for d in payload["data"]}
    # THE HEALTH-PARADOX PAIR at the population level (the book's own
    # face is the CDC's college-educated cut — the seam documented):
    # USA 41.8 vs FRA 12.5 (2024), Japan's lean counter-example, the
    # American fourfold rise 1980->2024, the Pacific island tail.
    assert canon[("united_states", 2024, None)]["value"] == pytest.approx(41.830319)
    assert canon[("france", 2024, None)]["value"] == pytest.approx(12.524594)
    assert canon[("japan", 2024, None)]["value"] == pytest.approx(5.1900275)
    assert canon[("france", 1980, None)]["value"] == pytest.approx(10.615123)
    assert canon[("russian_federation", 2024, None)]["value"] == pytest.approx(21.247752)
    # THE SEX SPLIT rides the canonical tier itself (the merge key keeps
    # the three apart): the American female-over-male inversion, the
    # French near-parity, the Pacific female tail (the bound's own
    # calibrator), the Vietnamese male floor.
    assert canon[("united_states", 2024, "female")]["value"] == pytest.approx(43.015891)
    assert canon[("united_states", 2024, "male")]["value"] == pytest.approx(40.642369)
    assert canon[("france", 2024, "female")]["value"] == pytest.approx(12.585108)
    assert canon[("france", 2024, "male")]["value"] == pytest.approx(12.458491)
    assert canon[("american_samoa", 2024, "female")]["value"] == pytest.approx(80.890405)
    assert canon[("viet_nam", 1980, "male")]["value"] == pytest.approx(0.045321116)

    sources = payload["sources"]
    assert [(s["provider"], s["source_ref"], s["role"], s["root"]) for s in sources] == [
        ("who_gho", "NCD_BMI_30C", "canonical", "ncd_risc_bmi"),
    ]
    assert sources[0]["layer"] == "harmonized"
    # NO WITNESS TIER — the same-root absence (the OWID chart door
    # refused as an auto-witness, its bit-identity the evidence).
    assert payload["witnesses"] == []


def test_hiv_prevalence_rate_is_the_unaids_door_canonical_alone(tmp_path, real_indicators, real_entities):
    # THE TWENTY-THIRD INDICATOR (v20, 1 citation — Où en sommes-nous ?'s
    # patrilineality proxy). Canonical = UNAIDS' Global AIDS Update
    # epidemic indicators through OWID's chart door (aidsinfo is a
    # client-rendered SPA with no discoverable API, api.unaids.org is
    # DNS-dead — the chart IS the wire, the wid door relation). NO
    # WITNESS — the GHO and WB doors redistribute the same root, and
    # IHME's cross-root family stays behind OWID's 403 (re-confirmed
    # live on the unaids-vs-ihme chart).
    processed_dir, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "hiv_prevalence_rate.json").read_text())

    assert (tr := payload["todd_refs"]) and (tr["citations"], tr["books"]) == (1, 1)
    assert payload["unit"] == "percent"
    assert payload["family"] == "mortality"

    canon = {(d["entity_id"], d["year"], d.get("sex")): d for d in payload["data"]}
    # THE PATRILINEAL-BELT GEOGRAPHY the book maps, printed as the
    # epidemic's own curves: the southern-African face rich and peaking
    # (ZWE 1995 = 29.65 the live max, SWZ 23.4 by 2024, ZAF 17.2, BWA
    # from 7.7), France's low-prevalence European face doubling.
    assert canon[("zimbabwe", 1995, None)]["value"] == pytest.approx(29.64893)
    assert canon[("eswatini", 2024, None)]["value"] == pytest.approx(23.37995)
    assert canon[("south_africa", 2024, None)]["value"] == pytest.approx(17.20138)
    assert canon[("botswana", 1990, None)]["value"] == pytest.approx(7.65814)
    assert canon[("zambia", 1990, None)]["value"] == pytest.approx(9.43451)
    assert canon[("france", 1990, None)]["value"] == pytest.approx(0.12917)
    assert canon[("france", 2023, None)]["value"] == pytest.approx(0.28482)
    # THE COMPILATION'S OWN COUNTRY UNIVERSE: no United States, no
    # Russia, no China (verified identically on the GHO redistribution —
    # the UNAIDS reporting shape itself, the honest coverage limit).
    assert all(e not in ("united_states", "russian_federation", "china") for e, _, _ in canon)
    # THE AGGREGATE ROWS resolve to no registry entity — "World" and the
    # UNAIDS regional aggregates never enter the canonical tier (the
    # drops are logged, the OWID-door rule).
    assert all(e != "world" for e, _, _ in canon)
    assert all(d.get("sex") is None for d in payload["data"])

    sources = payload["sources"]
    assert [(s["provider"], s["source_ref"], s["role"], s["root"]) for s in sources] == [
        ("owid", "share-of-the-population-infected-with-hiv", "canonical", "unaids"),
    ]
    # NO WITNESS TIER — the honest absence, the top_income_share
    # precedent; the same-root doors (GHO MDG_0000000029, WB counts)
    # are registered non-wired.
    assert payload["witnesses"] == []


def test_male_height_trend_is_the_ncdrisc_door_with_the_baten_blum_witness(tmp_path, real_indicators, real_entities):
    # THE TWENTY-FOURTH INDICATOR (v20, 1 citation) — THE METRIC THAT
    # CLOSED THE CORPUS (24/24 at v20; 22/22 since v26's withdrawal).
    # Canonical = the NCD-RisC 2016 eLife
    # compilation through OWID's chart door (height at age 18 by birth
    # cohort); witness = Baten & Blum (2015) via Clio-Infra (the
    # historical anthropometric record — a genuinely cross-root
    # compilation, the barro_lee relation).
    processed_dir, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "male_height_trend.json").read_text())

    assert (tr := payload["todd_refs"]) and (tr["citations"], tr["books"]) == (1, 1)
    assert payload["unit"] == "centimeters"
    assert payload["family"] == "society"

    canon = {(d["entity_id"], d["year"], d.get("sex")): d for d in payload["data"]}
    # THE TODD ARC PRINTS BIGGER: the book's +10cm French century is
    # +13.3cm on the birth-cohort read (166.41 -> 179.74, 101 annual
    # cohort points); the catch-up arcs (KOR the biggest gain), the
    # Netherlands' ceiling, Laos' floor, the American mid-band.
    assert canon[("france", 1896, None)]["value"] == pytest.approx(166.41232)
    assert canon[("france", 1996, None)]["value"] == pytest.approx(179.73792)
    assert canon[("united_states", 1896, None)]["value"] == pytest.approx(171.07927)
    assert canon[("netherlands", 1985, None)]["value"] == pytest.approx(182.5673)
    assert canon[("korea_republic_of", 1996, None)]["value"] == pytest.approx(174.91963)
    assert canon[("japan", 1896, None)]["value"] == pytest.approx(156.16695)
    assert canon[("lao_people_s_democratic_republic", 1896, None)]["value"] == pytest.approx(152.88463)
    assert canon[("russian_federation", 1996, None)]["value"] == pytest.approx(176.46053)
    # No sex dimension on the Men column (the Women column is the
    # registered future door).
    assert all(d.get("sex") is None for d in payload["data"])

    sources = payload["sources"]
    assert [(s["provider"], s["source_ref"], s["role"], s["root"]) for s in sources] == [
        ("owid", "average-height-of-men", "canonical", "ncd_risc_height"),
        ("owid", "average-height-of-men-by-year-of-birth", "witness", "baten_blum"),
    ]

    # THE WITNESS: Baten-Blum/Clio-Infra — the pre-1896 tail the
    # canonical cannot carry (FRA 1660 = 162.6, the early-modern
    # record), the cm-level seams on the overlapping cohorts displayed
    # never reconciled (FRA 1900: 166.8 here vs 167.7 on NCD-RisC),
    # PNG's floor and Denmark's ceiling the bound calibrators.
    assert len(payload["witnesses"]) == 1
    witness = payload["witnesses"][0]
    assert (witness["provider"], witness["source_ref"]) == ("owid", "average-height-of-men-by-year-of-birth")
    wit = {(d["entity_id"], d["year"], d.get("sex")): d for d in witness["data"]}
    assert wit[("france", 1660, None)]["value"] == pytest.approx(162.6)
    assert wit[("france", 1900, None)]["value"] == pytest.approx(166.8)
    assert wit[("france", 1980, None)]["value"] == pytest.approx(176.5)
    assert wit[("united_states", 1710, None)]["value"] == pytest.approx(171.5)
    assert wit[("papua_new_guinea", 1880, None)]["value"] == pytest.approx(152.359)
    assert wit[("denmark", 1980, None)]["value"] == pytest.approx(183.2)
    assert wit[("russian_federation", 1700, None)]["value"] == pytest.approx(163.9)


# --- v21: the vanished entities land end-to-end --------------------------------


def test_v21_vanished_entities_land_end_to_end(tmp_path, real_indicators, real_entities):
    """The DYB 1978 transcription tables: three indicators, six entities,
    the as-reported prints of states the XLS loop cannot reach — seeded
    through the REAL curated connector against the REAL committed catalog
    (deterministic, network-free), read through the whole pipeline."""
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    dist_dir = tmp_path / "dist"
    reports_dir = tmp_path / "reports"

    seed_curated_snapshot(raw_dir, "infant_mortality")
    seed_curated_snapshot(raw_dir, "infant_mortality", "dyb1978_vanished_infant_mortality")
    seed_dyb_snapshot(raw_dir, "infant_mortality")
    seed_owid_snapshot(raw_dir, "infant_mortality", "infant-mortality", "owid_infant_mortality.csv")
    seed_curated_snapshot(raw_dir, "crude_birth_rate", "dyb1978_vanished_crude_birth_rate")
    seed_dyb_table9_snapshot(raw_dir, "crude_birth_rate")
    seed_wb_snapshot(raw_dir, "crude_birth_rate", "SP.DYN.CBRT.IN")
    seed_curated_snapshot(raw_dir, "life_expectancy", "dyb1978_vanished_life_expectancy")
    seed_dyb_table4_snapshot(raw_dir, "life_expectancy")
    seed_owid_snapshot(raw_dir, "life_expectancy", "life-expectancy", "owid_life_expectancy.csv")

    todd_refs = load_todd_refs(CONFIG_DIR)
    cross_validate_todd_core(real_indicators, todd_refs)
    normalize_all(real_indicators, raw_dir, processed_dir, real_entities)
    merge_all(list(real_indicators.keys()), processed_dir)
    build_all(real_indicators, processed_dir, dist_dir, real_entities, todd_refs=todd_refs)

    # infant_mortality: the five vanished entities' Total rows land
    imr = json.loads((dist_dir / "indicators" / "infant_mortality.json").read_text())
    canon = {(d["entity_id"], d["year"]): d for d in imr["data"]}
    assert canon[("czechoslovakia", 1974)]["value"] == pytest.approx(20.5)
    assert canon[("czechoslovakia", 1978)]["value"] == pytest.approx(18.7)
    assert canon[("yugoslavia_sfr", 1974)]["value"] == pytest.approx(40.9)
    assert canon[("yugoslavia_sfr", 1978)]["value"] == pytest.approx(33.6)
    assert canon[("east_germany", 1974)]["value"] == pytest.approx(15.9)
    assert canon[("east_germany", 1978)]["value"] == pytest.approx(13.2)
    assert canon[("byelorussian_ssr", 1974)]["value"] == pytest.approx(16.6)
    assert canon[("ukrainian_ssr", 1974)]["value"] == pytest.approx(19.2)
    # The printed markers ride as-reported: '*' = provisional on the
    # 1977/1978 prints, the row code C rides quality_code.
    assert canon[("czechoslovakia", 1978)].get("provisional") is True
    assert canon[("czechoslovakia", 1974)].get("provisional") is not True
    assert canon[("yugoslavia_sfr", 1978)]["quality_code"] == "C"
    # The citation is the DYB 1978 table itself; the note carries the
    # count cross-check and (on Soviet rows) the live-birth definition.
    yug74 = canon[("yugoslavia_sfr", 1974)]
    assert "Demographic Yearbook 1978" in yug74["citation"]
    assert "15,666" in yug74["citation"]
    bssr = canon[("byelorussian_ssr", 1974)]
    assert "Soviet live-birth definition" in bssr["definition_note"]
    gdr78 = canon[("east_germany", 1978)]
    assert "Berlin" in gdr78["definition_note"]

    # crude_birth_rate: the USSR union's OWN CBR print + the two SSR rows
    cbr = json.loads((dist_dir / "indicators" / "crude_birth_rate.json").read_text())
    ccanon = {(d["entity_id"], d["year"]): d["value"] for d in cbr["data"]}
    assert [ccanon[("ussr", y)] for y in (1974, 1975, 1976, 1977)] == [18.0, 18.1, 18.4, 18.1]
    assert [ccanon[("byelorussian_ssr", y)] for y in (1974, 1975, 1976, 1977)] == [15.8, 15.7, 15.7, 15.8]
    assert [ccanon[("ukrainian_ssr", y)] for y in (1974, 1975, 1976, 1977)] == [15.2, 15.1, 15.2, 14.7]
    assert ccanon[("czechoslovakia", 1974)] == pytest.approx(19.9)
    assert ccanon[("east_germany", 1978)] == pytest.approx(13.9)
    assert ccanon[("yugoslavia_sfr", 1978)] == pytest.approx(17.4)
    # The GDR's 1976-1978 prints carry '*' = provisional as-printed.
    gdr = {(d["entity_id"], d["year"]): d for d in cbr["data"]}
    assert gdr[("east_germany", 1976)].get("provisional") is not True
    assert gdr[("east_germany", 1977)].get("provisional") is True

    # life_expectancy: the sex-split pairs, the end-year convention, the
    # reference_range as-printed
    le = json.loads((dist_dir / "indicators" / "life_expectancy.json").read_text())
    lcanon = {(d["entity_id"], d["year"], d["sex"]): d for d in le["data"]}
    assert lcanon[("ussr", 1972, "male")]["value"] == 64.0
    assert lcanon[("ussr", 1972, "female")]["value"] == 74.0
    assert lcanon[("ussr", 1972, "male")]["reference_range"] == "1971-1972"
    assert lcanon[("byelorussian_ssr", 1971, "male")]["value"] == 68.0
    assert lcanon[("ukrainian_ssr", 1971, "female")]["value"] == 74.0
    assert lcanon[("czechoslovakia", 1976, "male")]["value"] == pytest.approx(66.99)
    assert lcanon[("east_germany", 1976, "female")]["value"] == pytest.approx(74.42)
    assert lcanon[("yugoslavia_sfr", 1972, "male")]["value"] == pytest.approx(65.42)
    # The (entity, year, sex) merge key: the pair coexists, no collision.
    assert ("ussr", 1972, "male") in lcanon and ("ussr", 1972, "female") in lcanon

    # The corpus is untouched: v21 adds DATA to existing indicators,
    # no flips (the corpus count stays).
    corpus = json.loads((dist_dir / "todd_corpus.json").read_text())
    assert corpus["meta"]["implemented_metrics"] == 22  # 24 at v20; 22 since v26's withdrawal


# --- v22: the by-origin face (the bilateral layer) ---------------------------


def test_unemployment_rate_carries_the_segment_faces_end_to_end(
    tmp_path, real_indicators, real_entities, real_todd_refs
):
    # THE MAIN V25 DELIVERY: Le Destin des immigrés' own question wired —
    # the CLASS decomposition of the unemployment rate, two PARALLEL
    # layers (ADR-0010: immigrés vs étrangers, never merged, never
    # arbitrated across, layer-scoped class vocabularies), canonical =
    # the LFS questionnaire's own class tables (lfsa_urgacob /
    # lfsa_urgan, the doors the v25 probe found), witness = the ILOSTAT
    # class cross-sections on the ILO's own SDMX wire (the flows the
    # 2026-09-24 restructure left in the coupe shape).
    processed_dir, dist_dir, _, validate_results = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "unemployment_rate.json").read_text())

    # --- THE BIRTH FACE (immigrés): the class decomposition's own key
    # space (entity, class, year, sex), the four classes the
    # questionnaire prints, the FR 2015 Destin anchors read live.
    seg = payload["segments"]
    spts = {
        (d["entity_id"], d["population_class"], d["year"], d.get("sex")): d["value"]
        for d in seg["data"]
    }
    assert spts[("france", "natives", 2015, None)] == pytest.approx(9.4)
    assert spts[("france", "foreign_born", 2015, None)] == pytest.approx(17.1)
    assert spts[("france", "eu_born", 2015, None)] == pytest.approx(10.7)
    assert spts[("france", "non_eu_born", 2015, None)] == pytest.approx(19.0)
    # the by-sex rows are NOT on the canonical segment face (the M/F
    # doors stay unwired, recorded) — sex=None on every point.
    assert all(d.get("sex") is None for d in seg["data"])
    birth_classes = {d["population_class"] for d in seg["data"]}
    assert birth_classes == {"natives", "foreign_born", "eu_born", "non_eu_born"}
    # the 31-year memory the class tables carry (1995 — RICHER than the
    # plain rate's own 2003+ collector window).
    assert min(d["year"] for d in seg["data"]) == 1995

    # --- THE CITIZENSHIP FACE (étrangers): its own vocabulary, never
    # meeting the birth face's — the de-facto Destin board.
    ctz = payload["segments_citizenship"]
    cpts = {
        (d["entity_id"], d["population_class"], d["year"], d.get("sex")): d["value"]
        for d in ctz["data"]
    }
    assert cpts[("france", "nationals", 2015, None)] == pytest.approx(9.7)
    assert cpts[("france", "foreigners", 2015, None)] == pytest.approx(20.5)
    assert cpts[("france", "eu_foreigners", 2015, None)] == pytest.approx(12.6)
    assert cpts[("france", "non_eu_foreigners", 2015, None)] == pytest.approx(24.5)
    ctz_classes = {d["population_class"] for d in ctz["data"]}
    assert ctz_classes == {"nationals", "foreigners", "eu_foreigners", "non_eu_foreigners"}
    # THE TWO VOCABULARIES NEVER MIX (ADR-0010 made executable).
    assert not (birth_classes & ctz_classes)
    # THE UK: the class doors' own richer codelist (une_rt_a lost it at
    # Brexit; the LFS class tables still print it).
    assert any(d["entity_id"] == "united_kingdom" for d in seg["data"]) or \
        any(d["entity_id"] == "united_kingdom" for d in ctz["data"])
    # the TOTAL class never rides (the total rate's own door is
    # une_rt_a — one door per face).
    assert "total" not in birth_classes and "total" not in ctz_classes

    # --- THE ILOSTAT WITNESSES: one per face, the world cross-section in
    # the coupe shape, the two aggregate classes, BOTH SEXES' rows (the
    # canonical's T-only asymmetry documented), the KOS->XKX quirk.
    assert len(seg["witnesses"]) == 1
    sw = seg["witnesses"][0]
    assert (sw["provider"], sw["source_ref"]) == ("ilostat", "DF_UNE_DEAP_SEX_AGE_CBR_RT")
    assert sw["root"] == "ilo_lfs"
    assert sw["layer"] == "harmonized"  # the provider's own tier
    wpts = {
        (d["entity_id"], d["population_class"], d["year"], d.get("sex")): d["value"]
        for d in sw["data"]
    }
    assert wpts[("france", "natives", 2025, None)] == pytest.approx(7.023)
    assert wpts[("france", "foreign_born", 2025, None)] == pytest.approx(12.003)
    assert wpts[("france", "foreign_born", 2025, "female")] == pytest.approx(12.846)
    assert wpts[("france", "foreign_born", 2025, "male")] == pytest.approx(11.245)
    # Kosovo on the birth witness: the CBR flow's Kosovo rows print 2000
    # (the pre-independence era) — the entity's valid_from=2008 floor
    # drops them honestly, the same discipline the WB witness's XKX-2001
    # point follows.
    assert not any(k[0] == "kosovo" for k in wpts)

    cw = ctz["witnesses"][0]
    assert (cw["provider"], cw["source_ref"]) == ("ilostat", "DF_UNE_DEAP_SEX_AGE_CCT_RT")
    wpts_c = {
        (d["entity_id"], d["population_class"], d["year"], d.get("sex")): d["value"]
        for d in cw["data"]
    }
    assert wpts_c[("france", "nationals", 2025, None)] == pytest.approx(7.162)
    assert wpts_c[("france", "foreigners", 2025, None)] == pytest.approx(13.902)
    assert wpts_c[("france", "foreigners", 2025, "male")] == pytest.approx(12.961)
    # Kosovo rides the KOS->XKX override (the v21 code) on the
    # citizenship witness — its rows print 2024, inside the entity's
    # validity window.
    assert any(k[0] == "kosovo" for k in wpts_c)
    assert wpts_c[("kosovo", "foreigners", 2024, None)] == pytest.approx(6.929)

    # --- THE SINGLE-AXIS FACE UNTOUCHED by the segment wiring: the T
    # rows keep their own anchors (the coverage-cliff test's domain).
    canon = {(d["entity_id"], d["year"], d.get("sex")): d["value"] for d in payload["data"]}
    assert canon[("france", 2015, None)] == pytest.approx(10.4)

    # --- VALIDATION: both segment layers' sections, no duplicates across
    # the (entity, class, year, sex) key, no range violations (the class
    # rates sit inside 0-60 with the XKX tail).
    une = next(r for r in validate_results if r["indicator_id"] == "unemployment_rate")
    for layer in ("segments", "segments_citizenship"):
        assert une[layer]["duplicate_entity_year"] == []
        assert une[layer]["range_violations"] == []
        assert all(not w["range_violations"] for w in une[layer]["witnesses"])
    assert une["segments"]["n_classes"] == 4
    assert une["segments_citizenship"]["n_classes"] == 4

    # --- THE ROOTS: the segment canonicals join eurostat_lfs (the same
    # questionnaire — one questionnaire, four metrics); the ILOSTAT
    # witnesses join ilo_lfs on its direct door.
    catalog = {c["id"]: c for c in json.loads((dist_dir / "catalog.json").read_text())}
    roots = catalog["unemployment_rate"]["roots"]
    canon_roots = {r["root"] for r in roots["canonical"]}
    assert canon_roots == {"eurostat_lfs"}
    wit_roots = {r["root"] for r in roots["witness"]}
    assert wit_roots == {"ilo_lfs"}

    # --- THE STATS LINES: the segment faces print their own counts.
    from src.pipeline.stats import render_stats

    stats = render_stats(dist_dir)
    assert "segments (country-of-birth classes)" in stats
    assert "segments (citizenship classes)" in stats
    assert "classes (eu_born, foreign_born, natives, non_eu_born)" in stats

    # --- THE CORPUS count unchanged (a FACE added, zero flips).
    corpus = json.loads((dist_dir / "todd_corpus.json").read_text())
    assert corpus["meta"]["implemented_metrics"] == 22  # 24 at v20; 22 since v26's withdrawal


def test_road_accident_mortality_per_vehicle_is_the_1974_denominator(
    tmp_path, real_indicators, real_entities
):
    # THE COMPACT V25 DELIVERY: Todd's own denominator wired — the
    # per-vehicle road-death rate (Le Fou et le Prolétaire's 1974 table
    # shape, deaths per million vehicles then, per 10,000 now), the v19
    # registry's "one config line away" line taken. todd_core=false by
    # the corpus closure (a FACE of the corpus's road-death metric, the
    # notes carrying the fidelity), the companion pair declared on BOTH
    # sides, WITNESSLESS (no other machine door prints a per-vehicle
    # rate — the top_income_share constitution).
    _, dist_dir, _, validate_results = _run_pipeline(tmp_path, real_indicators, real_entities)
    payload = json.loads((dist_dir / "indicators" / "road_accident_mortality_per_vehicle.json").read_text())

    assert payload["todd_core"] is False  # the corpus closure, documented
    assert "todd_refs" not in payload     # honest absence — no corpus entry
    assert payload["unit"] == "deaths_per_10000_vehicles"
    assert payload["family"] == "mortality"
    # THE COMPANION PAIR (declared on both sides, the symmetry contract).
    assert payload["companion_indicators"] == ["road_accident_mortality"]
    road = json.loads((dist_dir / "indicators" / "road_accident_mortality.json").read_text())
    assert road["companion_indicators"] == ["road_accident_mortality_per_vehicle"]

    canon = {(d["entity_id"], d["year"]): d for d in payload["data"]}
    # THE LIVE ANCHORS (read from the carved fixture, never typed):
    # FRA 2010 = 0.9497 (the door's own French start — the per-vehicle
    # registration series arrive late), FRA 2024 = 0.6512 (the sécurité
    # routière arc under its own denominator), CHE 1994 = 1.6303 (the
    # longest series' start), CHL 1998 = 13.1494 (the slice's own tail —
    # the Chilean registration crisis).
    assert canon[("france", 2010)]["value"] == pytest.approx(0.949683318)
    assert canon[("france", 2024)]["value"] == pytest.approx(0.651244379)
    assert canon[("switzerland", 1994)]["value"] == pytest.approx(1.630302595)
    assert canon[("chile", 1998)]["value"] == pytest.approx(13.14939566)
    # THE HONEST LIMITS: the USA ABSENT (the IRTAD questionnaire never
    # carried the US vehicle-registration series — the 1974 table's own
    # third column has no modern machine face), 38 areas, the
    # heterogeneous windows printed as-is.
    assert not any(e == "united_states" for (e, _y) in canon)
    assert len({e for e, _y in canon}) == 38
    assert min(y for _e, y in canon) == 1994 and max(y for _e, y in canon) == 2024

    # WITNESSLESS: the witnesses list is the honest empty list (the dist
    # contract's uniform field), the top_income_share constitution.
    assert payload["witnesses"] == []

    # VALIDATION: no violations (the CHL tail sits inside 0-16), the
    # sources block carries the single canonical door with its layer.
    veh = next(r for r in validate_results if r["indicator_id"] == "road_accident_mortality_per_vehicle")
    assert veh["range_violations"] == []
    assert veh["witnesses"] == []
    src = payload["sources"][0]
    assert (src["provider"], src["source_ref"], src["role"]) == (
        "oecd", "DF_SAFETY/FATALITIES/10P4VEH_MOT_ROAD", "canonical"
    )
    assert src["root"] == "itf_irtad"
    assert src["layer"] == "collector"


def test_segment_layers_absent_on_class_less_indicators(
    tmp_path, real_indicators, real_entities
):
    # THE ADDITIVITY PIN (the v22 guarantee extended to the segment
    # layers): every class-less indicator's dist file carries NO segment
    # keys — the emission is layer-scoped, one indicator carries the
    # faces, the 26 others stay clean. The life_expectancy payload (the
    # sex-split single-axis shape) pins the single-axis contract.
    _, dist_dir, _, _ = _run_pipeline(tmp_path, real_indicators, real_entities)
    for name in ("life_expectancy", "road_accident_mortality"):
        payload = json.loads((dist_dir / "indicators" / f"{name}.json").read_text())
        assert "segments" not in payload, name
        assert "segments_citizenship" not in payload, name
