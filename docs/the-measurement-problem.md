# The measurement problem: how the same indicator tells different stories

This document is the methodological heart of ToddLab. It was written after a
live investigation (September 2026) triggered by a real discrepancy: the
project's founding tracer — the Soviet infant-mortality rise of the 1970s —
turned out to be visible in some sources and absent from others. Understanding
*why* is not an edge case of data engineering. It is the core of the Todd
method, and it dictates several architectural decisions catalogued at the end
of this file.

All numbers below were verified live during this project's audits unless
explicitly marked otherwise.

## 1. The case: Soviet infant mortality, 1970–1985

Four data providers, one indicator, one country, one decade. Four different
answers.

| Provider | Russia/USSR values over time | What the series looks like |
|---|---|---|
| **UN IGME family** (OWID `infant-mortality`, World Bank WDI `SP.DYN.IMRT.IN`, WHO GHO `MDG_0000000001`) | 22.9‰ (1970) → **21.9‰ flat plateau (1974–1978)** → 17.5‰ (1990) | A plateau. The anomaly never happened. |
| **Official Soviet series** (as eventually published; compiled by Davis & Feshbach 1980 from statistical yearbooks; retrospective detailed series published late-1980s) | USSR: 24.7‰ (1970) → 27.9‰ (1974) → **peak 31.4‰ (1976)** → 22.7‰ (1989). RSFSR 1971: 22.9‰ | A rise of +27% in six years, peak in 1976, then decline. |
| **Macrotrends** (provenance undocumented; ToS: "various third-party providers") | 26.37 (1973) → 26.85 → 27.33 → 27.81 → 28.29 → 28.77 (1978), then near-linear decline to 24.98 (1985) | A perfectly linear ramp of +0.48/yr for six consecutive years — an interpolation signature, not observed data. |
| **UN WPP** (model estimates, 1950+) | Not verifiable live (API is auth-walled) — a distinct model family from IGME; treat as unverified until checked | Unknown; flag as unverified. |

Two facts make this table more uncomfortable than a simple "good source vs
bad source" story:

1. **The plateau is not an error.** The UN IGME series is a deliberate,
   documented, methodologically defensible re-estimation. Its purpose is to
   produce numbers that are *comparable across countries and across years*
   under a single definition (WHO live-birth criteria, corrected for
   under-registration). To do that, it models away definitional breaks — and
   the Soviet break of the 1970s is exactly such a break.

2. **The sources are not independent.** OWID, the World Bank, and GHO do not
   merely *agree* — they are three redistributions of the *same* estimates.
   Verified first-party during this audit: the OWID chart's API metadata lists
   its origin as the "United Nations Inter-agency Group for Child Mortality
   Estimation"; GHO `MDG_0000000001` values for Russia match OWID's to the
   third decimal; WDI carries the same series. Three providers, one root.
   Cross-confirming them against each other is an illusion of independent
   verification. **Since v11 this paragraph is executable, not just asserted:
   all three doors are wired as witnesses (OWID, WDI's SP.DYN.IMRT codes,
   GHO MDG_0000000001) and every source declares its `root` — the catalog
   says "one harmonized root (UN IGME) via four doors" from the data.**

## 2. What actually happened in the USSR (the historical event)

The historical record, as established in the demographic literature, is
roughly this:

- The Soviet definition of a *live birth* excluded very premature and
  early-neonatal deaths (infants under 1000 g / 28 cm, deaths in the first
  week were often recorded as stillbirths). This made the official Soviet IMR
  artificially low by international standards.
- From **1974 onward**, Soviet statistical practice progressively began
  re-registering these cases as live births and infant deaths. Recorded IMR
  rose accordingly — concentrated in the Central Asian republics, where
  reporting coverage was improving fastest.
- Simultaneously, real public-health deterioration was plausibly underway
  (deteriorating health system, environmental exposure). The literature split
  into two readings: Anderson & Silver argued the rise was "largely an
  artifact of improved reporting"; Davis & Feshbach (1980) and Eberstadt
  (1981, *New York Review of Books*) argued a substantive health crisis.
  The consensus that emerged: both, in unknown proportions.
- From **1976, the Soviet Union simply stopped publishing detailed infant
  mortality data**. The gap lasted roughly until 1987, when the detailed
  retrospective series (including the 31.4‰ peak of 1976) was released.
- This is the context in which Emmanuel Todd wrote *La Chute finale* (1976):
  he read the official series *as published at the time* — the visible rise
  of 1971–74, and then the blackout itself — as a hard signal of systemic
  decomposition. The statistical artifact (a state changing its registration
  rules under stress, then hiding the numbers) *is itself information about
  the state of the system*. Bodies don't lie; and when the ledger of bodies
  starts behaving oddly, that oddity is the observation.

## 3. The layer model

The general lesson: "the same indicator" exists at several depths of
processing, and each depth answers a different question. ToddLab must
distinguish them explicitly — in its catalog, not just its docs.

| Layer | Name | What it is | Example in this case | Carries the 1970s signal? |
|---|---|---|---|---|
| **L0** | Register events | The actual recorded vital events, at the office that records them | ZAGS/TsSU registration records | Yes (in principle) |
| **L1** | Official series as published | National statistical office series, national definitions, as released at the time | Soviet yearbooks (Народное хозяйство СССР); the late-1980s retrospective series | **Yes — this is where Todd read it** |
| **L2** | Scholarly reconstructions | Expert corrections/reconstructions of L1, with methods disclosed | Davis & Feshbach 1980; Andreev–Darski–Kharkova, *Naselenie Sovetskogo Soiuza 1922–1991*; Anderson & Silver | Yes, with explicit uncertainty |
| **L3** | Harmonized international estimates | Model-based estimates re-expressing everything under one definition for comparability | UN IGME (→ OWID, WDI, GHO); UN WPP | **No — smoothed by design** |
| **L4** | Derivatives/aggregators | Redistributed L3 (or undocumented mixes), sometimes with interpolation | OWID (honest L3 redistribution, documented); Macrotrends, Statista (undocumented) | Varies / unreliable |

Three properties of this stack matter for methodology:

- **Going up the stack gains comparability and loses events.** L3 lets you
  compare France 2020 to Russia 1974 — but it cannot tell you that something
  happened inside the Soviet statistical system in 1974–1976.
- **Anomalies at L1 are data, not noise.** A definitional break, a suspicious
  level shift, a publication gap — for the Todd method these are *the signal*.
  For L3 they are defects to be corrected. Both attitudes are correct for
  their own purpose; the sin is silently mixing them.
- **Provenance opacity at L4 is disqualifying.** A series whose chain to L0–L2
  cannot be stated (Macrotrends) cannot be used, corrected, or even argued
  with. The linear-ramp interpolation signature found on their Russia page
  (constant +0.48‰/yr over six years — arithmetically perfect) is exactly
  what an anchor-interpolated derivative looks like.

## 4. Where the "real" data actually lives

Concretely, for this indicator (and as a template for others):

1. **The late-Soviet official series** — available through three routes:
   - Davis, C. & Feshbach, M. (1980), *Rising Infant Mortality in the Soviet
     Union in the 1970s*, U.S. Bureau of the Census, Series P-95 — the
     standard compilation of the yearbook data as then published.
   - The retrospective detailed series published in the late 1980s (peak
     31.4‰ in 1976), as reported in Kingkade & Arriaga (1997) and
     summarized in Wikipedia's "Demographics of the Soviet Union" (cited
     there with its sources).
   - **Institutional carrier (verified live, this audit): the UN
     Demographic Yearbook itself** — 1978 edition, Table 15, USSR row:
     125,908 infant deaths and 27.7‰ for 1974, footnote 33 documenting the
     Soviet live-birth definition, and blank cells from 1975 on. The value,
     the definitional caveat AND the publication gap, as reported by the
     collector of record — see §7.1.

   *Proposal: encode this as a `curated` source — a small hand-entered
   table in the catalog, one citation per point, committed in git (see
   §5); the DYB 1978 row gives the institutional provenance for the 1974
   value and the gap.* — DONE (v6): `catalog/curated/
   ussr_infant_mortality_official.csv`, canonical source #1 per ADR-0008.
2. **HMD (Human Mortality Database)** — births 1959–2014 and deaths by age
   (input data from 1946) for Russia, 1-year series, built from official
   vital registration. Free after registration; downloads require an
   account, so raw snapshots stay out of git (same policy as GHO). Quality
   warnings: 1959–1969 lower quality; updates suspended after 2014 (pair
   with Rosstat for recent years). **This is the phase-2 route to L1-quality
   data for Russia and ~40 other countries.**
3. **Rosstat / EMISS (modern Russia)** — the direct national source for
   post-Soviet years; Russian-language, free.
4. **UN IGME (via OWID)** — keep it: it is the right backbone for the
   cross-country comparison mode (board "Extra" and beyond), where
   comparability is the point.
5. **UN WPP** — a *separate* model family from IGME (worth having as a
   witness for convergence/divergence analysis); currently auth-walled for
   programmatic access, unverified in this audit.
6. **Rejected: Macrotrends, Statista** — undocumented provenance,
   interpolation artifacts, anti-bot walls. No salvage path.

## 5. Consequences for ToddLab's architecture

Decisions implied by this analysis (to be applied incrementally):

1. **`family` and `layer` fields in `config/sources.yaml`** (source
   genealogy). Example: `owid`, `worldbank`, `who_gho` on infant mortality
   all declare `family: un_igme, layer: harmonized`. The catalog can then
   compute how many *independent* roots an indicator has (here: one, not
   three) and say so in the UI. — **DONE (v11): implemented as the `root`
   field on every `SourceRef` (a closed registry, `ROOT_LABELS`), emitted
   on the dist's `sources[]`/`witnesses[]` and summarized per-role with
   door counts in `catalog.json`; `cli stats` prints the genealogy line
   ("witness: un_igme (owid, who_gho, worldbank x2)"). The LE
   counter-case is wired too: its witnesses carry two DIFFERENT roots —
   `owid_longrun_composite` vs `un_wpp` — the divergence between them is
   the genealogy showing, display material. Since v13 the registry holds
   a ninth root, `who_ghe` (the WHO Global Health Estimates): suicide_
   rate's witness is the first to carry it, and it is the root-field
   case the project was built for — the GHE model re-distributes the
   ill-defined causes over the collectors' printed suicides, so the
   canonical (who_mdb: 69.8 for Russia's male 2000) and the witness
   (who_ghe: 95.2, same country-year-sex) diverge SYSTEMATICALLY; two
   tiers, two roots, one displayed spread that IS the metric's
   reclassification sensitivity.** Since v14 the registry holds a tenth
   root, `eurostat_demo` — birth_rate_fertility's canonical (the corpus's
   #1 needed a collector that prints a national TFR and none of the
   existing wires does: the DYB publishes CBR and age-specific rates but
   no TFR column, the OECD SDMX registry has no national fertility
   dataflow), so the root is the Eurostat questionnaire collector itself,
   sitting BESIDE `un_wpp` (the WPP witness): for the EU the two roots
   AGREE because WPP anchors on the national series (FR 2022 prints
   1.78 on both tiers), and everywhere else the witness models what the
   collector never polled — the tier split, stated as genealogy.
   Since v15 the registry holds an eleventh root, `national_legislation`
   — the MARKERS' root (same-sex marriage legalization, universal
   suffrage introduction): the dated law itself, cited per point. A
   root unlike every other: there is no upstream redistributor to
   disclose (the citation IS the origin), which is also why the
   markers carry `witnesses: none` — nothing upstream exists to
   witness. The genealogy field's honest answer to a tier that cannot
   be cross-checked: it says so. Since v16 the registry holds a
   twelfth root, `oecd_family` — illegitimate_births' witness: the
   OECD Family Database's compiled share of births outside marriage
   (SF2.4), reached through OWID's chart door (the compilation itself
   carries no SDMX wire). An OECD-COMPILED product sits on the
   harmonized side of the line (the OECD assembles and standardizes
   national series — the relation WPP/GHE hold to their collectors),
   and the root label is what lets its honest limit read correctly:
   the vintage ends at the OECD's 2021 compilation where the collector
   prints through 2024, and on the co-covered entities the two roots
   AGREE (France 2020 = 62.2 on both doors — the OECD anchors on the
   national series, the WPP-witness pattern in a second family).
   Since v17 the registry holds a FIFTEENTH-ROOT-PAIR (roots 13-15):
   `consanguinity_studies` — the consanguinity-literature root, the
   markers' constitution applied to a RATE metric (the published study
   IS the origin: national surveys, dispensation registries, DHS final
   reports, vectored by Bittles' consang.net compilation; no upstream
   redistributor exists anywhere — probed live — so consanguineous_
   marriage_rate carries `witnesses: none`); and the unemployment
   pair `eurostat_lfs` / `ilo_lfs` — the collector and the ILO-processed
   family it faces (Eurostat's une_rt_a questionnaire collecting each
   office's own LFS rate; the ILOSTAT LFS database's re-processed
   microdata redistributed by WDI as the national-estimate line). The
   pair holds the same relation who_mdb/who_ghe hold — same underlying
   national surveys, one harmonization step apart — and its seams are
   the coverage cliff (Germany 1991-2008 lives only on the witness:
   the collector's own coverage, stated as genealogy) and the
   print-precision seam (FRA 2024: 7.436 vs 7.4 — the collector's
   1-decimal face), both reading as two doors, never a contradiction.
2. **A `curated` source type**: small tables committed in the repo
   (`catalog/curated/*.csv`), each row carrying `entity_id, year, value,
   citation, definition_note`. This is how the `ussr` entity finally gets a
   real infant-mortality series — and how the founding tracer becomes
   representable without fabrication. License posture: facts with citation,
   small extracts, clearly attributed (see `docs/licenses.md`).
3. **Canonical + witnesses, now with a paradigm case.** For each indicator:
   one canonical series (chosen for the mode's purpose) plus witness series
   (other families/layers), with divergence flagged in the UI. The case in
   §1 — canonical IGME plateau vs curated official rise of +27% — is exactly
   the divergence display working as intended, not an embarrassment to hide.
4. **Composite guard.** The composite mode must never average across layers
   silently: an indicator whose canonical series is L3 and whose witness
   shows a definitional break must expose that to the user before any
   weighting is applied.
5. **Reclassification, promoted from test to case study.** The 1974 Soviet
   live-birth re-registration *is* the reclassification phenomenon — the
   same class of event as suicides migrating to "ill-defined causes" or
   cirrhosis to "liver disease". It becomes the documented reference case
   in the reclassification test design (alongside GHO `WHS10_9`).
6. **Publication gaps as first-class events.** The 1976–87 Soviet data
   blackout should be representable as an explicit coverage event with a
   reason ("publication suspended"), not just as missing values. A state
   stopping publication is a hard indicator in its own right.
7. **Data ops**: HMD requires an account (CI secret, raw never committed);
   curated tables are plain text, reviewed like code.

## 6. Questions resolved by ADR-0008 (2026-09-06)

- **Which layer is canonical for the Todd board?** DECIDED (Technique A,
  chosen by the project owner in conversation: "A is more logical — with
  B, we fall back into the same smoothing problem"): the as-reported tier
  (curated L0-L2 + collectors L1) is canonical; L3 rides as witness. The
  Extra board reads the same dist with the harmonized series as its
  display layer — comparability vs authenticity is a per-board display
  choice, not two pipelines. Full record: `docs/adr/0008-todd-board-
  canonical-layer.md`.
- **Enter the USSR official series now?** DECIDED: yes — done. The
  curated tier (`catalog/curated/ussr_infant_mortality_official.csv`, 21
  points 1970-1990, one citation per point, gate check in
  `catalog/curated/README.md`) is infant_mortality's canonical source #1,
  live-verified end-to-end. The HMD cross-check remains a phase-2 plan.
- **WPP**: still open — verify its Russia series shape as soon as
  programmatic access is found (it would tell us whether *any* big
  harmonized family kept the signal).

## 7. The collector tier: where "as reported" is actually fetchable

This section answers the question that closed the loop on the sourcing
strategy: *is there one universal database of "raw" figures, or must every
country be hunted down on its own national site?* The answer has two parts,
both verified live during this project.

**Part 1 — No, and no such thing can exist.** "Raw" is not a property of a
database; it is a rank in a production chain (register event → national
publication → international collection → harmonization → derivative). Every
rank makes documented choices, so a "universal raw base" would be a base
with no choices — a contradiction. What *can* exist universally is the next
best thing:

**Part 2 — The collector tier.** International databases that republish
national official statistics **as reported by each country**, without
re-modeling them. One questionnaire per country, one collector institution,
machine-readable output. Collecting 193 national statistical sites
ourselves would be re-building the UNSD's job with a fraction of its staff;
the collectors have already done it, and their annotations (quality codes,
footnotes, honest gaps) are precisely the L1 signal the layer model says we
must not lose.

| Collector | What it republishes as reported | Machine access | Quality annotations | Verified live |
|---|---|---|---|---|
| **UN Demographic Yearbook** (UNSD) | vital statistics from ~230 countries/areas since 1948, via questionnaires to national statistical offices | per-table XLS per edition (2014+), SpreadsheetML 2003; older editions as PDF | yes: "C"/"U"/"\|"/"..." completeness codes, per-row footnotes, "..." = never interpolated | yes — Table 15 (2024) parsed end-to-end; Table 15 (1978) inspected |
| **WHO Mortality Database** | causes of death by ICD revision, from civil registration, "as reported annually by Member States" | NO API of its own (verified live 2026-09: platform.who.int/mortality is a JS app with obfuscated endpoints; who.int/healthinfo bulk paths dead; dthub gateway DNS-dead) — but the OECD "Causes of mortality" dataflow (DF_COM) redistributes it over a clean public SDMX REST API | yes: coverage/quality flags per country-year-cause (in the OECD flow: OBS_STATUS attributes) | yes — OECD SDMX route wired as `oecd` (v8): 21,898 assault rows, 49 countries, 1960-2024, live-verified end-to-end |
| **UN IGME inputs** | the VR/census/survey inputs behind child-mortality estimates — the portal publishes "the data used to derive them" | childmortality.org portal (single-page app; source public on GitLab) | yes: source type per data point | portal + documentation verified |
| **HMD (+ HCD)** | vital-event counts with the methods protocol AND the constructed series *co-published* — the transparency gold standard this document aspires to | mortality.org after free registration | yes: per-population quality warnings | Russia pages verified (see §4) |

(HCD = the Human Cause-of-Death Data series, HMD's sister database for
causes of death — a later addition to this inventory, same access model.)

### 7.1 The paradigm case, upgraded

The founding tracer now has an institutional, citable carrier — verified
directly in the **Demographic Yearbook 1978, Table 15** (downloaded and
inspected during this audit):

- **The value**: USSR, 1974: 125,908 infant deaths, rate **27.7 per 1,000
  live births** — the official Soviet series (the rising family that
  reached 22.9‰ in 1971), *not* the IGME re-modeled 21.9‰ plateau.
- **The definition**: footnote 33, attached to the USSR row, spells out the
  Soviet live-birth rule (excluding infants born under 28 weeks / 1,000 g /
  35 cm who die within seven days). The comparability hazard is printed in
  the table itself.
- **The gap**: 1975-1978 are simply blank. The publication blackout is
  preserved as first-class missingness, not papered over.

Value, definition, gap — the three signals of the measurement problem, in
one row of one table of one collector. And the 2024 edition shows the
tier's character at the other end of history: the quality codes govern what
the UN is willing to compute (rates only for "C"/"|"), Algeria's row
carries counts with "..." in every rate cell, Tonga has two "Total" rows
under different quality regimes, and Russia, the US, China and the UK are
absent altogether (questionnaire gaps, not data gaps). The collector
degrades honestly instead of inventing — the exact stance ToddLab wants
for itself.

### 7.2 Consequences for the architecture

1. **Collectors are first-class providers.** `un_dyb` is implemented,
   live-fetchable, and — since v7 — **wired as an EDITION LOOP**: 13
   editions (2011-2015 + 2017-2024 — the 2015 vintage recovered in v10
   through the legacy URL pattern after its own index links proved to be
   the dead part; 2016 = FILEPASS-encrypted, verified live and excluded
   without coverage loss), three file eras (legacy-site SpreadsheetML,
   BIFF via xlrd, modern SpreadsheetML), five tables (15 = infant
   deaths/IMR, 9 = live births/crude birth rates — since v15, the
   collector's natalité print served by the Table 15 parser through its
   own content-guarded dispatch branch, 2,225 valued canonical CBR
   points across 179 entities over 2007-2024, 1,900 edition
   arbitrations logged; 4 = life expectancy at birth, 17 = maternal
   deaths and
   ratios, 21/22 = life expectancy at specified ages). Consecutive
   5-year windows overlap and the merge arbitrates by vintage (later
   edition wins, logged) — reconstructing the as-reported series: **1,426
   valued canonical IMR points across 118 entities (1,405 un_dyb over
   reference years 2007-2024 + 21 curated USSR over 1970-1990 — the
   split is stated because a bare count is not recountable without it;
   plus, since v9, 1,276 explicit gap points, 2,702 total)** and 3,032
   valued canonical LE points (184 entities; plus 2,986 explicit gaps,
   6,018 total; sex-split: the collector prints Male/Female separately
   and averaging would be a derivation). Since v8 the collector's OWN
   annotations ride every point as-reported: quality codes (C/U/|/+, the
   "+" = tabulated by registration date), footnote refs JOINED to their
   texts (the Armenian live-birth definition ships beside Armenia's
   IMR), the LE reference ranges (the Roman numerals — a "2012" LE with
   range III was computed over 2010-2012), the printed missing markers
   and the "*" provisional flags — and since v10 that includes the
   SpreadsheetML editions' <html:Sup>-wrapped refs, silently dropped by
   the v2-era text extraction and now carried everywhere (728 IMR + 558
   LE + 22 maternal points gained their printed refs at the v10
   cutover, nothing else moved). The WHO Mortality Database is wired
   too (v8) — through the OECD DF_COM SDMX redistribution (`oecd`
   connector, cause Assault = CICDHOCD, CRUDE methodology pinned: the
   dataflow also carries age-standardized rates for the same keys — RUS
   1994 male 52.5 crude vs 63.3 standardized — and standardization is a
   derived measure, not the as-reported rate): homicide_rate's canonical
   tier, 49 countries, 1960-2024, sex-split, Russia's 1994 crisis peak
   (male 52.5 vs female 14.3) as counted by the registrar. Since v13 a
   second cause rides the same dataflow: **intentional self-harm =
   CICDHARM, suicide_rate's canonical tier** — 46 countries, 1960-2024,
   7,225 as-reported points, zero null observations, the live slice's
   maximum being Lithuania 1994 male 83.5 (the post-Soviet peak ABOVE
   Russia's 73.9). The corpus (todd_refs, v13) ranked it #2 of Todd's
   metrics (80 citations across 11 books) BEFORE it was wired — the
   compilation now weights the roadmap, and the roadmap pointed here.
   Since v14 the same roadmap pointed at its #1, and the finding there
   is architectural: **no collector wire prints a national total
   fertility rate except Eurostat's demo_find** (verified live on the
   files and the SDMX registry before any config: DYB Table 9 = crude
   birth rates, Table 10 = general/age-specific rates with NO TFR
   column — summing the printed ASFR would be a derivation, forbidden
   at the canonical tier; OECD SDMX = no national fertility dataflow).
   So birth_rate_fertility's canonical tier is the **eurostat collector**
   (demo_find/TOTFERRT, the TFRs the national statistical offices
   themselves publish, 1960-2024, per-observation b/e/p flags riding
   the points as-reported), and it carries the project's newest
   as-reported display case: the **France variant pair** — Eurostat
   prints TWO French series (FX "Metropolitan France" 1960-2012, FR
   "France" 1998-2024, values differing in the overlap: 2000 = 1.87
   metro vs 1.89 total), wired as separate geo-pinned sources so the
   merge arbitrates the 15 overlap years by vintage with every
   discarded value logged — the definitional seam the collector itself
   printed, displayed, never reconciled. The WPP witness (WDI's
   SP.DYN.TFRT.IN) carries the worldwide face the collector never
   polled: Todd's Muslim-world and Central-Asia comparisons of Après
   l'Empire live on the modeled layer, next to a collector that never
   asked those countries — the honest tier split of the corpus's #1.
   Since v15 the CBR face of the same phenomenon is wired too, as its
   own indicator: **crude_birth_rate** (DYB Table 9, the collector's
   natalité print — the same births Table 17's ratios are computed
   from; 2,225 valued points, 179 entities, 2007-2024, 1,900 edition
   arbitrations; Russia answers this questionnaire through 2024,
   unlike Table 15). The TFR and CBR ride as COMPANION indicators —
   the dist's `companion_indicators` field says what a unit conversion
   never may: the two measures differ by exactly the age structure CBR
   drags along. And the corpus's marker family entered the pipeline
   the same version: **same_sex_marriage_legalization_year** (33
   countries, the 'religion zero' chain of La Défaite de l'Occident)
   and **universal_suffrage_introduction_year** (16 countries, 1848-
   1946, the franchise's arrival dated as the historiography dates it,
   the male/female decomposition riding every row's note) — curated
   tables, one point per country, the curation gate's condition (b)
   finding being the ABSENCE of any machine-readable door (probed
   live: no OWID chart, no collector wire). Since v16 the
   illégitimité itself is wired: **illegitimate_births** — the share
   of live births outside marriage (16 citations, 6 books), printed
   DIRECTLY by the Eurostat collector (demo_find's NMARPCT — the same
   dataset as the TFR, two Todd metrics through one questionnaire,
   2,144 canonical points, 46 entities, 1960-2024, zero derivation:
   no ratio computed anywhere) with the OECD Family Database as its
   witness through OWID's chart door (42 entities, 1960-2021 — the
   vintage's honest end). THE GERMAN SEAM is this indicator's own
   display case, and the exact REVERSE of the TFR's duplicate: the
   codelist's DE_TOT ("Germany including former GDR") is the FULL
   65-year series while DE's pre-reunification benchmarks are
   FRG-only prints that DIVERGE (1980: 7.6 FRG vs 11.9 all-Germany —
   the GDR's high non-marital share is Todd's communist-family story
   in one number), so DE_TOT rides its own geo-pinned source ABOVE
   the main slice and every DE collision becomes a logged provenance
   discard: the FX/FR seam's architecture (two prints of one country,
   arbitrated, displayed, never reconciled) applied to a definitional
   seam — the same v16 repaired the seam-field's own symmetry (the
   TFR/CBR companion pair now declared on both sides, a
   cross-validation away from ever drifting one-way again). And v17
   claimed the backlog's head in the same motion, both tracks at once:
   **consanguineous_marriage_rate** (34 citations, 10 books — the
   corpus's #6, Le Destin des immigrés alone carrying 16) through the
   CURATED tier — the third curated family, the consensus-literature
   series: 102 published readings, 69 countries, 1943-2021, one
   citation per point, a SPARSE panel by the metric's own nature (a
   country rides the vintages its literature prints — Norway's three
   registry vintages, Pakistan's four DHS vintages 61.2 -> 63.9, the
   Maghreb trio, the European sub-1% dispensation belt Todd's
   L'invention de l'Europe reads); and **unemployment_rate** (20
   citations, 7 books, the economy family's first indicator) on the
   probe's collector verdict — NO other wire prints the plain national
   rate (ILOSTAT wholesale ILO-processed: ILOEST modeled, 19th-ICLS
   harmonized, LFS/ILMS microdata-reprocessed, Germany's own rows the
   EU-LFS adjusted series; OECD doors OECD-harmonized or registered
   counts) — so the canonical is Eurostat's une_rt_a pinned
   Y15-74/PC_ACT/T (the pins ARE the indicator: no age TOTAL exists in
   the codelist, PC_ACT the rate's own denominator, the LFS-2021 'd'
   flag the definitional seam France's continuous series carries) with
   the WB national-estimate witness — the coverage cliff (Germany
   1991-2008 witness-only) and the crisis peaks (ES/EL 2013 = 26.1 /
   27.8) displayed as-reported. The PDF-era
   editions (1948-2010, the only route for the defunct entities) were
   measured by the P1b spike on the 1978 edition: 5/6 spot-checks exact,
   47% of lines full-confidence, 21% OCR-refused — viable but reviewed,
   not fully automatic; for the defunct (a few rows per edition) the
   curated gate is the honest route. Since v9 the loop carries a third
   table: **17 = maternal deaths and maternal mortality ratios** (the
   number STABLE across editions, unlike the 21/22 renumbering zone),
   2001-2022, 97 entities on the ratio — the counts WHO-collected, the
   ratio computed by the UN Statistics Division itself (we republish the
   collector's published figure, we do not re-derive it), and the table's
   own "♦" marker ("Ratios based on 30 or fewer maternal deaths") riding
   the points as-reported — the marker marks RATE cells only (zero
   occurrences on Number rows, verified on the 2015 file). Since v12 the
   table is wired at BOTH blocks: the ratio indicator reads the Rate rows
   (1,114 valued points over 97 entities, 13 editions since the 2015
   vintage joined the loop) and **maternal_deaths reads the Number rows**
   — 1,584 valued points over 131 entities: the counts block is WIDER
   because the collector's editorial rule refuses ratios, never counts,
   so the Number-ONLY countries (Libya: 12 registered deaths in 2016, no
   ratio computed) finally have a series instead of an absence. Since v10 a fourth table is wired: **21/22 = life
   expectancy at specified ages** — the table NUMBER alternates with the
   5qx probabilities by edition parity (21 in even editions, 22 in odd
   ones; the dispatch keys on the title's WORDS), each edition prints
   each country's LATEST available life table (the series is a stack of
   cross-sections: Russia's last table is 2012, frozen across every
   later edition), printed reference periods ride the points with their
   END year as the point's year (the collector's own convention,
   verified against Table 4's Roman-numeral rows) — LE-60's canonical
   tier: 1,754 valued points (166 entities, reference years 1992-2025)
   + 774 explicit gaps, beside the first GHO witness (WHOSIS_000015,
   WPP-derived: Russia 2012 male 15.38 as-reported vs 15.43 modeled).
2. **Source-of-record per layer, witnesses beside it.** The merge layer
   arbitrates duplicates *within* one layer family only; cross-layer series
   are displayed as divergence, never averaged into one line. Implemented:
   `SourceRef.role` (canonical/witness), per-source witness series in the
   dist, canonical arbitration logged in the provenance trail.
3. **The collector's holes are data.** DYB coverage gaps (Russia/US/China/
   UK absent from Table 15 2024) go into coverage maps as "not reported to
   collector", with the alternative route named (HMD, national office) —
   never patched silently. Live-verified in v6: Russia is honestly absent
   from the canonical series while the IGME witness carries its series.
   Since v9 the principle is enforced one level deeper: a cell the
   collector PRINTED as empty ("..." under a "U" code — counts published,
   no rate computed) survives into the canonical dist as a value=null gap
   point carrying the printed code, instead of silently vanishing the way
   "never reported" and "reported, refused" used to read identically.
   Measured effect at the v9 cutover: IMR +1,270 explicit gap points and
   LE +2,944 with zero valued points changed — the degradation the
   collector prints is now the frontend's to display ("no ratio [code
   U]") rather than the pipeline's to hide.
4. **The curation gate stays narrow.** Hand-curated points (the full USSR
   1965-1990 official series — done: 1970-1990, 21 points) enter only with
   a Todd claim, a demonstrated distortion, and a citable source — a
   finite, PR-reviewable set, not a per-country patchwork.

The full decision record — including why tiered sourcing with declared
layers is the industry-standard pattern (HMD, IGME, OWID all do it) rather
than "bricolage" — is in `docs/adr/0007-source-of-record-and-witnesses.md`.

## References (the case's paper trail)

- Davis, C. & Feshbach, M. (1980). *Rising Infant Mortality in the Soviet
  Union in the 1970s*. U.S. Bureau of the Census, International Population
  Reports, Series P-95.
- Eberstadt, N. (1981). "The Health Crisis in the Soviet Union." *New York
  Review of Books*, 28(2).
- Anderson, B. A. & Silver, B. D. (1986/1990) on the registration-change
  interpretation (1986 article; 1990, *The Annals* 510: 155–177).
- Andreev, E. M., Darski, L. E. & Kharkova, T. L. (1993). *Naselenie
  Sovetskogo Soiuza 1922–1991* (the standard demographic reconstruction).
- Kingkade, W. W. & Arriaga, E. E. (1997). "Mortality in the New Independent
  States: Patterns and Impacts." In *Premature Death in the New Independent
  States*, National Academy Press, 156–183.
- UN IGME methodology (the harmonization that smooths the break — the
  "opposing" methodology, quoted fairly).
- Live verifications performed during this project's audits (September
  2026): OWID/WDI/GHO value-level matches; OWID API origin metadata;
  GHO entity dimension; Macrotrends page structure and series values; HMD
  Russia availability pages. See the conversation log and CHANGELOG.
