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

v25 (the population-segment face): {indicator}.segments.json and
{indicator}.segments_citizenship.json — the CLASS decomposition of a rate
normalize routed on population_class — merge under their OWN key
(entity, class, year, sex) into {indicator}.segments.merged.json +
.witnesses.json (and the citizenship twin), with the same two rules
verbatim. The layer kinds never collide BY CONSTRUCTION: a
class-carrying point never enters the (entity, year, sex) flow, and
the class vocabularies are layer-scoped (the birth face's natives/foreign_born never meet the
citizenship face's nationals/foreigners — separate files, separate key
spaces, the ADR-0010 discipline extended to the segment pair).

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


def _segments_key(point: NormalizedPoint | "MergedPoint") -> tuple[str, str, int, str | None]:
    """v25: the population-segment layer's own merge key — (entity, class,
    year, sex). The class is always set on this layer's points (normalize
    routes on its presence); a point reaching here without one is a
    pipeline bug, refused loudly."""
    pop_class = getattr(point, "population_class", None)
    if pop_class is None:
        raise ValueError(
            f"segments merge received a point without population_class ({point.entity_id}, "
            f"{point.year}) — the single-axis flow must never reach this path."
        )
    return (point.entity_id, pop_class, point.year, getattr(point, "sex", None))


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
    # v25 (the population-segment face): the CLASS of a class-decomposed
    # rate — set on every point of the segment layers; None on every
    # single-axis point.
    population_class: str | None = None
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


def merge_segment_points(
    points: list[NormalizedPoint], layer_label: str = "segments"
) -> tuple[list[MergedPoint], list[dict]]:
    """v25: the population-segment layer's canonical merge — the same two
    rules as merge_points, under the (entity, class, year, sex) key. In
    the wired shape the two Eurostat class doors (birth and citizenship)
    are disjoint by FACE (separate key spaces), so the within-tier
    arbitration never fires across them — the machinery exists for the
    same reason the single-axis one does: a future class-canonical door
    colliding on an (entity, class, year, sex) must be arbitrated by
    priority and LOGGED, never silently shadowed."""
    by_key: dict[tuple[str, str, int, str | None], list[NormalizedPoint]] = {}
    for p in points:
        by_key.setdefault(_segments_key(p), []).append(p)

    merged: list[MergedPoint] = []
    provenance_log: list[dict] = []

    for (entity_id, pop_class, year, sex), candidates in by_key.items():
        usable = [c for c in candidates if c.value is not None]
        if usable:
            usable.sort(key=lambda c: c.priority)
            winner = usable[0]
        else:
            candidates.sort(key=lambda c: c.priority)
            winner = candidates[0]  # the explicit-gap semantics, verbatim
        merged.append(
            MergedPoint(
                entity_id=entity_id,
                year=year,
                value=winner.value,
                provider=winner.provider,
                source_ref=winner.source_ref,
                sex=sex,
                population_class=pop_class,
                quality_code=winner.quality_code,
                provisional=winner.provisional,
            )
        )
        if usable and len(usable) > 1:
            provenance_log.append(
                {
                    "role": "canonical",
                    "layer": layer_label,
                    "entity_id": entity_id,
                    "population_class": pop_class,
                    "year": year,
                    "retained": {"provider": winner.provider, "source_ref": winner.source_ref, "value": winner.value},
                    "discarded": [
                        {"provider": c.provider, "source_ref": c.source_ref, "value": c.value}
                        for c in usable[1:]
                    ],
                }
            )

    merged.sort(key=lambda m: (m.entity_id, m.population_class or "", m.year, m.sex or ""))
    return merged, provenance_log


def build_segment_witness_series(
    group: list[NormalizedPoint], layer_label: str = "segments"
) -> tuple[WitnessSeries, list[dict]]:
    """v25: the segment witness twin — one (provider, source_ref)'s
    class-decomposed points as one series, duplicates reduced under the
    (entity, class, year, sex) key and logged, all-null keys kept as
    explicit gap points. The ILOSTAT CCT/CBR class cross-sections are the
    first riders (one row per area-class-year-sex — no duplicates by
    construction, the machinery guards the day a second segment witness
    arrives)."""
    provider, source_ref = group[0].provider, group[0].source_ref
    by_key: dict[tuple[str, str, int, str | None], list[NormalizedPoint]] = {}
    for p in group:
        by_key.setdefault(_segments_key(p), []).append(p)

    points: list[MergedPoint] = []
    provenance_log: list[dict] = []
    for (entity_id, pop_class, year, sex), candidates in by_key.items():
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
                sex=sex,
                population_class=pop_class,
                quality_code=winner.quality_code,
                provisional=winner.provisional,
            )
        )
        if len(candidates) > 1:
            provenance_log.append(
                {
                    "role": "witness",
                    "layer": layer_label,
                    "entity_id": entity_id,
                    "population_class": pop_class,
                    "year": year,
                    "witness": f"{provider}:{source_ref}",
                    "retained": {"value": winner.value, "n_candidate_rows": len(candidates)},
                    "discarded": [
                        {"value": c.value, "priority": c.priority} for c in candidates if c is not winner
                    ],
                }
            )

    points.sort(key=lambda m: (m.entity_id, m.population_class or "", m.year, m.sex or ""))
    return WitnessSeries(provider=provider, source_ref=source_ref, points=points), provenance_log


def _merge_segments_layer(
    indicator_id: str, processed_dir: Path, layer: str, provenance: list[dict]
) -> None:
    """v25: one population-segment FACE's merge — the same layer discipline
    on the (entity, class, year, sex) key space: reads
    {indicator}.{layer}.json, merges the canonical tier, builds the
    per-source witness series, writes {indicator}.{layer}.merged.json +
    .witnesses.json only when the layer has points (and UNLINKS stale
    copies when it does not — an absent file is what build reads as "no
    layer").
    layer: "segments" (the birth face — immigrés) | "segments_citizenship"
    (the legal face — étrangers) — the label rides every provenance entry
    the layer emits, and the class vocabularies are layer-scoped."""
    layer_path = processed_dir / f"{indicator_id}.{layer}.json"
    if not layer_path.exists():
        return
    layer_raw = json.loads(layer_path.read_text(encoding="utf-8"))
    if not layer_raw:
        for stale in (f"{layer}.merged.json", f"{layer}.witnesses.json"):
            (processed_dir / f"{indicator_id}.{stale}").unlink(missing_ok=True)
        return
    layer_points = [NormalizedPoint(**p) for p in layer_raw]
    s_canonical, s_witness_groups = _split_by_role(layer_points)
    s_merged, s_provenance = merge_segment_points(s_canonical, layer_label=layer)
    provenance.extend(s_provenance)

    s_witness_payload = []
    for group in s_witness_groups:
        s_series, s_series_provenance = build_segment_witness_series(group, layer_label=layer)
        provenance.extend(s_series_provenance)
        s_witness_payload.append(
            {
                "provider": s_series.provider,
                "source_ref": s_series.source_ref,
                "data": [
                    {
                        "entity_id": p.entity_id,
                        "year": p.year,
                        "population_class": p.population_class,
                        "value": p.value,
                        **({"sex": p.sex} if p.sex else {}),
                        **({"quality_code": p.quality_code} if p.quality_code else {}),
                        **({"provisional": True} if p.provisional else {}),
                    }
                    for p in s_series.points
                ],
            }
        )
    (processed_dir / f"{indicator_id}.{layer}.merged.json").write_text(
        json.dumps([m.__dict__ for m in s_merged], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (processed_dir / f"{indicator_id}.{layer}.witnesses.json").write_text(
        json.dumps(s_witness_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


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

    # v25 (the population-segment face): the two CLASS faces merge under
    # their own keys BEFORE the provenance file is written, so one trail
    # carries every layer's entries (each self-describing — every segment
    # entry carries layer: "segments" or "segments_citizenship" and
    # population_class). The two faces are PARALLEL, never merged
    # (ADR-0010) — separate files, separate key spaces, shared machinery.
    # CLASS faces — segments (birth, immigrés) and segments_citizenship
    # (citizenship, étrangers), parallel under the ADR-0010 rule, each
    # self-describing in the shared provenance trail.
    _merge_segments_layer(indicator_id, processed_dir, "segments", provenance)
    _merge_segments_layer(indicator_id, processed_dir, "segments_citizenship", provenance)

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
    else:
        # v22 corollary of the stale-file discipline: a clean run with zero
        # arbitrations removes a stale provenance file too (previously the
        # file simply stopped being rewritten — the last run's trail would
        # have survived every subsequent clean run unread).
        (processed_dir / f"{indicator_id}.provenance.json").unlink(missing_ok=True)
    return merged, provenance


def merge_all(indicator_ids: list[str], processed_dir: Path) -> dict[str, int]:
    return {iid: len(merge_indicator(iid, processed_dir)[0]) for iid in indicator_ids}
