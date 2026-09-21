"""todd_refs (v13): the corpus as first-class metadata — normalizer, schema,
cross-validation.

The corpus enters the repo through scripts/normalize_todd_refs.py (the
one-way transform from Ediz's todd_core.csv — the CSV stays outside the
repo, untouched). These tests pin the transform's contract:
- determinism (same CSV bytes -> same YAML bytes, ordering included);
- the loud failures (duplicate metric x book rows, family ties, bad book
  years, non-integer citation counts);
- the family majority rule (the compilation labels a handful of rows by
  book context — the metric-level family is the citation-weighted
  majority, and the disagreement is REPORTED, not buried);
- the CSV's `status` column is ignored (implemented-ness is the repo's
  own state — the bijection tests below enforce it from the configs).

The tests build their own miniature CSVs (tmp_path): the miniatures carry
synthetic book names and counts BY DESIGN (fixture rules) — the committed
config/todd_refs.yaml is what integration tests read, and its own numbers
are asserted in test_pipeline_integration (from the built dist, never from
these fixtures).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from normalize_todd_refs import dump_yaml, normalize, parse_book  # noqa: E402

from src.config_loader import ConfigError, cross_validate_todd_core, load_todd_refs
from src.schema.todd_refs import ToddCorpus
from tests.conftest import CONFIG_DIR


MINI_CSV = """id,label,family,book,citation_count,status,notes
suicide_rate,"Suicide rate per 100,000",mortality,Le Livre A (1980),12,not_implemented,"Series X."
suicide_rate,Suicide rate,mortality,Le Livre B (1990),8,not_implemented,"Series Y."
infant_mortality,Infant mortality,mortality,Le Livre A (1980),5,not_implemented,"Series Z."
consanguineous_marriage_rate,Rate,society,Livre C (2000),3,not_implemented,"Mostly society."
consanguineous_marriage_rate,Rate,demography,Livre D (2010),1,not_implemented,"One demography row."
birth_rate_fertility,Fertility,society,Livre E (2020),3,not_implemented,"Note."
birth_rate_fertility,Fertility,demography,Livre F (2021),1,not_implemented,"Note."
"""


def _write_mini_csv(tmp_path: Path, content: str = MINI_CSV) -> Path:
    path = tmp_path / "todd_core_mini.csv"
    path.write_text(content, encoding="utf-8")
    return path


# --- parse_book -----------------------------------------------------------


def test_parse_book_extracts_year_and_keeps_dual_edition_raw():
    book, year, year_raw = parse_book("La Chute finale (1976/1990)")
    assert (book, year, year_raw) == ("La Chute finale", 1976, "1976/1990")
    book, year, year_raw = parse_book("Où en sommes-nous ? (2017)")
    assert (book, year, year_raw) == ("Où en sommes-nous ?", 2017, None)


def test_parse_book_refuses_years_it_cannot_parse():
    with pytest.raises(ValueError, match="does not end in a"):
        parse_book("Le Livre sans année")


# --- normalize ------------------------------------------------------------


def test_normalize_counts_ranks_and_ignores_the_status_column(tmp_path):
    payload, disagreements = normalize(_write_mini_csv(tmp_path))
    assert payload["meta"]["rows"] == 7
    assert payload["meta"]["metrics"] == 4
    assert payload["meta"]["books"] == 6
    assert payload["meta"]["total_citations"] == 33
    # the CSV's status column is deliberately not carried anywhere
    dumped = dump_yaml(payload)
    assert "not_implemented" not in dumped
    # ranking: citations desc, then id asc
    assert list(payload["metrics"]) == [
        "suicide_rate",          # 20
        "infant_mortality",      # 5
        "birth_rate_fertility",  # 4 -- tie with consanguineous, id breaks it
        "consanguineous_marriage_rate",  # 4
    ]
    # refs chronological within a metric
    assert [r["book"] for r in payload["metrics"]["suicide_rate"]["refs"]] == ["Le Livre A", "Le Livre B"]


def test_normalize_reports_family_disagreements_and_resolves_by_majority(tmp_path):
    payload, disagreements = normalize(_write_mini_csv(tmp_path))
    # two metrics disagree: consanguineous (3 society vs 1 demography) and
    # birth_rate (3 society vs 1 demography)
    assert len(disagreements) == 2
    assert payload["metrics"]["consanguineous_marriage_rate"]["family"] == "society"
    assert payload["metrics"]["birth_rate_fertility"]["family"] == "society"


def test_normalize_refuses_a_family_tie(tmp_path):
    # birth_rate sits at society 3 / demography 1; rebalance to 1/1 -> the
    # majority rule must refuse to pick a side.
    content = MINI_CSV.replace(
        "birth_rate_fertility,Fertility,society,Livre E (2020),3",
        "birth_rate_fertility,Fertility,society,Livre E (2020),1",
    )
    with pytest.raises(ValueError, match="family tie"):
        normalize(_write_mini_csv(tmp_path, content))


def test_normalize_refuses_duplicate_metric_book_rows(tmp_path):
    content = MINI_CSV + "suicide_rate,Suicide rate,mortality,Le Livre A (1980),1,not_implemented,Dup.\n"
    with pytest.raises(ValueError, match="duplicate \\(id, book\\) pair"):
        normalize(_write_mini_csv(tmp_path, content))


def test_normalize_refuses_non_integer_citation_counts(tmp_path):
    content = MINI_CSV.replace(",12,not_implemented,", ",many,not_implemented,",
    )
    with pytest.raises(ValueError, match="not a non-negative integer"):
        normalize(_write_mini_csv(tmp_path, content))


def test_normalize_output_is_deterministic(tmp_path):
    csv_path = _write_mini_csv(tmp_path)
    payload1, _ = normalize(csv_path)
    payload2, _ = normalize(csv_path)
    assert dump_yaml(payload1) == dump_yaml(payload2)
    # and the payload validates against the repo schema
    ToddCorpus.model_validate(payload1)


# --- the committed corpus ---------------------------------------------------


def test_the_committed_corpus_loads_and_its_meta_agrees():
    corpus = load_todd_refs(CONFIG_DIR)
    assert corpus is not None
    assert corpus.meta.metrics == 24
    assert corpus.meta.rows == 117
    assert corpus.meta.books == 16
    assert corpus.meta.total_citations == sum(m.citations_total for m in corpus.metrics.values())
    # the corpus's own #1 is the unimplemented fertility metric
    first = next(iter(corpus.metrics.values()))
    assert first.citations_total == max(m.citations_total for m in corpus.metrics.values())


def test_load_todd_refs_absent_file_is_none_not_an_error(tmp_path):
    assert load_todd_refs(tmp_path) is None


def test_corpus_schema_refuses_a_meta_that_disagrees_with_the_body():
    with pytest.raises(Exception, match="regenerate"):
        ToddCorpus.model_validate(
            {
                "meta": {
                    "source_csv_sha256": "a" * 64,
                    "rows": 5,
                    "metrics": 2,
                    "books": 2,
                    "total_citations": 999,  # disagrees with the refs below
                },
                "metrics": {
                    "suicide_rate": {
                        "family": "mortality",
                        "refs": [{"book": "B", "year": 1980, "citations": 1, "label": "l", "note": "n"}],
                    }
                },
            }
        )


# --- cross-validation (the todd_core flag becomes evidence-backed) ---------


def _mini_corpus() -> ToddCorpus:
    return ToddCorpus.model_validate(
        {
            "meta": {
                "source_csv_sha256": "b" * 64,
                "rows": 2,
                "metrics": 2,
                "books": 2,
                "total_citations": 3,
            },
            "metrics": {
                "infant_mortality": {
                    "family": "mortality",
                    "refs": [{"book": "B1", "year": 1980, "citations": 2, "label": "l", "note": "n"}],
                },
                "suicide_rate": {
                    "family": "mortality",
                    "refs": [{"book": "B2", "year": 1990, "citations": 1, "label": "l", "note": "n"}],
                },
            },
        }
    )


def test_cross_validation_passes_on_the_real_config(real_indicators):
    corpus = load_todd_refs(CONFIG_DIR)
    cross_validate_todd_core(real_indicators, corpus)  # no raise = pass


def test_cross_validation_is_a_noop_without_a_corpus(real_indicators):
    cross_validate_todd_core(real_indicators, None)  # pre-v13 behavior


def test_cross_validation_refuses_an_unsupported_todd_core_flag(real_indicators):
    corpus = _mini_corpus()  # carries infant_mortality + suicide_rate only
    # life_expectancy is flagged todd_core=true but has no corpus entry here
    with pytest.raises(ConfigError, match="life_expectancy: todd_core=true but the corpus"):
        cross_validate_todd_core(real_indicators, corpus)


def test_cross_validation_refuses_a_corpus_metric_marked_extra_only(real_indicators):
    corpus = _mini_corpus()
    # maternal_mortality_ratio is todd_core=false; pretend the corpus carries it
    corpus.metrics["maternal_mortality_ratio"] = corpus.metrics["suicide_rate"].model_copy(deep=True)
    with pytest.raises(ConfigError, match="maternal_mortality_ratio: the corpus carries this metric"):
        cross_validate_todd_core(real_indicators, corpus)


# --- v16: the companion_indicators symmetry contract -------------------------

from src.config_loader import cross_validate_companions  # noqa: E402


def test_companion_symmetry_passes_on_the_real_config(real_indicators):
    # v16: the TFR/CBR pair is declared on BOTH sides — the v15 review's
    # asymmetry (crude_birth_rate pointing at birth_rate_fertility, the
    # TFR carrying []) repaired; the guard now keeps it that way.
    cross_validate_companions(real_indicators)  # no raise = pass


def test_companion_symmetry_refuses_a_one_way_declaration(real_indicators):
    # The exact v15 shape: crude_birth_rate -> birth_rate_fertility with
    # nothing coming back (the TFR carrying the honest empty list) — the
    # loud failure the guard exists for.
    indicators = dict(real_indicators)
    indicators["birth_rate_fertility"] = indicators["birth_rate_fertility"].model_copy(
        update={"companion_indicators": []}
    )
    with pytest.raises(ConfigError, match="ONE-WAY.*does not list crude_birth_rate back"):
        cross_validate_companions(indicators)


def test_companion_symmetry_refuses_an_unknown_companion_id(real_indicators):
    indicators = dict(real_indicators)
    indicators["birth_rate_fertility"] = indicators["birth_rate_fertility"].model_copy(
        update={"companion_indicators": ["crude_birth_rate", "nonexistent_metric"]}
    )
    with pytest.raises(ConfigError, match="names 'nonexistent_metric', but no indicator"):
        cross_validate_companions(indicators)


def test_companion_symmetry_refuses_self_reference_and_duplicates(real_indicators):
    self_ref = dict(real_indicators)
    self_ref["birth_rate_fertility"] = self_ref["birth_rate_fertility"].model_copy(
        update={"companion_indicators": ["crude_birth_rate", "birth_rate_fertility"]}
    )
    with pytest.raises(ConfigError, match="lists itself as a companion"):
        cross_validate_companions(self_ref)

    duplicated = dict(real_indicators)
    duplicated["crude_birth_rate"] = duplicated["crude_birth_rate"].model_copy(
        update={"companion_indicators": ["birth_rate_fertility", "birth_rate_fertility"]}
    )
    with pytest.raises(ConfigError, match="lists 'birth_rate_fertility' twice"):
        cross_validate_companions(duplicated)
