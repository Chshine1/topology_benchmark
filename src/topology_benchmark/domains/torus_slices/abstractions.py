from typing import Protocol

from topology_benchmark.core.generation.object_generator import IConditionalGenerator
from topology_benchmark.core.presentation.representation import IRepresentation
from topology_benchmark.core.problem.recipe import IProblemRecipe, ProblemRecipeCatalog
from topology_benchmark.core.problem.recipe_distribution import DifficultyProblemRecipeDistribution
from topology_benchmark.domains.torus_slices.generation.context import TorusGenerationContext
from topology_benchmark.domains.torus_slices.models.torus import TorusSliceObservation

type TorusAnswer = int | bool


class ITorusSliceGenerator(
    IConditionalGenerator[TorusGenerationContext, TorusSliceObservation],
    Protocol,
):
    pass


class ITorusSliceRepresentation(IRepresentation[TorusSliceObservation], Protocol):
    pass


class TorusProblemRecipeCatalog(ProblemRecipeCatalog[IProblemRecipe[TorusAnswer]]):
    pass


class TorusProblemRecipeDistribution(
    DifficultyProblemRecipeDistribution[IProblemRecipe[TorusAnswer]]
):
    pass
