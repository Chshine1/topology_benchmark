from random import Random
from typing import Protocol

from topology_benchmark.core.models import GenerationRequest, QuestionSection
from topology_benchmark.core.probability import SamplingSession
from topology_benchmark.core.protocols import (
    ConditionalGenerator,
    ObjectGenerator,
    Representation,
)
from topology_benchmark.domains.surfaces.generation import (
    SurfaceGenerationContext,
    SurfaceProblemIntent,
)
from topology_benchmark.domains.surfaces.models import EdgeRef, SurfaceMorphism, SurfacePresentation

type SurfaceAnswer = int | str | bool | tuple[int, ...]


class SurfaceGenerator(
    ObjectGenerator[SurfacePresentation],
    ConditionalGenerator[SurfaceGenerationContext, SurfacePresentation],
    Protocol,
):
    pass


class SurfaceMorphismGenerator(
    ObjectGenerator[SurfaceMorphism],
    ConditionalGenerator[SurfaceGenerationContext, SurfaceMorphism],
    Protocol,
):
    pass


class SurfaceIntentGenerator(Protocol):
    def sample(
        self, request: GenerationRequest, sampling: SamplingSession
    ) -> SurfaceProblemIntent: ...


class SurfaceRepresentation(Representation[SurfacePresentation], Protocol):
    def render(
        self,
        obj: SurfacePresentation,
        request: GenerationRequest,
        rng: Random,
        *,
        edge_labels: tuple[tuple[EdgeRef, str], ...] = (),
    ) -> QuestionSection: ...
