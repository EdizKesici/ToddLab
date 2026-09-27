"""Dist statistics — the single source of the numbers changelogs quote.

The v9 review taught the project two things about its own bookkeeping.
First, a bare count is not re-verifiable without archaeology when the
canonical tier is multi-provider: "1,419 canonical IMR points" and the
un_dyb-only subset "1,398" describe the same dist depending on whether
the 21 curated USSR points (1970-1990) are included — a provider filter
and a 2007-2024 reference-year window both drop exactly that series.
Second, a "Verified (live)" section is only as good as the bytes it
quotes: the v9 changelog cited "the MMEIG witness carries 5.2" for France
2022, a value that existed nowhere in the fetched data (the witness stops
at 2020 for every entity; France's real last point is 7.91) — the number
had leaked from a TEST FIXTURE (tests/fixtures/owid_maternal_mortality
.csv, "France,FRA,2020,5.2"). Retracted in v9.1.

`cli stats` exists so that every number a future entry cites is emitted by
one command reading the dist files themselves — never memory, never a
fixture. This module READS the built dist; it does not re-derive anything
from the raws (the authoritative replay check remains `cli rebuild` plus
a diff), so it reports what IS, including anything a build shipped.
"""
from __future__ import annotations

import json
from pathlib import Path


def _fmt(n: int) -> str:
    return f"{n:,}"


def _year_range(points: list[dict]) -> str | None:
    years = [p["year"] for p in points]
    if not years:
        return None
    return f"{min(years)}-{max(years)}"


def indicator_line(payload: dict) -> str:
    """The canonical-tier line for one indicator: totals, the per-provider
    split of valued points (each provider with its own year range — the
    split is what makes any recount reconcile), and entity counts that
    distinguish gap-only entities from covered-with-values ones."""
    data = payload["data"]
    valued = [p for p in data if p["value"] is not None]
    gaps = [p for p in data if p["value"] is None]

    by_provider: dict[str, list[dict]] = {}
    for p in valued:
        by_provider.setdefault(p["provider"], []).append(p)
    parts = []
    for provider in sorted(by_provider, key=lambda k: (-len(by_provider[k]), k)):
        pts = by_provider[provider]
        rng = _year_range(pts)
        parts.append(f"{provider} {_fmt(len(pts))} ({rng})" if rng else f"{provider} {_fmt(len(pts))}")
    split = " + ".join(parts) if parts else "none"

    ents_valued = len({p["entity_id"] for p in valued})
    ents_total = len({p["entity_id"] for p in data})
    rng = _year_range(valued)
    line = (
        f"canonical {_fmt(len(data))} points = {_fmt(len(valued))} valued + "
        f"{_fmt(len(gaps))} explicit gaps; valued by provider: {split}"
    )
    if rng:
        line += f"; reference years {rng}"
    line += f"; entities {_fmt(ents_valued)} with >=1 valued point"
    if ents_total != ents_valued:
        line += f" ({_fmt(ents_total)} total incl. gap-only)"
    return line


def _roots_line(payload: dict) -> str:
    """The genealogy line (v11): per role, the roots and the doors — the
    line that answers "how many INDEPENDENT roots back this indicator?"
    at a glance (IMR's four agreeing witnesses are one IGME root seen
    through four doors; the line must say so, or agreement reads like
    confirmation)."""
    by_role: dict[str, dict[str, list[str]]] = {}
    for s in payload.get("sources", []):
        by_role.setdefault(s["role"], {}).setdefault(s["root"], []).append(s["provider"])
    segments = []
    for role in ("canonical", "witness"):
        roots = by_role.get(role)
        if not roots:
            continue
        parts = []
        for root, providers in sorted(roots.items()):
            counts: dict[str, int] = {}
            for p in providers:
                counts[p] = counts.get(p, 0) + 1
            doors = ", ".join(f"{p} x{n}" if n > 1 else p for p, n in sorted(counts.items()))
            parts.append(f"{root} ({doors})" if doors else root)
        segments.append(f"{role}: {' + '.join(parts)}")
    return "roots " + "; ".join(segments)


def _todd_refs_line(payload: dict) -> str | None:
    """The corpus line (v13): how heavily Todd used this metric — the
    citations total and the book count from the todd_refs block, plus the
    heaviest book (the one number that carries the most context for
    "where this metric comes from in Todd's work")."""
    tr = payload.get("todd_refs")
    if not tr:
        return None
    heaviest = max(tr["refs"], key=lambda r: r["citations"])
    line = f"todd refs: {tr['citations']} citations across {tr['books']} book(s)"
    if heaviest["citations"] > 0:
        line += f" (heaviest: {heaviest['book']} {heaviest['year']}, {heaviest['citations']})"
    return line


def _corpus_block(dist_dir: Path) -> list[str]:
    """The closing corpus section (v13), from dist/todd_corpus.json when the
    build carried the compilation: the implemented share of the corpus and
    the citation-weighted backlog — the numbers that make "what to build
    next" a data statement instead of a preference."""
    path = dist_dir / "todd_corpus.json"
    if not path.is_file():
        return []
    corpus = json.loads(path.read_text(encoding="utf-8"))
    meta = corpus["meta"]
    metrics = corpus["metrics"]
    implemented = sorted(
        (m for m in metrics if m["implemented"]), key=lambda m: -m["citations"]
    )
    backlog = sorted((m for m in metrics if not m["implemented"]), key=lambda m: -m["citations"])
    lines = [
        f"todd corpus: {meta['metrics']} metrics, {meta['total_citations']} citations, "
        f"{meta['books']} books (source_csv_sha256 {meta['source_csv_sha256'][:12]}...)"
    ]
    if implemented:
        impl = ", ".join(f"{m['id']} {m['citations']}" for m in implemented)
        lines.append(f"  implemented {len(implemented)}/{meta['metrics']} ({impl})")
    if backlog:
        top = ", ".join(f"{m['id']} {m['citations']}" for m in backlog[:5])
        more = f" (+{len(backlog) - 5} more)" if len(backlog) > 5 else ""
        lines.append(f"  top unimplemented: {top}{more}")
    return lines


def _bilateral_lines(payload: dict) -> list[str]:
    """v22: the by-origin layer's own lines — the canonical matrix's size
    (points, pairs, destinations x origins, the year range — the same
    re-verifiable counts the single-axis line carries, on the layer where
    every point's year is a MEASUREMENT year, never a birth year) and one
    line per bilateral witness (the OECD matrix's world face).
    v23: the citizenship face emits the SAME lines under its own key —
    the two faces print side by side, never blended (ADR-0010)."""
    lines = []
    for layer_key, layer_label in (
        ("bilateral", "bilateral (by-origin)"),
        ("bilateral_citizenship", "bilateral (by-citizenship)"),
    ):
        b = payload.get(layer_key)
        if not b:
            continue
        data = b["data"]
        valued = [p for p in data if p["value"] is not None]
        pairs = {(p["destination_entity_id"], p["origin_entity_id"]) for p in data}
        dests = {p["destination_entity_id"] for p in data}
        origins = {p["origin_entity_id"] for p in data}
        rng = _year_range(data)
        lines.append(
            f"  {layer_label}: {_fmt(len(data))} points = {_fmt(len(valued))} valued + "
            f"{_fmt(len(data) - len(valued))} explicit gaps; {_fmt(len(pairs))} (destination x origin) pairs; "
            f"{_fmt(len(dests))} destinations x {_fmt(len(origins))} distinct origins"
            + (f"; reference years {rng}" if rng else "")
        )
        for w in b.get("witnesses", []):
            wpts = w["data"]
            wrng = _year_range(wpts)
            wdests = len({p["destination_entity_id"] for p in wpts})
            worigins = len({p["origin_entity_id"] for p in wpts})
            wpairs = len({(p["destination_entity_id"], p["origin_entity_id"]) for p in wpts})
            lines.append(
                f"  {layer_label} witness {w['provider']}:{w['source_ref']}: "
                f"{_fmt(len(wpts))} points, {_fmt(wpairs)} pairs, {_fmt(wdests)} destinations, "
                f"{_fmt(worigins)} origins" + (f", {wrng}" if wrng else "")
            )
    return lines


def render_stats(dist_dir: Path) -> str:
    """One canonical line + one line per witness for every indicator file
    in dist/indicators/, sorted by filename. Witness lines carry the
    coverage (points, entities, year range) — the line that makes
    "the witness carries <value> for <year>" claims checkable at a glance.
    v22: indicators carrying a `bilateral` layer get its own lines too —
    the by-origin matrix's counts, canonical and witness. v23: the
    `bilateral_citizenship` face prints its own lines the same way."""
    lines: list[str] = []
    for f in sorted((dist_dir / "indicators").glob("*.json")):
        payload = json.loads(f.read_text(encoding="utf-8"))
        lines.append(f"{f.stem}: {indicator_line(payload)}")
        if payload.get("sources"):
            lines.append(f"  {_roots_line(payload)}")
        todd_line = _todd_refs_line(payload)
        if todd_line:
            lines.append(f"  {todd_line}")
        witnesses = payload.get("witnesses", [])
        for w in witnesses:
            wpts = w["data"]
            wrng = _year_range(wpts)
            wents = len({p["entity_id"] for p in wpts})
            coverage = f", {wrng}" if wrng else ""
            lines.append(
                f"  witness {w['provider']}:{w['source_ref']}: "
                f"{_fmt(len(wpts))} points, {_fmt(wents)} entities{coverage}"
            )
        if not witnesses:
            lines.append("  witnesses: none")
        lines.extend(_bilateral_lines(payload))
    lines.extend(_corpus_block(dist_dir))
    return "\n".join(lines)
