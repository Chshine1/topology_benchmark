from copy import deepcopy
from random import Random
from typing import cast

import pytest
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError, create_model

from topology_benchmark.core.probability.distribution import FiniteDistribution, IDistribution
from topology_benchmark.utils.distribution_model import create_distribution_model


class ExampleConfig(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    value: int


def test_weighted_configuration_preserves_types_weights_and_input() -> None:
    model: type[IDistribution[ExampleConfig]] = create_distribution_model(ExampleConfig)
    adapter = TypeAdapter(model)
    data = [{"value": 1, "$weight": 1}, {"value": 2, "$weight": 3.0}]
    original = deepcopy(data)
    config = adapter.validate_python(data)

    assert data == original
    expected = FiniteDistribution.weighted(
        [(ExampleConfig(value=1), 1), (ExampleConfig(value=2), 3)]
    )
    for seed in range(100):
        assert config.sample(Random(seed)) == expected.sample(Random(seed))
        assert isinstance(config.sample(Random(seed)), ExampleConfig)
    distribution: IDistribution[ExampleConfig] = config
    assert distribution.sample(Random(0)).value == 2
    assert adapter.validate_python(config) is config
    with pytest.raises(ValidationError, match="frozen"):
        config.__setattr__("distribution", object())


@pytest.mark.parametrize(
    "data",
    [
        {},
        None,
        [1],
        [{"value": 1}],
        [{"value": 1, "$weight": None}],
        [{"value": 1, "$weight": "1"}],
        [{"value": 1, "$weight": True}],
        [{"value": 1, "$weight": -1}],
        [{"value": 1, "$weight": float("nan")}],
        [{"value": 1, "$weight": float("inf")}],
        [{"value": 1, "$weight": 0}],
        [],
        [{"value": "1", "$weight": 1}],
        [{"$weight": 1}],
        [{"value": 1, "$weight": 1, "unknown": 2}],
    ],
)
def test_invalid_configuration_raises_validation_error(data: object) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(create_distribution_model(ExampleConfig)).validate_python(data)


def test_nested_configuration_and_json_validation() -> None:
    class Envelope(BaseModel):
        choices: object

    distribution_model = create_distribution_model(ExampleConfig)
    envelope = create_model(
        "ConfiguredEnvelope", __base__=Envelope, choices=(distribution_model, ...)
    )
    config = envelope.model_validate_json('{"choices": [{"value": 7, "$weight": 1}]}')
    choices = cast(IDistribution[ExampleConfig], config.choices)
    assert choices.sample(Random(0)) == ExampleConfig(value=7)


def test_zero_weight_entries_are_never_sampled() -> None:
    config = TypeAdapter(create_distribution_model(ExampleConfig)).validate_python(
        [{"value": 1, "$weight": 0}, {"value": 2, "$weight": 1}]
    )
    assert all(config.sample(Random(seed)).value == 2 for seed in range(20))
