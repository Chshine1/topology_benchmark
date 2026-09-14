from random import Random

import pytest

from topology_benchmark.core.probability.distribution import FiniteDistribution
from topology_benchmark.core.problem.recipe_distribution import (
    DifficultyProblemRecipeDistribution,
    DifficultyProblemRecipeWeight,
)


class _Recipe:
    def __init__(self, recipe_id: str) -> None:
        self.id = recipe_id

    def generate(self, request):
        del request
        raise NotImplementedError


def test_finite_distribution_samples_registered_recipes() -> None:
    first, second = object(), object()
    distribution = FiniteDistribution.weighted(((first, 0), (second, 1)))

    assert distribution.sample(Random(3)) is second


def test_recipe_distribution_requires_a_positive_weight() -> None:
    with pytest.raises(ValueError, match="positive total weight"):
        FiniteDistribution.weighted(((object(), 0),))
    with pytest.raises(ValueError, match="nonnegative"):
        FiniteDistribution.weighted(((object(), -1),))


def test_difficulty_and_concentrated_distributions_resolve_before_sampling() -> None:
    first, second = _Recipe("first"), _Recipe("second")
    default = DifficultyProblemRecipeDistribution(
        (
            DifficultyProblemRecipeWeight(first, ((1, 1.0),)),
            DifficultyProblemRecipeWeight(second, ((1, 0.0),)),
        )
    )
    assert default.at(1).sample(Random(1)) is first
    assert FiniteDistribution.concentrated(second).sample(Random(1)) is second
