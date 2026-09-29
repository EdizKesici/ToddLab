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
    ILOSTAT_DATAFLOW_TITLES,
    EUROSTAT_DATASET_TITLES,
    IDD_DEFINITION_LABELS,
    OECD_DATAFLOW_TITLES,
    PROVIDER_CITATION,
    PROVIDER_LAYER,
    PROVIDER_LICENSE,
    ROOT_LABELS,
    Indicator,
    Provider,
)
from src.schema.todd_refs import ToddCorpus

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
    if provider == Provider.who_gho:
        from src.connectors.gho import build_url as gho_build_url  # idem

        return gho_build_url(ref)
    if provider == Provider.worldbank:
        from src.connectors.worldbank import build_url as wb_build_url  # idem

        return wb_build_url(ref)
    if provider == Provider.ilostat:
        from src.connectors.ilostat import build_url as ilo_build_url  # idem

        return ilo_build_url(ref)
    # NOTE (v25): eurostat sources intentionally keep url=None here — the
    # pre-v25 dists never carried a Eurostat URL, and wiring one now would
    # touch every Eurostat-sourced indicator's dist file (a cross-cutting
    # change this version refuses to smuggle in; recorded in the v25
    # changelog's known limitations as its own reviewable decision).
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
        # v19: the connector speaks THREE dataflows — the citation
        # dispatches per flow (the same one-flow-one-title rule the
        # Eurostat titles follow). DF_COM keeps its v10 template
        # verbatim (bit-compat with every pre-v19 dist).
        parts = ref.split("/")
        flow = parts[0]
        if flow == "DF_IDD":
            _, measure, methodology, definition = parts
            return (
                f"OECD, {OECD_DATAFLOW_TITLES['DF_IDD']} (DSD_WISE_IDD@DF_IDD), "
                f"measure '{measure}', {methodology}, "
                f"{IDD_DEFINITION_LABELS[definition]} - national household "
                "surveys as submitted"
            )
        if flow == "DF_SAFETY":
            _, measure, unit = parts
            return (
                f"OECD/ITF, {OECD_DATAFLOW_TITLES['DF_SAFETY']} "
                f"(DSD_INDICATORS@DF_SAFETY), measure '{measure}', unit {unit} - "
                "IRTAD road crash registrations as submitted"
            )
        if flow == "DF_MIG_POPF":
            # v22: the migration questionnaire's foreign-born matrix — the
            # bare-flow ref (the empty-key /all download), the bilateral
            # witness of immigration_stock.
            return (
                f"OECD, {OECD_DATAFLOW_TITLES['DF_MIG_POPF']} (DSD_MIG_F@DF_MIG_POPF), "
                "the foreign-born stock by country of birth - the migration "
                "questionnaire's answers as submitted, OECD-compiled"
            )
        if flow == "DF_MIG":
            # v23: the SAME questionnaire's citizenship matrix — the keyed
            # wildcard download (measure B15), the bilateral witness of the
            # by-citizenship face.
            return (
                f"OECD, {OECD_DATAFLOW_TITLES['DF_MIG']} (DSD_MIG@DF_MIG), "
                "the stock of foreign population by nationality (measure B15) - "
                "the migration questionnaire's answers as submitted, OECD-compiled"
            )
        return template.format(cause=parts[1])
    if provider == Provider.eurostat:
        # 'demo_find/TOTFERRT' (all countries) or 'demo_find/TOTFERRT/FR'
        # (the geo-pinned variant-series door) — the optional third part is
        # the geo code, named in the citation so the two French series stay
        # distinguishable where a reader meets them (dist sources block).
        # v17: the dataset's own API title rides the citation (one
        # questionnaire, one title — une_rt_a is the labour-force
        # collection, never 'Fertility indicators').
        parts = ref.split("/")
        title = EUROSTAT_DATASET_TITLES[parts[0]]
        if len(parts) == 3 and parts[1] == "ROW":
            # v22/v23: the bilateral ROW doors — 'migr_pop3ctb/ROW/FR' (the
            # by-origin row of one destination, c_birth open) and
            # 'migr_pop1ctz/ROW/FR' (the by-citizenship twin, citizen open):
            # geo named so the doors stay distinguishable in the sources
            # block, the axis named so the two faces read as what they are.
            axis = "by-origin (c_birth)" if parts[0] == "migr_pop3ctb" else "by-citizenship (citizen)"
            return (
                f"{template.format(title=title, dataset=parts[0], code='ROW')}, "
                f"the {axis} row of geo {parts[2]}"
            )
        if len(parts) == 3:
            return f"{template.format(title=title, dataset=parts[0], code=parts[1])}, geo {parts[2]}"
        if len(parts) == 2 and parts[0] in ("lfsa_urgan", "lfsa_urgacob"):
            # v25: the class-decomposition twins — 'lfsa_urgan/Y15-74/T'
            # (age/sex pins, the class dimension open): the axis named so
            # the two faces read as what they are, the pins named so the
            # door stays distinguishable from its M/F siblings.
            axis = "by citizenship (citizen open)" if parts[0] == "lfsa_urgan" else "by country of birth (c_birth open)"
            return (
                f"{template.format(title=title, dataset=parts[0], code=parts[1])}, "
                f"the class decomposition {axis}"
            )
        return template.format(title=title, dataset=parts[0], code=parts[1])
    if provider == Provider.ilostat:
        # v25: the bare-flow refs — the ILO's own SDMX wire, the flow's own
        # registry title riding the citation (one-flow-one-title).
        return template.format(
            title=ILOSTAT_DATAFLOW_TITLES[ref], flow=ref
        )
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


def build_indicator_file(
    indicator: Indicator,
    processed_dir: Path,
    dist_dir: Path,
    todd_refs: ToddCorpus | None = None,
) -> dict:
    merged_path = processed_dir / f"{indicator.id}.merged.json"
    points = json.loads(merged_path.read_text(encoding="utf-8"))
    witnesses_path = processed_dir / f"{indicator.id}.witnesses.json"
    raw_witnesses = json.loads(witnesses_path.read_text(encoding="utf-8")) if witnesses_path.exists() else []

    sources_meta = _sources_meta(indicator, _load_footnotes(processed_dir, indicator.id))
    native_unit_by_ref = {(s["provider"], s["source_ref"]): s["native_unit"] for s in sources_meta}
    root_by_ref = {(s["provider"], s["source_ref"]): s["root"] for s in sources_meta}

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
        # Table 17's "\u2666" marker: ratio based on 30 or fewer maternal
        # deaths — same as-reported transport as `provisional`.
        if p.get("small_base"):
            out["small_base"] = True
        return out

    def _bilateral_point_dict(p: dict) -> dict:
        """v22: the by-origin layer's own point shape — the destination named
        EXPLICITLY (destination_entity_id) so the two axes never read as one
        field with different meanings, the origin beside it, then the same
        conditional annotation transport as the single-axis face (the
        bilateral doors print quality codes and provisional flags, nothing
        else)."""
        out = {
            "destination_entity_id": p["entity_id"],
            "origin_entity_id": p["origin_entity_id"],
            "year": p["year"],
            "value": p["value"],
            **({"provider": p["provider"]} if p.get("provider") else {}),
            **({"source_ref": p["source_ref"]} if p.get("source_ref") else {}),
        }
        if p.get("sex"):
            out["sex"] = p["sex"]
        if p.get("quality_code"):
            out["quality_code"] = p["quality_code"]
        if p.get("provisional"):
            out["provisional"] = True
        return out

    def _segment_point_dict(p: dict) -> dict:
        """v25: the population-segment layer's own point shape — the class
        named EXPLICITLY (population_class, the layer-scoped project
        vocabulary: natives/foreign_born/eu_born/non_eu_born on the birth
        face, nationals/foreigners/eu_foreigners/non_eu_foreigners on the
        citizenship face), then the same conditional annotation transport
        as the other faces (the class doors print quality codes, nothing
        else). The entity stays entity_id — a segment point is one
        country's own rate on one of ITS population segments."""
        out = {
            "entity_id": p["entity_id"],
            "population_class": p["population_class"],
            "year": p["year"],
            "value": p["value"],
            **({"provider": p["provider"]} if p.get("provider") else {}),
            **({"source_ref": p["source_ref"]} if p.get("source_ref") else {}),
        }
        if p.get("sex"):
            out["sex"] = p["sex"]
        if p.get("quality_code"):
            out["quality_code"] = p["quality_code"]
        if p.get("provisional"):
            out["provisional"] = True
        return out

    witnesses_payload = [
        {
            "provider": w["provider"],
            "source_ref": w["source_ref"],
            "layer": PROVIDER_LAYER[Provider(w["provider"])],
            # Root genealogy (v11): the ultimate origin this witness
            # redistributes — the field that makes "three providers, one
            # root" (the IGME triangle) a machine-checkable claim instead
            # of a doc's assertion.
            "root": root_by_ref[(w["provider"], w["source_ref"])],
            "root_label": ROOT_LABELS[root_by_ref[(w["provider"], w["source_ref"])]],
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

    # v22 (the bilateral face) / v23 (the citizenship face): each by-origin
    # FACE rides BESIDE the single-axis data/witnesses — its own data
    # (destination x origin x year) and its own witness series. ADDITIVE by
    # construction: each layer is emitted ONLY when the processed tree
    # carries that layer's points (merge_indicator writes the pair exactly
    # then, and unlinks stale copies otherwise), so every single-axis
    # indicator's dist file stays byte-identical — no key, no change. The
    # two faces are PARALLEL, never merged (ADR-0010): `bilateral` = the
    # place-of-birth legality (immigrés), `bilateral_citizenship` = the
    # legal face (étrangers).
    def _bilateral_layer_payload(merged_path: Path) -> dict | None:
        if not merged_path.exists():
            return None
        b_points = json.loads(merged_path.read_text(encoding="utf-8"))
        b_witnesses_path = merged_path.parent / merged_path.name.replace(".merged.json", ".witnesses.json")
        raw_b_witnesses = (
            json.loads(b_witnesses_path.read_text(encoding="utf-8")) if b_witnesses_path.exists() else []
        )
        return {
            "data": [_bilateral_point_dict(p) for p in b_points],
            "witnesses": [
                {
                    "provider": bw["provider"],
                    "source_ref": bw["source_ref"],
                    "layer": PROVIDER_LAYER[Provider(bw["provider"])],
                    "root": root_by_ref[(bw["provider"], bw["source_ref"])],
                    "root_label": ROOT_LABELS[root_by_ref[(bw["provider"], bw["source_ref"])]],
                    "unit": indicator.unit,
                    "native_unit": native_unit_by_ref.get((bw["provider"], bw["source_ref"])),
                    "citation": _source_citation(Provider(bw["provider"]), bw["source_ref"]),
                    "url": _source_url(Provider(bw["provider"]), bw["source_ref"]),
                    "license": PROVIDER_LICENSE[Provider(bw["provider"])],
                    "n_points": len(bw["data"]),
                    "data": [_bilateral_point_dict(p) for p in bw["data"]],
                }
                for bw in raw_b_witnesses
            ],
        }

    bilateral_payload = _bilateral_layer_payload(
        processed_dir / f"{indicator.id}.bilateral.merged.json"
    )
    bilateral_citizenship_payload = _bilateral_layer_payload(
        processed_dir / f"{indicator.id}.bilateral_citizenship.merged.json"
    )

    # v25 (the population-segment face): the same ADDITIVE-by-construction
    # emission for the two CLASS faces — each rides BESIDE the single-axis
    # data/witnesses and the bilateral faces with its own data
    # (entity x class x year) and its own witness series, emitted ONLY when
    # the processed tree carries that layer's points. The two faces are
    # PARALLEL (ADR-0010): `segments` = the birth-axis classes (immigrés),
    # `segments_citizenship` = the legal classes (étrangers) — never merged,
    # never arbitrated across, the class vocabularies layer-scoped.
    def _segments_layer_payload(merged_path: Path) -> dict | None:
        if not merged_path.exists():
            return None
        s_points = json.loads(merged_path.read_text(encoding="utf-8"))
        s_witnesses_path = merged_path.parent / merged_path.name.replace(".merged.json", ".witnesses.json")
        raw_s_witnesses = (
            json.loads(s_witnesses_path.read_text(encoding="utf-8")) if s_witnesses_path.exists() else []
        )
        return {
            "data": [_segment_point_dict(p) for p in s_points],
            "witnesses": [
                {
                    "provider": sw["provider"],
                    "source_ref": sw["source_ref"],
                    "layer": PROVIDER_LAYER[Provider(sw["provider"])],
                    "root": root_by_ref[(sw["provider"], sw["source_ref"])],
                    "root_label": ROOT_LABELS[root_by_ref[(sw["provider"], sw["source_ref"])]],
                    "unit": indicator.unit,
                    "native_unit": native_unit_by_ref.get((sw["provider"], sw["source_ref"])),
                    "citation": _source_citation(Provider(sw["provider"]), sw["source_ref"]),
                    "url": _source_url(Provider(sw["provider"]), sw["source_ref"]),
                    "license": PROVIDER_LICENSE[Provider(sw["provider"])],
                    "n_points": len(sw["data"]),
                    "data": [_segment_point_dict(p) for p in sw["data"]],
                }
                for sw in raw_s_witnesses
            ],
        }

    segments_payload = _segments_layer_payload(
        processed_dir / f"{indicator.id}.segments.merged.json"
    )
    segments_citizenship_payload = _segments_layer_payload(
        processed_dir / f"{indicator.id}.segments_citizenship.merged.json"
    )

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
        # v15: the companion link (crude_birth_rate <-> birth_rate_fertility)
        # — the explicit statement that two indicators read the same
        # demographic phenomenon through DIFFERENT measures (TFR vs CBR),
        # never a unit conversion of one another. Emitted as [] for every
        # companion-less indicator (the honest empty list, not an absent
        # key: the frontend can read one field uniformly).
        "companion_indicators": indicator.companion_indicators,
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
    # v22 (the bilateral face): the by-origin layer — ADDITIVE, emitted only
    # when the indicator's processed tree carries it (see above). The field
    # name is the dist contract's own vocabulary: destination_entity_id x
    # origin_entity_id x year, the shape of Todd's boards.
    # v23 (the citizenship face): the PARALLEL twin — `bilateral_citizenship`,
    # the same point shape on the legal axis (ADR-0010: never merged with
    # the birth face, never arbitrated across).
    if bilateral_payload is not None:
        payload["bilateral"] = bilateral_payload
    if bilateral_citizenship_payload is not None:
        payload["bilateral_citizenship"] = bilateral_citizenship_payload
    # v25 (the population-segment faces): ADDITIVE, the same rule — emitted
    # only when the indicator's processed tree carries the layer. The field
    # names are the dist contract's own vocabulary: `segments` (the birth
    # classes — natives/foreign_born/eu_born/non_eu_born) and
    # `segments_citizenship` (the legal classes — nationals/foreigners/
    # eu_foreigners/non_eu_foreigners), the shape of Le Destin des
    # immigrés' own étrangers/immigrés boards.
    if segments_payload is not None:
        payload["segments"] = segments_payload
    if segments_citizenship_payload is not None:
        payload["segments_citizenship"] = segments_citizenship_payload
    # v13 (todd_refs): the corpus entry joins BY ID — when the indicator
    # implements a corpus metric, the "why this metric exists" block rides
    # with the data (books, citations, per-book usage). Absent corpus or no
    # matching metric -> no key (honest absence; the cross-validation in
    # config_loader guarantees todd_core=true indicators always find one).
    if todd_refs is not None and indicator.id in todd_refs.metrics:
        payload["todd_refs"] = todd_refs.metrics[indicator.id].public_dict()

    out_dir = dist_dir / "indicators"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{indicator.id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _sources_meta(indicator: Indicator, footnotes_by_source: dict | None) -> list[dict]:
    """One entry per declared source: role/layer/native_unit (v7) + the P2
    citation block (citation/url/license) + the v11 root genealogy + the
    footnote legend and the texts of the refs the emitted points actually
    carry (see _join_footnotes)."""
    meta = []
    for s in indicator.sources_by_priority():
        entry = {
            "provider": s.provider.value,
            "source_ref": s.ref,
            "role": s.role.value,
            "layer": PROVIDER_LAYER[s.provider],
            # Root genealogy (v11): see ROOT_LABELS — the ultimate origin this
            # source redistributes (the DYB's 13 editions are 13 DOORS on the
            # unsd_dyb root; OWID/WB/GHO on IMR are 4 doors on un_igme).
            "root": s.root,
            "root_label": ROOT_LABELS[s.root],
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


def _referenced_refs(
    points: list[dict], *, provider: str | None = None, source_ref: str | None = None
) -> set[tuple[str, str, str]]:
    """{(provider, source_ref, footnote ref)} for every emitted point that
    carries refs — the join key for the per-source note texts.

    Canonical points carry their own provider/source_ref keys; WITNESS points
    inherit them from their series (merge.py's witness payload omits them per
    point) — hence the explicit fallback parameters, which must be passed for
    witness data. The audit of the QC/footnote plumbing found the previous
    p["provider"] access would have raised a KeyError the day any witness
    point carried footnote_refs (v9 fix, regression-tested)."""
    referenced = set()
    for p in points:
        for ref in p.get("footnote_refs") or ():
            referenced.add((p.get("provider") or provider, p.get("source_ref") or source_ref, ref))
    return referenced


def _join_footnotes(sources_meta: list[dict], points: list[dict], witnesses: list[dict]) -> None:
    """Restricts each source's footnotes block to the refs its emitted points
    actually carry (canonical + witness) — the texts ride with the data, but
    only the ones that matter for THIS build. A referenced ref with no text in
    the snapshot's notes is kept as a null and logged: an honest gap, never a
    silent drop."""
    referenced = _referenced_refs(points)
    for w in witnesses:
        referenced |= _referenced_refs(
            w.get("data", []), provider=w.get("provider"), source_ref=w.get("source_ref")
        )
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


def _roots_summary(indicator: Indicator) -> dict:
    """Per-role genealogy: which roots back this indicator and through how
    many doors. The point (the-measurement-problem.md section 5.1): an
    indicator whose witnesses agree because they are the SAME root must
    say so — "1 root via 4 doors" — instead of reading like four
    independent confirmations."""
    def _group(role: str) -> list[dict]:
        doors: dict[str, list[str]] = {}
        for s in indicator.sources:
            if s.role.value == role:
                doors.setdefault(s.root, []).append(s.provider.value)
        return [
            {"root": root, "label": ROOT_LABELS[root], "doors": len(provs)}
            for root, provs in sorted(doors.items())
        ]

    return {"canonical": _group("canonical"), "witness": _group("witness")}


def _todd_corpus_payload(indicators: dict[str, Indicator], corpus: ToddCorpus) -> dict:
    """dist/todd_corpus.json: the full compilation — implemented AND
    unimplemented metrics — as the executable roadmap. The ranking is the
    corpus's own (citation-weighted, carried over from the generated
    YAML); `implemented` is derived from the indicator configs, never
    carried stale from the CSV's own status column (the normalizer
    deliberately ignores it)."""
    metrics = [
        {
            "id": mid,
            **metric.public_dict(),
            "implemented": mid in indicators,
        }
        for mid, metric in corpus.metrics.items()  # ranked by citations (generation order)
    ]
    implemented = [m for m in metrics if m["implemented"]]
    return {
        "source": (
            "todd_core.csv (OCR compilation of Todd's metrics, by Ediz) -> "
            "config/todd_refs.yaml (one-way transform, scripts/normalize_todd_refs.py); "
            "meta.source_csv_sha256 anchors this dist to the exact CSV vintage."
        ),
        "meta": {
            **corpus.meta.model_dump(),
            "implemented_metrics": len(implemented),
        },
        "metrics": metrics,
    }


def build_catalog(
    indicators: dict[str, Indicator],
    built_payloads: dict[str, dict],
    dist_dir: Path,
    todd_refs: ToddCorpus | None = None,
) -> None:
    catalog = [
        {
            "id": ind.id,
            "label": ind.label,
            "family": ind.family.value,
            "unit": ind.unit,
            "higher_is_better": ind.higher_is_better,
            "todd_core": ind.todd_core,
            # v15: the companion link on the catalog entry too (the board
            # navigates from the catalog — the TFR/CBR pair must be visible
            # there, one field read uniformly).
            "companion_indicators": ind.companion_indicators,
            "reliability": ind.reliability.value,
            "reliability_criteria": ind.reliability_criteria,
            "reclassification_sensitive": ind.reclassification_sensitive,
            "license": ind.license,
            "roots": _roots_summary(ind),
            "n_points": len(built_payloads[ind.id]["data"]),
            "n_witness_points": sum(len(w["data"]) for w in built_payloads[ind.id]["witnesses"]),
            # v13: the corpus block on the catalog entry too — the frontend
            # renders "why this metric" from the catalog without loading
            # every indicator file.
            **(
                {"todd_refs": todd_refs.metrics[ind.id].public_dict()}
                if todd_refs is not None and ind.id in todd_refs.metrics
                else {}
            ),
        }
        for ind in sorted(indicators.values(), key=lambda i: i.id)
    ]
    (dist_dir / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    if todd_refs is not None:
        (dist_dir / "todd_corpus.json").write_text(
            json.dumps(_todd_corpus_payload(indicators, todd_refs), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def build_entities(entities: EntityRegistry, dist_dir: Path) -> None:
    payload = [_entity_public_dict(e) for e in entities.entities]
    (dist_dir / "entities.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_all(
    indicators: dict[str, Indicator],
    processed_dir: Path,
    dist_dir: Path,
    entities: EntityRegistry,
    todd_refs: ToddCorpus | None = None,
) -> None:
    dist_dir.mkdir(parents=True, exist_ok=True)
    built = {
        ind.id: build_indicator_file(ind, processed_dir, dist_dir, todd_refs=todd_refs)
        for ind in indicators.values()
    }
    build_catalog(indicators, built, dist_dir, todd_refs=todd_refs)
    build_entities(entities, dist_dir)
