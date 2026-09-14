from random import Random

import pytest

from topology_benchmark.core.problem.question_distribution import (
    DifficultyQuestionChoice,
    DifficultyQuestionDistribution,
    QuestionChoice,
    QuestionDistribution,
)


class _Question:
    def __init__(self, question_id: str) -> None:
        self.id = question_id


def test_question_distribution_samples_registered_instances() -> None:
    first, second = object(), object()
    distribution = QuestionDistribution((QuestionChoice(first, 0), QuestionChoice(second, 1)))

    assert distribution.sample(Random(3)) is second


def test_question_distribution_requires_a_positive_weight() -> None:
    with pytest.raises(ValueError, match="positive total weight"):
        QuestionDistribution((QuestionChoice(object(), 0),))
    with pytest.raises(ValueError, match="nonnegative"):
        QuestionChoice(object(), -1)


def test_difficulty_and_concentrated_distributions_resolve_before_sampling() -> None:
    first, second = _Question("first"), _Question("second")
    default = DifficultyQuestionDistribution(
        (
            DifficultyQuestionChoice(first, ((1, 1.0),)),
            DifficultyQuestionChoice(second, ((1, 0.0),)),
        )
    )
    assert default.at(1).sample(Random(1)) is first
    assert QuestionDistribution.concentrated(second).sample(Random(1)) is second
