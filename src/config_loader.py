"""Loads and validates config/indicators/*.yaml, config/entities.yaml, config/sources.yaml,
config/todd_refs.yaml.

Principle: an invalid config file must fail the build immediately, with a
message pointing at the offending file — never produce a silently
incomplete dist/. Errors from all files are accumulated before raising, so
you don't have to fix-and-rerun one file at a time.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from src.schema.entity import Entity, EntityRegistry
from src.schema.indicator import Indicator
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
