"""Schema for config/score.yaml — the v27 score layer's own contract.

WHAT THIS FILE MODELS
The score layer is the project's FIRST AND ONLY derived product (ADR-0011):
two composite scores per country-year — "official" (canonical-tier sources)
and "modelled" (widest-coverage single source) — built ON TOP of the frozen
indicator dist, never inside it. The three prohibitions stand at the
indicator layer; the score layer DERIVES, openly, from what the indicators
measured. This schema is what the pipeline validates config/score.yaml
against — the same fail-loudly contract as every other config.

The config is DECLARATIVE INTENT: directions, transforms, sex handling,
which score a component enters, the basis of each value judgment (a
boolean higher_is_better hid them; here `basis` is mandatory and emitted),
and the corpus_metric each component's todd-preset weight reads. The
NUMBERS (bounds, floors, chosen sources) never live here — they are frozen
by scripts/freeze_score_bounds.py into config/score_bounds.yaml so a later
`fetch` cannot move the scale (changing bounds = a deliberate regeneration
plus a bounds_version bump).

House invariants enforced here:
- every component names a KNOWN indicator id (validated at load against
  the indicator registry — see config_loader.cross_validate_score);
- the EXCLUDED ids (decision 7/9: gini_index, the markers, the counts,
  the postponed) are refused loudly, not silently dropped;
- direction/transform pairs must be coherent (target transform rides a
  target direction; log/linear ride higher or lower);
- one entry per indicator — the split-sex components (life expectancy
  pair) are DERIVED from sex_mode, not listed twice.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Direction(str, Enum):
    higher = "higher"
    lower = "lower"
    target = "target"


class Transform(str, Enum):
    linear = "linear"
    log = "log"
    target = "target"


class SexMode(str, Enum):
    both = "both"
    split = "split"


class ScoreName(str, Enum):
    official = "official"
    modelled = "modelled"


class Basis(str, Enum):
    """WHERE the direction judgment comes from — emitted with every
    component so the frontend renders the value judgment, not hides it
    (todd = the corpus's own usage; consensus = the field's agreement;
    editorial = this project's judgment, Ediz's to reverse)."""

    todd = "todd"
    consensus = "consensus"
    editorial = "editorial"


# Decision 7/9: the ids that must NEVER appear as score components.
# gini_index: removed from the score only (double counting with
#   top_income_share over the shared survey universe — it stays an
#   indicator, todd_core true, in the catalog and on the site);
# maternal_deaths: a count, the RATIO is the component;
# the markers, male_height_trend, consanguineous_marriage_rate,
#   crude_birth_rate, road_accident_mortality (per capita), and the
#   postponed illegitimate_births: out by earlier decisions;
# immigration_stock / agricultural_employment_share: withdrawn in v26.
EXCLUDED_INDICATORS: frozenset[str] = frozenset(
    {
        "gini_index",
        "maternal_deaths",
        "same_sex_marriage",
        "universal_suffrage",
        "male_height_trend",
        "consanguineous_marriage_rate",
        "crude_birth_rate",
        "road_accident_mortality",
        "illegitimate_births",
        "immigration_stock",
        "agricultural_employment_share",
    }
)


class ScoreComponent(BaseModel):
    indicator: str = Field(..., min_length=1)
    direction: Direction
    transform: Transform
    sex_mode: SexMode
    scores: list[ScoreName] = Field(..., min_length=1)
    basis: Basis
    provisional: bool = False
    corpus_metric: str | None = None

    @model_validator(mode="after")
    def _coherent(self) -> "ScoreComponent":
        if self.transform == Transform.target and self.direction != Direction.target:
            raise ValueError(
                f"{self.indicator}: transform 'target' rides direction 'target' only "
                "(the fertility distance form)"
            )
        if self.direction == Direction.target and self.transform != Transform.target:
            raise ValueError(
                f"{self.indicator}: direction 'target' requires transform 'target'"
            )
        if self.sex_mode == SexMode.split and self.direction == Direction.target:
            raise ValueError(
                f"{self.indicator}: a target direction has no split-sex face"
            )
        return self


class ScoreConfig(BaseModel):
    version: str = Field(..., min_length=1)
    bounds_from_year: int = Field(1990, ge=1800, le=2100)
    percentiles: list[float] = Field([0.01, 0.99], min_length=2, max_length=2)
    coverage_threshold: float = Field(0.60, gt=0, le=1)
    delta_min_common_weight: float = Field(0.50, gt=0, le=1)
    fertility_target: float = Field(2.1, gt=0)
    rounding: int = Field(2, ge=0, le=6)
    presets: list[str] = Field(..., min_length=1)
    components: list[ScoreComponent] = Field(..., min_length=1)

    @field_validator("percentiles")
    @classmethod
    def _ordered_percentiles(cls, v: list[float]) -> list[float]:
        lo, hi = v
        if not 0 < lo < hi < 1:
            raise ValueError(f"percentiles must satisfy 0 < p1 < p2 < 1, got {v}")
        return v

    @model_validator(mode="after")
    def _unique_indicators(self) -> "ScoreConfig":
        seen: dict[str, int] = {}
        for c in self.components:
            seen[c.indicator] = seen.get(c.indicator, 0) + 1
            if c.indicator in EXCLUDED_INDICATORS:
                raise ValueError(
                    f"{c.indicator} is EXCLUDED from the score by decision 7/9 — "
                    "remove the component (the exclusion is deliberate, never silent)"
                )
        dups = sorted(k for k, n in seen.items() if n > 1)
        if dups:
            raise ValueError(f"duplicate score components: {dups}")
        unknown_presets = sorted(set(self.presets) - {"equal", "todd"})
        if unknown_presets:
            raise ValueError(
                f"unknown presets {unknown_presets} — the layer computes 'equal' and "
                "'todd' only (custom weights are the frontend's job, per the contract)"
            )
        return self

    def components_for(self, score: ScoreName) -> list[ScoreComponent]:
        return [c for c in self.components if score in c.scores]
