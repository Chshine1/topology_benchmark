from .morphism import (
    BoundaryChangeProblemRecipe,
    ComponentChangeProblemRecipe,
    EulerChangeProblemRecipe,
    HomologyIsomorphismProblemRecipe,
    MapInjectiveProblemRecipe,
    MapSurjectiveProblemRecipe,
    SurfaceMorphismProblemRecipe,
    TargetHomologyProblemRecipe,
    TargetOrientableProblemRecipe,
)
from .object import (
    BoundaryComponentsProblemRecipe,
    ConnectedComponentsProblemRecipe,
    EulerCharacteristicProblemRecipe,
    HomologyGroupsProblemRecipe,
    OrientableProblemRecipe,
    PathIsCycleProblemRecipe,
    PathRepresentativeProblemRecipe,
    SurfaceObjectProblemRecipe,
)

type SurfaceProblemRecipe = SurfaceObjectProblemRecipe | SurfaceMorphismProblemRecipe

__all__ = [
    "BoundaryChangeProblemRecipe",
    "BoundaryComponentsProblemRecipe",
    "ComponentChangeProblemRecipe",
    "ConnectedComponentsProblemRecipe",
    "EulerChangeProblemRecipe",
    "EulerCharacteristicProblemRecipe",
    "HomologyGroupsProblemRecipe",
    "HomologyIsomorphismProblemRecipe",
    "MapInjectiveProblemRecipe",
    "MapSurjectiveProblemRecipe",
    "OrientableProblemRecipe",
    "PathIsCycleProblemRecipe",
    "PathRepresentativeProblemRecipe",
    "SurfaceProblemRecipe",
    "TargetHomologyProblemRecipe",
    "TargetOrientableProblemRecipe",
]
