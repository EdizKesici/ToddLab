/**
 * ToddLab score layer — client-side contract math (docs/score-contract.md, ADR-0011).
 *
 * Pure functions, no server imports: the backend pre-computes the presets;
 * this module renders CUSTOM weights and the two-year delta from the stored
 * `normalised` (resolved values) and sparse `age` maps. It must reproduce the
 * backend's golden vectors exactly.
 *
 * Contract facts implemented here:
 * - score(e,y)  = sum(w_c * n_c) / sum(w_c)      over components with a resolved value
 *   (components with weight 0 - outside a Todd-only preset - take no part at all)
 * - coverage    = sum(w_c available) / sum(w_c all components of the score)
 * - a score EXISTS iff coverage >= threshold AND at least one component is FRESH
 *   (age 0 — the ghost guard; a country-year living entirely on carried values is refused)
 * - delta(y1,y2) is computed on components available at BOTH dates whose UNDERLYING
 *   OBSERVATION DIFFERS (obs_year = year - age); REFUSED when C is empty or the
 *   common-weight share is below delta_min_common_weight (0.50)
 * - decomposition terms are additive: w_c * (n2 - n1) / sum_C(w)
 */

export interface ScoreCompSeries {
  key: string;
  weight: number;
  /** yearStr -> resolved normalised value (fresh or carried), 0..100. */
  normalised: Record<string, number>;
  /** SPARSE yearStr -> age (absent = fresh, age 0). */
  age: Record<string, number>;
}

export function roundTo(x: number, decimals: number): number {
  const f = 10 ** decimals;
  return Math.round(x * f) / f;
}

export function ageOf(comp: ScoreCompSeries, year: number): number {
  return comp.age[String(year)] ?? 0;
}

/** obs_year = year - age: the real observation the (possibly carried) value rests on. */
export function obsYearOf(comp: ScoreCompSeries, year: number): number {
  return year - ageOf(comp, year);
}

export interface ScoreAtYear {
  /** Rounded score (2 decimals) — display value. */
  score: number;
  /** Unrounded weighted mean. */
  raw: number;
  /** Rounded coverage 0..1 (4 decimals), matching the stored convention. */
  coverage: number;
  /** Components with a resolved value at that year. */
  n: number;
  /** Fresh (age 0) components among the available ones. */
  nFresh: number;
  /** Ghost guard + threshold: whether a score is emitted for this point. */
  emitted: boolean;
}

export function scoreAtYear(
  comps: ScoreCompSeries[],
  year: number,
  opts: { coverageThreshold: number },
): ScoreAtYear | null {
  let sumAll = 0;
  let sumAvail = 0;
  let weighted = 0;
  let n = 0;
  let nFresh = 0;
  for (const c of comps) {
    if (c.weight <= 0) continue; // outside the preset's metric set (v30: Todd-only presets)
    sumAll += c.weight;
    const v = c.normalised[String(year)];
    if (v === undefined) continue;
    n++;
    sumAvail += c.weight;
    weighted += c.weight * v;
    if (ageOf(c, year) === 0) nFresh++;
  }
  if (n === 0 || sumAll === 0) return null;
  const coverage = sumAvail / sumAll;
  const raw = weighted / sumAvail;
  return {
    score: roundTo(raw, 2),
    raw,
    coverage: roundTo(coverage, 4),
    n,
    nFresh,
    emitted: coverage >= opts.coverageThreshold && nFresh >= 1,
  };
}

export interface DeltaTerm {
  key: string;
  /** Additive contribution: w_c * (n2 - n1) / sum_C(w), rounded to 4 decimals. */
  term: number;
  weight: number;
  n1: number;
  n2: number;
  obs1: number;
  obs2: number;
}

export interface DeltaResult {
  refused: boolean;
  reason: "no_common_components" | "common_weight_below_threshold" | null;
  /** Rounded delta (2 decimals) — display value; null when refused. */
  delta: number | null;
  n_components: number;
  /** Rounded 4 decimals — the common-weight share over the score's full weight. */
  common_weight_share: number;
  /** Additive decomposition, sorted by |term| desc. */
  decomposition: DeltaTerm[];
}

export function deltaBetweenYears(
  comps: ScoreCompSeries[],
  y1: number,
  y2: number,
  opts: { minCommonWeight: number },
): DeltaResult {
  let sumAll = 0;
  let sumCommon = 0;
  let weightedDelta = 0;
  const decomposition: DeltaTerm[] = [];

  for (const c of comps) {
    if (c.weight <= 0) continue; // outside the preset's metric set (v30: Todd-only presets)
    sumAll += c.weight;
    const v1 = c.normalised[String(y1)];
    const v2 = c.normalised[String(y2)];
    if (v1 === undefined || v2 === undefined) continue;
    const obs1 = obsYearOf(c, y1);
    const obs2 = obsYearOf(c, y2);
    if (obs1 === obs2) continue; // same underlying observation — excluded (v28)
    sumCommon += c.weight;
    weightedDelta += c.weight * (v2 - v1);
    decomposition.push({
      key: c.key,
      weight: c.weight,
      n1: v1,
      n2: v2,
      obs1,
      obs2,
      term: 0, // filled after sumCommon is known
    });
  }

  if (decomposition.length === 0) {
    return {
      refused: true,
      reason: "no_common_components",
      delta: null,
      n_components: 0,
      common_weight_share: 0,
      decomposition: [],
    };
  }

  for (const term of decomposition) {
    term.term = roundTo((term.weight * (term.n2 - term.n1)) / sumCommon, 4);
  }
  decomposition.sort((a, b) => Math.abs(b.term) - Math.abs(a.term));

  const share = roundTo(sumCommon / sumAll, 4);
  if (share < opts.minCommonWeight) {
    return {
      refused: true,
      reason: "common_weight_below_threshold",
      delta: null,
      n_components: decomposition.length,
      common_weight_share: share,
      decomposition,
    };
  }

  return {
    refused: false,
    reason: null,
    delta: roundTo(weightedDelta / sumCommon, 2),
    n_components: decomposition.length,
    common_weight_share: share,
    decomposition,
  };
}
