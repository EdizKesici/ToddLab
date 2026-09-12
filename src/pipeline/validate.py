"""validate: {indicator}.merged.json + {indicator}.witnesses.json -> {indicator}.validation.json + section in reports/coverage_report.md

Two families of checks:
1. Plausibility (bounds declared in plausible_range) — a safety net against
   unit/entry errors, not a scientific judgement. Applied to the canonical
   series AND to every witness series: a conversion mistake on a witness is
   exactly as damaging as one on the canonical series (the witness is what
   the divergence display compares against).
2. Coverage — for each indicator, which entities have data, over what
   range, with which internal gaps. This is the direct materialization of
   the "never hide gaps" principle: this report must be readable by someone
   who doesn't know the code. Witness series get a summary line each
   (points, entities, explicit-gap points) so the report shows what the
   comparison mode can actually compare.

Finer anomaly detection (suspicious jumps, inter-source definition breaks)
is explicitly left as phase-4 work — see docs/architecture.md.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.pipeline.merge import MergedPoint
from src.schema.entity import EntityRegistry
from src.schema.indicator import Indicator


def check_plausible_range(indicator: Indicator, points: list[MergedPoint]) -> list[dict]:
    if indicator.plausible_range is None:
        return []
    lo, hi = indicator.plausible_range.min, indicator.plausible_range.max
    violations = []
    for p in points:
        if p.value is None:
            continue
        if (lo is not None and p.value < lo) or (hi is not None and p.value > hi):
            violations.append({"entity_id": p.entity_id, "year": p.year, "value": p.value, "bounds": [lo, hi]})
    return violations


def check_no_duplicate_entity_year(points: list[MergedPoint]) -> list[tuple[str, int, str | None]]:
    """Duplicate detection on the full merge key (entity, year, sex). The
    sex part matters for the sex-split sources (DYB Table 4 emits one point
    per sex): a male + female pair on the same entity-year is NOT a
    duplicate — two points with the SAME sex would be."""
    seen = set()
    dupes = set()
    for p in points:
        key = (p.entity_id, p.year, p.sex)
        if key in seen:
            dupes.add(key)
        seen.add(key)
    return sorted(dupes)


def coverage_summary(indicator: Indicator, points: list[MergedPoint], entities: EntityRegistry) -> dict:
    by_entity: dict[str, list[int]] = {}
    for p in points:
        by_entity.setdefault(p.entity_id, []).append(p.year)

    covered_entities = []
    for entity_id, years in sorted(by_entity.items()):
        years_sorted = sorted(set(years))
        span = years_sorted[-1] - years_sorted[0] + 1
        n_present = len(years_sorted)
        covered_entities.append(
            {
                "entity_id": entity_id,
                "label": entities.by_id(entity_id).label if entities.by_id(entity_id) else entity_id,
                "year_min": years_sorted[0],
                "year_max": years_sorted[-1],
                "n_points": n_present,
                "n_missing_within_span": span - n_present,
            }
        )

    all_entity_ids = {e.entity_id for e in entities.entities}
    no_data_entities = sorted(all_entity_ids - by_entity.keys())

    return {
        "indicator_id": indicator.id,
        "n_entities_total_registry": len(entities.entities),
        "n_entities_with_data": len(covered_entities),
        "n_entities_no_data": len(no_data_entities),
        "no_data_entities": no_data_entities,
        "covered_entities": covered_entities,
    }


def validate_indicator(indicator: Indicator, processed_dir: Path, entities: EntityRegistry) -> dict:
    merged_path = processed_dir / f"{indicator.id}.merged.json"
    raw_points = json.loads(merged_path.read_text(encoding="utf-8"))
    points = [MergedPoint(**p) for p in raw_points]

    witnesses_path = processed_dir / f"{indicator.id}.witnesses.json"
    raw_witnesses = json.loads(witnesses_path.read_text(encoding="utf-8")) if witnesses_path.exists() else []

    witness_results = []
    for w in raw_witnesses:
        w_points = [
            MergedPoint(
                entity_id=p["entity_id"],
                year=p["year"],
                value=p["value"],
                provider=w["provider"],
                source_ref=w["source_ref"],
                sex=p.get("sex"),
            )
            for p in w["data"]
        ]
        witness_results.append(
            {
                "provider": w["provider"],
                "source_ref": w["source_ref"],
                "n_points": len(w_points),
                "n_explicit_gaps": sum(1 for p in w_points if p.value is None),
                "n_entities": len({p.entity_id for p in w_points}),
                "range_violations": check_plausible_range(indicator, w_points),
                "duplicate_entity_year": check_no_duplicate_entity_year(w_points),
            }
        )

    result = {
        "indicator_id": indicator.id,
        "reliability": indicator.reliability.value,
        "range_violations": check_plausible_range(indicator, points),
        "duplicate_entity_year": check_no_duplicate_entity_year(points),
        "coverage": coverage_summary(indicator, points, entities),
        "witnesses": witness_results,
    }
    (processed_dir / f"{indicator.id}.validation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def render_coverage_report_md(results: list[dict]) -> str:
    lines = ["# Coverage report", "", "Generated automatically on every build. Do not edit by hand.", ""]
    for r in results:
        cov = r["coverage"]
        lines.append(f"## {r['indicator_id']} (declared reliability: {r['reliability']})")
        lines.append("")
        lines.append(f"- Entities with at least one point: **{cov['n_entities_with_data']} / {cov['n_entities_total_registry']}**")
        lines.append(f"- Entities with no data at all: {cov['n_entities_no_data']}")
        if r["range_violations"]:
            lines.append(f"- ⚠️ **{len(r['range_violations'])} value(s) out of plausible bounds**")
        if r["duplicate_entity_year"]:
            lines.append(f"- ⚠️ **{len(r['duplicate_entity_year'])} entity-year duplicate(s) after merge (merge bug)**")
        lines.append("")
        lines.append("| Entity | First year | Last year | Points | Internal gaps |")
        lines.append("|---|---|---|---|---|")
        for e in cov["covered_entities"]:
            lines.append(
                f"| {e['label']} | {e['year_min']} | {e['year_max']} | {e['n_points']} | {e['n_missing_within_span']} |"
            )
        lines.append("")
        for w in r.get("witnesses", []):
            lines.append(
                f"- Witness `{w['provider']}:{w['source_ref']}` — {w['n_entities']} entities, "
                f"{w['n_points']} points ({w['n_explicit_gaps']} explicit gap points)"
            )
            if w["range_violations"]:
                lines.append(f"  - ⚠️ **{len(w['range_violations'])} witness value(s) out of plausible bounds**")
            if w["duplicate_entity_year"]:
                lines.append(f"  - ⚠️ **{len(w['duplicate_entity_year'])} witness entity-year duplicate(s) (merge bug)**")
        if r.get("witnesses"):
            lines.append("")
    return "\n".join(lines)


def validate_all(indicators: dict[str, Indicator], processed_dir: Path, entities: EntityRegistry, reports_dir: Path) -> list[dict]:
    results = [validate_indicator(ind, processed_dir, entities) for ind in indicators.values()]
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "coverage_report.md").write_text(render_coverage_report_md(results), encoding="utf-8")
    return results
