from .morphism import (
    BoundaryChangeQuestion,
    ComponentChangeQuestion,
    EulerChangeQuestion,
    HomologyIsomorphismQuestion,
    MapInjectiveQuestion,
    MapSurjectiveQuestion,
    SurfaceMorphismQuestion,
    TargetHomologyQuestion,
    TargetOrientableQuestion,
)
from .object import (
    BoundaryComponentsQuestion,
    ConnectedComponentsQuestion,
    EulerCharacteristicQuestion,
    HomologyGroupsQuestion,
    OrientableQuestion,
    PathIsCycleQuestion,
    PathRepresentativeQuestion,
    SurfaceObjectQuestion,
)

type SurfaceQuestion = SurfaceObjectQuestion | SurfaceMorphismQuestion

__all__ = [
    "BoundaryChangeQuestion",
    "BoundaryComponentsQuestion",
    "ComponentChangeQuestion",
    "ConnectedComponentsQuestion",
    "EulerChangeQuestion",
    "EulerCharacteristicQuestion",
    "HomologyGroupsQuestion",
    "HomologyIsomorphismQuestion",
    "MapInjectiveQuestion",
    "MapSurjectiveQuestion",
    "OrientableQuestion",
    "PathIsCycleQuestion",
    "PathRepresentativeQuestion",
    "SurfaceQuestion",
    "TargetHomologyQuestion",
    "TargetOrientableQuestion",
]
