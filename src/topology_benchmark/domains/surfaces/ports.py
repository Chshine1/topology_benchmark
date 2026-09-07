"""Surface-domain extension points."""

from typing import Protocol

from topology_benchmark.core.protocols import Invariant, ObjectGenerator, Question, Representation
from topology_benchmark.domains.surfaces.models import SurfaceMorphism, SurfacePresentation

type SurfaceAnswer = int | str | bool


class SurfaceGenerator(ObjectGenerator[SurfacePresentation], Protocol):
    pass


class SurfaceMorphismGenerator(ObjectGenerator[SurfaceMorphism], Protocol):
    pass


class SurfaceRepresentation(Representation[SurfacePresentation], Protocol):
    pass


class SurfaceInvariant(Invariant[SurfacePresentation, SurfaceAnswer], Protocol):
    pass


class SurfaceQuestion(Question[SurfaceAnswer], Protocol):
    pass
