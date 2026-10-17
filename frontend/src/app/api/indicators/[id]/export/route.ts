import { NextResponse } from "next/server";
import { siteUrl } from "@/lib/site-url";
import { getEntities, getIndicatorFile, UNAVAILABLE_INDICATORS } from "@/lib/toddlab/store";
import { buildCsv, csvResponse, today } from "@/lib/toddlab/server/csv";

export const dynamic = "force-dynamic";

/**
 * GET /api/indicators/{id}/export
 *
 * Every non-gap point of the indicator, canonical and witness tiers in one
 * long table (column `tier`), read straight from the published payload: no
 * recomputation. The `#` header carries the provenance, the licence of each
 * source and the citation, which the sources' licences require.
 */
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

  const names = new Map(getEntities().map((e) => [e.entity_id, e]));
  const rows: (string | number | boolean | null | undefined)[][] = [];
  let nCanonical = 0;
  let nWitness = 0;

  for (const p of file.data) {
    if (p.value === null) continue;
    const e = names.get(p.entity_id);
    rows.push([
      file.id, p.entity_id, e?.label ?? p.entity_id, e?.iso3 ?? "", p.year, p.value, file.unit,
      p.sex ?? "", "canonical", p.provider, p.source_ref, p.quality_code ?? "",
      p.provisional ? "true" : "", p.definition_note ?? "",
    ]);
    nCanonical++;
  }
  for (const w of file.witnesses) {
    for (const p of w.data) {
      if (p.value === null) continue;
      const e = names.get(p.entity_id);
      rows.push([
        file.id, p.entity_id, e?.label ?? p.entity_id, e?.iso3 ?? "", p.year, p.value, w.unit,
        p.sex ?? "", "witness", w.provider, w.source_ref, p.quality_code ?? "",
        p.provisional ? "true" : "", "",
      ]);
      nWitness++;
    }
  }
  rows.sort(
    (a, b) =>
      String(a[8]).localeCompare(String(b[8])) ||
      String(a[1]).localeCompare(String(b[1])) ||
      Number(a[4]) - Number(b[4]) ||
      String(a[7]).localeCompare(String(b[7])),
  );

  const comments = [
    `ToddLab export: ${file.label} (${file.id})`,
    `Exported ${today()} from ${siteUrl()}/indicators/${file.id}`,
    `Unit: ${file.unit}. Nature: ${file.canonical_nature === "modelled" ? "estimate (the source recalculates or models the figure)" : "official (published by statistical services, collected as reported)"}. Reliability: ${file.reliability}.`,
    `Rows: ${nCanonical} canonical + ${nWitness} witness. Gap points (no value) are omitted. Tiers are never merged: filter on the "tier" column.`,
    `Definition: ${file.reliability_criteria}`,
    ...file.sources.flatMap((s) => [
      `Source (${s.role}): ${s.citation}${s.url ? ` <${s.url}>` : ""}`,
      `Licence of that source: ${s.license}`,
    ]),
    `Attribution is required by the sources' licences: cite the sources above and ToddLab (${siteUrl()}). Licence details: https://github.com/EdizKesici/ToddLab/blob/main/docs/licenses.md`,
  ];
  const header = [
    "indicator_id", "country_id", "country", "iso3", "year", "value", "unit", "sex", "tier",
    "provider", "source_ref", "quality_code", "provisional", "definition_note",
  ];
  return csvResponse(buildCsv(comments, header, rows), `toddlab_${file.id}.csv`);
}
