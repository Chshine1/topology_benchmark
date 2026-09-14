import math
from typing import Protocol, override

from attrs import field, frozen, validators

from topology_benchmark.core.probability.distribution import FiniteDistribution
from topology_benchmark.core.probability.interpolation import interpolate_anchors
from topology_benchmark.core.problem.recipe import IProblemRecipe
from topology_benchmark.core.validation import all_members, nonempty


@frozen
class DifficultyProblemRecipeWeight[RecipeT: IProblemRecipe[object]]:
    recipe: RecipeT
    weights: tuple[tuple[int, float], ...] = field(
        validator=validators.and_(
            nonempty("difficulty problem recipe weights must not be empty"),
            all_members(
                lambda anchor: anchor[0] >= 1 and anchor[1] >= 0 and math.isfinite(anchor[1]),
                message="difficulty problem recipe weights are invalid",
            ),
        )
    )

    def weight_at(self, difficulty: int) -> float:
        return interpolate_anchors(self.weights, difficulty)


class IProblemRecipeDistribution[RecipeT: IProblemRecipe[object]](Protocol):
    def at(self, difficulty: int) -> FiniteDistribution[RecipeT]: ...


@frozen
class DifficultyProblemRecipeDistribution[RecipeT: IProblemRecipe[object]](
    IProblemRecipeDistribution[RecipeT]
):
    recipe_weights: tuple[DifficultyProblemRecipeWeight[RecipeT], ...] = field(
        validator=nonempty("a difficulty problem recipe distribution must not be empty")
    )

    @override
    def at(self, difficulty: int) -> FiniteDistribution[RecipeT]:
        return FiniteDistribution.weighted(
            (weighted.recipe, weighted.weight_at(difficulty)) for weighted in self.recipe_weights
        )
