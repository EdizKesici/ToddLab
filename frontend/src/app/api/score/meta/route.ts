import { NextResponse } from "next/server";
import { getScoreMeta, scoreLayerExists } from "@/lib/toddlab/score-store";

export const dynamic = "force-dynamic";

export async function GET() {
  if (!scoreLayerExists()) {
    return NextResponse.json({ error: "score_layer_unavailable" }, { status: 503 });
  }
  return NextResponse.json(getScoreMeta());
}
