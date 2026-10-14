"""Schema for config/extra_refs.yaml: the metrics OUTSIDE Todd's books.

extra_core.csv (repo root) is the source of truth, the sibling of
todd_core.csv: same layout minus the book / citation_count columns (one row
per metric, since there are no books to cite). scripts/normalize_extra_refs.py
turns it, one way, into this generated config; the build reads it to write
dist/extra_corpus.json and config_loader.cross_validate_extra_core enforces
the bijection with the indicators' todd_core flag (an indicator that is not
in Todd's books MUST be listed here, and a listed metric that is an
indicator MUST be flagged todd_core: false).

Like the Todd corpus, it lists implemented AND planned metrics: `implemented`
is derived from config/indicators/*.yaml, never stored.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


class ExtraMetric(BaseModel):
    label: str = Field(..., min_length=1)
    family: str = Field(..., min_length=1)
    note: str = Field(..., min_length=1)

    @field_validator("label", "family", "note", mode="before")
    @classmethod
    def _strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v


class ExtraCorpusMeta(BaseModel):
    source_csv_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    rows: int = Field(..., ge=1)
    metrics: int = Field(..., ge=1)


class ExtraCorpus(BaseModel):
    meta: ExtraCorpusMeta
    metrics: dict[str, ExtraMetric]

    @model_validator(mode="after")
    def _meta_matches_body(self) -> "ExtraCorpus":
        if len(self.metrics) != self.meta.metrics or self.meta.rows != self.meta.metrics:
            raise ValueError(
                f"meta says {self.meta.metrics} metrics / {self.meta.rows} rows but the file "
                f"carries {len(self.metrics)} metrics (one row per metric) - regenerate the "
                "file from extra_core.csv."
            )
        return self
