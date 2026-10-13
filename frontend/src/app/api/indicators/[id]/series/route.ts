import { NextResponse } from "next/server";
import { buildSeriesPayload } from "@/lib/toddlab/server/queries";
import { UNAVAILABLE_INDICATORS } from "@/lib/toddlab/store";

export const dynamic = "force-dynamic";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (UNAVAILABLE_INDICATORS.has(id)) {
    return NextResponse.json({ error: "unavailable", id }, { status: 503 });
  }
  const url = new URL(req.url);
  const countriesParam = url.searchParams.get("countries") ?? "";
  const countries = countriesParam
    .split(",")
    .map((s) => s.trim())
    .filter((s) => /^[a-z0-9_]+$/.test(s))
    .slice(0, 32);
  const payload = buildSeriesPayload(id, countries);
  if (!payload) {
    return NextResponse.json(
      { error: UNAVAILABLE_INDICATORS.has(id) ? "unavailable" : "not_found", id },
      { status: UNAVAILABLE_INDICATORS.has(id) ? 503 : 404 },
    );
  }
  return NextResponse.json(payload);
}
