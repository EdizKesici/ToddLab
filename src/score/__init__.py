"""src/score — the v27 score layer (ADR-0011): the project's first and
only DERIVED product, two composites (official / modelled) built on top
of the frozen indicator dist. Pure functions, no network, no raw tier —
see core.py (the rules) and emit.py (the builder)."""
from src.score.core import (
    ComponentBounds,
    ComponentKey,
    SelectedSource,
    aggregate,
    component_keys,
    compute_bounds,
    delta,
    load_indicator_file,
    normalise_series,
    pct,
    preset_weights,
    score_and_coverage,
    select_source,
)
from src.score.emit import BoundsDriftError, build_score_layer

__all__ = [
    "BoundsDriftError",
    "ComponentBounds",
    "ComponentKey",
    "SelectedSource",
    "aggregate",
    "build_score_layer",
    "component_keys",
    "compute_bounds",
    "delta",
    "load_indicator_file",
    "normalise_series",
    "pct",
    "preset_weights",
    "score_and_coverage",
    "select_source",
]
