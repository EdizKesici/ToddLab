/**
 * ToddLab data contract — mirrors data/dist/ exactly (backend V29).
 * Source of truth: github.com/EdizKesici/ToddLab
 *
 * Key contract facts:
 * - catalog.json and entities.json are ROOT ARRAYS; todd_corpus.json is an OBJECT.
 * - Canonical points carry provider/source_ref; witness points inherit them from their series.
 * - value can be null (explicit gap points — gaps are data, never interpolated).
 * - Annotation keys on points are conditional (only present when carried by the source).
 * - bilateral / bilateral_citizenship / segments / segments_citizenship are additive keys
 *   (present only when the layer has points). Not used in V1 (immigration_stock file is
 *   gitignored upstream / not shipped).
 */

export type Sex = "male" | "female";

export type Family =
  | "mortality"
  | "society"
  | "economy"
  | "education"
  | "demography"
  | "markers"
  | "anthropometry_health";

export type Layer = "curated" | "collector" | "harmonized";

export type Provider =
  | "owid"
  | "worldbank"
  | "who_gho"
  | "un_dyb"
  | "curated"
  | "oecd"
  | "eurostat"
  | "ilostat"
  | "unesco_uis";

export type Reliability = "high" | "medium" | "low";

/* ---------------------------------- Catalog ---------------------------------- */

export interface RootSummary {
  root: string;
  label: string;
  doors: number;
}

export interface ToddRefsBlock {
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
}

export interface CatalogEntry {
  id: string;
  label: string;
  family: Family;
  unit: string;
  higher_is_better: boolean;
  todd_core: boolean;
  canonical_nature: "published" | "modelled";
  companion_indicators: string[];
  reliability: Reliability;
  reliability_criteria: string;
  reclassification_sensitive: boolean;
  license: string;
  roots: { canonical: RootSummary[]; witness: RootSummary[] };
  n_points: number;
  n_witness_points: number;
  todd_refs?: ToddRefsBlock;
}

/* ---------------------------------- Entities ---------------------------------- */

export interface FormerUnionMembership {
  union_entity_id: string;
  until_year: number;
  note: string;
}

export interface DistEntity {
  entity_id: string;
  label: string;
  iso3: string | null;
  valid_from: number | null;
  valid_to: number | null;
  predecessor: string | null;
  successors: string[];
  formerly_part_of: FormerUnionMembership | null;
}

/* ---------------------------------- Corpus ---------------------------------- */

export interface ToddCorpus {
  source: string;
  meta: {
    source_csv_sha256: string;
    rows: number;
    metrics: number;
    books: number;
    total_citations: number;
    implemented_metrics: number;
  };
  metrics: (ToddRefsBlock & { id: string })[];
}

/* ---------------------------------- Indicator files ---------------------------------- */

export interface SourceBlock {
  provider: Provider;
  source_ref: string;
  role: "canonical" | "witness";
  layer: Layer;
  root: string;
  root_label: string;
  native_unit: string | null;
  citation: string;
  url: string | null;
  license: string;
  footnotes?: {
    legend: Record<string, string>;
    notes: Record<string, string | null>;
  };
}

/** Canonical point. value === null is an explicit gap point (printed missingness). */
export interface CanonicalPoint {
  entity_id: string;
  year: number;
  value: number | null;
  provider: Provider;
  source_ref: string;
  citation?: string;
  definition_note?: string;
  sex?: Sex;
  quality_code?: string;
  footnote_refs?: string[];
  reference_range?: string;
  missing_marker?: string;
  provisional?: boolean;
  small_base?: boolean;
}

/** Witness point — provider/source_ref inherited from the parent series. */
export interface WitnessPoint {
  entity_id: string;
  year: number;
  value: number | null;
  sex?: Sex;
  quality_code?: string;
  provisional?: boolean;
  missing_marker?: string;
}

export interface WitnessSeries {
  provider: Provider;
  source_ref: string;
  layer: Layer;
  root: string;
  root_label: string;
  unit: string;
  native_unit: string | null;
  citation: string;
  url: string | null;
  license: string;
  n_points: number;
  data: WitnessPoint[];
}

export interface IndicatorFile {
  id: string;
  label: string;
  family: Family;
  unit: string;
  higher_is_better: boolean;
  todd_core: boolean;
  canonical_nature: "published" | "modelled";
  companion_indicators: string[];
  reliability: Reliability;
  reliability_criteria: string;
  reclassification_sensitive: boolean;
  coverage_declared: { start: number; end: number };
  license: string;
  notes: string;
  sources: SourceBlock[];
  data: CanonicalPoint[];
  witnesses: WitnessSeries[];
  bilateral?: unknown;
  bilateral_citizenship?: unknown;
  segments?: unknown;
  segments_citizenship?: unknown;
  todd_refs?: ToddRefsBlock;
}

/* ---------------------------------- API payloads (frontend-specific) ---------------------------------- */

export interface CatalogMeta {
  vintage: string;
  n_indicators_available: number;
  n_indicators_total: number;
  n_entities: number;
  n_canonical_points: number;
  n_witness_points: number;
  corpus: ToddCorpus["meta"];
}

export interface StatsPayload {
  meta: CatalogMeta;
}

export interface SeriesPayload {
  id: string;
  label: string;
  family: Family;
  unit: string;
  higher_is_better: boolean;
  todd_core: boolean;
  canonical_nature: "published" | "modelled";
  reliability: Reliability;
  reliability_criteria: string;
  sex_split: boolean;
  available_years: number[];
  coverage_declared: { start: number; end: number };
  canonical: CompactPoint[];
  witnesses: {
    key: string;
    provider: Provider;
    source_ref: string;
    root: string;
    root_label: string;
    layer: Layer;
    citation: string;
    points: WitnessPoint[];
  }[];
  unavailable?: boolean;
}

/** Compact canonical point over the wire (filtered per request). */
export interface CompactPoint {
  entity_id: string;
  year: number;
  value: number | null;
  sex?: Sex;
  provider: Provider;
  source_ref: string;
  citation?: string;
}

export interface YearPayload {
  id: string;
  year: number;
  sex: Sex | "all";
  higher_is_better: boolean;
  unit: string;
  points: {
    entity_id: string;
    value: number | null;
    provider: Provider;
    source_ref: string;
  }[];
  witness_points: {
    key: string;
    root_label: string;
    points: { entity_id: string; value: number | null }[];
  }[];
}

export interface CountryProfilePayload {
  entity: DistEntity;
  indicators: {
    id: string;
    label: string;
    family: Family;
    unit: string;
    higher_is_better: boolean;
    todd_core: boolean;
    canonical_nature: "published" | "modelled";
    reliability: Reliability;
    sex_split: boolean;
    last_year: number | null;
    last_value: number | null;
    last_sex: Sex | null;
    n_points: number;
    series: { year: number; value: number | null }[];
    sex_series?: {
      male: { year: number; value: number | null }[];
      female: { year: number; value: number | null }[];
    };
    rank: number | null;
    n_ranked: number | null;
    rank_basis: "canonical" | "witness" | null;
    witness_root_label?: string;
  }[];
}
