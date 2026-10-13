import "server-only";
import fs from "fs";
import path from "path";

/**
 * Reader for the backend's published payload (<repo>/data/dist).
 *
 * The frontend has no copy of the data: it reads the backend's files in
 * place. Parsed files are cached per process and keyed by the file's
 * modification time, so a new backend build is picked up on the next
 * request without restarting the server.
 *
 * Location, in order:
 *   1. TODDLAB_DIST_DIR (explicit override);
 *   2. the nearest `data/dist/catalog.json` found walking up from the
 *      working directory, ignoring anything under `.next` (the standalone
 *      build would otherwise find a stale build-time copy).
 */

function findDistDir(): string {
  const fromEnv = process.env.TODDLAB_DIST_DIR;
  if (fromEnv) return path.resolve(fromEnv);

  let dir = process.cwd();
  for (;;) {
    const candidate = path.join(dir, "data", "dist");
    if (
      !candidate.split(path.sep).includes(".next") &&
      fs.existsSync(path.join(candidate, "catalog.json"))
    ) {
      return candidate;
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  throw new Error(
    "ToddLab data/dist not found. Run from the repository (frontend/) " +
      "or set TODDLAB_DIST_DIR to the backend's data/dist directory.",
  );
}

let distDir: string | null = null;

export function getDistDir(): string {
  if (!distDir) distDir = findDistDir();
  return distDir;
}

const cache = new Map<string, { mtimeMs: number; value: unknown }>();

/** Read and parse a JSON file under data/dist (cached until it changes). */
export function readDistJson<T>(relPath: string): T {
  const abs = path.join(getDistDir(), relPath);
  const { mtimeMs } = fs.statSync(abs);
  const hit = cache.get(relPath);
  if (hit && hit.mtimeMs === mtimeMs) return hit.value as T;
  const value = JSON.parse(fs.readFileSync(abs, "utf8")) as T;
  cache.set(relPath, { mtimeMs, value });
  return value;
}

export function distFileExists(relPath: string): boolean {
  return fs.existsSync(path.join(getDistDir(), relPath));
}
