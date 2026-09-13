import math
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from random import Random
from types import MappingProxyType
from typing import Protocol, override

from topology_benchmark.core.probability import (
    FiniteDistribution,
    WeightedValue,
    interpolate_anchors,
)


@dataclass(frozen=True, slots=True)
class QuestionChoice[QuestionT]:
    question: QuestionT
    weight: float

    def __post_init__(self) -> None:
        if self.weight < 0 or not math.isfinite(self.weight):
            raise ValueError("question weights must be finite and nonnegative")


@dataclass(frozen=True, slots=True)
class QuestionDistribution[QuestionT]:
    choices: tuple[QuestionChoice[QuestionT], ...]

    def __post_init__(self) -> None:
        if not self.choices or not any(choice.weight > 0 for choice in self.choices):
            raise ValueError("a question distribution needs positive total weight")

    def sample(self, rng: Random) -> QuestionT:
        distribution = FiniteDistribution(
            tuple(WeightedValue(choice.question, choice.weight) for choice in self.choices)
        )
        return distribution.sample(rng)

    @classmethod
    def concentrated(cls, question: QuestionT) -> QuestionDistribution[QuestionT]:
        return cls((QuestionChoice(question, 1.0),))


@dataclass(frozen=True, slots=True)
class DifficultyQuestionChoice[QuestionT]:
    question: QuestionT
    weights: tuple[tuple[int, float], ...]

    def __post_init__(self) -> None:
        if not self.weights:
            raise ValueError("difficulty question weights must not be empty")
        if any(
            level < 1 or weight < 0 or not math.isfinite(weight) for level, weight in self.weights
        ):
            raise ValueError("difficulty question weights are invalid")

    def weight_at(self, difficulty: int) -> float:
        return interpolate_anchors(self.weights, difficulty)


class QuestionDistributionResolver[QuestionT](Protocol):
    def at(self, difficulty: int) -> QuestionDistribution[QuestionT]: ...


@dataclass(frozen=True, slots=True)
class DifficultyQuestionDistribution[QuestionT](QuestionDistributionResolver[QuestionT]):
    choices: tuple[DifficultyQuestionChoice[QuestionT], ...]

    def __post_init__(self) -> None:
        if not self.choices:
            raise ValueError("a difficulty question distribution must not be empty")

    @override
    def at(self, difficulty: int) -> QuestionDistribution[QuestionT]:
        return QuestionDistribution(
            tuple(
                QuestionChoice(choice.question, choice.weight_at(difficulty))
                for choice in self.choices
            )
        )


class QuestionCatalog[QuestionT](Mapping[str, QuestionT]):
    def __init__(self, questions: tuple[QuestionT, ...]) -> None:
        indexed: dict[str, QuestionT] = {}
        for question in questions:
            question_id = getattr(question, "id", None)
            if not isinstance(question_id, str) or not question_id:
                raise ValueError("questions need a nonempty string ID")
            if question_id in indexed:
                raise ValueError(f"duplicate question ID: {question_id}")
            indexed[question_id] = question
        if not indexed:
            raise ValueError("a question catalog must not be empty")
        self._questions = MappingProxyType(indexed)

    @override
    def __getitem__(self, question_id: str) -> QuestionT:
        return self._questions[question_id]

    @override
    def __iter__(self) -> Iterator[str]:
        return iter(self._questions)

    @override
    def __len__(self) -> int:
        return len(self._questions)
