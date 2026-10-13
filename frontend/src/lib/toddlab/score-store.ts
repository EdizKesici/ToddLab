import "server-only";
import fs from "fs";
import path from "path";
import type { ScoreFile, ScoreMeta, ScoreName } from "./score-types";

/**
 * Server-side store for the score layer (data/dist/score/).
 * Derived product, backend V29 — contract: docs/score-contract.md.
 * Files are read once per process (module-level cache), same pattern as store.ts.
 */

const SCORE_DIR = path.join(process.cwd(), "data", "dist", "score");

const jsonCache = new Map<string, unknown>();

function readJson<T>(relPath: string): T {
  const key = relPath;
  if (jsonCache.has(key)) return jsonCache.get(key) as T;
  const parsed = JSON.parse(
    fs.readFileSync(path.join(SCORE_DIR, relPath), "utf8"),
  ) as T;
  jsonCache.set(key, parsed);
  return parsed;
}

export function scoreLayerExists(): boolean {
  return fs.existsSync(path.join(SCORE_DIR, "meta.json"));
}

export function getScoreMeta(): ScoreMeta {
  return readJson<ScoreMeta>("meta.json");
}

export function getScoreFile(score: ScoreName): ScoreFile {
  if (!/^(official|modelled)$/.test(score)) {
    throw new Error(`Unknown score: ${score}`);
  }
  return readJson<ScoreFile>(`${score}.json`);
}

/** Golden vectors (backend-emitted verification cases — used for self-checks). */
export function getScoreGoldenVectors(): unknown {
  return readJson<unknown>("golden_vectors.json");
}
