"""Todd's predictions (docs/todd_predictions.md -> dist/predictions.json).

The parser is exercised on a miniature document (synthetic books BY DESIGN:
fixture rules) and on the shipped document, whose numbers are read, never
typed: the shipped test only asserts relations (header = table, books of the
list = books of the Todd corpus, dist = parse of the markdown).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.config_loader import ConfigError
from src.pipeline.predictions import build_predictions, load_translations, parse_predictions

ROOT = Path(__file__).resolve().parent.parent
MD = ROOT / "docs" / "todd_predictions.md"
FR = ROOT / "catalog" / "curated" / "todd_predictions_fr.csv"
DIST = ROOT / "data" / "dist"

ROWS = [
    ("1", "Book A (1980)", "Intro", "First claim", "Done.", "✅", "« a »", "a"),
    ("2", "Book A (1980)", "Intro", "Second \\~claim\\~ with \\[brackets\\]", "Partly.", "🟡", "« b »", "b"),
    ("3", "Book B (1990/2000)", "End", "Third claim", "Missed.", "❌", "« c »", "c"),
]


def _doc(rows=ROWS, *, n=None, books=None, per_book=None, verdicts=None, header=None) -> str:
    n = len(rows) if n is None else n
    per = per_book or {"Book A (1980)": 2, "Book B (1990/2000)": 1}
    verdicts = verdicts or "✅ 1, 🟡 1, ❌ 1"
    cols = header or "| # | Book | Chapter | Prediction | Outcome | Verdict | Citation | Citation\\_translation |"
    scope = "\n".join(f"| {k} | {v} |" for k, v in per.items())
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    return (
        f"# Title\n\n{n} predictions from {books or len(per)} books, in order:\n\n"
        f"| Book | Predictions |\n| --- | --- |\n{scope}\n\nVerdicts: {verdicts.replace(', ', ', ')}.\n\n"
        f"## Legend\n\n- ✅ x\n\n## Table\n\n{cols}\n| --- | --- | --- | --- | --- | --- | --- | --- |\n{body}\n"
    )


def test_parses_books_predictions_and_unescapes_markdown():
    out = parse_predictions(_doc())
    assert out["meta"] == {
        "n_predictions": 3,
        "n_books": 2,
        "verdicts": {"verified": 1, "partial": 1, "not_realized": 1},
    }
    a, b = out["books"]
    assert (a["title"], a["year"], a["label"]) == ("Book A", "1980", "Book A (1980)")
    assert (b["title"], b["year"]) == ("Book B", "1990/2000")
    assert [p["verdict"] for p in a["predictions"]] == ["verified", "partial"]
    # the editor's escapes are plain text in the payload
    assert a["predictions"][1]["text"] == "Second ~claim~ with [brackets]"
    # only the prediction and the verdict are published
    assert set(a["predictions"][0]) == {"text", "verdict"}


@pytest.mark.parametrize(
    "doc, message",
    [
        (_doc(n=4), "announces 4 predictions"),
        (_doc(books=3), "announces 3 books"),
        (_doc(per_book={"Book A (1980)": 1, "Book B (1990/2000)": 2}), "per-book counts differ"),
        (_doc(verdicts="✅ 3, 🟡 0, ❌ 0"), "verdict counts differ"),
        (_doc(header="| # | Book | Chapter | Prediction |"), "table columns"),
        (_doc([ROWS[0], ("3",) + ROWS[1][1:], ROWS[2]]), "where 2 was expected"),
        (_doc([ROWS[0], ROWS[1][:5] + ("?",) + ROWS[1][6:], ROWS[2]]), "unknown verdict"),
        (_doc([ROWS[0], ROWS[1][:3] + ("",) + ROWS[1][4:], ROWS[2]]), "empty prediction"),
        (_doc([ROWS[0], ROWS[1][:1] + ("Book B (1990/2000)",) + ROWS[1][2:], ROWS[2]]), "per-book counts differ"),
        (_doc([ROWS[0], ("2",) + ROWS[2][1:], ("3",) + ROWS[0][1:]]), "comes back"),
        (_doc([ROWS[0], ROWS[1][:1] + ("No year",) + ROWS[1][2:], ROWS[2]]), r"not 'Title \(year\)'"),
        (_doc([ROWS[0], ROWS[1][:-1], ROWS[2]]), "cells, expected 8"),
    ],
)
def test_a_document_that_disagrees_with_its_header_is_refused(doc, message):
    with pytest.raises(ConfigError, match=message):
        parse_predictions(doc)


def test_document_without_a_table_is_refused():
    with pytest.raises(ConfigError, match="no '## Table'"):
        parse_predictions("# Title\n\nnothing\n")


def test_build_writes_the_payload_with_the_source_hash(tmp_path):
    md = tmp_path / "p.md"
    md.write_text(_doc(), encoding="utf-8")
    payload = build_predictions(md, tmp_path)
    written = json.loads((tmp_path / "predictions.json").read_text(encoding="utf-8"))
    assert written == payload
    assert len(written["meta"]["source_sha256"]) == 64
    assert written["books"][0]["predictions"][0] == {"text": "First claim", "verdict": "verified", "text_fr": None}


def test_shipped_document_parses_and_lists_the_books_of_the_todd_corpus():
    out = parse_predictions(MD.read_text(encoding="utf-8"))
    assert out["meta"]["n_predictions"] == sum(len(b["predictions"]) for b in out["books"])
    # owner rule: the corpus keeps exactly the books that have predictions
    corpus = json.loads((DIST / "todd_corpus.json").read_text(encoding="utf-8"))
    corpus_books = {f'{r["book"]} ({r.get("year_raw", r["year"])})' for m in corpus["metrics"] for r in m["refs"]}
    assert {b["label"] for b in out["books"]} == corpus_books
    # books come in chronological order of first publication
    years = [int(b["year"][:4]) for b in out["books"]]
    assert years == sorted(years)


def test_shipped_dist_is_the_parse_of_the_shipped_document():
    published = json.loads((DIST / "predictions.json").read_text(encoding="utf-8"))
    parsed = parse_predictions(MD.read_text(encoding="utf-8"))
    strip = lambda books: [  # noqa: E731 - the French wording is checked separately
        {**b, "predictions": [{k: v for k, v in p.items() if k != "text_fr"} for p in b["predictions"]]} for b in books
    ]
    assert strip(published["books"]) == parsed["books"]
    assert {k: v for k, v in published["meta"].items() if k != "source_sha256"} == parsed["meta"]


def _fr_csv(tmp_path, rows, header="prediction,prediction_fr"):
    path = tmp_path / "fr.csv"
    path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_french_wording_is_attached_by_exact_english_text(tmp_path):
    md = tmp_path / "p.md"
    md.write_text(_doc(), encoding="utf-8")
    fr = _fr_csv(tmp_path, ['First claim,Première affirmation', '"Second ~claim~ with [brackets]","Seconde, avec [crochets]"'])
    payload = build_predictions(md, tmp_path, fr)
    texts = [p["text_fr"] for b in payload["books"] for p in b["predictions"]]
    # a missing translation is published as null (the site falls back to English)
    assert texts == ["Première affirmation", "Seconde, avec [crochets]", None]


@pytest.mark.parametrize(
    "rows, header, message",
    [
        (["a,b"], "x,y", "columns"),
        (["a,"], "prediction,prediction_fr", "empty cell"),
        (["a,b", "a,c"], "prediction,prediction_fr", "duplicate prediction"),
    ],
)
def test_malformed_translation_file_is_refused(tmp_path, rows, header, message):
    with pytest.raises(ConfigError, match=message):
        load_translations(_fr_csv(tmp_path, rows, header))


def test_every_shipped_prediction_has_a_french_wording_and_none_is_stale():
    parsed = parse_predictions(MD.read_text(encoding="utf-8"))
    english = {p["text"] for b in parsed["books"] for p in b["predictions"]}
    french = load_translations(FR)
    assert english - set(french) == set(), "predictions without a French wording"
    assert set(french) - english == set(), "translations that match no prediction (reworded?)"
    assert not any("\u2014" in v or "\u2013" in v for v in french.values()), "no dashes in French copy"
    published = json.loads((DIST / "predictions.json").read_text(encoding="utf-8"))
    assert all(p["text_fr"] for b in published["books"] for p in b["predictions"])
