"""Static extension points for mathematical domains."""

from random import Random
from typing import TYPE_CHECKING, Protocol, TypeVar

from topology_benchmark.core.models import GenerationRequest, Problem, PromptData

if TYPE_CHECKING:
    from topology_benchmark.core.recipe import ProblemRecipe

ObjectT = TypeVar("ObjectT")
AnswerT = TypeVar("AnswerT")
ContextT = TypeVar("ContextT")


class ObjectGenerator(Protocol[ObjectT]):
    def generate(self, request: GenerationRequest, rng: Random) -> ObjectT: ...


class ConditionalGenerator[ContextT, ObjectT](Protocol):
    def generate_for(self, context: ContextT) -> ObjectT: ...


class Morphism(Protocol[ObjectT]):
    """A first-class arrow which can itself be the subject of a problem."""

    @property
    def name(self) -> str: ...

    @property
    def source(self) -> ObjectT: ...

    @property
    def target(self) -> ObjectT: ...


class Transformation(Protocol[ObjectT]):
    """A recipe-stage operation, distinct from the arrow value it may construct."""

    @property
    def name(self) -> str: ...

    def apply(self, obj: ObjectT, request: GenerationRequest, rng: Random) -> ObjectT: ...


class Invariant(Protocol[ObjectT, AnswerT]):
    @property
    def name(self) -> str: ...

    def compute(self, obj: ObjectT) -> AnswerT: ...


class Representation(Protocol[ObjectT]):
    def render(self, obj: ObjectT, request: GenerationRequest, rng: Random) -> PromptData: ...


class Question(Protocol[AnswerT]):
    def formulate(self, invariant_name: str) -> str: ...


class ProblemComposer(Protocol):
    def compose[ObjectT, AnswerT](
        self,
        recipe: ProblemRecipe[ObjectT, AnswerT],
        request: GenerationRequest,
    ) -> Problem[AnswerT]: ...
