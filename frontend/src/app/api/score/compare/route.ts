import { NextResponse } from "next/server";
import { getScoreFile, scoreLayerExists } from "@/lib/toddlab/score-store";
import { isStoredPreset, type ScoreName } from "@/lib/toddlab/score-types";

export const dynamic = "force-dynamic";

const ENTITY_RE = /^[a-z][a-z0-9_]*$/;

/**
 * GET /api/score/compare?ids=FR,DE&score=official&preset=equal
 *   (preset: equal | todd | equal_todd_only | todd_todd_only)
 *
 * Per-year emitted scores ([score, coverage]) for up to four entities, read
 * straight from the stored preset tables (data/dist/score/{score}.json).
 * No recomputation: the comparison uses exactly the same numbers as the
 * rankings table. Entities keep the requested order so client line colors
 * match the picker chips.
 */
export async function GET(req: Request) {
  if (!scoreLayerExists()) {
    return NextResponse.json({ error: "score_layer_unavailable" }, { status: 503 });
  }
  const sp = new URL(req.url).searchParams;

  const idsRaw = sp.get("ids") ?? "";
  const ids = [...new Set(idsRaw.split(",").map((s) => s.trim()).filter((s) => ENTITY_RE.test(s)))].slice(0, 4);

  const score: ScoreName = sp.get("score") === "modelled" ? "modelled" : "official";
  const presetRaw = sp.get("preset");
  const preset = isStoredPreset(presetRaw) ? presetRaw : ("equal" as const);

  const file = getScoreFile(score);
  const table = file.scores[preset];

  const entities = ids.map((id) => {
    const years = table[id] ?? {};
    const points = Object.entries(years)
      .map(([y, entry]) => ({ year: Number(y), score: entry[0], coverage: entry[1] }))
      .filter((p) => Number.isInteger(p.year))
      .sort((a, b) => a.year - b.year);
    return { entity_id: id, points };
  });

  return NextResponse.json({ score, preset, entities });
}
