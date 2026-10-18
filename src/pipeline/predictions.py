"""Todd's predictions, published for the website.

`docs/todd_predictions.md` is the single source: one row per prediction, one
section of the table per book, every citation checked against the books. The
website shows only a short list per book (the prediction and a verdict symbol),
so this module reads the table, validates it against the figures the document
announces in its own header, and writes `dist/predictions.json`.

Fail loudly: a table that drifts from its header (a deleted row whose counts
were not updated, a renumbering hole, an unknown verdict symbol, a book that
comes back after another one) stops the build instead of publishing a list
that disagrees with the document.
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import re
from pathlib import Path

from src.config_loader import ConfigError

SOURCE_NAME = "docs/todd_predictions.md"
TRANSLATIONS_NAME = "catalog/curated/todd_predictions_fr.csv"

COLUMNS = (
    "#",
    "Book",
    "Chapter",
    "Prediction",
    "Outcome",
    "Verdict",
    "Citation",
    "Citation_translation",
)

VERDICTS = {"✅": "verified", "🟡": "partial", "❌": "not_realized"}

_UNESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|~<>$])")
_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")
_BOOK = re.compile(r"^(?P<title>.+) \((?P<year>\d{4}(?:/\d{4})?)\)$")


def _clean(cell: str) -> str:
    """A table cell as plain text: markdown escapes removed, spaces trimmed."""
    return _UNESCAPE.sub(r"\1", cell.strip())


def _split_row(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return [c.strip() for c in _UNESCAPED_PIPE.split(body)]


def _table_lines(text: str) -> list[str]:
    """The lines of the main table: the first block of `|` lines after the
    `## Table` heading."""
    lines = text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == "## Table")
    except StopIteration as e:
        raise ConfigError(f"{SOURCE_NAME}: no '## Table' section") from e
    block: list[str] = []
    for ln in lines[start + 1 :]:
        if ln.lstrip().startswith("|"):
            block.append(ln)
        elif block:
            break
    if len(block) < 3:
        raise ConfigError(f"{SOURCE_NAME}: the table under '## Table' is empty")
    return block


def _announced(text: str) -> tuple[int, int, dict[str, int], dict[str, int]]:
    """The figures the header announces: (predictions, books, per-book counts,
    verdict counts). The table below must reproduce them."""
    m = re.search(r"^(\d+) predictions from (\d+) books", text, re.M)
    if not m:
        raise ConfigError(f"{SOURCE_NAME}: header lacks the 'N predictions from M books' line")
    per_book: dict[str, int] = {}
    scope = re.search(r"^\| Book \| Predictions \|\n\| --- \| --- \|\n((?:\|.*\|\n?)+)", text, re.M)
    if not scope:
        raise ConfigError(f"{SOURCE_NAME}: header lacks the per-book scope table")
    for ln in scope.group(1).splitlines():
        cells = _split_row(ln)
        per_book[_clean(cells[0])] = int(cells[1])
    v = re.search(r"^Verdicts: ✅ (\d+), 🟡 (\d+), ❌ (\d+)\.", text, re.M)
    if not v:
        raise ConfigError(f"{SOURCE_NAME}: header lacks the 'Verdicts:' line")
    verdicts = {"verified": int(v.group(1)), "partial": int(v.group(2)), "not_realized": int(v.group(3))}
    return int(m.group(1)), int(m.group(2)), per_book, verdicts


def parse_predictions(text: str) -> dict:
    """Parse and validate the markdown. Returns the payload of
    `dist/predictions.json` (without the source hash, added by the caller)."""
    table = _table_lines(text)
    header = [_clean(c) for c in _split_row(table[0])]
    expected = [_clean(c) for c in COLUMNS]
    if header != expected:
        raise ConfigError(f"{SOURCE_NAME}: table columns {header} != {expected}")

    books: list[dict] = []
    seen_books: set[str] = set()
    n_total = 0
    verdict_counts = {k: 0 for k in VERDICTS.values()}

    for ln in table[2:]:
        cells = _split_row(ln)
        if len(cells) != len(COLUMNS):
            raise ConfigError(f"{SOURCE_NAME}: row with {len(cells)} cells, expected {len(COLUMNS)}: {ln[:80]}")
        number, label, _chapter, prediction, _outcome, verdict = (_clean(c) for c in cells[:6])
        n_total += 1
        if number != str(n_total):
            raise ConfigError(f"{SOURCE_NAME}: row numbered {number!r} where {n_total} was expected")
        if verdict not in VERDICTS:
            raise ConfigError(f"{SOURCE_NAME}: row {number}: unknown verdict {verdict!r}")
        if not prediction:
            raise ConfigError(f"{SOURCE_NAME}: row {number}: empty prediction")
        m = _BOOK.match(label)
        if not m:
            raise ConfigError(f"{SOURCE_NAME}: row {number}: book {label!r} is not 'Title (year)'")
        if not books or books[-1]["label"] != label:
            if label in seen_books:
                raise ConfigError(f"{SOURCE_NAME}: row {number}: book {label!r} comes back after another book")
            seen_books.add(label)
            books.append({"label": label, "title": m.group("title"), "year": m.group("year"), "predictions": []})
        key = VERDICTS[verdict]
        verdict_counts[key] += 1
        books[-1]["predictions"].append({"text": prediction, "verdict": key})

    n_head, books_head, per_book_head, verdicts_head = _announced(text)
    per_book = {b["label"]: len(b["predictions"]) for b in books}
    problems = []
    if n_head != n_total:
        problems.append(f"header announces {n_head} predictions, the table has {n_total}")
    if books_head != len(books):
        problems.append(f"header announces {books_head} books, the table has {len(books)}")
    if per_book_head != per_book:
        problems.append(f"per-book counts differ: header {per_book_head} vs table {per_book}")
    if verdicts_head != verdict_counts:
        problems.append(f"verdict counts differ: header {verdicts_head} vs table {verdict_counts}")
    if problems:
        raise ConfigError(f"{SOURCE_NAME}: " + "; ".join(problems))

    return {
        "meta": {"n_predictions": n_total, "n_books": len(books), "verdicts": verdict_counts},
        "books": books,
    }


def load_translations(path: Path) -> dict[str, str]:
    """French wording of the predictions, keyed by the exact English text of
    the table (the site shows it to French readers; the book titles stay as
    printed). A malformed file is refused."""
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ["prediction", "prediction_fr"]:
            raise ConfigError(f"{TRANSLATIONS_NAME}: columns {reader.fieldnames} != ['prediction', 'prediction_fr']")
        out: dict[str, str] = {}
        for row in reader:
            en, fr = row["prediction"].strip(), row["prediction_fr"].strip()
            if not en or not fr:
                raise ConfigError(f"{TRANSLATIONS_NAME}: empty cell in the row for {en or fr!r}")
            if en in out:
                raise ConfigError(f"{TRANSLATIONS_NAME}: duplicate prediction {en!r}")
            out[en] = fr
    return out


def build_predictions(md_path: Path, dist_dir: Path, translations_path: Path | None = None) -> dict:
    """Write dist/predictions.json from the markdown; returns the payload.

    Each prediction carries `text_fr` (null when the translation file has no
    row for that exact English text: the site then falls back to English, and
    the build logs the gap)."""
    raw = md_path.read_bytes()
    payload = parse_predictions(raw.decode("utf-8"))
    translations = load_translations(translations_path) if translations_path else {}
    used: set[str] = set()
    for book in payload["books"]:
        for p in book["predictions"]:
            fr = translations.get(p["text"])
            if fr is not None:
                used.add(p["text"])
            p["text_fr"] = fr
    if translations_path:
        missing = [p["text"] for b in payload["books"] for p in b["predictions"] if p["text_fr"] is None]
        stale = sorted(set(translations) - used)
        if missing:
            logging.warning("%d prediction(s) without a French translation in %s, first: %r", len(missing), TRANSLATIONS_NAME, missing[0])
        if stale:
            logging.warning("%d translation(s) in %s match no prediction (reworded?), first: %r", len(stale), TRANSLATIONS_NAME, stale[0])
    payload = {
        "source": (
            f"{SOURCE_NAME}: Todd's predictions, one row per prediction, citations checked "
            "against the books. The list keeps the prediction and a verdict symbol; the "
            "outcomes and verdicts are drafts assessed from a 2026 vantage point."
        ),
        "meta": {"source_sha256": hashlib.sha256(raw).hexdigest(), **payload["meta"]},
        "books": payload["books"],
    }
    (dist_dir / "predictions.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return payload
