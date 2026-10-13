import { NextResponse } from "next/server";
import { buildCountryProfile } from "@/lib/toddlab/server/queries";

export const dynamic = "force-dynamic";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  if (!/^[a-z0-9_]+$/.test(id)) {
    return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  }
  const payload = buildCountryProfile(id);
  if (!payload) {
    return NextResponse.json({ error: "not_found", id }, { status: 404 });
  }
  return NextResponse.json(payload);
}
