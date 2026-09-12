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
   verification.

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
   three) and say so in the UI.
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
   live-fetchable, and — since v7 — **wired as an EDITION LOOP**: 12
   editions (2011-2014 + 2017-2024; 2015 = dead XLS links, 2016 =
   FILEPASS-encrypted, both verified live and excluded without coverage
   loss), three file eras (legacy-site SpreadsheetML, BIFF via xlrd,
   modern SpreadsheetML), two tables (15 = infant deaths/IMR, 4 = life
   expectancy at birth). Consecutive 5-year windows overlap and the merge
   arbitrates by vintage (later edition wins, logged) — reconstructing
   the as-reported series over **2007-2024**: 1419 canonical IMR points
   (118 entities) and 3018 canonical LE points (182 entities, sex-split:
   the collector prints Male/Female separately and averaging would be a
   derivation). Since v8 the collector's OWN annotations ride every point
   as-reported: quality codes (C/U/|/+, the "+" = tabulated by
   registration date), footnote refs JOINED to their texts (the Armenian
   live-birth definition ships beside Armenia's IMR), the LE reference
   ranges (the Roman numerals — a "2012" LE with range III was computed
   over 2010-2012), the printed missing markers and the "*" provisional
   flags. The WHO Mortality Database is wired too (v8) — through the
   OECD DF_COM SDMX redistribution (`oecd` connector, cause Assault =
   CICDHOCD, CRUDE methodology pinned: the dataflow also carries
   age-standardized rates for the same keys — RUS 1994 male 52.5 crude
   vs 63.3 standardized — and standardization is a derived measure, not
   the as-reported rate): homicide_rate's canonical tier, 49 countries,
   1960-2024, sex-split, Russia's 1994 crisis peak (male 52.5 vs female
   14.3) as counted by the registrar. The PDF-era
   editions (1948-2010, the only route for the defunct entities) were
   measured by the P1b spike on the 1978 edition: 5/6 spot-checks exact,
   47% of lines full-confidence, 21% OCR-refused — viable but reviewed,
   not fully automatic; for the defunct (a few rows per edition) the
   curated gate is the honest route.
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
