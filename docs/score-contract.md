# The score layer's frontend contract (v27, ADR-0011)

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
- **Two scores, never merged**: `official` (canonical-tier sources,
  ~37 countries) and `modelled` (widest-coverage single source per
  component, ~110 countries). They diverge where modeling runs ahead of
  collection; the divergence is the signal. Display them side by side,
  never average them.
- **"Official" means the canonical tier of this project, not
  "non-modelled"**: obesity (WHO) and HIV are modeled estimates,
  top income share rides OWID/WID. A component inside the official
  score whose retained source is a witness carries
  `source_class: "modelled"` — surface the badge.

## The files

- `data/dist/score/meta.json` — the layer's contract card: global
  parameters (`bounds_from_year`, `percentiles`, `coverage_threshold`,
  `delta_min_common_weight`, `fertility_target`, `rounding`), the
  component list (`direction`, `transform`, `basis`, `provisional`,
  `sex`, `corpus_metric`), BOTH presets' weights per component, input
  fingerprints (config/bounds/corpus sha256), and the excluded ids with
  reasons.
- `data/dist/score/official.json` / `modelled.json` — per score:
  - `components`: per `indicator/sex` key, the retained-source metadata
    (`source`, `source_class`, `root`, `layer`, `n_points`,
    `n_entities`, `year_min/max`) AND the frozen bounds (`floor`, `lo`,
    `hi`, `n_sample`, `bounds_version`).
  - `normalised`: per `indicator/sex`, `entity_id -> year -> value`
    (0..100, rounded to `rounding` decimals). Available wherever the
    retained source has a non-null value at `year >= bounds_from_year` —
    including where no score exists.
  - `scores`: per preset (`equal`, `todd`), `entity_id -> year ->
    [score, coverage]`, EMITTED ONLY where `coverage >=
    coverage_threshold` (0.60).
- `data/dist/score/golden_vectors.json` — ≤ 20 hand-checkable cases
  (score/coverage, deltas accepted and refused, the split-sex case, the
  log and target components, the coverage-just-below-threshold case).
  Your implementation must reproduce every one.

## The formulas

### Score of a year (custom weights)

```
score(e, y)   = sum(w_c * n_c(e, y)) / sum(w_c)        over components c
                with a stored value for (e, y)
coverage(e,y) = sum(w_c available) / sum(w_c all components of the score)
```

- `n_c` values come from `normalised` (the stored, rounded values —
  never re-derive them from the indicator files).
- A score EXISTS iff `coverage >= coverage_threshold` (0.60). Show the
  coverage next to every score; show the component count behind it.
- Sex-split components (life expectancy, life expectancy at 60) are two
  keys (`indicator/male`, `indicator/female`); in the presets each
  carries HALF the indicator's weight. Custom weights are yours: apply
  them to component keys directly.

### Difference between two years (one country, one score)

```
C       = components with a stored value at BOTH y1 and y2
delta   = sum_{c in C}(w_c * (n_c(y2) - n_c(y1))) / sum_{c in C}(w_c)
```

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
  `corpus_metric` in the Todd corpus (floor 1 when null or 0). Fertility
  carries 16 of 96 — the concentration is Todd's own reading, display
  it, and offer `equal` beside it.

## Display discipline (the three prohibitions, applied to rendering)

- **Gaps are visible**: a missing component is missing — no smoothed
  curve, no carry-forward, no interpolated year. A country-year with
  coverage < 0.60 shows its components, not a score.
- **The scale is absolute and frozen**: `bounds_version` in every
  component block. A score of 72 in 1995 and 72 in 2020 mean the same
  thing on the same scale — that is the point of p1/p99 bounds frozen
  at generation time. Never re-rank per year.
- **Badges to surface**: `source_class: "modelled"` inside the official
  score; `reliability: "low"` of the underlying indicator (read the
  catalog); `provisional: true` directions (industrial employment,
  tertiary attainment — Ediz has not confirmed them in the books yet);
  the component count behind every value; the chosen `source` per
  component.

## Known limitations to carry into the UI

- The score per year is uneven because the sources' rhythms are (PISA
  ~3-year, tertiary 5-year, incarceration biennial on even years,
  suicide and LE-at-60 stop 2021, maternal mortality differs by door).
  This is accepted, not a bug; coverage display is the honest answer.
- The fertility target (2.1) is a simplification; replacement is higher
  where mortality is high.
- The modelled score has no road mortality per-vehicle (no world-wide
  source exists — decision 6).
- The official score starts where canonical by-sex life expectancy
  starts (~2007-2010) — the first year of a score follows from the
  data, by design (decision 8).
