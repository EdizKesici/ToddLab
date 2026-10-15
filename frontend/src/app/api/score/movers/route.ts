import { NextResponse } from "next/server";
import { scoreLayerExists } from "@/lib/toddlab/score-store";
import { isStoredPreset, type ScoreName } from "@/lib/toddlab/score-types";
import { buildScoreMoversPayload } from "@/lib/toddlab/server/score-queries";

export const dynamic = "force-dynamic";

function intOrNull(raw: string | null): number | null {
  if (raw === null) return null;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) ? n : null;
}

/**
 * GET /api/score/movers?score=official&preset=equal&from=2005&to=2019
 *
 * Every country scored in both years, ranked by the contract's delta (the
 * change over the components they share), best improvement first. The client
 * slices the best and the worst ends.
 */
export async function GET(req: Request) {
  if (!scoreLayerExists()) {
    return NextResponse.json({ error: "score_layer_unavailable" }, { status: 503 });
  }
  const sp = new URL(req.url).searchParams;
  const score: ScoreName = sp.get("score") === "modelled" ? "modelled" : "official";
  const presetRaw = sp.get("preset");
  const preset = isStoredPreset(presetRaw) ? presetRaw : ("equal" as const);
  return NextResponse.json(
    buildScoreMoversPayload(score, preset, intOrNull(sp.get("from")), intOrNull(sp.get("to"))),
  );
}
