from random import Random
from typing import Any, Protocol, TypeVar

from topology_benchmark.core.models import GenerationRequest, Problem, QuestionSection

ObjectT = TypeVar("ObjectT")
ContextT = TypeVar("ContextT")


class ObjectGenerator(Protocol[ObjectT]):
    def generate(self, request: GenerationRequest, rng: Random) -> ObjectT: ...


class ConditionalGenerator[ContextT, ObjectT](Protocol):
    def generate_for(self, context: ContextT) -> ObjectT: ...


class Representation(Protocol[ObjectT]):
    def render(self, obj: ObjectT, request: GenerationRequest, rng: Random) -> QuestionSection: ...


class ProblemProvider(Protocol):
    def generate(self, *, seed: int, difficulty: int = 1) -> Problem[Any]: ...
