import { NextResponse } from "next/server";
import { scoreLayerExists } from "@/lib/toddlab/score-store";
import { buildScoreEntityPayload } from "@/lib/toddlab/server/score-queries";

export const dynamic = "force-dynamic";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (!/^[a-z0-9_]+$/.test(id)) {
    return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  }
  if (!scoreLayerExists()) {
    return NextResponse.json({ error: "score_layer_unavailable" }, { status: 503 });
  }
  const payload = buildScoreEntityPayload(id);
  if (!payload) {
    return NextResponse.json({ error: "not_found", id }, { status: 404 });
  }
  return NextResponse.json(payload);
}
