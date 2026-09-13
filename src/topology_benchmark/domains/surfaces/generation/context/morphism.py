from typing import ClassVar

from attrs import frozen

from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.core.probability import FiniteDistribution, SamplingSession


@frozen
class FullDiskBoundaryCondition:
    family_id: ClassVar[str] = "full-disk-boundary"


@frozen
class AttachmentCondition:
    family_id: ClassVar[str] = "attachment"


@frozen
class PartialIntercomponentCondition:
    family_id: ClassVar[str] = "partial-intercomponent"


@frozen
class SelfBoundaryCondition:
    family_id: ClassVar[str] = "self-boundary"


@frozen
class AnnulusClosureCondition:
    family_id: ClassVar[str] = "annulus-closure"


type SurfaceMorphismCondition = (
    FullDiskBoundaryCondition
    | AttachmentCondition
    | PartialIntercomponentCondition
    | SelfBoundaryCondition
    | AnnulusClosureCondition
)


@frozen
class SurfaceMorphismGenerationContext:
    request: GenerationRequest
    law: FiniteDistribution[SurfaceMorphismCondition]
    sampling: SamplingSession
