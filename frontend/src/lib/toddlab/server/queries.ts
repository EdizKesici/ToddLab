import "server-only";
import {
  getAvailableYears,
  getCatalog,
  getCatalogMeta,
  getCorpus,
  getEntities,
  getIndicatorFile,
  indicatorFileExists,
  isSexSplit,
} from "../store";
import type {
  CatalogEntry,
  CountryProfilePayload,
  SeriesPayload,
  YearPayload,
} from "../types";

/* --------------------------------- Catalog --------------------------------- */

export interface CatalogItem extends CatalogEntry {
  available: boolean;
}

export function buildCatalogPayload(): {
  meta: ReturnType<typeof getCatalogMeta>;
  indicators: CatalogItem[];
} {
  const catalog = getCatalog();
  const indicators: CatalogItem[] = catalog
    .map((c) => ({ ...c, available: indicatorFileExists(c.id) }))
    .sort((a, b) => a.label.localeCompare(b.label));
  return { meta: getCatalogMeta(), indicators };
}

/* ------------------------------- Entities list ------------------------------ */

let entitiesIndexCache: {
  entities: (import("../types").DistEntity & { n_indicators_with_data: number })[];
} | null = null;

export function buildEntitiesPayload() {
  if (entitiesIndexCache) return entitiesIndexCache;
  const entities = getEntities();
  const catalog = getCatalog().filter((c) => indicatorFileExists(c.id));
  const counts = new Map<string, number>();
  for (const c of catalog) {
    const file = getIndicatorFile(c.id);
    if (!file) continue;
    const seen = new Set<string>();
    for (const p of file.data) {
      if (p.value !== null && !seen.has(p.entity_id)) {
        seen.add(p.entity_id);
        counts.set(p.entity_id, (counts.get(p.entity_id) ?? 0) + 1);
      }
    }
  }
  entitiesIndexCache = {
    entities: entities.map((e) => ({
      ...e,
      n_indicators_with_data: counts.get(e.entity_id) ?? 0,
    })),
  };
  return entitiesIndexCache;
}

/* ------------------------------- Series payload ----------------------------- */

export function buildSeriesPayload(
  id: string,
  countryIds: string[],
): SeriesPayload | null {
  const file = getIndicatorFile(id);
  if (!file) return null;
  const wanted = new Set(countryIds);
  const canonical = file.data
    .filter((p) => wanted.has(p.entity_id))
    .map((p) => ({
      entity_id: p.entity_id,
      year: p.year,
      value: p.value,
      sex: p.sex,
      provider: p.provider,
      source_ref: p.source_ref,
      citation: p.citation,
    }));
  const witnesses = file.witnesses
    .map((w, i) => ({
      key: `${w.provider}:${w.source_ref}:${i}`,
      provider: w.provider,
      source_ref: w.source_ref,
      root: w.root,
      root_label: w.root_label,
      layer: w.layer,
      citation: w.citation,
      points: w.data.filter((p) => wanted.has(p.entity_id)),
    }))
    .filter((w) => w.points.length > 0);
  const years = new Set<number>();
  for (const p of canonical) years.add(p.year);
  for (const w of witnesses) for (const p of w.points) years.add(p.year);
  return {
    id: file.id,
    label: file.label,
    family: file.family,
    unit: file.unit,
    higher_is_better: file.higher_is_better,
    todd_core: file.todd_core,
    canonical_nature: file.canonical_nature,
    reliability: file.reliability,
    reliability_criteria: file.reliability_criteria,
    sex_split: isSexSplit(file),
    available_years: [...years].sort((a, b) => a - b),
    coverage_declared: file.coverage_declared,
    canonical,
    witnesses,
  };
}

/* -------------------------------- Year payload ------------------------------ */

/**
 * One reference year, or — for event-year indicators (unit "year", where the
 * value IS the year of the event) — every event that had occurred by that
 * year (`byYear: true`, value ≤ year). Never mixes the two semantics.
 */
export function buildYearPayload(
  id: string,
  year: number,
  sex: "all" | "male" | "female",
  byYear = false,
): YearPayload | null {
  const file = getIndicatorFile(id);
  if (!file) return null;
  const matchSex = (p: { sex?: "male" | "female" }) =>
    sex === "all" ? p.sex === undefined : p.sex === sex;
  const matchYear = (p: { year: number; value: number | null }) =>
    byYear
      ? p.value !== null && (p.value as number) <= year
      : p.year === year;

  const points = file.data
    .filter((p) => matchYear(p) && matchSex(p))
    .map((p) => ({
      entity_id: p.entity_id,
      value: p.value,
      provider: p.provider,
      source_ref: p.source_ref,
      sex: p.sex,
    }));
  const witness_points = file.witnesses
    .map((w, i) => ({
      key: `${w.provider}:${w.source_ref}:${i}`,
      root_label: w.root_label,
      points: w.data
        .filter((p) => p.year === year && matchSex(p))
        .map((p) => ({ entity_id: p.entity_id, value: p.value })),
    }))
    .filter((w) => w.points.length > 0);

  return {
    id: file.id,
    year,
    sex,
    higher_is_better: file.higher_is_better,
    unit: file.unit,
    points,
    witness_points,
  };
}

/* ----------------------------- Country profile ------------------------------ */

interface BasicPoint {
  year: number;
  value: number | null;
  sex?: "male" | "female";
}

function toSeries(points: BasicPoint[]) {
  return points
    .filter((p) => p.value !== null)
    .map((p) => ({ year: p.year, value: p.value as number }))
    .sort((a, b) => a.year - b.year);
}

function rankOf(
  entityId: string,
  year: number,
  sex: "all" | "male" | "female",
  higherIsBetter: boolean,
  allPoints: (BasicPoint & { entity_id: string })[],
): { rank: number | null; n: number } {
  const peers = allPoints.filter(
    (p) =>
      p.year === year &&
      p.value !== null &&
      (sex === "all" ? p.sex === undefined : p.sex === sex),
  );
  if (peers.length === 0) return { rank: null, n: 0 };
  const me = peers.find((p) => p.entity_id === entityId);
  if (!me || me.value === null) return { rank: null, n: peers.length };
  const mine = me.value;
  let better = 0;
  for (const p of peers) {
    if (higherIsBetter ? (p.value as number) > mine : (p.value as number) < mine)
      better++;
  }
  return { rank: better + 1, n: peers.length };
}

export function buildCountryProfile(
  entityId: string,
): CountryProfilePayload | null {
  const entity = getEntities().find((e) => e.entity_id === entityId);
  if (!entity) return null;
  const catalog = getCatalog().filter((c) => indicatorFileExists(c.id));

  const indicators = catalog.map((entry) => {
    const file = getIndicatorFile(entry.id);
    if (!file) {
      return {
        id: entry.id,
        label: entry.label,
        family: entry.family,
        unit: entry.unit,
        higher_is_better: entry.higher_is_better,
        todd_core: entry.todd_core,
        canonical_nature: entry.canonical_nature,
        reliability: entry.reliability,
        sex_split: false,
        last_year: null,
        last_value: null,
        last_sex: null,
        n_points: 0,
        series: [],
        rank: null,
        n_ranked: null,
        rank_basis: null,
      };
    }
    const mine = file.data.filter((p) => p.entity_id === entityId);
    const valued = mine.filter((p) => p.value !== null);
    const split = valued.some((p) => p.sex !== undefined);
    const plain = valued.filter((p) => p.sex === undefined);

    let last_year: number | null = null;
    let last_value: number | null = null;
    let last_sex: "male" | "female" | null = null;
    let series: { year: number; value: number | null }[] = [];
    let sex_series:
      | {
          male: { year: number; value: number | null }[];
          female: { year: number; value: number | null }[];
        }
      | undefined;
    let rank: number | null = null;
    let n_ranked: number | null = null;
    let rank_basis: "canonical" | "witness" | null = null;
    let witness_root_label: string | undefined;

    if (plain.length > 0) {
      const s = toSeries(plain);
      series = s;
      last_year = s[s.length - 1]?.year ?? null;
      last_value = s[s.length - 1]?.value ?? null;
      if (last_year !== null) {
        const r = rankOf(entityId, last_year, "all", file.higher_is_better, file.data);
        rank = r.rank;
        n_ranked = r.n;
        rank_basis = "canonical";
      }
    } else if (split) {
      const males = toSeries(valued.filter((p) => p.sex === "male"));
      const females = toSeries(valued.filter((p) => p.sex === "female"));
      sex_series = { male: males, female: females };
      const lastM = males[males.length - 1];
      const lastF = females[females.length - 1];
      const years = [lastM?.year, lastF?.year].filter(
        (y): y is number => typeof y === "number",
      );
      const year = years.length > 0 ? Math.max(...years) : null;
      last_year = year;
      if (year !== null) {
        const pickSex: "male" | "female" = lastM?.year === year ? "male" : "female";
        const pick = pickSex === "male" ? lastM : lastF;
        last_value = pick?.value ?? null;
        last_sex = pickSex;
        const r = rankOf(entityId, year, pickSex, file.higher_is_better, file.data);
        rank = r.rank;
        n_ranked = r.n;
        rank_basis = "canonical";
      }
    }

    // Witness fallback when no canonical series at all
    if (last_year === null) {
      for (const w of file.witnesses) {
        const wp = w.data.filter(
          (p) => p.entity_id === entityId && p.value !== null,
        );
        const plainW = wp.filter((p) => p.sex === undefined);
        const use = plainW.length > 0 ? plainW : wp;
        if (use.length === 0) continue;
        const s = toSeries(use);
        if (s.length === 0) continue;
        const last = s[s.length - 1];
        last_year = last.year;
        last_value = last.value;
        series = s;
        let peers = w.data.filter(
          (p) => p.year === last.year && p.value !== null && p.sex === undefined,
        );
        if (peers.length === 0)
          peers = w.data.filter((p) => p.year === last.year && p.value !== null);
        let better = 0;
        for (const p of peers) {
          if (
            p.value !== null &&
            (file.higher_is_better
              ? p.value > (last.value as number)
              : p.value < (last.value as number))
          )
            better++;
        }
        rank = better + 1;
        n_ranked = peers.length;
        rank_basis = "witness";
        witness_root_label = w.root_label;
        break;
      }
    }

    return {
      id: entry.id,
      label: entry.label,
      family: entry.family,
      unit: entry.unit,
      higher_is_better: entry.higher_is_better,
      todd_core: entry.todd_core,
      canonical_nature: entry.canonical_nature,
      reliability: entry.reliability,
      sex_split: split,
      last_year,
      last_value,
      last_sex,
      n_points: valued.length,
      series,
      sex_series,
      rank,
      n_ranked,
      rank_basis,
      witness_root_label,
    };
  });

  return { entity, indicators };
}

/* ---------------------------------- Corpus ---------------------------------- */

export function buildCorpusPayload() {
  return { meta: getCatalogMeta(), corpus: getCorpus() };
}
