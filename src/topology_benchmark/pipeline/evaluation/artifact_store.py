import json
from collections import Counter
from pathlib import Path
from typing import Any

from topology_benchmark.pipeline.config import ModelEvaluationConfig
from topology_benchmark.pipeline.dataset.models import GeneratedBenchmarkRun
from topology_benchmark.pipeline.evaluation.answer_scorer import ANSWER_SCORER_VERSION
from topology_benchmark.pipeline.evaluation.identity import EVALUATION_SCHEMA_VERSION, evaluation_id
from topology_benchmark.pipeline.evaluation.model_provider import OPENAI_COMPATIBLE_PROVIDER_VERSION
from topology_benchmark.pipeline.evaluation.models import (
    BenchmarkEvaluation,
    ModelPrediction,
    QuestionScore,
)
from topology_benchmark.pipeline.serialization.json_writer import (
    write_json_atomic,
    write_jsonl_atomic,
)


class EvaluationArtifactStore:
    def __init__(self, config: ModelEvaluationConfig) -> None:
        self._config = config

    def open(self, dataset: GeneratedBenchmarkRun) -> EvaluationArtifactSession:
        identifier = evaluation_id(dataset, self._config)
        directory = dataset.directory / "evaluations" / identifier
        predictions = directory / "predictions"
        predictions.mkdir(parents=True, exist_ok=True)
        manifest = _evaluation_manifest(dataset, self._config, identifier)
        manifest_path = directory / "manifest.private.json"
        if manifest_path.exists():
            if _read_json(manifest_path) != manifest:
                raise ValueError(
                    "existing evaluation manifest does not match the requested evaluation"
                )
        else:
            write_json_atomic(manifest_path, manifest)
        return EvaluationArtifactSession(directory, predictions)


class EvaluationArtifactSession:
    def __init__(self, directory: Path, predictions_directory: Path) -> None:
        self.directory = directory
        self._predictions_directory = predictions_directory

    def load_predictions(self) -> dict[str, ModelPrediction]:
        predictions: dict[str, ModelPrediction] = {}
        for path in sorted(self._predictions_directory.glob("*.json")):
            record = _read_json(path)
            prediction = _prediction_from_record(record)
            if path.stem != prediction.item_id:
                raise ValueError(f"prediction filename does not match item ID: {path.name}")
            predictions[prediction.item_id] = prediction
        return predictions

    def write_prediction(self, prediction: ModelPrediction) -> None:
        write_json_atomic(
            self._predictions_directory / f"{prediction.item_id}.json",
            _prediction_record(prediction),
        )

    def publish(
        self, dataset: GeneratedBenchmarkRun, predictions: dict[str, ModelPrediction]
    ) -> None:
        expected_ids = {item.item_id for item in dataset.items}
        if predictions.keys() != expected_ids:
            raise ValueError("cannot publish an incomplete evaluation")
        ordered = tuple(predictions[item.item_id] for item in dataset.items)
        correct = Counter[str]()
        totals = Counter[str]()
        for item, prediction in zip(dataset.items, ordered, strict=True):
            key = f"{item.domain}/{item.problem.recipe_id}"
            totals[key] += 1
            correct[key] += int(prediction.correct)
        evaluation = BenchmarkEvaluation(
            ordered,
            tuple(
                (key, QuestionScore(correct[key], count)) for key, count in sorted(totals.items())
            ),
        )
        write_jsonl_atomic(
            self.directory / "predictions.jsonl",
            [_prediction_record(prediction) for prediction in ordered],
        )
        write_json_atomic(self.directory / "summary.json", _summary(evaluation))


def _evaluation_manifest(
    dataset: GeneratedBenchmarkRun,
    config: ModelEvaluationConfig,
    identifier: str,
) -> dict[str, object]:
    provider = config.model_provider
    return {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "evaluation_id": identifier,
        "dataset_id": dataset.dataset_id,
        "dataset_content_id": dataset.content_id,
        "provider_version": OPENAI_COMPATIBLE_PROVIDER_VERSION,
        "scorer_version": ANSWER_SCORER_VERSION,
        "model": provider.model,
        "base_url": provider.base_url.rstrip("/"),
        "timeout_seconds": provider.timeout_seconds,
        "extra_header_names": sorted(provider.extra_headers),
        "max_retries": config.evaluation.max_retries,
    }


def _prediction_record(prediction: ModelPrediction) -> dict[str, object]:
    return {
        "id": prediction.item_id,
        "response": prediction.response,
        "extracted_answer": prediction.extracted_answer,
        "correct": prediction.correct,
        "error": prediction.error,
        "attempts": prediction.attempts,
    }


def _prediction_from_record(record: dict[str, Any]) -> ModelPrediction:
    item_id = record.get("id")
    response = record.get("response")
    extracted = record.get("extracted_answer")
    correct = record.get("correct")
    error = record.get("error")
    attempts = record.get("attempts")
    if not isinstance(item_id, str) or not item_id:
        raise ValueError("prediction has an invalid item ID")
    if not isinstance(response, str) or not isinstance(extracted, str):
        raise ValueError(f"prediction {item_id} has invalid response text")
    if not isinstance(correct, bool) or not (error is None or isinstance(error, str)):
        raise ValueError(f"prediction {item_id} has invalid result fields")
    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 1:
        raise ValueError(f"prediction {item_id} has an invalid attempt count")
    return ModelPrediction(item_id, response, extracted, correct, error, attempts)


def _summary(evaluation: BenchmarkEvaluation) -> dict[str, object]:
    total = sum(score.total for _, score in evaluation.scores)
    correct = sum(score.correct for _, score in evaluation.scores)
    failures = sum(prediction.error is not None for prediction in evaluation.predictions)
    return {
        "accuracy": correct / total if total else 0.0,
        "correct": correct,
        "total": total,
        "failed_requests": failures,
        "by_question": {
            key: {"accuracy": score.accuracy, "correct": score.correct, "total": score.total}
            for key, score in evaluation.scores
        },
    }


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value
