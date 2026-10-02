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


def check_no_duplicate_segments(points: list[MergedPoint]) -> list[tuple[str, str, int, str | None]]:
    """v25: the population-segment layer's duplicate detection — the full
    class key (entity, class, year, sex), the same discipline as the
    single-axis check."""
    seen = set()
    dupes = set()
    for p in points:
        key = (p.entity_id, p.population_class, p.year, p.sex)
        if key in seen:
            dupes.add(key)
        seen.add(key)
    return sorted(dupes)


def _segments_validation(
    indicator: Indicator, processed_dir: Path, layer: str, entities: EntityRegistry
) -> dict | None:
    """v25: one population-segment FACE's own checks — the same two
    families as every other layer, under the (entity, class, year, sex)
    key: the plausible bounds apply (a unit error on a class point is
    exactly as damaging whatever the segment), the duplicate detection
    runs on the full class key, and the coverage summary counts the
    ENTITY axis with the class count beside it. None when the indicator
    carries no points on this layer (honest absence, same as the dist
    layer itself)."""
    segments_merged_path = processed_dir / f"{indicator.id}.{layer}.merged.json"
    if not segments_merged_path.exists():
        return None
    s_raw_points = json.loads(segments_merged_path.read_text(encoding="utf-8"))
    s_points = [MergedPoint(**p) for p in s_raw_points]
    s_witnesses_path = processed_dir / f"{indicator.id}.{layer}.witnesses.json"
    s_raw_witnesses = (
        json.loads(s_witnesses_path.read_text(encoding="utf-8")) if s_witnesses_path.exists() else []
    )
    s_witness_results = []
    for sw in s_raw_witnesses:
        sw_points = [
            MergedPoint(
                entity_id=p["entity_id"],
                population_class=p.get("population_class"),
                year=p["year"],
                value=p["value"],
                provider=sw["provider"],
                source_ref=sw["source_ref"],
                sex=p.get("sex"),
            )
            for p in sw["data"]
        ]
        s_witness_results.append(
            {
                "provider": sw["provider"],
                "source_ref": sw["source_ref"],
                "n_points": len(sw_points),
                "n_explicit_gaps": sum(1 for p in sw_points if p.value is None),
                "n_entities": len({p.entity_id for p in sw_points}),
                "n_classes": len({p.population_class for p in sw_points}),
                "range_violations": check_plausible_range(indicator, sw_points),
                "duplicate_entity_year": check_no_duplicate_segments(sw_points),
            }
        )
    return {
        "n_points": len(s_points),
        "n_entities": len({p.entity_id for p in s_points}),
        "n_classes": len({p.population_class for p in s_points}),
        "n_explicit_gaps": sum(1 for p in s_points if p.value is None),
        "range_violations": check_plausible_range(indicator, s_points),
        "duplicate_entity_year": check_no_duplicate_segments(s_points),
        "coverage": coverage_summary(indicator, s_points, entities),
        "witnesses": s_witness_results,
    }


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

    # v25 (the population-segment faces): the two CLASS faces get the same
    # per-layer checks — segments (birth) and segments_citizenship (the
    # legal face), absent when the indicator carries no points there.
    for layer in ("segments", "segments_citizenship"):
        layer_result = _segments_validation(indicator, processed_dir, layer, entities)
        if layer_result is not None:
            result[layer] = layer_result

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
        # v25: the segment faces' own summary blocks — the class count, the
        # entity count, the witnesses beside them (the ILOSTAT class
        # cross-sections' world face). The two faces read side by side,
        # never blended.
        for layer_key, layer_label in (("segments", "Segments (country-of-birth classes) layer"),
                                       ("segments_citizenship", "Segments (citizenship classes) layer")):
            b = r.get(layer_key)
            if not b:
                continue
            if layer_key.startswith("segments"):
                lines.append(
                    f"- {layer_label}: **{b['n_points']} points** on {b['n_classes']} population classes "
                    f"across {b['n_entities']} entities ({b['n_explicit_gaps']} explicit gap points)"
                )
                if b["range_violations"]:
                    lines.append(f"  - ⚠️ **{len(b['range_violations'])} segment value(s) out of plausible bounds**")
                if b["duplicate_entity_year"]:
                    lines.append(f"  - ⚠️ **{len(b['duplicate_entity_year'])} segment (entity, class, year) duplicate(s) (merge bug)**")
                for bw in b.get("witnesses", []):
                    lines.append(
                        f"- Segment witness `{bw['provider']}:{bw['source_ref']}` — {bw['n_entities']} entities, "
                        f"{bw['n_classes']} classes, {bw['n_points']} points ({bw['n_explicit_gaps']} explicit gap points)"
                    )
                    if bw["range_violations"]:
                        lines.append(f"  - ⚠️ **{len(bw['range_violations'])} segment witness value(s) out of plausible bounds**")
                    if bw["duplicate_entity_year"]:
                        lines.append(f"  - ⚠️ **{len(bw['duplicate_entity_year'])} segment witness duplicate(s) (merge bug)**")
                lines.append("")
                continue
    return "\n".join(lines)


def validate_all(indicators: dict[str, Indicator], processed_dir: Path, entities: EntityRegistry, reports_dir: Path) -> list[dict]:
    results = [validate_indicator(ind, processed_dir, entities) for ind in indicators.values()]
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "coverage_report.md").write_text(render_coverage_report_md(results), encoding="utf-8")
    return results
