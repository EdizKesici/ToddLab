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
