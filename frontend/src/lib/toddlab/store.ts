import "server-only";
import type {
  CatalogEntry,
  DistEntity,
  IndicatorFile,
  ToddCorpus,
} from "./types";
import { distFileExists, readDistJson } from "./server/dist";

/**
 * Server-side data store for the backend's dist files (<repo>/data/dist).
 * Files are read in place (see server/dist.ts): parsed once per process and
 * re-read automatically when the backend rebuilds them.
 * Total dist is ~53 MB — an all-files-warm footprint is acceptable for a small server.
 */

function readJson<T>(relPath: string): T {
  return readDistJson<T>(relPath);
}

/* ------------------------------- Core artifacts ------------------------------- */

export function getCatalog(): CatalogEntry[] {
  return readJson<CatalogEntry[]>("catalog.json");
}

export function getEntities(): DistEntity[] {
  return readJson<DistEntity[]>("entities.json");
}

export function getCorpus(): ToddCorpus {
  return readJson<ToddCorpus>("todd_corpus.json");
}

/** Indicators withdrawn upstream (V26 retraction) or gitignored — never served. */
export const UNAVAILABLE_INDICATORS = new Set<string>(["immigration_stock"]);

export function indicatorFileExists(id: string): boolean {
  if (UNAVAILABLE_INDICATORS.has(id)) return false;
  return distFileExists(`indicators/${id}.json`);
}

export function getIndicatorFile(id: string): IndicatorFile | null {
  if (UNAVAILABLE_INDICATORS.has(id)) return null;
  if (!/^[a-z][a-z0-9_]*$/.test(id)) return null; // path-traversal guard
  try {
    return readJson<IndicatorFile>(`indicators/${id}.json`);
  } catch {
    return null;
  }
}

/* --------------------------------- Derived ---------------------------------- */

export interface CatalogMeta {
  vintage: string;
  n_indicators_available: number;
  n_indicators_total: number;
  n_entities: number;
  n_canonical_points: number;
  n_witness_points: number;
  corpus: ToddCorpus["meta"];
}

/** Data vintage, read from the payload itself (the score layer's frozen bounds version). */
function readVintage(): string {
  try {
    const meta = readDistJson<{ bounds_version?: string }>("score/meta.json");
    return meta.bounds_version ? `score bounds ${meta.bounds_version}` : "unknown";
  } catch {
    return "unknown";
  }
}

export function getCatalogMeta(): CatalogMeta {
  const catalog = getCatalog();
  const available = catalog.filter((c) => indicatorFileExists(c.id));
  return {
    vintage: readVintage(),
    n_indicators_available: available.length,
    n_indicators_total: catalog.length,
    n_entities: getEntities().length,
    n_canonical_points: available.reduce((acc, c) => acc + c.n_points, 0),
    n_witness_points: available.reduce((acc, c) => acc + c.n_witness_points, 0),
    corpus: getCorpus().meta,
  };
}

/** Sorted available years (canonical ∪ witness) for an indicator. */
export function getAvailableYears(id: string): number[] {
  const file = getIndicatorFile(id);
  if (!file) return [];
  const years = new Set<number>();
  for (const p of file.data) years.add(p.year);
  for (const w of file.witnesses) for (const p of w.data) years.add(p.year);
  return [...years].sort((a, b) => a - b);
}

/**
 * Sensible default year for an indicator detail page.
 * - Event-year indicators (unit "year": value = the year of the event) → the
 *   latest event year; the map/ranking then show every past event at once.
 * - Otherwise → the latest year whose canonical coverage reaches at least
 *   half of the best-covered year (min 8 countries), so the default view is
 *   never a near-empty snapshot (e.g. road mortality in the current year).
 */
export function getDefaultYear(id: string): number | null {
  const file = getIndicatorFile(id);
  if (!file) return null;
  const counts = new Map<number, number>();
  for (const p of file.data) {
    if (p.value !== null) counts.set(p.year, (counts.get(p.year) ?? 0) + 1);
  }
  if (counts.size === 0) return null;
  if (file.unit === "year") {
    return Math.max(...counts.keys());
  }
  const max = Math.max(...counts.values());
  const threshold = Math.max(8, Math.ceil(max / 2));
  const eligible = [...counts.entries()]
    .filter(([, n]) => n >= threshold)
    .map(([y]) => y);
  return eligible.length > 0 ? Math.max(...eligible) : Math.max(...counts.keys());
}

export function isSexSplit(file: IndicatorFile): boolean {
  return file.data.some((p) => p.sex !== undefined) ||
    file.witnesses.some((w) => w.data.some((p) => p.sex !== undefined));
}

export function entitiesWithCanonicalData(id: string): Set<string> {
  const file = getIndicatorFile(id);
  const out = new Set<string>();
  if (!file) return out;
  for (const p of file.data) if (p.value !== null) out.add(p.entity_id);
  return out;
}
