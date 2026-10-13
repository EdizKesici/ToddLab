import { NextResponse } from "next/server";
import { buildEntitiesPayload } from "@/lib/toddlab/server/queries";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json(buildEntitiesPayload());
}
