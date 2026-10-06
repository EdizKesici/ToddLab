# The score layer's frontend contract (v27, amended v27.1 and v28, ADR-0011)

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
- **Two scores, never merged**: `official` (canonical-tier sources, 20
  components / total weight 18, 18 indicators — illegitimate_births
  among them since v28) and `modelled` (widest-coverage single source
  per component, 18 components / total weight 16, 16 indicators, ~140
  countries). They diverge where modeling runs ahead of collection;
  the divergence is the signal. Display them side by side, never
  average them.
- **"Official" means the canonical tier of this project, not
  "non-modelled"**: obesity (WHO) and HIV are modeled estimates,
  top income share rides OWID/WID. A component inside the official
  score whose retained source is a witness carries
  `source_class: "modelled"` — surface the badge.
- **The v28 carry rule is NOT interpolation** (decision 16, amends
  ADR-0011's decision 3): no value is invented — a real, older
  observation is reused, capped at `max_age_years` (3), and labelled
  with its age.

## The files

- `data/dist/score/meta.json` — the layer's contract card: global
  parameters (`bounds_from_year`, `percentiles`, `coverage_threshold`,
  `delta_min_common_weight`, `fertility_target`, `rounding`,
  `max_age_years`), the `carry_rule` description, `max_obs_year` per
  score, the component list (`direction`, `transform`, `basis`,
  `provisional`, `sex`, `corpus_metric`), BOTH presets' weights per
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
  - `scores`: per preset (`equal`, `todd`), `entity_id -> year ->
    [score, coverage]`, EMITTED ONLY where `coverage >=
    coverage_threshold` (0.60) AND at least one component is FRESH
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
- Coverage counts a carried component as available (its full weight).
- A score EXISTS iff `coverage >= coverage_threshold` AND at least one
  component is fresh at `Y` (the ghost guard: a country-year living
  entirely on carried values is refused).

## The formulas

### Score of a year (custom weights)

```
score(e, y)   = sum(w_c * n_c(e, y)) / sum(w_c)        over components c
                with a resolved value for (e, y)
coverage(e,y) = sum(w_c available) / sum(w_c all components of the score)
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
- Display: `|C|`, the common-weight share `sum_C(w_c) /
  sum(w_c all)`, and each component's term `w_c * (n_c(y2) -
  n_c(y1)) / sum_C(w)` (the additive decomposition — arithmetic means
  give you this for free; it is why they were chosen).
- REFUSE when `C` is empty or the common-weight share is below
  `delta_min_common_weight` (0.50). Refusal is information ("the two
  years do not overlap enough to compare"), display it as such.

### The presets

- `equal`: weight 1 per indicator (0.5 per sex component).
- `todd`: weight = the number of DISTINCT BOOKS citing the component's
  `corpus_metric` in the Todd corpus (floor 1 when null or 0).
  Fertility carries 16 of 99 indicator weight on the official score
  (92 modelled — v28 added illegitimate_births' 6 to the official
  side) — the concentration is Todd's own reading, display it, and
  offer `equal` beside it.

## Display discipline (the three prohibitions, applied to rendering)

- **Gaps are still visible**: a gap longer than 3 years is a gap — no
  smoothed curve, no interpolated year, no carry beyond
  `max_age_years`. A country-year with coverage < 0.60 shows its
  components, not a score; a ghost (coverage >= 0.60, nothing fresh)
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
  at generation time. Never re-rank per year.
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

- The composition noise is cut, not gone (0.33/0.34 points per year,
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
