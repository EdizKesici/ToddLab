#!/usr/bin/env python3
"""normalize_todd_refs: todd_core.csv -> config/todd_refs.yaml (one-way).

WHAT THIS SCRIPT IS
The Todd corpus (Ediz's OCR mega-compilation of every metric Todd uses,
one row per metric x book with a citation count) enters the repo as a
GENERATED config file — the CSV itself stays outside the repo as the
source of truth and is never modified by this project. The transform is
strictly one-way:

    todd_core.csv  --(this script)-->  config/todd_refs.yaml  --(build)-->  dist

Regenerate whenever the CSV changes upstream (a new book OCR'd, a citation
count corrected):

    python scripts/normalize_todd_refs.py --csv /path/to/todd_core.csv

The output is DETERMINISTIC: same CSV bytes -> same YAML bytes (metrics
ranked by total citations desc then id; refs chronological by book year).
The YAML carries the source CSV's SHA-256 in its meta block so a regen
can be tied to the exact upstream vintage.

DELIBERATELY IGNORED CSV columns:
- `status` ("not_implemented"): implemented-ness is the REPO's own state,
  derived by cross-validation against config/indicators/*.yaml (see
  src/config_loader.cross_validate_todd_core) — a stale flag in the CSV
  must never override the config's own truth.

VALIDATIONS (fail loudly, never silently mangle):
- unique (id, book) pairs — a duplicate row is an upstream OCR artifact
  that must be resolved in the CSV, not averaged here;
- citation_count a non-negative integer;
- book year parseable as "(YYYY)" or "(YYYY/YYYY)" — anything else is a
  layout surprise worth a human look;
- one family per metric, resolved as the citation-weighted MAJORITY (the
  compilation labels a handful of rows by book context — e.g.
  consanguineous_marriage_rate is 'demography' in Le Destin des immigrés
  but 'society' everywhere else; the majority keeps the label stable
  while the regen output prints the disagreement). An exact tie refuses
  to pick a side.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "config" / "todd_refs.yaml"

_BOOK_RE = re.compile(r"^(?P<book>.+?)\s+\((?P<year>\d{4})(?:/(?P<year_end>\d{4}))?\)$")


def parse_book(raw: str) -> tuple[str, int, str | None]:
    """'La Chute finale (1976/1990)' -> ('La Chute finale', 1976, '1976/1990').

    The bare year is the sortable/display int; year_raw keeps the original
    parenthetical when it is not a plain year (the one 1976/1990 dual-
    edition case). Raises ValueError on anything unparseable."""
    match = _BOOK_RE.match(raw.strip())
    if not match:
        raise ValueError(f"book {raw!r} does not end in a (YYYY) or (YYYY/YYYY) year")
    year = int(match["year"])
    year_raw = None
    if match["year_end"]:
        year_raw = f"{match['year']}/{match['year_end']}"
    return match["book"].strip(), year, year_raw


def normalize(csv_path: Path) -> tuple[dict, list[str]]:
    """The pure transform: CSV path -> (todd_refs.yaml payload, family
    disagreement notes for the regen output)."""
    csv_bytes = csv_path.read_bytes()
    text = csv_bytes.decode("utf-8")
    reader = csv.DictReader(text.splitlines())
    required = ["id", "label", "family", "book", "citation_count", "status", "notes"]
    missing = [c for c in required if c not in (reader.fieldnames or [])]
    if missing:
        raise ValueError(f"CSV is missing column(s) {missing}: layout change upstream?")

    metrics: dict[str, dict] = {}
    families_by_metric: dict[str, dict[str, int]] = {}  # id -> {family: citations}
    seen_pairs: dict[tuple[str, str], int] = {}
    n_rows = 0
    for lineno, row in enumerate(reader, start=2):  # 2 = first data row under the header
        rid = (row.get("id") or "").strip()
        if not rid:
            continue  # a trailing blank line, not a record
        n_rows += 1
        book_name, year, year_raw = parse_book(row["book"])
        pair = (rid, book_name)
        if pair in seen_pairs:
            raise ValueError(
                f"row {lineno}: duplicate (id, book) pair {pair!r} — resolve the duplicate "
                "in the CSV (an OCR artifact), do not regenerate over it."
            )
        seen_pairs[pair] = lineno

        citations_raw = (row.get("citation_count") or "").strip()
        if not re.fullmatch(r"\d+", citations_raw):
            raise ValueError(f"row {lineno}: citation_count {citations_raw!r} is not a non-negative integer")
        note = (row.get("notes") or "").strip()

        ref = {
            "book": book_name,
            "year": year,
            "citations": int(citations_raw),
            "label": (row.get("label") or "").strip(),
            "note": note,
        }
        if year_raw:
            ref["year_raw"] = year_raw

        family = (row.get("family") or "").strip()
        metric = metrics.setdefault(rid, {"family": family, "refs": []})
        families_by_metric.setdefault(rid, {})[family] = (
            families_by_metric.setdefault(rid, {}).get(family, 0) + int(citations_raw)
        )
        metric["refs"].append(ref)

    if not metrics:
        raise ValueError("CSV yielded zero metrics: wrong file?")

    # The family resolution: citation-weighted majority per metric (an
    # exact tie refuses to pick a side); disagreements are PRINTED at
    # regen so the disagreement itself stays visible to the operator.
    disagreements: list[str] = []
    for rid, fams in families_by_metric.items():
        if len(fams) > 1:
            disagreements.append(
                f"{rid}: " + ", ".join(f"{f} ({c} cits)" for f, c in sorted(fams.items(), key=lambda kv: -kv[1]))
            )
        best = max(fams.items(), key=lambda kv: (kv[1], kv[0]))
        runners_up = {f: c for f, c in fams.items() if f != best[0]}
        if runners_up and max(runners_up.values()) == best[1]:
            raise ValueError(
                f"metric {rid!r} has a family tie {fams} — the majority rule refuses to "
                "pick a side; resolve it in the CSV."
            )
        metrics[rid]["family"] = best[0]

    # Deterministic ordering: the backlog reads by citation weight; refs
    # read chronologically (the corpus's own history).
    for metric in metrics.values():
        metric["refs"].sort(key=lambda r: (r["year"], r["book"]))
    ranked = sorted(
        metrics.items(),
        key=lambda kv: (-sum(r["citations"] for r in kv[1]["refs"]), kv[0]),
    )

    books = {(r["book"], r["year"]) for m in metrics.values() for r in m["refs"]}
    payload = {
        "meta": {
            "source_csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
            "rows": n_rows,
            "metrics": len(metrics),
            "books": len(books),
            "total_citations": sum(r["citations"] for m in metrics.values() for r in m["refs"]),
        },
        "metrics": dict(ranked),
    }
    return payload, disagreements


_HEADER = """\
# config/todd_refs.yaml — GENERATED, do not edit by hand.
#
# Source: todd_core.csv (Ediz's OCR compilation of the metrics Todd uses,
# one row per metric x book, citation-counted across 16 books). The CSV is
# the source of truth and lives OUTSIDE the repo; this file is the one-way
# transform the pipeline reads. Regenerate after any CSV change:
#
#     python scripts/normalize_todd_refs.py --csv <path>/todd_core.csv
#
# Same CSV bytes -> same YAML bytes (deterministic); meta.source_csv_sha256
# ties this file to the exact upstream vintage. The CSV's own `status`
# column is deliberately ignored: implemented-ness is derived from
# config/indicators/*.yaml by cross-validation at config load, never
# carried stale from the compilation.
"""


def dump_yaml(payload: dict) -> str:
    """Deterministic YAML text: header comment + block-style body."""
    body = yaml.safe_dump(
        payload,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=100,
    )
    return _HEADER + "\n" + body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", required=True, type=Path, help="path to todd_core.csv (read-only)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output YAML (default: {DEFAULT_OUT})")
    parser.add_argument("--dry-run", action="store_true", help="validate the CSV and print the summary without writing")
    args = parser.parse_args(argv)

    if not args.csv.is_file():
        print(f"ERROR: CSV not found: {args.csv}", file=sys.stderr)
        return 1
    try:
        payload, disagreements = normalize(args.csv)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if disagreements:
        print("family disagreements resolved by citation majority:")
        for d in disagreements:
            print(f"  - {d}")

    meta = payload["meta"]
    print(
        f"OK: {meta['rows']} rows -> {meta['metrics']} metrics, {meta['books']} books, "
        f"{meta['total_citations']} citations (sha256 {meta['source_csv_sha256'][:12]}...)"
    )
    if args.dry_run:
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(dump_yaml(payload), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
