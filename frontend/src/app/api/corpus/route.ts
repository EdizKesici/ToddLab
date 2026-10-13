import { NextResponse } from "next/server";
import { buildCorpusPayload } from "@/lib/toddlab/server/queries";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json(buildCorpusPayload());
}
