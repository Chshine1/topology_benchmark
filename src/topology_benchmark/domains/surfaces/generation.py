from dataclasses import dataclass
from enum import Enum

from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.core.probability import SamplingSession


class QuestionFocus(Enum):
    GLOBAL = "global"
    CLASSIFICATION = "classification"
    PATH = "path"


class PathGenerationMode(Enum):
    NONE = "none"
    CYCLE_TEST = "cycle-test"
    REPRESENTATIVE = "representative"


@dataclass(frozen=True, slots=True)
class SurfaceObjectGenerationSpec:
    focus: QuestionFocus
    path_mode: PathGenerationMode = PathGenerationMode.NONE
    favor_multiple_polygons: bool = False


@dataclass(frozen=True, slots=True)
class SurfaceObjectGenerationContext:
    request: GenerationRequest
    spec: SurfaceObjectGenerationSpec
    sampling: SamplingSession


class MorphismFamily(Enum):
    FULL_DISK_BOUNDARY = "full-disk-boundary"
    ATTACHMENT = "attachment"
    PARTIAL_INTERCOMPONENT = "partial-intercomponent"
    SELF_BOUNDARY = "self-boundary"
    ANNULUS_CLOSURE = "annulus-closure"


@dataclass(frozen=True, slots=True)
class MorphismFamilyAffinity:
    full_disk_boundary: float = 1.0
    attachment: float = 1.0
    partial_intercomponent: float = 1.0
    self_boundary: float = 1.0
    annulus_closure: float = 1.0

    def __post_init__(self) -> None:
        if (
            min(
                self.full_disk_boundary,
                self.attachment,
                self.partial_intercomponent,
                self.self_boundary,
                self.annulus_closure,
            )
            < 0
        ):
            raise ValueError("morphism family affinities must be nonnegative")

    def for_family(self, family: MorphismFamily) -> float:
        return {
            MorphismFamily.FULL_DISK_BOUNDARY: self.full_disk_boundary,
            MorphismFamily.ATTACHMENT: self.attachment,
            MorphismFamily.PARTIAL_INTERCOMPONENT: self.partial_intercomponent,
            MorphismFamily.SELF_BOUNDARY: self.self_boundary,
            MorphismFamily.ANNULUS_CLOSURE: self.annulus_closure,
        }[family]


@dataclass(frozen=True, slots=True)
class SurfaceMorphismGenerationContext:
    request: GenerationRequest
    affinity: MorphismFamilyAffinity
    sampling: SamplingSession
