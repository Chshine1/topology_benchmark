from random import Random
from typing import Protocol

from topology_benchmark.core.problem.models import GenerationRequest, QuestionSection


class IRepresentation[ObjectT](Protocol):
    def render(self, obj: ObjectT, request: GenerationRequest, rng: Random) -> QuestionSection: ...
