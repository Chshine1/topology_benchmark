from collections.abc import Callable
from random import Random
from typing import Any, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    SkipValidation,
    create_model,
    model_serializer,
    model_validator,
)

from topology_benchmark.core.probability.distribution import FiniteDistribution, IDistribution


class _FinitelyDistributedConfig[T: BaseModel](BaseModel):
    """Pydantic adapter structurally implementing IDistribution (metaclasses conflict)."""

    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", allow_inf_nan=False, arbitrary_types_allowed=True
    )

    # The generated model's before-validator constructs and validates this value.
    distribution: SkipValidation[FiniteDistribution[T]]

    def sample(self, rng: Random) -> T:
        return self.distribution.sample(rng)

    @model_serializer
    def _serialize_weighted_values(self) -> list[dict[str, Any]]:
        return [
            {**item.value.model_dump(), "$weight": item.weight} for item in self.distribution.values
        ]


def _get_transform_validator[T: BaseModel](
    generic_class: type[T],
) -> Callable[[Any], dict[str, FiniteDistribution[T]]]:
    def extract_meta_and_body(data: Any) -> dict[str, FiniteDistribution[T]]:
        if not isinstance(data, list):
            raise ValueError("a distributed configuration must be a list of weighted objects")

        weighted: list[tuple[T, float]] = []

        for item in data:
            if not isinstance(item, dict):
                raise ValueError("each distributed configuration entry must be an object")

            item_dict = dict(item)  # intended copy

            if "$weight" not in item_dict:
                raise ValueError("each distributed configuration entry requires $weight")
            weight = item_dict.pop("$weight")
            if isinstance(weight, bool) or not isinstance(weight, int | float):
                raise ValueError("$weight must be a finite nonnegative number")
            value = generic_class.model_validate(item_dict)

            weighted.append((value, float(weight)))

        return {"distribution": FiniteDistribution.weighted(weighted)}

    return extract_meta_and_body


def create_distribution_model[T: BaseModel](
    generic_class: type[T],
) -> type[IDistribution[T]]:
    """Create a weighted-list Pydantic model; validate it through TypeAdapter."""
    validator = model_validator(mode="before")(_get_transform_validator(generic_class))
    return create_model(
        f"{generic_class.__name__}FinitelyDistributedConfig",
        __base__=_FinitelyDistributedConfig[generic_class],
        __validators__={
            # Pydantic accepts decorator descriptors here, but annotates only callables.
            "distribution_validator": cast(Callable[..., Any], validator),
        },
    )


def finite_distribution_from_config[T](config: IDistribution[T], /) -> FiniteDistribution[T]:
    """Expose the exact law of a model produced by create_distribution_model."""
    if not isinstance(config, _FinitelyDistributedConfig):
        raise TypeError("the distribution was not created by create_distribution_model")
    return config.distribution
