import math
from collections.abc import Iterator, Mapping
from random import Random
from types import MappingProxyType
from typing import Protocol, override

from attrs import field, frozen, validators

from topology_benchmark.core.probability import (
    FiniteDistribution,
    WeightedValue,
    interpolate_anchors,
)
from topology_benchmark.core.validation import all_members, any_member, nonempty, number_range


@frozen
class QuestionChoice[QuestionT]:
    question: QuestionT
    weight: float = field(
        validator=number_range(
            minimum=0.0,
            finite=True,
            message="question weights must be finite and nonnegative",
        )
    )


@frozen
class QuestionDistribution[QuestionT]:
    choices: tuple[QuestionChoice[QuestionT], ...] = field(
        validator=any_member(
            lambda choice: choice.weight > 0,
            message="a question distribution needs positive total weight",
        )
    )

    def sample(self, rng: Random) -> QuestionT:
        distribution = FiniteDistribution(
            tuple(WeightedValue(choice.question, choice.weight) for choice in self.choices)
        )
        return distribution.sample(rng)

    @classmethod
    def concentrated(cls, question: QuestionT) -> QuestionDistribution[QuestionT]:
        return cls((QuestionChoice(question, 1.0),))


@frozen
class DifficultyQuestionChoice[QuestionT]:
    question: QuestionT
    weights: tuple[tuple[int, float], ...] = field(
        validator=validators.and_(
            nonempty("difficulty question weights must not be empty"),
            all_members(
                lambda anchor: anchor[0] >= 1 and anchor[1] >= 0 and math.isfinite(anchor[1]),
                message="difficulty question weights are invalid",
            ),
        )
    )

    def weight_at(self, difficulty: int) -> float:
        return interpolate_anchors(self.weights, difficulty)


class QuestionDistributionResolver[QuestionT](Protocol):
    def at(self, difficulty: int) -> QuestionDistribution[QuestionT]: ...


@frozen
class DifficultyQuestionDistribution[QuestionT](QuestionDistributionResolver[QuestionT]):
    choices: tuple[DifficultyQuestionChoice[QuestionT], ...] = field(
        validator=nonempty("a difficulty question distribution must not be empty")
    )

    @override
    def at(self, difficulty: int) -> QuestionDistribution[QuestionT]:
        return QuestionDistribution(
            tuple(
                QuestionChoice(choice.question, choice.weight_at(difficulty))
                for choice in self.choices
            )
        )


class RegisteredQuestion(Protocol):
    @property
    def id(self) -> str: ...


class QuestionCatalog[QuestionT: RegisteredQuestion](Mapping[str, QuestionT]):
    def __init__(self, questions: tuple[QuestionT, ...]) -> None:
        indexed: dict[str, QuestionT] = {}
        for question in questions:
            question_id = question.id
            if not question_id:
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
