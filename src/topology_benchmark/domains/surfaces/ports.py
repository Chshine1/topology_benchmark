from random import Random
from typing import Protocol, override

from topology_benchmark.core.generation.object_generator import IConditionalGenerator
from topology_benchmark.core.presentation.representation import IRepresentation
from topology_benchmark.core.problem.models import GenerationRequest, QuestionSection
from topology_benchmark.domains.surfaces.generation.context.morphism import (
    SurfaceMorphismGenerationContext,
)
from topology_benchmark.domains.surfaces.generation.context.object import (
    SurfaceObjectGenerationContext,
)
from topology_benchmark.domains.surfaces.models import EdgeRef, SurfaceMorphism, SurfacePresentation

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
    @override
    def render(
        self,
        obj: SurfacePresentation,
        request: GenerationRequest,
        rng: Random,
        *,
        edge_labels: tuple[tuple[EdgeRef, str], ...] = (),
    ) -> QuestionSection: ...
