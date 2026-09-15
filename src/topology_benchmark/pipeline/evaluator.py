from pathlib import Path

from topology_benchmark.core.problem.models import QuestionSection
from topology_benchmark.pipeline.config import EvaluationConfig
from topology_benchmark.pipeline.dataset.models import GeneratedBenchmarkRun
from topology_benchmark.pipeline.evaluation.answer_scorer import IAnswerScorer
from topology_benchmark.pipeline.evaluation.artifact_store import EvaluationArtifactStore
from topology_benchmark.pipeline.evaluation.model_provider import IModelProvider
from topology_benchmark.pipeline.evaluation.models import (
    ModelPrediction,
)


class BenchmarkEvaluator:
    def __init__(
        self,
        config: EvaluationConfig,
        model_provider: IModelProvider,
        artifact_store: EvaluationArtifactStore,
        answer_scorer: IAnswerScorer,
    ) -> None:
        self._config = config
        self._model_provider = model_provider
        self._artifact_store = artifact_store
        self._answer_scorer = answer_scorer

    def evaluate(self, generated: GeneratedBenchmarkRun) -> Path:
        session = self._artifact_store.open(generated)
        predictions = session.load_predictions()
        expected_ids = {item.item_id for item in generated.items}
        unexpected = predictions.keys() - expected_ids
        if unexpected:
            raise ValueError(
                f"evaluation contains predictions for unknown items: {sorted(unexpected)}"
            )
        for item in generated.items:
            if item.item_id in predictions:
                continue
            response, error, attempts = self._answer(item.problem.prompt, item.problem.sections)
            is_correct = error is None and self._answer_scorer.score(item.problem.answer, response)
            prediction = ModelPrediction(
                item.item_id,
                response,
                self._answer_scorer.extract(response),
                is_correct,
                error,
                attempts,
            )
            session.write_prediction(prediction)
            predictions[item.item_id] = prediction
        session.publish(generated, predictions)
        return session.directory

    def _answer(
        self, question: str, sections: tuple[QuestionSection, ...]
    ) -> tuple[str, str | None, int]:
        response = ""
        error = None
        for attempt in range(1, self._config.max_retries + 2):
            try:
                return self._model_provider.answer(question, sections), None, attempt
            except Exception as caught:  # A provider failure is an item result, not a lost run.
                error = f"{type(caught).__name__}: {caught}"
        return response, error, self._config.max_retries + 1
