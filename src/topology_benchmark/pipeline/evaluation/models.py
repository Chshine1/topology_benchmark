from dataclasses import dataclass

from attrs import field, frozen, validators


@dataclass(frozen=True, slots=True)
class ModelPrediction:
    item_id: str
    response: str
    extracted_answer: str
    correct: bool
    error: str | None


@frozen
class QuestionScore:
    correct: int = field(validator=validators.ge(0))
    total: int = field(validator=validators.ge(1))

    def __attrs_post_init__(self) -> None:
        if self.correct > self.total:
            raise ValueError("a question score cannot have more correct answers than attempts")

    @property
    def accuracy(self) -> float:
        return self.correct / self.total


@dataclass(frozen=True, slots=True)
class BenchmarkEvaluation:
    predictions: tuple[ModelPrediction, ...]
    scores: tuple[tuple[str, QuestionScore], ...]
