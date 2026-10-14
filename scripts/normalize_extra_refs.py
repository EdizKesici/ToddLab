#!/usr/bin/env python3
"""normalize_extra_refs: extra_core.csv -> config/extra_refs.yaml (one-way).

The sibling of normalize_todd_refs.py for the metrics outside Todd's books:

    extra_core.csv  --(this script)-->  config/extra_refs.yaml  --(build)-->  dist/extra_corpus.json

The CSV layout is `id,label,family,notes` (todd_core.csv minus `book` and
`citation_count`): ONE row per metric. The output is deterministic (metrics
sorted by id) and carries the CSV's SHA-256, so a regeneration is tied to the
exact CSV vintage.

    python scripts/normalize_extra_refs.py --csv extra_core.csv

Validations (fail loudly): required columns present, ids unique and
snake_case, label / family / notes non-empty.
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
DEFAULT_CSV = REPO_ROOT / "extra_core.csv"
DEFAULT_OUT = REPO_ROOT / "config" / "extra_refs.yaml"
_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def normalize(csv_path: Path) -> dict:
    csv_bytes = csv_path.read_bytes()
    reader = csv.DictReader(csv_bytes.decode("utf-8").splitlines())
    required = ["id", "label", "family", "notes"]
    missing = [c for c in required if c not in (reader.fieldnames or [])]
    if missing:
        raise ValueError(f"CSV is missing column(s) {missing}: layout change?")

    metrics: dict[str, dict] = {}
    n_rows = 0
    for lineno, row in enumerate(reader, start=2):
        rid = (row.get("id") or "").strip()
        if not rid:
            continue  # trailing blank line
        n_rows += 1
        if not _ID_RE.match(rid):
            raise ValueError(f"row {lineno}: id {rid!r} is not snake_case")
        if rid in metrics:
            raise ValueError(f"row {lineno}: duplicate id {rid!r} (one row per metric)")
        entry = {k: (row.get(k) or "").strip() for k in ("label", "family")}
        entry["note"] = (row.get("notes") or "").strip()
        empty = [k for k, v in entry.items() if not v]
        if empty:
            raise ValueError(f"row {lineno} ({rid}): empty {empty}")
        metrics[rid] = entry
    if not metrics:
        raise ValueError("CSV yielded zero metrics: wrong file?")
    return {
        "meta": {
            "source_csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
            "rows": n_rows,
            "metrics": len(metrics),
        },
        "metrics": dict(sorted(metrics.items())),
    }


_HEADER = """\
# config/extra_refs.yaml - GENERATED, do not edit by hand.
#
# Source: extra_core.csv (the metrics outside Todd's books, one row per
# metric). The CSV is the source of truth; this file is the one-way
# transform the pipeline reads. Regenerate after any CSV change:
#
#     python scripts/normalize_extra_refs.py --csv extra_core.csv
#
# Same CSV bytes -> same YAML bytes (deterministic); meta.source_csv_sha256
# ties this file to the exact CSV vintage. Implemented-ness is derived from
# config/indicators/*.yaml at build time, never stored here.
"""


def dump_yaml(payload: dict) -> str:
    body = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, default_flow_style=False, width=100)
    return _HEADER + "\n" + body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help=f"extra_core.csv (default: {DEFAULT_CSV})")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output YAML (default: {DEFAULT_OUT})")
    parser.add_argument("--dry-run", action="store_true", help="validate and print the summary without writing")
    args = parser.parse_args(argv)
    if not args.csv.is_file():
        print(f"CSV not found: {args.csv}", file=sys.stderr)
        return 2
    try:
        payload = normalize(args.csv)
    except ValueError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    m = payload["meta"]
    print(f"{m['metrics']} metrics (sha256 {m['source_csv_sha256'][:12]}...)")
    if args.dry_run:
        return 0
    args.out.write_text(dump_yaml(payload), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
