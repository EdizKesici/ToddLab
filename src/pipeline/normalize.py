"""normalize: data/raw/{provider}/{indicator}/{source_ref}/{ts}.json -> data/processed/{indicator}.normalized.json

Resolves every raw row to a canonical Entity via EntityRegistry. A row
whose entity can't be resolved is NEVER interpolated or attached by
approximation: it's dropped from the normalized series and logged in a
separate report (*.unresolved.json) for manual correction of entities.yaml.
This is the direct translation of the brief's "never hide gaps" principle,
applied upstream at entity-resolution time.

Unit conversion (phase 2, now real — ADR-0007/0008): each source declares
its NATIVE unit in the indicator config (`SourceRef.unit`); this module
converts every point into the indicator's canonical unit through the
DECLARED lookup table below — never a guessed factor. A conversion pair
missing from the table raises loudly and kills the rebuild: a silent
wrong-unit point is strictly worse than a failed build (the infant-
mortality percentage-vs-per-1000 bug was exactly this class of error).

Each point also carries its `role` (canonical/witness, from the config)
and, when the source prints it, per-point `citation`/`definition_note`
(the curated tier's mandatory provenance). Merge.py splits on `role`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.schema.entity import EntityRegistry
from src.schema.indicator import Indicator

# Must match RawFetchResult.now_iso()'s strftime format exactly.
SNAPSHOT_TS_FORMAT = "%Y-%m-%dT%H%M%SZ"

# Explicit unit-conversion lookup (the anti-guessing rule: every factor
# here is a dimensional identity — 1 percent = 10 per 1,000 — declared
# once, applied nowhere else). Adding a source with a new unit means
# adding its pair here or hearing the rebuild fail.
UNIT_CONVERSIONS: dict[tuple[str, str], float] = {
    ("deaths_per_100_births", "deaths_per_1000_births"): 10.0,
    ("deaths_per_1000_births", "deaths_per_100_births"): 0.1,
}


@dataclass
class NormalizedPoint:
    entity_id: str
    year: int
    value: float | None
    provider: str
    source_ref: str
    priority: int
    role: str  # "canonical" | "witness" (ADR-0007/0008) — merge splits on this
    citation: str | None = None
    definition_note: str | None = None
    # Demographic breakdown printed by the source (UN DYB Table 4: life
    # expectancy Male/Female). None = the source reports no breakdown. Part
    # of the merge key: (entity, year, sex) — see merge.py.
    sex: str | None = None
    # The collector's own quality annotations (P2), transported as-reported
    # from RawRecord and never interpreted — see base.RawRecord's docs.
    quality_code: str | None = None
    footnote_refs: list[str] | None = None
    reference_range: str | None = None
    missing_marker: str | None = None
    provisional: bool | None = None
    # Table 17's "\u2666" marker (ratio based on 30 or fewer maternal
    # deaths) — same transport discipline as `provisional`.
    small_base: bool | None = None


def _snapshot_timestamp(path: Path) -> datetime | None:
    try:
        return datetime.strptime(path.stem, SNAPSHOT_TS_FORMAT)
    except ValueError:
        return None  # unparseable filename: excluded from selection, not silently trusted


def _source_dir(raw_dir: Path, provider: str, indicator_id: str, source_ref: str) -> Path:
    """One snapshot directory per (provider, indicator, source_ref).

    The source_ref is slugified ("2024/table15" -> "2024_table15") because
    it becomes a directory name. This per-source split is what lets one
    indicator carry several sources of the SAME provider (e.g. consecutive
    DYB editions, the planned as-reported series loop) without their
    snapshots silently shadowing each other — with the previous
    per-{provider, indicator} layout, two OWID slugs would have competed
    for one directory and only the latest fetch would survive into
    normalize. A latent bug of exactly the class this project hunts.
    """
    return raw_dir / provider / indicator_id / source_ref.replace("/", "_")


def _latest_snapshot(raw_dir: Path, provider: str, indicator_id: str, source_ref: str) -> Path | None:
    """Return the chronologically most recent raw snapshot, by actually
    parsing each filename's timestamp — NOT by sorting filenames as plain
    strings. Plain lexical sort silently breaks the moment two snapshots
    use timestamp strings of different shapes (e.g. one with dashes in the
    date, one without): '2026-09-03T...' sorts BEFORE '20260101T...'
    because '-' (0x2D) is less than '0' (0x30) in ASCII, so a same-day
    mock/test snapshot with no dashes could outrank a genuinely newer real
    fetch. Caught by a live-network audit — see CHANGELOG.
    """
    source_dir = _source_dir(raw_dir, provider, indicator_id, source_ref)
    if not source_dir.is_dir():
        return None
    candidates = [(p, _snapshot_timestamp(p)) for p in source_dir.glob("*.json")]
    valid = [(p, ts) for p, ts in candidates if ts is not None]
    if not valid:
        return None
    return max(valid, key=lambda item: item[1])[0]


def _convert_unit(value: float, from_unit: str, to_unit: str) -> float:
    """Convert through the declared table ONLY. `from_unit == to_unit` is
    the identity. An unknown pair raises: a missing conversion is a config
    error to fix (add the pair or fix the declared unit), never something
    to guess. The 1e-10 rounding only removes float artifacts of the exact
    multiplication (0.31 * 10 -> 3.1000000000000005 -> 3.1)."""
    if from_unit == to_unit:
        return value
    factor = UNIT_CONVERSIONS.get((from_unit, to_unit))
    if factor is None:
        raise NotImplementedError(
            f"Conversion {from_unit!r} -> {to_unit!r} is not in the declared UNIT_CONVERSIONS "
            "table — add the pair explicitly (never guess a factor)."
        )
    return round(value * factor, 10)


def normalize_indicator(
    indicator: Indicator, raw_dir: Path, entities: EntityRegistry
) -> tuple[list[NormalizedPoint], dict[str, list[str]], dict[str, dict]]:
    """Returns (normalized points across all sources, {source_ref: [unresolved
    names]}, {"provider:ref": footnotes block of that source's snapshot}).

    The third return is new in P2: the footnote legend/texts the source
    printed (currently un_dyb only), extracted from the raw snapshot and
    written beside the points so the dist can join refs -> texts."""
    points: list[NormalizedPoint] = []
    unresolved: dict[str, list[str]] = {}
    footnotes_by_source: dict[str, dict] = {}

    for source in indicator.sources_by_priority():
        snapshot_path = _latest_snapshot(raw_dir, source.provider.value, indicator.id, source.ref)
        if snapshot_path is None:
            continue  # source not fetched yet (e.g. provider with no connector in phase 1): expected, not an error

        raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
        if raw.get("footnotes"):
            footnotes_by_source[f"{source.provider.value}:{source.ref}"] = raw["footnotes"]
        unresolved_names: set[str] = set()
        source_unit = source.unit or indicator.unit  # None = source is already in the canonical unit

        for record in raw["records"]:
            entity = entities.resolve_from_source(
                source.provider.value, record["entity_raw_name"], record.get("iso3_raw")
            )
            if entity is None:
                unresolved_names.add(record["entity_raw_name"])
                continue
            if not entity.covers_year(record["year"]):
                # The entity exists but not on this date (e.g. a "Russia" row
                # in 1980 from a source that shouldn't expose it): dropped
                # rather than distorting a historical series.
                continue
            value = record["value"]
            if value is not None:  # a gap stays a gap: conversion never invents a value
                value = _convert_unit(value, source_unit, indicator.unit)
            points.append(
                NormalizedPoint(
                    entity_id=entity.entity_id,
                    year=record["year"],
                    value=value,
                    provider=source.provider.value,
                    source_ref=source.ref,
                    priority=source.priority,
                    role=source.role.value,
                    citation=record.get("citation"),
                    definition_note=record.get("definition_note"),
                    sex=record.get("sex"),
                    quality_code=record.get("quality_code"),
                    footnote_refs=record.get("footnote_refs"),
                    reference_range=record.get("reference_range"),
                    missing_marker=record.get("missing_marker"),
                    provisional=record.get("provisional"),
                    small_base=record.get("small_base"),
                )
            )

        if unresolved_names:
            unresolved[source.ref] = sorted(unresolved_names)

    return points, unresolved, footnotes_by_source


def classify_unresolved(unresolved: dict[str, list[str]], raw_dir: Path, provider: str, indicator_id: str, source_ref: str) -> dict[str, dict]:
    """Splits each source's unresolved names into two buckets, using the
    OWID_-prefix heuristic reported by the live-network audit:

    - "owid_special": the raw row's Code starts with "OWID_" (aggregates,
      regions, income groups, or a historical/disputed entity OWID tracks
      under a pseudo-code, e.g. Kosovo=OWID_KOS). These need individual
      product judgement (ignore, like continents; or add, like Kosovo) —
      they are NOT automatically a bug in entities.yaml.
    - "possible_mapping_gap": everything else — most likely a real country
      whose name/spelling doesn't match what entities.yaml expects. This is
      the bucket to check first when correcting entities.yaml.

    This is a reporting aid only; it does not change resolution behaviour.
    """
    raw_path = _latest_snapshot(raw_dir, provider, indicator_id, source_ref)
    if raw_path is None:
        return {ref: {"owid_special": [], "possible_mapping_gap": sorted(names)} for ref, names in unresolved.items()}

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    code_by_name: dict[str, str | None] = {}
    for record in raw["records"]:
        code_by_name.setdefault(record["entity_raw_name"], record.get("iso3_raw"))

    classified: dict[str, dict] = {}
    for source_ref, names in unresolved.items():
        owid_special, mapping_gap = [], []
        for name in names:
            code = code_by_name.get(name)
            (owid_special if (code and code.startswith("OWID_")) else mapping_gap).append(name)
        classified[source_ref] = {"owid_special": sorted(owid_special), "possible_mapping_gap": sorted(mapping_gap)}
    return classified


def write_normalized(
    indicator_id: str,
    points: list[NormalizedPoint],
    unresolved: dict,
    processed_dir: Path,
    classified_unresolved: dict | None = None,
    footnotes_by_source: dict | None = None,
) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    data_path = processed_dir / f"{indicator_id}.normalized.json"
    data_path.write_text(
        json.dumps([p.__dict__ for p in points], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # Always written, even when empty: a stale unresolved.json from a
    # previous run must never survive a clean run (e.g. an old test
    # fixture's junk entity outliving the fixture itself).
    unresolved_path = processed_dir / f"{indicator_id}.unresolved.json"
    payload = classified_unresolved if classified_unresolved is not None else unresolved
    unresolved_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # The sources' footnote legend/texts (P2), keyed "provider:ref" so the
    # dist can join each emitted point's refs to the texts of ITS source.
    # Always written (same stale-file discipline).
    footnotes_path = processed_dir / f"{indicator_id}.footnotes.json"
    footnotes_path.write_text(
        json.dumps(footnotes_by_source or {}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def normalize_all(
    indicators: dict[str, Indicator], raw_dir: Path, processed_dir: Path, entities: EntityRegistry
) -> dict[str, dict]:
    """Returns a summary {indicator_id: {"n_points": int, "unresolved": {...}}} for the CLI/logs."""
    summary = {}
    for indicator in indicators.values():
        points, unresolved, footnotes_by_source = normalize_indicator(indicator, raw_dir, entities)
        classified = {}
        for source in indicator.sources_by_priority():
            if source.ref in unresolved:
                classified.update(
                    classify_unresolved(
                        {source.ref: unresolved[source.ref]},
                        raw_dir,
                        source.provider.value,
                        indicator.id,
                        source.ref,
                    )
                )
        write_normalized(
            indicator.id, points, unresolved, processed_dir, classified_unresolved=classified,
            footnotes_by_source=footnotes_by_source,
        )
        summary[indicator.id] = {"n_points": len(points), "unresolved": classified}
    return summary
