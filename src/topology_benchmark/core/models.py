from dataclasses import dataclass

from attrs import field as attrs_field
from attrs import frozen

from topology_benchmark.core.validation import number_range


@dataclass(frozen=True, slots=True)
class QuestionSection:
    media_type: str
    content: str


@dataclass(frozen=True, slots=True)
class Problem[AnswerT]:
    question: str
    sections: tuple[QuestionSection, ...]
    answer: AnswerT
    seed: int
    question_kind: str


@frozen
class GenerationRequest:
    seed: int
    difficulty: int = attrs_field(
        default=1,
        validator=number_range(
            minimum=1,
            maximum=10,
            message="difficulty must be between 1 and 10",
        ),
    )
