from attrs import field, frozen

from topology_benchmark.core.probability.distribution import FiniteDistribution
from topology_benchmark.core.probability.sampling import SamplingSession
from topology_benchmark.core.problem.models import GenerationRequest
from topology_benchmark.core.validation import number_range


@frozen
class NoSurfacePaths:
    """The sampled presentation carries no distinguished paths."""


@frozen
class DistinguishedSurfacePaths:
    count: int = field(
        validator=number_range(
            minimum=1,
            message="a distinguished-path count must be positive",
        )
    )
    first_closed: bool


@frozen
class NontrivialHomologySurfacePath:
    """One closed path representing a nonzero first-homology class."""


type SurfacePathCondition = (
    NoSurfacePaths | DistinguishedSurfacePaths | NontrivialHomologySurfacePath
)


@frozen
class SurfaceObjectCondition:
    """A semantic surface outcome, independent of its construction strategy."""

    component_count: int = field(
        validator=number_range(
            minimum=1,
            message="a requested component count must be positive",
        )
    )
    paths: SurfacePathCondition


@frozen
class SurfaceObjectGenerationContext:
    request: GenerationRequest
    law: FiniteDistribution[SurfaceObjectCondition]
    sampling: SamplingSession
