"use client";

import { useQuery, type UseQueryResult } from "@tanstack/react-query";

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { error?: string };
    const err = new Error(body.error ?? `HTTP ${res.status}`) as Error & {
      status?: number;
    };
    err.status = res.status;
    throw err;
  }
  return res.json() as Promise<T>;
}

export interface CatalogItem {
  id: string;
  label: string;
  family: string;
  unit: string;
  higher_is_better: boolean;
  todd_core: boolean;
  canonical_nature: "published" | "modelled";
  companion_indicators: string[];
  reliability: "high" | "medium" | "low";
  reliability_criteria: string;
  reclassification_sensitive: boolean;
  license: string;
  roots: {
    canonical: { root: string; label: string; doors: number }[];
    witness: { root: string; label: string; doors: number }[];
  };
  n_points: number;
  n_witness_points: number;
  todd_refs?: {
    family: string;
    citations: number;
    books: number;
    refs: {
      book: string;
      year: number;
      year_raw?: string;
      citations: number;
      label: string;
      note: string;
    }[];
  };
  available: boolean;
}

export interface CatalogPayload {
  meta: {
    vintage: string;
    n_indicators_available: number;
    n_indicators_total: number;
    n_entities: number;
    n_canonical_points: number;
    n_witness_points: number;
    corpus: {
      rows: number;
      metrics: number;
      books: number;
      total_citations: number;
      implemented_metrics: number;
    };
  };
  indicators: CatalogItem[];
}

export interface EntityItem {
  entity_id: string;
  label: string;
  iso3: string | null;
  valid_from: number | null;
  valid_to: number | null;
  predecessor: string | null;
  successors: string[];
  formerly_part_of: {
    union_entity_id: string;
    until_year: number;
    note: string;
  } | null;
  n_indicators_with_data: number;
}

export interface CorpusPayload {
  meta: CatalogPayload["meta"];
  corpus: {
    source: string;
    meta: CatalogPayload["meta"]["corpus"] & { source_csv_sha256: string };
    metrics: {
      id: string;
      family: string;
      citations: number;
      books: number;
      refs: {
        book: string;
        year: number;
        year_raw?: string;
        citations: number;
        label: string;
        note: string;
      }[];
    }[];
  };
}

export interface IndicatorMetaPayload {
  id: string;
  label: string;
  family: string;
  unit: string;
  higher_is_better: boolean;
  todd_core: boolean;
  canonical_nature: "published" | "modelled";
  companion_indicators: string[];
  reliability: "high" | "medium" | "low";
  reliability_criteria: string;
  reclassification_sensitive: boolean;
  coverage_declared: { start: number; end: number };
  license: string;
  notes: string;
  todd_refs: {
    family: string;
    citations: number;
    books: number;
    refs: {
      book: string;
      year: number;
      year_raw?: string;
      citations: number;
      label: string;
      note: string;
    }[];
  } | null;
  sources: {
    provider: string;
    source_ref: string;
    role: "canonical" | "witness";
    layer: "curated" | "collector" | "harmonized";
    root: string;
    root_label: string;
    native_unit: string | null;
    citation: string;
    url: string | null;
    license: string;
  }[];
  sex_split: boolean;
  available_years: number[];
  /** Sensible default year (latest well-covered year; latest event year for unit "year"). */
  default_year: number | null;
}

export interface SeriesPoint {
  entity_id: string;
  year: number;
  value: number | null;
  sex?: "male" | "female";
  provider: string;
  source_ref: string;
  citation?: string;
}

export interface WitnessBlock {
  key: string;
  provider: string;
  source_ref: string;
  root: string;
  root_label: string;
  layer: string;
  citation: string;
  points: {
    entity_id: string;
    year: number;
    value: number | null;
    sex?: "male" | "female";
  }[];
}

export interface SeriesPayload {
  id: string;
  label: string;
  family: string;
  unit: string;
  higher_is_better: boolean;
  todd_core: boolean;
  canonical_nature: "published" | "modelled";
  reliability: "high" | "medium" | "low";
  reliability_criteria: string;
  sex_split: boolean;
  available_years: number[];
  coverage_declared: { start: number; end: number };
  canonical: SeriesPoint[];
  witnesses: WitnessBlock[];
}

export interface YearPayload {
  id: string;
  year: number;
  sex: "all" | "male" | "female";
  higher_is_better: boolean;
  unit: string;
  points: {
    entity_id: string;
    value: number | null;
    provider: string;
    source_ref: string;
    sex?: "male" | "female";
  }[];
  witness_points: {
    key: string;
    root_label: string;
    points: { entity_id: string; value: number | null }[];
  }[];
}

export interface CountryProfile {
  entity: EntityItem;
  indicators: {
    id: string;
    label: string;
    family: string;
    unit: string;
    higher_is_better: boolean;
    todd_core: boolean;
    canonical_nature: "published" | "modelled";
    reliability: "high" | "medium" | "low";
    sex_split: boolean;
    last_year: number | null;
    last_value: number | null;
    last_sex: "male" | "female" | null;
    n_points: number;
    series: { year: number; value: number }[];
    sex_series?: {
      male: { year: number; value: number }[];
      female: { year: number; value: number }[];
    };
    rank: number | null;
    n_ranked: number | null;
    rank_basis: "canonical" | "witness" | null;
    witness_root_label?: string;
  }[];
}

/* --------------------------------- Hooks --------------------------------- */

export function useCatalog(): UseQueryResult<CatalogPayload> {
  return useQuery({
    queryKey: ["catalog"],
    queryFn: () => fetchJson<CatalogPayload>("/api/catalog"),
    staleTime: 10 * 60 * 1000,
  });
}

export function useEntities(): UseQueryResult<{ entities: EntityItem[] }> {
  return useQuery({
    queryKey: ["entities"],
    queryFn: () => fetchJson<{ entities: EntityItem[] }>("/api/entities"),
    staleTime: 10 * 60 * 1000,
  });
}

export function useCorpus(): UseQueryResult<CorpusPayload> {
  return useQuery({
    queryKey: ["corpus"],
    queryFn: () => fetchJson<CorpusPayload>("/api/corpus"),
    staleTime: 10 * 60 * 1000,
  });
}

export function useIndicatorMeta(
  id: string | null,
): UseQueryResult<IndicatorMetaPayload> {
  return useQuery({
    queryKey: ["indicator-meta", id],
    queryFn: () => fetchJson<IndicatorMetaPayload>(`/api/indicators/${id}/meta`),
    enabled: !!id,
    staleTime: 10 * 60 * 1000,
    retry: (count, err) => {
      const status = (err as Error & { status?: number }).status;
      if (status === 404 || status === 503) return false;
      return count < 2;
    },
  });
}

export function useSeries(
  id: string | null,
  countries: string[],
): UseQueryResult<SeriesPayload> {
  const key = [...countries].sort().join(",");
  return useQuery({
    queryKey: ["series", id, key],
    queryFn: () =>
      fetchJson<SeriesPayload>(
        `/api/indicators/${id}/series?countries=${encodeURIComponent(key)}`,
      ),
    enabled: !!id && countries.length > 0,
    staleTime: 10 * 60 * 1000,
    retry: (count, err) => {
      const status = (err as Error & { status?: number }).status;
      if (status === 404 || status === 503) return false;
      return count < 2;
    },
  });
}

export function useYearData(
  id: string | null,
  year: number | null,
  sex: "all" | "male" | "female",
  opts?: { byYear?: boolean },
): UseQueryResult<YearPayload> {
  const byYear = opts?.byYear === true;
  return useQuery({
    queryKey: ["year", id, year, sex, byYear],
    queryFn: () =>
      fetchJson<YearPayload>(
        `/api/indicators/${id}/year?year=${year}&sex=${sex}${
          byYear ? "&mode=by_year" : ""
        }`,
      ),
    enabled: !!id && year !== null,
    staleTime: 10 * 60 * 1000,
    retry: (count, err) => {
      const status = (err as Error & { status?: number }).status;
      if (status === 404 || status === 503) return false;
      return count < 2;
    },
  });
}

export function useCountryProfile(
  id: string | null,
): UseQueryResult<CountryProfile> {
  return useQuery({
    queryKey: ["country", id],
    queryFn: () => fetchJson<CountryProfile>(`/api/countries/${id}`),
    enabled: !!id,
    staleTime: 10 * 60 * 1000,
  });
}

/* ------------------------------ Score layer ------------------------------ */

export interface ScoreMetaPayload {
  version: string;
  derived: true;
  notice: string;
  carry_rule: string;
  bounds_version: string;
  global: {
    bounds_from_year: number;
    percentiles: number[];
    coverage_threshold: number;
    delta_min_common_weight: number;
    fertility_target: number;
    max_age_years: number;
    bounds_drift_tolerance: number;
    rounding: number;
    presets: string[];
  };
  max_obs_year: Record<string, number>;
  components: Record<
    string,
    {
      indicator: string;
      sex: "both" | "male" | "female";
      sex_mode: "both" | "split";
      direction: "higher" | "lower" | "target";
      transform: "linear" | "log" | "target";
      basis: "todd" | "consensus";
      corpus_metric: string | null;
      scores: string[];
    }
  >;
  presets: Record<string, Record<string, Record<string, number>>>;
  excluded: Record<string, string>;
}

export interface ScoreEntityComponent {
  key: string;
  indicator: string;
  sex: "both" | "male" | "female";
  label_en: string;
  weight_equal: number;
  weight_todd: number;
  normalised: Record<string, number>;
  age: Record<string, number>;
  meta: {
    source: string | string[];
    source_class: "canonical" | "modelled";
    layer: string;
    root: string | string[];
    root_label: string | string[];
    transform: "linear" | "log" | "target";
    direction: "higher" | "lower" | "target";
    basis: "todd" | "consensus";
    floor: number | null;
    lo: number;
    hi: number;
    n_sample: number;
    n_entities: number;
    n_points: number;
    bounds_version: string;
    year_min: number;
    year_max: number;
  };
}

export interface ScoreEntitySide {
  years: number[];
  max_obs_year: number;
  bounds_version: string;
  presets: Record<"equal" | "todd", Record<string, [number, number]>>;
  components: ScoreEntityComponent[];
  carried_share: number | null;
}

export interface ScoreEntity {
  entity_id: string;
  official: ScoreEntitySide | null;
  modelled: ScoreEntitySide | null;
}

export interface ScoreRankingRow {
  entity_id: string;
  score: number;
  coverage: number;
  n_components: number;
}

export interface ScoreRankings {
  year: number;
  years: Record<string, number[]>;
  default_year: Record<string, number>;
  max_obs_year: Record<string, number>;
  rankings: Record<string, Record<"equal" | "todd", ScoreRankingRow[]>>;
}

export function useScoreMeta(): UseQueryResult<ScoreMetaPayload> {
  return useQuery({
    queryKey: ["score-meta"],
    queryFn: () => fetchJson<ScoreMetaPayload>("/api/score/meta"),
    staleTime: 10 * 60 * 1000,
    retry: (count, err) => {
      const status = (err as Error & { status?: number }).status;
      if (status === 503) return false;
      return count < 2;
    },
  });
}

export function useScoreEntity(
  id: string | null,
): UseQueryResult<ScoreEntity> {
  return useQuery({
    queryKey: ["score-entity", id],
    queryFn: () => fetchJson<ScoreEntity>(`/api/score/entity/${id}`),
    enabled: !!id,
    staleTime: 10 * 60 * 1000,
    retry: (count, err) => {
      const status = (err as Error & { status?: number }).status;
      if (status === 404 || status === 503) return false;
      return count < 2;
    },
  });
}

export function useScoreRankings(
  year: number | null,
): UseQueryResult<ScoreRankings> {
  return useQuery({
    queryKey: ["score-rankings", year],
    queryFn: () =>
      fetchJson<ScoreRankings>(
        year !== null ? `/api/score/rankings?year=${year}` : "/api/score/rankings",
      ),
    staleTime: 10 * 60 * 1000,
    retry: (count, err) => {
      const status = (err as Error & { status?: number }).status;
      if (status === 503) return false;
      return count < 2;
    },
  });
}

/* --------------------------- Score comparison ---------------------------- */

export interface ScoreComparePoint {
  year: number;
  score: number;
  coverage: number;
}

export interface ScoreCompareEntity {
  entity_id: string;
  points: ScoreComparePoint[];
}

export interface ScoreComparePayload {
  score: "official" | "modelled";
  preset: "equal" | "todd";
  entities: ScoreCompareEntity[];
}

/**
 * Per-year emitted scores for up to two entities, straight from the stored
 * preset tables (no client-side recomputation). Response entities keep the
 * requested order so line colors match the picker chips.
 */
export function useScoreCompare(
  ids: string[],
  score: "official" | "modelled",
  preset: "equal" | "todd",
): UseQueryResult<ScoreComparePayload> {
  const key = ids.join(",");
  return useQuery({
    queryKey: ["score-compare", key, score, preset],
    queryFn: () =>
      fetchJson<ScoreComparePayload>(
        `/api/score/compare?ids=${encodeURIComponent(key)}&score=${score}&preset=${preset}`,
      ),
    enabled: key.length > 0,
    staleTime: 10 * 60 * 1000,
    retry: (count, err) => {
      const status = (err as Error & { status?: number }).status;
      if (status === 503) return false;
      return count < 2;
    },
  });
}
