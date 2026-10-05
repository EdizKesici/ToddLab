"""Loads and validates config/indicators/*.yaml, config/entities.yaml, config/sources.yaml,
config/todd_refs.yaml, config/score.yaml, config/score_bounds.yaml.

Principle: an invalid config file must fail the build immediately, with a
message pointing at the offending file — never produce a silently
incomplete dist/. Errors from all files are accumulated before raising, so
you don't have to fix-and-rerun one file at a time.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml
from pydantic import ValidationError

from src.schema.entity import Entity, EntityRegistry
from src.schema.indicator import Indicator
from src.schema.score import ScoreConfig, ScoreName
from src.schema.todd_refs import ToddCorpus


class ConfigError(Exception):
    pass


def _load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_indicators(config_dir: Path) -> dict[str, Indicator]:
    indicators_dir = config_dir / "indicators"
    if not indicators_dir.is_dir():
        raise ConfigError(f"Directory not found: {indicators_dir}")

    errors: list[str] = []
    indicators: dict[str, Indicator] = {}

    for path in sorted(indicators_dir.glob("*.yaml")):
        raw = _load_yaml(path)
        try:
            indicator = Indicator.model_validate(raw)
        except ValidationError as e:
            errors.append(f"{path.name}: {e}")
            continue
        if indicator.id != path.stem:
            errors.append(
                f"{path.name}: declared id ('{indicator.id}') does not match the file name ('{path.stem}')"
            )
            continue
        if indicator.id in indicators:
            errors.append(f"{path.name}: id '{indicator.id}' already used by another file")
            continue
        indicators[indicator.id] = indicator

    if errors:
        raise ConfigError("Indicator config errors:\n- " + "\n- ".join(errors))
    return indicators


def load_entities(config_dir: Path) -> EntityRegistry:
    path = config_dir / "entities.yaml"
    raw = _load_yaml(path)
    try:
        return EntityRegistry.from_yaml(raw)
    except ValidationError as e:
        raise ConfigError(f"entities.yaml is invalid:\n{e}") from e


def load_sources(config_dir: Path) -> dict:
    path = config_dir / "sources.yaml"
    return _load_yaml(path)


def load_todd_refs(config_dir: Path) -> ToddCorpus | None:
    """config/todd_refs.yaml -> the validated corpus, or None when the file
    is absent (the mechanism is inert until the compilation arrives: no
    emission, no cross-validation — honest absence, never an invented
    empty corpus). A PRESENT but invalid file raises like any other
    config: a broken corpus must not pass silently because it happens to
    be optional."""
    path = config_dir / "todd_refs.yaml"
    if not path.is_file():
        return None
    raw = _load_yaml(path)
    try:
        return ToddCorpus.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(f"todd_refs.yaml is invalid:\n{e}") from e


def cross_validate_todd_core(indicators: dict[str, Indicator], corpus: ToddCorpus | None) -> None:
    """The bijection that makes the todd_core flag evidence-backed (v13).

    - every indicator flagged todd_core=true MUST have a corpus entry:
      the flag claims "Todd uses this metric" and the compilation is
      where that claim is checked (an unsupported flag fails the build);
    - every corpus metric sharing an indicator id MUST find todd_core=true:
      implementing a corpus metric as "Extra only" is a contradiction
      between two configs, and the louder it fails the better.

    No-op when the corpus is absent (pre-v13 behavior preserved exactly).
    The join is BY ID — the corpus's metric ids and the indicator file
    names must agree for the refs to attach, which is the convention new
    indicators follow (suicide_rate is suicide_rate in both)."""
    if corpus is None:
        return
    errors: list[str] = []
    for iid, ind in indicators.items():
        in_corpus = iid in corpus.metrics
        if ind.todd_core and not in_corpus:
            errors.append(
                f"{iid}: todd_core=true but the corpus (config/todd_refs.yaml) has no metric "
                "with this id — either the flag is wrong or the corpus needs regenerating "
                "from an up-to-date todd_core.csv."
            )
        if in_corpus and not ind.todd_core:
            errors.append(
                f"{iid}: the corpus carries this metric but the indicator is todd_core=false — "
                "an implemented corpus metric is Todd-core by construction; fix the flag."
            )
    if errors:
        raise ConfigError("todd_core/corpus cross-validation errors:\n- " + "\n- ".join(errors))


def cross_validate_companions(indicators: dict[str, Indicator]) -> None:
    """The symmetry contract on companion_indicators (v16).

    A companion link says "two indicators read the same phenomenon
    through DIFFERENT measures, never a unit conversion" — a statement
    about a PAIR, so it is declared on BOTH sides or not at all:
    - every listed companion id must exist (a link to nothing is a typo);
    - every link must be reciprocated (one-way declarations are exactly
      the asymmetry the v15 review caught: crude_birth_rate pointed at
      birth_rate_fertility while the TFR carried the honest empty list);
    - no self-reference, no duplicate entries.

    Empty lists (the companion-less majority) pass untouched — the field
    stays additive and uniform across the dist."""
    errors: list[str] = []
    for iid, ind in indicators.items():
        seen: set[str] = set()
        for companion in ind.companion_indicators:
            if companion == iid:
                errors.append(f"{iid}: lists itself as a companion — the link is between two DIFFERENT indicators.")
                continue
            if companion in seen:
                errors.append(f"{iid}: lists {companion!r} twice — one link per pair.")
                continue
            seen.add(companion)
            other = indicators.get(companion)
            if other is None:
                errors.append(
                    f"{iid}: companion_indicators names {companion!r}, but no indicator with that id "
                    "exists — a link to nothing is a typo, not a witness."
                )
                continue
            if iid not in other.companion_indicators:
                errors.append(
                    f"{iid} -> {companion}: the companion link is ONE-WAY ({companion} does not list "
                    f"{iid} back) — the pair is declared on both sides or not at all."
                )
    if errors:
        raise ConfigError("companion_indicators cross-validation errors:\n- " + "\n- ".join(errors))


# ---------------------------------------------------------------------------
# v27: the score layer's configs — score.yaml (intent) and score_bounds.yaml
# (the frozen numbers). Both are REQUIRED once present: the layer is part
# of the build, and an absent bounds file is a loud failure, never a
# silent recompute (changing bounds = a deliberate regeneration plus a
# bounds_version bump, per ADR-0011).
# ---------------------------------------------------------------------------


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_score_config(config_dir: Path) -> ScoreConfig:
    path = config_dir / "score.yaml"
    if not path.is_file():
        raise ConfigError(
            f"{path} is missing — the score layer is part of the build since v27; "
            "an absent config is a loud failure, never a silently skipped layer."
        )
    raw = _load_yaml(path)
    try:
        return ScoreConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(f"score.yaml is invalid:\n{e}") from e


def load_score_bounds(config_dir: Path) -> dict:
    """The frozen numbers, read raw (deterministic YAML written by
    scripts/freeze_score_bounds.py). Shape:
    meta: {bounds_version, generated, score_config_sha256, ...}
    bounds: {official|modelled: {'indicator/sex': {source, source_class,
    floor, lo, hi, n_sample, bounds_version}}}"""
    path = config_dir / "score_bounds.yaml"
    if not path.is_file():
        raise ConfigError(
            f"{path} is missing — rebuild never recomputes bounds (ADR-0011: a later "
            "fetch must not move the scale). Regenerate deliberately: "
            "python scripts/freeze_score_bounds.py [--dry-run]"
        )
    raw = _load_yaml(path)
    if not isinstance(raw, dict) or "meta" not in raw or "bounds" not in raw:
        raise ConfigError(f"{path}: expected the meta/blocks structure written by freeze_score_bounds.py")
    return raw


def cross_validate_score(
    score: ScoreConfig,
    indicators: dict[str, Indicator],
    corpus: ToddCorpus | None,
) -> None:
    """The score layer's own cross-validations (fail loudly, never silently
    drop a component):

    - every component names a KNOWN indicator (an unknown id is a typo or
      a withdrawn indicator resurrected);
    - every non-null corpus_metric exists in todd_refs (the todd preset's
      book counts read it);
    - the direction agreement (the brief's drift test): for every
      non-target component, higher_is_better == (direction == 'higher')
      — the catalog flag and the score config must never disagree;
      birth_rate_fertility (a target) is the only exclusion;
    - at least one component per declared score (an empty score is a
      config contradiction).
    """
    errors: list[str] = []
    for c in score.components:
        if c.indicator not in indicators:
            errors.append(
                f"score.yaml: component {c.indicator!r} names no indicator in "
                "config/indicators/ — a typo or a withdrawn id resurrected."
            )
            continue
        if c.corpus_metric and (corpus is None or c.corpus_metric not in corpus.metrics):
            errors.append(
                f"score.yaml: {c.indicator}: corpus_metric {c.corpus_metric!r} not in "
                "config/todd_refs.yaml — the todd preset's book count reads it."
            )
        ind = indicators[c.indicator]
        if c.direction.value != "target":
            agrees = ind.higher_is_better == (c.direction.value == "higher")
            if not agrees:
                errors.append(
                    f"score.yaml: {c.indicator}: direction {c.direction.value!r} DISAGREES with the "
                    f"indicator's higher_is_better={ind.higher_is_better} — the catalog flag and "
                    "the score config must agree for every non-target component (flip one of the "
                    "two, deliberately, in the same version)."
                )
    for name in ScoreName:
        if not score.components_for(name):
            errors.append(f"score.yaml: the {name.value} score carries no component.")
    if errors:
        raise ConfigError("score.yaml cross-validation errors:\n- " + "\n- ".join(errors))


def score_config_sha256(config_dir: Path) -> str:
    return _file_sha256(config_dir / "score.yaml")
