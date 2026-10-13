import { NextResponse } from "next/server";
import { buildYearPayload } from "@/lib/toddlab/server/queries";
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
  const year = parseInt(url.searchParams.get("year") ?? "", 10);
  const sexParam = url.searchParams.get("sex") ?? "all";
  const sex =
    sexParam === "male" || sexParam === "female" ? sexParam : ("all" as const);
  const byYear = url.searchParams.get("mode") === "by_year";
  if (!Number.isFinite(year)) {
    return NextResponse.json({ error: "invalid_year" }, { status: 400 });
  }
  const payload = buildYearPayload(id, year, sex, byYear);
  if (!payload) {
    return NextResponse.json({ error: "not_found", id }, { status: 404 });
  }
  return NextResponse.json(payload);
}
