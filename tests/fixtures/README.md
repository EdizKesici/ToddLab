# Test fixtures

Every file here is SYNTHETIC test data. The parsers and the pipeline are
real — tests run the repo's real code against these files — but the
VALUES are hand-picked for readability, not copied from the sources.

Two design rules, learned the hard way (the v9 review):

1. **Fixture values must diverge from the live data.** The maternal
   fixture's `France,FRA,2020,5.2` sits next to the real snapshot's
   7.9090786, and the fixture's witness coverage even extends to 2021
   where the real fetch stops at 2020. The divergence is deliberate:
   it is what makes contamination detectable — a fixture number quoted
   as data (exactly what the v9 changelog did with "the MMEIG witness
   carries 5.2", retracted in v9.1) cannot accidentally match the truth.
2. **Fixture numbers never leave this directory.** Changelogs, docs and
   reviews quote `python -m src.cli stats` output, or bytes from the
   raw snapshots and the dist — never anything read here.

The WB fixtures (`wb_imrt_ma_sample.json`, `wb_country_meta_sample.json`)
follow the same rules: the response SHAPE is the live API's (the [meta,
rows] pair, the /country aggregate classification, the .MA.IN suffix and
its printed name), the values are synthetic (RUS 1990 = 17.5 is a real
WB print but the co-coverage makes the set unmistakably not a snapshot).

The v13 suicide fixtures (`oecd_suicide_sdmx.csv`,
`gho_sdgsuicide_sample.json`) follow the homicide precedent with one
documented nuance: their ANCHOR values are the live-probed numbers
(RUS 1994 M 73.9 / F 13.2, RUS 2000 M 69.8 as-reported vs 95.20444591
modeled, LTU 1994 M 83.5, RUS 2021 YEARSALL 36.68325073) — the
collector-vs-model divergence pair is the integration test's subject, so
the fixture reproduces the exact bytes the live probes returned. The
fills around them are synthetic (GHO Low/High intervals, the LTU GHE
rows, RUS F 2000), and the co-coverage is unmistakably not a snapshot
(3 countries over 2-3 years vs the live slices' 46 countries x 1960-2024
and 185 countries x 2000-2021). If a live vintage ever moves, the fixture
keeps the old anchors and the divergence becomes detectable — the same
safety property, arrived at from the other side.

The v14 fertility fixtures (`eurostat_totferrt_sample.json`,
`eurostat_totferrt_fx_sample.json`, `eurostat_totferrt_fr_sample.json`,
`wb_tfrt_sample.json`) follow the v13 anchor precedent: the response
SHAPES are the live APIs' (Eurostat's flat-position JSON over [freq,
indic_de, geo, time] with the optional per-observation `status` flags;
the WB [meta, rows] page), and the ANCHOR values are the live-probed
numbers (2026-09-19) because the quirks they pin ARE the tests'
subjects — the FX/FR seam pair (FX 1960=2.73, FX 1994=1.66, FX
2000=1.87, FX 2012=1.99 metro vs FR 1998=1.78, FR 2000=1.89, FR
2012=2.01, FR 2014=2.0 flag 'b', FR 2023=1.66 flag 'p' whole-France),
the DE/DE_TOT identical duplicate (1.39 flag 'b'), the codelist quirks
(EL 2023=1.26, UK 2012=1.92, XK 2017=1.65), the collector's honest
partial windows (IE 1960=3.78, RU 2008=1.49) and the aggregate drop
(EU27_2020 2023=1.38 flag 'bep'). The WB page reuses the IMRT fixture's
row set with TFR-plausible prints (RUS 1990=1.892 and FRA 2020=1.79 are
real WPP prints — the WDI precision is as carried, per-observation; ZWE
1990=4.61 and FRA 1960=2.9 are synthetic fills;
the shared page itself could NOT be retargeted — its per-1,000 values
sit outside the TFR's plausible bound and would flag as range
violations in the harness). Co-coverage is unmistakably not a snapshot:
10 geo x 7 years (and 4-5 years on the geo-pinned miniatures) vs the
live 58 x 65. If a live vintage ever moves, the anchors keep the old
values and the drift becomes detectable.

The v15 fixtures (`dyb_table9_sample.xls`, `wb_cbrt_sample.json`) follow
the anchor precedent one generation on. `dyb_table9_sample.xls` is the
Table 15 builder's layout with Table 9's own title and LIVE DYB 2024
anchor values (Algeria's CBR series 22.3369498881 / 21.1357648315 /
20.0570445530 / 19.3150537642, Botswana's 24.4493008232, Burundi's
'+U' all-gap rates) plus the '*2' glued star-plus-ref marker on
Algeria's 2021 count (the v15 grammar find, in the real editions' own
family: "*47"/"*25") and Tonga's two Total rows under different quality
codes. `wb_cbrt_sample.json` is the TFRT page's shape with CBR-plausible
prints anchored on the live WDI values (FRA 2024 = 9.7, RUS 1960 =
23.881, NER 1960 = 57.613 — the WPP tail's peak) and synthetic fills
(World/AFE/XD aggregates for the drop test, FRA 1960 = 17.9). The same
contamination-dodge reason as v14, in mirror: the shared IMRT page's
per-1,000 prints (17.5) would read as PLAUSIBLE CBR values and
contaminate silently — the dedicated page keeps the co-coverage
unmistakably not a snapshot (5 countries x 1-2 years vs the live
13 editions x 175 entities and 215 x 65 on the witness door). The
marker indicators carry NO fixtures — their integration seeds read the
REAL committed curated tables (the connector is network-free by
construction), which is the same anchor discipline from the other side:
the test world and the dist world read the very same reviewed CSVs.

A v15 correction rides the Table 9 fixture itself (the external
review's find, repaired in v16): its France block had been built with
fabricated round numbers (rates 11.7/11.5/..., counts 842000+) and the
'*' provisional marker glued on 2020 — an anchor-discipline violation
the v15 changelog then quoted as fact ("France 2020 carries
provisional=true"), while the live file prints 2020 UNFLAGGED and the
'*' on 2022/2023/2024. The block now carries the real DYB 2024 France
Total row byte-for-byte (rates 10.6579082599 / 10.7086704955 /
10.4267737019* / 9.6873422054* / 9.5025212576*, counts 696664 /
701819 / 686564* / 639533* / 629000*). The lesson is structural and
v16 enforces it by construction: the NMARPCT fixtures below are not
hand-typed at all — `scripts/v16_probe/make_nmarpct_fixtures.py`
GENERATES them from the live API responses, so every value is read,
never typed.

The v16 fixtures are the NMARPCT quartet + the OECD witness page.
`eurostat_nmarpct_sample.json` (the main unpinned slice, 10 geo x 9
years vs the live 58 x 65) carries the codelist's own quirks and the
live anchors: the DE/DE_TOT pre-reunification divergence years (DE
1960 = 6.3 vs DE_TOT 7.6; DE 1980 = 7.6 vs 11.9 — the GDR's high
non-marital share), the FX/FR seam values (FX 1960 = 6.1 / 2000 =
42.6; the FR/FX rows dropped at parse as variants, logged), the
collector's flags (EL 2023 'b', MD 2022 'p' — the live slice's only
country-level flagged cells), the EU27_2020 aggregate, and Kosovo's
no-ISO3 path (XK 2002 = 6.8, 2012 = 46.1). The three geo-pinned
miniatures carry the seam doors' own series: `eurostat_nmarpct_de_tot_
sample.json` (the German series — the five divergent benchmark years
1960/1970/1980/1985/1990 at 7.6/7.2/11.9/16.2/15.3 plus the modern
prints), `eurostat_nmarpct_fr_sample.json` (41.7 -> 59.7, the
whole-France series), `eurostat_nmarpct_fx_sample.json` (6.1 -> 55.8,
the metropolitan series). `owid_nmarpct_sample.csv` is the OECD Family
Database witness's shape with live-anchored rows only (France 1998 =
41.7 / 2020 = 62.2 — equal to the collector's own prints; Germany
1960 = 7.6 — the OECD rides the all-Germany series; Japan 2020 = 2.4;
Chile 2019 = 75.08 — the questionnaire tail's peak and the plausible
bound's own reason): the real chart carries no aggregate rows, so the
fixture invents none (the World/Freedonia resolution paths live in the
homicide fixture).

## v17 — the une_rt_a miniature and the dedicated NE page (generated)

The v17 fixtures continue the v16 discipline: `scripts/v17_probe/
make_unert_fixtures.py` GENERATES both files from the live API
responses at generation time, and prints the anchors it found as the
generation-time audit (the values below are those live reads).

`eurostat_unert_sample.json` (the une_rt_a canonical slice, 6 geos x
10 years vs the live 38 x 23) carries the labour-force door's own
quirks and live anchors: France the full-length series (2003 = 8.5,
the door's own start; 2015 = 10.4; 2023/2024 = 7.4 with the 'd' flag;
2025 = 7.7 'd' — the LFS-2021 questionnaire redesign's definitional
seam, the dataset's flag vocabulary b/d with no 'p'), the German
coverage cliff (DE 2009 = 7.3, DE 2005 ABSENT — the pre-2009 years
live only on the witness), the crisis peaks as published (ES 2013 =
26.1, EL 2013 = 27.8 — the EL code resolving through the GRC
override), Montenegro's short series (2020 = 17.9, 2021 ABSENT), and
the EU27_2020 aggregate drop (8 cells, logged). The layout is the
dataset's own [freq, age, unit, sex, geo, time] with the three pins
(Y15-74/PC_ACT/T) exactly as the connector's pin-guards demand.

`wb_uem_ne_sample.json` is the dedicated national-estimate witness
page (the shared IMRT page's per-1,000 prints would sit INSIDE the
rate's plausible band and contaminate silently — the same dedicated-
page discipline as the TFR and CBR pages). Live-anchored rows only:
FRA 1990 = 9.36 / 2015 = 10.354 / 2023 = 7.335 / 2024 = 7.436 (the
rounding seam against the collector's 1-decimal 7.4), DEU 1991 =
5.316 and 2005 = 11.193 (the coverage cliff's other side), USA 1991 =
6.8, ESP 2013 = 26.094, GRC 2013 = 27.686, XKX 2001 = 57.0 (the
post-war break value, flowing to the unresolved report — the pending
class), plus the WLD aggregate row the provider's own classification
drops. The consanguineous indicator needs no fixture at all: its
source IS the committed catalog table, which the test harness reads
for real (network-free by construction — the markers' precedent).

## v18 (2026-09-21)

`oecd_cicdcirr_sdmx.csv` (the cirrhosis canonical slice, 104 rows vs
the live 7,089) carries the mortality door's third-cause anchors:
La Chute finale's own calibration pair (FRA 1979 = 29.0 both-sexes —
NO sex split in the era's French data, a lesson the first test draft
learned; SWE 1979 = 12.2 / 17.5 male / 7.0 female), le Fou et le
Prolétaire's Mediterranean pole (ITA 1979 = 34.7 / 50.0 male), DEU's
post-reunification face (1994 =
24.4 / 32.9 male), and the flag rows the live slice carries on
specific areas the carver had to READ before carving (KOR 1995 'B',
TUR 2010/2015 'D' — the first draft missed them by guessing the flag
areas instead of reading the slice). Generated from the saved live
response by scripts/make_v18_fixtures.py.

`gho_cirrhosis_sample.json` (SA_0000001457, 12 parsed rows) carries
the GHE witness's own grammar lesson: the indicator prints BOTH an
AGEGROUP_YEARS15PLUS and an AGEGROUP_YEARSALL series per key — the
connector keeps the all-ages face (RUS 2019 = 22.5 both / 31.1 male /
15.7 female) and drops the 15+ slices logged (the 42.1 male 15+ face
living in the drop log, not the tier) — the SDGSUICIDE Dim2 rule's
second instance, and the first where the indicator's own title face
differs from the kept series.

The Eurostat quartet (`eurostat_nama_be_sample.json`,
`eurostat_nama_a_sample.json`, `eurostat_edat_ed58_sample.json`,
`eurostat_edat_ed34_sample.json`) are carved from the live full
slices with the dims/codelists intact and only the value/status
dictionaries filtered: nama B-E carries the EA two-letter aggregate
row (the only one in any wired codelist — the drop-log path's own
test) beside FR/DE/XK-codelist rows and the accounts' 'p' flags on
2023-2024; nama A the agrarian-exodus anchors (FR 4.4 -> 2.3 — the
agricultural indicator withdrawn in v26, the fixture stays as the
nama grammar's own nace-pin test); edat ED5-8 the attainment climb
(FR 24.5 -> 43.2) with the 'b' break flags; ED3_4 the completed-
secondary face (FR 41.4 / DE 56.7 — the at-least face would run ~20
points higher, a misload the pin catches). (v26: the migr FOR
fixture withdrew with its indicator.)

The WB dedicated page (`wb_sl_ind_empl_sample.json`) follows the v17
dedicated-page discipline (the shared page's per-1,000 prints would
contaminate a share band): the ILOEST industrial share (FRA 1991 =
28.42 -> 2024 = 19.54; BGR 1991 = 45.09 the planned-economy tail;
JPN/USA the world face) — plus the WLD/EMU aggregate rows the
provider's own classification drops. (v26: the agricultural and
migrant-stock pages withdrew with their indicators.)

`owid_education_tertiary_sample.csv` (49 rows vs the live 3,699)
carries the Barro-Lee witness's long-run anchors: France 1870 = 0.2
(the literacy-era true zero) -> 2020 = 31.9, and La Défaite de
l'Occident's own board — Russia 1990 = 37.8 vs USA 50.2 (the Soviet
tertiary legacy one read behind America's), Poland 1990 = 8.9 ->
2015 = 23.7. The chart's own face read live and documented: the
slug says completed-tertiary, the column prints "incomplete
tertiary", the subtitle "completed OR partially completed" — the
some-tertiary face the config's definitional note carries.

## v19 — the three-indicator delivery (eight fixtures, all live-carved)

All eight were generated by `scripts/v19_probe/make_v19_fixtures.py`
through the connector's own `build_url` (the v16 discipline: anchors
READ from the live responses, never typed — and the session's own two
typed-anchor bug-reports, FRA 2019 guessed at 0.281 for the door's
0.292 and BRA 2006 copied from an unfiltered probe line for the
door's 0.50879539, are the discipline's own proof it earns its keep).

The four IDD vintage doors (`oecd_idd_gini_cur.csv`,
`oecd_idd_gini_prevdef.csv`, `oecd_idd_gini_incdef.csv`,
`oecd_idd_gini_m2011.csv` — 88/12/4/103 anchored rows carved from the
649/19/61/421 live slices, the anchor areas FRA/USA/DEU/GBR/SWE/BRA/
RUS/ZAF/MEX/CHL) carry the stitching grammar's own anchors: the
current print (FRA 2020 = 0.278 -> 2023 = 0.299, USA 2023 = 0.3944025,
ZAF 2015 = 0.625602135 the world tail), the definition back-series
(FRA 2011 = 0.309 the seam year itself), the without-overlap variant
(BRA 2006 = 0.50879539), and the METH2011 history (FRA 1996 = 0.277,
USA 1995 = 0.361 — L'illusion économique's own year — and USA 1993 =
0.369, DEU 1985 = 0.251).

`itf_safety_road_mortality.csv` (358 of the live 1,551 rows, the
anchor areas FRA/USA/DEU/SWE/GBR/LVA/KOR/LIE/KAZ/SVN/JPN/NLD) carries
the IRTAD print's anchors: the sécurité-routière arc (FRA 1994 =
15.20273212 -> 2024 = 4.657801614), the never-halved USA (1994 =
15.47395544 -> 2023 = 12.1702024), the post-Soviet tail (LVA 1994 =
28.44400577, the live maximum), and the honest zero (LIE's microstate
0-death years).

The two WID chart doors (`owid_incomes_of_richest.csv`,
`owid_gini_wid.csv` — 558 rows each, the anchor entities incl. the
aggregate World row and East Germany) carry the inequality arcs: the
USA's full U-shape (1913 = 20.43 -> 2024 = 20.73), France's
Atkinson-Piketty decline (1910 = 22.73 -> 2022 = 12.1), Russia's
46-point arc (1820 = 16.01 -> 2017 = 20.0), the pre-tax gini tail
(Malawi 1997 = 0.8414), and the entity-resolution shapes the tests
pin (OWID_GDR the GDR entity, World resolving to nothing).

`gho_road_mortality.json` (11 country rows + the 7 non-COUNTRY rows
the parser drops logged, carved from the live 204) carries the WHO
coupe's own anchors: RUS 2021 = 10.6, FRA 2021 = 4.7 — every point
printing the report's single vintage.

## v20 fixtures — the queue delivery (the corpus-closing version)

All seven were generated by `scripts/make_v20_fixtures.py` through the
connectors' own `build_url` (the standing discipline: anchors READ
from the live responses, never typed).

The five OWID chart-door carves:

- `owid_prison_population_rate.csv` (118 of the live 2,272 rows — the
  Todd six-country board whole: FRA/USA/RUS/DEU/JPN/GBR, plus the
  bound calibrators SLV/CUB/SYC and the floor pair KOS/YEM) carries
  the Défaite board's anchors: USA 683 (2000) -> 542 (2023), RUS
  729 -> 300, FRA 82 -> 126, JPN 48 -> 33 — and Kosovo's pre-2008
  rows for the entity-validity discipline (the registry entity exists
  from 2008 only; the 2000-2006 prints refuse, dropped logged).
- `owid_pisa_math.csv` (61 of 496 — the six Todd countries' full
  cycles plus SGP/QAT/DOM the scale's ceiling/floor) carries the
  mathematics column's own anchors: FRA 510.79947 (2003) -> 473.94443
  (2022), the 2000 reading-only rows arriving as explicit gaps, and
  Russia's 2022 absence (the cycle it did not sit — no row at all).
- `owid_hiv_prevalence.csv` (179 of 5,514 — the patrilineal-belt
  anchors SWZ/ZAF/BWA/ZWE/ZMB plus FRA/DEU/GBR, with the World row
  and a UNAIDS regional aggregate kept deliberately: they resolve to
  nothing and drop logged, the discipline living in the fixture)
  carries the epidemic's own curves: ZWE 1995 = 29.64893 the peak,
  SWZ 2024 = 23.37995, FRA 0.12917 -> 0.28482.
- `owid_height_men.csv` (178 of 21,008 — FRA's full 101 cohort points
  whole, the other Todd anchors at decade cadence, NLD/KOR/LAO the
  ceiling/catch-up/floor, the World row for the drop discipline)
  carries the closing metric's arcs: FRA 166.41232 -> 179.73792
  (+13.3cm), NLD 182.5673, KOR 174.91963, LAO 152.88463.
- `owid_height_baten_blum.csv` (88 of 1,499 — FRA/USA/RUS whole, DEU
  at milestone years, PNG/DNK the floor/ceiling) carries the
  cross-root witness's own anchors: FRA 1660 = 162.6 the pre-1896
  tail, FRA 1900 = 166.8 (the cm-level seam against NCD-RisC's
  167.7), PNG 1880 = 152.359, DNK 1980 = 183.2.

The two GHO carves:

- `gho_ncd_bmi_30c.json` (96 country rows + the 4 non-COUNTRY rows
  the parser drops logged, carved from the live 28,350) carries the
  per-code AGE pin's own face (every row YEARS18-PLUS) and the full
  sex split: FRA 2024 = 12.524594/12.458491/12.585108 (both/male/
  female), USA 41.830319/40.642369/43.015891 the female inversion,
  ASM 2024 female = 80.890405 the Pacific tail, VNM 1980 male =
  0.045321116 the floor.
- `gho_prison_a2.json` (11 of the live 36 — the coupe's own anchored
  subset: FRA/DEU/GBR/GEO/MDA/SMR/MCO/ESP/ITA/POL/UKR) carries the
  WHO Health in Prisons cross-section: FRA 2020 = 93.1, GEO =
  245.99 the post-Soviet European top, SMR = 23.03 — every point the
  single 2020 vintage, the coupe's own shape.

(v26: the v22 bilateral fixtures — `eurostat_migr_row_fr_sample.json`
and `oecd_migf_sample.csv` — withdrew with the migration indicator;
the carving history lives in scripts/archive/make_v22_fixtures.py.)

## v23 fixtures (generated live by scripts/make_v23_fixtures.py)

- `gho_mdg_0000000001_sample.json` — a REAL slice of the GHO
  MDG_0000000001 payload as the API serves it SINCE THE DOOR CHANGE
  (verified live 2026-09-25: every row now carries Dim2 =
  AGEGROUP_MONTHS0-11 — the 0-11-months frame, the per-code AGE pin's
  own face): the FRA 2019-2020 rows on the three sexes (the
  integration test's ("france", 2020, male/None) assertions), one
  REGION row (the non-COUNTRY skip), one XKX 1986 row (the entity
  validity guard's drop in normalize). Replaces the WHOSIS-shape
  seeding of the MDG door (the pin would refuse the old shape loudly
  — by design).
(v26: the v23 migration fixtures — `eurostat_migr1ctz_row_fr_sample.json`
and `oecd_mig_b15_sample.csv` — withdrew with the migration indicator;
the carving history lives in scripts/archive/make_v23_fixtures.py.)

(v26: the v24 by-sex fixtures — `eurostat_migr3ctb_row_fr_m_sample.json`
and `eurostat_migr1ctz_row_fr_f_sample.json` — withdrew with the
migration indicator; the carving history lives in
scripts/archive/make_v24_fixtures.py.)

## v25 fixtures (generated live by scripts/make_v25_fixtures.py)

- `eurostat_lfsa_urgacob_t_sample.json` — the REAL 74,125-byte full
  response of lfsa_urgacob/Y15-74/T (the LFS questionnaire's own
  UNEMPLOYMENT RATES BY COUNTRY OF BIRTH — the collector door the v25
  probe found, the v17 registry's "future Destin door" settled at the
  collector tier): 4,444 non-empty cells -> 3,023 records across the
  four birth classes {natives, foreign_born, eu_born, non_eu_born},
  segment_axis="birth", 36 printing geos, 1995-2025 (the class
  tables' 31-year memory), the TOTAL/NRP cells dropping logged. The
  anchors: FR 2015 natives 9.4 / foreign_born 17.1 / eu_born 10.7 /
  non_eu_born 19.0 — the Destin contrast at the aggregate level.
- `eurostat_lfsa_urgan_t_sample.json` — the REAL 80,356-byte full
  response of lfsa_urgan/Y15-74/T (unemployment rates by CITIZENSHIP,
  the étrangers face): 4,187 cells -> 2,710 records across
  {nationals, foreigners, eu_foreigners, non_eu_foreigners},
  segment_axis="citizenship", 35 geos, 1995-2025, the TOTAL/STLS/NRP
  drops logged. The anchors: FR 2015 nationals 9.7 / foreigners 20.5 /
  eu_foreigners 12.6 / non_eu_foreigners 24.5 — the de-facto Destin
  board. The UK rides (lost to une_rt_a at Brexit).
- `eurostat_unert_m_sample.json` / `eurostat_unert_f_sample.json` —
  the REAL 11,616/11,636-byte full responses of the une_rt_a M/F doors
  (the v17 registry's "one ref away" by-sex ventilations of the plain
  rate): 635 cells -> 584 records each, sex="male"/"female". The
  anchors: FR 2015 M = 10.8 / F = 9.9 (the v17 probe anchors, now
  wired), FR 2024 M = 7.6 / F = 7.3.
- `ilostat_cct_sample.json` / `ilostat_cbr_sample.json` — the REAL
  1,691,847/1,902,954-byte FULL flow responses on the ILO's own SDMX
  wire (the wired key `.A.UNE_DEAP_RT..AGE_AGGREGATE_YGE15.`), as the
  API served them the day of the v25 probe: the class cross-sections
  the 2026-09-24 restructure left (CCT 822 records = 411 nationals +
  411 foreigners over 137 areas; CBR 867 records over 145 areas), both
  sexes' rows, OBS_STATUS U/B riding quality_code, the KOS->XKX quirk
  (CCT Kosovo 2024 rides; CBR Kosovo prints the pre-independence 2000
  rows the entity's valid_from floor drops honestly), the TOTAL/X
  class drops logged. The anchors: FR 2025 CCT nationals 7.162 /
  foreigners 13.902 (M 12.961 / F 15.058); CBR natives 7.023 /
  foreign_born 12.003 (M 11.245 / F 12.846). The flow's own odd
  Italian vintage rides as-reported (ITA 2001 ~ 73.8-78.5 every
  class — the outlier the widened plausible bound documents).
- `itf_10p4veh_sample.csv` — the REAL 65,269-byte FULL response of
  DF_SAFETY/FATALITIES/10P4VEH_MOT_ROAD (the ITF per-vehicle face,
  Todd's own 1974 denominator — the v19 registry's "one config line
  away" taken): 534 rows, 38 areas, 1994-2024 the union window with
  the heterogeneous per-area arrival. The anchors: FRA 2010 = 0.9497
  -> 2024 = 0.6512, CHE 1994 = 1.6303 the longest series' start, CHL
  1998 = 13.1494 the slice's own tail; the USA ABSENT (the IRTAD
  questionnaire never carried the US vehicle-registration series).
