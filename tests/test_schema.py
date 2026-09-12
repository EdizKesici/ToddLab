import pytest
from pydantic import ValidationError

from src.schema.indicator import Indicator


def _base_indicator(**overrides) -> dict:
    data = {
        "id": "test_indicator",
        "label": "Test indicator",
        "family": "mortality",
        "unit": "test_unit",
        "higher_is_better": False,
        "todd_core": True,
        "sources": [{"provider": "owid", "ref": "test-slug", "priority": 1}],
        "reliability": "high",
        "reliability_criteria": "Justification long enough to pass the validator.",
        "license": "CC-BY-4.0",
    }
    data.update(overrides)
    return data


def test_valid_indicator_passes():
    ind = Indicator.model_validate(_base_indicator())
    assert ind.id == "test_indicator"


def test_duplicate_priorities_rejected():
    with pytest.raises(ValidationError, match="source priorities must be unique"):
        Indicator.model_validate(
            _base_indicator(
                sources=[
                    {"provider": "owid", "ref": "a", "priority": 1},
                    {"provider": "worldbank", "ref": "b", "priority": 1},
                ]
            )
        )


def test_reliability_low_requires_detailed_justification():
    with pytest.raises(ValidationError, match="requires a detailed reliability_criteria"):
        Indicator.model_validate(
            _base_indicator(reliability="low", reliability_criteria="too short")
        )


def test_reliability_low_with_good_justification_passes():
    ind = Indicator.model_validate(
        _base_indicator(
            reliability="low",
            reliability_criteria="Modeled estimate, single source, no cross-check possible.",
        )
    )
    assert ind.reliability.value == "low"


def test_id_must_be_snake_case():
    with pytest.raises(ValidationError):
        Indicator.model_validate(_base_indicator(id="Not Snake Case"))


def test_sources_by_priority_is_sorted():
    ind = Indicator.model_validate(
        _base_indicator(
            sources=[
                {"provider": "worldbank", "ref": "b", "priority": 3},
                {"provider": "owid", "ref": "a", "priority": 1},
            ]
        )
    )
    assert [s.priority for s in ind.sources_by_priority()] == [1, 3]


def test_trailing_newline_from_yaml_block_scalar_is_stripped():
    ind = Indicator.model_validate(_base_indicator(reliability_criteria="Some text.\n"))
    assert ind.reliability_criteria == "Some text."
