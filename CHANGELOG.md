# Changelog

All notable changes to this repo are listed here, most recent first. Free-
form, suited to tracking an in-progress conversational project rather than
formal Git version tags.

House rules (adopted with v8; past entries are vintages — never edited
after the fact, corrections land in a new entry):
- An entry carries a vX label if and only if that delivery produced a
  reviewable artifact (zip/patch); otherwise it is date-only.
- Recurring sections: Context (the why, incl. decisions taken in
  conversation), Investigated (live findings that justify the change),
  Added, Changed, Fixed, Verified (live numbers, frozen at delivery
  time), Known limitations. One-off named sections are allowed when an
  entry carries a distinct sub-project (e.g. the P1b spike).
- Contract-breaking changes get a bold "Breaking" line right under the
  entry title; additive contract changes are noted as such in Verified.
- The numbers in an entry are frozen at delivery time (docs/
  the-measurement-problem.md carries the current state).

## 2026-09-22 — v22: the by-origin face — the bilateral
## decomposition of immigration_stock (THE Todd question, the book's own
## table shape), the OECD migration questionnaire's matrix as its
## witness, and the vanished origins admitted on the birth-place axis

**No dist contract break (additive, one indicator):** the 27 other
indicator files are byte-identical; immigration_stock.json keeps every
pre-existing key bit-identical (the 557-point (entity, year) data, the
UN DESA witness series, the todd_refs block) modulo the designed
additions — 31 new sources[] entries (30 Eurostat ROW doors + the OECD
witness) and the `bilateral` layer: 91,230 canonical points on 6,282
(destination x origin) pairs, 30 destinations x 243 origins, 1998-2025,
plus the OECD witness series (99,225 points, 38 destinations, 236
origins, 1995-2024). entities.json gains exactly one record
(netherlands_antilles, iso3 ANT) and four iso3 field changes (ussr SUN,
czechoslovakia CSK, yugoslavia_sfr YUG, serbia_and_montenegro SCG —
the withdrawn codes, declared). catalog.json moves only
immigration_stock's roots summary (canonical eurostat_migr doors 1 ->
31; witness +oecd_mig). todd_corpus.json is BIT-IDENTICAL: v22 adds a
FACE to an existing indicator, the corpus stays 24/24 with zero flips
(the v21 discipline).

### Context

Ediz re-uploaded ToddLab_v21.zip (the session-loss #4 recovery: the
workspace had reverted to the v16 era, the v20 base was re-certified,
the v22 probes ran and the design froze — see the v22 design dossier in
scripts/v22_probe/, Task 33 of the worklog) with the instruction to run
the wiring start to finish ("Tu peux déjà te lancer dans la v22 en
attendant la review de la v21"; the zip arrived as "la V21
(non-review)"). The base was extracted and certified (341/341, the v21
changelog on top) and the wiring ran on it exactly as designed, probes
already complete: the by-origin matrix of immigration_stock — the shape
of Le Destin des immigrés' own boards ("the stock of
Moroccans/Turks/Portuguese IN France/Germany/UK"), the door the project
recorded as "THE TODD BY-ORIGIN QUESTION, RECORDED AS THE FUTURE DOOR"
since v18.

### Investigated (live, before any wiring — the v22 probe record)

- **The Eurostat bilateral face (probe A):** migr_pop3ctb with geo
  pinned, c_birth UNPINNED = the FULL bilateral row of a destination in
  one 33 KB call (FR: 1,450 non-empty cells, 1998-2025, the 307-code
  by-birth codelist of which 243 are country codes). The v18 anchors
  disambiguated: the BIRTH face prints FR<-MA 2015 = 954,742 (v18's
  "MA 2015 = 458,561" was the CITIZENSHIP face, migr_pop1ctz — two
  legalities of the same stock, now recorded in the config's notes).
  The door's own arithmetic: NAT + FOR = TOTAL to the unit every year.
- **The UN DESA matrix (probe B):** still no wire (the dataportal = net
  migration only, the pages 404) — the witness tier does not need it.
- **The OECD finding (probes C+D):** the SDMX registry carries 16
  migration dataflows, among them DSD_MIG_F@DF_MIG_POPF ("International
  migration database - stocks of foreign-born population", OECD.ELS.IMD)
  — the questionnaire's own bilateral matrix, REF_AREA x BIRTH_COUNTRY,
  both axes ISO3. The flow serves ONLY through the empty-key /all
  download (positional keys 404 — the observation dimension carries
  TIME): 197,570 rows / 18.2 MB, already the pinned frame (MEASURE=B14
  only, FREQ=A only, PS only), SEX _T + F. THE SEAM, verified to the
  unit: OECD FR<-MAR _T 2015 = 954,742 = the Eurostat c_birth print
  EXACTLY (2018 = 992,120 both sides); the OECD face EXTENDS the FR
  Maghreb series past the Eurostat 2018 cutoff (2019 = 1,009,605,
  2021 = 1,036,133) and carries the world's non-European destinations
  (US<-MEX 12,383,868 in 2024, US<-W 51,226,993) the Eurostat universe
  structurally cannot print.
- **The wiring's own finding (the fetch):** 14 of the codelist's 44
  country geos print ONLY their totals on the by-origin face (DE, EL,
  MT, ME, MD, MK, GE, AL, RS, UA, AD, MC, AM, AZ — Germany's row
  carries 184 cells, every one an aggregate or a FOR/NAT/TOTAL/UNK
  summary code, ZERO country origins) — the registration's own honest
  absence, the same class as Ukraine's zero cells on the FOR door;
  those doors stay unwired, recorded in the config's notes.
- **The origin-axis codelist surprises:** Eurostat prints AN (the
  Netherlands Antilles' withdrawn alpha-2) as a birth place (FR<-AN
  1999 = 78, 2005 = 450); the OECD prints the _F vanished-entity codes
  (ANT_F "Former Netherlands Antilles", CSK_F, SCG_F, SUN_F, YUG_F)
  and XKV (its own Kosovo code) — plus the residual vocabulary (W,
  W_X "World unspecified", EEA, EU15, A4 "Caribbean", STLS
  "Stateless"), each decoded live from the DSD's codelist.

### Added

- **The `bilateral` dist layer** (the additive contract): destination
  x origin x year points shaped {destination_entity_id,
  origin_entity_id, year, value, provider, source_ref} + its own
  witness series — emitted ONLY when the indicator's processed tree
  carries by-origin points, so every single-axis indicator's dist file
  stays byte-identical (the honest absence of the layer is itself the
  additivity guarantee, pinned by the v18-era integration test).
- **The Eurostat ROW grammar** (migr_pop3ctb/ROW/{geo}): geo pinned in
  the URL, c_birth deliberately UNPINNED; the frame pins (age=TOTAL,
  sex=T, unit=NR) verified by the layout guard; the general row-major
  position decode (c_birth and geo sit at different strides than the
  pinned-c_birth layout the historical arithmetic assumed); the three
  drop classes logged per class (aggregates/regions, the
  FOR/NAT/TOTAL/OTH/UNK/RNC summary codes, the c_birth == geo
  diagonal — the native face); the origin axis resolved through the
  shared override tables (EL/UK/XK ride the geo table, AN rides the
  new origin table).
- **The OECD DF_MIG_POPF grammar** (the bare-flow ref, the empty-key
  /all download): the frame pins hard-verified per row (FREQ=A,
  MEASURE=B14, BIRTH_PLACE=_Z, EDUCATION_LEV=_Z, UNIT=PS — the flow's
  whole vocabulary); the SEX split (_T kept, F dropped logged — the
  by-sex face recorded unwired); the residual vocabulary dropped
  logged per code; the origin overrides (XKV -> XKX, the _F codes ->
  their withdrawn ISO3).
- **The pipeline's bilateral plumbing**: normalize routes the origin
  axis (RawRecord.origin_raw_name/origin_iso3_raw — additive fields)
  to a separate layer written {id}.bilateral.json (always, the
  stale-file discipline); merge arbitrates under the (destination,
  origin, year, sex) key with the same two rules verbatim; validate
  checks the layer's own plausible bounds, duplicates and coverage;
  build emits the dist layer with its own citations; stats prints the
  matrix's counts (the numbers this entry quotes).
- **The origin-axis covers_year exemption**, documented in code: a
  stock point's year is the MEASUREMENT year, never the birth year —
  people born in the former Netherlands Antilles are counted in the
  2015 stock exactly as both questionnaires print them; the
  destination axis keeps the guard.
- **The netherlands_antilles entity** (iso3 ANT, valid_to 2010, the
  two successors) and the withdrawn ISO3 declarations on ussr (SUN),
  czechoslovakia (CSK), yugoslavia_sfr (YUG), serbia_and_montenegro
  (SCG) — the by-origin face of the v21 vanished-entity admission
  (the kosovo/XKX precedent: a withdrawn code declared on the entity
  the ISO3-first resolution lands on).
- **The oecd_mig root** (the OECD migration questionnaire's matrix —
  the IMD's own foreign-born face, OECD-compiled) and the DF_MIG_POPF
  title read live from the SDMX registry.
- **Tests: 341 -> 361** (+10 Eurostat ROW, +9 OECD MIGF, +1 the
  bilateral end-to-end integration, +1 v18-era test extended with the
  additivity pin), the fixtures GENERATED live (the v16 discipline:
  every anchor READ from the response bytes, never typed — the FR row
  response whole, the OECD CSV a byte-copied slice of the /all
  download carrying every drop class and override code).

### Verified (live, frozen at delivery time)

- Fetch: 31/31 sources, 0 failures (30 ROW doors + the OECD /all
  download — 18.2 MB, 99,225 records after the sex split and the
  drops).
- Rebuild + verify_v22_diff.py: **53 PASS / 0 FAIL** — the 27 other
  indicator files byte-identical; immigration_stock's pre-existing
  keys bit-identical; entities.json exactly +1 record and 4 iso3
  flips; catalog.json one entry's roots summary; todd_corpus.json
  byte-identical; double rebuild deterministic.
- Stats v22: bilateral canonical 91,230 points = 91,230 valued + 0
  explicit gaps; 6,282 pairs; 30 destinations x 243 origins;
  1998-2025. The FR row: 226 country origins (FR<-DZ 1999 =
  1,246,706 -> 2018 = 1,390,284, FR<-MA 2015 = 954,742, FR<-PT 2025 =
  599,492); the Maghreb/Turkey slices ride the census rounds and stop
  at 2018 for FR (the coverage cliff, as-printed); the UK row prints
  1998-2004. The witness: 99,225 points, 7,684 pairs, 38 destinations
  (the USA's row: 210 origins), 236 origins, 1995-2024 — the seam
  (FR<-MAR 2015 = 954,742 on BOTH doors), the extension (2019-2021),
  the world face (US<-MEX 2024 = 12,383,867.87), the vanished origins
  (CSK/SUN/YUG/SCG/ANT/XKX all landed on their entities). The 11 other
  counters unchanged; corpus 24/24.

### Known limitations

- The by-sex face of both doors stays unwired (recorded: the Eurostat
  M/F sex doors, the OECD F rows dropped logged); same for the age
  bands (Eurostat) and the citizenship face (migr_pop1ctz +
  DSD_MIG@DF_MIG — both DSDs documented in sources.yaml).
- The UN DESA bilateral matrix (the world face's own compilation)
  remains manual-download; the OECD matrix carries the non-European
  destinations in its place.
- The OWID US-by-CoB historical chart (1850+, the census-era US face
  of exactly Todd's table class) is recorded as the US historical
  face's future door.
- The 14 total-only geos (above) stay unwired until the day they
  print; the day one starts, its fetch fails loudly (the soft-miss
  guard doubles as the change detector).

## 2026-09-25 — v24: the by-sex face — the M/F ventilations of the two
## migration matrices wired on BOTH faces (Ediz's approved direction),
## the OECD F rows un-blocked instead of re-downloaded, and the whole
## face riding the SAME bilateral layers under the merge key's own sex
## term

**No dist contract break (additive, one indicator):** the 27 other
indicator files, entities.json and todd_corpus.json are byte-identical
to the v23 commit; catalog.json moves only immigration_stock's roots
summary (canonical eurostat_migr doors 65 -> 189 — the +124 by-sex ROW
doors; the OECD witness doors unchanged at 2). immigration_stock.json
keeps every pre-existing key bit-identical (the 557-point (entity,
year) data, the UN DESA witness, the todd_refs block, the 68 v23-era
sources[] entries, and — the v24 contract's own heart — every
sex=None point of both bilateral layers and every _T point of both
OECD witnesses) modulo the designed additions: 124 new sources[]
entries (the M/F ROW doors, priorities 69-192) and the by-sex points
themselves — birth +182,478 canonical (M 91,249 + F 91,229),
citizenship +219,720 (M 109,906 + F 109,814), the B14 witness +94,952
female points (the flow's F rows kept), the B15 witness +101,829 (the
V23 pull's 104,009 rows un-blocked). Layer totals: bilateral 273,708
canonical / 194,177 witness; bilateral_citizenship 331,778 / 211,592.

### Context

Ediz pre-approved the direction and asked for the launch without
waiting ("Ediz a donné son feu vert et demandé à lancer la V24 sans
attendre davantage"): the by-sex face of the migration matrix — the
M/F ventilations of the SAME rows on both faces, the OECD F rows
already in the V23 pull to be un-blocked rather than re-downloaded.
The detailed design was frozen AFTER the probes (the §9 protocol),
then executed with the v23 method.

### Investigated (live, before any wiring — the v24 probe record)

- **The Eurostat ventilations (probes A-B, all 64 wired doors x 2
  sexes):** the M/F rows print on the SAME frame as the _T doors —
  FR birth M: 1,220 records / F: 1,219; FR ctz M/F: 714 each; the
  M/F perimeter = the _T perimeter minus CROATIA (29/30 birth, 33/34
  ctz — HR prints the _T detail but NO ventilation, the honest
  absence, unwired and recorded). THE ARITHMETIC, verified to the unit
  on every probed anchor: M + F = the _T print exactly (FR<-MA birth
  2015: 479,354 + 475,388 = 954,742; ctz: 231,893 + 226,668 =
  458,561; FR<-PT both faces; 2018 likewise) — the disaggregation is
  the registration's own, not a derivation.
- **The OECD F faces (probes C-D):** the flows print NO male face —
  their whole vocabulary is _T + F (B14: 100,944 + 96,570 data rows;
  B15: 112,111 + 104,009), the female face beside the both-sexes face,
  verified live on the full downloads. THE SEAMS, verified to the
  unit: B14's F print agrees with the Eurostat birth-face F doors
  (FR<-MAR F 2015 = 475,388 on both sides; 2018 = 499,397; FR<-PRT F
  2015 = 316,815), B15's with the ctz F doors (226,668 / 243,044 /
  252,472) — the questionnaire pair agreeing on the ventilated face
  exactly as it agrees on the both-sexes face. US<-MEX F 2024 =
  3,752,511 (the B14 F face carrying no US<-MEX row at all — the
  as-printed shape, documented). After the drop vocabulary: B14 F
  94,952 points (38 x 236, 1995-2024), B15 F 101,829 (35 x 236).

### Added

- **The by-sex face on the SAME bilateral layers**: the M/F points
  ride `bilateral` and `bilateral_citizenship` under the merge key's
  own fourth term — (destination, origin, year, SEX) — the component
  the v22 key carried as None until now (the base.py docstring's own
  "the sex-split doors, when ever wired, coexist without colliding"
  anticipation, landed). No new layer, no new key space: a
  (destination, origin, year) that prints on all three sexes exists
  three times, once per sex, M + F = _T the arithmetic the layer now
  displays.
- **The Eurostat ROW-SEX grammar** `migr_pop{3ctb,1ctz}/ROW/{geo}/
  {sex}` (sex in {M, F} — four segments with parts[1] == "ROW", a
  reserved position the pre-v22 pinned grammar's c_birth can never
  print): the same frame pins with the sex pin swapped, the same drop
  classes, the same origin-axis routing; records carry sex="male"/
  "female" through the shared _UNE_RT_A_SEX_TO_PROJECT table.
- **The OECD F rows un-blocked**: parse_migf_csv and parse_mig_csv now
  KEEP the F rows (sex="female") instead of dropping them logged —
  "débloquer plutôt que re-télécharger" read literally: no new door,
  no new download shape, the SAME single pull serving both faces (the
  re-fetch is the routine snapshot refresh; the F rows never lived in
  the snapshots, only in the responses). The M row guard stays loud:
  the flows print no male face, an M row is a door change, a human
  decides.
- **The config**: 124 doors (29 birth M + 29 birth F, priorities
  69-126; 33 ctz M + 33 ctz F, priorities 127-192 — HR unwired on
  both faces, recorded) — 192 sources total on the indicator, the
  targeted fetch's own count. Catalog: eurostat_migr 65 -> 189 doors.
- **Tests: 384 -> 391** (+1 build_url M/F, +3 the ROW-SEX grammar
  refusals, +1 the birth M fixture's anchors (M+F=_T arithmetic), +1
  the ctz F fixture's anchors (the OECD seam), +1 the by-sex
  end-to-end integration; four v22/v23-era tests extended — the
  door counts 65 -> 189, the witness maps keyed by the merge key's
  sex component, the OECD fixture counts re-read with the F rows
  kept). The fixtures GENERATED live (scripts/make_v24_fixtures.py:
  the FR M row of the birth face at 1,220 records, the FR F row of
  the citizenship face at 714 — every anchor read from the response
  bytes).
- **scripts/v24_probe.py** and **scripts/verify_v24_diff.py** (the
  four probes and the 27-check delivery verification, committed with
  the code).

### Changed

- config/sources.yaml, README, docs/architecture.md: the by-sex face
  now WIRED (the "by-sex (both doors)" unwired record resolved); the
  no-male-face OECD shape documented; the remaining unwired faces
  re-listed (the age bands, the single-axis ctz total door, the DESA
  matrix, the OWID US historical chart).

### Verified (live, frozen at delivery time)

- Fetch ciblé: 192/192 sources, 0 failures (the 124 new M/F doors +
  the 68 v23 doors re-fetched, the two OECD matrices included — the
  snapshots now carrying the F records).
- Rebuild ×2 + verify_v24_diff.py: **27 PASS / 0 FAIL** — the 27 other
  files byte-identical to the v23 commit; every pre-existing point of
  both layers and both witnesses bit-identical; the by-sex counts
  exact (91,249/91,229/109,906/109,814 canonical; 94,952/101,829
  witness); M+F=_T to the unit on the six anchor pairs; the F seams on
  both matrices; the vanished origins carrying their ventilations
  (Eurostat M/F, OECD female); HR's honest absence; double rebuild
  deterministic (31/31 md5); corpus 24/24; `cli check-config` OK.
- Stats v24: bilateral (by-origin) 273,708 points on 6,306 pairs; the
  witness 194,177; bilateral (by-citizenship) 331,778 on 6,627 pairs;
  the witness 211,592. The 11 other counters unchanged.
- Tests: 391/391.

### Known limitations

- The OECD matrices print NO male face (verified live on both full
  downloads — the flows' whole vocabulary is _T + F): the by-sex
  witness coverage is female-only, the honest as-printed shape; the
  male face lives on the Eurostat canonical doors only.
- Croatia prints the _T by-origin detail but NO M/F ventilation on
  either face — the by-sex doors stay unwired, recorded; the day they
  print, their fetch fails loudly.
- The age bands (Eurostat migr_pop's own dimension) stay unwired,
  recorded; same for the single-axis ctz foreigners-total door, the
  DESA bilateral matrix (manual-download), and the OWID US-by-CoB
  historical chart.

## 2026-09-25 — v23: the citizenship face — the bilateral decomposition's
## LEGAL twin (étrangers vs immigrés, the two boards of Le Destin des
## immigrés), the OECD questionnaire's B15 matrix as its witness, and the
## two faces carried as PARALLEL layers, never merged (ADR-0010)

**No dist contract break (additive, one indicator):** the 27 other
indicator files are byte-identical to the v22 commit EXCEPT ONE
DESIGNED PROVIDER REVISION — illegitimate_births carries exactly one
re-point (Moldova 2022: 18.3 -> 18.2, the collector's own rounding
correction re-read live twice, flagged to Ediz; see Fixed);
entities.json, todd_corpus.json are byte-identical; catalog.json moves
only immigration_stock's roots summary (canonical eurostat_migr doors
31 -> 65; witness +oecd_mig doors 1 -> 2). immigration_stock.json keeps
every pre-existing key bit-identical (the 557-point (entity, year)
data, the UN DESA witness, the todd_refs block, the 33 pre-existing
sources[] entries, the whole `bilateral` birth layer — 91,230 canonical
points + the B14 witness 99,225) modulo the designed additions: 35 new
sources[] entries (34 migr_pop1ctz ROW doors + the OECD DF_MIG/B15
witness) and the `bilateral_citizenship` layer — 112,058 canonical
points on 6,627 (destination x origin) pairs, 34 destinations x 226
origins, 1998-2025, plus the OECD B15 witness series (109,763 points,
36 destinations, 236 origins, 1995-2024).

### Context

The fifth session-loss recovery, and the cleanest: the GitHub repo
itself was the base (HEAD at a7cd073, the V22 commit — the delivery
this entry follows). The session re-fetched the FULL raw tree live (169
sources at the v22 config — the v18 recovery pattern), rebuilt, and
certified the dist against the GitHub state before any v23 work began:
30 of 31 files bit-for-bit, the one exception the Moldova rounding
revision above (investigated live: the Eurostat API prints 18.2 today,
the v22 snapshot had printed 18.3 — a provider revision between the
deliveries, surfaced not buried). On that certified base the v23 design
(the frozen dossier of the lost session, re-verified anchor by anchor
before any wiring) executed in the probe-wire-verify order.

### Investigated (live, before any wiring — the v23 probe record)

- **The Eurostat citizenship face (probes A-C):** migr_pop1ctz/ROW/FR
  answers 26,577 bytes, 927 non-empty cells, the SAME frame pins as the
  birth face (age=TOTAL, sex=T, unit=NR — the only unit) and the same
  layout with `citizen` in c_birth's stride. The 287-code by-citizenship
  codelist: 226 country codes + NAT/RNC/TOTAL/OTH/UNK summary + STLS
  stateless + 55 aggregates/regions (each class dropped logged). THE
  v18 ANCHORS, landed on the face they always belonged to: FR<-MA ctz
  2015-2018 = 458,561/465,230/472,843/480,600 — the "MA 2015 =
  458,561" of the v18 probe record was the citizenship print all
  along, re-read live exact. FR<-PT ctz 2015 = 541,867.
- **The face's own geography (probe D, all 44 candidate geos):** 34
  destinations print the by-citizenship detail — GERMANY JOINS (6,400
  cells, 5,498 country cells — the citizenship questionnaire carries
  what the birth questionnaire's honest absence never printed) while
  CYPRUS LEAVES (222 cells, every one an aggregate or summary); EL/ME/
  MD/AD join as census cross-sections; the sums over the 34 doors:
  112,058 country cells, 6,627 pairs, 226 origins, 1998-2025 — every
  anchor exact. The asymmetry is the registration's own shape, never
  "corrected".
- **The OECD finding (probe E):** the SIBLING flow the v22 record kept
  unwired at "CITIZENSHIP at position 2" is DSD_MIG@DF_MIG, and it is
  the ACCESS MIRROR of the B14 quirk — it REFUSES the empty-key /all
  download but SERVES the positional wildcard key '..A.B15.._Z._Z.PS':
  18,435,034 bytes / 216,120 data rows in ONE call, the frame pins
  (FREQ=A, MEASURE=B15, BIRTH_PLACE=_Z, EDUCATION_LEV=_Z,
  UNIT_MEASURE=PS) hard-verified per row with ZERO violations. SEX
  carries _T (112,111) + F (104,009 — the V24 hook, drop logged).
  THE DROP-VOCABULARY ARITHMETIC, read live and exact: 112,111 _T rows
  - STLS 455 - W 832 - W_X 397 - EEA 115 - EU15 210 - A4 114 -
  diagonal 225 = 109,763 points on 236 origins x 36 destinations,
  1995-2024 — the vanished-entity codes (XKV, the _F prints) are KEPT
  and mapped onto their withdrawn ISO3 entities (the same admission as
  the birth face), the residual vocabulary drops logged per class. THE
  SEAM, verified to the unit: OECD FR<-MAR _T 2015 = 458,561 = the
  Eurostat ctz print EXACTLY (2016-2018 both sides); the world face
  US<-MEX 2024 = 8,226,106 (citizenship) vs 12,383,868 (birth) — the
  two faces diverging naturally on the pair the naturalization gap
  widens.
- **TWO PROMPT DIVERGENCES, investigated and flagged to Ediz (never
  silently adapted):** (1) the frozen design's §5.4 contrast anchor
  carried its face labels SWAPPED — live reads settle it: 648,112 is
  the BIRTH face of FR<-PT 2015 (Eurostat and OECD B14 agreeing to the
  unit), 541,867 the CITIZENSHIP face; the CONVERGE story itself is
  real and rides the corrected labels everywhere in this entry and the
  config. (2) the frozen design's §3 drop list named the
  vanished-entity codes as "always dropped" — the anchors' own
  arithmetic (109,763/236 OECD, 112,058/226 Eurostat) proves the
  OPPOSITE treatment: the codes are kept and mapped, the v22 discipline
  verbatim; the §3 sentence is the memory slip of a residual list (the
  actual drops: STLS/W/W_X/EEA/EU15/A4). The repo's structural truth
  and the anchors win; both divergences are flagged in the delivery
  message.

### Added

- **The `bilateral_citizenship` dist layer** (ADR-0010): the LEGAL twin
  of the by-origin face — the stock of FOREIGN CITIZENS (étrangers) by
  nationality, in mirror of the birth face's foreign-born (immigrés).
  PARALLEL, never merged: separate normalized/merged/witnesses files,
  the same (destination, origin, year, sex) merge key in separate key
  spaces, its own dist block with its own witnesses. A pair printing on
  both faces exists TWICE (FR<-MA 2015: 954,742 born in `bilateral`,
  458,561 citizens in `bilateral_citizenship`) — the divergence IS the
  display.
- **`RawRecord.origin_axis`** (additive field): "birth" |
  "citizenship" | None — the routing key normalize reads (None and
  "birth" keep the v22 routing, so pre-v23 snapshots rebuild
  bit-identically); stamped by the connectors (migr_pop3ctb ROW and
  DF_MIG_POPF -> birth; migr_pop1ctz ROW and DF_MIG/B15 ->
  citizenship).
- **The shared Eurostat ROW grammar** `migr_pop{3ctb,1ctz}/ROW/{geo}`:
  one regex, the DATASET capture choosing the origin dimension
  (c_birth vs citizen), the layout (both verified live), the pins and
  the dist layer; the citizenship face's own drop class — STLS
  (stateless), logged; the 4-segment pinned-citizen grammar REFUSED
  (the single-axis ctz door stays unwired, recorded in sources.yaml).
- **The OECD DF_MIG/B15 grammar**: the keyed wildcard
  '..A.B15.._Z._Z.PS' (the access mirror), the frame pins per row, the
  SEX split (the 104,009 F rows drop logged — the V24 hook), the
  residual drops per class (STLS/W/W_X/EEA/EU15/A4 + the NAT/TOTAL/UNK
  guard, 0 rows live), the vanished-entity mapping (shared override
  table), origin_axis="citizenship".
- **The pipeline plumbing for the second layer**: normalize routes on
  origin_axis and always writes both layer files (stale-file
  discipline); merge's bilateral block extracted and parameterized
  (one helper, two calls — v22 behavior byte-identical, provenance
  entries self-describing with layer labels); validate's bilateral
  checks per layer; build emits the block with its own citations (the
  ctz door's citation carries the citizenship questionnaire's own API
  title, the B15 entry the registry's own flow title, both read live);
  stats prints both faces' lines.
- **The config**: 34 migr_pop1ctz ROW doors (priorities 34-67, the
  birth-face order minus CY plus DE/EL/ME/MD/AD) + the OECD DF_MIG/B15
  witness (priority 68) — 68 doors total on the indicator, the
  targeted fetch's own count. Catalog: eurostat_migr 31 -> 65 doors,
  oecd_mig 1 -> 2.
- **ADR-0010** (the parallel-faces decision, the §3 requirement: no
  prior ADR covered it) and the fixtures' README entries.
- **Tests: 361 -> 384** (+11 Eurostat ctz ROW incl. the shared-grammar
  routing pin, +10 OECD B15, +1 the origin_axis routing test with the
  pre-v23 bit-compat guarantee, +1 the citizenship end-to-end
  integration; two v22-era tests extended — the doors-count and the
  additivity pins), the fixtures GENERATED live
  (scripts/make_v23_fixtures.py: the FR ctz row whole at 927 cells,
  the B15 slice at 16,285 lines = 8,283 _T + 8,002 F — the frozen
  design's own anchor, reproduced exactly, every drop class and
  override code riding).
- **scripts/v23_probe.py** and **scripts/verify_v23_diff.py** (the
  five probes and the 33-check delivery verification, committed with
  the code).

### Changed

- config/sources.yaml: the migration blocks rewritten — the
  citizenship face now WIRED on both providers (the sibling-flow note
  resolved), the two flows' access-mirror relationship documented, the
  remaining unwired faces re-listed (by-sex — the V24 hook, age bands,
  the single-axis ctz total door, the DESA matrix, the OWID US
  historical chart).
- README and docs/architecture.md: the migration sections carry the
  citizenship face (the two-boards story, the anchors, the
  asymmetry).

### Fixed

- **The GHO MDG_0000000001 door change (a provider-side recoding
  caught by the recovery fetch):** the live payload now prints
  Dim2=AGEGROUP_MONTHS0-11 on every one of its 39,279 COUNTRY rows (at
  v22 the rows rode Dim2-less; the Indicator metadata still declares
  Dim2Type null, out of sync with the data). The YEARSALL default
  would have refused the WHOLE payload as age slices. Verified live
  before any fix: the 39,210 dist-point keys all present with ZERO
  value divergence, the 69 extra rows all Kosovo pre-2008 (dropped by
  the entity validity guard, the same rows the v22 build dropped). The
  fix is the v20 per-code AGE PIN applied to a door change:
  MDG_0000000001 pinned to AGEGROUP_MONTHS0-11 (one deliberate line,
  the loud-guard discipline kept — a future re-coding is a door change
  again, a human decides). The rebuilt infant_mortality.json is
  byte-identical through the pin; a live-generated fixture
  (gho_mdg_0000000001_sample.json) replaces the WHOSIS-shape seeding.
- **One provider data revision, surfaced not buried:** Moldova 2022 on
  NMARPCT prints 18.2 today (verified twice: the fresh snapshot and a
  direct API call, no status flag) where the v22 dist carried 18.3 — a
  Eurostat rounding correction between 2026-09-22 and 2026-09-25. The
  rebuild carries the live print; the verify script pins the exact
  one-point diff so the revision is reviewable in the commit itself.
  Flagged to Ediz.

### Verified (live, frozen at delivery time)

- Fetch ciblé: 68/68 sources, 0 failures (the 34 new ctz doors + the
  33 existing doors re-fetched + the B15 keyed download — 18.4 MB in
  one call).
- Rebuild ×2 + verify_v23_diff.py: **33 PASS / 0 FAIL** — the 26 other
  indicator files byte-identical to the v22 commit; the Moldova
  one-point revision pinned exactly; entities/todd_corpus
  byte-identical; catalog one entry's roots summary; the pre-existing
  keys and the whole birth layer bit-identical; the citizenship
  layer's anchors exact; double rebuild deterministic (31/31 md5).
- Stats v23: bilateral (by-citizenship) canonical 112,058 points =
  112,058 valued + 0 explicit gaps; 6,627 pairs; 34 destinations x 226
  origins; 1998-2025. The witness: 109,763 points, 7,247 pairs, 36
  destinations, 236 origins, 1995-2024 — the seam (FR<-MAR 2015 =
  458,561 on BOTH doors), the world face (US<-MEX 2024 = 8,226,106
  citizens vs the birth face's 12,383,868), the vanished origins
  (XKX/ANT/CSK/SCG/SUN/YUG all landed on their entities). The 11 other
  counters unchanged; corpus 24/24; `cli check-config` OK.
- Tests: 384/384.

### Known limitations

- The by-sex face of all four doors stays unwired (recorded: the
  Eurostat M/F sex doors; the OECD B14 F rows and B15's 104,009 F rows
  drop logged — the V24 hook, already downloaded, un-blocking beats
  re-fetching).
- The two faces' coverage differs (34 vs 30 Eurostat destinations; the
  witness pair 36 vs 38 OECD destinations) — the asymmetry is carried
  as-printed, explained wherever the pair is displayed; a derived
  "naturalization gap" product would be a derivation, deliberately out
  of scope (the ADR-0010 accepted cost).
- The single-axis ctz foreigners-total door (migr_pop1ctz/FOR-class
  pins) stays unwired, recorded in sources.yaml; same for the age
  bands, the DESA bilateral matrix (manual-download), and the OWID
  US-by-CoB historical chart.
- ERRATUM V21, kept noted (the tally was not re-edited by this
  version): the v21 tally prints +285 witness points; the corrected
  value is +267 — the GHO Kosovo rows 2002-2007 were rejected by a
  valid_from=2008 bound, 18 rows overcounted. The corrected Kosovo
  arithmetic now prints through the live GHO door change: the
  MDG_0000000001 payload carries exactly 69 Kosovo rows, all
  pre-2008, all dropped by the same guard (the honest count behind
  both numbers).


## 2026-09-22 — v21: the entities version — the DYB 1978
## vanished-entity tables (the PDF route the XLS loop cannot reach), the
## Byelorussian and Ukrainian SSR admitted as the UN's own member rows,
## and the Kosovo resolution (XKX, the user-assigned code)

**No dist contract break (additive, data-only):** the 28 existing
indicator files keep every pre-existing key bit-identical; the designed
additions are exactly +72 canonical points (17 IMR + 27 CBR + 12 LE —
the vanished entities — and 12 + 4 Kosovo on the Eurostat collectors)
and +285 witness points, every single one of them Kosovo (verified
entity-by-entity). entities.json gains exactly two records
(byelorussian_ssr, ukrainian_ssr) and one field change
(kosovo.iso3 None -> "XKX"). todd_corpus.json is BIT-IDENTICAL: v21
adds data to existing indicators, the corpus stays 24/24 with zero
flips. catalog.json moves only n_points / n_witness_points, the
coverage_declared starts (1974 / 1971), and the roots door-counts
(unsd_dyb 13 -> 14: the curated door joins its own collector root).

### Context

Ediz approved v19 and v20 in one message ("C'est tout bon pour la v19
et v20 ! Tu peux continuer !") — the corpus-closing version and the
inequality pair both passed review, and with the backlog empty the
roadmap question became depth, not count. The first pending decision
on the list since v1 was the vanished entities (USSR, Czechoslovakia,
Yugoslavia SFR, the GDR, the two Yemens): the P1b spike's recommended
route was the curated gate, and the probe material (the DYB 1978 PDF,
24 MB, on disk since that spike) was already in the workspace. The
session started with a THIRD base loss (the local tree back at v16,
the GitHub still at v17); Ediz re-uploaded ToddLab_v20.zip, the tree
was restored, verified (328/328, rebuild bit-identical against the
shipped dist), and the probe ran BEFORE any wiring (the probes-before-
code discipline).

### Investigated (live, before any config)

- **The DYB 1978 inventory (the probe's own bug-reports included):**
  every table zone was located by its printed title, then every
  vanished-entity row re-found by pattern — the probe's first pass
  MISSED the Soviet rows because the UNION OF SOVIET SOCIALIST
  REPUBLICS section prints bare "USSR" / "Byelorussian SSR" /
  "Ukrainian SSR" (not the long form the patterns carried), a lesson
  recorded in the probe before the extraction was trusted.
- **The harvest:** Table 9 (live births + CBR 1974-1978) prints the
  full Total rows for Czechoslovakia (19.9 -> 18.4 per 1,000, counts
  291,800 -> 278,250), the GDR (10.6 -> 13.9 — the post-1976
  pronatalist climb, counts 179,127 -> 232,151), Yugoslavia (18.1 ->
  17.4) and the three Soviet UN seats: the USSR itself (18.0/18.1/
  18.4/18.1 over 1974-1977, 4,546,095 -> 4,693,369 live births), the
  Byelorussian SSR (15.8/15.7/15.7/15.8) and the Ukrainian SSR
  (15.2/15.1/15.2/14.7). Table 15 (infant deaths + IMR 1974-1978):
  Czechoslovakia 20.5 -> 18.7, the GDR 15.9 -> 13.2, Yugoslavia 40.9
  -> 33.6 (counts 15,666 -> 12,811), and the three Soviet seats'
  single pre-blackout 1974 rows: USSR 27.7 (125,908 deaths — the
  known institutional carrier), BySSR 16.6 (2,443), UkSSR 19.2
  (14,136). Table 4 (the latest-year vitals + LE at birth): every
  entity's LE pair printed with its own reference period — the USSR
  1971-1972 M 64 / F 74 (the union-level print of the founding
  claim's era, integer precision), BySSR 1970-1971 68/76, UkSSR
  67/74, Czechoslovakia 1976 66.99/74.05, the GDR 1976 68.82/74.42,
  Yugoslavia 1970-1972 65.42/70.22. Table 22 corroborates the three
  European LE pairs at their age-0 column, byte-for-byte.
- **THE CROSS-CHECK MATRIX (every extracted value, before any CSV):**
  Table 15's count over Table 15's rate reproduces Table 9's births
  within 0.4% on all fifteen CSK/GDR/YUG year-pairs (e.g. Yugoslavia
  1974: 15,666/40.9*1000 = 383,032 vs 382,947 printed); Table 4's
  latest-year CBR equals Table 9's rate for that year on all six
  entities; Table 4's IMR equals Table 15's; Table 4's LE equals
  Table 22's age-0. The generator script refuses to write a CSV if
  any cross-check fails, and every decoded value is verified present
  in its raw text-layer line (the v16 anchor discipline applied to
  the catalog itself: READ, never typed).
- **THE YEMEN GATE (the probe protecting the tier boundary):** the
  two Yemen entities print in Tables 4 and 9 (CBR 48.7 / 48.2, LE M/F
  37.3/38.7 and 40.6/42.4, "1970-1975") — but the rows carry
  footnote 4: "Estimate(s) for 1970-1975 prepared by the Population
  Division of the United Nations." UN PD estimates are the WPP
  family: WITNESS-class by the project's constitution, never
  canonical. The Yemen rows are EXCLUDED from the curated tables —
  the two entities remain declared-but-data-less, the negative
  finding documented in sources.yaml.
- **The Kosovo question (pending since the v1 audit):** the WB prints
  countryiso3code XKX on its Kosovo rows; Eurostat prints geo XK on
  demo_find (NMARPCT carries 16 rows 2002-2021, TOTFERRT 4 rows
  2016-2019 — the collector's own Kosovo TFR series); both are the
  SAME user-assigned code (the XK prefix is reserved for user
  assignment under ISO 3166-1). Resolution: the kosovo entity carries
  iso3 XKX (it had null), the Eurostat override table gains XK -> XKX
  — both collectors' doors land on one entity, pre-2008 rows still
  refuse on valid_from. The Channel Islands (CHI, 66 rows on every WB
  witness) stay the documented permanent class: a WB-specific grouping
  of two crown dependencies, no Todd relevance, no invented entity.

### Added

- **The three DYB 1978 curated tables (the PDF route):**
  `dyb1978_vanished_infant_mortality.csv` (17 points: CSK/YUG/GDR
  1974-1978 + the two SSR single 1974 rows), `dyb1978_vanished_crude_
  birth_rate.csv` (27 points: the six entities, the USSR 1974-1977
  union prints included), `dyb1978_vanished_life_expectancy.csv` (12
  points: the six entities x male/female, the year = the printed
  period's END year, the period string riding reference_range).
  Root: unsd_dyb on all three — the DATA's origin is the collector's
  own 1978 print; the curator only transcribes (the same genealogy
  rule that keeps the ussr IMR table on soviet_official, its own
  origin). Every row's citation names the table and the printed
  counts; every Soviet row's note carries the live-birth definition
  (Table 9 fn 37 / Table 15 fn 33); every GDR row carries the Berlin
  footnote (fn 24); the '*' prints ride provisional=true; the row
  code C rides quality_code.
- **The curated CSV format's v21 extension (additive):** four
  optional transcription columns — sex, provisional, quality_code,
  reference_range — mirroring RawRecord one-to-one; both headers
  accepted (legacy 5-column, extended 9-column), anything else is a
  parse error; the duplicate key gains sex (a male/female pair on one
  year is legitimate, twice the same sex is the collision it always
  was); sex accepts exactly male/female, provisional exactly
  true/false — loud failures on anything else.
- **The two SSR entities:** byelorussian_ssr and ukrainian_ssr
  (1922-1991, successors belarus/ukraine, the UN's own printed names
  as their un_dyb overrides). THE DECISION the 1978 tables settle:
  the USSR, BySSR and UkSSR were three distinct UN MEMBER seats —
  the collector prints each its own rows, so the as-reported
  principle carries them as three entities. The successors' own
  continuous (witness-attached) series never collide with the SSR
  prints: distinct entity ids, the merge key is (entity, year, sex).
- **The Kosovo resolution:** kosovo.iso3 = XKX + the Eurostat
  override XK -> XKX. Canonical landings: illegitimate_births +12
  (2008-2021, the NMARPCT gaps of 2013/2014 honest), birth_rate_
  fertility +4 (2016-2019: 1.66/1.65/1.61/1.55 — the collector's
  Kosovo TFR, the fertility slide as-reported). Witness landings:
  +285 points across the ten WB-witness indicators, every one
  Kosovo (valued on the five data-carrying doors, explicit gaps on
  the five where the WB prints Kosovo rows without values — the
  witness contract's own "no value stays one gap point" rule).
- 13 tests (328 -> 341): 8 curated-format (the extended header, the
  loud validations, the sex-aware duplicate key, the real tables
  against the real registry with covers_year), 4 entity (the SSR
  records, the XKX resolution, the DYB 1978 printed names), 1
  integration (the vanished entities end-to-end: the five IMR rows
  with their markers and notes, the four CBR series, the six LE
  pairs with the reference_range, the corpus untouched at 24/24).

### Changed

- The three indicator configs gain their curated source at the top
  of the canonical block (IMR p2 behind the official Soviet series,
  CBR and LE p1 — the earliest data), the DYB loop renumbered behind
  them (priorities are NOT part of the dist contract — verified:
  zero provenance change, the sources' order in the dist files is
  the only visible move, plus the new curated entry).
- coverage_declared: crude_birth_rate 2007 -> 1974, life_expectancy
  2007 -> 1971 (the curated tables predate the XLS loop; the v5-era
  review lesson — declared coverage must track the real floor).
- The ussr entity's note: the "future source" it waited for is the
  1978 print itself — the union now carries CBR and LE beside the
  official IMR series.
- The two Eurostat slices carrying XK rows re-fetched (the v20
  snapshots had frozen iso3_raw=None at their parse time; the
  override only applies at parse — the counts identical: 2069 +
  1892 records, the live data unchanged).

### Fixed

- Nothing inherited: the v19 and v20 reviews both came back clean.
- The session's own bug-reports, fixed before they could land: the
  probe's missed Soviet rows (bare "USSR" name forms), the staging
  script re-staging an already-rebuilt dist as its baseline (caught
  by the entities diff showing 260 instead of 258 — the pristine
  baseline re-extracted from the shipped zip before the verify ran).

### Verified (live numbers, frozen at delivery)

- Fetch: 5/5 targeted (3 curated network-free + the two Eurostat
  slices), 0 failures.
- Rebuild + verify_v21_diff.py: **199 PASS / 0 FAIL** — the 28
  indicators keep every pre-existing point bit-identical with exactly
  the designed additions; entities.json = +2 records + kosovo.iso3;
  todd_corpus.json bit-identical (24/24, zero flips); catalog.json
  moves only the designed fields; double rebuild deterministic.
- Stats: infant_mortality 2,702 -> 2,719 canonical (curated 38 = 21
  official + 17 vanished); crude_birth_rate 3,319 -> 3,346 (curated
  27, the USSR union's own CBR prints); life_expectancy 6,018 ->
  6,030 (curated 12, sex-split); illegitimate_births 2,144 -> 2,156
  (Kosovo 2008-2021); birth_rate_fertility 1,953 -> 1,957 (Kosovo
  TFR 2016-2019). Spot-checks from the dist: the founding claim's
  union-level print (USSR 1971-1972: M 64 / F 74 — the ten-year gap
  at union level, the RSFSR-specific 12-13 year gap of the books
  living on the successor's series); the Yugoslav IMR halving
  40.9 -> 33.6 in five years; the GDR's pronatalist CBR climb
  10.6 -> 13.9 over the same window; Kosovo TFR 1.66 -> 1.55.
- Tests: 341/341.

### Known limitations

- The vanished entities live on ONE edition: the DYB 1978 prints
  five years (1974-1978) of CBR/IMR and one LE print per entity —
  the PDF route is a cross-section, not a loop; earlier editions
  (1975, 1976, 1977...) would extend the windows one print at a
  time, each needing its own text-layer verification pass.
- The USSR/SSR IMR prints stop at 1974 (the publication blackout
  1976-1987, exactly the territory the official curated series
  already covers 1970-1990); the SSR entities carry exactly one IMR
  point each, their 1975+ story living in the successor republics'
  witness-attached series.
- The two Yemens remain data-less (the Population Division estimate
  gate); the Channel Islands remain the documented permanent
  unresolved class; the pre-2008 Kosovo rows refuse on valid_from
  (2002-2007 on NMARPCT, 2001 on the WB witness).
- The URSS/SSR LE prints are integer-precision on Table 4 (64/74,
  68/76, 67/74) — the print's own precision, carried as-reported;
  the European pairs print two decimals.

## 2026-09-22 — v20: the queue claimed whole — incarceration_rate (La
## Défaite's six-country board on the ICPR World Prison Brief's chart
## door, the UNODC collector portal a client-rendered SPA with no
## machine door), math_test_scores (L'illusion économique's TIMSS table
## read through the OECD's modern face — the PISA chart door, the SDMX
## registry carrying no PISA dataflow), obesity_rate (the NCD-RisC
## pooled analysis on WHO GHO's OWN wire, the per-code AGE pin's first
## door), hiv_prevalence_rate (the UNAIDS chart door — aidsinfo a SPA,
## api.unaids.org DNS-dead), and male_height_trend (the NCD-RisC 2016
## birth-cohort compilation + the Baten-Blum/Clio-Infra cross-root
## witness) — the five-indicator final delivery, THE CORPUS-CLOSING
## VERSION, 19 -> 24 of 24

**No dist contract break (purely additive):** the twenty-three existing
indicators keep every pre-existing key bit-identical (verified
key-by-key, 57/57 checks); the dist gains exactly five new indicator
files, five catalog entries, the designed corpus flips (implemented
19 -> 24 — ALL of them, the backlog empty for the first time), and the
registry's seven new roots (icpr_wpb, who_prisons, oecd_pisa,
ncd_risc_bmi, unaids, ncd_risc_height, baten_blum — 31 at the
registry). One new Family value (education — the corpus's own
vocabulary for the assessed-learning reads, math_test_scores its first
indicator) and one new grammar pin (the GHO connector's per-code AGE
pin — see Added). No new provider: PROVIDER_LAYER unchanged, every new
door rides an existing provider (owid ×5, who_gho ×2). No designed
value change.

### Context

Ediz green-lit V20 while his V19 review is still pending ("OK, en
attendant la review de la V19, tu peux déjà commencer la V20") — the
max-parallel cadence now spanning reviews. The v19 exit note had
proposed the queue option (d): finish the five remaining metrics in
ONE version, the corpus at 24/24; the standing max-parallel mandate
and Ediz's go settled it — v20 is THE QUEUE VERSION, the delivery that
closes todd_core.csv's universe. Five probe tracks ran before a single
line of wiring (scripts/v20_probe/), all verdicts below read from the
live APIs 2026-09-22. The v19 state was intact in the working repo
this time (no recovery preamble needed — the first session since v16
to start from the previous delivery's tree verbatim).

### Investigated (live, before any config)

(A) INCARCERATION — the collector-tier question answered honestly
negative: UNODC's dataunodc.un.org (the penal-system questionnaire
collector, the natural canonical) is a client-rendered SPA — every
datareport page returns the same 44KB shell, the Drupal settings carry
no data API, and no machine door surfaced in any probed shape (the
record in scripts/v20_probe/probe_v20_unodc.py + prison_probe.log).
The World Prison Brief's own site answers 404 on /api (prisonstudies
.org serves HTML country pages only). The machine face of the
compilation the field reads is OWID's chart door: prison-population-
rate, 225 entities, 1993-2026, "Number of prisoners, including
pre-trial and remand detainees, per 100,000 people" (the chart's own
subtitle), attribution read live from the chart metadata: "Institute
for Crime & Justice Policy Research (2026) ... 'World Prison Brief'
[original data]" — the same door-relation oecd_family (v16) and wid
(v19) hold. THE WITNESS the probes surfaced: GHO's PRISON_A2_
PRISIONERS_PER100KPOP — the WHO Health in Prisons database, the
European prison-health questionnaire collection, printing a 36-country
cross-section at its own single 2020 vintage (FRA 93.1, DEU 69.7, GBR
129.8, GEO 245.99 the post-Soviet European top) — the coupe pattern
(RS_198 v19, SA_0000001457 v18) on a genuinely cross-root door. The
sub-national faces recorded: the door carries the UK's constituent
parts (England & Wales, Scotland, Northern Ireland) and BiH's entities
as separate rows — they resolve to no registry entity and drop logged,
the honest OWID-door discipline.

(B) MATH — the assessment seam: Todd's own table is TIMSS 8th-grade
(L'illusion économique, "OECD source" — the corpus's own words), and
TIMSS has NO machine door (zero hit in OWID's full saved sitemap, no
IEA API). The OECD SDMX registry (the full live listing saved at v19)
carries NO PISA dataflow — the education flows there are REG_EDU
(regional attainment) and TALIS (teacher surveys). The OECD's modern
machine face is the chart door: average-performance-of-15-year-olds-
in-mathematics-reading-and-science, 90 entities, the mathematics
column (the CSV's own header "Mathematics" — the field pin), the seven
cycles 2003-2022, attribution read live: "OECD (2023) ... 'PISA
Database' [original data]". The by-sex sibling chart is the same root
(auto-witness refused, registered); the World Bank's harmonized
learning scores are a derived composite (refused by the anti-derivation
line — the extrapolations precedent); TIMSS registered as the future
door. NO WITNESS — canonical-alone, the top_income_share precedent.
The door's own shape documented: the 2000 cycle prints reading-only
rows (PISA 2000's major domain) — the math column arrives as explicit
gap points, 41 of them on the live slice; Russia prints six cycles
2003-2018 and is ABSENT from 2022 (the cycle it did not sit).

(C) OBESITY — the first GHO-CANONICAL indicator, and the grammar find
that came with it: NO collector prints an obesity prevalence anywhere
(the WB probe: SH.STA.OBES/.ZS/SN.ITK.OBES all answer the empty
message — recorded). The origin tier is the NCD-RisC adult BMI pooled
analysis REPUBLISHED BY WHO GHO as the NCD_BMI_* family — and the GHO
API is the provider's own machine wire: NCD_BMI_30C (the crude 18+
face, 199 countries, 1980-2024, FULL SEX SPLIT, 26,865 COUNTRY rows).
THE GRAMMAR: unlike SDGSUICIDE (age slices beside an all-ages row),
NCD_BMI_30C carries Dim2 = AGEGROUP_YEARS18-PLUS on EVERY row — the
door's single population face — which the YEARSALL rule would have
refused wholesale: the connector gained a per-code AGE pin (a pinned
code accepts exactly its frame, anything else raises; unpinned codes
keep the YEARSALL grammar bit-identical). THE SAME-ROOT RELATION
verified at the byte level: the OWID chart door (share-of-adults-
defined-as-obese, attribution "World Health Organization - Global
Health Observatory (2026)" read live) prints the IDENTICAL series —
FRA 2024 = 12.524594 on both doors, USA 41.830319/41.83032, JPN
5.1900275/5.1900277 — the chart IS this door's redistribution, an
auto-witness refused with its own bit-identity as the evidence. The
age-standardized sibling (NCD_BMI_30A) registered non-wired (the
standardization seam).

(D) HIV — the compilation the corpus names ("WHO/UNAIDS-style data")
with its direct machine door CLOSED: aidsinfo.unaids.org is a
client-rendered SPA (21KB shell, /api 404), kbase/api.unaids.org are
DNS-dead. The machine face is the OWID chart door: share-of-the-
population-infected-with-hiv, 161 entities, 1990-2024, attribution
read live: "Joint United Nations Programme on HIV/AIDS (2026) ...
'Global AIDS Update, Epidemic Indicators' [original data]" — the wid
door relation. THE COVERAGE FINDING, verified TWICE: the compilation's
own country universe excludes the USA, Russia and China — the GHO
redistribution (MDG_0000000029, 145 areas) is absent of exactly the
same three, so the exclusion is the UNAIDS reporting shape itself, not
a door artifact (the regional aggregate that carries them, "Western &
Central Europe and North America (UNAIDS)", drops logged). The
same-root doors refused as auto-witnesses and registered: the GHO
MDG_0000000029 print (1-decimal — FRA 2024 = 0.3 vs the door's
0.28482) and the WB SH.DYN.AIDS code, whose own metadata READ LIVE
names it "Adults (ages 15+) living with HIV" — the COUNT face (FRA
2023 = 180,000). The cross-root family (IHME GBD) re-confirmed behind
OWID's 403 on the unaids-vs-ihme chart, verbatim the v1 record. NO
WITNESS — canonical-alone.

(E) HEIGHT — two compilations, one cross-root pair: the NCD-RisC 2016
eLife "century of trends" (1,472 studies re-analyzed, mean height AT
AGE 18 BY BIRTH COHORT, 200 entities, 1896-1996) through the chart
door average-height-of-men (single column, attribution "NCD Risk
Factor Collaboration (2016)" read live; ncdrisc.org's own downloads
page carries only the 2020 child/adolescent study files today — read
live, the adult 2016 eLife files no longer listed, the chart IS the
wire); and the Baten & Blum (2015) compilation through Clio-Infra's
"Biological Standards of Living" (the economic-history record —
militia rolls, army recruits: 153 entities, 1550-2000, sparse by
nature) as the CROSS-ROOT WITNESS, the barro_lee relation (the
cm-level seams on the overlapping cohorts displayed never reconciled;
the pre-1896 tail carried on the witness tier alone). The sibling
Men+Women chart refused as the same-root auto-witness (the Women
column registered as the future door). THE FRAMING SEAMS drawn and
documented: birth-cohort years vs Todd's calendar years, age 18 vs
the book's 20-year-olds — displayed, never reconciled. The probe
artifact honestly kept: the Baten-Blum door prints the DRC under the
name "Congo, DRC" with NO ISO3 code — 11 witness points drop logged
(the possible_mapping_gap bucket, the report the record; the same
pending class the Channel Islands hold).

### Added

- src/schema/indicator.py: the registry's SEVEN new roots (31 total),
  each with its live-verified registry comment — icpr_wpb (the
  compilation canonical by necessity, the consanguinity_studies
  constitution), who_prisons (the prison-health questionnaire
  collection), oecd_pisa (the assessment's own scores through the
  chart door — the OECD runs the survey, no SDMX wire), ncd_risc_bmi
  (the pooled analysis on the provider's own wire), unaids (the
  Global AIDS Update estimates through the chart door),
  ncd_risc_height (the 2016 eLife birth-cohort compilation), and
  baten_blum (the Clio-Infra historical record). The Family enum
  gains `education` — the corpus's own vocabulary, its first
  indicator math_test_scores.
- src/connectors/gho.py: THE PER-CODE AGE PIN (_CODE_AGE_PIN) — a door
  whose every row carries one age frame (NCD_BMI_30C: YEARS18-PLUS,
  read live on the full 28,350-row slice) declares that frame in the
  table; a pinned code accepts exactly it and raises on anything else
  (a door change stops the parse, never silently re-interpreted);
  unpinned codes keep the YEARSALL drop-the-slices grammar
  bit-identical (SDGSUICIDE's 17 tests untouched). parse_gho gains the
  optional code kwarg (fetch_raw forwards source_ref — the pin applies
  in production exactly as in tests); the loop's country-code local
  renamed (spatial) so the two codes never shadow each other — the
  collision itself caught by the fixture validation during the
  session, the probe scripts kept as the record.
- config/indicators/incarceration_rate.yaml — the twentieth indicator
  (3 citations, 3 books): canonical = the ICPR World Prison Brief
  through the OWID chart door (prison-population-rate, 225 entities,
  1993-2026, per 100k, pre-trial included), reliability medium (a
  compilation canonical by necessity — no collector wire anywhere),
  plausible 0-1800 (SLV 2024 = 1,659 the estado-de-excepción
  calibrator; a raw count or per-million print flags immediately);
  witness = the GHO PRISON_A2 coupe (36 European countries at the
  2020 vintage).
- config/indicators/math_test_scores.yaml — the twenty-first (3
  citations, the education family's first): canonical = the OECD PISA
  mathematics mean through the chart door with field=Mathematics (the
  CSV's own header — the pin, 90 entities, 2003-2022), reliability
  high (the assessment's own scores, the OECD the collector), plausible
  300-650 (QAT 2006 = 317.96 the floor, SGP 2022 = 574.66 the
  ceiling; a percentage, rank, or doubled scale flags); witnesses:
  NONE — the honest absence, the TIMSS seam and the refused composite
  documented in the config's own block.
- config/indicators/obesity_rate.yaml — the twenty-second (3
  citations): canonical = GHO NCD_BMI_30C on the provider's own wire
  (the crude 18+ face, 199 countries, 1980-2024, full sex split —
  the first GHO-canonical indicator, the per-code AGE pin's own
  door), reliability medium (a modeled-estimates canonical by
  necessity — the top_income_share constitution), plausible 0-90
  (ASM women 2024 = 80.89 the Pacific tail; a fraction read or a BMI
  mean flags); witnesses: NONE — the OWID chart's bit-identity the
  auto-witness refusal's own evidence.
- config/indicators/hiv_prevalence_rate.yaml — the twenty-third (1
  citation): canonical = the UNAIDS prevalence through the OWID chart
  door (161 entities, 1990-2024, % of 15-49), reliability medium
  (modeled central estimates by necessity), plausible 0-40 (ZWE 1995
  = 29.65 the epidemic's own peak); witnesses: NONE — the same-root
  doors and the 403 family documented.
- config/indicators/male_height_trend.yaml — the TWENTY-FOURTH, THE
  CLOSING METRIC (1 citation): canonical = the NCD-RisC birth-cohort
  compilation through the chart door (200 entities, 1896-1996, cm),
  reliability high (two independent compilations agreeing at the cm
  level), plausible 145-190 (both doors' spans: LAO 1896 = 152.88 to
  NLD 1985 = 182.57, Baten-Blum PNG 152.36 to DNK 183.2); witness =
  the Baten-Blum/Clio-Infra door (the pre-1896 tail on the witness
  tier — the barro_lee relation).
- tests/conftest.py: seed_gho_snapshot forwards the code to the parser
  (exactly as fetch_raw does — the AGE pin applies in tests too);
  the v20 seed block in test_pipeline_integration.py's _run_pipeline.
- Seven fixtures GENERATED from the live APIs through the connectors'
  own build_url (scripts/make_v20_fixtures.py — the v19 discipline:
  anchors READ, never typed): the five OWID chart-door carves
  (prison 118/2,272 rows — the Todd six-country board whole; PISA
  61/496; HIV 179/5,514 including the aggregate rows the parser
  drops logged; height 178/21,008; Baten-Blum 88/1,499) and the two
  GHO carves (NCD_BMI_30C 96+4 rows with the full sex split; PRISON_A2
  11/36 — the coupe's own anchored subset).

### Changed

- Nothing pre-existing: the twenty-three old indicator files, catalog
  entries and entities.json are bit-identical (verify_v20_diff 57/57);
  the GHO connector's unpinned path keeps its exact public behavior
  (SDGSUICIDE's tests untouched), the code kwarg optional and
  backward-compatible.

### Fixed

- One shadowing bug caught by the fixture validation itself during
  the session (the v18/v19 lesson repeating, gladly): parse_gho's
  loop had reused the name `code` for the SpatialDim country code
  since v10 — the new code kwarg collided, the pin looked up "FRA"
  instead of "NCD_BMI_30C", and every row dropped as an "age slice"
  with a zero-rows error. The local renamed (spatial), the make_
  v20_fixtures validation the guard that caught it before any test
  was written.

### Verified (live, frozen at delivery 2026-09-22)

- Fetch: 7/7 doors, 0 failures (prison owid 2,272 records; the GHO
  prison coupe 36; PISA 496; obesity 26,865; HIV 5,514; height
  21,008; Baten-Blum 1,499).
- Tests: 314 -> 328 (+14: six GHO connector — the pin's acceptance,
  the unpinned refusal, the off-frame and Dim2-less sabotage guards,
  the coupe pass, the fetch_raw piping; three OWID connector — the
  field pin's anchors, the multi-variable refusal, the typo'd-field
  guard; five integration — the ICPR door + coupe, the PISA canonical-
  alone with its 2000 gaps, the GHO canonical-alone with its sex
  split, the UNAIDS canonical-alone with its universe limits, the
  NCD-RisC + Baten-Blum pair). 328/328 at packaging.
- Rebuild + verify_v20_diff.py: 57/57 PASS / 0 FAIL — the twenty-three
  old indicators bit-identical, catalog +5 exactly (old entries
  identical), entities.json identical, corpus = exactly the five
  designed flips (19 -> 24) and the backlog EMPTY, double rebuild
  deterministic (31 dist files byte-stable).
- Stats dist: incarceration_rate canonical 2,207 points, 220
  entities, 1993-2026 (the door's 225 minus the five UK/BiH
  sub-national faces, dropped logged); witness coupe 36 points, 36
  entities, 2020. math_test_scores canonical 480 points = 439 valued
  + 41 explicit gaps (the 2000 reading-only rows — the door's own
  shape), 88 entities, 2003-2022. obesity_rate canonical 26,865
  points, 199 entities, 1980-2024, the sex split riding the canonical
  tier itself. hiv_prevalence_rate canonical 5,199 points, 152
  entities, 1990-2024 (161 minus the World and eight UNAIDS regional
  aggregates, dropped logged). male_height_trend canonical 20,200
  points, 200 entities, 1896-1996; witness 1,488 points, 152
  entities, 1550-2000 (the pre-1896 tail the canonical cannot carry).
- The Todd anchors print themselves: the Défaite six-country board —
  USA 683 (2000) -> 542 (2023), RUSSIA 729 -> 300 (the two carceral
  worlds the book sets against each other), FRANCE 82 -> 126 (the Qui
  est Charlie ? écroués arc's stock face), GERMANY 85 -> 71, JAPAN
  48 -> 33, UK 121 -> 139; the French PISA slide 510.8 (2003) ->
  473.9 (2022) with the American 482.9 -> 464.9 beside it; the
  health-paradox pair USA 41.8 vs FRANCE 12.5 (2024) with the
  American female-over-male inversion (43.0/40.6) and Japan's lean
  5.2; the patrilineal belt — ZWE peaking 29.65 (1995), SWZ 23.4,
  ZAF 17.2 (2024); and the height arcs — FRANCE birth-1896 = 166.41
  -> birth-1996 = 179.74 (+13.3cm, the book's +10cm printing bigger),
  KOR +15.2 the compilation's biggest gain, NLD 182.57 the tallest.

### Known limitations

- incarceration_rate: a compilation canonical (no collector wire —
  the UNODC SPA record); L'illusion économique's US number is the
  total correctional population (probation and parole included, ~3x
  the stock — the book's own note); the écroués flow vs the detention
  stock seam documented; the pre-1993 faces and the 1970s French
  series are BOOK data (curated territory); the witness carries 36
  European countries at one vintage (no trend, no USA/RUS/JPN); the
  UK sub-national faces (England & Wales etc.) drop logged.
- math_test_scores: the TIMSS-vs-PISA assessment seam (two frames,
  one metric family — Todd's own table is TIMSS, the machine door is
  PISA 15-year-olds); the 2000 cycle's reading-only rows arrive as 41
  explicit gaps; Russia absent from 2022; the by-sex faces, the
  reading/science columns, and TIMSS itself registered as future
  doors; no witness tier.
- obesity_rate: a modeled-estimates canonical (the pooled analysis'
  confidence intervals dropped at parse with every GHO door — the
  standing record); the crude-vs-age-standardized seam (NCD_BMI_30A
  registered non-wired); the book's college-educated face is survey
  microdata, curated territory; no witness tier (the same-root
  absence, its bit-identity the evidence).
- hiv_prevalence_rate: the compilation's own universe excludes the
  USA, Russia and China (verified on both redistributions — the
  UNAIDS reporting shape); the corpus's own women-15-49 face lives
  behind the closed aidsinfo door (registered); no witness tier (the
  403 family re-confirmed).
- male_height_trend: the birth-cohort vs calendar-year and age-18 vs
  age-20 framing seams (documented, never reconciled); the 1996+
  cohorts live behind the 2020 child/adolescent study (a different
  publication, registered); the Women column registered (no corpus
  metric demands it); the Baten-Blum DRC rows print under a name the
  registry doesn't carry ("Congo, DRC", no ISO3 — 11 witness points
  dropped logged, the pending class); the witness is sparse by nature.
- THE CORPUS IS CLOSED (24/24): the implemented share's own roadmap
  is empty — the "what to build next" question the corpus made
  a data statement in v13 now answers itself. The registered future
  doors (per-vehicle road deaths, the WID percentile vocabulary, the
  by-origin migration matrix, the by-sex PISA and HIV faces, the
  1996+ height cohorts, TIMSS, NCD_BMI_30A...) and the curated
  territories (the 19th-century boards, the book tables) remain the
  recorded expansion space — depth, not corpus count.

## 2026-09-22 — v19: the inequality pair and the road — top_income_share
## (the backlog's head claimed through WID's chart door, the corpus's own
## named source), gini_index (the OECD IDD's four-door vintage stitch, the
## 1995 table's lineage), and road_accident_mortality (Le Fou et le
## Prolétaire's metric on the ITF/IRTAD wire) — the three-indicator
## parallel delivery, corpus 16 -> 19 of 24

**No dist contract break (purely additive):** the twenty existing
indicators keep every pre-existing key bit-identical (verified
key-by-key, 52/52 checks); the dist gains exactly three new indicator
files, three catalog entries, the designed corpus flips (implemented
16 -> 19), and the registry's four new roots (wid, oecd_idd, itf_irtad,
who_roadsafety). No new provider enum, no new Family value — the OECD
connector's THIRD and FOURTH dataflows arrive instead (the eurostat
v18 precedent: one connector, several datasets, one grammar + pin guard
per dataset). No designed value change.

### Context
Ediz's v18 review landed "rien à corriger", with the standing
max-parallel mandate ("tu peux faire tout en parallèle (si tu en es
capable), sinon choisis celui que tu veux") still governing the
cadence. The v18 exit note had proposed four v19 candidates
(top_income_share, gini_index, road_accident_mortality, the curated
19th-century faces); the corpus-order house rule settles the first
three — they ARE the remaining backlog's head (7, 4 and 4 citations,
the three highest of the eight left) — and the curated historical
faces stay a recorded future door. One recovery preamble, the same
shape v18 itself needed: the local workspace had again rolled back
(worse this time — the working repo showed v16, not v17), but every
v18 artifact survived in download/ (zip + patch + the probe scripts);
the reviewed zip IS the authoritative state, so the repo was restored
by extracting ToddLab_v18.zip fresh (289 raw snapshots included), the
baseline re-verified (302/302), and the v18 dist staged bit-identical
for this entry's diff. The GitHub remote still sits at v17 (the v18
push is Ediz's, at his own cadence) — so this entry's patch is built
against the v18 zip extract, the delivery he reviewed.

### Investigated (live, before any config)
Four probe tracks, all run in parallel (scripts/v19_probe/), all
verdicts below read from the live APIs 2026-09-21/22:

(A) WID.World — the corpus NAMES the source for La Défaite de
l'Occident's own board ("Russia/USA/France, WID data", pre-tax top 1%
and next 9%). The direct machine door is CLOSED from this environment:
api.wid.world answers 403 CloudFront on every extractor shape probed
(GET query-string, POST form, POST raw, browser headers — the endpoint
the R/Stata packages ride), the new portal's country pages are
WordPress views carrying no data files, and the old bulk-download path
is gone (404). The machine-readable face is OWID's chart door:
incomes-of-the-richest, 165 entities, 1820-2024, single clean column
"Share (richest 1%, before tax)", the chart's own attribution read
live from its metadata: "WID.world (2026) - World Inequality
Database". The same door-relation oecd_family holds (v16). The
sibling extrapolations chart (income-share-top-1-before-tax-wid-
extrapolations, 227 entities) is the SAME root plus the provider's own
"(Projected)" column — refused by the anti-derivation line, never
wired. The Atkinson-Piketty historical chart OWID still carries
(declining-share-of-the-top-1..., 8 entities 1871-2019 — the Où en
sommes-nous ? six-country table) is ALSO WID-rooted now (the series
were folded in): a self-witness, not a cross-check — so
top_income_share stands canonical-ALONE, the secondary_education
precedent for the witness tier's honest absence (the OECD IDD's 35
measures, enumerated live, carry no top-fractile share).

(B) The OECD Income Distribution Database — the 1995 fifteen-country
table L'illusion économique read is this collection's lineage, and it
rides the SDMX wire as DSD_WISE_IDD@DF_IDD (OECD.WISE.INE): MEASURE=
INC_DISP_GINI, unit 0_TO_1, 45 areas, 1974-2025, RUS carried
2008-2017 (the RLMS survey window). THE GRAMMAR FINDING: the flow
prints the same (country, year) under METHODOLOGY x DEFINITION
vintages — METH2012 (the current computation) vs METH2011 (the
pre-revision history); D_CUR ("current definition") vs D_PREV
("previous definition - with overlap year") vs D_INC ("previous
definition - without overlap year"; labels read live from the DSD's
own CL_DEFINITION codelist). The stitching chain was SIMULATED on the
full live slice before any wiring: 906 (area, year) keys, zero
unresolved, D_CUR/M12 > D_PREV/M12 > D_INC/M12 > D_CUR/M2011
(649/10/61/186 wins; M2011-D_PREV never wins a key — not wired, the
minimal-chain discipline). France sews three times: 1996-2011 on
METH2011, 2011-2020 on METH2012-D_PREV, 2020-2023 on METH2012-D_CUR —
the OECD explorer's own chained display, made explicit. The WID gini
chart (gini-coefficient-wid, 165 entities 1820-2024, attribution
verified the same way) is the cross-root witness — a DIFFERENT income
concept (pre-tax national income vs equivalized disposable), the seam
displayed never reconciled: France 2022 = 0.299 disposable vs 0.4592
pre-tax, the redistribution IS the gap.

(C) The road — the ITF/IRTAD statistics ride the SDMX wire as
OECD.ITF DSD_INDICATORS@DF_SAFETY: police-reported crash registrations
as submitted, 55 areas, 1994-2025, THREE printed denominators (the
flow's own unit codelist read live): 10P5HB (per 100,000 population —
the family-consistent face, WIRED), 10P4VEH_MOT_ROAD (per 10,000
registered motor vehicles — the direct descendant of Todd's 1974 WHO
table denominator, registered non-wired), 10P9VEHKM (per billion
vehicle-km, registered non-wired). The count face rides a sibling
dataflow (DSD_ST@DF_STFAT, 53 areas, annual/monthly/quarterly rows —
FRA 2018 = 3,248 as counted, also registered non-wired). RUS is
absent from the ENTIRE ITF flow — zero rows across 1994-2025 on every
unit, verified on the full slice. The witness: GHO RS_198 ("Estimated
road traffic death rate (per 100 000 population)"), 197 countries at
the report's own single 2021 vintage (RUS 2021 = 10.6, FRA 4.7) — the
GHE-cirrhosis coupe pattern, one print not a series; the neighboring
RS_196 (counts) same single vintage, no multi-year series on the API
for this family, recorded.

(D) Two endpoint grammar lessons, both caught by the probes before any
code: the OECD SDMX data endpoint REFUSES "latest" as the version
token ("Invalid version string provided" — every flow reference
carries its explicit registry version), and the SDMX-CSV envelope is
uniform across providers (DATAFLOW,<flow-urn>,I,<area>,... — REF_AREA
at position 3 behind the three envelope columns, the shared walker's
existing skip rule handling the residue).

### Added
- src/connectors/oecd.py: THE THREE-FLOW CONNECTOR — DF_COM (v10,
  verbatim behavior, its 17 existing tests untouched), DF_IDD
  ('DF_IDD/{measure}/{methodology}/{definition}', 9 dimensions, the
  unit derived per-measure through a deliberate gate
  _IDD_UNIT_BY_MEASURE), DF_SAFETY ('DF_SAFETY/{measure}/{unit}', 8
  dimensions, TRANSPORT_MODE pinned ROAD, FREQ pinned A — the flow's
  monthly/quarterly rows never fetched). One shared SDMX-CSV walker
  (_walk_sdmx_csv) with a per-flow pin dict: trust the URL, verify
  the response — a row from any other slice (a METH2011 row under a
  D_CUR ref, a monthly row, a per-vehicle unit) is refused loudly,
  never ingested. Neither new flow carries a SEX dimension: every
  record sex=None, the flows' own shape.
- The registry's four new roots (schema/indicator.py, each with its
  live-verified registry comment): wid (the DINA research
  harmonization — CANONICAL for top_income_share by the
  consanguinity_studies constitution: no collector anywhere prints a
  top-fractile income share, the metric is by construction a
  constructed series, so the compilation the corpus names is the
  origin tier), oecd_idd (the national household surveys as
  submitted), itf_irtad (the police crash registrations), and
  who_roadsafety (the Global status report estimates — a DIFFERENT
  WHO family from who_ghe, its own methodology and vintage cadence).
  PROVIDER_LAYER unchanged: every new door rides an existing provider.
- OECD_DATAFLOW_TITLES + IDD_DEFINITION_LABELS (schema) and the
  per-flow citation dispatch (build.py): the IDD citation names the
  vintage each door carries ("current definition" vs the back-series
  variants); DF_COM's citation template is verbatim (bit-compat with
  every pre-v19 dist).
- config/indicators/top_income_share.yaml — the seventeenth
  indicator, the backlog's head (7 citations, 5 books): canonical =
  the WID pre-tax top-1% share through the OWID chart door
  (incomes-of-the-richest), reliability medium (a research
  compilation by necessity, displayed as what it is), plausible
  0-70 (the compilation's own tail: Malawi 1997 = 64.09), witnesses:
  NONE — the honest absence, the config's own comment block recording
  why (the IDD measure list, the refused extrapolations door).
- config/indicators/gini_index.yaml — the eighteenth indicator (4
  citations, 2 books): the FOUR-DOOR canonical chain (the NMARPCT
  quatuor pattern, applied to a methodology-definition seam instead of
  a geo seam) + the WID pre-tax witness (the concept seam: France 2022
  0.299 disposable vs 0.4592 pre-tax, never reconciled, displayed).
  Plausible 0-1: the Gini's own mathematical domain, the unit-error
  bound by construction.
- config/indicators/road_accident_mortality.yaml — the nineteenth
  indicator (4 citations, 1 book — all Le Fou et le Prolétaire):
  canonical = ITF FATALITIES/10P5HB (the per-100k family face, the
  choice documented against the per-vehicle door of Todd's own 1974
  table), witness = GHO RS_198 (the 2021 coupe). Plausible 0-35 (the
  registrations' own tail: LVA 1994 = 28.44 — the post-Soviet
  road-death crisis; LIE's honest zeros ride the floor).
- tests/conftest.py: seed_oecd_idd_snapshot + seed_oecd_safety_snapshot
  (the pins extracted from the source_ref like the production
  connector — a D_CUR seed REFUSES a D_PREV fixture row).
- Eight fixtures GENERATED from the live APIs through the connector's
  own build_url (scripts/v19_probe/make_v19_fixtures.py — the v16
  discipline: anchors READ, never typed): the four IDD vintage doors
  (oecd_idd_gini_cur/prevdef/incdef/m2011.csv — 88/12/4/103 anchored
  rows from the 649/19/61/421 live slices), the ITF road door
  (itf_safety_road_mortality.csv, 358 of 1,551), the two WID charts
  (owid_incomes_of_richest.csv + owid_gini_wid.csv, 558 rows each),
  and the GHO coupe (gho_road_mortality.json — 11 country rows + the
  7 non-COUNTRY rows the parser drops logged).

### Changed
- Nothing pre-existing: the twenty old indicator files, catalog
  entries and entities.json are bit-identical (verify_v19_diff 52/52);
  the DF_COM connector path kept its exact public surface (parse_
  sdmx_csv's signature and its 17 tests untouched, the walker
  refactor internal).

### Fixed
- Two TYPED ANCHORS caught by the tests themselves during the session
  (the v18 lesson repeating, gladly): FRA 2019 D_PREV guessed at 0.281
  (the door prints 0.292) and BRA 2006 D_INC copied from an unfiltered
  probe line (0.5039 — a row from another slice; the pinned door
  prints 0.50879539), plus RUS 2008 read off the full slice instead of
  the M2011 door (0.374 vs the door's 0.428). All three corrected
  against the fixtures' own bytes; the probe scripts remain the
  mistake's record.

### Verified (live, frozen at delivery 2026-09-22)
- Fetch: 8/8 doors, 0 failures (top_income owid 3,765 records; the
  four IDD doors 649/19/61/421; gini witness 3,765; road ITF 1,551;
  RS_198 197 country rows).
- Tests: 302 -> 314 (+12: nine connector — the URL pins, the vintage
  anchors, the sabotage guards on METHODOLOGY/DEFINITION/UNIT/AGE/
  FREQ/TRANSPORT_MODE/MEASURE, the shared body rules; three
  integration — the canonical-alone contract, the four-door stitch
  with its provenance seam assertions, the IRTAD print + coupe).
  314/314 at packaging.
- Rebuild + verify_v19_diff.py: 52/52 PASS / 0 FAIL — the twenty old
  indicators bit-identical, catalog +3 exactly, entities.json
  identical, corpus = exactly the three designed flips (16 -> 19),
  double rebuild deterministic (26 dist files byte-stable).
- Stats dist: top_income_share canonical 3,203 points = 3,203 valued +
  0 gap, 155 entities, 1820-2024 (the chart's 165 entities minus the
  ten aggregate/historical rows that resolve to nothing — World and
  the nine "… (WID)" regional aggregates, dropped logged, the OWID
  door's own discipline; GDR rides as its own entity); witnesses:
  none. gini_index canonical 906 points, 45 entities, 1974-2025 (the
  exact simulated key count — the chain's own arithmetic); witness WID
  3,203 points, 155 entities, 1820-2024. road_accident_mortality
  canonical 1,551 points, 55 entities, 1994-2025; witness RS_198 197
  entities at the single 2021 vintage (the coupe's own shape, every
  witness point 2021).
- The Todd anchors print themselves: USA 1913 = 20.43 -> 2024 = 20.73
  (the full U-shape), France 1910 = 22.73 -> 2022 = 12.1 (the
  Atkinson-Piketty arc, now INSIDE WID), Russia 1820-2017 in 46 points
  ending at the oligarchy's 20.0; USA 1995 = 0.361 (L'illusion
  économique's own year on the door's own series), the stitched France
  0.277 (1996, M11) -> 0.309 (2011, M12-D_PREV) -> 0.278 (2020,
  M12-D_CUR) -> 0.299 (2023); France 1994 = 15.2 -> 2024 = 4.7 road
  deaths, the USA 15.5 -> 12.2 (the never-halved divergence), LVA 1994
  = 28.44 the post-Soviet tail.

### Known limitations
- top_income_share: a single research compilation, canonical-alone (no
  cross-root machine witness exists — the probe record); the provider's
  pre-tax concept is a distributional-national-accounts construct; the
  "next 9%" of La Défaite's own table (p90p99) lives behind the blocked
  WID API — registered as the future door; the 19th-century tails are
  the compilation's own reconstructions (the layer judgment rides the
  root label).
- gini_index: 45 areas canonical (the world face rides the witness
  tier alone); the vintage seams are real series breaks (France 2011
  and 2020, Germany 2011, the USA 2013, the UK 2002) — carried
  honestly, every collision a logged provenance discard; no sex
  dimension (a household-distribution index); Russia's canonical
  window is the five survey points 2008-2017.
- road_accident_mortality: RUS absent from the whole ITF flow (the
  witness carries Russia's modeled 2021 face alone); the 1974
  thirteen-country table itself is BOOK data (curated territory, the
  same line the 19th-century boards hold); the per-vehicle denominator
  of Todd's own table is one registered door away (10P4VEH_MOT_ROAD,
  38 areas 1994-2024); the witness is a single-vintage cross-section —
  no trend on that tier.
- The remaining backlog, after nineteen of twenty-four: incarceration_
  rate 3, math_test_scores 3, obesity_rate 3, hiv_prevalence_rate 1,
  male_height_trend 1 — the corpus's tail, three of them at the same
  citation weight.

## 2026-09-21 — v18: the six-indicator delivery — the economy family's
## second and third (industrial and agricultural employment, the backlog's
## head claimed and the composite question dissolved), the education pair
## (tertiary and secondary, the LFS's third metric family), the migration
## door (immigration_stock, the demography family's first), and cirrhosis
## (the mortality family's fourth cause) — the everything-in-parallel version

**No dist contract break (purely additive):** the fourteen existing
indicators keep every pre-existing key bit-identical (verified
key-by-key); the dist gains exactly six new indicator files, six catalog
entries, the designed corpus flips (implemented 10 -> 16), and the
registry's five new roots (eurostat_na, ilo_modelled, barro_lee,
un_desa, eurostat_migr) plus the Family enum's `demography`. No designed
value change this time — not even a companion flip.

### Context

Ediz green-lit V18 with the maximal-parallelism challenge ("tu peux
faire tout en parallèle (si tu en est capable), sinon choisis celui que
tu veux") after a clean v17 review. The version therefore ran FOUR probe
tracks in parallel before a single line of wiring (scripts/v18_probe/,
five rounds): (A) the cirrhosis doors, (B) the industrial/agricultural
employment doors — the backlog's HEAD, deferred three times on the
composite-derived-layer question, (C) the education pair's doors, (D)
the immigration-stock doors. All four tracks returned before the wiring
began; the six metrics that follow are what the probes blessed.

A session-recovery note for the record: the v17 delivery had been built
outside this workspace's visible repo — the working tree sat at v16
while Ediz's GitHub carried v17. The v18 session recovered by syncing
the GitHub state into the working repo, re-fetching the two v17 network
raws + the curated snapshot live, and verifying that the rebuilt dist
reproduces the GitHub v17 dist BIT-FOR-BYTE (no provider revision
between the deliveries) before any v18 work began.

### Investigated (live, before any config)

- **industrial_employment_share (30 citations, 5 books — the backlog's
  head since v15):** the finding that earned the wiring is a
  CORRECTION of the project's own probe record. The v15/v16/v17
  deferral rested on "NO collector prints the % as-reported" — true of
  every door probed then (ILOSTAT counts, re-verified for v18: the
  73-flow EMP+ECO inventory shows every _RT flow is an
  informal-employment or employment-to-population rate, no plain
  sector-share print; the OECD doors are counts or OECD-harmonized;
  WB SL.IND.EMPL.ZS is ILOEST modeled), but the EU NATIONAL ACCOUNTS
  were never probed: nama_10_a10_e prints the share of total
  employment by industry DIRECTLY at unit PC_TOT_PER, na_item EMP_DC
  ("Total employment domestic concept"), nace_r2 B-E — the door's own
  aggregate, labeled "Industry (except construction)" (FR 1995 = 16.4
  -> 2024 = 10.1, DE 23.1 -> 17.5, 34 countries, the accounts' own
  'p' flags on the freshest years, verified live 2026-09-21). The
  composite-derived-layer ADR held in reserve since v15 is RETIRED
  UNUSED: no derivation is needed because the collector prints the
  share. The EA edge: this dataset's geo codelist carries the
  Euro-area aggregate as the bare TWO-LETTER code "EA" — the only
  two-letter aggregate in any wired Eurostat codelist — dropped logged
  by a per-dataset aggregate table. The DYB re-probe closed the
  historical door honestly: the DYB's economic-characteristic tables
  were dropped before the live XLS archive begins (the wired 2011-2024
  editions carry none; the archive's 2001-2006 editions carry none
  either) — Todd's c.1880/c.1970 faces are book tables, curated
  territory. agricultural_employment_share (2 citations) rides the
  same door one nace pin away (A: FR 1995 = 4.4 -> 2024 = 2.3).
- **tertiary + secondary education (13 + 8 citations):** UNESCO UIS —
  the world's education collector and the pair's natural un_dyb — has
  NO live machine door in 2026 (probed: api.uis.unesco.org answers
  every SDMX path with a 98-byte JSON 404 shell, the old bulk
  endpoints DNS-dead). The collector tier the pair CAN reach: the LFS
  attainment table (edat_lfse_03 — one questionnaire, the labour-force
  survey, now carrying three Todd metrics: unemployment v17, tertiary
  and secondary v18). The pins: ED5-8 (tertiary as highest
  attainment), ED3_4 (upper secondary + post-secondary non-tertiary —
  the Barro-Lee "secondary" bucket's closest LFS face; the ED3-8
  at-least face would run ~20 points higher, a misload the pins
  catch), age Y25-64, sex T, unit PC (the dataset's only unit, pinned
  and guarded). The tertiary witness: OWID's long-run chart door —
  the Barro-Lee (2015) + Lee-Lee (2016) panels, 1870+, 153 entities,
  the corpus's own named source (La Défaite de l'Occident's refs read
  "(Barro-Lee)"). The chart's own face, read live and documented: the
  slug says completed-tertiary, the variable column prints "incomplete
  tertiary", the subtitle "completed OR partially completed" — the
  some-tertiary face, the seam the root pair displays. Secondary's
  witness gap: every candidate OWID slug 404s (the collection exposes
  tertiary and mean-years only) — secondary rides canonical-only with
  the world face recorded as the Barro-Lee direct door's future
  wiring.
- **immigration_stock (11 citations, one book — Le Destin des
  immigrés, THE Todd question):** the migration questionnaire's stock
  table (migr_pop3ctb) prints the foreign-born stock per country,
  pinned c_birth=FOR ("Foreign country") — FR 2008 = 7,076,824 ->
  2024 = 9,362,105, annual, census-aligned, the door's 45-geo
  codelist richer than the LFS's (TR/UA/GE/AM/AZ/AD/MC). The Todd
  BY-ORIGIN face probed and recorded as the future door: the
  citizenship/birth codelists carry MA/DZ/TN/TR/PT (FR-by-MA 2015 =
  458,561, DZ 496,064, TR 215,587 — the detailed French slices print
  2015-2018 only); the UN DESA bilateral matrix is a manual-download
  dataset (the dataportal's 86 indicators carry net migration only).
  The witness: WB SM.POP.TOTL (the UN DESA Trends in International
  Migrant Stock estimates, world 1990-2024 — FR 1990 = 5,890,023; FR
  2024 = 9,186,757 DESA vs 9,362,105 collector, the estimation seam
  displayed).
- **cirrhosis_alcohol_mortality (9 citations, 4 books):** the v13
  probe note "RUS absent du slice cirrhose (404 NoRecordsFound)" was a
  PROBE ARTIFACT — the v13 probe omitted the Accept header the
  connector sends, so the API answered XML and the probe misread it;
  the full CICDCIRR slice answers 7,089 records through the
  production machinery (45 areas, 1960-2024, sex-split, FRA 1979 =
  29.0 — La Chute finale's own France-vs-Sweden calibration pair
  prints: FRA 29.0 vs SWE 12.2 both-sexes, SWE 17.5 male, the
  class-and-gender structure the book reads). The honest finding that
  replaced the artifact: RUS and UKR are GENUINELY absent from this
  cause's collector slice (they ride DF_COM for assault and suicide)
  — the WHO-MDB coding story: Russia's alcohol deaths live under
  different ICD codes (alcoholic cardiomyopathy, the ill-defined
  cardiovascular basket — the Treml/Nemtsov critique), and the GHE
  witness carries the modeled redistribution that covers Russia
  (SA_0000001457: RUS 2019 = 22.5 both at the YEARSALL face the
  connector keeps, 42.1 male at the 15+ face it drops logged — the
  SDGSUICIDE Dim2 precedent's second instance).
- The dead ends, honestly kept: the DYB economic tables (above), UIS
  (above), the OWID cirrhosis chart candidates (404-class), the UN
  DESA portal's bilateral matrix (no API). The probe round that never
  was: the session's first cirrhosis probe crashed on its own probe
  bugs (XML mistaken for CSV, dict/attribute confusion) — the
  discipline held: the CONNECTOR's machinery parsed the slice, and the
  probe errors never reached the wiring.

### Added

- **industrial_employment_share (the SIXTEENTH indicator, the corpus's
  #4 by citations):** canonical = Eurostat nama_10_a10_e pinned
  EMP_DC/PC_TOT_PER/B-E (the door's own printed share, the
  national-accounts questionnaire — root eurostat_na); witness = WB
  SL.IND.EMPL.ZS (root ilo_modelled, world 1991-2024). THE COMPOUND
  SEAM THE PAIR DISPLAYS (documented exactly, verified live): the ILO
  face includes construction AND rides a labor-force-modeled
  employment concept — FR 2015: 10.8 canonical vs 20.376 witness,
  a divergence the construction coverage alone does not close.
- **agricultural_employment_share (the SEVENTEENTH):** the same door
  at nace A (root eurostat_na); witness WB SL.AGR.EMPL.ZS — the
  definitional-cleanest pair (agriculture converges on the co-covered
  core: FR 2015 = 2.7 canonical face vs 2.7445 witness).
- **tertiary_education_share (the EIGHTEENTH):** canonical = edat_
  lfse_03/ED5-8/Y25-64/T (root eurostat_lfs — the LFS questionnaire's
  own table); witness = the Barro-Lee/Lee-Lee long-run panel via
  OWID's chart door (root barro_lee). The corpus's own named source
  rides the witness tier; the collector tier is the survey print.
- **secondary_education_share (the NINETEENTH):** edat_lfse_03/ED3_4/
  Y25-64/T (root eurostat_lfs). Witnesses: none wired — the probe
  verdict (no machine-readable secondary-attainment chart exists),
  the marker/consanguinity shape with the honest difference recorded:
  a machine-readable world panel EXISTS (Barro-Lee direct), it is
  simply not yet wired.
- **immigration_stock (the TWENTIETH, the demography family's first —
  the Family enum gains `demography`, the corpus's own vocabulary):
  canonical = migr_pop3ctb/FOR/TOTAL/T (root eurostat_migr); witness
  = WB SM.POP.TOTL (root un_desa). Unit persons.
- **cirrhosis_alcohol_mortality (the FIFTEENTH indicator by delivery
  order, wired sixth this version — the mortality family's fourth
  cause): canonical = OECD DF_COM/CICDCIRR (root who_mdb, the
  homicide/suicide architecture one cause-code swap away); witness =
  GHO SA_0000001457 (root who_ghe). The v13 probe artifact corrected
  in Investigated; Russia's absence documented as the coding story it
  is.
- Roots eurostat_na / ilo_modelled / barro_lee / un_desa /
  eurostat_migr in the registry (each with its live-verified comment
  record); EUROSTAT_DATASET_TITLES gains the three new datasets' own
  API titles (read live, never borrowed).
- Fixtures GENERATED from the live APIs (scripts/make_v18_fixtures.py,
  the v16/v17 anchor discipline — every value READ from a saved
  response, never typed): oecd_cicdcirr_sdmx.csv (the benchmark pair
  + the KOR 'B'/TUR 'D' flag rows — the flags ride specific areas,
  the carver learned), gho_cirrhosis_sample.json (RUS/FRA/SWE/ITA x
  both Dim2 variants), the Eurostat quintet (nama B-E with the EA
  row, nama A, edat ED5-8/ED3_4 with the 'b' flags, migr FOR with the
  'b'/'e'/'p' flags), the three WB dedicated pages (the v17
  discipline: a shared page's per-1,000 prints would contaminate a
  share's plausible band), owid_education_tertiary_sample.csv (the
  long-run anchors incl. Russia 1990 = 37.8 and USA 50.2 — La
  Défaite's own board).
- 24 tests (278 -> 302): 12 Eurostat connector (the three grammars,
  the URL pins, the EA aggregate drop, the layout guards across five
  datasets, the soft-miss pattern on every new dataset, the anchors)
  + 2 OECD (the benchmark pair + the cause-pin refusal) + 1 GHO (the
  YEARSALL/15+ grammar's second instance) + 6 integration (the six
  indicators' two-tier contracts, the corpus pins updated 10 -> 16,
  the backlog's new head top_income_share 7) + the catalog/dist-file
  pins.

### Changed

- The Eurostat connector speaks FIVE datasets now (three dispatch
  decisions added): nama_10_a10_e '{na_item}/{unit}/{nace}',
  edat_lfse_03 '{isced11}/{age}/{sex}' (+ the implicit unit=PC pin),
  migr_pop3ctb '{c_birth}/{age}/{sex}' (+ unit=NR) — each with its
  own layout pin-guard; the sex-pin mapping extends to the three sexed
  datasets; the per-dataset two-letter-aggregate table handles nama's
  EA edge.
- config/sources.yaml: the industrial deferral record REPLACED by the
  wiring record (the composite question dissolved, the ADR retired
  unused); the eurostat block carries the five questionnaires; the
  v18 probe records appended (UIS dead, the DYB economic-tables dead
  end, the Barro-Lee direct door, the migr by-origin doors, the
  unwired doors list).

### Fixed

- Nothing inherited (the v17 review came back clean). The wiring's own
  bug-reports, caught before they could land: (a) the first fixture
  carver missed the flag rows (they ride KOR/TUR, not the anchor
  areas — the carver learned to read the live slice before carving);
  (b) TWO typed anchors in the first test drafts failed against the
  fixtures' read values (a guessed FR-1979 male split that does not
  exist in the data, a guessed Poland-2015 value of 30 where the
  panel prints 23.7) — the anchor discipline held exactly as
  designed: the tests failed, the values were re-read from the saved
  evidence, the fix landed in the same session; (c) the industrial
  config's first seam note attributed the FR 2015 divergence to the
  construction coverage alone — the witness's own value (20.376 vs
  the 10.8 canonical) does not close on construction alone, and the
  note now documents the COMPOUND seam (construction + the ILO
  modeled employment concept).

### Verified (live, frozen at delivery 2026-09-21)

- Fetch v18: 11/11 source doors, 0 failures — oecd CICDCIRR 7,089
  records (45 areas, 1960-2024, 48 flagged cells: KOR 'B', TUR 'D'),
  gho SA_0000001457 540 records (the 15+ slices dropped logged — the
  YEARSALL face kept), eurostat nama B-E + A (the shares, the EA
  aggregate dropped logged), edat ED5-8 + ED3_4, migr FOR (the FR
  annual series 2008-2024), wb SL.IND.EMPL.ZS / SL.AGR.EMPL.ZS /
  SM.POP.TOTL 14,322 records each (3,168 aggregates skipped), owid
  tertiary 3,699 rows. (The Eurostat dissemination API went "Server
  temporarily unavailable" — HTTP 200 with an HTML error page —
  mid-fetch; the connector's loud parse refusal is the correct
  behavior and the fetch script's retries carried it through; the
  connector itself was NEVER weakened.)
- Rebuild + verify_v18_diff.py: the fourteen old indicators
  bit-identical; catalog +6 entries only; entities.json identical;
  corpus = exactly the six designed flips (10 -> 16, the backlog's
  head moves to top_income_share 7); double rebuild determinism.
- Stats (the dist's own counters, frozen at delivery): cirrhosis
  canonical 7,089 points (45 entities, 1960-2024, sex-split — every
  record a valued point, the 48 flag cells riding as-reported) + the
  GHE 2019 cross-section witness (540 records, 180 entities); industrial
  1,132 points (37 entities, 1975-2025 — the door's own starts: FR and
  Norway 1975, FR 51 annual points; Finland 1980; Germany 1991 the
  reunification start) + the ILOEST witness; agricultural 1,132 (the
  same door, 1975-2025); tertiary 1,000 (36 entities, 1992-2025) + the
  Barro-Lee witness 3,511 points (146 entities, 1870-2020); secondary
  1,000 (1992-2025, canonical-only); immigration 557 (33 entities,
  2000-2025 — Ireland 2000, Italy/Spain 2002, France 2007) + the UN
  DESA witness; corpus: implemented 16/24, the backlog's new head
  top_income_share 7.
- The plausible-bound recalibration, on the record: the cirrhosis
  config's first draft carried max 100 and the REBUILD'S OWN COVERAGE
  REPORT flagged six cells — Hungary's post-communist alcoholic
  cirrhosis epidemic, male 104.1 (1992) -> 126.5 (1994) -> 104.7
  (1999), as-reported history the bound would have hidden; recalibrated
  to 130 (the GHE witness's Egypt 2019 male 113.3 also riding inside).
  The verification machinery caught the config, exactly its job.
- Spot-checks from the live dist: the Todd benchmark pair itself —
  cirrhosis FRA 1979 = 29.0 vs SWE 12.2 (La Chute finale's
  calibration anchor, the both-sexes ratio 2.4x while the male rates
  nearly match: the class-and-gender structure the book reads);
  industrial FR 16.4 -> 10.1 / DE 23.1 -> 17.5 (the
  de-industrialization slopes as the accounts print them);
  agricultural FR 4.4 -> 2.3; tertiary FR 24.5 (2004) -> 43.2 (2024)
  with the witness's France 1870 = 0.2 and Russia 1990 = 37.8 vs USA
  50.2 (La Défaite's own board); secondary FR 41.4 / DE 56.7 (the
  ED3_4 face — the at-least face would run ~20 points higher);
  immigration FR 7.08M (2008) -> 9.36M (2024) with the DESA seam at
  9.19M; the crisis-era anchors (HUN 1994 M = 126.5 the canonical's
  own max — Hungary's post-communist transition epidemic, the cells
  that recalibrated the plausible bound; ITA 1979 M = 50.0 the
  Mediterranean cohort-memory tail; BGR 1991 = 45.1 on the industrial
  witness, the planned-economy tail; BFA 1991 = 81.9 on the
  agricultural witness, the agrarian South).
- Tests: 302/302.

### Known limitations

- The industrial/agricultural canonical tier is EU-shaped (the
  accounts universe: EU + IS/NO/CH/UK + the enlargement countries)
  — the US/Japan/world face rides the ILOEST witness alone, and the
  pair's seam is COMPOUND (construction coverage + the modeled
  employment concept): the two doors display a real definitional
  divergence, never reconciled. Todd's c.1880 and c.1970 industry
  maps, and Le Destin des immigrés' 1841 boards, are book tables —
  curated territory, not living wires.
- The education pair's collector is EU-shaped the same way (36
  countries); the world face rides the Barro-Lee witness (tertiary)
  or nothing yet (secondary — the direct Barro-Lee door recorded).
  The Todd claims' cohort faces (70-74, the US BA-by-birth-cohort)
  are panel faces: the witness carries them, the canonical prints the
  LFS's adult band.
- immigration_stock: the by-origin decomposition (THE Todd question)
  is the recorded future door (the codelists print it, the indicator
  shape does not carry bilateral values); Ukraine rides the migr
  codelist with zero valued cells; the 1946-1990 boards are book
  tables.
- cirrhosis: Russia and Ukraine are absent from the collector slice
  for this cause (the WHO-MDB coding story) — the Russian alcohol
  mortality claim rides the GHE witness (modeled, age-standardized)
  and the book tables; France's 19th-century series is curated
  territory.
- The unresolved classes unchanged: Kosovo + Channel Islands, the
  Byelorussian/Ukrainian SSR and HMD/HFD decisions, the pending
  product classes the WB/Eurostat Kosovo prints keep surfacing.


## 2026-09-20 — v17: the backlog's head claimed — consanguineous_marriage_rate,
## the thirteenth indicator (the curated tier's third family) and
## unemployment_rate, the fourteenth (the economy family's first, and the
## Eurostat labour-force door) — the two-track version

**No dist contract break (purely additive):** the twelve existing
indicators keep every key bit-identical (verified key-by-key, 63/63
checks — NO designed change this time, not even a value flip); the dist
gains exactly two new indicator files, two catalog entries, and the two
designed corpus flips (implemented 8 -> 10). entities.json is
bit-identical (the new indicator's unresolved names are the pending
Kosovo/Channel-Islands classes only).

### Context

Ediz green-lit V17 with the explicit challenge to run BOTH tracks in
parallel (the V15 precedent: "tu peux essayer"). The two tracks were
probed in parallel before any wiring — track B by a dedicated probe
pass (scripts/v17_probe/unemp/, 21 evidence files + REPORT.md), track A
by the consanguinity harvest (scripts/v17_probe/consang/, the Bittles
compilation parsed + 60 gap-evidence files). Both probes had delivered
their verdicts before a single line of wiring was written: (a) the
consanguinity gate was already satisfied at v16 (the ABSENCE of any
machine-readable door — GHO 0 hit, WDI 0/25000, OWID 404), the work
was the curation itself; (b) the unemployment collector question
(ILOSTAT DEAP/5EAP, the v16 deferral record) was answered wholesale
NO — every ILOSTAT unemployment flow is ILO-processed material (2EAP =
ILOEST modeled; 5EAP = 19th-ICLS WORK harmonized; DEAP/TUNE = the
LFS/ILMS databases with "Repository: ILO-STATISTICS - Micro data
processing" and LFS-ADJ adjusted series, verified on a 46,454-row 2015
live sample), the OECD doors are OECD-harmonized or
registered-unemployment counts ("not comparable across countries" per
their own description) — leaving Eurostat's une_rt_a as the ONE
collector wire that prints the plain national rate.

### Investigated (live, before any config)

- **consanguineous_marriage_rate (34 citations, 10 books — Le Destin
  des immigrés alone carries 16):** the consang.net global tables
  (A.H. Bittles' compilation, the domain's standard reference) parsed
  across all five continent tables (~500 rows); the per-country
  candidate set selected (national readings first, the largest-sample
  subnational study where no national print exists); the harvest's own
  bug-reports found and fixed in selection (the parser's country
  context had mis-attributed Argentina/Bolivia rows to the US block,
  the Palestinian territories to Oman's, and the Irish Republic's
  reading to Northern Ireland's slot — all re-attributed by reading
  the raw table lines). The gap evidence: PDHS 2017-18 FR354 Table
  4.5 read directly (63.9% married-to-a-relative, N=12,364, the Total
  row's Not-related 36.1%), El-Mouzan et al. 2008 (Saudi national
  56%, first-degree 33.6%), Saadat et al. 2004 (Iran national 38.6%
  over 306,343 couples — the compilation's own 30.0 is the Persian
  Shi'a subgroup, superseded), Ben Halim et al. 2012 (Tunisia's
  representative control cohort 29.80%), Kalam et al. 2024 (India's
  NFHS-4+5 pooled national 13.6%), Kaplan et al. 2016 (Turkey's
  Ministry-of-Health national 18.5%). The dead ends, honestly kept:
  the Sudan DHS 1989-90 carries no consanguinity question (Todd's
  own "Sudan 57%" reads a different compilation — the divergence is
  documented on the row); the DHS Turkey 1993 report page was a
  ColdFusion error (never fetched); Kalam 2024 turned out to be
  India's national pooling, not Iran's.
- **unemployment_rate (20 citations, 7 books):** the probe inventory —
  Eurostat une_rt_a pinned age=Y15-74/unit=PC_ACT/sex=T (635 valued
  cells, 38 geos, 2003-2025, 1-decimal; the age codelist carries NO
  TOTAL — Y15-74 is the LFS's own labour-force window and the de-facto
  total; flags b/d, d on FR and ES 2021-2025 = the LFS questionnaire
  redesign, a DEFINITIONAL seam, not a geo one; FX/DE_TOT/XK/UK/US all
  probed ABSENT — the codelist is EU+EFTA+Western-Balkans+Türkiye);
  the WB code choice NE over ZS (208 vs 187 real countries, 1990 vs
  1991, XKX Kosovo only in NE; the fingerprint: WB NE ≡ ILOSTAT DEAP
  plain rate to 3 decimals — FRA 1992 = 10.203 on both doors); the
  coverage cliffs (FR alone 2003-2025, everyone else 2009+, SE 2005,
  CH/RS 2010, BA 2021, ME STOPS AT 2020); the OECD registry gotcha
  (agency-qualified path 404s, dataflow/all/all/latest with SDMX-JSON
  2.0 works). The ILOSTAT by-citizenship flows (DEAP_CCT/CBR) verified
  live for FRA 2015-2018 — recorded for Le Destin des immigrés'
  by-nationality door (a future harmonized-tier wiring).

### Added

- **consanguineous_marriage_rate (the THIRTEENTH indicator, the
  corpus's #6):** catalog/curated/consanguineous_marriage_rate.csv —
  102 rows, 69 countries, 1943-2021, one citation per point, generated
  by scripts/v17_probe/consang/build_curated_table.py (the v16
  anchor-discipline lesson applied: every row READ from a saved
  evidence file, never typed). The table's three belts: the European
  registry belt (France 1958 = 0.8 over 510,000 Sutter & Goux
  dispensations; Norway's three registry vintages 0.6 -> 0.7 -> 0.1 up
  to 1.4 million marriages; Spain 4.1; the two Masterson island
  readings Ireland 0.5 / Northern-Ireland-as-UK 0.4), the Latin
  dispensation belt (Freire-Maia's 1956/57 cycle: Brazil 4.8, Ecuador
  6.3, the later Orioli/Liascovich/Castilla vintages), and the
  Muslim-world survey belt (the corpus's heart: Pakistan's four DHS
  vintages 61.2 -> 60.5 -> 56.4 -> 63.9, Iran 38.6, Saudi Arabia 40.6
  -> 56.0, Iraq 33.0, Jordan 39.7, Kuwait 38.4 -> 34.3, the Maghreb
  trio 22.6/19.9/29.8, Turkey's four vintages 21.2 -> 18.5, Israel's
  Arab community 34.2 -> 22.9, Palestine's two 29.2 -> 27.7, Sudan's
  Khartoum 52.0). Year convention: the END year of the printed
  measurement period; the publication year where none prints; the
  decade's end for a fuzzy '1970s' — the source's own period string
  rides every note. The 13th root: consanguinity_studies (the study IS
  the origin — no upstream redistributor to disclose, no witness can
  ever cross-check it; the same constitution as the markers).
- **unemployment_rate (the FOURTEENTH indicator, the economy family's
  first — the Family enum gains `economy`):** canonical =
  Eurostat une_rt_a/Y15-74/PC_ACT/T (the labour-force questionnaire —
  the project's SECOND Eurostat dataset, wired as the connector's
  second dispatch decision with its own ref grammar
  une_rt_a/{age}/{unit}/{sex}, its own layout pin-guard [freq, age,
  unit, sex, geo, time], and the sex pin mapped to the project's sex
  vocabulary so the unwired M/F doors are one ref away); witness = WB
  SL.UEM.TOTL.NE.ZS (root ilo_lfs, the ILO-processed LFS family
  redistributed by WDI as the national-estimate line). Roots 14 and
  15: eurostat_lfs / ilo_lfs — the pair that keeps the coverage cliff
  (DE 1991-2008 witness-only) and the rounding seam (FRA 2024 7.436
  vs 7.4) reading as two doors, never a contradiction.
- Fixtures GENERATED from the live APIs (make_unert_fixtures.py, the
  v16 lesson): eurostat_unert_sample.json (the six-geo miniature with
  the FR full-length series, the 'd' seam, the DE cliff, the ME stop,
  the aggregate drop) + wb_uem_ne_sample.json (the dedicated NE page —
  FRA 1990 9.36, DEU 1991 5.316, DEU 2005 11.193, XKX 2001 57.0, the
  WLD aggregate row).
- 15 tests (263 -> 278): 13 connector (the une_rt_a grammar, the URL
  pins, the live anchors, the pin-guards across datasets, the
  soft-miss loud failure) + 2 integration (the curated table's own
  contract — every point's citation and scope note verified from the
  dist; the unemployment two-tier with the coverage cliff, the flag
  story, the root pair).

### Changed

- The Eurostat source citation in the dist now carries the dataset's
  own API title (EUROSTAT_DATASET_TITLES in the schema; build.py
  formats it) — une_rt_a prints "Unemployment by sex and age - annual
  data", never v14's borrowed "Fertility indicators". demo_find's
  citation is byte-identical with before (the old indicator files
  verified bit-identical).
- config/sources.yaml: the two v16 deferral records (consanguineous,
  unemployment) replaced by their wired blocks and probe findings; the
  unwired doors recorded (ILOSTAT wholesale witness-only incl. the
  citizenship/place-of-birth ILMS family for Le Destin des immigrés,
  OECD LFS_INDIC/IALFS/OIALAB, WB ZS + the four sex-split codes,
  Eurostat une_rt_m monthly and the M/F pins).

### Fixed

- Nothing inherited this time (the v16 review came back clean); the
  harvest's own bug-reports were fixed before they could land (the
  selection re-attributions above, plus the fixture-time discovery of
  the borrowed citation — caught by reading the dist the verify
  script was about to certify).

### Verified (live numbers, frozen at delivery)

- Fetch: 3/3 snapshots, 0 failures — eurostat une_rt_a 584 country
  records (51 aggregate rows dropped logged), WB NE 14,322 records
  (3,168 aggregates skipped by the provider's own classification),
  curated 102 records (network-free).
- Rebuild + verify_v17_diff.py: **63 PASS / 0 FAIL** — the twelve old
  indicators bit-identical; catalog +2 entries only; entities.json
  bit-identical; corpus = exactly the two designed flips (8 -> 10,
  the backlog's head moves to industrial_employment_share 30); double
  rebuild determinism (every dist byte stable).
- Stats: consanguineous_marriage_rate canonical 102 points = 102
  valued + 0 gap, 69 entities, 1943-2021, roots consanguinity_studies
  (curated), witnesses: none; unemployment_rate canonical 584 points
  = 584 valued + 0 gap, 35 entities, 2003-2025, roots eurostat_lfs
  (eurostat) + witness ilo_lfs (worldbank) 14,190 points 215 entities
  1960-2025; the twelve other counters unchanged; corpus: "implemented
  10/24 (birth_rate_fertility 111, suicide_rate 80, infant_mortality
  52, consanguineous_marriage_rate 34, life_expectancy 26,
  homicide_rate 25, unemployment_rate 20, illegitimate_births 16,
  same_sex 13, suffrage 7); top unimplemented:
  industrial_employment_share 30...".
- Spot-checks from the live dist: the consanguinity board's own
  extremes as-reported (Norway 1993 = 0.1 over 1,431,055 marriages ->
  Burkina Faso North 2001 = 65.8; the as-reported zero Panama 1957);
  Pakistan's four vintages; the unemployment board's France 8.5
  (2003) -> 7.4 'd' (2023) with the witness's 1990 9.36 on the other
  tier; the crisis peaks ES 2013 = 26.1 / EL 2013 = 27.8; the German
  cliff (2005 ABSENT on the collector, 11.193 on the witness).
- Tests: 278/278.

### Known limitations

- The consanguinity table is a SPARSE panel, not an annual series —
  a country rides the vintages its literature prints (Norway 3,
  Pakistan 4, Brazil 3; most 1-2 readings); subnational and
  community-scope readings enter only where no national print exists
  (each flagged in its note, the alternatives documented); the two
  Israels are the Arab community's own national surveys; Todd's
  19th-century face (the historical France/Algeria of his books'
  tables) has no citable machine print in hand — the table starts
  1943, the limit documented in the config.
- unemployment: the collector's coverage cliff is the honest shape
  (FR alone 2003-2025; everyone else 2009+; ME stops 2020; no UK —
  post-Brexit the door stopped carrying it); the interwar prints of
  L'invention de l'Europe are book tables, territory curated, not a
  living wire; the by-nationality question (Le Destin des immigrés)
  waits on the ILMS citizenship door recorded in sources.yaml.
- The unresolved classes unchanged: Kosovo + Channel Islands (the
  WB witness), the Byelorussian/Ukrainian SSR and HMD/HFD decisions,
  the industrial composite-derived-layer question (now the backlog's
  own head, 30 citations).

## 2026-09-20 — v16: the three review repairs and illegitimate_births,
## the twelfth indicator — Todd's illégitimité, printed directly by the
## collector (and the German seam)


**No dist contract break (additive, with ONE designed value change):**
the eleven existing indicators keep every pre-existing key bit-identical
(verified key-by-key, 53/53 checks) with exactly ONE designed VALUE
change: birth_rate_fertility's `companion_indicators` flips
[] -> ["crude_birth_rate"] — the external v15 review's asymmetry
repaired (the TFR/CBR pair is now declared on BOTH sides, enforced by a
new cross-validation). The additions are one NEW indicator file
(illegitimate_births.json), a new root in the registry (oecd_family),
todd_corpus.json's ONE designed flip (implemented 7/24 -> 8/24), and
five new raw snapshots (the Eurostat NMARPCT main slice + the three
geo-pinned series doors + the OWID/OECD witness). Plus a REPAIR to the
v15 test fixtures and two corrected sentences in the v15 entry itself
(the France-2020 provisional claim — see Fixed).

### Context
Ediz's external review of v15 landed three remarks, all confirmed
against the repo: (1) the v14 entry's header had vanished from this
changelog — the entry's body sat orphaned between v15 and v13, an
accident of the v15 prepend; (2) the v15 entry claimed "France 2020
carries provisional=true" but the data prints the flag on 2022/2023/
2024, 2020 unflagged — a REAL divergence between the changelog's words
and the dist; (3) `companion_indicators` was asymmetric
(crude_birth_rate pointed at birth_rate_fertility, the TFR carried the
empty list) with nothing explaining the one-way shape. "Pour la V16, tu
peux continuer une fois que tu auras résolu / répondu aux remarques
ci-dessus" — so v16 is the three repairs PLUS the roadmap's next move,
chosen probe-first as always.

### Investigated
- The review's remark (2) traced to its ROOT: not a data bug — the dist
  was always right — but a FIXTURE bug. tests/fixtures/
  dyb_table9_sample.xls's France block carried fabricated round numbers
  (rates 11.7/11.5/..., counts 842000+) with '*' glued on 2020, in
  violation of the repo's own anchor discipline; the changelog then
  quoted the fixture's fiction. The real DYB 2024 France Total row
  (extracted from the probe cache, byte-for-byte): counts 696664/
  701819/686564*/639533*/629000*, rates 10.6579082599/10.7086704955/
  10.4267737019*/9.6873422054*/9.5025212576* — the '*' provisional
  marker rides BOTH blocks on the three most recent years, and 2020/
  2021 print unflagged.
- The v16 roadmap probes (three candidates, in parallel): (a)
  illegitimate_births — Eurostat's demo_find codelist carries NMARPCT,
  "Proportion of live births outside marriage": the collector prints
  Todd's exact metric DIRECTLY (2,374 cells, 58 geo, 1960-2024, values
  in percent — France 1998 = 41.7, Turkey 2024 = 3.4); the counts-based
  doors (demo_cnia and family) do not exist as share doors, WDI carries
  no such indicator, and OECD Family Database SF2.4 has no SDMX wire
  (the v14 finding) — but OWID's share-of-births-outside-marriage chart
  IS that compilation's machine-readable face (42 entities, 1960-2021;
  OWID's own attribution: "OECD (2025)"). (b) consanguineous_marriage_
  rate — NO machine-readable door anywhere (GHO zero hits, WDI zero of
  25,000 indicators, OWID 404): the curated gate's condition (b)
  satisfied, the metric waits on the curation work (documented in
  sources.yaml). (c) unemployment_rate — the ILOSTAT registry's 69 UNE
  flows: the plain national rate line is ILO modelled estimates
  (witness-only by constitution); the non-modeled rate flows are
  characteristic-split cross-sections — DEFERRED with the record.
- THE GERMAN SEAM (the probe's own find): on NMARPCT the codelist's
  DE_TOT ("Germany including former GDR") is the FULL 65-year series
  while DE's 39 points carry five pre-reunification FRG-only benchmarks
  that DIVERGE (1960: 6.3 vs 7.6; 1970: 5.5 vs 7.2; 1980: 7.6 vs 11.9;
  1985: 9.4 vs 16.2; 1990: 10.5 vs 15.3 — the GDR's high non-marital
  share is Todd's communist-family-systems story in one number) — the
  EXACT REVERSE of the TFR case, where DE_TOT was the verified
  duplicate. The v14 connector had hardcoded the TFR-specific finding
  ("identical, drop DE_TOT") into generic machinery; NMARPCT needed the
  per-code truth instead. The OWID/OECD witness independently rides the
  all-Germany series too (its Germany 1960 = 7.6 = DE_TOT's print) —
  the collector-side arbitration matches what the OECD compiled.

### Added
- **Indicator `illegitimate_births`** (the TWELFTH, todd_core — 16
  citations, 6 books): unit percent_of_live_births, family society,
  plausible 0-100 (the collector's own max prints in the low 60s;
  the witness tail peaks at Chile 2019 = 75.08). Four canonical
  sources, one collector: demo_find/NMARPCT/DE_TOT (priority 1 — the
  German series door, the seam's winner), the main slice (priority 2),
  demo_find/NMARPCT/FR and /FX (priorities 3/4 — the French seam,
  identical architecture to the TFR's) + the OECD Family Database
  witness through OWID's chart door (root oecd_family, the registry's
  new root). No sex split by construction; higher_is_better=false as
  the least-misleading default (the corpus reads levels and contrasts).
- `cross_validate_companions` (src/config_loader.py): the symmetry
  contract on companion_indicators — every link reciprocated, every id
  existing, no self-reference, no duplicates; wired into every config
  load (cli._load_config), so the v15 asymmetry is now a BUILD FAILURE,
  not a review catch.
- Root `oecd_family` in the registry; `DE_TOT` in the Eurostat override
  table (resolving to DEU — the pinned German series door); the
  code-aware DE_TOT drop log (the TFR's "verified duplicate" claim now
  scoped to TOTFERRT, the NMARPCT message documenting the reversed
  relationship and its own pinned source_ref).
- Fixtures (generated FROM the live API by
  scripts/v16_probe/make_nmarpct_fixtures.py — the anchor discipline
  enforced by construction this time, the v15 lesson): the NMARPCT
  quartet (main miniature with the EL 'b' / MD 'p' flags, the EU27
  aggregate, XK 2002/2012, the DE/DE_TOT divergence years, the FX/FR
  seam values; the three geo-pinned miniatures carrying the German seam
  and the French seam's own numbers) + owid_nmarpct_sample.csv (14
  live-anchored witness rows: France 1998/2020, Germany 1960/2020,
  Sweden, Japan, Estonia, Turkey, Chile).
- 10 new tests (253 -> 263): 4 companion-symmetry (the real config
  passes; the exact v15 one-way shape raises; unknown id raises; self/
  duplicate raise) + 5 connector (the NMARPCT dispatch, the code-aware
  drop log, the flags, the DE_TOT pin with its guard, the FR/FX pins)
  + 1 integration (the German seam end-to-end: DE_TOT wins 1980 with
  DE's 7.6 a logged provenance discard, the 39 German + 15 French
  arbitrations, the witness's vintage face).

### Changed
- birth_rate_fertility.yaml gains `companion_indicators:
  ["crude_birth_rate"]` — the pair's other side (the ONE designed dist
  value change; the catalog entry carries it too).
- The Eurostat connector's DE_TOT drop is now code-aware (message and
  claim), the France-variant drop message cites the requesting code's
  own pinned refs — no behavior change on TOTFERRT (pinned by the
  existing tests).

### Fixed
- **The v14 changelog header, restored**: the entry's title line
  ("## 2026-09-19 — v14: birth_rate_fertility, the eighth indicator —
  the corpus's #1 — and the Eurostat collector (the TFR-vs-CBR
  decision)") was lost in the v15 prepend — recovered verbatim from the
  v14 delivery patch (git-tracked) and re-inserted between v15 and the
  orphaned v14 body. A structural repair, not a content edit.
- **The France-2020 provisional claim, corrected at its root**: the
  fixture's France block rewritten to the live DYB 2024 bytes (see
  Investigated); the two v15-entry sentences that carried the fiction
  now state the true facts with an explicit "(corrected in v16: ...)"
  marker — the vintage stays honest, the correction is visible where
  the error lived. The dist itself never carried the error (the
  reviewer's own check confirmed the values; only the words and the
  fixture were wrong).
- **The companion asymmetry, repaired and made unrepeatable**: the
  declaration now rides both configs, and cross_validate_companions
  fails any future one-way link at config load (the v15 review's exact
  shape is now a test case that MUST raise).

### Verified (live, frozen at delivery 2026-09-20)
- Fetch v16: 5/5 snapshots, 0 failures — Eurostat main 2,069 records
  (160 aggregate + 65 DE_TOT + 80 France-variant rows dropped, all
  logged with the code-aware messages), DE_TOT pin 65, FR 27, FX 53,
  OWID witness 2,139 records.
- Rebuild + verify_v16_diff.py: 53 PASS / 0 FAIL — the eleven old
  indicators bit-identical except the TFR's ONE companion value;
  entities.json bit-identical; the corpus's one designed flip (7 -> 8);
  double rebuild determinism (every dist byte stable).
- illegitimate_births: canonical 2,144 points = 2,144 valued + 0
  explicit gaps (2,214 fetched records - 16 Kosovo unresolved - 39
  German - 15 French arbitrations = 2,144 exactly), 46 entities,
  1960-2024; witness 2,139 points, 42 entities, 1960-2021. THE GERMAN
  SEAM verified from the dist: Germany 1980 = 11.9 (the all-Germany
  print; DE's FRG-only 7.6 a provenance discard, with all 39 DE
  collisions logged); Germany 1960 = 7.6 / 1990 = 15.3 / 2024 = 32.4.
  THE FRENCH SEAM: France 1960 = 6.1 (FX metro) / 1998 = 41.7 / 2000 =
  43.6 / 2020 = 62.2 / 2024 = 59.7 (FR wins the 1998-2012 overlap, 15
  FX discards logged). Flags as-reported: Greece 2023 'b', Moldova 2022
  'p'. The witness anchors: France 2020 = 62.2 = the collector's own
  FR print (the OECD anchors on the national series), Germany 1960 =
  7.6 = DE_TOT's print, Japan 2020 = 2.4, Chile 2019 = 75.08 inside
  the bound.
- THE REVIEW REPAIR verified against the live dist: crude_birth_rate's
  France 2020 = 10.6579082599 with NO provisional flag; France 2022/
  2023/2024 carry provisional=true; France 2023 = 9.6873422054 (the
  reviewer's own cited value, exact).
- Stats: illegitimate_births canonical 2,144 = 2,144 valued + 0 gap,
  46 entities, roots eurostat_demo (eurostat x4) + witness oecd_family
  (owid); the eleven other counters unchanged; corpus block:
  "implemented 8/24 (birth_rate_fertility 111, suicide_rate 80,
  infant_mortality 52, life_expectancy 26, homicide_rate 25,
  illegitimate_births 16, same_sex... 13, universal_suffrage... 7);
  top unimplemented: consanguineous_marriage_rate 34..." — the
  backlog's head unchanged.
- Tests: 263/263.

### Known limitations
- The canonical tier is Eurostat-shaped: the questionnaire's honest
  freezes (the UK to 2017, Russia 2006-2014, Kosovo printing 2002-2021
  but unresolved — the pending class) and NO 19th-century face: Todd's
  France 1900-1973 and England 1835 rows are book data, curated-tier
  territory (the HFD-class pending decision carries the historical
  depth question). The worldwide-OECD face rides the witness alone —
  its vintage honestly ends at the OECD's 2021 compilation.
- The German seam keeps ONE definitionally-consistent series (the
  all-Germany print); the FRG-only variant's five divergent benchmarks
  live in the provenance log, not the canon — the inverse choice would
  have been equally defensible (a metro-Germany canon), but a zigzag
  mix of the two would not.
- consanguineous_marriage_rate (the backlog's head, 34 citations) and
  unemployment_rate (20) remain unimplemented with their probe records
  in sources.yaml — the curated gate is satisfied for consanguineous,
  the curation work is the v17 candidate; unemployment waits on the
  collector-tier question the 69-flow inventory raised.
- Unwired doors recorded: demo_find's remaining Todd-adjacent codes
  (AGEMOTH/MEDAGEMOTH — mean/median age at childbirth, LBIRTHRnPC —
  birth-order shares) are one config away if ever demanded; the DYB
  Table 9 Number block stays a `field: number` away.

## 2026-09-20 — v15: the CBR companion (crude_birth_rate, the ninth
## indicator) and the markers — the curated tier's second family (two
## indicators, one probe-referenced deferral)

**No dist contract break (additive):** the eight existing indicators keep
every pre-existing key bit-identical (data, witnesses, sources, roots,
todd_refs — verified key-by-key, 57/57 checks); the additions are one new
field on every indicator file and catalog entry (`companion_indicators`,
[] for the companion-less — the honest empty list), three NEW indicator
files (crude_birth_rate.json, same_sex_marriage_legalization_year.json,
universal_suffrage_introduction_year.json), a new Family enum value
(markers), a new root (national_legislation), and todd_corpus.json's two
designed flips (implemented 5/24 -> 7/24 — the markers; the backlog's
head unchanged, consanguineous_marriage_rate 34). Sixteen new raw
snapshots (13 DYB Table 9 editions + the WB CBRT witness + the two
curated tables' network-free snapshots).

### Context
v15 was green-lit free-form ("c'est comme tu veux ! Tu peux même tout
faire en parallèle si tu en es capable" — Ediz, after his external
review of v13+v14 passed). The roadmap's three candidates (a: CBR
companion via DYB Table 9; b: the curatable markers, same-sex 13 +
suffrage 7; c: industrial_employment_share 30) were probed IN PARALLEL
before any wiring decision — the project's probes-before-code
discipline — and the probes themselves settled the scope: (a) and (b)
wired, (c) deferred with a founding constitutional finding (see
Investigated). Ediz's v13/v14 review verdict: "parfait".

### Investigated
- DYB Table 9 across ALL 13 wired editions (downloaded live, parsed
  through the repo's own _rows_from_bytes BEFORE any code): the table
  "Live births and crude birth rates, by urban/rural residence" is the
  EXACT Table 15 wide layout (Total/Urban/Rural rows, quality-code
  column, Number-then-Rate blocks, 5-year windows, Footnotes worksheet)
  with a STABLE table number 2011-2024 (no renumbering zone) — titles
  verified edition by edition (2024: 493 rows / 166 Total-rows; 2011:
  497 / 165). The Table 15 parser therefore serves it through a new
  dispatch branch with a content guard on the title's own words (the
  21/22 lesson applied anyway — the title is the ground truth, the
  number the cross-check).
- A REAL GRAMMAR FIND (the probe's own bug report): the '*' provisional
  marker GLUED to a footnote ref ("*47", "*25") on live-birth COUNT
  cells — 26 live occurrences across editions 2011/2017-2022, ZERO on
  rate cells. The connector's marker grammar refused it loudly (the
  loud-failure rule working as designed); the fix is the diamond form's
  exact mirror (provisional=True, the digits riding footnote_refs).
- The markers curation gate, condition (b) — probed live: OWID carries
  NO same-sex-marriage or suffrage grapher chart (10 candidate slugs,
  all HTTP 404), and no collector prints statutes. The demonstrated
  distortion is the ABSENCE itself: the curated tier is not competing
  with a wire, it is the only tier. The probe record (slug list +
  statuses) lives in the v15 worklog and the sources.yaml curated notes.
- industrial_employment_share (the corpus's #6, 30 citations) — probed
  live across THREE collector doors: ILOSTAT SDMX DF_EMP_TEMP_SEX_IND_NB
  (the old branch classification, national sources — FRA 2024 total
  29021.954 thousands, verified live) and its ECO/ISIC variants, ALL
  count (NB) flows; OECD DSD_ALFS@DF_ALFS_EMP_ISIC (agency OECD.SDD.TPS
  v1.1 — 49 areas, 1955-2025, counts in persons/thousands, the
  "Industry (including construction)" aggregate present); the rplumber
  bulk door (EMP_TEMP_SEX_ECO_NB_A — ECO_AGGREGATE/ECO_ISIC4
  classifications, counts again; the _RT_ rate flow returns 400 and
  does not exist). The one door printing the percentage — WB
  SL.IND.EMPL.ZS (FRA 2024 = 19.54, verified live) — is ILOEST, the
  ILO's MODELED estimates: harmonized, witness-only by constitution.
  Computing sector/total from the collectors' counts would be a
  DERIVATION (the same refusal as summing Table 10's ASFRs into a TFR).
  The metric is therefore DEFERRED on the pending composite-derived-
  layer decision (client-side ratio of two canonical counts, its own
  ADR), documented in sources.yaml with the full probe record.
- WB SP.DYN.CBRT.IN verified live (FRA 2024 = 9.7, RUS 1960 = 23.881,
  NER 1960 = 57.613 — the WPP tail's peak, the plausible bound's own
  reason); bare code, the same shape as TFRT.

### Added
- `crude_birth_rate` (the NINTH indicator, the CBR companion): DYB
  Table 9's rate block canonical across the 13-edition loop (the same
  births Table 17's maternal ratios are computed from — the collector's
  own cross-table dependency, one reason this table is the canonical
  CBR) + WB SP.DYN.CBRT.IN witness (un_wpp). todd_core=false BY DESIGN:
  no corpus metric carries the crude rate as its own id — the corpus's
  19th-century CBR rows ("France < 30/1 000") live under
  birth_rate_fertility's umbrella; the relationship rides the new
  `companion_indicators` field (emitted on every indicator file and
  catalog entry, the TFR/CBR pair reading the same demographic
  phenomenon through two DIFFERENT measures, never a unit conversion).
- `same_sex_marriage_legalization_year` (the TENTH indicator, the
  FIRST MARKER): 33 countries, 2001-2025, one point per country (year
  = value = the legalization year), every point carrying its citation
  (the statute or nationwide ruling with its effective date) and its
  dating-convention note. The 'religion zero' marker of La Défaite de
  l'Occident (13 citations — the chain 2015 -> Trump -> Ukraine war
  reads from these dates). Family=markers (the enum's new value), root
  national_legislation (the registry's new root — the citation IS the
  origin, nothing upstream to witness, hence witnesses: none).
- `universal_suffrage_introduction_year` (the ELEVENTH indicator, the
  SECOND MARKER): 16 countries, 1848-1946, L'invention de l'Europe's
  anthropological fingerprint (7 citations — Austria 1907, Belgium
  1919, Sweden's '1911/1921' dual dating, the corpus label's own
  convention applied uniformly: the marker = the historiography's
  dating, the male/female decomposition riding every row's note).
- catalog/curated/same_sex_marriage_legalization.csv (33 rows) and
  catalog/curated/universal_suffrage_introduction.csv (16 rows) — the
  curated tier's second family, the gates written into
  catalog/curated/README.md.
- The Table 9 dispatch branch (content guard on the title's words) +
  the '*NN' star-plus-ref marker grammar (_STAR_REF_RE, the diamond
  form's mirror) in src/connectors/dyb.py.
- Family enum value `markers`; ROOT_LABELS entry `national_legislation`;
  the `companion_indicators` field emitted by build.py (indicator files
  + catalog); tests/fixtures/dyb_table9_sample.xls (live DYB 2024
  anchors: Algeria 22.3369498881, Botswana 24.4493008232, Burundi +U,
  the '*2' glued marker) + tests/fixtures/wb_cbrt_sample.json (live
  WDI anchors: FRA 2024 9.7, RUS 1960 23.881, NER 1960 57.613).
- 13 new tests (240 -> 253): 10 connector (the Table 9 shape/anchors/
  guard/grammar, the star-plus-ref unit pin) + 3 integration (the CBR
  two-tier end-to-end with the '+U' degradation and France's '*' flags
  on 2022/2023/2024 — corrected in v16: this line originally said "the
  France 2020 '*' flag", a fabricated-anchor artifact; the live 2024
  file prints 2020 UNFLAGGED; the markers' shape/citations/chain; the
  markers' corpus pins).

### Changed
- `_parse_marker_cell`'s grammar: '*' + digits now accepted (was a
  loud refusal — correct behavior then, the 26 live occurrences
  documented now); the refusal message updated to name the starred
  form. No existing behavior changed: '*' alone, digits, Roman ranges,
  diamonds all parse exactly as before (pinned by tests).
- todd_corpus.json's implemented share 5/24 -> 7/24 (the two markers'
  designed flips — the ONLY flips, verified metric by metric).

### Verified (live, frozen at delivery 2026-09-20)
- Fetch v15: 16/16 snapshots, 0 failures — 13 Table 9 editions
  (845-915 rows each) + WB CBRT 14,322 records (3,168 aggregates
  skipped, logged) + the two curated tables (33 + 16 rows,
  network-free).
- Rebuild + verify_v15_diff.py: 57 PASS / 0 FAIL — the eight old
  indicators bit-identical modulo the ONE additive key; entities.json
  bit-identical; the corpus's two designed flips exactly; double
  rebuild determinism (every dist byte stable).
- crude_birth_rate: canonical 3,319 points = 2,225 valued + 1,094
  explicit gaps (the collector's own C/U editorial rule: "U" rows
  print counts with "..." rates — the honest degradation, kept as
  printed); 179 valued entities, 2007-2024; roots unsd_dyb (un_dyb
  x13) + witness un_wpp 14,190 points, 215 entities, 1960-2025; 1,900
  edition arbitrations logged in provenance.json. Russia answers the
  Table 9 questionnaire through 2024 (18 points 2007-2024 — unlike
  Table 15, the births keep flowing). France's as-reported natalité:
  12.68 (2007) -> 9.5 (2024), the continuous decline Todd's board
  reads. Spot-checks: Algeria 2020 = 22.3369498881, France 2023 =
  9.6873422054, and the '*' provisional flag rides France 2022/2023/2024
  — 2020 prints 10.6579082599 with NO flag (corrected in v16: this
  bullet originally claimed "France 2020 carries provisional=true", a
  claim born in the fabricated fixture anchor, not the data; the dist
  itself was always right), witness FRA 2024 = 9.7 / NER 1960 = 57.613.
- same_sex_marriage_legalization_year: 33 points, 33 countries,
  2001-2025, witnesses: none; the chain Todd reads verified from the
  dist (France 2013 / Ireland 2015 / USA 2015 / Germany 2017 / Greece
  2024 — the Orthodox world's first / Taiwan 2019 — Asia's first /
  Netherlands 2001 — the world's first). todd_refs 13/1.
- universal_suffrage_introduction_year: 16 points, 1848-1946; the
  anthropological order verified from the dist (France 1848 / Germany
  1871 / Austria 1907 / Sweden 1911 with '1921' in the note — Todd's
  own dual dating / Norway 1913 / Italy 1946). todd_refs 7/1.
- Corpus block: "implemented 7/24 (birth_rate_fertility 111,
  suicide_rate 80, infant_mortality 52, life_expectancy 26,
  homicide_rate 25, same_sex_marriage_legalization_year 13,
  universal_suffrage_introduction_year 7); top unimplemented:
  consanguineous_marriage_rate 34..." — the backlog's head unchanged.
- Tests: 253/253.

### Known limitations
- crude_birth_rate's unresolved names are the PENDING classes only
  (Saint Helena ex. dep. — the same sub-territory question as Table
  15; Saint-Barthélemy, Saint Helena: Ascension; the WB's Kosovo and
  Channel Islands) — no real country missing.
- The markers carry no witness tier BY CONSTRUCTION (nothing upstream
  to witness — the citation is the origin); their dating conventions
  (effective year vs signature, nationwide ruling vs statute, male
  grant vs women's completion) are the one interpretive layer, carried
  per-row in definition_note, reviewable in git.
- industrial_employment_share remains unimplemented with the probe
  record documenting WHY (no as-reported share door exists; the
  derivation refusal; the pending composite-derived-layer decision).
- The Table 9 Number block (live-birth counts) is wired in the parser
  (the grammar fix was its own test) but not as an indicator — one
  `field: number` config away if ever demanded.

## 2026-09-19 — v14: birth_rate_fertility, the eighth indicator — the
## corpus's #1 — and the Eurostat collector (the TFR-vs-CBR decision)

**No dist contract change (additive):** the seven existing indicators are
bit-identical to v13 (verified byte-for-byte, data and witnesses and every
other key); the additions are one NEW indicator file
(birth_rate_fertility.json), a new provider in the registry (eurostat,
collector tier), a new root (eurostat_demo), and todd_corpus.json's ONE
designed flip (its #1 becomes implemented: 4/24 -> 5/24). Four new raw
snapshots (Eurostat main + the two geo-pinned French series + the WB
TFRT witness door).

### Context
v14 was green-lit in conversation with the TFR-vs-CBR question left to
answer ("on peut se lancer sur la V14 ! Mais avant, c'est quoi la
difference entre TFR et CBR ?" — the v13 roadmap had flagged the choice).
The answer is the decision this entry documents: Todd's variable is
FERTILITY PER WOMAN — the corpus's own notes say it (birth_rate_fertility
carries 111 citations across 16/16 books, the only metric Todd uses in
every book, and its rows read "World TFR decline", "TFR trends 1965-77",
"onset dates", "threshold crossings") — because the crude birth rate
(births per 1,000 total population) is dragged by age structure while
the TFR (the synthetic children-per-woman passing through one year's
age-specific rates) is structure-free and comparable across Todd's full
span; the replacement threshold (~2.1) against which he reads every
series is native to it. The CBR face (the collector's own natalite
print) is recorded as the unwired companion door — a future
crude_birth_rate decision, one DYB parser away. The constitution set
the hard constraint: the canonical tier must be a collector, and the
probes found exactly ONE collector wire that prints a national TFR —
Eurostat's demo_find. Ediz's v13 review is deferred; v14 shipped on the
standing corpus-driven roadmap.

### Investigated
- The DYB fertility tables (files downloaded and parsed before any
  code): Table 9 = "Live births and crude birth rates, by urban/rural
  residence" (the collector's CBR, the Table 15/17 wide layout, quality
  codes, 2020-2024 window); Table 10 = "Live births by age of mother
  and sex of child, general and age-specific fertility rates"
  (latest-available-year cross-sections like Table 21) — verified on
  the 2024 file to carry NO TFR column: summing the printed ASFR would
  be a derivation the canonical tier refuses by constitution.
- The OECD SDMX registry (all 1,548 dataflows, live): no national
  fertility dataflow — DSD_REG_DEMO@DF_FERTILITY is TL2/TL3 REGIONAL
  demography; the Family Database is not on SDMX.
- The harmonized doors (live): WB SP.DYN.TFRT.IN (TFR, ~200 countries,
  1960-2024, FRA 2022 = 1.78) and SP.DYN.CBRT.IN (the CBR twin, 10.7);
  GHO carries 'tfr' ("Total fertility rate (per woman)" — a third WPP
  door, unwired on the one-witness-door discipline); OWID
  'children-per-woman' (pure WPP, 1950-2023, 254 entities) and
  'total-fertility-rate' (WPP + pre-1950 depth for a handful — Sweden
  from 1891; would need its own composite root).
- Eurostat demo_find/TOTFERRT (live, the canonical): 58 geo x 1960-2024,
  2,126 valued cells — Western Europe annual from 1960 (65 points
  each); the Eastern partnership partially (Russia 2006-2010 = 5 points
  1.30->1.57, Belarus to 2018, Ukraine to 2019, Moldova to 2023); the
  UK to 2018 (Brexit ended the series); Bosnia prints no point at all.
  The codelist's own quirks: EL/UK/FX/XK are codes pycountry cannot
  answer (mapped explicitly; Kosovo flows to the unresolved report);
  DE_TOT prints values IDENTICAL to DE on all 25 overlapping years
  (dropped, logged); per-observation status flags (b = break, e =
  estimated, p = provisional — FR 2014 'b', FR 2018/2022-2024 'p',
  DE 2023 'b') transported as-reported. THE FRANCE VARIANT PAIR: FX
  "Metropolitan France" 1960-2012 (53 points — the France of Todd's
  books) and FR "France" 1998-2024 (27 points, whole France incl.
  overseas departments; the overlap differs: 1998 1.76 vs 1.78, 2000
  1.87 vs 1.89, 2010 2.02 vs 2.03) — two prints of one collector, wired
  as separate geo-pinned sources so the merge arbitrates the 1998-2012
  overlap by priority with every discarded value logged.
- Slice max verified: Ireland 1964 = 4.07 (the collector's own maximum);
  the witness's WPP tail peaks at Yemen 1985 = 8.864 — the plausible
  bound is 0-10 (headroom for the modeled tail without swallowing a
  per-1,000 misload).

### Added
- **Provider `eurostat`** (collector tier, the seventh provider): the
  demo_find connector (`src/connectors/eurostat.py`) — one dataset by
  design (another dataset = another dispatch decision, the DYB-table
  scope); source_refs 'demo_find/TOTFERRT' (all countries) and
  'demo_find/TOTFERRT/{geo}' (the geo-pinned series doors); pin-guards
  on the dimension layout, freq, indic_de and the geo pin; the
  aggregate/DE_TOT/France-variant drops logged at parse (the v11.1
  discipline); the EL/UK/FX explicit ISO3 overrides; XK deliberately
  unresolved. Root `eurostat_demo` added to the registry; layer
  "collector"; citation/license maps extended.
- **Indicator `birth_rate_fertility`** (the corpus's #1, todd_core):
  unit births_per_woman, family society (the corpus's own weighted-
  majority resolution), three Eurostat canonical sources (main priority
  1, FR priority 2, FX priority 3 — FR wins the seam's overlap, the
  later-maintained national series) + the WPP witness
  (SP.DYN.TFRT.IN, priority 4, root un_wpp). No sex split by
  construction (a synthetic measure over women's lifetimes);
  higher_is_better=false documented as the least-misleading default
  (the corpus's dominant signal is the transition itself, not a
  direction); plausible 0-10.
- Fixtures: the Eurostat trio (main miniature with the codelist quirks,
  FX/FR geo-pinned miniatures with the seam's own flags — anchors are
  the live-probed numbers, the v13 precedent) + a dedicated WB TFRT
  page fixture (the shared IMRT page retargeted would print per-1,000
  values outside the TFR's bound).
- Tests: 225 -> 240 (+15) — 13 connector tests (drops logged, quirks,
  flags, pin-guards, field refusal), 2 integration tests (the seam with
  its 2 provenance arbitrations on the fixture data, the corpus's #1
  flipping to implemented), the corpus/stats pins updated (5/24, top
  unimplemented consanguineous_marriage_rate 34).

### Changed
- Nothing structural. todd_corpus.json flips exactly one metric's
  implemented flag (the #1) and its meta count (4 -> 5) — the designed
  change, verified entry-by-entry against the v13 dist. The shared WB
  seed gains a TFRT branch (its own page fixture); no existing test
  changed meaning.

### Verified (live, frozen at delivery)
- Fetch: 4/4 snapshots, 0 failure — eurostat main 1,892 records (129
  aggregate rows + 25 DE_TOT + 80 France-variant rows dropped, logged),
  FR 27, FX 53, WB TFRT 14,322 records (3,168 aggregate rows skipped).
- Dist: canonical 1,953 points = 1,953 valued + 0 explicit gaps, 46
  entities, 1960-2024, all eurostat; witness 14,190 points, 215
  entities, 1960-2025 (the WDI grid, trailing-2025 nulls as explicit
  gaps). The seam: FRA 1960 = 2.73 (FX), FRA 1994 = 1.66 (the trough,
  FX), FRA 2000 = 1.89 / FRA 2012 = 2.01 (FR wins the overlap), FRA
  2023 = 1.66 provisional 'p' — with 15 FRA arbitrations logged in
  provenance.json, every retained = the FR source, the 2000 discard =
  FX 1.87. IE 1964 = 4.07 the live max; RUS 2008 = 1.49; GBR 2012 =
  1.92 and GRC 1994 = 1.33 (the codelist quirks); DEU 2023 = 1.39
  quality_code 'b'. Witness: FRA 2022 = 1.78 (the collector prints the
  same — WPP anchors on the national series), RUS 1990 = 1.892, YEM
  1985 = 8.864 inside the bound.
- The additive contract: the 7 old indicator files bit-identical to
  v13; entities.json bit-identical; catalog entries unchanged + the new
  one; the corpus's one designed flip; unresolved = the pending
  Kosovo/Channel-Islands class only. Double `cli rebuild` deterministic
  (identical dist hash). 240/240 tests.

### Known limitations
- No 19th-century history on the canonical tier (Eurostat starts 1960):
  Todd's 1870-1930 European transition onset dates are book data —
  territory for the curated tier or the HFD decision (the HMD-class
  pending decision, now recorded beside HMD/CLIO-INFRA in
  sources.yaml).
- The collector's honest freezes: Russia 2006-2010 only, Ukraine to
  2019, Belarus to 2018, the UK to 2018 (Brexit), Bosnia never, Kosovo
  2016-2019 printed but unresolved (the pending class). The worldwide
  face rides the WPP witness alone outside Europe — that IS the
  metric's honest reality (TFR is an estimated quantity where
  registration is incomplete), displayed by the tier split.
- The witness carries no vintage pinning (WPP revisions arrive
  silently). Unwired doors recorded for the next decisions: GHO 'tfr'
  (third WPP door), OWID 'children-per-woman' / 'total-fertility-rate'
  (WPP + the few pre-1950 runs), DYB Table 9 (the CBR companion, one
  parser away — the future crude_birth_rate), DYB Table 10 (GFR + ASFR
  cross-sections), HFD (France from 1817).

## 2026-09-19 — v13: the corpus enters the pipeline (todd_refs) and
## suicide_rate, the seventh indicator — the corpus's #2

**No dist contract change (additive):** the six existing indicators keep
their v4 point schema and their values bit-for-bit (verified: data and
witnesses arrays identical to v12 on all six); the additions are one NEW
indicator file (suicide_rate.json), one new root in the registry
(who_ghe), the `todd_refs` key on the three Todd-core indicator files
and their catalog entries, and a NEW dist file (todd_corpus.json). Two
new raw snapshots (OECD CICDHARM, GHO SDGSUICIDE).

### Context
Ediz's mega-compilation of Todd's metrics (announced since v11 as "OCR in
progress", delivered as todd_core.csv — 117 rows, 24 metrics, 16 books,
483 citations, one row per metric x book with a citation count) arrived
and was explored before any code moved: the corpus's #2 by citations is
suicide_rate (80 citations across 11 books — the flagship of Le Fou et
le Prolétaire at 38 and a pivot of La Chute finale at 15), it was NOT
implemented, and the OECD dataflow serving homicide already carries it.
Decisions taken in conversation: (a) the CSV is the source of truth,
stays outside the repo untouched, and enters as a generated one-way
transform (Ediz: "le faire passer par un YAML est plus logique"); (b)
v13 = the corpus metadata + suicide_rate together; (c) Ediz's standing
directive — metrics Todd uses within limited windows get taken IN FULL
(all countries, all years, within what the providers publish), which is
already the pipeline's fetch discipline and is restated here as a rule.
ADR-0009 records the whole design.

### Investigated
- The corpus itself (scripts/analyze_todd_core.py): 24 unique metrics;
  citation ranking birth_rate_fertility 111 (16/16 books) > suicide_rate
  80 > infant_mortality 52 (implemented) > consanguineous_marriage_rate
  34 > industrial_employment_share 30 > life_expectancy 26 (implemented)
  > homicide_rate 25 (implemented). Two CSV quirks caught by the
  normalizer's validations: the `family` column labels a handful of rows
  by book context (consanguineous: society 18 cits vs demography 16;
  birth_rate: society 90 vs demography 21) and every row carries
  status=not_implemented — both handled by rule (below), neither silent.
- OECD DF_COM cause list (probe, FRA/M/2021 all-causes): 50 DEATH_CAUSE
  codes; CICDHARM (intentional self-harm) and CICDCIRR (cirrhose) both
  present. CICDHARM full slice verified live: 46 countries, 1960-2024,
  7,225 rows, ZERO null observations, as-reported max LTU 1994 M 83.5
  (Lithuania's post-Soviet peak sits ABOVE Russia's 1994 M 73.9 — the
  plausible_range is 0-100 with the rationale documented).
- The witness door hunt: GHO's indicator index returns FIVE suicide
  indicators; SDGSUICIDE ("Crude suicide rates per 100 000") is the
  crude one — matching the canonical unit — and sex-split on Dim1.
  MH_12 is age-standardized (rejected: the witness must compare like
  with like on measure); SDG_SH_STA_SCIDEN is counts. OWID's
  death-rate-from-suicides-ghe door ("Death rate from self-harm among
  both sexes", 2000-2021) is the same GHE root through another door —
  probed (RUS 2000 = 52.72 vs GHO's 53.06 BTSX: different vintages of
  one root) and deliberately NOT wired (one witness door is the minimal
  honest choice; recorded as the natural second door, like v12's unwired
  GHO maternal doors).
- The SDGSUICIDE hidden dimension (the trap of this delivery): the raw
  payload counts 19,041 records for 12,210 (country, year, sex) keys —
  Dim2Type=AGEGROUP disaggregates the LATEST year (2021) into 11
  overlapping age bands printed beside the all-ages record, for every
  key (6,105 slice rows). Verified live: the ALL-AGES series is uniform
  (every kept record carries Dim2=AGEGROUP_YEARSALL, plus Low/High
  uncertainty intervals on all 12,210), exactly one per key, zero nulls,
  zero keys missing their all-ages record. A parser without a Dim2 rule
  would have ingested duplicates — the homicide-era multi-slice trap
  again, one dimension deeper.
- The founding divergence, live on both sides: Russia male 2000 prints
  69.8 as-reported (OECD/WHO-MDB) vs 95.20444591 modeled (GHE/GHO) —
  the ill-defined-causes redistribution, a +36% uplift that IS the
  reclassification sensitivity the schema's own docstring promises for
  suicides. 1994 as-reported: M 73.9 / F 13.2 (5.6x). GHE 2021 (the
  disaggregated year): RUS M 36.68325073 / BTSX 21.37479131 / F 8.09
  (all-ages record kept, slices dropped).

### Added
- `scripts/normalize_todd_refs.py` + the generated
  `config/todd_refs.yaml` (committed): the one-way transform, ADR-0009.
  Deterministic (same CSV bytes -> same YAML bytes; metrics ranked by
  citations desc then id; refs chronological); validates loudly
  (duplicate metric x book rows, bad book years, non-integer counts,
  exact family ties); the family column resolves by citation-weighted
  majority with the disagreement PRINTED at regen; the CSV's `status`
  column is ignored (implemented-ness is the repo's own state).
- `src/schema/todd_refs.py`: the ToddCorpus/ToddMetric/ToddRef models
  (computed totals — a stored total can drift from the list it
  summarizes, a computed one cannot; meta/body agreement validated).
- `config_loader.load_todd_refs` (absent file -> None: the mechanism is
  inert until the corpus arrives; a present-but-invalid file raises like
  any config) + `cross_validate_todd_core` (the ADR-0009 bijection:
  todd_core=true requires a corpus entry; a corpus metric sharing an
  indicator id requires todd_core=true). Wired into `_load_config` —
  every command now cross-validates.
- Build emission (additive): `todd_refs` on matching indicator payloads
  and catalog entries (join BY ID); `dist/todd_corpus.json` — all 24
  metrics, implemented AND unimplemented, corpus-ranked, with the
  source_csv_sha256 anchoring the dist to the CSV vintage.
- `cli stats`: per-indicator "todd refs" line (citations, books,
  heaviest book) + the closing corpus block (implemented 4/24, top
  unimplemented: birth_rate_fertility 111, consanguineous 34,
  industrial_employment 30...). `check-config` prints the corpus line
  and per-indicator citation counts.
- `config/indicators/suicide_rate.yaml`: the seventh indicator, the
  homicide architecture one cause-code away — canonical = OECD
  DF_COM/CICDHARM crude rate per 100k (root who_mdb), witness = GHO
  SDGSUICIDE crude rate (root who_ghe, the registry's ninth root, added
  with the live-verified 69.8-vs-95.2 rationale in ROOT_LABELS).
  coverage 1960-2024, reliability high, reclassification_sensitive true,
  plausible_range 0-100 (LTU 83.5 + headroom for the GHE tail).
- GHO connector Dim2 rule (the SDGSUICIDE enabler): AGEGROUP ->
  AGEGROUP_YEARSALL kept, age slices dropped at parse (logged, the
  v11.1 honest-drop formula), any OTHER Dim2Type raises (layout change
  -> a human decides). Dim2-less indicators (WHOSIS_000015,
  MDG_0000000001) untouched, regression-tested.
- Tests: 203 -> 225 (+22) — the normalizer contract (determinism,
  ranking, family majority + tie refusal, duplicate/parse refusals,
  status-column absence), the committed corpus's own numbers, the
  cross-validation bijection (both failure directions + the real-config
  pass), the GHO Dim2 rule (all-ages kept, slices dropped + logged,
  unknown Dim2Type refused, Dim2-less unaffected), the suicide
  integration (sex split, the 69.8/95.2 divergence pair side by side,
  YEARSALL resolution on the disaggregated year, LTU max inside bounds),
  the todd_refs emission (matching-only, catalog mirror, heaviest book =
  Le Fou et le Prolétaire 38, La Chute finale year_raw 1976/1990), the
  corpus roadmap file, and the stats corpus lines.
- Fixtures: oecd_suicide_sdmx.csv + gho_sdgsuicide_sample.json (real
  probed anchors — the divergence pair is the test's subject — plus
  synthetic fills; the mixed practice documented in fixtures/README.md);
  conftest gained fixture-selecting params on the OECD/GHO seeds (the
  OECD seed now pins the cause from the source_ref like production) and
  the integration harness loads + cross-validates the REAL committed
  corpus exactly like cmd_rebuild.

### Verified (live, frozen at delivery 2026-09-19)
- Fetch: OECD CICDHARM 7,225 records; GHO SDGSUICIDE 19,041 rows ->
  12,210 records parsed (6,105 age slices + 726 aggregates dropped,
  both drop lines logged), 4,070 per sex, 2000-2021.
- Rebuild: suicide_rate canonical 7,225 points = 7,225 valued, 46
  entities, 1960-2024; roots canonical who_mdb (oecd); witness who_ghe
  (who_gho) — the first who_ghe-root indicator. Witness: 12,210 points,
  185 entities, 2000-2021. The other six indicators' canonical counts
  unchanged (7,193 / 2,702 / 6,018 / 2,528 / 2,834 / 1,898).
- Diff v12 -> v13 (scripts/verify_v13_diff.py, all PASS): data and
  witnesses bit-identical on the six; additive keys only (todd_refs on
  IMR/LE/homicide); catalog entries unchanged except the additive key +
  the new suicide entry; entities.json bit-identical; todd_corpus.json
  and suicide_rate.json new. Validation: zero range violation, zero
  duplicate. Double rebuild: bit-identical (deterministic).
- Spot-checks from the dist: RUS 1994 M 73.9 / F 13.2; RUS 2000 M 69.8
  (canonical) vs 95.20444591 (witness) — the ill-defined redistribution
  displayed side by side; LTU 1994 M 83.5; FRA 1979 18.2; RUS 2021 M
  36.68325073 (the YEARSALL record, not a slice).
- Corpus emission: todd_corpus.json = 24 metrics, 483 citations, 16
  books, 4 implemented; #1 unimplemented = birth_rate_fertility 111;
  suicide's todd_refs = 80 citations / 11 books / heaviest Le Fou et le
  Prolétaire 1979 (38).

### Known limitations
- The witness's Low/High uncertainty intervals remain dropped at parse
  (the documented witness-CI decision, unchanged since v10; every
  SDGSUICIDE all-ages record carries one).
- The OWID door of the GHE root (death-rate-from-suicides-ghe,
  both-sexes only) is probed and unwired — the natural second door when
  the two-doors-one-root display is wanted (v11 precedent).
- The corpus's historical-window metrics (suicide France 1835-1977,
  illegitimacy 1900-1973, Algeria 1898...) are book data: curated-tier
  territory, out of any living provider's reach.
- The bijection makes todd_core=true fail the build without corpus
  backing — if the CSV ever loses a metric behind a flag, the build
  says so instead of guessing (ADR-0009's accepted negative).

## 2026-09-13 — v12: the maternal bloc — 2015/table17 wired, the second
## MMEIG door (SH.STA.MMRT), and maternal_deaths, the sixth indicator

**No dist contract change (additive):** the existing indicators' files keep
the v4 point schema; the additions are one NEW indicator file
(maternal_deaths.json), one new witness series on
maternal_mortality_ratio.json (same shape as every witness), 16 new raw
snapshots (the 13 Table 17 editions re-fetched at the number block, the
2015 edition at the rate block, and the two WB codes), and the
v12 canonical deltas on the maternal ratio (+8 keys, 12 gap-to-valued, 15
value re-arbitrations by the 2015 vintage — itemized below).

### Context
Ediz chose option A of the v11 next-step proposal ("Je veux qu'on continue
uniquement sur l'option A. Pour le reste, on verra plus tard." — the
alternative, the P5 education/fertility suite, waits for his in-progress
mega-compilation of Todd's metrics, currently in OCR): the deferred
maternal bloc, exactly as recorded in the v11 stage summary — 2015/table17
+ SH.STA.MMRT + maternal_deaths. The v9 delivery had deliberately deferred
one piece of its own scope ("wiring the counts as a second indicator is a
separate decision") and v10 had recovered the 2015 edition for the other
tables while postponing its Table 17 ("one re-arbitration per delivery");
this delivery is those two debts plus the World Bank door.

### Investigated
- 2015/Table17.xls (legacy URL pattern, recovered v10, re-verified live):
  alive, 579,624 bytes, parses clean at BOTH blocks — Rate: 770 records /
  509 valued / 77 countries, Number: 1,240 records / 705 valued / 124
  countries, years 2005-2014, ZERO unresolved entity names. The counts
  block serves 47 MORE countries than the ratio block in that edition
  alone.
- WB SH.STA.MMRT (probe, countries only after the provider's own
  aggregate drop): 17,490 raw rows -> 14,322 country records, valued
  1985-2023 ANNUAL (>=150 countries every year — not the 5-yearly cadence
  the MMEIG print reports suggest; WDI carries the full annual series),
  7,566 valued + 6,756 null (5,859 outside the series window inside the
  1960-2025 grid + 897 for the 23 entities with no MMEIG estimate).
  Integer print.
- WB SH.MMR.DTHS ("Number of maternal deaths"): same grid, same window —
  the modeled-counts door exists and is the witness maternal_deaths needs.
  OWID's maternal-mortality CSV carries NO deaths column (header verified
  live), so the World Bank is the single deaths door for now.
- GHO carries the same MMEIG family (MDG_0000000026 ratio,
  MORT_MATERNALNUM counts) — noted as the natural third door, deliberately
  NOT wired in v12 (scope discipline: option A only).
- The two MMEIG doors redistribute DIFFERENT ROUNDS: the OWID door the
  2020 round (1751-2020), the WDI door the 2023 round (1985-2023) — their
  divergence on overlapping years (South Sudan 1987: 6,774.7 vs 8,045) is
  the model's own revision, which is why the ratio's plausible_range moves
  7,000 -> 9,000 (a bound left at 7,000 would flag the new door's
  legitimate tail on every build — the cry-wolf the bound exists to
  avoid).
- The "♦" marker is a RATE-row annotation: 341 diamonds on the 2015
  edition's Rate rows, ZERO on its Number rows (verified live) —
  maternal_deaths therefore carries small_base nowhere in the real files.

### Added
- `config/indicators/maternal_deaths.yaml`: the sixth indicator, the
  counts half of the maternal bloc — canonical = UN DYB Table 17 Number
  rows (field: number, 13 editions incl. 2015), witness = worldbank
  SH.MMR.DTHS (root un_mmeig), unit maternal_deaths, reliability medium,
  reclassification_sensitive true, plausible_range 0-200,000 (the two-tier
  band-split rationale documented: canonical tops at Philippines 2008 =
  1,731, witness at India 1985 = 180,000, and Andorra 2023 = 0 is a TRUE
  zero on the witness tier).
- `maternal_mortality_ratio.yaml`: worldbank SH.STA.MMRT as the second
  witness (priority 15, root un_mmeig) — the witness tier becomes two
  doors of one root carrying different rounds.
- 2015/table17 wired on the ratio (priority 9, renumbering 2014->10 ...
  2011->13, OWID witness ->14) and present from the start on
  maternal_deaths' 13-edition loop.
- Tests: +3 (203 total) — the two maternal-bloc integration tests
  (maternal_deaths serves the Number-only countries: Libya 12 / +U /
  absent from the ratio, closed as the v9 deferred decision; the ratio's
  two witness doors + the 13-edition loop + the catalog roots summaries
  unsd_dyb x13 / un_mmeig x2 and x1) and the WB connector pin on the two
  real maternal names (bare codes, sex=None).
- conftest: seed_dyb_table17_snapshot gained the `block` parameter
  (field-faithful seeding: the counts seed now parses the Number rows —
  the default rate seed was silently feeding maternal_deaths the wrong
  block, caught by the new integration test itself) and the two WB
  maternal names joined _WB_INDICATOR_NAMES.

### Changed
- maternal_mortality_ratio canonical, from the 2015 vintage joining the
  arbitration: +8 keys (explicit gaps on 2005-2006 country-years only the
  2015 edition prints), 12 gap-to-valued (e.g. Bahamas 2012: None ->
  67.12911; Kazakhstan 2013: None -> 10.5881), 15 value re-arbitrations
  (e.g. Colombia 2006: 72.6433 -> 73.8338, Finland 2005: 5.1953 ->
  5.2195 — later edition wins, logged), 144 annotation-only re-winnings;
  0 keys removed, 0 witness values touched (the OWID door is
  bit-identical). 1,898 points = 1,114 valued + 784 gaps (was 1,890 =
  1,102 + 788).
- plausible_range 0-9,000 (was 0-7,000, see Investigated), reliability_
  criteria/license/notes texts updated for the 13 editions + the two-door
  witness tier; sources.yaml (un_dyb TABLE 17 block: 13 editions, both
  blocks wired; worldbank block: the maternal codes' bare-code/integer/
  grid semantics); README, architecture.md, the-measurement-problem.md
  (§7.2: both blocks, the counts' 131 vs the ratio's 97 entities).

### Verified
- Live fetch 16/16 (2015/table17 rate; SH.STA.MMRT; 13 editions at the
  number block; SH.MMR.DTHS), 0 failure; raw tree restored from the v11.1
  zip (204 snapshots) then rebuilt. `cli stats`:
  maternal_deaths canonical 2,834 = 1,584 valued + 1,250 explicit gaps /
  131 entities with >=1 valued (137 total incl. gap-only) / 2001-2022;
  witness SH.MMR.DTHS 14,190 points, 215 entities, 1960-2025 (the WDI
  grid). maternal_mortality_ratio canonical 1,898 = 1,114 + 784 / 97
  entities; witnesses owid 8,868 (1751-2020) + worldbank 14,190
  (1960-2025).
- The four OTHER indicators: canonical and witnesses bit-identical to
  v11.1 (diff itemized per key, 0 added / 0 removed / 0 changed);
  entities.json identical; catalog gains only maternal_deaths + the
  ratio's documentation keys.
- Spot-checks read from the rebuilt dist: Libya canonical deaths
  2016 = 12 (+U code, '...' gaps around it — the exact v9-documented
  case) and 2017 = 10, while the ratio keeps Libya absent; the two doors
  side by side — South Sudan 1987: 6,774.713 (OWID, 2020 round) vs
  8,045 (WB, 2023 round), Egypt 2020: 16.82 vs 31, Russia 2019: 7.45 vs
  12; France 2020 deaths: 36 registered vs 62 modeled (the collector's
  undercount, displayed); 2015/table17 wins 167 ratio keys (99 valued)
  and 87 of the loop's arbitrations.
- Validation: 0 range violation on every indicator and every witness
  (the 9,000 / 200,000 bounds hold the real bands, South Sudan 8,045
  and India 180,000 included); full test suite 203/203 on the repo and
  on the packaged extract.

### Known limitations
- The WDI maternal witnesses carry the provider's full 1960-2025 grid:
  5,859 outside-window null slots per code ride as explicit gap points
  (1960-1984 + 2024-2025) — the honest print of a year slot with no
  estimate, same discipline as the IGME codes' trailing-2025 slots, more
  of them; a frontend that wants a tighter view reads the witness's own
  year range from `cli stats` / n_points coverage.
- Kosovo and Channel Islands stay unresolved on the WB doors (the v11
  pending product decision, unchanged — the OWID_KOS class); the 23
  WDI-classified entities with no MMEIG estimate at all stay as all-gap
  witness series.
- GHO's MMEIG doors (MDG_0000000026 / MORT_MATERNALNUM) remain unwired —
  the natural third door when phase 5's GHO dims handling grows.
- Russia's recent Table 17 rows print '...' on both blocks (2018-2022):
  the collector's honest degradation, kept as explicit gaps — the
  2019-2022 Russian maternal story lives on the witness tier.

## 2026-09-13 — v11.1: the v11 GHO fix applied in full — every false
## "raw snapshot" claim corrected repo-wide

### Context
The v11 fix reworded the GHO docstring's false claim that the dropped
aggregate rows "stay in the raw snapshot" — but the rewording was
applied to the docstring only. The log line that runs at every fetch
still said the old wording verbatim, contradicting the corrected
docstring in the same file (caught by the reviewer after delivery, not
by any check of the delivery itself — nothing was looking at the log
text). Completing it meant asking where else the same false assumption
lived, and the sweep found it in seven more places: a "raw snapshot"
in this repo is the PARSED-RECORDS file fetch.py writes
(`_write_snapshot` = `asdict(RawRecord)` + the footnotes block), never
the provider's raw payload — every claim built on the other reading
was false with it.

### Fixed
- `src/connectors/gho.py`, the fetch log line (the reported bug): the
  dropped rows are "not stored anywhere, this log line is the record
  of the drop, re-fetchable from source_url" — the same facts as the
  corrected docstring, the same construction as the World Bank
  connector's log (checked clean: one place, consistent).
- `src/connectors/gho.py`, the witness-CI bullet: "Value"/Low/High do
  NOT "live in the raw snapshot untouched" — no RawRecord field exists
  for them; they are dropped at parse, stored nowhere, re-fetchable
  from source_url. The old text also called that drop "not a silent
  drop" — it had no record at all; the corrected bullet is the record.
- `tests/test_gho_connector.py`: the comment in
  test_parse_gho_keeps_country_rows_only carried the same false phrase;
  and a NEW regression test pins the log line via caplog ("not stored
  anywhere" present, "stay in the raw snapshot" absent) — the check
  that was missing when the half-fix shipped.
- `src/connectors/dyb.py`, both Table 21/22 spots: the other 20 ages
  do NOT "stay in the raw snapshots", and wiring one is NOT "no
  re-fetch" — the snapshot holds the selected column's records only
  (the XLS payload is parsed in memory and never persisted), so
  another age is another indicator + config + a re-fetch of the same
  stable URL.
- `config/sources.yaml` + `config/indicators/life_expectancy_60.yaml`:
  the same claims in the who_gho notes, the sources comment, the
  reliability_criteria and the notes (the text the dist regenerates
  from) — all reworded to the parsed-records truth.

### Changed
- data/dist regenerated (offline `cli rebuild` from the v11 zip's raw
  snapshots, through the corrected config): catalog.json and
  life_expectancy_60.json pick up the corrected reliability_criteria /
  notes texts — the only content change in the shipped dist.

### Verified
- Full test suite: 200 passed (v11: 199) — the caplog regression test
  included; the only remaining "stay in the raw snapshot" in src/,
  config/ or tests/ is its own negative assertion.
- The regenerated dist differs from v11's by EXACTLY three lines —
  life_expectancy_60.json's reliability_criteria + notes and
  catalog.json's reliability_criteria, all documentation; every data
  value, the four other indicators' files and entities.json are
  bit-identical. `cli stats`: the v11 counts unchanged (canonical IMR
  2,702 / LE 6,018 / LE-60 2,528 / maternal 1,890 / homicide 7,193;
  every witness series identical).
- The sweep itself: grep for "raw snapshot" across src/, config/,
  tests/ and docs/ — the surviving claims are the true mechanism
  descriptions (normalize.py's latest-snapshot selection, the git
  policy line in the-measurement-problem.md) and the frozen changelog
  vintages named below. OWID, OECD, curated: no such claim.

### Known limitations
- The v10 and v11 entries keep their original wording (vintages are
  never edited): v10's "Verified (live)" section says the 726 non-country
  rows were "filtered at parse, kept in the raw snapshot" and its Added
  section "the 20 other ages stay in the raw snapshots, one config
  away"; v11's Known limitations say the witness CIs "stay in the raw
  snapshot" and "another age = another config, no re-fetch" — the same
  false claims, corrected here.
- The GHO parser still does not count the dropped "Value"/Low/High
  fields at runtime (the docstring bullet is their record); a log line
  would mean reading fields the parser deliberately never touches.

## 2026-09-13 — v11: the phase-5 witnesses — the World Bank connector,
## the root genealogy field, and the IGME triangle made executable

**No dist contract change (additive):** the existing indicators' files keep
the v4 point schema; the additions are new witness series (same shape) and
the `root`/`root_label` keys on `sources[]`/`witnesses[]` entries plus the
per-indicator `roots` summary in `catalog.json` — all additive. **Config
schema:** `SourceRef.root` is now REQUIRED (a deliberate enforcement —
the genealogy can never silently go missing when a source is added); all
in-repo configs declare it.

### Context
The v10 review approved, Ediz green-lit the next block ("V10 approuvé !
On peut continuer !"): P5 (le monde) — the World Bank/GHO witnesses the
architecture had planned since phase 1, together with the `family`
root-genealogy field of the-measurement-problem.md section 5.1, whose
implementation was explicitly deferred "once more worldbank/gho
indicators land". The GHO connector arriving in v10 and LE-60 being done,
this delivery is that moment: the World Bank lands as a witness provider,
GHO gains its second indicator, and every source starts declaring where
its numbers were actually made.

### Investigated (live, 2026-09-13)
- The WB v2 API shape: JSON arrays `[meta, rows]`; pagination is NOT
  optional (documented default per_page = 50); per_page=5000 verified
  accepted, answering each wired code's ~17.5k rows in 4 pages.
- /country/all includes 78 AGGREGATE entities beside the 217 countries,
  and the data rows carry no region field. The provider's own /country
  metadata (region.id "NA") classifies them — but the join needs BOTH
  keys: regional aggregates carry their ISO3-like code in
  `countryiso3code`, while the five income-group aggregates print an
  EMPTY `countryiso3code` and join on the two-letter `country.id`
  instead (verified live: "High income" = HIC arrives as id "XD" with
  iso3 ""; the first fetch surfaced them in unresolved.json, 66 rows
  each, and the connector was fixed before delivery — filtered at parse
  like every other aggregate).
- WDI's sex convention lives in the CODE suffix (.MA.IN / .FE.IN / the
  bare code), and every data row prints its indicator name
  ("..., male (per 1,000 live births)") — the connector derives the sex
  from the suffix and cross-checks it bidirectionally against the name
  (the OECD pin-guard precedent).
- WDI redistributes IGME/WPP ROUNDED to at most one decimal: France 2020
  female IMR prints 3 where GHO carries 3.023055115; Russia 1990 male
  prints 20.1 where GHO carries 20.056990877. Same root, coarser print —
  the honest genealogy footnote, kept as display material.
- GHO MDG_0000000001 ("Infant mortality rate"): Dim1Type = SEX only,
  SpatialDimType = COUNTRY for countries, 39,279 country rows, years
  1931-2024, zero null NumericValues — the v10 connector's SEX-only
  shape held, the second indicator wired with ZERO new connector code.
  SP.DYN.LE60.IN re-verified INVALID on the WB API (the GHO WHOSIS
  witness remains LE-60's only door).
- The IGME triangle, value-level: OWID France 2020 = 3.3304706 where GHO
  MDG = 3.330470548; Russia 1990 = 17.46196 vs 17.461960157. Seven
  significant digits of identity — the section-1 claim, now in the dist.

### Added
- `src/connectors/worldbank.py` — the phase-5 provider: paginated v2
  JSON, the provider's own /country aggregate classification fetched
  once per connector (both join keys), the sex suffix convention with
  the bidirectional name pin-guard, null values as explicit gap points,
  annual dates asserted. Kosovo and the Channel Islands are NOT
  aggregates in that classification: they flow to normalize's
  unresolved report by name — a pending product decision, the same
  class as OWID's OWID_KOS pseudo-codes.
- The `root` genealogy field (the-measurement-problem.md section 5.1,
  implemented): `SourceRef.root` — REQUIRED, validated against the
  closed `ROOT_LABELS` registry (un_igme, un_wpp, un_mmeig, who_mdb,
  unsd_dyb, unodc, owid_longrun_composite, soviet_official). Emitted on
  the dist's `sources[]` and `witnesses[]` (id + label), summarized
  per-role with door counts in `catalog.json`, and printed by
  `cli stats` as the genealogy line.
- Five witness sources: infant_mortality + worldbank
  SP.DYN.IMRT.MA.IN / SP.DYN.IMRT.FE.IN (sex-split, IGME) + who_gho
  MDG_0000000001 (the third IGME door, sex-split MLE/FMLE/BTSX);
  life_expectancy + worldbank SP.DYN.LE00.MA.IN / SP.DYN.LE00.FE.IN
  (sex-split, pure WPP). LE's witness tier now deliberately carries TWO
  different roots — OWID's mixed long-run compilation vs the World
  Bank's pure WPP.

### Fixed
- The GHO connector docstring claimed the dropped aggregate rows "stay
  in the raw snapshot" — they do not (the snapshot holds the parsed
  COUNTRY records, like every connector here). Reworded to the honest
  description; the docstring also now names its second indicator.

### Verified (live, `python -m src.cli stats` + scripts/spotcheck_v11.py,
frozen at delivery)
- Canonical tiers UNTOUCHED, bit-identical on all five indicators (IMR
  2,702; LE 6,018; LE-60 2,528; maternal 1,890; homicide 7,193); the
  pre-existing witness series bit-identical; entities.json identical.
  The v10 -> v11 diff is additive-only: 3 new witness series on
  infant_mortality, 2 on life_expectancy, root/root_label on every
  source, roots in the catalog (itemized by scripts/verify_v11_diff.py:
  CLEAN).
- infant_mortality witnesses: owid 13,202 points / 200 entities /
  1931-2024; who_gho MDG_0000000001 39,159 / 199 / 1931-2024; worldbank
  SP.DYN.IMRT.MA.IN and .FE.IN 14,190 each / 215 entities / 1960-2025
  (the fetched 14,322 rows per code = 17,490 total minus 3,168 aggregate
  rows filtered at parse; unresolved: Kosovo, Channel Islands).
- life_expectancy witnesses: owid 19,468 / 237 / 1543-2023; worldbank
  SP.DYN.LE00.MA.IN and .FE.IN 14,190 each / 215 / 1960-2025.
- The genealogy lines (cli stats): infant_mortality "witness: un_igme
  (owid, who_gho, worldbank x2)"; life_expectancy "witness:
  owid_longrun_composite (owid) + un_wpp (worldbank x2)".
- The triangle in the dist: France 2020 BTSX 3.3304706 (owid) =
  3.330470548 (gho); Russia 1990 17.46196 = 17.461960157; the WB doors
  print the rounded 3.0 / 20.1 (vs GHO female 3.023055115 / male
  20.056990877).
- The WPP-vs-collector convergence: worldbank LE male Russia 2012 =
  64.56 = the DYB Table 4 as-reported value (Russia's last life table);
  1994 male = 57.55 where the collector is absent.
- The WDI trailing-2025 slots: 215 of 215 year-2025 points per WB code
  are explicit null gap points.
- Validation 0 range violations / 0 duplicates on all five indicators;
  offline rebuild twice -> bit-identical dist.
- 199/199 tests (+23: 17 World Bank connector, 2 schema root validators,
  3 integration, 1 stats roots line).

### Known limitations
- WDI prints its redistribution rounded to at most one decimal: the
  World Bank witnesses are coarser than the OWID/GHO doors of the same
  roots. The divergence display shows it; the root field explains it.
- The WB both-sexes codes (SP.DYN.IMRT.IN, SP.DYN.LE00.IN) are not
  wired: the sex-split codes are the value-add (the canonical tiers are
  sex-split), and the both-sexes witness slot is already covered (OWID
  on both indicators, MDG's BTSX series on infant mortality).
- Kosovo (XKX) and the Channel Islands (CHI) stay unresolved by name —
  a pending product decision (add like an entity, or document as
  out-of-scope), same class as OWID's OWID_KOS pseudo-codes.
- SH.STA.MMRT (the World Bank's MMEIG maternal door) identified live
  but not wired: the maternal block (its 2015 vintage re-arbitration,
  the maternal_deaths counts indicator) belongs to its own delivery.
- GHO indicators carrying non-SEX Dim1 types remain unwired (none
  needed so far; the connector still raises loudly on them).

## 2026-09-13 — v10: LE-60 (the fifth indicator, DYB Tables 21/22 + the
first GHO witness), the 2015 edition recovered, and the SpreadsheetML
footnote-refs fix

**No dist contract change:** the existing indicators' files keep the v4
point schema; the new indicator's file is an additive contract (same
shape, new id). Values inside infant_mortality / life_expectancy changed
through ordinary vintage arbitration (the 2015 edition) and two entity
resolutions — itemized below, nothing else moved.

### Context
The v9.1 review settled, Ediz green-lit the next block ("on peut
continuer"): the v10 planned in Task 20's investigation — LE-60, the
companion indicator the brief mentions and the Extra board seeds. The
investigation had established that LE-60 is neither a hidden column nor
a new source but a NEW TABLE of the already-wired DYB (same editions,
formats, entity names, vintage discipline), with two live traps: the
21/22 renumbering (the LE-by-age table swaps numbers with the 5qx
probabilities by edition parity) and the cross-section semantics (each
edition prints each country's LATEST available life table — the series is
a stack of cross-sections, not an annual panel). The same investigation
found the 2015 edition recoverable through the legacy URL pattern, a +1
vintage for three indicators.

### Investigated (live, 2026-09-13)
- The renumbering, verified file by file across all 13 wired editions:
  "Life expectancy at specified ages" is table 21 in EVEN editions,
  table 22 in ODD ones; the other number holds the 5qx probabilities —
  SAME layout, different measure. A number-only dispatch would have
  mis-parsed the 5qx silently (its values share the shape); the
  connector now keys on the title TEXT and raises with the parity rule.
- The reference-period convention, verified against the DYB's own cross-
  table correspondence (edition 2017): Table 4's "France 2015 + Roman IV
  (2012-2015)" is the same life table Table 22 prints as "2012 - 2015";
  same for Mauritius 2017/III, Dominican Republic 2015/VI, Chile 2015.
  The year of a printed period is its END year — the collector's own
  convention, now ours. Three countries print actuarial-style periods
  extending beyond the edition year (Dominican Republic / Philippines /
  Yemen "2020 - 2025" in the 2024 edition): kept as printed, year 2025.
- The BIFF year-row gluing ("20103" = 2010 + footnote 3 — years are
  always exactly 4 digits, so the split is deterministic), 146-156
  records carrying refs per BIFF edition.
- The 2015 edition, recovered by direct download through the legacy
  pattern /dyb2015/TableNN.xls (the edition page's own links return
  1,245-byte HTML error pages — that is what kept 2015 out since v7):
  Table04 2.2 MB (1,464 records), Table15 716 KB (625), Table21 468 KB,
  Table22 1.3 MB — all parse clean through the existing machinery.
- The GHO witness, verified live (12,936 rows): ISO3 codes, the SEX
  dimension (MLE/FMLE/BTSX), years 2000-2021, no nulls, no duplicates,
  the provider's own SpatialDimType classifying the 726 non-country
  rows (REGION/GLOBAL/income groups — filtered at parse, kept in the
  raw snapshot). Russia 2012 male = 15.43 modeled vs 15.38 as-reported:
  the divergence display works.

### Added
- `life_expectancy_60`, the FIFTH indicator (Extra board): canonical =
  13 DYB editions (2011-2015 + 2017-2024, table 21 in even editions /
  table 22 in odd ones), sex-split as printed (Male/Female rows — no
  both-sexes column, averaging would be a derivation); witness = who_gho
  WHOSIS_000015 (WPP-derived, 2000-2021). `field: "60"` selects the age
  column; the 20 other ages stay in the raw snapshots, one config away.
- `src/connectors/gho.py` — the first GHO connector (the piece of phase
  5 pulled forward because this indicator needed a witness and OWID
  publishes no age-60 chart, its by-age charts jump 45 -> 65).
  Deliberately minimal: one indicator code per source_ref, COUNTRY rows
  only, the SEX dimension mapped; more GHO indicators = P5.
- `_parse_table21_rows` + `parse_table21`: the by-age table parser
  (age header asserted EXACTLY 0,5,...,100; country -> year -> Male/
  Female blocks; single years and printed periods; '...' kept as
  explicit gaps; the 2024 France dual block — full 2020 table + 2024
  age-0-only — materializes the 2024 LE-60 gap exactly like Table 15's
  "counts published, no rate").
- Edition 2015 wired into infant_mortality (2015/table15) and
  life_expectancy (2015/table04), priorities 10/9 (later edition wins,
  the standard vintage discipline). 13 editions each.
- Entity schema: `source_ids.un_dyb` now accepts a LIST of printed names
  (backward compatible — a bare string still works).

### Changed
- infant_mortality: v9.1 -> v10 = +13 keys (+4 valued +9 gaps, the 2015
  vintage's unique years and the Palestine 2011 rows), 9 values re-
  arbitrated on 2011-2012 overlaps (the 2015 vintage re-reports; every
  arbitration in provenance.json), 155 winner-source shifts. Examples:
  Philippines 2011 12.757308845 -> 12.7573161488; Guatemala 2012 None
  -> 18.32 (the 2015 edition prints a rate the 2014 printed "..." for).
- life_expectancy: +56 keys (+6 valued +50 gaps), 8 values, ALL None ->
  valued (American Samoa 2011, Germany/Malaysia/Rwanda 2012 — the 2015
  edition values what the 2014 left as gaps). No valued point was ever
  overwritten with a different number.
- maternal_mortality_ratio and homicide_rate: NOT A SINGLE value, key or
  annotation changed (maternal is untouched by the 2015 wiring — Table
  17's 2015 vintage is deliberately deferred, one indicator's re-
  arbitration per delivery).
- All 51 un_dyb snapshots re-fetched so every stored record carries the
  footnote-refs fix below (the fix applies at parse time; stored
  snapshots keep the parser they were fetched with — a partial
  application would have made the dist inconsistent edition by edition).

### Fixed
- **The SpreadsheetML footnote-refs silent drop (a v2-era gap).** The
  SpreadsheetML editions 2011-2015 + 2024 wrap their country-level (and
  Table 21 year-row) footnote references in <html:Sup>NN</html:Sup>
  child elements; `_row_values` read `Data.text`, which stops at the
  first child — 65 dropped refs in t21 2024, 90 in t15 2024, 26 in t4
  2024, 6 in t17 2024, across every wired SpreadsheetML edition (the
  BIFF editions glue the same refs as plain text and were fine). Found
  because the v10 fixture wrote the Sup form faithfully and the parser
  test came back with refs=None. Fix: `itertext()`. Effect on the dist:
  728 IMR + 558 LE + 22 maternal points now carry their printed
  footnote_refs (joined to their texts as before); nothing else moved.
- "Micronesia (Federated States of)" (Table 21's parenthesized spelling)
  and "Occupied Palestinian Territory" (the 2011-and-earlier name of the
  State of Palestine) now resolve — the latter was unresolved since v6
  in two other indicators' unresolved.json, closed by the alias-list
  support. LE-60's unresolved is now exactly one deliberate name
  ("Saint Helena ex. dep.", the documented sub-territory question).

### Verified (live, `python -m src.cli stats`, frozen at delivery)
- life_expectancy_60: canonical 2,528 points = 1,754 valued + 774
  explicit gaps; un_dyb 1,754 (1992-2025); 166 entities with >=1 valued
  point (209 total incl. gap-only); witness who_gho:WHOSIS_000015: 12,210
  points, 185 entities, 2000-2021.
- Spot-checks against the source bytes: Russia 2012 M 15.38 / F 20.97
  (from the 2024 vintage; the series freezes at 2012 — 2009, 2011, 2012 —
  exactly the cross-section semantics); France 2020 M 22.77 / F 27.31;
  France 2024 = explicit gap "..." (the dual-block degradation); Mauritius
  2024 = 18.4020081940217 with reference_range "2022 - 2024" and the
  printed Sup footnote joined; Dominican Republic 2025 range "2020 -
  2025"; witness Russia 2012 M 15.43 / F 20.99 (the canonical-vs-model
  spread the front can now display). 550 vintage arbitrations, all
  logged in life_expectancy_60.provenance.json.
- The v9.1 -> v10 diff, itemized above (no key removed anywhere, no
  witness moved anywhere); validation 0 range violations / 0 duplicates
  on all five indicators; offline rebuild twice -> bit-identical dist.
- 176/176 tests (+23: 11 Table 21 parser incl. the 5qx guard and the
  BIFF year-glue, 10 GHO connector, 2 LE-60 integration).

### Known limitations
- LE-60 is a stack of latest-available-year cross-sections: read the
  gaps between a country's points as "no newer life table was
  available", never as missing years of an annual series (Russia's
  frozen 2012 is the canonical example).
- The GHO witness's uncertainty intervals (Low/High in the API payload)
  stay in the raw snapshot; the dist schema does not carry witness CIs
  yet — a schema decision to take explicitly if the frontend needs them.
- The other 20 ages of Tables 21/22 stay unwired (one indicator = one
  age column; another age = another config, no re-fetch).
- Table 17's 2015 vintage deliberately deferred (see Changed); wiring
  it re-arbitrates maternal 2011-2015 and belongs to its own delivery.
- The witness's both-sexes series (BTSX) coexists with the sex-split
  canonical on the same (entity, year) — the merge key keeps them
  apart; a both-sexes CANONICAL series would be a derivation, out of
  scope until a separate decision says otherwise.

## 2026-09-13 — v9.1: the v9 review settled — one retraction (the 5.2
never existed in the data), one reconciliation (the 1,419 by provider),
and `cli stats`

**No dist change:** this delivery touches no pipeline data path —
verified by an offline rebuild producing a bit-identical dist.

### Context
The v9 review checked the changelog's Verified numbers against the data
and came back with two findings, both documentation-level. (1) The IMR
cutover base "1,419" looked wrong: recounting a kept copy of the v8 dist
gave 1,398 valued points / 117 entities, with the v9 total at 2,668.
(2) The spot-check "France 2022 = explicit gap while the MMEIG witness
carries 5.2" did not match the witness, which stops at 2020. Both were
re-investigated from the bytes; one retraction and one reconciliation
follow.

### Investigated (live, 2026-09-13)
- The maternal witness, snapshot AND dist: 9,264 fetched records, 200
  source names -> 189 resolved entities, and NOT ONE carrying a point
  beyond 2020 (185 end at 2020, 3 at 2016, 1 at 2017). France's last
  witness point is 2020 = 7.909. The value 5.2 appears nowhere in the
  fetched data.
- The v8.1 base, rebuilt from the v8.1 code + the raw snapshots shipped
  in the v9 zip: IMR = 1,419 valued / 118 entities, and the v8.1 -> v9
  diff is zero valued points added, changed or lost.
- The review's 1,398 / 117 / 2,668 is those same dists minus exactly the
  21 curated USSR points (entity `ussr`, 1970-1990, provider `curated`):
  1,419 = 1,398 un_dyb (reference years 2007-2024) + 21 curated. Both a
  provider filter and a 2007-2024 year window produce that subset — and
  the docs' own "over 2007-2024" phrasing invited exactly that reading
  (fixed below). The LE figures were exact on both sides: LE has no
  curated points. Either way the review's conclusion held: nothing is
  broken, zero valued points changed.

### Fixed
- **Retracted — the review is right.** v9's "while the MMEIG witness
  carries 5.2" is false: the witness has no 2022 point at all, and
  France's real 2020 value is 7.91. The 5.2 existed only in the
  hand-written test fixture (tests/fixtures/owid_maternal_mortality
  .csv, "France,FRA,2020,5.2") — a fixture number quoted as if it were
  live data. The canonical half of the claim (France 2022 = explicit
  gap, "...", code C) is confirmed correct. The v9 entry stays untouched
  per the house rules; this entry is the retraction of record.
- docs/the-measurement-problem.md: the IMR count now carries the provider
  split and the gap points (the "over 2007-2024" phrasing described only
  the un_dyb subset of the 1,419).

### Added
- `python -m src.cli stats` (src/pipeline/stats.py): emits from the dist
  files themselves every number a Verified section should cite — per
  indicator, canonical total/valued/gaps, the per-provider split of
  valued points with each provider's year range, entity counts
  (gap-only entities distinguished), and each witness's coverage
  (points / entities / year range). The Verified lines below are its
  output; future entries quote it, not memory.
- tests/fixtures/README.md: fixture values are synthetic BY DESIGN and
  deliberately diverge from the live data (the maternal fixture's France
  2020 = 5.2 vs the live 7.91; its witness even runs to 2021 where the
  real snapshot stops at 2020) — the divergence is what makes
  contamination detectable. Fixture numbers must never leave the tests.
- +2 tests (153 total): the provider-split line and the witness-coverage
  line, pinned against the deterministic fixture mini-dist.

### Verified (live, 2026-09-13 — `cli stats` output on the real dist)
- infant_mortality: canonical 2,689 points = 1,419 valued + 1,270
  explicit gaps; valued by provider: un_dyb 1,398 (2007-2024) + curated
  21 (1970-1990); reference years 1970-2024; entities 118 with >=1
  valued point (181 total incl. gap-only). Witness
  owid:infant-mortality: 13,202 points, 200 entities, 1931-2024.
- life_expectancy: canonical 5,962 = 3,018 + 2,944; un_dyb 3,018
  (2007-2024); 182 entities with >=1 valued point (222 total incl.
  gap-only). Witness owid:life-expectancy: 19,468 points, 237 entities,
  1543-2023.
- homicide_rate: canonical 7,193 = 7,193 + 0; oecd 7,193 (1960-2024);
  46 entities. Witness owid:homicide-rate-unodc: 4,220 points, 200
  entities, 1990-2024.
- maternal_mortality_ratio: canonical 1,890 = 1,102 + 788; un_dyb 1,102
  (2001-2022); 97 entities. Witness owid:maternal-mortality: 8,868
  points, 189 entities, 1751-2020.
- Offline rebuild: dist bit-identical to v9's. Tests: 153/153.

### Known limitations (deliberate)
- `cli stats` reads the BUILT dist; it re-derives nothing from the raws —
  the authoritative replay check remains `cli rebuild` plus a diff. It
  reports what IS, including anything a build shipped.
- The reviewer's kept v8 copy could not be re-inspected directly (the
  v8-era zips were removed after v9's packaging, per convention); the
  v8.1 dist was instead rebuilt from the v8.1 code + the raw snapshots
  shipped in the v9 zip — deterministic, and matching every count the
  v8/v8.1 entries recorded.

## 2026-09-12 — v9: P3b delivered (maternal mortality, DYB Table 17, two
tiers) + the QC/footnote plumbing audit closed

**Breaking (dist contract v4):** the canonical `data[]` arrays may now
contain explicit gap points — `"value": null` carrying the collector's own
degradation annotations (`quality_code`, `missing_marker`). Consumers that
assume every canonical point is valued must handle null. Measured at the
cutover: IMR 1,419 -> 2,689 points (+1,270 gaps), LE 3,018 -> 5,962
(+2,944), zero valued points changed, zero lost. Everything else is
additive (a new indicator file; a new per-point `small_base` field).

### Context
The v8 review closed with one residual risk explicitly left open:
normalize.py/merge.py (the P2 quality-code/footnote plumbing) had been
spot-checked, never line-audited. v9 was planned as that audit plus P3b —
the second half of P3, deliberately deferred from v8 as "not smuggled in
half-done": a new indicator (maternal mortality ratio) with its own layout
probe, parser, fixture and config.

### Investigated (live, 2026-09-12)
- Table 17 exists on every wired edition 2011-2024 and its number is
  STABLE (unlike the 21/22 zone, where the LE-by-age table swaps numbers
  between editions — verified during the LE-60 investigation the same
  day). Title dispatch confirmed per edition by downloading and parsing
  all twelve files.
- The official Notes17 PDF settles the two things the XLS files do not
  state: the ratio is "maternal deaths per 100 000 live births (table 9)
  in the same year", COMPUTED by the UN Statistics Division (we republish
  the collector's published figure); and the "♦" marker means "Ratios
  based on 30 or fewer maternal deaths" — 3,336 bare + 501 glued to a
  footnote ref ("♦1") across the twelve editions, verified by scanning
  every marker cell.
- The audit of the existing QC/footnote plumbing, on the real v8.1 data:
  12,672 records carry footnote refs with zero country names still
  holding glued digits; 1,154 vintage arbitrations re-verified against
  the winners' raw snapshots with ZERO annotation mismatches (the residual
  risk the review flagged is now measured and closed); 63 footnote
  numbers carry different texts across editions and each joined to the
  right one. TWO real defects found: (1) canonical keys where every
  edition prints "..." (the collector's own "counts published, no rate
  computed" degradation — 1,270 IMR + 2,944 LE keys) were silently
  dropped at merge, reading identically to "never reported" although
  merge.py's own docstring cites exactly this case as the thing to keep;
  (2) build.py's footnote-ref join accessed witness points'
  provider/source_ref directly — a latent KeyError that would have
  crashed the first DYB-style witness carrying footnote refs.
- OWID `maternal-mortality` (the UN MMEIG estimates) verified live: 200
  entities, 1751-2020, multi-variable CSV ("field" pinned to "Maternal
  mortality ratio"). The tier contrast is structural: witness values
  reach 6,774.7 (South Sudan 1987) where the canonical as-reported band
  tops out around 100.

### Added
- `parse_table17` (src/connectors/dyb.py): country rows + "Number -
  Nombre"/"Rate - Taux" measure rows, quality code in the column beside
  the label ("Co-de"), (value, footnote-ref) year pairs, the "♦"
  small-numbers marker (alone or glued to a ref — the marker-cell grammar
  extended), "..." gaps and "-" nils, repeated page headers skipped,
  BIFF-glued digits on names captured. Dispatch wired on the title with
  the same cross-check; `field` selects the block like Table 15
  ("rate" default / "number").
- `maternal_mortality_ratio` indicator (config/indicators/): 12 DYB
  editions canonical (2001-2022) + OWID/MMEIG witness; unit
  maternal_deaths_per_100k_live_births; plausible_range 0-7000 with the
  two-tier rationale documented in the config (a tight bound flags
  thousands of legitimate modeled values — cry-wolf; the net catches
  unit confusions, not tier divergence). Notes carry the UNSD-computed-
  ratio nuance, the pre-1975 denominator caveat (outside our window) and
  the ICD-10-bold typeface limitation (style signal, not cell value).
- `small_base` field, end-to-end (RawRecord -> NormalizedPoint ->
  MergedPoint -> dist): the ♦ marker transported as-reported, exactly
  like `provisional`.
- Faithful Table 17 fixture (SpreadsheetML: Co-de header beside the
  years, ♦/♦N/"..."/"-" cases, a Number-only country, a mid-table repeated
  header, Footnotes worksheet) + OWID MMEIG fixture + conftest seed.
- +16 tests (151 total): 12 connector tests (grammar, gaps vs nils,
  dispatch, BIFF-style glued digits), 3 integration tests (two-tier,
  witness bound, small_base in the dist), 1 regression for the witness
  footnote-join KeyError.

### Changed
- **Canonical explicit gap points** (merge.py): a key where every
  canonical source prints "no value" now yields ONE value=null point
  carrying the highest-priority (latest vintage) candidate's own
  annotations; no provenance entry (nothing was discarded — the gap
  point itself is the record). Valued arbitration is unchanged: the
  highest-priority VALUED source still wins, so a gap in a late edition
  never erases an earlier vintage's value. Existing tests asserting the
  old drop semantics were rewritten to pin the new contract (witness-tier
  honesty extended to the canonical tier, per the audit finding).
- `_referenced_refs` (build.py): witness points' refs now join against
  the witness series' own provider/source_ref (the fallback parameters),
  instead of raising KeyError on the per-point keys the witness payload
  never carries.

### Verified (live, 2026-09-12)
- Fetch: 13/13 maternal sources, 0 failures (12 DYB editions + OWID
  MMEIG); rebuild offline from the raw snapshots.
- maternal_mortality_ratio: 1,890 canonical points (1,102 valued + 788
  explicit gaps), 97 entities, 2001-2022, zero unresolved mapping gaps
  (the existing entities.yaml covers every Table 17 name); witness 8,868
  points / 189 entities. Spot-checks exact against the raw files: France
  2019 = 3.50126 with small_base; Russia 2003 = 31.34094 with the
  Chechnya-exclusion note 5 joined into sources[] from the 2014 edition;
  Mauritius 2013 = 66.726, ♦-marked; France 2022 = explicit gap
  ("...", code C) while the MMEIG witness carries 5.2.
- Cross-individual regression: v8.1 -> v9 dist diff is exactly the gap
  points — every valued point identical, none lost (IMR 1,419 -> 2,689,
  LE 3,018 -> 5,962, homicide 7,193 unchanged; the OECD connector emits
  no null rows).
- Validation: 0 range violations (canonical and witness), 0 duplicates.
- Tests: 151/151.

### Known limitations (deliberate)
- Table 17's counts block is not wired as an indicator: a country whose
  block is Number-ONLY (no Rate row at all — Libya in the 2024 edition)
  leaves no point in the ratio indicator, the same counts-block scope
  limit as infant_mortality. Wiring `maternal_deaths` (counts) as a
  separate indicator is a one-config decision, not done here.
- The DYB prints ICD-10-classified data in bold: a typeface signal, not
  carried (the C/U/| code column is the machine-readable equivalent) —
  same documented stance as the italics convention.
- The canonical gap points change the dist's point counts; the coverage
  report now counts gap-only entity-years as covered (they ARE — the
  collector heard from them). The frontend owns rendering "no ratio
  [code U]" from the shipped annotations.
- 2015's legacy-pattern XLS files (alive, unlike the dead index links
  that justified the exclusion) and the LE-60 table (21/22 zone) remain
  unwired on purpose: they are v10's package (LE-60 + the 2015 recovery),
  not a v9 smuggle.

## 2026-09-12 — v8.1: the OECD example figure corrected (the crude 52.5,
not the age-standardized 63.3) + the parser now verifies the fetch pins

### Context
The v8 external review (approved: 130/130 tests, bit-identical rebuild)
caught one real defect — documentation, not data: the illustrative
"Russia 1994, male: 63.3" example is the age-standardized rate, not the
crude rate, and it had propagated through the homicide_rate config notes,
the oecd.py docstring and the SDMX test fixture. The review also flagged
the deeper hole behind it: the parser trusted the URL's
CALC_METHODOLOGY=CRUDE pin without ever looking at the column, so nothing
would catch an OECD API behavior change returning standardized rows
some day. This delivery fixes both.

### Investigated (live, 2026-09-12)
- Re-verified the diagnosis against the raw cache and the shipped dist:
  the CRUDE-pinned snapshot reads RUS 1994 _T 32.3 / male 52.5 / female
  14.3, and dist carries exactly those values — the production data was
  never wrong, only the example figure was.
- The wrong figure had travelled further than the review's three files:
  two test assertions (test_oecd_connector, test_pipeline_integration)
  and the generated dist notes carried it too (the config's "crisis
  peak (4.4x)" mixes a standardized male with a crude female — the
  honest crude ratio is 3.7x). The correct contrasts elsewhere (the
  docstring's CRUDE-pin paragraphs, the-measurement-problem.md, the v8
  entry below) were left untouched.

### Fixed
- The crisis-peak example now reads crude everywhere it stands for the
  as-reported number: src/connectors/oecd.py (docstring: "male 52.5 vs
  female 14.3 per 100k printed as counted"; the source-is paragraph now
  states the dataflow carries BOTH methodology variants),
  config/indicators/homicide_rate.yaml (52.5, 3.7x), and the assertions
  in tests/test_oecd_connector.py + tests/test_pipeline_integration.py.
- tests/fixtures/oecd_homicide_sdmx.csv: every row now carries
  CALC_METHODOLOGY=CRUDE (as a response to the pinned URL actually does)
  and the Russia 1994 male row reads 52.5, matching the real cached
  snapshot; the attribute-only IDN test row follows suit.

### Added
- The pin guard in parse_sdmx_csv (the review's ask): every data row is
  verified against the dimensions build_url() pins — FREQ, MEASURE,
  UNIT_MEASURE (per field), AGE, CALC_METHODOLOGY=CRUDE, plus DEATH_CAUSE
  when the caller passes the cause it asked for (fetch_raw does). A row
  from any other slice — the age-standardized variant above all — is
  refused loudly (ValueError naming the row and the violation), never
  silently ingested.
- 5 tests: the three pin sabotages (methodology / unit / frequency), the
  literal v8 fixture row frozen as a regression, and the DEATH_CAUSE
  verification. 135/135.

### Verified (live, full pipeline)
- 135/135 tests (v8: 130).
- Full offline rebuild from the cached raw snapshots: data/dist differs
  from v8's by EXACTLY one line — the homicide_rate notes regenerated
  from the corrected config (52.5, 3.7x); every data value, the other
  two indicators, catalog and entities are bit-identical. The v8 entry
  keeps its original figures (vintages are never edited).

### Known limitations
- The guard verifies the response against the URL's pins; it cannot
  detect a pin that is itself wrong in build_url's key — that stays the
  job of build_url's own tests and of review.

## 2026-09-11 — v8: the collector's own voice (P2): DYB quality codes,
footnote texts and LE reference ranges end-to-end; witness citations;
homicide two-tier via the OECD/WHO Mortality Database route (P3); LICENSE

**Breaking — dist contract v3 (additive): every `sources[]` entry and every
`witnesses[]` entry now carries a full citation block (`citation`, `url`,
`license`); points may carry `quality_code`, `footnote_refs`,
`reference_range`, `missing_marker`, `provisional` when the source prints
them; `sources[]` entries may carry a `footnotes` block (legend + the texts
of the refs the emitted points actually use). No field is removed — a v2
consumer ignores the new fields safely.**

### Context
The v7 external review (approved) left five accepted notes; two of them
were this delivery's mandate, agreed in conversation: (1) the collector's
quality annotations — the DYB's codes, footnotes and LE reference ranges —
were parsed away, kept in the source file one snapshot away; (2)
homicide_rate was still the review's standing gap, mono-OWID with no
canonical/witness treatment. The other three notes map to later phases
(WB/GHO stubs = P5, the metrics/predictions workstream = separate layer,
HMD = P4 gated) and a LICENSE file was missing entirely.

### Investigated (live, 2026-09-11)
- Where the DYB's quality annotations physically live, verified against
  every cached edition (2011-2024, both file families): the row quality
  code in the column right of the residence label (C, U, |, +C, +U, ... —
  the "+" prefix = tabulated by registration date rather than occurrence);
  per-value footnote refs and the "*" provisional flag in the columns
  immediately right of each value cell; the footnote TEXTS and the code
  legend on a second worksheet ("Footnotes") of every file.
- The Table 4 Roman numerals next to the LE values are NOT footnote refs:
  legend b says they are the WIDTH OF THE REFERENCE PERIOD ("a reference
  year of 2005 and a range of V years means the reference period is
  2001-2005") — 580 real canonical LE points carry one, the modal value
  III (a 3-year period). A Todd-relevant as-reported nuance: an LE "2012"
  with range III was computed over 2010-2012.
- The BIFF editions glue footnote digits to the bilingual names — the
  digits can ride the FRENCH part ("Algeria - Algérie1", "Norfolk Island
  - Île Norfolk128"): captured from the raw string's end, whichever part
  they sit on.
- The WHO Mortality Database itself has no documented public API: the
  platform.who.int/mortality portal is a JS app with obfuscated endpoints
  (its api/mdb route 404s; the widget bundles are compiled WebResource
  blobs), the classic who.int/healthinfo bulk paths are dead, the dthub
  gateway is DNS-dead. GHO's homicide indicators (VIOLENCE_HOMICIDERATE)
  are literally named "Estimates of ..." — harmonized tier, not a
  collector. The OECD "Causes of mortality" dataflow (DSD_HEALTH_STAT@
  DF_COM) redistributes the WHO MDB over a clean public SDMX REST API
  (no key): that is the route wired here. Verified against it live:
  21,898 assault rows, 49 countries (incl. RUS, CHN, BRA, ZAF, IND),
  1960-2024, sexes _T/M/F.
- The DF_COM dataflow carries TWO methodologies for the same keys
  (CALC_METHODOLOGY): CRUDE and age-standardized STANDARD — Russia 1994
  male reads 52.5 crude vs 63.3 standardized. Standardization adjusts
  for age structure: a derived comparability measure, not the as-reported
  rate. The connector pins CRUDE.

### Added
- The DYB quality annotations ride RawRecord -> NormalizedPoint ->
  MergedPoint -> dist, as-reported and never interpreted:
  `quality_code` (row code), `footnote_refs` (country-, row- and
  cell-level, reading order), `reference_range` (Table 4's Roman numeral
  — LE only), `missing_marker` (which of "..."/"-" was printed where the
  value is absent), `provisional` ("*"). Table 4 LE points deliberately
  carry NO quality_code: the C/U/| codes on that table describe the
  births/deaths/infant-deaths columns, and attaching them to the LE
  columns would be an interpretation.
- The Footnotes worksheet is extracted into the snapshot (`footnotes`
  block: legend + numbered texts, both file grammars: SpreadsheetML
  'marker\ntext' cells and BIFF 'marker text'), and the dist joins, per
  source, the texts of the refs the emitted points actually carry —
  e.g. Armenia's IMR 2017 carries ref 19 whose text ships beside it
  ("Excluding infants born alive of less than 28 weeks' gestation...",
  the Armenian live-birth definition — the as-reported nuance the project
  exists to surface).
- Citation blocks on EVERY source (the review's witness-citation gap):
  `citation` (PROVIDER_CITATION in src/schema/indicator.py — e.g.
  "United Nations Statistics Division, Demographic Yearbook 2024, Table
  15"), `url` (the real fetch URL), `license` — in `sources[]` AND on
  each `witnesses[]` entry.
- The OECD DF_COM connector (src/connectors/oecd.py): SDMX REST,
  13-dimension key with everything pinned except REF_AREA and SEX;
  CALC_METHODOLOGY pinned to CRUDE; attribute-only CSV rows (no
  TIME_PERIOD) skipped as metadata residue; REF_AREA rides iso3_raw
  (it IS an ISO3) so entity resolution goes through the ISO3-first path.
- homicide_rate two-tier (P3): canonical = OECD DF_COM Assault
  (CICDHOCD) — WHO Mortality Database registrations as submitted;
  witness = UNODC via OWID (criminal-justice + imputation). The two
  count homicide DIFFERENTLY — the divergence is signal to display.
  Canonical carries the sex split end-to-end like life_expectancy.
- LICENSE (MIT) — the repo had docs/licenses.md (data-source licences)
  but no licence for the code itself.
- 23 tests over the new surface (marker grammar, both footnote
  grammars, the French-part digits, the dist joins, the OECD connector,
  the homicide two-tier): 130/130.

### Verified (live, full pipeline)
- Fetch: 29 snapshots, 0 failures (12 DYB editions x 2 tables + curated
  + 3 OWID + 1 OECD). Rebuild clean.
- infant_mortality 1419 canonical points (v7: 1419 — unchanged);
  life_expectancy 3018 (v7: 3018 — unchanged); homicide_rate 7193
  canonical points, 46 entities, 1960-2024, sex-split (2426 _T / 2387
  male / 2380 female) — v7: 0 canonical.
- Real as-reported payload spot-checks: Armenia IMR 2017 = 8.25, code C,
  fn 19 joined to its text; Russia LE 2012 male 64.56 vs female 75.86
  (the 11.3-year sex gap, canonical); Russia homicide 1994 crisis peak
  male 52.5 vs female 14.3 crude as-reported; Russia 2019 homicide
  canonical (vital registration, crude) 4.9 vs UNODC witness 7.6 — a
  real collector-vs-compilation divergence now displayable.
- Colombia 1991-93 (158-163 per 100k, the Escobar-era peak as the
  registrar counted it) tripped the old 150 bound: kept in the dist on
  purpose, the bound widened to 200 with the reason commented in the
  config (the safety net reports, it does not censor).

### Known limitations
- The DYB footnotes block ships only the notes referenced by emitted
  points: a ref with no text in the snapshot's sheet is logged and kept
  as an explicit null (never silently dropped).
- The OECD/WHO-MDB homicide canonical covers 49 countries (OECD + key
  partners): NOT near-global; Russia ends 2019 (the WHO MDB's own lag).
  2020+ Russia is witness-only — a divergence to display, not a gap to
  patch. The age-standardized rates are deliberately not fetched.
- P3's second half (DYB Table 17, maternal mortality as a NEW indicator)
  is deliberately NOT in this delivery: it needs its own layout probe,
  parser and indicator config — v9 scope, not smuggled in half-done.
- The italic-print convention (incomplete-registration caveat in the
  DYB's printed tables) is not carried: the XLS files carry no
  machine-readable italics flag, and the C/U/| code column is its
  equivalent.

## 2026-09-06 — v7: the edition loop (P1): 12 DYB editions wired, 2007-2024 as-reported; life_expectancy two-tier with the sex dimension; P1b PDF spike

### Context
The P1 plan (agreed in conversation after the review of the multi-entity
coverage): wire the DYB edition loop so the canonical as-reported tier
covers more than the 2024 window, and give life_expectancy the same
two-tier treatment as infant_mortality. The loop's promised scope was
"editions 2014-2023"; live probing found both less and more (see below).
P1b ran in parallel: a one-edition PDF spike measuring whether a PDF-era
connector is viable at all.

### Investigated (live, 2026-09-06)
- The per-table XLS files exist for editions 2011-2024, but in THREE
  different shapes: 2011-2014 on the legacy site
  (/unsd/demographic/products/dyb/dyb{ed}/Table{NN}.xls) as SpreadsheetML;
  2016/2017/2021-2023 on the modern site as BINARY BIFF .xls; 2018-2020 +
  2024 as SpreadsheetML. All three shapes verified by parsing the actual
  downloaded files.
- Edition 2015: the index page's per-table links are dead (HTML 404) —
  PDF-only edition; build_url() refuses "2015/..." loudly.
- Edition 2016: the files are FILEPASS-encrypted (RC4; msoffcrypto-tool
  confirms it is not the empty password) — a broken artifact of that era
  of the site. Not wired; zero coverage loss (2012-2016 covered by
  editions 2014 + 2017).
- BIFF-era quirks normalized on ingestion: years/counts as floats
  (2018.0), footnote references glued to country names ("Botswana2") and
  to residence labels ("Total11"), '\xa0' footnote cells.
- The SpreadsheetML year-header row places years via a first ss:Index +
  MergeAcross pairs: row extraction now honours merge spans (a latent
  positional bug for any row whose cells rely on implicit positions).

### Added
- `parse_dyb()` dispatch: the connector now decides HOW to parse from the
  file's OWN title (self-describing), cross-checked against the
  configured table number — a "2024/table15" ref pointing at a file whose
  title says table 4 raises instead of mis-parsing. Tables wired: 15
  (infant deaths + IMR) and 4 (vital statistics summary + life
  expectancy at birth).
- Table 4 parser: life expectancy at birth, sex-split (Male/Female in
  columns 17/19, verified stable across all XLS editions 2011-2024) —
  the collector prints no "both sexes" column, and averaging would be a
  derivation (the canonical tier reports, it does not derive). New
  `sex` field end-to-end: RawRecord, NormalizedPoint, MergedPoint, the
  merge key (entity, year, sex), the dist points, and the
  duplicate check. Non-sex-split sources carry sex=None; the witness
  (both-sexes) and the canonical (sex-split) series coexist without
  colliding.
- Edition loop in the configs: infant_mortality now carries 12 canonical
  DYB sources (editions 2011-2014 + 2017-2024, later edition = higher
  priority = later vintage wins, every arbitration logged in
  provenance.json) + curated + OWID witness; life_expectancy now carries
  the same 12 DYB Table 4 editions as canonical + OWID witness (its
  first two-tier wiring — the ADR-0008 treatment asked for in review).
- 15 entity overrides for the UN's own official/vintage names across
  editions (Czech Republic, Turkey, TFYR of Macedonia, Swaziland, Cape
  Verde, long-form Bolivia/Venezuela, Faeroe spelling, ...) + 3 defunct-
  entity overrides prepared for the PDF route (USSR, Yugoslavia SFR,
  Germany F.R. — vintage names verified in the 1978 text; zero coverage
  in the XLS loop by construction, as the P1 correction established).
  The "Yemen" override is deliberately ABSENT: the vintage North and the
  modern unified entity share the printed name, and an override would
  hijack modern rows (documented in entities.yaml).
- xlrd as a declared dependency (the BIFF editions are wired in the
  default configs); tests for the dispatch, the Table 4 parser, the sex
  semantics, the vintage arbitration, the 2015 refusal, the '-' marker
  and the BIFF-era normalizations (row-level, no binary fixture needed).

### Verified (live, full pipeline)
- Fetch: 28 snapshots, 0 failures (12 editions x 2 tables + curated + 3
  OWID). Rebuild + dist: infant_mortality 1419 canonical points, 118
  entities, 1970-2024 (v6: 363); life_expectancy 3018 canonical points,
  182 entities, 2007-2024 (v6: 0 — witness only). France's IMR series
  is now reconstructed from six different edition vintages (2007-2024).
  The Russia hole is visible and honest: 10 canonical LE points
  (2007-2012, then the questionnaire gap), with the sex gap as-reported
  (male 61.4-64.6 vs female 73.9-75.9 in 2007-2012 — a Todd-relevant
  signal now carried canonically). USSR curated series intact (21 points,
  1976 = 31.4). 107/107 tests.

### P1b spike (DYB 1978 PDF, Table 15 — the reliability measurement)
- Token-level extraction from the PDF text reaches 5/6 known values
  exactly (USSR 125908/27.7, France, GDR, FRG, Yugoslavia; the UK miss
  is the footnote-digit-after-code ambiguity, irreducible at token
  level). Reliability: 47% of country lines parse with full confidence,
  15% print counts without rates (the collector's own "U" rule —
  expected), 21% carry OCR corruptions (refused, not guessed), 17% are
  data-less rows (expected).
- Verdict: a full PDF-era connector is VIABLE but REVIEWED, not fully
  automatic (~60% auto, per-edition eyeball for the flagged subset).
  For the defunct entities (the P1b target: ~10-20 rows per edition),
  the honest route is the CURATED gate (minutes per edition, mechanism
  already exists) rather than a connector. Decision recorded for the
  next review; no PDF connector written.

### Known limitations
- Canonical LE is sex-split only (no both-sexes canonical series — a
  derived product, explicitly out of scope until a separate decision).
- The pre-2007 as-reported history and the defunct entities remain
  outside the loop (PDF-era, gated per the spike's verdict).
- dist v2 contract: `sex` appears on points when the source prints it;
  the frontend (not yet built) must handle sex-split series for LE.

## 2026-09-06 — v6.1: identity hygiene (rename carried through the code)

### Changed
- `pyproject.toml` project name: `interface-todd` -> `toddlab`. The
  historical working title had survived every rename of the repo, the zips
  and the docs. Nothing imports the distribution name (all modules are
  imported as `src.*`), so the change is inert for the pipeline and the
  test suite.
- HTTP `User-Agent` in `owid.py` and `dyb.py`:
  `interface-todd-pipeline/0.1` -> `toddlab-pipeline/0.1`. This is the
  string external providers (OWID, UNSD) see in their access logs — it
  should carry the project's actual name. Same version token as before
  (matches `version = "0.1.0"` in `pyproject.toml`).

### Verified
- Full suite re-run after the change: 92/92.

## 2026-09-06 — v6: ADR-0008 wired (Technique A): curated tier + collectors canonical, harmonized witness, unit conversion real

### Context
ADR-0007 had left one decision open: which layer is canonical for the Todd
board. Asked as "Technique A vs B", the owner chose A, with the rationale
recorded in ADR-0008: *"with B, we fall back into the same smoothing
problem"* — a harmonized-canonical board keeps the re-modeled series as
its primary reading, and the witnesses would only ever measure the
distortion. This entry is the implementation of that choice, end to end,
on real data.

### Added
- **ADR-0008** (`docs/adr/0008-todd-board-canonical-layer.md`) — the
  decision record: as-reported tier (curated + collectors) canonical,
  harmonized witness; Extra board reads the same dist differently;
  canonical unit = per-1,000; per-point provenance as part of the
  canonical contract. ADR-0007's status updated (its deferred wiring is
  done).
- **The curated tier**: `src/connectors/curated.py` (strict parser: exact
  column contract, no empty values — a curated gap is an ABSENT row —
  empty `citation` rejected per the curation gate, duplicate
  (entity, year) rejected, path-fragment source_refs rejected) +
  `catalog/curated/` with its README (gate conditions, provenance,
  cross-checks) and the first series:
  **`ussr_infant_mortality_official.csv`** — the founding tracer, 21
  points 1970-1990, one citation per point (Kalabekov compilation of the
  TsSU/Goskomstat yearbooks; institutional carrier for 1974 = UN DYB 1978
  Table 15; by-republic aggregation reproduces 1970/1980/1985/1986;
  Kingkade & Arriaga for the retrospective series), per-row
  `definition_note` carrying the Soviet live-birth definition and the
  1976-87 blackout.
- **Schema**: `Provider.curated`, `SourceRole` (canonical/witness),
  `SourceRef.role` + `SourceRef.unit` (native unit, declared),
  `PROVIDER_LAYER` (curated/collector/harmonized), `RawRecord.citation`/
  `definition_note` (per-point provenance), validator: at least one
  canonical source per indicator.
- **Entity resolution for the new tiers**: curated resolves by canonical
  `entity_id` (typos land in unresolved.json — no silent forgiveness);
  `un_dyb` resolves by `source_ids.un_dyb` override then exact label. 12
  overrides added to `entities.yaml`, verified against the live 2024
  Table 15 (144/145 names resolve; "Saint Helena ex. dep." deliberately
  unresolved — sub-territory granularity, visible in
  `infant_mortality.unresolved.json`).
- **Witness semantics in the pipeline**: merge splits on `role`
  (canonical arbitration by priority stays WITHIN the tier, logged;
  witnesses built as per-source series, gap-preserving — value=None
  points kept — duplicate reductions logged with role=witness);
  validate applies plausibility bounds and duplicate checks to every
  witness series; the coverage report gets a witness summary line each.
- **34 tests** (`tests/test_curated_connector.py`, 17;
  `tests/test_witness_semantics.py`, 13; 3 new integration cases; bugfix
  tests extended with a per-source_ref scoping guard). Total: 92, all
  passing.

### Changed
- **`infant_mortality.yaml` v2**: three sources — curated
  (canonical, p1), `un_dyb 2024/table15` (canonical, p2), owid
  (witness, p3) — with `role` and native `unit` declared. Canonical unit
  is now **per-1,000** (the field's native unit; the phase-1 percentage
  was a single-source stopgap, always marked for phase 2): every
  published value is x10 vs v5, and the x10 conversion burden sits on the
  OWID witness (declared `UNIT_CONVERSIONS` table, never a guessed
  factor). Plausible range rescaled 0-400.
- **`normalize.py`**: `_convert_unit` is real (declared lookup, loud
  `NotImplementedError` on unknown pairs, 1e-10 float-artifact rounding);
  raw snapshots move to a per-`source_ref` directory
  (`raw/{provider}/{indicator}/{source_ref}/{ts}.json`) — a latent-bug
  fix: two sources of the same provider (the planned DYB editions loop)
  previously competed for one directory and only the latest fetch
  survived into normalize.
- **Dist v2 (breaking for the frontend contract, documented here)**:
  `sources_used` replaced by `sources` (role + layer + native unit);
  canonical `data` points carry `provider`/`source_ref` and, for curated,
  `citation`/`definition_note`; new `witnesses` block (per source:
  layer, unit, converted data); `catalog.json` gains `n_witness_points`.
- **Docs**: the-measurement-problem.md §6 (both open questions closed),
  §4/§7.2 updated to "implemented"; architecture.md phase list updated;
  dyb.py/sources.yaml wiring notes updated.

### Verified live (2026-09-06, real network fetch + rebuild)
- Full fetch: 5 snapshots, 0 failures (21 curated rows; 755 DYB records;
  13,944 OWID IMR rows; life expectancy + homicide).
- The founding divergence is now carried by the data layer itself:
  canonical USSR 1974 = **27.9‰** (curated, cited, DYB-1978 carrier on
  the row; peak 31.4‰ in 1976) vs witness Russia 1974 = **21.91‰**
  (UN IGME via OWID, converted to per-1,000 — the plateau).
- Canonical coverage: 363 points = 342 DYB (90 countries, 2020-2024,
  0 violations, 0 duplicates) + 21 curated USSR. Russia/US/China/UK
  honestly absent from the canonical tier (collector holes); the IGME
  witness carries 200 entities / 13,202 points; the pre-1991 South Sudan
  point (484‰) stays flagged in the witness bounds check, on purpose.

### Known limitations (deliberate)
- Canonical as-reported coverage is 2020-2024 + the USSR tracer: the
  1991-2019 gap awaits the DYB editions loop (2014-2023 tables) and the
  HMD/national routes (ADR-0007 decision 4).
- DYB quality codes and footnote markers still not carried into
  `RawRecord` (per-point provenance for the collector tier, phase 2).
- The `family` root-genealogy field (§5.1) deferred until the
  worldbank/gho connectors make multi-root indicators real.
- Witness points with `value=None` are kept as explicit gaps, but no
  current witness source emits them (DYB is canonical here); the
  semantics are tested at unit level.

---

## 2026-09-06 — The collector tier: `un_dyb` connector (prototype), ADR-0007, doc §7

### Context
The question that closed the sourcing loop: if harmonized sources (OWID
included) smooth the signals the Todd method reads, is there a universal
"raw figures" database — or must we scrape 193 national statistical
offices, and wouldn't multi-source stitching be bricolage? Answer (ADR-0007):
no universal raw base can exist ("raw" is a rank in a production chain, not
a property of a database), but the *collector tier* — international
databases republishing national official statistics as reported — already
does the per-country work once, centrally, machine-readably, with quality
annotations.

### Investigated (live)
- **Demographic Yearbook 1978, Table 15** (downloaded from the UNSD PDF
  archive): USSR row = 125,908 infant deaths and **27.7‰ for 1974** (the
  official Soviet rising series, not the UN IGME 21.9‰ plateau), **footnote
  33** spelling out the Soviet live-birth definition (under 28 weeks /
  1,000 g / 35 cm, dying within 7 days), and **blank cells 1975-1978** —
  the publication blackout preserved as first-class missingness by the
  collector itself. Value + definition + gap in one institutional row:
  the founding tracer has a citable carrier.
- **DYB 2024, Table 15** (XLS, SpreadsheetML 2003): structure decoded
  (merged year-header cells give the value columns; footnote-reference
  cells alternate with values and can hold digits — a real trap for naive
  value filtering); quality codes C/U/|/...; the table's own editorial
  rule (rates computed only for C/| data) explains why ~90 of ~151
  reporting countries have rates; Tonga carries two Total rows under
  different quality regimes; Russia, the US, China and the UK are absent
  (questionnaire gaps — coverage data, not errors to patch).
- WHO Mortality Database ("as reported annually by Member States", per-part
  files), UN IGME inputs (childmortality.org, "the data used to derive
  them"), HMD + HCD: inventoried as the collector tier for causes and
  child mortality (§7 table). UNdata's ASP.NET portal probed and found
  not curl-friendly: documented as a phase-2 alternative, not a blocker.

### Added
- **`src/connectors/dyb.py`** — `un_dyb` connector: positional SpreadsheetML
  parser (stdlib ElementTree, no xlrd/openpyxl), `source_ref` format
  `{edition}/table{NN}` (e.g. `2024/table15`), `field` selects the value
  block (`rate` = IMR per 1,000 — the DYB's native unit; `number` =
  registered deaths). Loud failures on layout drift per the house rule.
- **`Provider.un_dyb`** registered in `CONNECTORS` — fetchable today, but
  deliberately not referenced by any indicator yet: wiring it as
  `infant_mortality`'s witness needs per-point unit conversion first
  (per-1,000 vs percentage — the exact trap the unit bug came from).
- **`config/sources.yaml`**: `un_dyb` block (collector-tier notes, quality
  codes, coverage holes, licensing posture).
- **`docs/the-measurement-problem.md` §7** — the collector tier: the
  two-part answer (no universal raw base / the collector tier), the
  verified inventory table, the paradigm case upgraded with the DYB 1978
  row, and four architecture consequences. §4 route list updated with the
  institutional carrier.
- **`docs/adr/`** — ADR register born: `0007-source-of-record-and-
  witnesses.md` (three-tier sourcing, source-of-record per layer,
  witnesses never merged, curation gate, collector holes as data) +
  `README.md` explaining the register and reserving 0001-0006 for
  decisions already recorded in this changelog.
- **16 tests** (`tests/test_dyb_connector.py`) + fixture
  `tests/fixtures/dyb_table15_sample.xls` (faithful SpreadsheetML replica:
  bilingual names, quality codes, "..." markers, digit-bearing footnote
  cells, Tonga's double Total rows). Total: 58 tests, all passing.
- Live smoke test through the pipeline's own snapshot writer: 755 records
  from the real DYB 2024 Table 15, 342 non-missing rate points, 90
  countries, France 2020-2024 exact (3.37 → 3.84‰).

### Known limitations (deliberate, see ADR-0007)
- Urban/Rural rows not emitted (needs a dimension field in the raw
  schema, phase 2); quality codes and footnote markers not carried into
  `RawRecord` yet (per-point provenance, phase 2).
- Table 16 (age/sex detail) and pre-2014 PDF-only editions not parsed;
  iterating editions 2014+ to build the full as-reported series is a
  phase-2 loop around the existing connector.

---

## 2026-09-04 — `label_fr` dropped (English-only labels), Option A for `data/`, full translation pass

### Changed
- **`label_fr` removed everywhere** (decided in conversation): the schema
  now carries a single English `label` field for both `Indicator` and
  `Entity` (`label_en` renamed to `label`, `label_fr` deleted). The
  public-facing project is English-first; if a French UI is ever wanted,
  labels can be reintroduced later as a separate locale layer without
  touching the pipeline. `label_source` values updated accordingly
  (`babel_fr` -> `pycountry`). Tests updated to match English labels
  (e.g. "Russie"/"Tchécoslovaquie" assertions -> "Russia"/"Czechoslovakia").
- **Git strategy for data (Option A, decided in conversation)**:
  `data/dist` stays committed (offline development, reviewable data
  revisions); `data/raw`, `data/processed` and `reports/` are now
  gitignored as regenerable artifacts. The demo fixtures currently in
  `data/dist` must be replaced by a real `fetch` + `rebuild` before the
  first public data commit.
- Full English pass completed on the remaining French: `.gitignore`
  comments, `pyproject.toml` description, `docs/emmanuel_todd.md`
  (typography, book-title glosses).
- `homicide_rate`: added the missing `field: "Homicide rate per 100,000
  population"` — without it, the live UNODC CSV (two value columns) fails
  to parse and the indicator yields zero data (found during the live
  re-audit).
- **New doc: `docs/the-measurement-problem.md`** — the deep analysis of the
  data problem behind the founding tracer (Soviet infant mortality 1970s):
  why the UN IGME family (OWID/WDI/GHO — one root, three redistributions)
  shows a plateau while the official Soviet series showed a +27% rise;
  the layer model (register / official / scholarly / harmonized /
  derivative); where the real data lives (Davis & Feshbach 1980, late-1980s
  retrospective series, HMD 1959-2014, Rosstat); and seven concrete
  architecture consequences (source `family`/`layer` genealogy fields,
  `curated` source type for hand-entered cited tables, canonical+witness
  divergence display, composite layer guard, reclassification case study,
  publication gaps as events, HMD data ops). Triggered by a live
  investigation after Macrotrends' Russia series was found to be an
  interpolated derivative of undocumented provenance.


## 2026-09-03 — USSR tracer resolved: `formerly_part_of` field added

### Context
Following up on the audit's gap finding (see entry below), asked directly:
"are you sure OWID has no USSR data at all?" rather than take the report on
faith. Investigated live against the OWID API instead of guessing.

### Investigated
- Fetched the live entity list for the `infant-mortality` indicator
  (`api.ourworldindata.org/v1/indicators/1271815.metadata.json`): no
  "USSR" entity present. Also confirms the percentage-unit bug fixed
  earlier (`"unit": "deaths per 100 live births"`, `"shortUnit": "%"`) —
  first-party confirmation, not just cross-referenced estimates.
- As a candidate alternative source (per conversation), checked OWID's
  deepest long-run child-mortality series, Gapminder + UN IGME,
  1751-2024 (`indicators/1271844.metadata.json`): still no "USSR" entity,
  despite 274 years of history. Gapminder's own documentation explains why:
  historical estimates are attached to *current* country boundaries, not
  preserved as defunct political unions.
- Conclusion: this isn't a "wrong slug" problem fixable by picking a
  different OWID chart — it's how this entire family of datasets is built.
  Russia's own entry already carries a continuous series through the
  Soviet period under the "Russia" label.

### Decided (in conversation, not unilaterally)
Each of the 15 former Soviet republics shows one continuous data series
across 1991 (not split into a separate fabricated "ussr" series, since
the underlying numbers are identical either way — this isn't a "proxy," OWID
simply never separated them). The pre-1991 portion carries an explicit
warning via a new `formerly_part_of` field.

### Added
- `FormerUnionMembership` model + `Entity.formerly_part_of` field
  (`src/schema/entity.py`): `{union_entity_id, until_year, note}`. Kept
  deliberately distinct from `predecessor`/`successor`, which model a real
  discontinuity (e.g. Czechia genuinely didn't exist before 1993) — the 15
  republics existed continuously before, during, and after the USSR, only
  their sovereign status changed.
- All 15 ex-Soviet republics in `config/entities.yaml` now carry
  `formerly_part_of: {union_entity_id: ussr, until_year: 1991, note: ...}`.
- `build.py` now includes `formerly_part_of` in `dist/entities.json`, so
  the frontend can render the warning without needing per-datapoint
  annotations in each indicator's JSON.
- The `ussr` entity's `notes` field updated to point at this resolution
  instead of describing it as an open question. Kept in `entities.yaml`
  for reference and in case a future source (e.g. HMD) does carry a real
  standalone series.
- `docs/methodology.md`: new "On the USSR tracer" section with the full
  reasoning.
- Test fixtures (`tests/fixtures/owid_infant_mortality.csv`) updated to
  match the confirmed live reality: no standalone USSR rows; Russia's
  fixture rows now span 1958-2023 continuously instead of being split
  into separate USSR (1950-1990) and Russia (1992-2023) blocks.
- New tests: `test_ex_soviet_republics_carry_formerly_part_of`,
  `test_unrelated_entity_has_no_formerly_part_of`,
  `test_russia_carries_one_continuous_series_across_1991`,
  `test_entities_json_flags_soviet_era_data`.
- Total: 42 tests, all passing (was 39).

## 2026-09-03 — Live-network audit: 3 bugs fixed, 1 gap surfaced, full English pass

### Context
An external AI with real network access audited the phase 0/1 deliverable
against live OWID data (this sandbox has no outbound access to
`ourworldindata.org`). Full findings in the conversation. Summary of what
was independently re-verified by re-reading this repo's own code (not just
trusted from the report) and what was fixed as a result:

### Fixed
- **Fetch isolation (critical).** `fetch_indicator` didn't catch exceptions
  around `connector.fetch_raw(...)`: one source failing (the audit hit a
  live HTTP 403) aborted the entire `fetch_all` loop, so indicators queued
  *after* the failing one were never even attempted. Confirmed by
  re-reading `src/pipeline/fetch.py` directly. Fixed: each source is now
  wrapped in try/except, failures are collected into a `FetchOutcome`
  instead of propagating, and the CLI reports them without stopping the
  run (partial success = exit 0 by default; `--strict` opts into
  fail-on-any-error for CI). Regression test:
  `tests/test_pipeline_bugfixes.py::test_fetch_all_isolates_a_failing_source_from_the_rest`.
- **Snapshot selection by lexical filename sort (critical, silent).**
  `_latest_snapshot` used `sorted(glob(...))[-1]` on filenames. Production
  timestamps (`RawFetchResult.now_iso()`) look like `2026-09-03T084822Z`
  (dashes in the date part); this repo's own test/demo seeding helper used
  `20260101T000000Z` (no dashes at all). Because `-` (0x2D) sorts before
  `0` (0x30) in ASCII, the compact mock filename could lexically outrank a
  genuinely newer real fetch — confirmed by direct inspection of both
  format strings in this repo. Fixed: `_latest_snapshot` now parses each
  filename with `datetime.strptime` and picks the true max by parsed time,
  excluding unparseable filenames instead of trusting their raw string
  order. Also fixed the root cause: `tests/conftest.py`'s
  `seed_raw_snapshot` now writes fixture snapshot filenames in the same
  format production actually uses. Regression tests:
  `tests/test_pipeline_bugfixes.py::test_latest_snapshot_*`.
- **Stale `unresolved.json` (minor).** `write_normalized` only wrote
  `{indicator}.unresolved.json` when non-empty, so a stale file from an
  earlier run with junk entities could survive a later, clean run. Fixed:
  the file is now always written, empty or not.
- **Unit bug in `infant_mortality` (critical, data-integrity).** The OWID
  `infant-mortality` chart reports the rate as a **percentage** of live
  births, not per-1000 as originally assumed when this indicator was
  configured; no conversion is applied in phase 1 (single source, pass-
  through), so the declared `unit: deces_pour_1000_naissances` was
  factually wrong for the values actually stored, and the old
  `plausible_range: [0, 500]` (calibrated for per-mille) was blind to the
  real ~0–10 scale. Independently sanity-checked against known real-world
  figures (France, Japan, Soviet-era Russia infant mortality) — internally
  consistent with the audit's reported values, though not re-fetched
  directly by me given the sandbox's network restriction. Fixed the
  minimal way, consistent with this project's "never guess a conversion
  factor" principle: relabeled `unit: deaths_per_100_births` and tightened
  `plausible_range` to `[0, 40]`, rather than silently multiplying stored
  values by 10. A canonical per-mille unit with an explicit, documented
  conversion is left for phase 2 (`_convert_unit`, already stubbed).
  Regression test: `tests/test_pipeline_integration.py::test_no_violation_for_infant_mortality_with_corrected_unit`.
- **`owid.py` docstring inaccuracy.** Claimed OWID leaves `Code` blank for
  non-ISO3 entities. In reality OWID uses `"OWID_"`-prefixed pseudo-codes
  (`OWID_USS`, `OWID_KOS`, `OWID_WRL`...). Resolution logic wasn't actually
  broken by this (name-based fallback already handled it), but the
  docstring was corrected, and the `OWID_` prefix is now used as a
  heuristic in `normalize.py::classify_unresolved` to split unresolved
  names into `owid_special` (aggregates/regions/historical-but-uncataloged
  entities — expected, needs individual judgement) vs.
  `possible_mapping_gap` (more likely a real naming bug in
  `entities.yaml`). Regression tests in `tests/test_pipeline_integration.py`
  and `tests/test_owid_connector.py`.
- **Missing `homicide-rate` slug (critical, source unusable).** The
  original slug returns HTTP 403 on direct CSV download (confirmed live).
  Swapped to `homicide-rate-unodc` (verified reachable via search,
  UNODC-sourced, CC-BY, timespan 1990-2024) — also a better match for this
  project's stated preference for raw registry compilations over modeled
  estimates, so `reliability` was bumped from `medium` to `high` and
  `reliability_criteria` updated accordingly.
- **Kosovo missing from `entities.yaml`.** Absent from ISO 3166-1 so
  absent from the pycountry-generated base list; confirmed by the audit as
  a real data gap (not an expected aggregate) once it showed up unresolved
  in live income/region-group indicators. Added by hand: `iso3: null`,
  `valid_from: 2008`, `source_ids.worldbank: "XKX"`.

### Investigated, resolved in the entry above (2026-09-03, "USSR tracer resolved")
- **The USSR/infant-mortality tracer — this project's founding example —
  turns out to be close to unrepresentable with the currently selected
  OWID slugs.** Reported near-zero usable USSR rows once `covers_year`
  (`valid_from=1922`) excludes pre-1922 rows OWID also tags "USSR" in the
  long-run life-expectancy series, and the `infant-mortality` slug appears
  to carry no USSR rows at all. Russia's own OWID entry does cover the
  Soviet period continuously (1958 onward) under the "Russia" label. See
  the entry above for the live-data follow-up investigation and decision.
- Sub-national UK entities (England and Wales, Scotland, Northern Ireland),
  flagged by the audit as potentially relevant to Todd's family-systems
  anthropology — noted in `docs/architecture.md` as a deferred question,
  not decided on.

### Changed — full English pass
- All Python code (identifiers were already English; comments and
  docstrings were mostly French) translated to English throughout
  `src/` and `tests/`.
- All YAML config comments (`config/*.yaml`) translated to English.
  `label_fr` values (and only those) deliberately kept in French — they're
  the explicitly French-facing frontend label field, not incidental
  documentation.
- `Family` enum values changed from French (`mortalite`,
  `anthropometrie_sante`, `societe`) to English (`mortality`,
  `anthropometry_health`, `society`) for consistency — this is a breaking
  config change; the 3 pilot indicator files were updated accordingly.
- `unit` string values changed from French to English
  (`deces_pour_1000_naissances` -> `deaths_per_1000_births`, etc.).
- `README.md`, `docs/architecture.md` translated in place;
  `docs/methodologie.md` -> `docs/methodology.md` and `docs/licences.md`
  -> `docs/licenses.md` (renamed + translated).
- This changelog: earlier French entries translated to English rather than
  left as a mixed-language history.

### New tests
- `tests/test_pipeline_bugfixes.py` (4 tests): fetch isolation, snapshot
  selection by real timestamp vs. lexical sort, malformed-filename
  handling.
- Additional cases added to `tests/test_entity_resolution.py` (OWID-
  prefixed code resolution, Kosovo), `tests/test_owid_connector.py`
  (OWID-prefixed code parsing), `tests/test_pipeline_integration.py`
  (unresolved-name classification, East/West Germany resolution despite
  `OWID_`-prefixed codes, corrected infant-mortality unit).
- Total: 39 tests, all passing (was 29).

---

## 2026-09-03 — Changelog added

### Added
- This file (`CHANGELOG.md`), to track the project's evolution across the
  conversation.

---

## 2026-09-03 — Phase 0 + Phase 1: foundations + end-to-end OWID connector

### Added
- **Schema** (`src/schema/`): `Indicator` and `Entity` Pydantic models,
  with business validators (unique source priorities, mandatory
  justification for `reliability: low`, temporal consistency between
  `valid_from`/`valid_to`).
- **`config/entities.yaml`**: 257 geographic entities at the time — 249
  current countries generated via `pycountry` + `Babel` (automatic French
  labels), plus 8 historical entities added by hand (USSR, Czechoslovakia,
  Yugoslavia/SFRY, Serbia and Montenegro, East Germany, West Germany, North
  Yemen, South Yemen), each with explicitly declared successors. (Kosovo
  added later — see the entry above.)
- **OWID connector** (`src/connectors/owid.py`): pure `parse_csv()`
  function (testable offline) separate from the network fetch
  (`fetch_raw()`), so all business logic could be tested without depending
  on network availability.
- **5-step pipeline**, each independently replayable (`src/pipeline/`):
  - `fetch.py` — network -> timestamped raw snapshots in `data/raw/`
  - `normalize.py` — entity resolution (never interpolates or guesses by
    name proximity; an unresolved name is logged in
    `{indicator}.unresolved.json`, never silently dropped)
  - `merge.py` — multi-source merge by declared priority, with a
    provenance log of every arbitration (`{indicator}.provenance.json`)
  - `validate.py` — plausible-bounds check + coverage report
    (`reports/coverage_report.md`: entities with no data, internal gaps
    per entity)
  - `build.py` — generates `data/dist/{catalog,entities}.json` and
    `data/dist/indicators/{id}.json`
- **3 pilot indicators** (`config/indicators/`): `infant_mortality`,
  `life_expectancy`, `homicide_rate`, all `todd_core: true`.
- **CLI** (`src/cli.py`): `check-config`, `fetch`, `rebuild`, `all`.
- **29 tests** (`pytest`), all passing, including an end-to-end integration
  test via realistic CSV fixtures that explicitly checks the USSR/modern-
  Russia distinction is preserved.
- **Docs**: `docs/architecture.md`, `docs/methodologie.md` (principle-to-
  code translation table), `docs/licences.md`.
- A demo build in `data/` and `reports/`, generated from test fixtures —
  **not real OWID data** (see limitation below).

### Known limitations (not resolved in this delivery)
- **Network fetch never exercised against the real server**: the
  development environment has no outbound access to `ourworldindata.org`
  (firewall restricted to PyPI/GitHub). The code used a public OWID CSV
  URL verified via web search, but never actually executed. (Resolved by
  the live-network audit above.)
- `entities.yaml`: `source_ids.owid` is a bet (pycountry English name =
  OWID entity name), not verified country by country.
- Kosovo missing from `entities.yaml` (outside ISO 3166-1). (Fixed above.)
- No inter-source unit conversion (pointless while only one provider is
  active per indicator — a stub that raises `NotImplementedError`, planned
  for phase 2).
- No fine-grained anomaly detection (suspicious jumps, definition breaks)
  — only declared min/max bounds.
- No per-indicator `citation_text` (just `license`) — to add before
  displaying mandatory frontend credits.

### Notable decisions
- HMD and CLIO-INFRA dropped from scope at explicit request (their
  licensing/authentication questions weren't investigated).
- World Bank and GHO OData connectors pushed to phase 2: chose to validate
  the whole pipeline on a single provider before adding others, rather
  than parallelizing all 3 connectors from the start.
