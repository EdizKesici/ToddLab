import { NextResponse } from "next/server";
import { siteUrl } from "@/lib/site-url";
import { getScoreFile, scoreLayerExists } from "@/lib/toddlab/score-store";
import { isStoredPreset, type ScoreName } from "@/lib/toddlab/score-types";
import { buildScoreRankingsPayload, getScoreLayerMeta } from "@/lib/toddlab/server/score-queries";
import { buildCsv, csvResponse, today } from "@/lib/toddlab/server/csv";
import { getEntities } from "@/lib/toddlab/store";

export const dynamic = "force-dynamic";

const ENTITY_RE = /^[a-z][a-z0-9_]*$/;

/**
 * GET /api/score/export?score=official&preset=equal&year=2019   -> the ranking of that year
 * GET /api/score/export?score=official&preset=equal&entity=france -> one country's score by year
 *
 * Stored values only (no recomputation). The score is a DERIVED product: the
 * header says so, with the scale version, the coverage threshold and the carry rule.
 */
export async function GET(req: Request) {
  if (!scoreLayerExists()) {
    return NextResponse.json({ error: "score_layer_unavailable" }, { status: 503 });
  }
  const sp = new URL(req.url).searchParams;
  const score: ScoreName = sp.get("score") === "modelled" ? "modelled" : "official";
  const presetRaw = sp.get("preset");
  const preset = isStoredPreset(presetRaw) ? presetRaw : ("equal" as const);
  const meta = getScoreLayerMeta();
  const names = new Map(getEntities().map((e) => [e.entity_id, e]));

  const common = [
    `ToddLab civilizational score, ${score} (derived product, not a measurement), preset "${preset}"`,
    `Exported ${today()} from ${siteUrl()}/score`,
    `Scale: frozen absolute scale ${meta.bounds_version}. A score exists only where at least ${Math.round(meta.global.coverage_threshold * 100)}% of the components are available (coverage) and one is fresh. Carry rule: ${meta.carry_rule}`,
    `Preset: equal = every indicator weighs the same; todd = weights follow Emmanuel Todd's books; *_todd_only = only the metrics Todd uses. Official and modelled scores are separate calculations, never merged.`,
    `Data licences: https://github.com/EdizKesici/ToddLab/blob/main/docs/licenses.md. Cite ToddLab (${siteUrl()}) and the underlying sources.`,
  ];

  const entity = sp.get("entity");
  if (entity !== null) {
    if (!ENTITY_RE.test(entity) || !names.has(entity)) {
      return NextResponse.json({ error: "not_found", entity }, { status: 404 });
    }
    const years = getScoreFile(score).scores[preset][entity] ?? {};
    const e = names.get(entity)!;
    const rows = Object.entries(years)
      .map(([y, v]) => [entity, e.label, e.iso3 ?? "", Number(y), score, preset, v[0], v[1]] as const)
      .sort((a, b) => a[3] - b[3])
      .map((r) => [...r]);
    return csvResponse(
      buildCsv(
        [...common, `Country: ${e.label}. Years without a row are years the score refuses (coverage below the threshold or no fresh component).`],
        ["country_id", "country", "iso3", "year", "score_type", "preset", "score", "coverage"],
        rows,
      ),
      `toddlab_score_${score}_${preset}_${entity}.csv`,
    );
  }

  const yearRaw = Number.parseInt(sp.get("year") ?? "", 10);
  const payload = buildScoreRankingsPayload(Number.isFinite(yearRaw) ? yearRaw : null);
  if (!payload) return NextResponse.json({ error: "score_layer_unavailable" }, { status: 503 });
  const list = payload.rankings[score][preset];
  const rows = list.map((r, i) => {
    const e = names.get(r.entity_id);
    return [i + 1, r.entity_id, e?.label ?? r.entity_id, e?.iso3 ?? "", payload.year, score, preset, r.score, r.coverage, r.n_components];
  });
  return csvResponse(
    buildCsv(
      [...common, `Ranking of ${payload.year}: ${list.length} countries, best first.`],
      ["rank", "country_id", "country", "iso3", "year", "score_type", "preset", "score", "coverage", "n_components"],
      rows,
    ),
    `toddlab_score_${score}_${preset}_${payload.year}.csv`,
  );
}
