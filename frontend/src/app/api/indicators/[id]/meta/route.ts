import { NextResponse } from "next/server";
import { getAvailableYears, getDefaultYear, getIndicatorFile, isSexSplit } from "@/lib/toddlab/store";
import { UNAVAILABLE_INDICATORS } from "@/lib/toddlab/store";

export const dynamic = "force-dynamic";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const file = getIndicatorFile(id);
  if (!file) {
    const unavailable = UNAVAILABLE_INDICATORS.has(id);
    return NextResponse.json(
      { error: unavailable ? "unavailable" : "not_found", id },
      { status: unavailable ? 503 : 404 },
    );
  }
  return NextResponse.json({
    id: file.id,
    label: file.label,
    family: file.family,
    unit: file.unit,
    higher_is_better: file.higher_is_better,
    todd_core: file.todd_core,
    canonical_nature: file.canonical_nature,
    companion_indicators: file.companion_indicators,
    reliability: file.reliability,
    reliability_criteria: file.reliability_criteria,
    reclassification_sensitive: file.reclassification_sensitive,
    coverage_declared: file.coverage_declared,
    license: file.license,
    notes: file.notes,
    todd_refs: file.todd_refs ?? null,
    sources: file.sources,
    sex_split: isSexSplit(file),
    available_years: getAvailableYears(id),
    default_year: getDefaultYear(id),
  });
}
