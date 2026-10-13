import { NextResponse } from "next/server";
import { scoreLayerExists } from "@/lib/toddlab/score-store";
import { buildScoreRankingsPayload } from "@/lib/toddlab/server/score-queries";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  if (!scoreLayerExists()) {
    return NextResponse.json({ error: "score_layer_unavailable" }, { status: 503 });
  }
  const yearRaw = new URL(req.url).searchParams.get("year");
  const year = yearRaw === null ? null : Number.parseInt(yearRaw, 10);
  const payload = buildScoreRankingsPayload(Number.isFinite(year) ? year : null);
  if (!payload) {
    return NextResponse.json({ error: "score_layer_unavailable" }, { status: 503 });
  }
  return NextResponse.json(payload);
}
