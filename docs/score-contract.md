# The score layer's frontend contract (v27, amended v27.1, v28, v28.1,
# v28.2 and v30, ADR-0011)

This is the EXACT, documented contract for computing a score, a custom-
weighted score, or a two-year difference from `data/dist/score/`. The
backend pre-computes everything the presets need; the frontend's job is
rendering and CUSTOM weights — this document is what to re-implement,
and `golden_vectors.json` is what to unit-test against.

## What the score IS (and is not)

- A **derived product**: weighted arithmetic means of normalised
  indicator values on a frozen absolute scale. NOT a measurement. The
  indicator layer's three prohibitions (no interpolation, no
  derivation, no reconciliation) are untouched — the score derives
  openly from what the indicators measured, and every file says so.
- **Two scores, never merged**: `official` (canonical-tier sources, 21
  components / total weight 19, 19 indicators — illegitimate_births
  among them since v28; 37 countries scored in 2019 in the Todd + extra
  set) and `modelled` (widest-coverage single source per component, 21
  components / total weight 19, 19 indicators, 158 countries in 2019 in
  the Todd + extra set). They diverge where modeling runs ahead of collection;
  the divergence is the signal. Display them side by side, never
  average them.
- **"Official" means figures published by state statistical services**
  (registers, censuses, their own surveys), with no model behind them.
  Since v30 (decision 20) the three model-based or compiled series are
  in the modelled score only: HIV (UNAIDS modelled estimates), obesity
  (NCD-RisC Bayesian model) and top income share (WID constructed
  series). A component inside the official score whose retained source
  is a witness would carry `source_class: "modelled"` — surface the
  badge.
- **The v28 carry rule is NOT interpolation** (decision 16, amends
  ADR-0011's decision 3): no value is invented — a real, older
  observation is reused, capped at `max_age_years` (3), and labelled
  with its age.
- **The official fertility component is a PRIORITY MERGE of two
  as-reported collectors** (decision 17, v28.1): Eurostat's
  `demo_find` TFR (priorities 1-3) wins on every shared entity-year,
  and the DYB Table 4 TFR fills every entity-year Eurostat does not
  print — one component, two collectors, never reconciled. Measured on
  the shipped provenance log (live, 2026-10-08): of the 568 shared
  entity-years, 220 agree exactly, 157 within 0.01, 128 within 0.05 —
  about 90% at rounding level (the v28.1 entry said 564; the live
  count on the shipped arbitration log is 568, the correction recorded
  in the v28.2 changelog). 7 entities show collector-vs-collector
  seams >= 0.1 (Azerbaijan up to 0.44; Romania, Bulgaria, Georgia,
  Latvia, Moldova, Montenegro — Eurostat's value always wins, the
  discarded DYB candidate logged per point), and the 130 DYB-only
  entities (Japan, Korea, the US, Israel, New Zealand, Latin America,
  Asia, Africa's civil-registration countries) have no second
  collector to cross-check at all. DO NOT treat cross-country
  differences on this component as exact below the ~0.05 TFR level:
  within that band the two collectors' prints are interchangeable at
  rounding level, and at the seams they genuinely disagree.

## The files

- `data/dist/score/meta.json` — the layer's contract card: global
  parameters (`bounds_from_year`, `percentiles`, `coverage_threshold`,
  `delta_min_common_weight`, `fertility_target`, `rounding`,
  `max_age_years`, `bounds_drift_tolerance` — the drift guard's refusal
  threshold since v28.2), the `carry_rule` description, `max_obs_year` per
  score, the component list (`direction`, `transform`, `basis`,
  `provisional`, `sex`, `corpus_metric`, `corpus_set`), ALL FOUR presets' weights per
  component, input fingerprints (config/bounds/corpus sha256), and the
  excluded ids with reasons.
- `data/dist/score/official.json` / `modelled.json` — per score:
  - `components`: per `indicator/sex` key, the retained-source metadata
    (`source`, `source_class`, `root`, `layer`, `n_points`,
    `n_entities`, `year_min/max`) AND the frozen bounds (`floor`, `lo`,
    `hi`, `n_sample`, `bounds_version`).
  - `normalised`: per `indicator/sex`, `entity_id -> year -> value`
    (0..100, rounded to `rounding` decimals) — the RESOLVED values
    (fresh or carried, see the carry rule below) for every year of
    `[bounds_from_year, max_obs_year]`.
  - `age`: per `indicator/sex`, `entity_id -> year -> age`, SPARSE —
    present only where `age >= 1` (a carried value); absent = fresh
    (age 0). `obs_year = year - age` is the observation the value
    rests on.
  - `scores`: per preset (`equal`, `todd`, `equal_todd_only`, `todd_todd_only`), `entity_id -> year ->
    [score, coverage]`, EMITTED ONLY where `coverage >=
    coverage_threshold` (0.50) AND at least one component is FRESH
    (age 0) — the ghost guard. No year beyond `max_obs_year` exists.
- `data/dist/score/golden_vectors.json` — ≤ 20 hand-checkable cases
  (score/coverage, deltas accepted and refused, the split-sex case, the
  log and target components, the coverage-just-below-threshold case, a
  carried component, a same-observation-exclusion delta, the right
  edge, an illegitimate_births official point, a ghost-guard refusal).
  Your implementation must reproduce every one.

## The carry rule (v28, decision 16)

For each (score, component, entity) and each year `Y` in
`[bounds_from_year, max_obs_year]`:

```
value(Y) = the normalised value of the LATEST real observation
           with obs_year in [Y - max_age_years, Y]   (max_age_years = 3)
age(Y)   = Y - obs_year          (0 = fresh; recorded in `age` when >= 1)
```

- The value used is the STORED (rounded) normalised value of that
  observation — never re-derive it from the indicator files.
- Nothing is carried across entities, sources or sexes; a gap longer
  than `max_age_years` is still a gap (no value, no coverage).
- `max_obs_year` (in `meta.json`, 2025 for both scores today) is the
  greatest year with a real observation in any retained source of the
  score — no score year exists beyond it.
- Coverage counts a carried component as available. Since decision 28 (v30)
  coverage is the share of COMPONENTS available (each indicator 1, each sex face
  of a sex-split indicator 0.5: the 'equal' weights), never of the preset's
  weight, so Egal, Todd and custom weights score exactly the same
  country-years; the weighting only changes the mean.
- A score EXISTS iff `coverage >= coverage_threshold` AND at least one
  component is fresh at `Y` (the ghost guard: a country-year living
  entirely on carried values is refused).

## The formulas

### Score of a year (custom weights)

```
score(e, y)   = sum(w_c * n_c(e, y)) / sum(w_c)        over components c
                with a resolved value for (e, y)
coverage(e,y) = sum(u_c available) / sum(u_c all components of the score)
                u_c = 1 per indicator, 0.5 per sex face (decision 28); only
                components with w_c > 0 are counted
```

- `n_c` values come from `normalised` (the stored, resolved values).
- Show the coverage next to every score; show the component count
  behind it.
- Sex-split components (life expectancy, life expectancy at 60) are two
  keys (`indicator/male`, `indicator/female`); in the presets each
  carries HALF the indicator's weight. Custom weights are yours: apply
  them to component keys directly.

### Difference between two years (one country, one score)

```
C       = components with a resolved value at BOTH y1 and y2
          WHOSE UNDERLYING OBSERVATION DIFFERS
          (obs_year(y1) != obs_year(y2); obs_year = year - age,
          age read from `age`, 0 when absent)
delta   = sum_{c in C}(w_c * (n_c(y2) - n_c(y1))) / sum_{c in C}(w_c)
```

- The exclusion is the v28 amendment: a component resting on the SAME
  observation at both dates contributes a zero term that would damp the
  delta and dilute the common weight — it must not be in C.
- Display: `|C|`, the common-component share `sum_C(u_c) /
  sum(u_c all)` (u_c: 1 per indicator, 0.5 per sex face, decision 28; the
  field keeps its historical name `common_weight_share`), and each component's term `w_c * (n_c(y2) -
  n_c(y1)) / sum_C(w)` (the additive decomposition — arithmetic means
  give you this for free; it is why they were chosen).
- REFUSE when `C` is empty or the common-component share is below
  `delta_min_common_weight` (0.50). Refusal is information ("the two
  years do not overlap enough to compare"), display it as such.

### The metric sets (v30, decision 21)

Every component carries `corpus_set`: `todd` (the indicator is in Todd's
books, `todd_core: true`) or `extra` (outside them, listed in
`extra_core.csv`). The score is stored for two metric sets:

- **Todd + extra** (`equal`, `todd`): every component, as before;
- **Todd only** (`equal_todd_only`, `todd_todd_only`): the same weighting,
  with weight **0** on every `extra` component.

The extra components weigh 1 under BOTH weightings (they have no books to
count). Since decision 25 (v30) eight extra metrics are components:
`life_expectancy_60`, `maternal_mortality_ratio` and
`road_accident_mortality_per_vehicle` (official or both, as before),
`reading_test_scores` and `science_test_scores` (both scores, like the Todd
PISA math component), `mean_years_of_schooling` (modelled only: UNESCO UIS
estimate) and `youth_suicide_rate` and `abortion_rate` (official only: the
data cover 36 and 49 European countries, and in the modelled score they would
push most non-European countries under the coverage threshold). The three
legalization-year markers cannot enter a mean of normalised values and stay
indicators. Measured cost of the extra set, 2015, equal preset: official 44 ->
37 countries scored, modelled 170 -> 144; the Todd-only sets are unchanged. A component with weight 0 takes no part at all: not in the weighted
mean, not in the coverage denominator, not in a delta (neither `n_components`
nor the decomposition), and not in the ghost guard (a Todd-only score needs a
fresh component among the weighted ones). A frontend re-implementing custom
weights must skip `weight <= 0` the same way.

### The presets

- `equal`: weight 1 per indicator (0.5 per sex component).
- `todd`: weight = the number of DISTINCT BOOKS citing the component's
  `corpus_metric` in the Todd corpus (floor 1 when null or 0).
  Fertility carries 15 of 89 indicator weight in the Todd + extra set, on
  both scores (82 on the official and 84 on the modelled score in the
  Todd-only set; read from `meta.json`, 2026-10-17, after the corpus
  dropped the book without predictions) — the concentration is Todd's own
  reading, display it, and offer `equal` beside it.

## Display discipline (the three prohibitions, applied to rendering)

- **Gaps are still visible**: a gap longer than 3 years is a gap — no
  smoothed curve, no interpolated year, no carry beyond
  `max_age_years`. A country-year with coverage < 0.50 shows its
  components, not a score; a ghost (coverage >= 0.50, nothing fresh)
  shows nothing at all.
- **Carried values are labelled, never disguised**: when `age > 0`,
  display the badge **"data from YYYY"** (YYYY = `year - age`) next to
  the component; display the carried-value share of a score (the share
  of its resolved values with `age >= 1`) — 13.5% official / 9.3%
  modelled of scored values today — and never present a carried value
  as a fresh measurement.
- **The scale is absolute and frozen**: `bounds_version` in every
  component block. A score of 72 in 1995 and 72 in 2020 mean the same
  thing on the same scale — that is the point of p1/p99 bounds frozen
  at generation time. Never re-rank per year. Since v28.2 the frozen
  file also records each block's bounds-sample `n_sample` and
  `n_entities`, and the build REFUSES (it does not silently re-scale)
  if the live selection would pick another source OR if either measure
  drifts beyond `bounds_drift_tolerance` — the two drift triggers are
  the source NAME and the sample's coverage; both demand a deliberate
  re-freeze (`bounds_version` bump, changelog entry). Since v28.3 the
  frozen file is VALIDATED at load: every block's counts must be
  integers and strictly positive, or both CLI doors refuse the file
  outright (a missing or zero count is a refusal, never a skipped
  check).
- **Badges to surface**: `source_class: "modelled"` inside the official
  score; `reliability: "low"` of the underlying indicator (read the
  catalog); the chosen `source` per component; the component count
  behind every value. (The `provisional: true` badge retired with
  v28's decisions 12-14 — no direction awaits confirmation any more.)
- **`incarceration_rate` and `gini_index` are indicators OUTSIDE the
  score** (decisions 11 and 7). The catalog still carries
  `higher_is_better: false` for incarceration — that boolean PREDATES
  the decision and is NOT a judgment the score endorses: never use it
  for an evaluative display of that indicator.
- **The right edge is honest**: the last years of a series are largely
  carried (2022 modelled: suicide and life expectancy at 60 rest on
  2021); nothing exists beyond `max_obs_year`; the ghost guard refuses
  country-years with nothing fresh. Display all three facts, never
  trim them.

## Known limitations to carry into the UI

- The composition noise is cut, not gone (0.32/0.34 points per year,
  2000-2020, from 0.86/0.95 at the exact year) — and the price is
  that the last years of a series are largely carried values (2025:
  74 modelled countries, 32 official). Coverage and age display is
  the honest answer.
- The fertility target (2.1) is a simplification; replacement is
  higher where mortality is high.
- The modelled score has no road mortality per-vehicle (no world-wide
  source exists — decision 6) and no `illegitimate_births` (decision
  15: 47 entities, almost all European — adding it would push ~40
  non-European countries per year under the coverage threshold).
- The official score of 2000 carries 21 countries (the carry rule
  undid v27.1's threshold fall to 3); the first year of a score
  follows from the resolved data, by design (decision 8).
- Since v28.1 the official fertility component reads TWO collectors
  (Eurostat first, the DYB Table 4 TFR filling — decision 17): the
  official fertility normalised map carries 177 entities where it
  carried 47, and the UK's series resumes 2019-2023 (it was
  witness-only after Brexit). Since v28.2 (decision 18) the component's
  frozen scale is the WORLDWIDE canonical sample (bounds_version
  2026-10-08.1: hi 0.9903 on 2,523 observations / 177 entities — the
  European freeze of 2026-10-06.2, hi 0.611 on 1,278 / 47, is
  retired): the component reads 0 only beyond TFR 5.65 / below 0.78.
  The p99 tail semantics stay: korea 2023 (TFR 0.721, distance 1.069
  > 0.990) still reads 0 — that is the tail rule, not a Korea-specific
  scale and not an error; the points beyond p99 are simply
  indistinguishable on this component, nothing more.
- Cross-country differences on the official fertility component are
  not exact below the ~0.05 TFR level (the two-collector seam facts
  above): display the component's source badge, and treat small
  cross-country gaps as rounding-level agreement, not signal.
- 4 ghost country-years in 2025 official (australia, canada, chile,
  costa_rica): fertility coverage arrived for costa_rica, nothing
  fresh did — the guard holds.

### Comparing countries and ranking the movers (v30, decision 26)

- **Comparability of a country comparison.** For each year where at least two
  of the compared countries have an emitted score, the web app flags whether
  they share enough of the scored weight: the weight of the components resolved
  for EVERY scored country over the weight of those resolved for ANY of them.
  Below `delta_min_common_weight` (0.50, the contract's own threshold for a
  delta) the gap compares different components and is shaded and labelled "not
  comparable". It is read from the stored normalised values; nothing is
  recomputed. The gap shown is the one of the latest year where every selected
  country is scored.
- **Official and modelled side by side** is a view of two independent queries,
  never a merged series.
- **Movers.** `/api/score/movers` ranks every country scored in BOTH years of a
  chosen period by the delta of this contract (change over the components that
  rest on a different observation in both years, refused below the
  common-weight threshold; the refused count is reported). The delta can differ
  from the difference of the two published scores when their component sets
  differ; the web app flags those rows ("different components in the two
  years") instead of hiding it.
