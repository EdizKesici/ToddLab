"""Schema for config/todd_refs.yaml — the Todd corpus as first-class metadata.

WHAT THIS FILE MODELS
Ediz's OCR compilation of every metric Todd uses across 16 books (one row
per metric x book, citation-counted) enters the repo as a GENERATED config
(scripts/normalize_todd_refs.py performs the one-way transform from
todd_core.csv; the CSV stays outside as the source of truth). This module
is what the pipeline validates that config against — the same
fail-loudly contract as every other config file.

Two consumers read it downstream:
- build.py attaches `todd_refs` to every indicator whose id matches a
  corpus metric (the "why this metric exists" block: which books, how
  many citations, what usage) and writes the full corpus — implemented
  AND unimplemented metrics — to dist/todd_corpus.json;
- config_loader.cross_validate_todd_core enforces the bijection that
  makes the Indicator.todd_core flag evidence-backed: an indicator
  flagged todd_core=true MUST have a corpus entry (the flag now cites
  its source), and a corpus metric sharing an indicator's id MUST find
  todd_core=true (an implemented corpus metric read as "Extra only"
  would be a config contradiction).

The corpus's own vocabulary (family: society/mortality/economy/
demography/markers/education) is WIDER than the Indicator schema's
Family enum on purpose: the corpus describes 24 metrics, only some of
which are (yet) indicators. The family here is a free string validated
non-empty; narrowing happens when a metric becomes an indicator.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


class ToddRef(BaseModel):
    """One metric x book row of the compilation: where and how heavily
    Todd used the metric. `label` is the usage label of that row (the
    compilation labels per row, e.g. 'Suicide rate per 100,000' vs a
    bare 'Suicide rate'), `note` the row's data description (countries,
    years, sources). `year_raw` keeps the original parenthetical when
    the book year is not a plain YYYY (the 1976/1990 dual edition)."""

    book: str = Field(..., min_length=1)
    year: int = Field(..., ge=1400, le=2100)
    year_raw: str | None = None
    citations: int = Field(..., ge=0)
    label: str
    note: str

    @field_validator("book", "label", "note", mode="before")
    @classmethod
    def _strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v


class ToddMetric(BaseModel):
    family: str = Field(..., min_length=1)
    refs: list[ToddRef] = Field(..., min_length=1)

    @property
    def citations_total(self) -> int:
        return sum(r.citations for r in self.refs)

    @property
    def books_count(self) -> int:
        return len(self.refs)

    def public_dict(self) -> dict:
        """The dist-facing shape: the refs list plus the derived totals
        (citations/books are computed, never stored — a stored total can
        drift from the list it summarizes; a computed one cannot)."""
        return {
            "family": self.family,
            "citations": self.citations_total,
            "books": self.books_count,
            "refs": [r.model_dump(exclude_none=True) for r in self.refs],
        }


class ToddCorpusMeta(BaseModel):
    source_csv_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    rows: int = Field(..., ge=1)
    metrics: int = Field(..., ge=1)
    books: int = Field(..., ge=1)
    total_citations: int = Field(..., ge=0)

    @model_validator(mode="after")
    def _counts_agree(self) -> "ToddCorpusMeta":
        if self.metrics > self.rows:
            raise ValueError("meta: more metrics than rows — a transform bug, not a config")
        return self


class ToddCorpus(BaseModel):
    """The whole generated file: meta + the metrics dict keyed by the
    corpus's metric ids (which the indicator configs join on by name)."""

    meta: ToddCorpusMeta
    metrics: dict[str, ToddMetric]

    @model_validator(mode="after")
    def _meta_matches_body(self) -> "ToddCorpus":
        if len(self.metrics) != self.meta.metrics:
            raise ValueError(
                f"meta says {self.meta.metrics} metrics but the file carries "
                f"{len(self.metrics)} — regenerate the file from the CSV."
            )
        total = sum(m.citations_total for m in self.metrics.values())
        if total != self.meta.total_citations:
            raise ValueError(
                f"meta says {self.meta.total_citations} total citations but the refs "
                f"sum to {total} — regenerate the file from the CSV."
            )
        return self
