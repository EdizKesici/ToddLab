"""Curated source connector — the L0-L2 tier (ADR-0007, ADR-0008).

WHAT THIS SOURCE IS
A curated source is a small hand-entered table committed in git under
`catalog/curated/*.csv`, one citation per point, reviewed like code in
pull requests. It exists for exactly the cases where the signal the Todd
method reads lives in an official or scholarly series that NO machine-
readable collector redistributes today (e.g. the official Soviet infant-
mortality series as compiled from TsSU/Goskomstat yearbooks), or where
every harmonized source demonstrably smooths the point away.

THE CURATION GATE (ADR-0007, condition 3) — a point may enter a curated
table only if ALL THREE hold:
(a) a `todd_ref` demands it: the claim the data must carry;
(b) the distortion vs the collector/harmonized layer is demonstrated and
    documented;
(c) a citable source exists for the point (enforced HERE: a row without
    a non-empty `citation` column is a parse error, not a warning).
The gate keeps the curated tier a finite, enumerable, PR-reviewable set —
the anti-bricolage guarantee. Series-level context (who compiled it, how
it was cross-checked) lives in `catalog/curated/README.md`.

FILE FORMAT (declared by ADR-0007, validated strictly here):
    entity_id,year,value,citation,definition_note
- `entity_id` is OUR canonical id (not a source name): curated tables are
  written by us, on purpose, so resolution happens by exact id in
  normalize.py. A typo surfaces in {indicator}.unresolved.json like any
  other source — curated does not get silent forgiveness.
- `value` must be non-empty: in a curated table a gap is an ABSENT ROW,
  never an empty cell (we only enter points we can cite).
- duplicate (entity_id, year) rows are a parse error: the table must be
  arbitration-free by construction.

`source_ref` format: the CSV file name without extension, e.g.
"ussr_infant_mortality_official" -> catalog/curated/ussr_infant_mortality_official.csv.

This connector performs NO network access: "fetching" a curated source is
reading a committed file. It still flows through the same raw-snapshot
path as every other source (fetch.py -> data/raw/curated/{indicator}/
{source_ref}/{timestamp}.json), so normalize/merge/build treat it
uniformly and a rebuild replays from the snapshot exactly like the
network sources.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

from src.connectors.base import Connector, RawFetchResult, RawRecord

DEFAULT_CATALOG_DIR = Path(__file__).resolve().parents[2] / "catalog" / "curated"

REQUIRED_COLUMNS = ["entity_id", "year", "value", "citation", "definition_note"]

_FORBIDDEN_IN_REF = ("/", "\\", "..")


def _validate_source_ref(source_ref: str) -> None:
    """A curated source_ref is a bare file name: path separators or traversal
    fragments mean config confusion, and must fail loudly here rather than
    read an unintended file."""
    for fragment in _FORBIDDEN_IN_REF:
        if fragment in source_ref:
            raise ValueError(
                f"Invalid curated source_ref {source_ref!r}: expected a bare CSV name "
                "(e.g. 'ussr_infant_mortality_official'), no path fragments."
            )


def parse_curated_csv(text: str) -> list[RawRecord]:
    """Pure function: CSV text -> RawRecords. Strict by design — this file
    format is OURS, so any deviation is a bug in the catalog, not a surprise
    from an external layout. Fails loudly with the offending line number."""
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != REQUIRED_COLUMNS:
        raise ValueError(
            f"Curated CSV header must be exactly {REQUIRED_COLUMNS}, got {reader.fieldnames!r}"
        )

    records: list[RawRecord] = []
    seen: set[tuple[str, int]] = set()
    for line_no, row in enumerate(reader, start=2):  # line 1 is the header
        where = f"line {line_no}"
        entity_id = (row.get("entity_id") or "").strip()
        year_raw = (row.get("year") or "").strip()
        value_raw = (row.get("value") or "").strip()
        citation = (row.get("citation") or "").strip()
        definition_note = (row.get("definition_note") or "").strip()

        if not entity_id:
            raise ValueError(f"{where}: empty entity_id in curated CSV")
        try:
            year = int(year_raw)
        except ValueError:
            raise ValueError(f"{where}: year {year_raw!r} is not an integer") from None
        if not value_raw:
            raise ValueError(
                f"{where}: empty value in curated CSV — a curated gap is an ABSENT row, "
                "never an empty cell (we only enter points we can cite)"
            )
        try:
            value = float(value_raw)
        except ValueError:
            raise ValueError(f"{where}: value {value_raw!r} is not a number") from None
        if not citation:
            raise ValueError(
                f"{where}: empty citation in curated CSV — curation gate condition (c) "
                "(ADR-0007): no citable source, no entry"
            )

        key = (entity_id, year)
        if key in seen:
            raise ValueError(
                f"{where}: duplicate ({entity_id}, {year}) in curated CSV — "
                "the curated tier must be arbitration-free by construction"
            )
        seen.add(key)

        records.append(
            RawRecord(
                entity_raw_name=entity_id,
                iso3_raw=None,
                year=year,
                value=value,
                citation=citation,
                definition_note=definition_note or None,
            )
        )

    if not records:
        raise ValueError("Curated CSV has a valid header but no data rows")
    return records


class CuratedConnector(Connector):
    provider = "curated"

    def __init__(self, catalog_dir: Path | None = None):
        self._catalog_dir = Path(catalog_dir) if catalog_dir else DEFAULT_CATALOG_DIR

    def fetch_raw(self, source_ref: str, indicator_id: str, field: str | None = None) -> RawFetchResult:
        if field is not None:
            raise ValueError(
                f"Curated source {source_ref!r} does not support field selection "
                "(a curated CSV carries exactly one value column)."
            )
        _validate_source_ref(source_ref)
        path = self._catalog_dir / f"{source_ref}.csv"
        if not path.is_file():
            raise FileNotFoundError(
                f"Curated table not found: {path} — source_ref '{source_ref}' has no CSV in "
                f"{self._catalog_dir} (create it or fix the indicator config)."
            )
        records = parse_curated_csv(path.read_text(encoding="utf-8"))
        return RawFetchResult(
            provider=self.provider,
            source_ref=source_ref,
            indicator_id=indicator_id,
            fetched_at=RawFetchResult.now_iso(),
            source_url=str(path),
            records=records,
        )
