"""build: {indicator}.merged.json + {indicator}.witnesses.json + {indicator}.footnotes.json + entities.yaml -> data/dist/*.json

The only step whose output is a contract for the frontend (which you own).
The format below is a proposal, not a frozen decision — tell me if you want
it to evolve once you start frontend integration.

ADR-0008 dist contract (the Todd board's data layer):
- `data` is the CANONICAL series (as-reported tier: curated + collectors),
  one point per (entity, year, sex), each carrying its own `provider`/
  `source_ref` (the canonical series is multi-source by construction, so
  per-point provenance IS the anti-bricolage guarantee) and, when the
  source prints it, `citation`/`definition_note` plus the collector's own
  quality annotations (P2): `quality_code`, `footnote_refs`,
  `reference_range` (LE only), `missing_marker`, `provisional`.
- `witnesses` holds the harmonized series BESIDE it — same unit, same
  entity space, never merged — for the divergence display and for the
  Extra board (which reads the same file with a witness as its display
  series: comparability vs authenticity is a per-board choice, not a
  hidden mix).
- `sources` declares every source with its `role`, `layer` (from
  PROVIDER_LAYER), `native_unit` (pre-conversion), and — since P2 — a
  full citation block (`citation`, `url`, `license`) plus the source's
  own footnote `legend`/`notes` (the DYB Footnotes worksheet) restricted
  to the refs the emitted points actually carry, so the frontend can
  render "27.7 [code U, fn 1: ...]" without touching the raw tier.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from src.schema.entity import EntityRegistry
from src.schema.indicator import (
    PROVIDER_CITATION,
    PROVIDER_LAYER,
    PROVIDER_LICENSE,
    Indicator,
    Provider,
)

logger = logging.getLogger(__name__)


def _source_url(provider: Provider, ref: str, field: str | None = None) -> str | None:
    """Where this source's data is fetched from — the concrete URL for the
    wired providers, None for the not-yet-wired ones (an invented URL would
    be worse than an absent field)."""
    if provider == Provider.un_dyb:
        from src.connectors.dyb import build_url as dyb_build_url  # local import: avoid a pipeline->connectors hard edge at import time

        return dyb_build_url(ref)
    if provider == Provider.oecd:
        from src.connectors.oecd import build_url as oecd_build_url  # idem

        return oecd_build_url(ref, field=field)
    if provider == Provider.owid:
        return f"https://ourworldindata.org/grapher/{ref}"
    if provider == Provider.curated:
        return f"catalog/curated/{ref}.csv"
    return None


def _source_citation(provider: Provider, ref: str) -> str:
    """The provider's citation template formatted with the source_ref's own
    parts (a DYB ref IS an edition/table pair — '2024/table15'; an OECD ref
    is a dataflow/cause pair — 'DF_COM/CICDHOCD')."""
    template = PROVIDER_CITATION[provider]
    if provider == Provider.un_dyb:
        edition, table = ref.split("/table")
        return template.format(edition=edition, table=table)
    if provider == Provider.oecd:
        _, cause = ref.split("/")
        return template.format(cause=cause)
    return template.format(ref=ref)


def _entity_public_dict(entity) -> dict:
    return {
        "entity_id": entity.entity_id,
        "label": entity.label,
        "iso3": entity.iso3,
        "valid_from": entity.valid_from,
        "valid_to": entity.valid_to,
        "predecessor": entity.predecessor,
        "successors": entity.successors,
        "formerly_part_of": (
            {
                "union_entity_id": entity.formerly_part_of.union_entity_id,
                "until_year": entity.formerly_part_of.until_year,
                "note": entity.formerly_part_of.note,
            }
            if entity.formerly_part_of
            else None
        ),
    }


def build_indicator_file(indicator: Indicator, processed_dir: Path, dist_dir: Path) -> dict:
    merged_path = processed_dir / f"{indicator.id}.merged.json"
    points = json.loads(merged_path.read_text(encoding="utf-8"))
    witnesses_path = processed_dir / f"{indicator.id}.witnesses.json"
    raw_witnesses = json.loads(witnesses_path.read_text(encoding="utf-8")) if witnesses_path.exists() else []

    sources_meta = _sources_meta(indicator, _load_footnotes(processed_dir, indicator.id))
    native_unit_by_ref = {(s["provider"], s["source_ref"]): s["native_unit"] for s in sources_meta}

    def _point_dict(p: dict) -> dict:
        # Canonical points carry their own provider/source_ref (multi-source
        # by construction); witness points don't (they inherit from the
        # series) — hence the .get()s.
        out = {
            "entity_id": p["entity_id"],
            "year": p["year"],
            "value": p["value"],
            **({"provider": p["provider"]} if p.get("provider") else {}),
            **({"source_ref": p["source_ref"]} if p.get("source_ref") else {}),
        }
        if p.get("citation"):
            out["citation"] = p["citation"]
        if p.get("definition_note"):
            out["definition_note"] = p["definition_note"]
        # Demographic breakdown when the source prints one (DYB Table 4:
        # male/female life expectancy) — omitted for plain points so the
        # dist stays clean for the (still sex-less) majority.
        if p.get("sex"):
            out["sex"] = p["sex"]
        # The collector's own quality annotations (P2), as-reported: the
        # code legend that decodes them ships per source (sources[].footnotes).
        if p.get("quality_code"):
            out["quality_code"] = p["quality_code"]
        if p.get("footnote_refs"):
            out["footnote_refs"] = p["footnote_refs"]
        if p.get("reference_range"):
            out["reference_range"] = p["reference_range"]
        if p.get("missing_marker"):
            out["missing_marker"] = p["missing_marker"]
        if p.get("provisional"):
            out["provisional"] = True
        return out

    witnesses_payload = [
        {
            "provider": w["provider"],
            "source_ref": w["source_ref"],
            "layer": PROVIDER_LAYER[Provider(w["provider"])],
            "unit": indicator.unit,  # witness data is converted into the canonical unit
            "native_unit": native_unit_by_ref.get((w["provider"], w["source_ref"])),
            # P2: the citation block on the WITNESS series too (they were the
            # review's gap) — same generator as sources[], so no drift risk.
            "citation": _source_citation(Provider(w["provider"]), w["source_ref"]),
            "url": _source_url(Provider(w["provider"]), w["source_ref"]),  # witness entries mirror sources[] (field-agnostic URL)
            "license": PROVIDER_LICENSE[Provider(w["provider"])],
            "n_points": len(w["data"]),
            "data": [_point_dict(p) for p in w["data"]],
        }
        for w in raw_witnesses
    ]

    # Restrict each source's footnote block to the refs the emitted points
    # (canonical + witness) actually carry.
    _join_footnotes(sources_meta, points, witnesses_payload)

    payload = {
        "id": indicator.id,
        "label": indicator.label,
        "family": indicator.family.value,
        "unit": indicator.unit,
        "higher_is_better": indicator.higher_is_better,
        "todd_core": indicator.todd_core,
        "reliability": indicator.reliability.value,
        "reliability_criteria": indicator.reliability_criteria,
        "reclassification_sensitive": indicator.reclassification_sensitive,
        "coverage_declared": {"start": indicator.coverage_start, "end": indicator.coverage_end},
        "license": indicator.license,
        "notes": indicator.notes,
        "sources": sources_meta,
        "data": [_point_dict(p) for p in points],
        "witnesses": witnesses_payload,
    }

    out_dir = dist_dir / "indicators"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{indicator.id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _sources_meta(indicator: Indicator, footnotes_by_source: dict | None) -> list[dict]:
    """One entry per declared source: role/layer/native_unit (v7) + the P2
    citation block (citation/url/license) + the footnote legend and the
    texts of the refs the emitted points actually carry (see _join_footnotes)."""
    meta = []
    for s in indicator.sources_by_priority():
        entry = {
            "provider": s.provider.value,
            "source_ref": s.ref,
            "role": s.role.value,
            "layer": PROVIDER_LAYER[s.provider],
            # Native unit of the source's raw values (None = canonical unit);
            # every emitted value was converted into the canonical `unit`.
            "native_unit": s.unit,
            # P2: the citation block the external review asked for — on
            # WITNESS sources too (they were the gap), on every source.
            "citation": _source_citation(s.provider, s.ref),
            "url": _source_url(s.provider, s.ref, field=s.field),
            "license": PROVIDER_LICENSE[s.provider],
        }
        meta.append(entry)
    if footnotes_by_source:
        for entry in meta:
            block = footnotes_by_source.get(f"{entry['provider']}:{entry['source_ref']}")
            if block:
                entry["footnotes"] = block
    return meta


def _load_footnotes(processed_dir: Path, indicator_id: str) -> dict:
    """{indicator}.footnotes.json -> {"provider:ref": {"legend": ..., "notes": ...}}
    (written by normalize since P2); {} when absent (e.g. an old processed
    tree built before P2 — the citation block then ships without the
    footnote texts, honestly absent rather than invented)."""
    path = processed_dir / f"{indicator_id}.footnotes.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _referenced_refs(points: list[dict]) -> set[tuple[str, str, str]]:
    """{(provider, source_ref, footnote ref)} for every emitted point that
    carries refs — the join key for the per-source note texts."""
    referenced = set()
    for p in points:
        for ref in p.get("footnote_refs") or ():
            referenced.add((p["provider"], p["source_ref"], ref))
    return referenced


def _join_footnotes(sources_meta: list[dict], points: list[dict], witnesses: list[dict]) -> None:
    """Restricts each source's footnotes block to the refs its emitted points
    actually carry (canonical + witness) — the texts ride with the data, but
    only the ones that matter for THIS build. A referenced ref with no text in
    the snapshot's notes is kept as a null and logged: an honest gap, never a
    silent drop."""
    referenced = _referenced_refs(points)
    for w in witnesses:
        referenced |= _referenced_refs(w.get("data", []))
    for entry in sources_meta:
        block = entry.get("footnotes")
        if not block:
            continue
        provider, ref = entry["provider"], entry["source_ref"]
        wanted = sorted({r for (p, s, r) in referenced if p == provider and s == ref})
        if not wanted:
            entry.pop("footnotes", None)  # no emitted point uses this source's notes
            continue
        notes = block.get("notes", {})
        joined = {}
        for r in wanted:
            if r in notes:
                joined[r] = notes[r]
            else:
                joined[r] = None
                logger.warning(
                    "%s:%s carries footnote ref %r but the snapshot's Footnotes sheet has no such note — "
                    "kept as an explicit null (the text lives only in the source file).",
                    provider, ref, r,
                )
        entry["footnotes"] = {"legend": block.get("legend", {}), "notes": joined}


def build_catalog(indicators: dict[str, Indicator], built_payloads: dict[str, dict], dist_dir: Path) -> None:
    catalog = [
        {
            "id": ind.id,
            "label": ind.label,
            "family": ind.family.value,
            "unit": ind.unit,
            "higher_is_better": ind.higher_is_better,
            "todd_core": ind.todd_core,
            "reliability": ind.reliability.value,
            "reliability_criteria": ind.reliability_criteria,
            "reclassification_sensitive": ind.reclassification_sensitive,
            "license": ind.license,
            "n_points": len(built_payloads[ind.id]["data"]),
            "n_witness_points": sum(len(w["data"]) for w in built_payloads[ind.id]["witnesses"]),
        }
        for ind in sorted(indicators.values(), key=lambda i: i.id)
    ]
    (dist_dir / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")


def build_entities(entities: EntityRegistry, dist_dir: Path) -> None:
    payload = [_entity_public_dict(e) for e in entities.entities]
    (dist_dir / "entities.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_all(indicators: dict[str, Indicator], processed_dir: Path, dist_dir: Path, entities: EntityRegistry) -> None:
    dist_dir.mkdir(parents=True, exist_ok=True)
    built = {ind.id: build_indicator_file(ind, processed_dir, dist_dir) for ind in indicators.values()}
    build_catalog(indicators, built, dist_dir)
    build_entities(entities, dist_dir)
