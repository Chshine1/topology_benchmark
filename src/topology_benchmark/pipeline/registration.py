from lagom import Container, Singleton

from topology_benchmark.pipeline.config import (
    DatasetConfig,
    EvaluationConfig,
    ModelEvaluationConfig,
    OpenAICompatibleModelProviderConfig,
)
from topology_benchmark.pipeline.dataset.artifact_writer import DatasetArtifactWriter
from topology_benchmark.pipeline.dataset.planner import DatasetPlanner
from topology_benchmark.pipeline.dataset_generator import BenchmarkDatasetGenerator
from topology_benchmark.pipeline.evaluation.answer_scorer import AnswerScorer, IAnswerScorer
from topology_benchmark.pipeline.evaluation.artifact_store import EvaluationArtifactStore
from topology_benchmark.pipeline.evaluation.model_provider import (
    IModelProvider,
    OpenAICompatibleModelProvider,
    OpenAICompatibleModelProviderCredentials,
)
from topology_benchmark.pipeline.evaluator import BenchmarkEvaluator


def add_dataset_generation(container: Container, config: DatasetConfig) -> Container:
    container[DatasetConfig] = config
    container[DatasetArtifactWriter] = Singleton(DatasetArtifactWriter)
    container[DatasetPlanner] = DatasetPlanner
    container[BenchmarkDatasetGenerator] = BenchmarkDatasetGenerator
    return container


def add_model_evaluation(
    container: Container,
    config: ModelEvaluationConfig,
    credentials: OpenAICompatibleModelProviderCredentials,
) -> Container:
    container[ModelEvaluationConfig] = config
    container[EvaluationConfig] = config.evaluation
    container[OpenAICompatibleModelProviderConfig] = config.model_provider
    container[OpenAICompatibleModelProviderCredentials] = credentials
    container[OpenAICompatibleModelProvider] = OpenAICompatibleModelProvider
    container[IModelProvider] = OpenAICompatibleModelProvider
    container[AnswerScorer] = Singleton(AnswerScorer)
    container[IAnswerScorer] = AnswerScorer
    container[EvaluationArtifactStore] = EvaluationArtifactStore
    container[BenchmarkEvaluator] = BenchmarkEvaluator
    return container
