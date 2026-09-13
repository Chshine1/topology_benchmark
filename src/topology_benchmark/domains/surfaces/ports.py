from random import Random
from typing import Protocol, override

from topology_benchmark.core.models import GenerationRequest, QuestionSection
from topology_benchmark.core.protocols import (
    ConditionalGenerator,
    ObjectGenerator,
    Representation,
)
from topology_benchmark.domains.surfaces.generation import (
    SurfaceMorphismGenerationContext,
    SurfaceObjectGenerationContext,
)
from topology_benchmark.domains.surfaces.models import EdgeRef, SurfaceMorphism, SurfacePresentation

type SurfaceAnswer = int | str | bool | tuple[int, ...]


class SurfaceGenerator(
    ObjectGenerator[SurfacePresentation],
    ConditionalGenerator[SurfaceObjectGenerationContext, SurfacePresentation],
    Protocol,
):
    pass


class SurfaceMorphismGenerator(
    ObjectGenerator[SurfaceMorphism],
    ConditionalGenerator[SurfaceMorphismGenerationContext, SurfaceMorphism],
    Protocol,
):
    pass


class SurfaceRepresentation(Representation[SurfacePresentation], Protocol):
    @override
    def render(
        self,
        obj: SurfacePresentation,
        request: GenerationRequest,
        rng: Random,
        *,
        edge_labels: tuple[tuple[EdgeRef, str], ...] = (),
    ) -> QuestionSection: ...
