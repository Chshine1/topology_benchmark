"""A statically compatible set of components from one mathematical domain."""

from dataclasses import dataclass
from typing import TypeVar

from topology_benchmark.core.protocols import (
    Invariant,
    ObjectGenerator,
    Question,
    Representation,
    Transformation,
)

ObjectT = TypeVar("ObjectT")
AnswerT = TypeVar("AnswerT")


@dataclass(frozen=True, slots=True)
class ProblemRecipe[ObjectT, AnswerT]:
    generator: ObjectGenerator[ObjectT]
    transformations: tuple[Transformation[ObjectT], ...]
    invariant: Invariant[ObjectT, AnswerT]
    representation: Representation[ObjectT]
    question: Question[AnswerT]
