import { NextResponse } from "next/server";
import { getCatalogMeta } from "@/lib/toddlab/store";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({ meta: getCatalogMeta() });
}
