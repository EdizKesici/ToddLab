/**
 * ToddLab score layer — types mirroring data/dist/score/ (backend V29).
 * Contract: docs/score-contract.md in the backend repo (ADR-0011).
 *
 * The score is a DERIVED product: weighted arithmetic means of normalised
 * values (0-100) on a frozen absolute scale. Two scores, never merged:
 * official (canonical tier) and modelled (widest-coverage single source).
 */

export type ScoreName = "official" | "modelled";
export type ScorePreset = "equal" | "todd" | "custom";

/** Which metrics enter the score: Todd's books plus the extra metrics, or Todd's books only. */
export type ScoreScope = "all" | "todd";

/** The presets the backend stores (v30): a weighting x a metric set. */
export type StoredPreset = "equal" | "todd" | "equal_todd_only" | "todd_todd_only";
export const STORED_PRESETS: readonly StoredPreset[] = [
  "equal",
  "todd",
  "equal_todd_only",
  "todd_todd_only",
];

export function storedPreset(weighting: "equal" | "todd", scope: ScoreScope): StoredPreset {
  return scope === "todd" ? (`${weighting}_todd_only` as StoredPreset) : weighting;
}

export function isStoredPreset(x: string | null): x is StoredPreset {
  return x !== null && (STORED_PRESETS as readonly string[]).includes(x);
}

/** meta.json — the layer's contract card. */
export interface ScoreMeta {
  version: string;
  derived: true;
  notice: string;
  carry_rule: string;
  bounds_version: string;
  global: {
    bounds_from_year: number;
    percentiles: [number, number];
    coverage_threshold: number;
    delta_min_common_weight: number;
    fertility_target: number;
    max_age_years: number;
    bounds_drift_tolerance: number;
    rounding: number;
    presets: string[];
  };
  max_obs_year: Record<ScoreName, number>;
  components: Record<
    string,
    {
      indicator: string;
      sex: "both" | "male" | "female";
      sex_mode: "both" | "split";
      direction: "higher" | "lower" | "target";
      transform: "linear" | "log" | "target";
      basis: "todd" | "consensus";
      provisional: false;
      corpus_metric: string | null;
      scores: ScoreName[];
    }
  >;
  presets: Record<
    ScoreName,
    Record<StoredPreset, Record<string, number>>
  >;
  excluded: Record<string, string>;
  fingerprints: Record<string, unknown>;
}

/** One component block inside official.json / modelled.json. */
export interface ScoreComponentBlock {
  source: string | string[];
  source_class: "canonical" | "modelled";
  layer: string;
  root: string | string[];
  root_label: string | string[];
  transform: "linear" | "log" | "target";
  direction: "higher" | "lower" | "target";
  basis: "todd" | "consensus";
  provisional: false;
  /** v30: in Todd's books ("todd") or in the extra metric set ("extra"). */
  corpus_set: "todd" | "extra";
  floor: number | null;
  lo: number;
  hi: number;
  n_sample: number;
  n_entities: number;
  n_points: number;
  bounds_version: string;
  year_min: number;
  year_max: number;
}

/** Full dist file (server-side shape). */
export interface ScoreFile {
  components: Record<string, ScoreComponentBlock>;
  /** component key -> entity_id -> yearStr -> normalised value (resolved: fresh or carried). */
  normalised: Record<string, Record<string, Record<string, number>>>;
  /** SPARSE: present only where age >= 1. Absent = fresh (age 0). */
  age: Record<string, Record<string, Record<string, number>>>;
  /** preset -> entity_id -> yearStr -> [score, coverage] — emitted only where
   *  coverage >= threshold AND at least one fresh component (ghost guard). */
  scores: Record<StoredPreset, Record<string, Record<string, [number, number]>>>;
}

/* ------------------------------ API payloads ------------------------------ */

/** Per-component slice for one entity (server-filtered). */
export interface ScoreEntityComponent {
  key: string;
  indicator: string;
  sex: "both" | "male" | "female";
  /** English label from the catalog (client maps to FR via i18n). */
  label_en: string;
  weight_equal: number;
  weight_todd: number;
  /** Whether the metric is in Todd's books ("todd") or in the extra set ("extra"). */
  corpus_set: "todd" | "extra";
  normalised: Record<string, number>;
  age: Record<string, number>;
  meta: ScoreComponentBlock;
}

export interface ScoreEntitySide {
  years: number[];
  max_obs_year: number;
  bounds_version: string;
  /** Stored preset scores: preset -> yearStr -> [score, coverage]. */
  presets: Record<StoredPreset, Record<string, [number, number]>>;
  components: ScoreEntityComponent[];
  /** Share of resolved values with age >= 1 among scored years (displayed, not hidden). */
  carried_share: number | null;
}

export interface ScoreEntityPayload {
  entity_id: string;
  official: ScoreEntitySide | null;
  modelled: ScoreEntitySide | null;
}

export interface ScoreRankingRow {
  entity_id: string;
  score: number;
  coverage: number;
  /** Number of components with a resolved value at that year (preset-independent). */
  n_components: number;
}

export interface ScoreRankingsPayload {
  year: number;
  years: Record<ScoreName, number[]>;
  default_year: Record<ScoreName, number>;
  max_obs_year: Record<ScoreName, number>;
  rankings: Record<ScoreName, Record<StoredPreset, ScoreRankingRow[]>>;
}
