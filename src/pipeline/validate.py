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


def check_no_duplicate_bilateral(points: list[MergedPoint]) -> list[tuple[str, str, int, str | None]]:
    """v22: the bilateral layer's duplicate detection — the full by-origin
    key (destination, origin, year, sex), the same discipline as the
    single-axis check one layer over."""
    seen = set()
    dupes = set()
    for p in points:
        key = (p.entity_id, p.origin_entity_id, p.year, p.sex)
        if key in seen:
            dupes.add(key)
        seen.add(key)
    return sorted(dupes)


def check_no_duplicate_segments(points: list[MergedPoint]) -> list[tuple[str, str, int, str | None]]:
    """v25: the population-segment layer's duplicate detection — the full
    class key (entity, class, year, sex), the same discipline as the
    single-axis and bilateral checks."""
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


def _bilateral_validation(
    indicator: Indicator, processed_dir: Path, layer: str, entities: EntityRegistry
) -> dict | None:
    """v22 (inline block) / v23 (extracted, parameterized): one bilateral
    FACE's own checks — the plausible bounds apply (a unit error on a
    by-origin point is exactly as damaging whatever the legality), the
    duplicate detection runs on (destination, origin, year, sex), and the
    coverage summary counts the DESTINATION axis (the boards' rows) with
    the pair count beside it. None when the indicator carries no points
    on this layer (the 27 single-axis indicators — honest absence, same
    as the dist layer itself)."""
    bilateral_merged_path = processed_dir / f"{indicator.id}.{layer}.merged.json"
    if not bilateral_merged_path.exists():
        return None
    b_raw_points = json.loads(bilateral_merged_path.read_text(encoding="utf-8"))
    b_points = [MergedPoint(**p) for p in b_raw_points]
    b_witnesses_path = processed_dir / f"{indicator.id}.{layer}.witnesses.json"
    b_raw_witnesses = (
        json.loads(b_witnesses_path.read_text(encoding="utf-8")) if b_witnesses_path.exists() else []
    )
    b_witness_results = []
    for bw in b_raw_witnesses:
        bw_points = [
            MergedPoint(
                entity_id=p["entity_id"],
                origin_entity_id=p.get("origin_entity_id"),
                year=p["year"],
                value=p["value"],
                provider=bw["provider"],
                source_ref=bw["source_ref"],
                sex=p.get("sex"),
            )
            for p in bw["data"]
        ]
        b_witness_results.append(
            {
                "provider": bw["provider"],
                "source_ref": bw["source_ref"],
                "n_points": len(bw_points),
                "n_explicit_gaps": sum(1 for p in bw_points if p.value is None),
                "n_destinations": len({p.entity_id for p in bw_points}),
                "n_origins": len({p.origin_entity_id for p in bw_points}),
                "range_violations": check_plausible_range(indicator, bw_points),
                "duplicate_entity_year": check_no_duplicate_bilateral(bw_points),
            }
        )
    return {
        "n_points": len(b_points),
        "n_pairs": len({(p.entity_id, p.origin_entity_id) for p in b_points}),
        "n_destinations": len({p.entity_id for p in b_points}),
        "n_origins": len({p.origin_entity_id for p in b_points}),
        "n_explicit_gaps": sum(1 for p in b_points if p.value is None),
        "range_violations": check_plausible_range(indicator, b_points),
        "duplicate_entity_year": check_no_duplicate_bilateral(b_points),
        "coverage": coverage_summary(indicator, b_points, entities),
        "witnesses": b_witness_results,
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

    # v22 (the bilateral face) / v23 (the citizenship face): each by-origin
    # FACE gets the SAME two families of checks under its own key (see
    # _bilateral_validation) — the plausible bounds apply (a unit error on
    # a by-origin point is exactly as damaging), the duplicate detection
    # runs on (destination, origin, year, sex), and the coverage summary
    # counts the DESTINATION axis (the boards' rows) with the pair count
    # beside it. Absent when the indicator carries no points on that layer
    # (the 27 single-axis indicators — honest absence, same as the dist
    # layer itself).
    for layer in ("bilateral", "bilateral_citizenship"):
        layer_result = _bilateral_validation(indicator, processed_dir, layer, entities)
        if layer_result is not None:
            result[layer] = layer_result
    # v25 (the population-segment faces): the same per-layer checks for the
    # two CLASS faces — segments (birth) and segments_citizenship (the
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
        # v22: the by-origin layer's own summary block — the destination
        # axis is the boards' row space, the pair count the matrix's own
        # size, the witnesses beside it (the OECD matrix's world face).
        # v23: the citizenship face renders its own block with the same
        # shape — the two faces read side by side, never blended.
        for layer_key, layer_label in (("bilateral", "Bilateral layer"),
                                       ("bilateral_citizenship", "Bilateral (citizenship) layer"),
                                       ("segments", "Segments (country-of-birth classes) layer"),
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
            lines.append(
                f"- {layer_label}: **{b['n_points']} points** on {b['n_pairs']} (destination x origin) "
                f"pairs — {b['n_destinations']} destinations x {b['n_origins']} distinct origins "
                f"({b['n_explicit_gaps']} explicit gap points)"
            )
            if b["range_violations"]:
                lines.append(f"  - ⚠️ **{len(b['range_violations'])} bilateral value(s) out of plausible bounds**")
            if b["duplicate_entity_year"]:
                lines.append(f"  - ⚠️ **{len(b['duplicate_entity_year'])} bilateral (destination, origin, year) duplicate(s) (merge bug)**")
            for bw in b.get("witnesses", []):
                lines.append(
                    f"- Bilateral witness `{bw['provider']}:{bw['source_ref']}` — {bw['n_destinations']} destinations, "
                    f"{bw['n_origins']} origins, {bw['n_points']} points ({bw['n_explicit_gaps']} explicit gap points)"
                )
                if bw["range_violations"]:
                    lines.append(f"  - ⚠️ **{len(bw['range_violations'])} bilateral witness value(s) out of plausible bounds**")
                if bw["duplicate_entity_year"]:
                    lines.append(f"  - ⚠️ **{len(bw['duplicate_entity_year'])} bilateral witness duplicate(s) (merge bug)**")
            lines.append("")
    return "\n".join(lines)


def validate_all(indicators: dict[str, Indicator], processed_dir: Path, entities: EntityRegistry, reports_dir: Path) -> list[dict]:
    results = [validate_indicator(ind, processed_dir, entities) for ind in indicators.values()]
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "coverage_report.md").write_text(render_coverage_report_md(results), encoding="utf-8")
    return results
