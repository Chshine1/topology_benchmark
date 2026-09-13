from random import Random
from typing import Protocol, TypeVar

from topology_benchmark.core.models import GenerationRequest, Problem, QuestionSection
from topology_benchmark.core.recipes import QuestionDistribution, RegisteredQuestion

ObjectT = TypeVar("ObjectT")
ContextT = TypeVar("ContextT")
AnswerT = TypeVar("AnswerT")


class ObjectGenerator(Protocol[ObjectT]):
    def generate(self, request: GenerationRequest, rng: Random) -> ObjectT: ...


class ConditionalGenerator[ContextT, ObjectT](Protocol):
    def generate_for(self, context: ContextT) -> ObjectT: ...


class Representation(Protocol[ObjectT]):
    def render(self, obj: ObjectT, request: GenerationRequest, rng: Random) -> QuestionSection: ...


class ProblemRecipe[AnswerT](RegisteredQuestion, Protocol):
    """A registered, independently selectable problem-producing capability."""

    def generate(self, request: GenerationRequest) -> Problem[AnswerT]: ...


class ProblemProvider[QuestionT, AnswerT](Protocol):
    def generate(
        self,
        *,
        request: GenerationRequest,
        distribution: QuestionDistribution[QuestionT],
    ) -> Problem[AnswerT]: ...
