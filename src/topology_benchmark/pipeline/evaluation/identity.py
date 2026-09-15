from topology_benchmark.core.problem.identity import canonical_hash
from topology_benchmark.pipeline.config import ModelEvaluationConfig
from topology_benchmark.pipeline.dataset.models import GeneratedBenchmarkRun
from topology_benchmark.pipeline.evaluation.answer_scorer import ANSWER_SCORER_VERSION
from topology_benchmark.pipeline.evaluation.model_provider import OPENAI_COMPATIBLE_PROVIDER_VERSION

EVALUATION_SCHEMA_VERSION = 1


def evaluation_id(dataset: GeneratedBenchmarkRun, config: ModelEvaluationConfig) -> str:
    provider = config.model_provider
    identity = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "dataset_content_id": dataset.content_id,
        "provider_version": OPENAI_COMPATIBLE_PROVIDER_VERSION,
        "model": provider.model,
        "base_url": provider.base_url.rstrip("/"),
        "timeout_seconds": provider.timeout_seconds,
        "extra_headers": {
            name: canonical_hash(value) for name, value in sorted(provider.extra_headers.items())
        },
        "max_retries": config.evaluation.max_retries,
        "scorer_version": ANSWER_SCORER_VERSION,
    }
    return canonical_hash(identity)[:16]
