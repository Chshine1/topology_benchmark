from topology_benchmark.pipeline.artifacts.json_writer import write_json, write_jsonl
from topology_benchmark.pipeline.artifacts.models import (
    BenchmarkEvaluation,
    GeneratedBenchmarkRun,
)


class EvaluationArtifactWriter:
    def write(
        self,
        generated: GeneratedBenchmarkRun,
        evaluation: BenchmarkEvaluation,
    ) -> None:
        write_jsonl(
            generated.directory / "predictions.jsonl",
            [
                {
                    "id": prediction.item_id,
                    "response": prediction.response,
                    "extracted_answer": prediction.extracted_answer,
                    "correct": prediction.correct,
                    "error": prediction.error,
                }
                for prediction in evaluation.predictions
            ],
        )
        total = sum(score.total for _, score in evaluation.scores)
        correct = sum(score.correct for _, score in evaluation.scores)
        failures = sum(prediction.error is not None for prediction in evaluation.predictions)
        write_json(
            generated.directory / "summary.json",
            {
                "accuracy": correct / total if total else 0.0,
                "correct": correct,
                "total": total,
                "failed_requests": failures,
                "by_question": {
                    key: {
                        "accuracy": score.accuracy,
                        "correct": score.correct,
                        "total": score.total,
                    }
                    for key, score in evaluation.scores
                },
            },
        )
