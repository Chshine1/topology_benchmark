from typing import Protocol

from topology_benchmark.core.generation.object_generator import IObjectGenerator
from topology_benchmark.core.presentation.representation import IRepresentation
from topology_benchmark.core.problem.recipe import IProblemRecipe, ProblemRecipeCatalog
from topology_benchmark.core.problem.recipe_distribution import DifficultyProblemRecipeDistribution
from topology_benchmark.domains.polyhedral_nets.models.net import PolyhedralFolding, PolyhedralNet

type PolyhedralAnswer = int | str | bool


class IPolyhedralNetGenerator(IObjectGenerator[PolyhedralFolding], Protocol):
    pass


class IPolyhedralNetRepresentation(IRepresentation[PolyhedralNet], Protocol):
    pass


class PolyhedralProblemRecipeCatalog(ProblemRecipeCatalog[IProblemRecipe[PolyhedralAnswer]]):
    pass


class PolyhedralProblemRecipeDistribution(
    DifficultyProblemRecipeDistribution[IProblemRecipe[PolyhedralAnswer]]
):
    pass
