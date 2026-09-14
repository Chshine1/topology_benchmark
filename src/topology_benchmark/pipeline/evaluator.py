from collections import Counter

from topology_benchmark.core.problem.models import QuestionSection
from topology_benchmark.pipeline.config import EvaluationConfig
from topology_benchmark.pipeline.dataset.models import GeneratedBenchmarkRun
from topology_benchmark.pipeline.evaluation.answer_scorer import IAnswerScorer
from topology_benchmark.pipeline.evaluation.artifact_writer import EvaluationArtifactWriter
from topology_benchmark.pipeline.evaluation.model_provider import IModelProvider
from topology_benchmark.pipeline.evaluation.models import (
    BenchmarkEvaluation,
    ModelPrediction,
    QuestionScore,
)


class BenchmarkEvaluator:
    def __init__(
        self,
        config: EvaluationConfig,
        model_provider: IModelProvider,
        artifact_writer: EvaluationArtifactWriter,
        answer_scorer: IAnswerScorer,
    ) -> None:
        self._config = config
        self._model_provider = model_provider
        self._artifact_writer = artifact_writer
        self._answer_scorer = answer_scorer

    def evaluate(self, generated: GeneratedBenchmarkRun) -> None:
        predictions = []
        correct = Counter[str]()
        totals = Counter[str]()
        for item in generated.items:
            response, error = self._answer(item.problem.question, item.problem.sections)
            is_correct = error is None and self._answer_scorer.score(item.problem.answer, response)
            key = f"{item.domain}/{item.problem.question_id}"
            totals[key] += 1
            correct[key] += int(is_correct)
            predictions.append(
                ModelPrediction(
                    item.item_id,
                    response,
                    self._answer_scorer.extract(response),
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
