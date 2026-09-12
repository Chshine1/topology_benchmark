from dataclasses import dataclass
from enum import Enum

from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.core.probability import SamplingSession


class ProblemSubject(Enum):
    OBJECT = "object"
    MORPHISM = "morphism"


class QuestionFocus(Enum):
    GLOBAL = "global"
    CLASSIFICATION = "classification"
    PATH = "path"
    RELATIONAL = "relational"
    TARGET_ONLY = "target-only"


@dataclass(frozen=True, slots=True)
class SurfaceProblemIntent:
    subject: ProblemSubject
    question_kind: str
    focus: QuestionFocus


@dataclass(frozen=True, slots=True)
class SurfaceGenerationContext:
    request: GenerationRequest
    intent: SurfaceProblemIntent
    sampling: SamplingSession
