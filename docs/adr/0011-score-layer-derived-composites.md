# ADR-0011: The score layer — two derived composites, official and modelled

- **Status**: ACCEPTED (2026-10-05, v27); AMENDED (2026-10-06, v27.1 —
  decision 11: `incarceration_rate` removed from the score only)
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
   property of it. No interpolation, ever.
4. A difference between two years is computed **only on the components
   available at both dates**, displays its common-component count and
   the per-component decomposition, and is REFUSED below 0.50 of common
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
   `road_accident_mortality` (per capita), the POSTPONED
   `illegitimate_births` (not included, not deleted), and the v26
   withdrawals.
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
guard fails the build loudly when the frozen source no longer matches
what the §4.4 rules would pick (a fetch moved the coverage under the
score — re-freezing is a deliberate `bounds_version` bump, recorded in
the changelog, never an auto-refresh). The backend pre-computes
normalised values, retained sources, coverage and the two presets; the
frontend applies custom weights on top of the stored values per
`docs/score-contract.md`, and unit-tests itself against the golden
vectors.

## Consequences

The accepted negatives, stated as such:

- **The score per year is uneven because the sources' rhythms are.**
  PISA prints every ~3 years, tertiary attainment in 5-year steps,
  suicide and life expectancy at 60 stop in 2021 (the GHE edition),
  maternal mortality differs by door (OWID to 2020, World Bank to
  2023). No carry-forward: a component absent in a year is absent in
  that year's score — Ediz's accepted worry about "the score per year",
  recorded, not solved. (v27.1 note: the incarceration alternation that
  motivated this bullet's first draft left with decision 11 — the
  cadence is an observed pattern whose cause was never established.)
- **"Official" means the canonical tier, not "non-modelled"**: obesity
  (WHO) and HIV are modeled estimates, top income share rides
  OWID/WID. The contract says so; the badge `source_class: modelled`
  flags the (currently empty, tested on a fixture) official fallback.
- **The fertility target is a simplification** (2.1 everywhere;
  replacement is higher where mortality is high).
- **Two provisional directions** (industrial employment, tertiary
  attainment) await Ediz's confirmation in the books — flagged in the
  config, emitted with every value.
- **The modelled score lacks road mortality per-vehicle** (decision 6's
  corollary): it compares ~140 countries on 16 indicators, not 17.
- The todd preset gives fertility 16 of 93 indicator weight on the
  official score (92 modelled — the per-vehicle component's book count
  is official-only; v27.1 removed incarceration's weight 3 from the
  96/95 it was). The concentration is Todd's own book counts —
  displayed, not hidden; the equal preset exists precisely because of
  it.
- **The official score of 2000 falls from 20 countries to 3** (v27.1):
  countries sat just above the 0.60 coverage threshold and fall just
  below it when the total weight shrinks to 17 — the official score
  effectively starts around 2005. An expected threshold effect,
  reported in the changelog's Known limitations, not fixed.

The indicator layer is untouched by all of this — the derivation lives
in its own layer, its own config, its own ADR, labelled derived
everywhere — with decision 10's single flag flip as the one deliberate,
Breaking, reviewable exception (decision 11, like 7 and 9 before it,
touches the score layer only). The score layer retires the
"composite-derived-layer" reserve: the question architecture.md held
open since v15 is answered, here, in writing.
