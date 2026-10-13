import "server-only";
import type { ScoreFile, ScoreMeta, ScoreName } from "./score-types";
import { distFileExists, readDistJson } from "./server/dist";

/**
 * Server-side store for the score layer (data/dist/score/).
 * Derived product, backend V29 — contract: docs/score-contract.md.
 * Read in place from the backend payload (see server/dist.ts), same pattern as store.ts.
 */

function readJson<T>(relPath: string): T {
  return readDistJson<T>(`score/${relPath}`);
}

export function scoreLayerExists(): boolean {
  return distFileExists("score/meta.json");
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
