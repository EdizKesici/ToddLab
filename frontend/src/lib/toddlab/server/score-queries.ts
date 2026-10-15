import "server-only";
import { getCatalog } from "../store";
import { getScoreFile, getScoreMeta } from "../score-store";
import { deltaBetweenYears, unitWeightOf, type ScoreCompSeries } from "../score-core";
import {
  STORED_PRESETS,
  type ScoreCompareYear,
  type ScoreMoverRow,
  type ScoreMoversPayload,
  type StoredPreset,
  type ScoreEntityComponent,
  type ScoreEntityPayload,
  type ScoreEntitySide,
  type ScoreMeta,
  type ScoreName,
  type ScoreRankingsPayload,
  type ScoreRankingRow,
} from "../score-types";

/**
 * Payload builders for the score layer (server-filtered slices of
 * data/dist/score/). The backend pre-computes the presets; the frontend
 * renders them and applies CUSTOM weights client-side (docs/score-contract.md).
 */

const SCORES: ScoreName[] = ["official", "modelled"];
const PRESETS = STORED_PRESETS;

function emptyPresetTable(): Record<(typeof STORED_PRESETS)[number], ScoreRankingRow[]> {
  return { equal: [], todd: [], equal_todd_only: [], todd_todd_only: [] };
}

const catalogLabels = new Map<string, string>();
function catalogLabel(indicatorId: string): string {
  if (catalogLabels.size === 0) {
    for (const c of getCatalog()) catalogLabels.set(c.id, c.label);
  }
  return catalogLabels.get(indicatorId) ?? indicatorId;
}

function buildSide(
  score: ScoreName,
  entityId: string,
  meta: ScoreMeta,
): ScoreEntitySide | null {
  const file = getScoreFile(score);
  // meta.presets[score][preset] = { componentKey -> weight }
  const presetWeights = meta.presets[score];
  const compKeys = Object.keys(presetWeights.equal);

  const presets = {} as ScoreEntitySide["presets"];
  for (const preset of PRESETS) presets[preset] = {};
  for (const preset of PRESETS) {
    presets[preset] = file.scores[preset][entityId] ?? {};
  }

  const scoredYears = new Set<string>();
  for (const preset of PRESETS) {
    for (const year of Object.keys(presets[preset])) scoredYears.add(year);
  }

  const components: ScoreEntityComponent[] = [];
  let resolvedCount = 0;
  let carriedCount = 0;

  for (const key of compKeys) {
    // NOTE: include EVERY component of the score, even ones this entity has no
    // data for — the coverage denominator is the score's FULL weight (contract:
    // sum(w_c all components of the score)). Empty comps contribute 0 to the
    // numerator and their weight to the denominator.
    const norm = file.normalised[key]?.[entityId] ?? {};
    const block = file.components[key];
    if (!block) continue;
    const compMeta = meta.components[key];
    const ageMap = file.age[key]?.[entityId] ?? {};
    const age: Record<string, number> = {};
    for (const [y, a] of Object.entries(ageMap)) {
      if (norm[y] !== undefined) age[y] = a;
    }
    if (Object.keys(norm).length > 0) {
      resolvedCount += Object.keys(norm).length;
      carriedCount += Object.values(age).length;
    }
    components.push({
      key,
      indicator: compMeta?.indicator ?? key.split("/")[0],
      sex: compMeta?.sex ?? "both",
      label_en: catalogLabel(compMeta?.indicator ?? key.split("/")[0]),
      weight_equal: presetWeights.equal[key] ?? 0,
      weight_todd: presetWeights.todd[key] ?? 0,
      corpus_set: block.corpus_set ?? "todd",
      normalised: norm,
      age,
      meta: block,
    });
  }

  // A side exists only if the entity is actually scored at least one year.
  // (Entities with stray normalised values but no emitted score — e.g. the
  // USSR — fall back to the not-scored card.)
  if (scoredYears.size === 0) return null;

  return {
    years: [...scoredYears]
      .map((y) => Number(y))
      .filter((y) => Number.isFinite(y))
      .sort((a, b) => a - b),
    max_obs_year: meta.max_obs_year[score],
    bounds_version: meta.bounds_version,
    presets,
    components,
    carried_share: resolvedCount > 0 ? carriedCount / resolvedCount : null,
  };
}

export function buildScoreEntityPayload(entityId: string): ScoreEntityPayload | null {
  if (!/^[a-z][a-z0-9_]*$/.test(entityId)) return null;
  const meta = getScoreMeta();
  const official = buildSide("official", entityId, meta);
  const modelled = buildSide("modelled", entityId, meta);
  if (!official && !modelled) return null;
  return { entity_id: entityId, official, modelled };
}

function scoredYearsOf(score: ScoreName): number[] {
  const file = getScoreFile(score);
  const years = new Set<number>();
  for (const rows of Object.values(file.scores.equal)) {
    for (const y of Object.keys(rows)) years.add(Number(y));
  }
  return [...years].sort((a, b) => a - b);
}

/** Components with a resolved value at that year AMONG THE ONES THE PRESET WEIGHTS (weight 0 = outside the metric set). */
function nComponentsAt(
  score: ScoreName,
  entityId: string,
  yearStr: string,
  weights: Record<string, number>,
): number {
  const file = getScoreFile(score);
  let n = 0;
  for (const key of Object.keys(file.normalised)) {
    if ((weights[key] ?? 0) <= 0) continue;
    const v = file.normalised[key][entityId]?.[yearStr];
    if (v !== undefined) n++;
  }
  return n;
}

function defaultYearFor(score: ScoreName): number {
  const file = getScoreFile(score);
  const counts = new Map<string, number>();
  for (const rows of Object.values(file.scores.equal)) {
    for (const y of Object.keys(rows)) counts.set(y, (counts.get(y) ?? 0) + 1);
  }
  const eligible = [...counts.entries()]
    .filter(([, n]) => n >= 20)
    .map(([y]) => Number(y));
  if (eligible.length > 0) return Math.max(...eligible);
  const lenient = [...counts.entries()]
    .filter(([, n]) => n >= 10)
    .map(([y]) => Number(y));
  if (lenient.length > 0) return Math.max(...lenient);
  return getScoreMeta().max_obs_year[score];
}

export function buildScoreRankingsPayload(
  yearInput: number | null,
): ScoreRankingsPayload | null {
  const meta = getScoreMeta();
  const rankings: ScoreRankingsPayload["rankings"] = {
    official: emptyPresetTable(),
    modelled: emptyPresetTable(),
  };

  // Absent or invalid year: fall back to the official score's default year
  // (the client corrects itself once it reads `years` / `default_year`).
  let year = yearInput;
  if (year === null || !Number.isInteger(year) || year < 1900 || year > 2100) {
    year = defaultYearFor("official");
  }

  for (const score of SCORES) {
    const file = getScoreFile(score);
    for (const preset of PRESETS) {
      const rows: ScoreRankingRow[] = [];
      const table = file.scores[preset];
      for (const [entityId, years] of Object.entries(table)) {
        const entry = year !== null ? years[String(year)] : undefined;
        if (!entry) continue;
        rows.push({
          entity_id: entityId,
          score: entry[0],
          coverage: entry[1],
          n_components: nComponentsAt(score, entityId, String(year), meta.presets[score][preset] ?? {}),
        });
      }
      rows.sort((a, b) => b.score - a.score || a.entity_id.localeCompare(b.entity_id));
      rankings[score][preset] = rows;
    }
  }

  return {
    year: year ?? 0,
    years: { official: scoredYearsOf("official"), modelled: scoredYearsOf("modelled") },
    default_year: { official: defaultYearFor("official"), modelled: defaultYearFor("modelled") },
    max_obs_year: meta.max_obs_year,
    rankings,
  };
}

/**
 * Per-year comparability of a country comparison. For each year where at least
 * two of the selected countries have an emitted score: the weight of the
 * components resolved for ALL of them over the weight of those resolved for ANY
 * of them. Below delta_min_common_weight (the contract's own threshold for a
 * delta) the gap compares different components and is flagged as not
 * comparable. Read from the stored normalised values: no recomputation.
 */
export function buildCompareComparability(
  ids: string[],
  score: ScoreName,
  preset: StoredPreset,
): { years: ScoreCompareYear[]; min_common_weight: number } {
  const meta = getScoreMeta();
  const file = getScoreFile(score);
  const weights = meta.presets[score][preset] ?? {};
  const keys = Object.keys(weights).filter((k) => weights[k] > 0);
  const table = file.scores[preset];
  const minCommon = meta.global.delta_min_common_weight;

  const yearSet = new Set<string>();
  for (const id of ids) for (const y of Object.keys(table[id] ?? {})) yearSet.add(y);

  const out: ScoreCompareYear[] = [];
  for (const y of [...yearSet].sort()) {
    const scored = ids.filter((id) => table[id]?.[y] !== undefined);
    if (scored.length < 2) continue;
    let wCommon = 0;
    let wAny = 0;
    for (const k of keys) {
      const present = scored.filter((id) => file.normalised[k]?.[id]?.[y] !== undefined).length;
      // components are COUNTED (decision 28), whatever the preset's weights
      if (present > 0) wAny += unitWeightOf(k);
      if (present === scored.length) wCommon += unitWeightOf(k);
    }
    const share = wAny > 0 ? wCommon / wAny : 0;
    out.push({
      year: Number(y),
      n_entities: scored.length,
      common_share: Math.round(share * 10000) / 10000,
      comparable: share >= minCommon,
    });
  }
  return { years: out, min_common_weight: minCommon };
}

/**
 * Best and worst score movers between two years. The ranking metric is the
 * contract's DELTA (docs/score-contract.md): the weighted change over the
 * components resolved from a different observation in both years, refused when
 * they carry less than delta_min_common_weight of the weight. Only countries
 * with an emitted score in BOTH years are ranked, so both endpoints are real.
 */
export function buildScoreMoversPayload(
  score: ScoreName,
  preset: StoredPreset,
  fromInput: number | null,
  toInput: number | null,
): ScoreMoversPayload {
  const meta = getScoreMeta();
  const file = getScoreFile(score);
  const weights = meta.presets[score][preset] ?? {};
  const years = scoredYearsOf(score);
  const defTo = defaultYearFor(score);
  const to = toInput !== null && years.includes(toInput) ? toInput : defTo;
  const defFrom = years.filter((y) => y <= to - 10).pop() ?? years[0] ?? to;
  let from = fromInput !== null && years.includes(fromInput) ? fromInput : defFrom;
  if (from >= to) from = years.filter((y) => y < to).pop() ?? from;

  const table = file.scores[preset];
  const rows: ScoreMoverRow[] = [];
  let nBoth = 0;
  let nRefused = 0;
  for (const [entityId, scored] of Object.entries(table)) {
    const a = scored[String(from)];
    const b = scored[String(to)];
    if (!a || !b) continue;
    nBoth++;
    const comps: ScoreCompSeries[] = Object.keys(weights).map((k) => ({
      key: k,
      weight: weights[k],
      normalised: file.normalised[k]?.[entityId] ?? {},
      age: file.age[k]?.[entityId] ?? {},
    }));
    const d = deltaBetweenYears(comps, from, to, { minCommonWeight: meta.global.delta_min_common_weight });
    if (d.refused || d.delta === null) {
      nRefused++;
      continue;
    }
    rows.push({
      entity_id: entityId,
      delta: d.delta,
      score_from: a[0],
      score_to: b[0],
      n_components: d.n_components,
      common_weight_share: d.common_weight_share,
    });
  }
  rows.sort((x, y) => y.delta - x.delta || x.entity_id.localeCompare(y.entity_id));
  return {
    score,
    preset,
    from,
    to,
    years,
    rows,
    n_refused: nRefused,
    n_scored_both: nBoth,
    min_common_weight: meta.global.delta_min_common_weight,
  };
}

export function getScoreLayerMeta(): ScoreMeta {
  return getScoreMeta();
}
