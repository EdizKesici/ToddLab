"""Schema for an indicator — the identity card of each metric.

One YAML file in config/indicators/ = one instance of this model. The
pipeline refuses to start if a file doesn't validate against this schema:
better an explicit build failure than a silently incomplete or inconsistent
output JSON.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class Family(str, Enum):
    mortality = "mortality"
    anthropometry_health = "anthropometry_health"
    society = "society"
    # v15: the corpus's own vocabulary carries a 'markers' family (Todd's
    # dated institutional events — same-sex marriage legalization,
    # universal suffrage introduction: one year per country, a step the
    # board reads as a threshold, not a curve). The enum narrows when a
    # metric becomes an indicator, per todd_refs.py's schema note — these
    # two metrics are that family's first indicators.
    markers = "markers"
    # v17: the corpus's 'economy' family (63 citations across its 5
    # metrics — unemployment_rate 20, the industrial/employment shares,
    # the GDP-adjacent reads). unemployment_rate is that family's first
    # indicator; the same one-metric-at-a-time narrowing as markers.
    economy = "economy"
    # v18: the corpus's 'demography' family (the population-stock reads —
    # immigration_stock 11 citations, Le Destin des immigrés' boards:
    # the metric that IS the demographic-structure question). The same
    # one-metric-at-a-time narrowing: immigration_stock is this family's
    # first indicator (the corpus's birth/fertility metrics ride the
    # society family — 'demography' in the corpus vocabulary names the
    # stock/structure reads, not the vital rates).
    demography = "demography"
    # v20: the corpus's 'education' family (the assessed-learning reads —
    # math_test_scores 3 citations, L'illusion économique's TIMSS table
    # read through the OECD's own comparative volume, "OECD source" in
    # the corpus's own words). The same one-metric-at-a-time narrowing:
    # math_test_scores is this family's first indicator; the attainment
    # shares (tertiary/secondary) ride the society family where the
    # corpus itself files them.
    education = "education"


class Reliability(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Provider(str, Enum):
    owid = "owid"
    worldbank = "worldbank"
    who_gho = "who_gho"
    un_dyb = "un_dyb"
    curated = "curated"
    oecd = "oecd"
    eurostat = "eurostat"


# Root genealogy (v11, P5 — the-measurement-problem.md section 5.1): the
# ULTIMATE ORIGIN a source redistributes or republishes, as a closed
# vocabulary. Providers are doors; roots are where the numbers were made.
# The founding case: on infant mortality, OWID, the World Bank and GHO are
# three doors carrying ONE root (UN IGME) — "cross-confirming them against
# each other is an illusion of independent verification". The `root` field
# makes that claim executable: the catalog computes how many independent
# roots an indicator has and which providers are merely re-publishing the
# same one. Adding a root = a deliberate, reviewable registry edit (never
# an ad-hoc string in a config).
ROOT_LABELS: dict[str, str] = {
    "un_igme": "UN Inter-agency Group for Child Mortality Estimation (IGME)",
    "un_wpp": "UN Population Division, World Population Prospects (WPP)",
    "un_mmeig": "UN Maternal Mortality Estimation Inter-agency Group (MMEIG)",
    "who_mdb": "WHO Mortality Database (civil registration, as submitted by member states)",
    "unsd_dyb": "UN Statistics Division, Demographic Yearbook (questionnaire collector)",
    "unodc": "UN Office on Drugs and Crime (UNODC)",
    # v13 (suicide_rate witness): the WHO Global Health Estimates — the
    # modeled cause-of-death series, DISTINCT from who_mdb (the as-submitted
    # registrations the OECD door redistributes). The distinction is the
    # indicator's whole story: GHE re-distributes ill-defined causes over
    # the suicides the collectors printed (Russia 2000 male: 69.8 as-
    # reported via the OECD door vs 95.2 modeled, both verified live
    # 2026-09-19) — the root field is what keeps that divergence from
    # reading like a contradiction.
    "who_ghe": "WHO Global Health Estimates (GHE) — modeled cause-of-death estimates",
    "owid_longrun_composite": (
        "OWID long-run compilation (Riley/HMD historical reconstructions + UN WPP modern estimates)"
    ),
    "soviet_official": (
        "Official Soviet statistical series (TsSU yearbooks; Davis & Feshbach 1980 compilation)"
    ),
    # v14 (birth_rate_fertility canonical): Eurostat's demographic
    # collection — national official fertility series (the TFR each
    # statistical office computes and publishes), collected by Eurostat
    # via its own questionnaire, the same collector judgment as unsd_dyb
    # for content. THE REASON THIS ROOT EXISTS: the Todd corpus's #1
    # metric is TFR (111 citations, 16/16 books) and NO other living
    # collector wire prints it — the UN DYB publishes CBR (Table 9) and
    # age-specific rates (Table 10) but no TFR column (verified on the
    # 2024 file, 2026-09-19), and the OECD SDMX registry carries no
    # national fertility dataflow (DF_FERTILITY is TL2/TL3 regional,
    # verified live). Without this door the corpus's #1 would have had a
    # harmonized (WPP) canonical — a constitution break; with it, the
    # collector tier stands and the WPP doors ride as witnesses.
    "eurostat_demo": (
        "Eurostat demographic statistics (demo_find — national official fertility series collected by Eurostat)"
    ),
    # v15 (the markers): the dated national legislation the curated
    # marker tables carry — statutes, constitutional rulings, referendums,
    # each row's own citation being the primary source. A ROOT distinct
    # from every collector (the law is not collected, it is enacted): the
    # genealogy field's way of saying the marker tier has no upstream
    # redistributor to disclose — the citation IS the origin, which is
    # also why no witness can ever cross-check it (there is nothing
    # upstream to witness).
    "national_legislation": (
        "National legislation and constitutional rulings (the enacted law itself, cited per point)"
    ),
    # v16 (illegitimate_births witness): the OECD Family Database — the
    # OECD-compiled share of births outside marriage (SF2.4), reached
    # through OWID's chart door (the Family Database itself carries no
    # SDMX wire — the v14 registry finding). An OECD-COMPILED product:
    # the OECD assembles and standardizes national series, which makes
    # it a harmonized-family witness (the same relation WPP/GHE hold to
    # their collectors), NOT the as-submitted collector tier. The root
    # label is what lets the vintage divergence (OECD 2021 vintage vs
    # Eurostat's fresher prints) read as two doors, never a
    # contradiction.
    "oecd_family": (
        "OECD Family Database (SF family indicators, OECD-compiled; via OWID's chart door)"
    ),
    # v17 (consanguineous_marriage_rate canonical): the consanguinity-
    # studies literature — the national surveys, dispensation registries
    # and DHS reports the curated table carries, each row's own citation
    # being the primary source, vectored by Bittles' consang.net
    # compilation. Like national_legislation, a root with NO upstream
    # redistributor to disclose: no collector or harmonized door prints
    # the metric anywhere (probed live 2026-09-20: GHO 0 hit, WDI
    # 0/25000, OWID 404 — the gate finding), so the study IS the origin
    # and no witness can ever cross-check it (the same constitution as
    # the markers; the probe record lives in config/sources.yaml).
    "consanguinity_studies": (
        "The consanguinity-studies literature (national surveys and dispensation registries; "
        "Bittles' consang.net compilation + DHS final reports, cited per point)"
    ),
    # v17 (unemployment_rate canonical): Eurostat's labour-force
    # collection — the national official unemployment rates (each
    # statistical office's own LFS print, collected by Eurostat via its
    # questionnaire, 1-decimal as published), dataset une_rt_a pinned
    # age=Y15-74/unit=PC_ACT/sex=T. Distinct from eurostat_demo (the
    # demography collection): same collector judgment, different
    # questionnaire. The witness face is the ILO-processed LFS family
    # (ilo_lfs below) — on the co-covered core the two doors print the
    # same rates to rounding (FR 2015: Eurostat 10.4 vs WB/ILO 10.354,
    # verified live 2026-09-20), the same relation who_mdb/who_ghe hold.
    "eurostat_lfs": (
        "Eurostat labour-force statistics (une_rt_a — national official unemployment rates collected by Eurostat)"
    ),
    # v17 (unemployment_rate witness): the ILOSTAT LFS database —
    # national labour-force surveys RE-PROCESSED by the ILO (microdata
    # harmonization, "Repository: ILO-STATISTICS - Micro data processing",
    # LFS-ADJ adjusted series for Germany — the v17 probe record),
    # redistributed by World Bank WDI as SL.UEM.TOTL.NE.ZS "national
    # estimate" (byte-identical to the ILOSTAT DEAP plain rate on the
    # co-covered core, verified live). A harmonized-family witness for
    # the Eurostat collector: same underlying national surveys, one
    # harmonization step apart — the root pair that keeps the FR 2024
    # 7.436-vs-7.4 rounding seam and the DE 2005 11.193-vs-ABSENT
    # coverage seam reading as two doors, never a contradiction.
    "ilo_lfs": (
        "ILOSTAT LFS database (ILO-processed national labour-force surveys; redistributed by World Bank WDI as national estimate)"
    ),
    # v18 (industrial/agricultural employment canonical): Eurostat's
    # national-accounts collection — employment by industry AS EACH
    # COUNTRY PRINTS IT IN ITS OWN NATIONAL ACCOUNTS (dataset
    # nama_10_a10_e, unit PC_TOT_PER: the share of total employment
    # printed DIRECTLY by the collector — the v18 probe finding that
    # dissolved the composite-derived-layer question the backlog's head
    # had waited on since v15: the v15/v16 record "no collector prints
    # the %" was true of ILOSTAT/OECD/WB but the national-accounts door
    # had never been probed). Distinct from eurostat_demo (demography)
    # and eurostat_lfs (the labour-force survey): same collector
    # judgment — the national office's own print — different
    # questionnaire, the accounts compilation. THE DEFINITIONAL SEAM the
    # root pair displays is COMPOUND: the canonical prints the door's
    # own aggregate B-E "Industry (except construction)" on the
    # accounts' domestic employment concept, while the ILOEST witness
    # (ilo_modelled) prints industry INCLUDING construction on a
    # labor-force-modeled employment base (FR 2015: 10.8 vs 20.376,
    # verified live — the construction coverage alone does not close
    # the gap) — two doors, never a contradiction; Todd's own boards'
    # broader "industry" (Le Destin des immigrés:
    # mines+manufacturing+construction+transport) is documented
    # per-indicator.
    "eurostat_na": (
        "Eurostat national accounts (nama_10_a10_e — employment by industry as each country prints it, shares at PC_TOT_PER)"
    ),
    # v18 (industrial/agricultural employment witness): the ILO modelled
    # estimates — ILOSTAT's 2EMP family ("Estimaciones modeladas de la
    # OIT" in the flow registry's own description), redistributed by
    # World Bank WDI as SL.IND.EMPL.ZS / SL.AGR.EMPL.ZS. The same
    # harmonized-family relation who_ghe/un_wpp hold to their
    # collectors: modeled world coverage on the witness tier, the
    # collector print on the canonical tier, and the definitional seam
    # (industry incl. construction on the modeled face vs the door's
    # B-E aggregate) reads as two doors, never a contradiction.
    "ilo_modelled": (
        "ILO modelled estimates, ILOSTAT 2EMP family (redistributed by World Bank WDI as the employment-by-sector share codes)"
    ),
    # v18 (tertiary_education_share witness): the Barro-Lee / Lee-Lee
    # educational-attainment panels — THE SCHOLARLY COMPILATION THE
    # CORPUS ITSELF NAMES (La Défaite de l'Occident's refs read
    # "Tertiary-educated share of age cohort 70-74 (Barro-Lee)"; the
    # OWID chart's own attribution: "Barro and Lee (2015); Lee and Lee
    # (2016)"). Reached through OWID's long-run chart door
    # (share-of-the-population-with-completed-tertiary-education,
    # 1870+, 153 entities). A harmonized-family witness: reconciled and
    # interpolated across censuses — the LFS attainment print
    # (eurostat_lfs) is the collector tier, the panel is the world/historical
    # face, and the pair displays the vintage and definitional divergence
    # (the chart's own subtitle: "completed OR partially completed").
    "barro_lee": (
        "Barro-Lee / Lee-Lee educational attainment panels (scholarly compilation, 1870-2010; via OWID's long-run chart door)"
    ),
    # v18 (immigration_stock witness): the UN Population Division's
    # Trends in International Migrant Stock — DESA's compiled estimates
    # of the foreign-born stock per country (census-based, with
    # estimation for missing years), worldwide 1990-2024, redistributed
    # by World Bank WDI as SM.POP.TOTL. The harmonized-family witness
    # for the Eurostat migration collector: same underlying
    # registrations, one estimation step apart (the WPP relation).
    "un_desa": (
        "UN Population Division, Trends in International Migrant Stock (DESA estimates; redistributed by World Bank WDI as SM.POP.TOTL)"
    ),
    # v18 (immigration_stock canonical): Eurostat's migration
    # collection — the foreign-born stock each country's own
    # registration prints (dataset migr_pop3ctb, pinned c_birth=FOR,
    # the "Foreign country" total). Distinct questionnaire from
    # demo_find/lfs/na: the migration/citizenship collection. The Todd
    # by-origin face (Le Destin des immigrés' Maghreb/Turkish/Portuguese
    # boards — FR-by-MA/DZ/TN/TR/PT probed live, the codes print
    # 2015-2018 for the detailed French slices) is the recorded future
    # door in sources.yaml: the indicator shape carries one value per
    # entity-year, the bilateral matrix is its own decision.
    "eurostat_migr": (
        "Eurostat migration statistics (migr_pop3ctb — foreign-born stock by country of birth, as each country reports)"
    ),
    # v22 (immigration_stock by-origin witness): the OECD migration
    # questionnaire's own bilateral matrix — DSD_MIG_F@DF_MIG_POPF,
    # "International migration database - stocks of foreign-born
    # population": the foreign-born stock by country of birth as the
    # member states submit it (REF_AREA x BIRTH_COUNTRY, both axes
    # OECD-ISO3). AN OECD-COMPILED WITNESS, not a second collector of
    # the registrations: the OECD assembles the questionnaire answers
    # into its International Migration Database (the IMD's own
    # foreign-born face), the same relation oecd_family (v16) holds to
    # the national series it standardizes. THE SEAM the root field
    # exists to display: the two questionnaires agree TO THE UNIT on
    # the co-covered core (FR<-MAR _T 2015 = 954,742 = the Eurostat
    # c_birth print exactly, 2018 = 992,120 both sides, verified live
    # 2026-09-22) — agreement that reads like independent confirmation
    # unless the genealogy says both doors walk back to the same
    # national registrations. And the OECD face EXTENDS what the
    # Eurostat universe prints: the FR Maghreb series 2019-2021 past
    # the Eurostat cutoff, and the world's non-European destinations
    # (US<-MEX 12,383,868 in 2024) the 45-geo Eurostat codelist
    # structurally cannot carry — the compilation seam, shown never
    # reconciled.
    "oecd_mig": (
        "OECD International Migration Database (DSD_MIG_F@DF_MIG_POPF — the questionnaire's foreign-born matrix, OECD-compiled)"
    ),
    # v19 (top_income_share canonical): the World Inequality Database —
    # the DINA research harmonization (distributional national accounts:
    # fiscal microdata + household surveys + national accounts blended
    # per the 2020/2025 guidelines) whose pre-tax national-income
    # concepts Todd himself reads in La Défaite de l'Occident ("WID
    # data" — the corpus's own words). Reached through OWID's chart
    # door: probed live 2026-09-21, api.wid.world refuses this
    # environment on EVERY extractor shape (CloudFront 403 — the
    # endpoint the R/Stata packages ride), the country pages are
    # WordPress views without machine files, so the chart door
    # (incomes-of-the-richest, 165 entities 1820-2024, attribution
    # "WID.world (2026)") is the machine-readable face of the
    # compilation — the same door-relation oecd_family holds (v16). A
    # research-harmonization root serving as CANONICAL: no collector
    # anywhere prints a top-1% income share (tax administrations
    # register incomes, never the national share of the top fractile —
    # the metric is by construction a constructed series), so the
    # authoritative compilation the corpus names IS the origin — the
    # consanguinity_studies constitution (v17), not a collector. No
    # cross-root witness exists on any machine door (the IDD's 35
    # measures carry no top-share print — the probe record; the OWID
    # extrapolations chart is the SAME root's modeled extension,
    # refused by the anti-derivation discipline).
    "wid": (
        "World Inequality Database (WID.world — DINA research harmonization, pre-tax "
        "national income concepts; via OWID's chart door)"
    ),
    # v19 (gini_index canonical): the OECD Income Distribution Database
    # — the national household-survey microdata AS SUBMITTED by member
    # statistical offices (equivalized disposable income, the concept
    # the 1995 fifteen-country table of L'illusion économique read), on
    # the SDMX wire as DSD_WISE_IDD@DF_IDD (MEASURE=INC_DISP_GINI, unit
    # 0_TO_1, 45 areas, 1974-2025 — RUS carried 2008-2017, the survey
    # window). The collector judgment for content: survey tabulations
    # redistributed, never modeled (the layer judgment the WID witness's
    # DINA estimates sit against). THE STITCHING the root label has to
    # carry: the IDD prints the same country-year under METHODOLOGY x
    # DEFINITION vintages (METH2012 the current computation, METH2011
    # the pre-revision history; D_CUR the current income definition,
    # D_PREV/D_INC its back-series with/without the overlap year) — the
    # config's four-door priority chain is the OECD explorer's own
    # chained display made explicit, every collision a logged
    # provenance discard.
    "oecd_idd": (
        "OECD Income Distribution Database (IDD — national household-survey Ginis as "
        "submitted, equivalized disposable income; METH2012 chained through the "
        "definition vintages)"
    ),
    # v19 (road_accident_mortality canonical): the ITF/IRTAD road-safety
    # database — police-reported crash registrations as the member
    # countries submit them (the IRTAD questionnaires), on the SDMX wire
    # as OECD.ITF DSD_INDICATORS@DF_SAFETY (FATALITIES/10P5HB: road
    # deaths per 100,000 population, 55 areas 1994-2025 — FRA 15.2 in
    # 1994 -> 4.7 in 2024). The collector judgment, the DF_COM relation
    # for road deaths. RUS absent from the ENTIRE flow (verified live on
    # the full slice, zero rows) — the honest coverage limit; the
    # same dataflow also prints the per-vehicle face (10P4VEH_MOT_ROAD
    # — the exact denominator of Todd's 1974 WHO table in Le Fou et le
    # Prolétaire) and the per-vehicle-km face (10P9VEHKM), both
    # registered non-wired doors.
    "itf_irtad": (
        "ITF/IRTAD road safety statistics (police-reported crash registrations as "
        "submitted; OECD.ITF DSD_INDICATORS@DF_SAFETY on the SDMX wire)"
    ),
    # v19 (road_accident_mortality witness): the WHO Global status
    # report on road safety estimates — the RS_* indicator family on
    # GHO ("Estimated road traffic death rate (per 100 000 population)",
    # RS_198: 197 countries at the report's own single 2021 vintage —
    # the modeled world face, RUS included at 10.6). A DIFFERENT WHO
    # estimate family from who_ghe (the GHE cause-of-death
    # redistribution): the status report models road deaths from the
    # registrations + corrections for underreporting — the same
    # collector-estimates relation, its own root because its own
    # methodology and vintage cadence (the biennial report's cross-
    # section, not the GHE's annual series).
    "who_roadsafety": (
        "WHO Global status report on road safety (modeled road-death estimates; the RS_* "
        "indicator family on GHO)"
    ),
    # v20 (incarceration_rate canonical): the Institute for Crime & Justice
    # Policy Research's World Prison Brief — THE compilation the field
    # reads (the national prison administrations' own counts, per 100,000
    # population, pre-trial and remand detainees included), 225 areas,
    # 1993-2026. Reached through OWID's chart door (prison-population-
    # rate, attribution "Institute for Crime & Justice Policy Research
    # (2026)" read live from the chart metadata 2026-09-22): the WPB's
    # own site (prisonstudies.org) carries no API (404 probed), and the
    # UNODC dataportal that also collects penal data is a client-rendered
    # SPA whose machine door never surfaced in the probe record — so the
    # chart IS the wire, the same door-relation oecd_family (v16) and wid
    # (v19) hold. A compilation serving as CANONICAL by necessity: no
    # international collector prints an incarceration rate on any machine
    # wire from this environment (the probe record), so the compilation
    # the boards read is the origin tier — the consanguinity_studies
    # constitution (v17).
    "icpr_wpb": (
        "Institute for Crime & Justice Policy Research, World Prison Brief "
        "(national prison-administration counts compiled; via OWID's chart door)"
    ),
    # v20 (incarceration_rate witness): the WHO Health in Prisons
    # database — the prison-health questionnaire collection (GHO's
    # PRISON_* indicator family, the European member states' own reports
    # through the WHO-Europe prison-health network). PRISON_A2_
    # PRISIONERS_PER100KPOP prints a 36-country European cross-section at
    # the collection's own single 2020 vintage (FRA 93.1, DEU 69.7,
    # GBR 129.8 — read live 2026-09-22) — the coupe pattern the GHE
    # cirrhosis witness (v18) and RS_198 (v19) set: one print, the
    # collection's own cadence, never a series. A genuinely different
    # root from icpr_wpb (the health-services questionnaire vs the
    # prison-administration compilation): the pair displays the two
    # doors' 2020 seams, never reconciled.
    "who_prisons": (
        "WHO Health in Prisons database (the European prison-health questionnaire "
        "collection; the PRISON_* family on GHO)"
    ),
    # v20 (math_test_scores canonical): the OECD PISA assessment — the
    # triennial survey's own mean scale scores (the PISA Database, OECD
    # 2023 vintage), reached through OWID's chart door (average-
    # performance-of-15-year-olds-in-mathematics-reading-and-science,
    # mathematics column, 90 entities, the seven cycles 2003-2022,
    # attribution "OECD (2023) ... 'PISA Database' [original data]" read
    # live from the chart metadata). The oecd_family door relation: the
    # OECD runs the assessment (the collector judgment — nobody upstream
    # prints a PISA score), but the SDMX registry carries NO PISA
    # dataflow (verified on the full live registry listing in v19's
    # probe record — the education flows there are REG_EDU regional and
    # TALIS teacher surveys), so the chart door is the machine face.
    # Todd's own table is TIMSS 8th-grade (L'illusion économique, "OECD
    # source") — the IEA assessment read through the OECD's own volume;
    # TIMSS itself has NO machine door (zero sitemap hit, no IEA API —
    # the probe record), so the modern OECD door is the wired face and
    # the TIMSS seam is documented per-indicator.
    "oecd_pisa": (
        "OECD PISA assessment (the PISA Database mean scale scores; via OWID's chart door)"
    ),
    # v20 (obesity_rate canonical): the NCD Risk Factor Collaboration's
    # adult BMI pooled analysis — the worldwide re-analysis of
    # population-based measurement surveys (945 country-years of
    # measured height/weight), REPUBLISHED BY WHO GHO as the NCD_BMI_*
    # indicator family (the 2026 vintage, lastUpdated 2026-05-22, read
    # live). Canonical through the provider's OWN machine wire (the GHO
    # API, NCD_BMI_30C the crude 18+ face, 199 countries, 1980-2024,
    # full sex-split) — richer than the OWID chart door that
    # redistributes the same series (share-of-adults-defined-as-obese,
    # bit-identical to rounding on every probed anchor: FRA 2024 =
    # 12.524594 on both doors, the same-root relation verified live —
    # the auto-witness refusal's own evidence). No collector prints an
    # obesity prevalence anywhere (no international health-examination
    # survey wire exists — the probe record), so the pooled analysis is
    # the origin tier, the consanguinity_studies/wid constitution.
    "ncd_risc_bmi": (
        "NCD Risk Factor Collaboration, adult BMI pooled analysis "
        "(republished by WHO GHO as the NCD_BMI_* family)"
    ),
    # v20 (hiv_prevalence_rate canonical): UNAIDS — the Joint United
    # Nations Programme on HIV/AIDS' own epidemic indicators (the Global
    # AIDS Update's estimates, the Spectrum/EPP modeling framework's
    # central estimates), reached through OWID's chart door (share-of-
    # the-population-infected-with-hiv, 161 entities, 1990-2024,
    # attribution "Joint United Nations Programme on HIV/AIDS (2026) ...
    # 'Global AIDS Update, Epidemic Indicators'" read live). The direct
    # UNAIDS machine door is closed from this environment (aidsinfo is
    # a client-rendered SPA with no discoverable API path, api.unaids
    # .org is DNS-dead — the probe record), so the chart IS the wire,
    # the wid door relation. The compilation's own country universe
    # EXCLUDES the USA, Russia and China (verified identically on the
    # GHO redistribution MDG_0000000029 — the UNAIDS reporting shape
    # itself, not a door artifact). Same-root doors refused as
    # auto-witnesses: the GHO MDG_0000000029 print (1-decimal) and the
    # WB SH.DYN.AIDS count face (its own metadata READ: "Adults (ages
    # 15+) living with HIV" — the number, not the rate); the IHME GBD
    # cross-root family stays behind OWID's 403 (re-confirmed live on
    # the unaids-vs-ihme chart).
    "unaids": (
        "UNAIDS (the Global AIDS Update epidemic indicators, modeled estimates; "
        "via OWID's chart door)"
    ),
    # v20 (male_height_trend canonical): the NCD Risk Factor
    # Collaboration's 2016 eLife compilation "A century of trends in
    # adult human height" — 1,472 population-based studies re-analyzed
    # into mean height AT AGE 18 by birth cohort, 200 countries and
    # territories, 1896-1996. Reached through OWID's chart door
    # (average-height-of-men, single column "Mean male height (cm)",
    # attribution "NCD Risk Factor Collaboration (2016)" read live);
    # ncdrisc.org's own downloads page carries only the 2020 child/
    # adolescent study files today (read live — the adult 2016 eLife
    # files no longer listed), so the chart door is the machine face.
    # The sibling door (average-height-by-year-of-birth, the Men+Women
    # columns) is the SAME root — an auto-witness, refused; the Women
    # column is the registered future door. Distinct from ncd_risc_bmi
    # (the same collaboration's BMI pooled analysis, a different
    # publication with its own cadence — the who_ghe/who_roadsafety
    # granularity).
    "ncd_risc_height": (
        "NCD Risk Factor Collaboration, a century of trends in adult human height "
        "(2016 eLife, birth cohorts 1896-1996; via OWID's chart door)"
    ),
    # v20 (male_height_trend witness): the Baten & Blum (2015) height
    # compilation through Clio-Infra's "Biological Standards of Living"
    # — the economic-history reconstruction of mean male heights from
    # the anthropometric record (militia, army recruits, conscripts:
    # the sources states kept before surveys existed), 153 entities,
    # 1550-2000, sparse by nature. Reached through OWID's chart door
    # (average-height-of-men-by-year-of-birth, column "Height (Baten
    # and Blum 2015)", attribution read live: "Various sources (2015)
    # ... 'Clio-Infra - Biological Standards of Living' [original
    # data]"). A genuinely CROSS-ROOT witness against ncd_risc_height
    # (the historical-record compilation vs the measured-survey
    # re-analysis — different source bases, different methods), the
    # barro_lee relation: the cm-level seams on the overlapping cohorts
    # (FRA 1900: Baten-Blum 166.8 vs NCD-RisC 166.9) are displayed,
    # never reconciled.
    "baten_blum": (
        "Baten & Blum (2015) via Clio-Infra, Biological Standards of Living "
        "(the historical anthropometric record; via OWID's chart door)"
    ),
}


# Layer of the sourcing stack each provider occupies (ADR-0007 tiers;
# the human-readable narrative lives in config/sources.yaml, this map is
# the executable truth the dist carries per source):
#   curated  = L0-L2: hand-entered, one-citation-per-point official or
#              scholarly series (committed CSVs in catalog/curated/);
#   collector = L1-collector: national official statistics republished
#              as reported by an international collector (UN DYB); the
#              OECD DF_COM entry below is the SAME judgment for content
#              (WHO Mortality Database registrations as submitted — not
#              modeled; contrast with who_gho, whose homicide indicators
#              are literally named "Estimates of ...");
#   harmonized = L3 model estimates for cross-country comparability
#              (UN IGME via OWID, WDI, GHO) — for OWID this describes the
#              *content* of the pilot charts: the provider itself is an
#              honest L4 redistribution of the L3 estimates.
PROVIDER_LAYER: dict["Provider", str] = {
    Provider.curated: "curated",
    Provider.un_dyb: "collector",
    Provider.oecd: "collector",
    Provider.eurostat: "collector",
    Provider.owid: "harmonized",
    Provider.worldbank: "harmonized",
    Provider.who_gho: "harmonized",
}

# How each provider's sources are cited in the dist (P2, the witness-
# citation gap of the external review): a human-readable citation string
# per source, formatted from the source_ref, plus the license its data
# carries. These mirror config/sources.yaml's narrative blocks (base_url /
# license_default) — keep the two in sync when a provider is added; the
# YAML is the human story, this map is the executable truth the dist emits.
# v17: the Eurostat template carries the dataset's own API title (the
# registry below) — one questionnaire, one title, never a borrowed one.
EUROSTAT_DATASET_TITLES: dict[str, str] = {
    "demo_find": "Fertility indicators",
    "une_rt_a": "Unemployment by sex and age - annual data",
    # v18 (read from each dataset's own live API label 2026-09-21 — the
    # citation carries the questionnaire's own title, never a borrowed one):
    "nama_10_a10_e": "Employment by main industry (NACE Rev.2) - national accounts - annual data",
    "edat_lfse_03": "Population in private households by educational attainment level",
    "migr_pop3ctb": "Population on 1 January by age group, sex and country of birth",
    # v23: read live from the API label (2026-09-25, the v23 probe) — the
    # citizenship questionnaire's own title, one-questionnaire-one-title.
    "migr_pop1ctz": "Population on 1 January by age group, sex and citizenship",
}
# v19: the OECD connector's three dataflows — titles read from the live
# SDMX registry (2026-09-21), the same one-questionnaire-one-title rule as
# EUROSTAT_DATASET_TITLES. The citation builder dispatches per flow; the
# DF_COM template stays PROVIDER_CITATION's oecd default (bit-compat with
# every pre-v19 dist).
OECD_DATAFLOW_TITLES: dict[str, str] = {
    "DF_COM": "Causes of mortality",
    "DF_IDD": "Income distribution database",
    "DF_SAFETY": "Transport safety indicators",
    # v22: read live from the SDMX registry (2026-09-22) — the migration
    # questionnaire's foreign-born face, one-flow-one-title as ever.
    "DF_MIG_POPF": "International migration database - stocks of foreign-born population",
    # v23: read live from the SDMX registry (2026-09-25, the v23 probe —
    # the registry's own `name` field on DSD_MIG@DF_MIG 1.0): the SIBLING
    # flow's plain title, the questionnaire's umbrella name. Its own
    # description names the citizenship content: "stocks of foreign
    # population by nationality".
    "DF_MIG": "International migration database",
}
# v19: the IDD DEFINITION dimension's own codelist labels (read live from
# the DSD, CL_DEFINITION) — the citation names the vintage a door carries
# ("current definition" vs the back-series variants) so the four gini
# doors stay distinguishable where a reader meets them.
IDD_DEFINITION_LABELS: dict[str, str] = {
    "D_CUR": "current definition",
    "D_PREV": "previous definition, with overlap year",
    "D_INC": "previous definition, without overlap year",
}
PROVIDER_CITATION: dict["Provider", str] = {
    Provider.curated: "Hand-curated series '{ref}' (catalog/curated/, one citation per point)",
    Provider.un_dyb: "United Nations Statistics Division, Demographic Yearbook {edition}, Table {table}",
    Provider.owid: "Our World in Data, grapher dataset '{ref}'",
    Provider.worldbank: "World Bank Open Data API, indicator '{ref}'",
    Provider.who_gho: "WHO Global Health Observatory (GHO) API, indicator '{ref}'",
    Provider.oecd: "OECD, Causes of mortality (DF_COM), death cause '{cause}' - WHO Mortality Database redistribution",
    Provider.eurostat: "Eurostat, {title} (dataset {dataset}), series '{code}'",
}
PROVIDER_LICENSE: dict["Provider", str] = {
    Provider.curated: "Facts with citation (small extracts, clearly attributed) — see docs/licenses.md",
    Provider.un_dyb: "UN data reuse policy (attribution required, no endorsement implied)",
    Provider.owid: "CC-BY-4.0",
    Provider.worldbank: "CC-BY-4.0",
    Provider.who_gho: "CC-BY-3.0-IGO",
    Provider.oecd: "OECD Terms and Conditions, attribution required (content: WHO Mortality Database)",
    Provider.eurostat: "Eurostat reuse policy (attribution required, no endorsement implied)",
}


class SourceRole(str, Enum):
    """ADR-0007/ADR-0008: how a source participates in an indicator.

    - `canonical`: feeds the indicator's canonical series. Duplicates
      across canonical sources are arbitrated by `priority` (an
      authenticity-tier-internal mechanism — never a cross-layer blend).
    - `witness`: stored, validated and displayed BESIDE the canonical
      series as divergence. Never merged into it, never averaged with
      it. The Todd board reads the canonical (as-reported) tier; the
      harmonized tier rides as witness (ADR-0008), and the Extra board
      reads the same dist with the witness as its display series.
    """

    canonical = "canonical"
    witness = "witness"


class SourceRef(BaseModel):
    provider: Provider
    # This indicator's identifier WITHIN that source (OWID slug, World Bank
    # code, GHO code, DYB "edition/table", curated CSV name...). The exact
    # meaning depends on the provider.
    ref: str
    # Column to use if the source exposes several values per row (e.g.
    # multi-variable OWID CSV, DYB number-vs-rate blocks). None = single
    # column auto-detected.
    field: str | None = None
    # Priority rank in case of an inter-source duplicate for the same
    # (entity, year): 1 = highest priority. Must be unique within a given
    # indicator (see validator below). Only canonical sources are ever
    # arbitrated by it (witnesses never enter arbitration — ADR-0007).
    priority: int = Field(..., ge=1)
    # Role in the canonical/witnesses model. Defaults to canonical, which
    # keeps every pre-ADR-0008 single-source indicator config valid.
    role: SourceRole = SourceRole.canonical
    # The NATIVE unit of this source's raw values, when it differs from the
    # indicator's canonical `unit`. Declared explicitly per source — the
    # conversion is applied by normalize.py through its declared lookup
    # table (never a guessed factor). None = source is already in the
    # canonical unit.
    unit: str | None = None
    # Root genealogy (v11): the ultimate origin this source redistributes —
    # see ROOT_LABELS above. REQUIRED on every source so the genealogy can
    # never silently go missing when a new one is added; must belong to the
    # closed registry.
    root: str

    @field_validator("root")
    @classmethod
    def _known_root(cls, v: str) -> str:
        if v not in ROOT_LABELS:
            raise ValueError(
                f"unknown root {v!r} — declare it in ROOT_LABELS (src/schema/indicator.py) "
                f"first; known roots: {sorted(ROOT_LABELS)}"
            )
        return v


class PlausibleRange(BaseModel):
    """Bounds used by validate.py as a plausibility guard — NOT a scientific
    ground truth, just a safety net against unit/entry errors."""
    min: float | None = None
    max: float | None = None


class Indicator(BaseModel):
    id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$")
    label: str
    family: Family
    unit: str
    higher_is_better: bool

    todd_core: bool = Field(
        ..., description="True = used by Todd in his books (Todd mode). False = added in Extra mode only."
    )

    sources: list[SourceRef] = Field(..., min_length=1)

    coverage_start: int | None = None
    coverage_end: int | None = None

    reliability: Reliability
    reliability_criteria: str = Field(
        ..., description="One-sentence justification for the reliability level — never a bare label (see architecture review)."
    )
    reclassification_sensitive: bool = Field(
        default=False,
        description="True if the indicator is exposed to cause-of-death reclassification bias (suicides, cirrhosis...).",
    )

    plausible_range: PlausibleRange | None = None
    companion_indicators: list[str] = Field(default_factory=list)

    license: str
    notes: str | None = None

    @field_validator("label", "reliability_criteria", "notes", "unit", "license", mode="before")
    @classmethod
    def _strip_whitespace(cls, v: str | None) -> str | None:
        # YAML folded block scalars (">") leave a trailing \n — cleaned up
        # here rather than polluting every config file.
        return v.strip() if isinstance(v, str) else v

    @field_validator("sources")
    @classmethod
    def _unique_priorities(cls, sources: list[SourceRef]) -> list[SourceRef]:
        priorities = [s.priority for s in sources]
        if len(priorities) != len(set(priorities)):
            raise ValueError("source priorities must be unique within a given indicator")
        return sources

    @model_validator(mode="after")
    def _low_reliability_consistency(self) -> "Indicator":
        # Enforces the brief's cross-cutting principle: never a composite on
        # "low" reliability data without a visible warning. We can't stop
        # the frontend from using it, but we can force a written
        # justification here — it's this exact value that will be shown as
        # the warning.
        if self.reliability == Reliability.low and len(self.reliability_criteria) < 15:
            raise ValueError(
                f"{self.id}: reliability=low requires a detailed reliability_criteria (>=15 chars), "
                "not a vague justification — this value is what gets displayed as the warning."
            )
        return self

    @model_validator(mode="after")
    def _at_least_one_canonical_source(self) -> "Indicator":
        # ADR-0007/0008: an indicator without a canonical source would have
        # an empty main series with only witnesses around it — a config
        # error, not a legitimate "witnesses-only" display mode. If that
        # mode is ever wanted, it deserves its own explicit decision.
        if not any(s.role == SourceRole.canonical for s in self.sources):
            raise ValueError(
                f"{self.id}: no canonical source declared — every indicator needs at least "
                "one source with role=canonical (witnesses supplement it, never replace it)."
            )
        return self

    def sources_by_priority(self) -> list[SourceRef]:
        return sorted(self.sources, key=lambda s: s.priority)
