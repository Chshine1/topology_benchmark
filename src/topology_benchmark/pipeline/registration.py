from lagom import Container, Singleton

from topology_benchmark.pipeline.config import (
    EvaluationConfig,
    OpenAICompatibleModelProviderConfig,
    PipelineConfig,
)
from topology_benchmark.pipeline.dataset.artifact_writer import DatasetArtifactWriter
from topology_benchmark.pipeline.dataset_generator import BenchmarkDatasetGenerator
from topology_benchmark.pipeline.evaluation.answer_scorer import AnswerScorer, IAnswerScorer
from topology_benchmark.pipeline.evaluation.artifact_writer import EvaluationArtifactWriter
from topology_benchmark.pipeline.evaluation.model_provider import (
    IModelProvider,
    OpenAICompatibleModelProvider,
    OpenAICompatibleModelProviderCredentials,
)
from topology_benchmark.pipeline.evaluator import BenchmarkEvaluator


def add_pipeline_domain(container: Container, config: PipelineConfig) -> Container:
    container[PipelineConfig] = config
    container[EvaluationConfig] = config.evaluation
    container[DatasetArtifactWriter] = Singleton(DatasetArtifactWriter)
    container[EvaluationArtifactWriter] = Singleton(EvaluationArtifactWriter)
    container[AnswerScorer] = Singleton(AnswerScorer)
    container[IAnswerScorer] = AnswerScorer
    container[BenchmarkDatasetGenerator] = BenchmarkDatasetGenerator
    return container


def add_model_evaluation(
    container: Container,
    config: OpenAICompatibleModelProviderConfig,
    credentials: OpenAICompatibleModelProviderCredentials,
) -> Container:
    container[OpenAICompatibleModelProviderConfig] = config
    container[OpenAICompatibleModelProviderCredentials] = credentials
    container[OpenAICompatibleModelProvider] = OpenAICompatibleModelProvider
    container[IModelProvider] = OpenAICompatibleModelProvider
    container[BenchmarkEvaluator] = BenchmarkEvaluator
    return container
