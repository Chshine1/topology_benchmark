from lagom import Container, Singleton

from topology_benchmark.pipeline.artifacts.dataset_writer import DatasetArtifactWriter
from topology_benchmark.pipeline.artifacts.evaluation_writer import EvaluationArtifactWriter
from topology_benchmark.pipeline.config import (
    EvaluationConfig,
    OpenAICompatibleModelProviderConfig,
    PipelineConfig,
)
from topology_benchmark.pipeline.dataset_generator import BenchmarkDatasetGenerator
from topology_benchmark.pipeline.evaluator import BenchmarkEvaluator
from topology_benchmark.pipeline.model_provider import (
    ModelProvider,
    OpenAICompatibleModelProvider,
    OpenAICompatibleModelProviderCredentials,
)


def add_pipeline_domain(container: Container, config: PipelineConfig) -> Container:
    container[PipelineConfig] = config
    container[EvaluationConfig] = config.evaluation
    container[DatasetArtifactWriter] = Singleton(DatasetArtifactWriter)
    container[EvaluationArtifactWriter] = Singleton(EvaluationArtifactWriter)
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
    container[ModelProvider] = OpenAICompatibleModelProvider
    container[BenchmarkEvaluator] = BenchmarkEvaluator
    return container
