import argparse
import os
from pathlib import Path

import yaml
from lagom import Container
from pydantic import ValidationError

from topology_benchmark.application.bootstrap import build_container
from topology_benchmark.application.errors import (
    BenchmarkApplicationError,
    InvalidApplicationRequestError,
)
from topology_benchmark.core.errors import ConfigurationError, GenerationError
from topology_benchmark.pipeline import (
    BenchmarkDatasetGenerator,
    load_dataset_config,
    load_evaluation_config,
)
from topology_benchmark.pipeline.dataset.artifact_reader import DatasetArtifactReader
from topology_benchmark.pipeline.evaluation.model_provider import (
    OpenAICompatibleModelProviderCredentials,
)
from topology_benchmark.pipeline.evaluator import BenchmarkEvaluator
from topology_benchmark.pipeline.registration import add_dataset_generation, add_model_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="generate a persisted benchmark dataset")
    generate.add_argument("config", help="dataset-generation YAML configuration")
    evaluate = commands.add_parser("evaluate", help="evaluate a model on a persisted dataset")
    evaluate.add_argument("dataset", help="generated dataset directory")
    evaluate.add_argument("config", help="model-evaluation YAML configuration")
    args = parser.parse_args()
    try:
        output = (
            _generate(args.config)
            if args.command == "generate"
            else _evaluate(args.dataset, args.config)
        )
    except (
        OSError,
        ConfigurationError,
        ValidationError,
        yaml.YAMLError,
        BenchmarkApplicationError,
        ValueError,
    ) as error:
        parser.error(str(error))
        return
    except GenerationError as error:
        parser.exit(1, f"generation failed: {error}\n")
        return
    print(output)


def _generate(config_path: str) -> Path:
    config = load_dataset_config(config_path)
    container = build_container()
    add_dataset_generation(container, config)
    return container.resolve(BenchmarkDatasetGenerator).generate().directory


def _evaluate(dataset_path: str, config_path: str) -> Path:
    config = load_evaluation_config(config_path)
    api_key = os.environ.get(config.model_provider.api_key_env)
    if not api_key:
        raise InvalidApplicationRequestError(
            f"missing API key environment variable {config.model_provider.api_key_env}"
        )
    dataset = DatasetArtifactReader().read(dataset_path)
    container = Container()
    add_model_evaluation(container, config, OpenAICompatibleModelProviderCredentials(api_key))
    return container.resolve(BenchmarkEvaluator).evaluate(dataset)


if __name__ == "__main__":
    main()
