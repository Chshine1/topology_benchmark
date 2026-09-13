import re
from collections import Counter
from typing import Any

from topology_benchmark.core.models import QuestionSection
from topology_benchmark.pipeline.artifacts.evaluation_writer import EvaluationArtifactWriter
from topology_benchmark.pipeline.artifacts.models import (
    BenchmarkEvaluation,
    GeneratedBenchmarkRun,
    ModelPrediction,
    QuestionScore,
)
from topology_benchmark.pipeline.config import EvaluationConfig
from topology_benchmark.pipeline.model_provider import ModelProvider


class BenchmarkEvaluator:
    def __init__(
        self,
        config: EvaluationConfig,
        model_provider: ModelProvider,
        artifact_writer: EvaluationArtifactWriter,
    ) -> None:
        self._config = config
        self._model_provider = model_provider
        self._artifact_writer = artifact_writer

    def evaluate(self, generated: GeneratedBenchmarkRun) -> None:
        predictions = []
        correct = Counter[str]()
        totals = Counter[str]()
        for item in generated.items:
            response, error = self._answer(item.problem.question, item.problem.sections)
            is_correct = error is None and self._score_answer(item.problem.answer, response)
            key = f"{item.domain}/{item.problem.question_id}"
            totals[key] += 1
            correct[key] += int(is_correct)
            predictions.append(
                ModelPrediction(
                    item.item_id,
                    response,
                    self._extract_final_answer(response),
                    is_correct,
                    error,
                )
            )
        evaluation = BenchmarkEvaluation(
            tuple(predictions),
            tuple(
                (key, QuestionScore(correct[key], count)) for key, count in sorted(totals.items())
            ),
        )
        self._artifact_writer.write(generated, evaluation)

    @staticmethod
    def _extract_final_answer(response: str) -> str:
        matches = re.findall(r"(?im)^\s*FINAL_ANSWER\s*:\s*(.*?)\s*$", response)
        return matches[-1] if matches else response.strip()

    @classmethod
    def _score_answer(cls, expected: Any, response: str) -> bool:
        candidate = cls._extract_final_answer(response)
        if isinstance(expected, bool):
            normalized = candidate.casefold().strip(" .")
            aliases = {True: {"true", "yes"}, False: {"false", "no"}}
            return normalized in aliases[expected]
        if isinstance(expected, int):
            return bool(re.fullmatch(r"[+-]?\d+", candidate.strip())) and int(candidate) == expected
        return _normalize_text(candidate) == _normalize_text(str(expected))

    def _answer(
        self, question: str, sections: tuple[QuestionSection, ...]
    ) -> tuple[str, str | None]:
        response = ""
        error = None
        for _ in range(self._config.max_retries + 1):
            try:
                return self._model_provider.answer(question, sections), None
            except Exception as caught:  # A provider failure is an item result, not a lost run.
                error = f"{type(caught).__name__}: {caught}"
        return response, error

def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold().strip(".")
