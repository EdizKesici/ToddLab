"""merge: {indicator}.normalized.json (all sources, roles attached) ->
    {indicator}.merged.json (canonical series: one value per entity-year-sex)
    {indicator}.witnesses.json (witness series: per-source, never merged)

Two rules (ADR-0007 decision 2, operationalized by ADR-0008):

1. WITHIN the canonical tier, for an (entity_id, year, sex) key covered by
   several canonical sources, keep the value from the highest-priority
   source (smallest number) that actually has a non-null value. This is an
   authenticity-tier-internal arbitration, never a cross-layer blend.
   Every arbitration is logged in a provenance trail — merge must never
   be a black box, an explicit requirement from the brief.
2. ACROSS layers there is no arbitration at all: witness sources are kept
   as separate per-source series (stored, validated, displayed beside the
   canonical series as divergence — never merged into it, never averaged
   with it). The only reduction inside one witness series is duplicate
   (entity, year, sex) points emitted by the source itself (e.g. DYB double
   "Total" rows under different quality regimes): the first non-null
   value wins, and every such reduction is logged in the same provenance
   trail with role="witness".

The merge key includes `sex` because the DYB Table 4 collector prints
life expectancy at birth for Male and Female separately (there is no
"both sexes" column to report — averaging would be a derivation, and the
canonical tier reports, it does not derive). All non-sex-split sources
carry sex=None, so their keys are unchanged; a both-sexes witness series
and a sex-split canonical series coexist on the same (entity, year)
without colliding.

Witness points with value=None are KEPT as points (an explicit "reported
to the collector but no value computed" gap — e.g. DYB rates for "U"
data), distinct from absent points (no row at all). Since v9 the SAME
semantics apply to the canonical tier: a key where every canonical source
prints "no value" is kept as ONE explicit gap point (the highest-priority
candidate's own annotations riding it), because that gap is itself data —
the collector's honest degradation ("counts published, no ratio computed
for cause-of-death data judged incomplete"). A key with at least onevalued candidate never emits a gap point.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.pipeline.normalize import NormalizedPoint


def _key(point: NormalizedPoint | "MergedPoint") -> tuple[str, int, str | None]:
    return (point.entity_id, point.year, getattr(point, "sex", None))


@dataclass
class MergedPoint:
    entity_id: str
    year: int
    value: float | None
    provider: str
    source_ref: str
    # Per-point provenance, carried when the source prints it (mandatory
    # on curated rows — the curation gate's citable-source condition).
    citation: str | None = None
    definition_note: str | None = None
    # Demographic breakdown printed by the source (DYB Table 4: male /
    # female life expectancy). None = no breakdown reported.
    sex: str | None = None
    # The collector's own quality annotations (P2) — carried from the WINNING
    # source's point, as-reported (see base.RawRecord's docs). Note they are
    # the winner's OWN annotations: when arbitration keeps a later edition's
    # value, the codes/refs are that edition's, never a blend.
    quality_code: str | None = None
    footnote_refs: list[str] | None = None
    reference_range: str | None = None
    missing_marker: str | None = None
    provisional: bool | None = None
    # Table 17's "\u2666" marker (ratio based on 30 or fewer maternal
    # deaths), same winner-annotations discipline as the fields above.
    small_base: bool | None = None


@dataclass
class WitnessSeries:
    provider: str
    source_ref: str
    points: list[MergedPoint]


def _split_by_role(points: list[NormalizedPoint]) -> tuple[list[NormalizedPoint], list[list[NormalizedPoint]]]:
    """Returns (canonical points, [witness points grouped per (provider, source_ref)])."""
    canonical = [p for p in points if p.role == "canonical"]
    witness_groups: dict[tuple[str, str], list[NormalizedPoint]] = {}
    for p in points:
        if p.role == "witness":
            witness_groups.setdefault((p.provider, p.source_ref), []).append(p)
    witnesses = [witness_groups[key] for key in sorted(witness_groups)]
    return canonical, witnesses


def merge_points(points: list[NormalizedPoint]) -> tuple[list[MergedPoint], list[dict]]:
    by_key: dict[tuple[str, int, str | None], list[NormalizedPoint]] = {}
    for p in points:
        by_key.setdefault(_key(p), []).append(p)

    merged: list[MergedPoint] = []
    provenance_log: list[dict] = []

    for (entity_id, year, sex), candidates in by_key.items():
        usable = [c for c in candidates if c.value is not None]
        if usable:
            usable.sort(key=lambda c: c.priority)
            winner = usable[0]
        else:
            # Every canonical source prints "no value" here (the collector's
            # honest degradation — e.g. DYB rates under "U"/"..." codes):
            # keep ONE explicit gap point carrying the highest-priority
            # (latest vintage) candidate's own annotations. Nothing is
            # fabricated, and the gap stops reading as "never reported".
            # No provenance entry: nothing was discarded — every candidate
            # agrees there is no value (the gap point itself is the record).
            candidates.sort(key=lambda c: c.priority)
            winner = candidates[0]
        merged.append(
            MergedPoint(
                entity_id=entity_id,
                year=year,
                value=winner.value,
                provider=winner.provider,
                source_ref=winner.source_ref,
                citation=winner.citation,
                definition_note=winner.definition_note,
                sex=sex,
                quality_code=winner.quality_code,
                footnote_refs=winner.footnote_refs,
                reference_range=winner.reference_range,
                missing_marker=winner.missing_marker,
                provisional=winner.provisional,
                small_base=winner.small_base,
            )
        )
        if usable and len(usable) > 1:
            provenance_log.append(
                {
                    "role": "canonical",
                    "entity_id": entity_id,
                    "year": year,
                    **({"sex": sex} if sex else {}),
                    "retained": {"provider": winner.provider, "source_ref": winner.source_ref, "value": winner.value},
                    "discarded": [
                        {"provider": c.provider, "source_ref": c.source_ref, "value": c.value}
                        for c in usable[1:]
                    ],
                }
            )

    merged.sort(key=lambda m: (m.entity_id, m.year, m.sex or ""))
    return merged, provenance_log


def build_witness_series(group: list[NormalizedPoint]) -> tuple[WitnessSeries, list[dict]]:
    """One witness source's points -> one series + provenance entries for
    the duplicate reductions (first non-null value wins; all-null duplicates
    collapse to a single explicit gap point)."""
    provider, source_ref = group[0].provider, group[0].source_ref
    by_key: dict[tuple[str, int, str | None], list[NormalizedPoint]] = {}
    for p in group:
        by_key.setdefault(_key(p), []).append(p)

    points: list[MergedPoint] = []
    provenance_log: list[dict] = []
    for (entity_id, year, sex), candidates in by_key.items():
        candidates.sort(key=lambda c: c.priority)
        non_null = [c for c in candidates if c.value is not None]
        if non_null:
            winner = non_null[0]
        else:
            winner = candidates[0]  # an all-null key stays as ONE explicit gap point
        points.append(
            MergedPoint(
                entity_id=entity_id,
                year=year,
                value=winner.value,
                provider=provider,
                source_ref=source_ref,
                citation=winner.citation,
                definition_note=winner.definition_note,
                sex=sex,
                quality_code=winner.quality_code,
                footnote_refs=winner.footnote_refs,
                reference_range=winner.reference_range,
                missing_marker=winner.missing_marker,
                provisional=winner.provisional,
                small_base=winner.small_base,
            )
        )
        if len(candidates) > 1:
            provenance_log.append(
                {
                    "role": "witness",
                    "entity_id": entity_id,
                    "year": year,
                    **({"sex": sex} if sex else {}),
                    "witness": f"{provider}:{source_ref}",
                    "retained": {"value": winner.value, "n_candidate_rows": len(candidates)},
                    "discarded": [
                        {"value": c.value, "priority": c.priority} for c in candidates if c is not winner
                    ],
                }
            )

    points.sort(key=lambda m: (m.entity_id, m.year, m.sex or ""))
    return WitnessSeries(provider=provider, source_ref=source_ref, points=points), provenance_log


def merge_indicator(indicator_id: str, processed_dir: Path) -> tuple[list[MergedPoint], list[dict]]:
    normalized_path = processed_dir / f"{indicator_id}.normalized.json"
    raw_points = json.loads(normalized_path.read_text(encoding="utf-8"))
    points = [NormalizedPoint(**p) for p in raw_points]

    canonical, witness_groups = _split_by_role(points)
    merged, provenance = merge_points(canonical)

    witness_payload = []
    for group in witness_groups:
        series, series_provenance = build_witness_series(group)
        provenance.extend(series_provenance)
        witness_payload.append(
            {
                "provider": series.provider,
                "source_ref": series.source_ref,
                "data": [
                    {
                        "entity_id": p.entity_id,
                        "year": p.year,
                        "value": p.value,
                        **({"citation": p.citation} if p.citation else {}),
                        **({"definition_note": p.definition_note} if p.definition_note else {}),
                        **({"sex": p.sex} if p.sex else {}),
                        **({"quality_code": p.quality_code} if p.quality_code else {}),
                        **({"footnote_refs": p.footnote_refs} if p.footnote_refs else {}),
                        **({"reference_range": p.reference_range} if p.reference_range else {}),
                        **({"missing_marker": p.missing_marker} if p.missing_marker else {}),
                        **({"provisional": True} if p.provisional else {}),
                        **({"small_base": True} if p.small_base else {}),
                    }
                    for p in series.points
                ],
            }
        )

    (processed_dir / f"{indicator_id}.merged.json").write_text(
        json.dumps([m.__dict__ for m in merged], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Always written (even when empty): the witness contract is part of the
    # dist format, and a stale witnesses.json must never survive a clean run.
    (processed_dir / f"{indicator_id}.witnesses.json").write_text(
        json.dumps(witness_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if provenance:
        (processed_dir / f"{indicator_id}.provenance.json").write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return merged, provenance


def merge_all(indicator_ids: list[str], processed_dir: Path) -> dict[str, int]:
    return {iid: len(merge_indicator(iid, processed_dir)[0]) for iid in indicator_ids}
