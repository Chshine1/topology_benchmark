from random import Random
from typing import Protocol

from topology_benchmark.core.problem.models import GenerationRequest


class IObjectGenerator[ObjectT](Protocol):
    def generate(self, request: GenerationRequest, rng: Random) -> ObjectT: ...


class IConditionalGenerator[ContextT, ObjectT](Protocol):
    def generate_for(self, context: ContextT) -> ObjectT: ...
