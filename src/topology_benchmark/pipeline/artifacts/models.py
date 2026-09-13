from dataclasses import dataclass
from pathlib import Path
from typing import Any

from topology_benchmark.core.models import Problem


@dataclass(frozen=True, slots=True)
class GeneratedItem:
    item_id: str
    domain: str
    problem: Problem[Any]


@dataclass(frozen=True, slots=True)
class GeneratedBenchmarkRun:
    directory: Path
    items: tuple[GeneratedItem, ...]


@dataclass(frozen=True, slots=True)
class ModelPrediction:
    item_id: str
    response: str
    extracted_answer: str
    correct: bool
    error: str | None


@dataclass(frozen=True, slots=True)
class QuestionScore:
    correct: int
    total: int

    @property
    def accuracy(self) -> float:
        return self.correct / self.total


@dataclass(frozen=True, slots=True)
class BenchmarkEvaluation:
    predictions: tuple[ModelPrediction, ...]
    scores: tuple[tuple[str, QuestionScore], ...]
