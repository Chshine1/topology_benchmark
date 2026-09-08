"""Surface-domain extension points."""

from typing import Protocol

from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.core.probability import SamplingSession
from topology_benchmark.core.protocols import (
    ConditionalGenerator,
    Invariant,
    ObjectGenerator,
    Question,
    Representation,
)
from topology_benchmark.domains.surfaces.generation import (
    SurfaceGenerationContext,
    SurfaceProblemIntent,
)
from topology_benchmark.domains.surfaces.models import SurfaceMorphism, SurfacePresentation

type SurfaceAnswer = int | str | bool


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
    pass


class SurfaceInvariant(Invariant[SurfacePresentation, SurfaceAnswer], Protocol):
    pass


class SurfaceQuestion(Question[SurfaceAnswer], Protocol):
    pass
