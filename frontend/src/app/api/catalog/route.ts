import { NextResponse } from "next/server";
import { buildCatalogPayload } from "@/lib/toddlab/server/queries";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json(buildCatalogPayload());
}
