import "server-only";
import { getCatalog } from "../store";
import { getScoreFile, getScoreMeta } from "../score-store";
import type {
  ScoreEntityComponent,
  ScoreEntityPayload,
  ScoreEntitySide,
  ScoreMeta,
  ScoreName,
  ScoreRankingsPayload,
  ScoreRankingRow,
} from "../score-types";

/**
 * Payload builders for the score layer (server-filtered slices of
 * data/dist/score/). The backend pre-computes the presets; the frontend
 * renders them and applies CUSTOM weights client-side (docs/score-contract.md).
 */

const SCORES: ScoreName[] = ["official", "modelled"];
const PRESETS = ["equal", "todd"] as const;

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

  const presets: ScoreEntitySide["presets"] = {
    equal: {},
    todd: {},
  };
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

function nComponentsAt(score: ScoreName, entityId: string, yearStr: string): number {
  const file = getScoreFile(score);
  let n = 0;
  for (const key of Object.keys(file.normalised)) {
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
    official: { equal: [], todd: [] },
    modelled: { equal: [], todd: [] },
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
          n_components: nComponentsAt(score, entityId, String(year)),
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

export function getScoreLayerMeta(): ScoreMeta {
  return getScoreMeta();
}
