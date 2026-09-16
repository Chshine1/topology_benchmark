from typing import Protocol

from topology_benchmark.core.generation.object_generator import IConditionalGenerator
from topology_benchmark.core.presentation.representation import IRepresentation
from topology_benchmark.core.problem.models import GenerationRequest, QuestionSection
from topology_benchmark.core.problem.recipe import IProblemRecipe, ProblemRecipeCatalog
from topology_benchmark.core.problem.recipe_distribution import DifficultyProblemRecipeDistribution
from topology_benchmark.domains.surfaces.generation.context.morphism import (
    SurfaceMorphismGenerationContext,
)
from topology_benchmark.domains.surfaces.generation.context.object import (
    SurfaceObjectGenerationContext,
)
from topology_benchmark.domains.surfaces.models import SurfaceMorphism, SurfacePresentation
from topology_benchmark.domains.surfaces.rendering.diagram_planner import DiagramPlan

type SurfaceAnswer = int | str | bool | tuple[int, ...]


class ISurfaceGenerator(
    IConditionalGenerator[SurfaceObjectGenerationContext, SurfacePresentation],
    Protocol,
):
    pass


class ISurfaceMorphismGenerator(
    IConditionalGenerator[SurfaceMorphismGenerationContext, SurfaceMorphism],
    Protocol,
):
    pass


class ISurfaceRepresentation(IRepresentation[SurfacePresentation], Protocol):
    pass


class ISurfaceRenderBackend(Protocol):
    def render(
        self,
        surface: SurfacePresentation,
        plan: DiagramPlan,
        request: GenerationRequest,
    ) -> QuestionSection: ...


class SurfaceProblemRecipeCatalog(ProblemRecipeCatalog[IProblemRecipe[SurfaceAnswer]]):
    pass


class SurfaceProblemRecipeDistribution(
    DifficultyProblemRecipeDistribution[IProblemRecipe[SurfaceAnswer]]
):
    pass
