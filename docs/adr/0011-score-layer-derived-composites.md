# ADR-0011: The score layer — two derived composites, official and modelled

- **Status**: ACCEPTED (2026-10-05, v27); AMENDED (2026-10-06, v27.1 —
  decision 11: `incarceration_rate` removed from the score only);
  AMENDED (2026-10-06, v28 — decisions 12-16: directions confirmed in
  the books, `illegitimate_births` joins the official score, and the
  score-per-year carry rule); AMENDED (2026-10-07, v28.1 — decision 17:
  the DYB Table 4 TFR wired as `birth_rate_fertility`'s second canonical
  door, the official fertility scale RETAINED); AMENDED (2026-10-08,
  v28.2 — decision 18: the official fertility scale regenerated on the
  worldwide canonical sample, and the drift guard hardened to trip on
  coverage drift, not only on source-name changes); AMENDED (2026-10-09,
  v28.3 — decision 19: the UNODC / WHO Mortality Database widening of
  the official score's coverage REFUSED, the measured what-if on record);
  AMENDED (2026-10-11, v29 — decision 19's cirrhosis row erratum: the
  v28.3 brief's 45/44/54/57 was the THREE-SWAP combination mislabelled
  as the cirrhosis swap, not an earlier reading of it — the brief was
  wrong, not the measurement; cirrhosis alone reads 40/42/45/49,
  re-run and confirmed); AMENDED (2026-10-13, v30 — decision 20: the
  three model-based canonical series move to the modelled score only)
- **Scope**: the project's FIRST AND ONLY derived product — two composite
  scores per country-year built on top of the frozen indicator dist; where
  the layer lives, what it may never touch, and the rules that compute it
- **Depends on**: ADR-0007 (source-of-record and witnesses — the
  collector/harmonized vocabulary the official/modelled split reuses),
  ADR-0009 (the corpus as first-class metadata — the todd preset's book
  counts read it), ADR-0010 (the parallel-faces discipline — its mooted
  vocabulary taught this project how two views of one phenomenon stay
  side by side), the retirement of the unused "composite-derived-layer"
  reserve recorded in architecture.md and the
  `industrial_employment_share` notes (the v18 probe dissolved the
  derivation question for THAT indicator; this ADR answers it for the
  whole layer)

## Context

The 2026-10 design interview (Ediz + the independent auditor) asked for
the thing the project had refused since its founding: a composite. The
constitution's anti-derivation line stands at the INDICATOR layer — no
interpolation, no averaging, no reconciliation — and it stays. But a
board of 27 hard indicators answers "what does each piece say", never
"where does the country stand", and Ediz wanted both questions answered
without corrupting the first. The v26 withdrawal had already closed the
counts' door on the score's future (a stock of persons has no direction);
what remained was the architecture the withdrawal's changelog recorded
as V27+ memory: an absolute fixed-bound scale, one source per indicator,
never an interpolation.

The decision that shaped everything else: TWO SEPARATE SCORES, never
merged. "Official" (canonical-tier sources — the project's own
authenticity standard) and "modelled" (widest-coverage single source —
comparability across ~140 countries instead of ~37). The pair is the
same never-a-cross-layer-blend discipline ADR-0007 taught for
indicators, applied to composites: the two scores diverge exactly where
modeling runs ahead of collection, and the divergence is the signal,
not an embarrassment to reconcile.

## Decision

Ediz's decisions (locked; numbered and testable):

1. Two scores, **official** and **modelled**; two rankings, two
   year-comparisons per country. Never merged, never averaged together.
2. **One source per component for all countries and all years, within a
   score. Never mixed.** Official = canonical-first; an indicator with
   no canonical series at all takes its witness for ALL countries and
   the component carries the `modelled` badge.
3. **Absolute scale with fixed bounds**: p1/p99 of all country-year
   values of the retained source since 1990, FROZEN in a committed
   config (versioned; log transform for the very skewed). No per-year
   percentile rank — rank is a display on the composite, never a
   property of it. No interpolation, ever; real observations may be
   carried forward for at most 3 years, with their age recorded and
   displayed (v28, decision 16 — the amendment; a carried value is a
   reuse of a real observation, never an invented one, and the bounds
   are computed on fresh observations only).
4. A difference between two years is computed **only on the components
   available at both dates WHOSE UNDERLYING OBSERVATION DIFFERS**
   (v28 amendment: a component resting on the same observation at both
   dates is excluded — its zero term would damp the delta and dilute the
   common weight), displays its common-component count and the
   per-component decomposition, and is REFUSED below 0.50 of common
   weight.
5. **Sex**: life expectancy and life expectancy at 60 are canonical by
   sex only — male and female are two components of equal weight whose
   total equals one indicator's (each carries half). No both-sexes
   canonical series is derived in the indicator layer (that would be a
   derived product, decided separately if ever).
6. Road mortality per vehicle enters the **official** score only (no
   world-wide source exists — the OECD/ITF door's per-vehicle unit
   carries 38 IRTAD areas, probed live 2026-10-05: the door's other
   unit carries 55, the per-vehicle club is the constraint).
7. **`gini_index` is removed from the score only** — it stays an
   indicator, `todd_core: true`, in the catalog and on the site. Reason:
   double counting with `top_income_share`. Two measured facts (read
   live 2026-10-05, restated neutrally in v27.1): (i) the WID Gini
   witness (`owid:gini-coefficient-wid`) covers exactly the same 3,203
   country-year keys as `top_income_share`'s canonical
   (`owid:incomes-of-the-richest`) — the same survey universe carrying
   two different measures, 0 of 3,203 values equal; (ii) the Gini's own
   canonical (OECD IDD, 906 country-year pairs) shares 774 of them
   (85.4%) with top_income. The overlap, not an identity, is the
   double-counting ground; the exclusion is Ediz's call either way.
8. No "long-run" pre-2000 mode: a score exists for a country-year when
   its weighted coverage reaches 0.60; the first year of a score
   follows from the data.
9. Out of the score (earlier decisions, refused loudly by the config
   schema): `maternal_deaths` (a count; the ratio is the component),
   the two markers, `male_height_trend`,
   `consanguineous_marriage_rate`, `crude_birth_rate`,
   `road_accident_mortality` (per capita), and the v26 withdrawals.
   The POSTPONED `illegitimate_births` is postponement no longer —
   decision 15 (v28) made it the official score's component.
10. **`industrial_employment_share` flips to "higher is better"** —
    Ediz's explicit instruction (Todd defends industry against free
    trade, *L'illusion économique*): the indicator config, its dist
    file and its catalog entry change in exactly that one field
    (v27's only indicator-layer change, a Breaking line in the
    changelog), the score component carries `provisional: true` until
    the direction is confirmed in the books, and a drift test now
    asserts the catalog flag and the score direction can never
    disagree silently.
11. **`incarceration_rate` is removed from the score only** (v27.1,
    2026-10-05) — Ediz's methodological objection, accepted: the prison
    population measures what policing and the justice system do, not
    crime or well-being. The same movement reads in opposite ways — a
    fall can mean fewer offenders or a police force that misses them; a
    rise can mean a crackdown judged effective (the El Salvador case is
    the example; the reading there is contested) or harsher penal
    policy. No defensible monotone direction exists, so it cannot be a
    score component (the v27 config's `basis: editorial` was the
    warning that should have kept it out). It stays an indicator —
    `todd_core: true`, in the catalog, in the corpus, on the site —
    exactly the Gini's treatment (decision 7). The score keeps
    `homicide_rate` as its outcome measure of crime. Side effect,
    reported not sought: incarceration publishes mostly on even years
    (observed pattern, cause NOT established — even years 2000-2018
    carry 135-158 countries under the stated counting rule of distinct
    `entity_id` with a non-null both-sexes point, odd years 1999-2021
    carry 10-36, 1998 is an even year with only 13, zero null points:
    the odd years lack rows, not values), so it made the score's
    composition alternate; without it the modelled score gains 13 to 39
    countries per year between 2000 and 2022.
12. **`industrial_employment_share` and `tertiary_education_share`:
    "higher is better" is confirmed in Todd's books** (v28, 2026-10-06).
    Both components drop `provisional: true` and move to `basis: todd`
    (they were editorial+provisional since v27). With this and decisions
    13-14, NO component carries `basis: editorial` any more and none is
    provisional — the frontend's caveat retires.
13. **`birth_rate_fertility` stays a target of 2.1; too high and too
    low are both bad** (confirmed in the books by Ediz; `basis: todd`).
    Transform (`abs(ln(TFR/2.1))`) and bounds unchanged — the known
    simplification (replacement is higher where mortality is high)
    stands and stays recorded below.
14. **`top_income_share`: lower is better, confirmed** (`basis: todd`).
    The Gini exclusion (decision 7) is untouched by the confirmation.
15. **`illegitimate_births` joins the score; direction `lower`; the
    OFFICIAL score only.** A high share of births outside marriage is
    "bad" in Todd's reading, verified in the books by Ediz — the
    family-anthropology axis (the corpus's own `illégitimité`:
    `todd_core: true`, 16 citations in 6 books; todd-preset weight 6).
    Official-only for a DATA reason (the auditor's recommendation,
    based on measurement; Ediz can reverse it): the indicator exists
    for 47 entities, almost all European — in the modelled score it
    would push about 40 non-European countries per year under the 0.60
    coverage threshold (modelled countries scored in 2015: 141 -> 104
    in a test), while in the official score it changes nothing in the
    number of countries (37 -> 37 in the same test). Same treatment as
    the per-vehicle road indicator (decision 6): the config schema
    refuses the id on the modelled side, loudly. With this decision the
    official score reaches 18 indicators / 20 components (total weight
    18); the modelled stays 16 / 18 / 16.
16. **Score per year: keep the latest real observation, at most 3 years
    old, with its age shown** (v28, 2026-10-06). This replaces the
    exact-year rule of v27 and amends decision 3: no interpolation; real
    observations may be carried forward for at most 3 years, with their
    age recorded and displayed. It is NOT interpolation — no value is
    invented: a real, older observation is reused, capped, and
    labelled. The reason is measured, not aesthetic: at the exact year
    the composition of a score changes from one year to the next
    because PISA comes every ~3 years, top income share and the
    official life expectancy at 60 have gaps up to 4 years, and the
    last years of the series are ragged (suicide and life expectancy
    at 60 stop in 2021). On the V27.1 dist the composition effect was
    0.86 (official) / 0.95 (modelled) score points per year against a
    real mean annual change of about 1.4, and it reversed the sign of
    the year-on-year change in about 18% (modelled) to 20% (official)
    of consecutive-year pairs; with the carry rule the composition
    noise falls to 0.33 / 0.34 (measured on the V27.1 dist, 2000-2020).
    Mechanics: for each (score, component, entity) and year Y in
    [bounds_from_year, max_obs_year(score)], the value used is the
    LATEST real observation with obs_year in [Y - 3, Y]; age = Y -
    obs_year (0 = fresh), recorded in the emitted sparse `age` maps;
    nothing is carried across entities, sources or sexes; a null point
    is never an observation; no score year beyond the score's
    max_obs_year (2025 for both scores today); a country-year is
    scored only with coverage >= 0.60 AND at least one FRESH component
    (the ghost guard — its measured effect: 3 country-years in 2025,
    official); carried values are 13.5% (official) / 9.3% (modelled) of
    the scored values; and the two-year delta is computed on components
    whose underlying observation DIFFERS between the two dates
    (decision 4's amendment). The frozen bounds never move: they are
    computed on fresh observations only (the invariant is tested —
    all 37 pre-existing blocks kept every field at the 2026-10-06.2
    regeneration).
17. **The DYB Table 4 TFR is `birth_rate_fertility`'s second canonical
    door; the frozen official fertility scale is RETAINED** (v28.1,
    2026-10-07 — Ediz's review of v28 approving the ranked wiring plan
    #1: "Le câblage de la fécondité par l'Annuaire démographique
    (risque faible, gain de 4 à 5 pays), à essayer avec le reste").
    The indicator layer's constitution is untouched: the TFR is
    PRINTED by the collector in Table 4 (the printed-value status of
    Table 17's ratios — v14's "no collector wire prints a national
    TFR" finding had probed Table 10 and missed it), so no derivation
    enters. The door is priority-merged UNDER Eurostat (the FX/FR seam
    discipline: every entity-year both collectors print keeps
    Eurostat's value, the discarded candidates logged in
    provenance.json) and the 13 wired editions follow the vintage
    rule. The SCORE consequence is coverage only: the official
    scored-country ladders gain 2010: +6, 2015: +5, 2019: +2,
    2021/2022: +6, 2023: +4, 2024: +5 with ZERO losses, and the
    fertility component enters the aggregates of 10 already-scored
    entities (97 entity-years move, -2.8 to +3.4 points). The frozen
    fertility bounds were deliberately NOT regenerated AT THAT VERSION
    (the drift guard's then-trigger — a §4.4 source-NAME change — did
    not fire, the selection still retained "canonical"); the
    regeneration became decision 18 below, taken the next day with the
    measured what-if on record.
18. **The official fertility bounds are REGENERATED on the worldwide
    canonical sample, and the drift guard trips on COVERAGE drift, not
    only on source-name changes** (v28.2, 2026-10-08). Why: the v28.1
    wiring kept the frozen European scale (hi 0.611 on 1,278
    observations / 47 entities) while the component's canonical became
    the two-collector worldwide series — every TFR above 3.87 or below
    1.14 read 0 on the component (190 country-years across 44 entities
    since 1990: Tanzania, Burundi, Mozambique, Hong Kong, Macao among
    them became indistinguishable), and the freeze's own principle
    ("bounds = p1/p99 of the retained source's sample since
    bounds_from_year") had stopped being true of this component. The
    regeneration was run by the SHIPPED freezer alone
    (`scripts/freeze_score_bounds.py`, bounds_version 2026-10-08.1):
    exactly one block changes — `official/birth_rate_fertility/both`
    moves hi 0.611 -> 0.9903 on 2,523 observations / 177 entities; the
    component now reads 0 only beyond TFR 5.65 / below 0.78; the
    modelled bounds and every modelled score value are untouched (the
    modelled fertility reads the unchanged World Bank witness). The
    GUARD RULE (the v28.1 defect, fixed here): the freezer additionally
    records `n_entities` per block (the distinct entities of the bounds
    sample), and rebuild recomputes both `n_sample` and `n_entities`
    live with the freezer's OWN sampling rule (one implementation,
    `src/score/core.bounds_sample`, shared by freezer and guard),
    refusing the build when either drifts beyond `bounds_drift_tolerance`
    (config/score.yaml — 0.25, a PARAMETER of this decision: a normal
    yearly refresh adds roughly 3% to a 30-year sample, so 0.25
    tolerates several years of refreshes and would have refused the
    v28.1 wiring at +97% observations / roughly +275% entities on the
    fertility block). The source-name check stays; BOTH checks run on
    every rebuild; the refusal message names the score, the component,
    both measures' frozen and live values, and the deliberate re-freeze
    prescription (re-run the freezer, bump `bounds_version`, record it
    in the changelog). No automatic refresh, no bypass flag.
19. **The official score's coverage is NOT widened through UNODC or the
    WHO Mortality Database — REFUSED, with the measurement on record**
    (v28.3, 2026-10-09). What was evaluated: the two doors the v28/v28.1
    probes left open. The UNODC intentional-homicide face (the v28.1
    memo: printed rates with per-point Source genealogy, 203 areas —
    but 15.2% of the candidate face carries UNODC's own GSH revisions,
    and promoting it is a REGISTER SWITCH for the 46 entities whose
    homicide today reads the WHO-MDB cause-of-death canonical). The WHO
    Mortality Database (suicide, cirrhosis, homicide: a genuine
    as-reported collector of ICD-coded deaths, 115-148 countries by
    year against the canonical's 45-46 — but it prints DEATH COUNTS by
    cause/sex/age, no rate column anywhere: reading a crude rate off
    the collector's own counts plus a population denominator is exactly
    what the anti-derivation rule forbids). The measurement (what-if on
    the V28.2 dist, equal weights, coverage 0.60, the shipped carry and
    ghost rules; the swapped component's bounds re-frozen on the
    witness sample with the freezer's own rule; the stand-ins are the
    EXISTING global witness series, so every row is an UPPER BOUND for
    what the raw faces would add; reproduced by TWO independent tools —
    the repo-core swap and the reference prototype — agreeing on every
    row): scored official countries at 2010/2015/2019/2021 — actual
    46/47/42/46; homicide on the OWID-UNODC witness (200 entities)
    46/48/45/49; suicide on the WHO GHO witness (185 entities)
    46/48/45/49; homicide and suicide together 51/49/46/51; the
    cirrhosis row is an ARTIFACT, not a widening — 40/42/45/49 as
    reproduced here by both tools (the brief's own earlier reading
    45/44/54/57; both readings agree on the shape: the WHO GHO
    cirrhosis witness is a 2019-only cross-section — 540 points, 180
    entities, one distinct year — so the swap DROPS 2010/2015 coverage
    while 2019/2021 ride the fresh cross-section; the row measures the
    swap's coverage artifact, not the source, and is recorded as not
    representative).

    2026-10-11 ERRATUM (v29): the parenthetical above that presented
    45/44/54/57 as "the brief's own earlier reading" of the cirrhosis
    swap mislabels that row — it was never a reading of the cirrhosis
    swap at all. The v28.3 brief's 45/44/54/57 was the COMBINATION of
    the three swaps (homicide + suicide + cirrhosis) presented under
    the cirrhosis label; the brief was wrong, not the measurement.
    Re-run on 2026-10-11 by BOTH tools (the repo-core swap on the
    pristine V28.3 dist; the reference prototype — agreeing on every
    row): cirrhosis alone 40/42/45/49 (unchanged), the three-swap
    combination 45/44/54/57 — the mislabelled row reproduced
    exactly, which is what it was. The conclusion stands
    unchanged: the cirrhosis row is not representative, because the
    only worldwide cirrhosis witness (WHO GHO) covers 2019 only.

    Why refused: (a) THE JOINT CONSTRAINT — a
    non-OECD country is kept out of the official score by the narrow
    components AS A SET (unemployment 35 entities, secondary and
    tertiary attainment 36, industrial employment 37, road deaths per
    vehicle 38, cirrhosis 45, homicide and suicide 46, illegitimate
    births 47 — the OECD/Eurostat-bound tier), so widening one or two
    components moves only the countries that already hold most of the
    others: +1 to +5 scored countries per year, against the modelled
    score's 159-166; (b) the UNODC promotion is a register switch for
    the 46 covered entities plus the GSH-revision mixing the memo
    recorded; (c) the WHO MDB route needs the anti-derivation rule
    amended (counts -> crude rates) — a constitutional change refused
    for a single-digit coverage gain. Reopens when: a single
    as-reported source widens SEVERAL of the narrow components at once
    (the decision-17 mirror: one collector, multiple components) —
    not before.

The auditor's delegated decisions (taken with data; Ediz can reverse):
weighted **arithmetic** mean (the geometric mean ranked nearly the same
— 0.98/0.94 rank correlation, 2015 — and breaks the additive
decomposition the frontend needs); **bounds_from_year 1990** (OWID's
1751-1820 deep history would otherwise set the scale); the **log set**
(infant mortality, homicide, HIV prevalence, maternal ratio, road
per-vehicle — skewness above 3, p99/p1 ratios of 25x and more);
fertility as a **target at 2.1** (distance `abs(ln(TFR/2.1))` — a
known simplification, replacement is higher where mortality is high);
**coverage 0.60**; **delta_min_common_weight 0.50**; the modelled
source rule (most country-years since 1990, tie to canonical, tie to
alphabetical); the presets `equal` and `todd` (book counts, floor 1 —
citation counts would give fertility ~28% of everything).

The layer's placement (the brief's architecture, now this repo's):
`src/score/` (pure functions — no network, no raw tier), input
`data/dist/indicators/*.json` + `config/score.yaml` (intent: directions,
transforms, sex handling, basis, provisional flags, corpus_metric) +
`config/score_bounds.yaml` (the frozen numbers, written ONLY by
`scripts/freeze_score_bounds.py`), output `data/dist/score/` —
`meta.json`, `official.json`, `modelled.json`, `golden_vectors.json`.
`rebuild` reads the frozen bounds and NEVER recomputes them; a drift
guard fails the build loudly on EITHER of its two triggers (v28.2,
decision 18): the frozen source no longer matches what the §4.4 rules
would pick, or the bounds sample's `n_sample` / `n_entities` drifts
beyond `bounds_drift_tolerance` (a fetch moved the coverage under the
score — re-freezing is a deliberate `bounds_version` bump, recorded in
the changelog, never an auto-refresh). The backend pre-computes
normalised values, retained sources, coverage and the two presets; the
frontend applies custom weights on top of the stored values per
`docs/score-contract.md`, and unit-tests itself against the golden
vectors.

## Consequences

The accepted negatives, stated as such:

- **The composition noise is measured and capped, not gone.** The
  exact-year rule of v27 made a score's composition jump with the
  sources' rhythms (PISA every ~3 years, tertiary attainment in 5-year
  steps, suicide and life expectancy at 60 stopping in 2021): a
  composition effect of 0.86 (official) / 0.95 (modelled) score points
  per year against a real mean annual change of about 1.4, sign
  reversals in about 18-20% of consecutive-year pairs. The v28 carry
  rule (decision 16) cuts that noise to 0.33 / 0.34 — at the price the
  amendment names: the last three years of a series are largely carried
  values (2025: 74 modelled countries, 32 official), every carried
  component wears its age and the frontend badge "data from YYYY", and
  the carried share (13.5% official / 9.3% modelled of scored values)
  is displayed, not hidden. A gap longer than 3 years is still a gap.
- **"Official" means the canonical tier, not "non-modelled"**: obesity
  (WHO) and HIV are modeled estimates, top income share rides
  OWID/WID. The contract says so; the badge `source_class: modelled`
  flags the (currently empty, tested on a fixture) official fallback.
- **The fertility target is a simplification** (2.1 everywhere;
  replacement is higher where mortality is high).
- **The official fertility scale is the worldwide canonical sample**
  (v28.2, decision 18): p1/p99 over 2,523 observations across 177
  entities — the two-collector canonical the v28.1 wiring built, no
  longer the European 47-entity sample the scale was first frozen on.
  The consequence is the p99 tail semantics: a country-year whose TFR
  distance sits beyond the sample's p99 reads 0 on the component —
  TFR above 5.65 or below 0.78 (26 country-years across 10 entities
  on the current dist). Korea 2023 (TFR 0.721, distance 1.069) does
  exactly that: 1.069 > 0.990, so the component reads 0 — that is the
  tail rule, NOT a Korea-specific scale, and the same reading applies
  to every point beyond p99, nothing more (the v28.1 entry had
  attributed the retained tail to "Korea and Macao" specifically; the
  attribution is corrected here — those are simply the points beyond
  the percentile, and the regenerated scale still leaves Korea 2023
  beyond it).
- **The modelled score's fertility scale is untouched** by decision 18
  (its component reads the World Bank witness, whose sample did not
  move): every modelled normalised value and score is identical to
  v28.1 — only the two files' per-component `bounds_version` metadata
  moved with the freeze.
- **No provisional direction remains**: industrial employment, tertiary
  attainment, the fertility target and top income share are confirmed
  in the books (decisions 12-14, v28) — the `provisional` flags and
  the last `basis: editorial` entries retired with them.
- **The modelled score lacks road mortality per-vehicle** (decision 6's
  corollary) **and `illegitimate_births`** (decision 15, v28 — 47
  entities, almost all European): it compares ~140 countries on 16
  indicators, not 18. The official score gains the illégitimité and
  with it a stronger European weight in its composition — the
  asymmetry is the price of not pushing ~40 non-European countries per
  year under the coverage threshold.
- The todd preset gives fertility 16 of 99 indicator weight on the
  official score (92 modelled — the per-vehicle component's book count
  is official-only; v27.1 removed incarceration's weight 3 from the
  96/95 it was; v28 added illegitimate_births' 6 to the official side).
  The concentration is Todd's own book counts — displayed, not hidden;
  the equal preset exists precisely because of it.
- **The official score of 2000 is 21 countries, not 3** (v28): the
  carry rule undoes v27.1's threshold fall (countries that lost
  coverage when the total weight shrank to 17 regain it when
  observations are carried), and the first years of a score follow
  from the resolved data. The right edge is the honest new cost: no
  score year exists beyond the score's max_obs_year (2025 for both
  scores today), and a country-year with coverage above the threshold
  but nothing fresh is a ghost — refused (3 such country-years in
  2025, official).

The indicator layer is untouched by all of this — the derivation lives
in its own layer, its own config, its own ADR, labelled derived
everywhere — with decision 10's single flag flip as the one deliberate,
Breaking, reviewable exception (decisions 11 and 15, like 7 and 9 before
them, touch the score layer only). The score layer retires the
"composite-derived-layer" reserve: the question architecture.md held
open since v15 is answered, here, in writing.

---

## Amendment 2026-10-13 (v30): decision 20, "official" means published by
## a state statistical service

**Decision 20 (Ediz, 2026-10-13).** The official score keeps only figures
that statistical services of the state produce and publish (civil
registration, censuses, their own surveys such as labour-force surveys),
with no model behind them. `hiv_prevalence_rate` (UNAIDS modelled
estimates produced with Spectrum), `obesity_rate` (the NCD-RisC Bayesian
hierarchical model, estimated for every country-year) and
`top_income_share` (the WID constructed series: fiscal microdata,
surveys and national accounts combined) move to the **modelled score
only**. They stay indicators, `todd_core` unchanged, with the same
canonical source; the schema refuses them on the official side
(`MODELLED_ONLY_INDICATORS`, the mirror of decision 15's list).

Measured effect (read live on the shipped dist): the official score is
17 components / weight 15 (todd preset 92, was 99); the modelled score is
value-identical (only the per-component `bounds_version` moved); the
bounds were regenerated by the freezer alone at `2026-10-13.1` with the
invariant proven (exactly the three official blocks removed, every other
block keeps every field); the scored country-year sets move
in the equal preset (net -3 to +1 over 2010-2024; 2015: 47 -> 44, Argentina, Colombia and Moldova
fall under the 0.60 threshold; 2019: 42 -> 43, Japan enters). The
2015 official head is still Japan (83.17, was 83.54), then Australia
79.79, New Zealand 77.47, Israel 75.50, Canada 75.34.

Rule recorded for future wirings: a source is canonical-official only if
the series is published by the statistical services themselves, surveys
included; anything an international institution recalculates, imputes or
models belongs to the modelled side (so UNESCO UIS attainment rates and
ILO modelled estimates are modelled, while the ILO series flagged `LFS`
or `OE` by their per-observation SOURCE are candidates for the official
side).

Follow-up (2026-10-13, v30): the same fact is now carried by the indicator
config and the dist. `canonical_nature` (`published` | `modelled`, default
`published`) is an additive field of every indicator file and of
`catalog.json`; the three decision-20 indicators declare `modelled`, and a
test keeps this field and the schema's `MODELLED_ONLY_INDICATORS` list equal.
The canonical source of record is unchanged (the schema still requires one
canonical source per indicator); consumers show a `modelled` canonical series
as an estimate, never as an official figure.

---

## Amendment 2026-10-14 (v30): decision 21, two metric sets - Todd, and Todd + extra

**Decision 21 (Ediz, 2026-10-14).** The user can choose, for the score,
between the metrics Todd uses in his books ("Todd only") and those plus the
metrics outside them ("Todd + extra"). The metrics outside Todd's books are
catalogued in `extra_core.csv` (same layout as `todd_core.csv` minus the book
and citation columns, one row per metric), turned one way into
`config/extra_refs.yaml` by `scripts/normalize_extra_refs.py` and published as
`dist/extra_corpus.json`; the config loader cross-validates it with the
indicators' `todd_core` flag (every `todd_core: false` indicator is listed, no
metric is in both corpora).

In the score layer this is two more presets, `equal_todd_only` and
`todd_todd_only`: the same weightings with weight 0 on the `extra` components
(`corpus_set` on every component). The extra components weigh 1 under both
weightings. The existing `equal` and `todd` presets are unchanged, byte for
byte. Today the extra components are life expectancy at 60 (male, female),
the maternal mortality ratio and road deaths per vehicle (official only).

Measured effect (read live on the shipped dist): official equal preset in
2015, 44 scored countries with the extra components and 34 without; the
Todd-only head is Switzerland (72.90), where the extra set had Japan (83.17),
which only reaches the 0.60 coverage threshold thanks to the extra components.
Planned extra metrics (not yet wired) are listed in `extra_core.csv` and
`dist/extra_corpus.json` with `implemented: false`.

---

## Amendment 2026-10-14 (v30): decision 22, the UNESCO UIS attainment rates feed the modelled score

**Decision 22 (Ediz, 2026-10-14).** The UNESCO Institute for Statistics'
attainment rates (UIS Data API, `api.uis.unesco.org`, provider `unesco_uis`,
harmonized tier, root `unesco_uis`) are wired as WITNESSES of
`secondary_education_share` (`EA.3T8.AG25T99`, upper secondary or higher, age
25+) and `tertiary_education_share` (`EA.5T8.AG25T99`, short-cycle tertiary or
higher, age 25+). The UIS compiles national censuses and household surveys,
maps them to ISCED and computes the rates itself: an estimate by decision 20's
rule, so the official score keeps the Eurostat canonical (36 countries, scores
unchanged) and only the MODELLED score, which reads the widest-coverage single
source per component, switches to the UIS (200 and 189 entities against 36).

Definition seams, displayed and never reconciled: the UIS secondary rate is
"upper secondary OR higher" (ISCED 3-8), the Eurostat canonical is the
completed-secondary face ED3_4 (tertiary excluded), and both UIS rates use the
age band 25+ against Eurostat's 25-64. The UIS wire prints no per-point
provenance (`magnitude` and `qualifier` are null): a census, a survey or a UIS
calculation are not distinguishable. License: CC BY-SA 4.0 (credit the UIS).

The frozen bounds were regenerated by the freezer alone at `2026-10-14.1`
with the invariant proven field by field: exactly two blocks change
(`modelled/secondary_education_share/both`, 36 -> 200 entities, 1,000 -> 2,370
observations, hi 75.2 -> 94.36; `modelled/tertiary_education_share/both`,
36 -> 189 entities, 1,000 -> 2,185 observations), every other block keeps
every field but its version. Measured effect on the modelled score: no
country-year is lost, the scored sets grow (equal preset: 2015 165 -> 170,
2019 166 -> 173, 2025 74 -> 114), the 2015 head is still Japan (84.45) and
Singapore falls from second to third; the official score is byte-identical in
values (only `bounds_version` moved).

The UIS also feeds the extra metric `mean_years_of_schooling`
(`MYS.1T8.AG25T99`, 207 areas, 1970-2024, `canonical_nature: modelled`,
indicator only, not in the score).

---

## Amendment 2026-10-14 (v30): decision 23, licensing posture and the abortion ranking direction

**Decision 23 (Ediz, 2026-10-14).** (1) ToddLab will never be commercial: the
NonCommercial condition of the WHO/Europe data (inferred CC BY-NC-SA 3.0 IGO,
`abortion_rate`) therefore holds; ShareAlike keeps applying to the files that
carry it. (2) For `abortion_rate` a lower ratio ranks as "better"
(`higher_is_better: false` is a decision, no longer a descriptive default).
(3) The WHO/Europe definition ("induced abortions, irrespective of the
method") is kept over the extra-metric list's "legally induced" wording.

---

## Amendment 2026-10-14 (v30): decision 24, marker rules for the three extra legalization years

**Decision 24 (Ediz, 2026-10-14).** The three marker metrics outside Todd's
books are curated tables, one row per country, each row citing its source.
(1) Women's suffrage = the year women can vote in national elections ON EQUAL
TERMS (restrictions lifted); the first, restricted grant rides the row's
`definition_note` (United Kingdom 1928, Belgium 1948, Switzerland 1971,
Australia 1962). (2) Divorce and abortion = the start of the CURRENT,
uninterrupted legal availability; earlier episodes (France divorce 1792, the
USSR abortion 1920) go in the note. (3) Perimeter: every country for which a
dated, citable law is found; the others stay absent.

`womens_suffrage_introduction_year` is the first of the three: the
Inter-Parliamentary Union "Women's Suffrage" archive table (185 countries,
1893-2005), generated by script from the page and reviewed. Compared with the
Lexical Index of Electoral Democracy (effective universal right, via OWID) the
IPU's legal dates agree for 68 of 179 matched countries; the rest are mostly
1-2 years apart, a few differ by decades (Brazil 1932 / 1985, South Africa
1930 / 1994, Chile 1949 / 1970): a different concept, not wired as a witness.

Abortion and divorce tables (same amendment). `abortion_legalization_year` (50
countries, 1948-2022) and `divorce_legalization_year` (12 countries, 1911-2011)
are curated from English Wikipedia articles read 2026-10-14, one citation and
one scope note per row; they are secondary-source and indicative. Absences are
deliberate: Poland (1956 broad grounds, reversed 1993), Germany, Malta and the
United States (after 2022) for abortion; every country with no single
legalization date (France, the United Kingdom, the Nordic countries) and the
Philippines and the Vatican (no legal divorce) for divorce. The drug-induced
deaths metric remains listed in `extra_core.csv` without an indicator (EUDA
data not reachable, owner decision 2026-10-14 to drop it).

---

## Amendment 2026-10-14 (v30): decision 25, the extra metrics enter the score; the summation rule

**Decision 25 (Ediz, 2026-10-14).** The extra metrics that can be scored enter
the score under `corpus_set: extra` (weight 1 in `equal` and `todd`, 0 in the
Todd-only presets): `reading_test_scores`, `science_test_scores`,
`mean_years_of_schooling`, `youth_suicide_rate`, `abortion_rate`, next to the
three already in. Placement, by the rules of decisions 15 and 20:
`mean_years_of_schooling` is modelled-score-only (UIS estimate, added to
`MODELLED_ONLY_INDICATORS`); `youth_suicide_rate` and `abortion_rate` are
official-score-only (added to `OFFICIAL_ONLY_INDICATORS`: 36 and 49 European
countries); PISA reading and science ride both scores like the math component.
`abortion_rate` ranks lower = better (decision 23), linear transform. The three
legalization-year markers and the count / crude-rate series excluded by
decisions 7, 9 and 11 stay out. `drug_induced_deaths` was removed from
`extra_core.csv` (EUDA data unreachable).

Bounds regenerated by the freezer alone (`2026-10-14.10`; the counter moved
through several trial freezes): exactly seven blocks are added (official:
`abortion_rate`, `reading_test_scores`, `science_test_scores`,
`youth_suicide_rate`; modelled: `mean_years_of_schooling`,
`reading_test_scores`, `science_test_scores`), no existing block changed.
Todd-only scores are identical to the previous build.

Measured cost, equal preset, countries scored (before -> after): official 2015
44 -> 37, 2019 43 -> 37; modelled 2015 170 -> 144, 2019 173 -> 158. Per metric
alone (2015): youth suicide and abortion -7 official each; reading and science
-15 modelled each (the same non-PISA countries, hence -26 together); mean years
of schooling -13 modelled. Japan leaves the official extra set (no European
health series), and the PISA domains now weigh 3 of 21 components. The Todd-only
set is the lever for maximal coverage.

**Rounding and summation (found while regenerating the golden vectors).** The
score-core in the frontend and the backend disagreed on one tie (Albania 2010,
modelled, equal: 56.39 against 56.38). Two causes. (1) Python 3.12 made
builtin `sum()` of floats compensated, so the backend's last bit differed from a
plain left-to-right addition (and from JavaScript, and from Python 3.11): the
weighted sums now use an explicit plain loop (`_ordered_sum` in
`src/score/core.py`). (2) The frontend's `roundTo` used `Math.round(x * f) / f`,
which can land on a false tie; it now rounds like Python's `round()` (exact
value, ties to even). Effect on the stored scores: 136 of 24,067 values moved by
0.01 (rounding ties); the frontend now reproduces every stored score exactly
(24,067 of 24,067, tolerance 0) and all 24 golden vectors.

---

## Amendment 2026-10-15 (v30): decision 26, comparing countries and ranking the movers; unresolved names

**Decision 26 (Ediz, 2026-10-15).** The web app gets (1) a "compare with another
country" shortcut from the country page, (2) official and modelled side by side
in the country comparison, (3) a marker for the years in which a comparison is
not comparable (the countries share less than `delta_min_common_weight` of the
scored weight; contract section added), and (4) a ranking of the biggest score
gains and drops over a chosen period, ranked by the contract's delta and
limited to countries scored in both years. Measured on the official equal
preset the 0.50 threshold flags 1.7% of country pairs in 2015 and 3.2% in 2022
(0.0% in 2005); the shared share is always shown, the flag is the contract's.

**Unresolved names (same decision).** Of the 87 distinct names that the
normaliser could not resolve, 80 were aggregates (regions, income groups, WID,
UNAIDS and UN roll-ups, OECD / PISA averages) or sub-national parts (Scotland,
Northern Ireland, England and Wales, Kurdistan Region, the two Bosnian
entities) and were reported as "likely mapping gap" because only `OWID_` codes
were recognised as special. They now land in a `known_non_country` bucket and
rebuild logs no warning. Three real gaps were fixed: "Congo, DRC" (NCD-RisC's
name for the Democratic Republic of the Congo, 11 male-height points),
"Saint-Barthélemy" (UN Yearbook spelling). Left out on purpose: the Channel
Islands (no umbrella entity is invented) and the two UN Yearbook pieces of
Saint Helena (attaching one piece to the whole territory would be an
approximation). The OWID entity names may now be a list, like the Yearbook's.

**Decision 27 (Ediz, 2026-10-15).** Entities that do not exist as countries are
removed, unless they existed at some point in history (the USSR, North and
South Yemen, Chechnya would qualify; the sub-national names Kurdistan, the two
Bosnian entities, Balochistan are not entities here and stay dropped at import).
Applied: the 12 current territories without a single data point (Antarctica,
Bouvet, Heard and McDonald, the French Southern Territories, the British Indian
Ocean Territory, South Georgia, the US Minor Outlying Islands, Svalbard and Jan
Mayen, Cocos, Christmas, Norfolk, Pitcairn) are removed from `entities.yaml`
(261 -> 249 entities); the five historical entities without data (West Germany,
Yemen Arab Republic, Yemen People's Republic, Serbia and Montenegro, the
Netherlands Antilles) are kept. Measured: no non-null value changes, scores
unchanged (only null points of Norfolk Island and Pitcairn leave four indicator
files).

---

## Amendment 2026-10-15 (v30): decision 28, coverage counts components; threshold 0.50

**Finding (Ediz, on the modelled score).** Switching the weighting from Egal to
Todd changed the number of countries available (90 -> 139 in 2025). Cause:
coverage was a share of the preset's WEIGHT. In the Todd preset four metrics
(fertility 16, infant mortality 13, suicide 11, homicide 10) carry 50 of the 95
total, so a country without PISA, schooling and the other single-weight
metrics still covers 60% of the weight (Algeria 61%, Bangladesh 60%) while it
covers 42-47% of the components under Egal. The gap existed before the extra
metrics (2015: 170 against 188 countries) and widened with them (144 against
189).

**Decision 28 (Ediz, 2026-10-15).** (1) The weighting changes the mean, never
which countries are scored: coverage is the share of COMPONENTS available, each
indicator counting 1 and each sex face of a sex-split indicator 0.5 (the Egal
weights), among the components with weight > 0. The same holds for the
common-component share that gates a delta, for the web app's comparability
marker and for custom weights. (2) `coverage_threshold` is lowered from 0.60 to
0.50 for every calculation (`delta_min_common_weight` was already 0.50). The
stored `coverage` field now holds the component share; `common_weight_share`
keeps its historical name and holds the common-component share.

Implementation: `unit_weight` / `unit_total` in `src/score/core.py`,
`unitWeightOf` in the frontend `score-core.ts`; bounds regenerated by the
freezer alone (`2026-10-15.1`, the config hash moved). Measured, countries
scored (Egal = Todd, now the same set for every country-year in both scores;
the two Todd-only presets also share one set): official 49 / 48 / 32 in
2015 / 2019 / 2025 (was 37 / 37 / 32 for Egal and 44 / 44 / 31 for Todd);
modelled 173 / 176 / 125 (was 144 / 158 / 90 for Egal and 189 / 189 / 139 for
Todd). The Todd + extra set is now never larger than what the Egal weighting
gave before, except where the lower threshold admits more countries; the
Todd-only sets: official 51 / 48 / 33, modelled 186 / 185 / 156.
The frontend reproduces all 26,646 stored scores exactly and all 24 golden
vectors. The figures of decision 26 about comparability were measured under the
previous weight-based rule.
