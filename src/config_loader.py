"""Loads and validates config/indicators/*.yaml, config/entities.yaml, config/sources.yaml.

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
