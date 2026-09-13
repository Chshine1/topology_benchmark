import argparse
import os

import yaml
from pydantic import ValidationError

from topology_benchmark.application.bootstrap import build_container
from topology_benchmark.application.errors import (
    BenchmarkApplicationError,
    InvalidApplicationRequestError,
)
from topology_benchmark.core.errors import GenerationError
from topology_benchmark.pipeline import (
    BenchmarkDatasetGenerator,
    load_pipeline_config,
)
from topology_benchmark.pipeline.evaluator import BenchmarkEvaluator
from topology_benchmark.pipeline.model_provider import OpenAICompatibleModelProviderCredentials
from topology_benchmark.pipeline.registration import add_model_evaluation, add_pipeline_domain


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="pipeline YAML configuration")
    parser.add_argument(
        "--generate-only", action="store_true", help="generate artifacts without calling a model"
    )
    args = parser.parse_args()
    evaluator: BenchmarkEvaluator | None = None
    try:
        config = load_pipeline_config(args.config)
        container = build_container()
        add_pipeline_domain(container, config)
        dataset_generator = container.resolve(BenchmarkDatasetGenerator)
        if not args.generate_only:
            if config.model_provider is None:
                raise InvalidApplicationRequestError(
                    "evaluation requested but no model provider is configured"
                )
            api_key = os.environ.get(config.model_provider.api_key_env)
            if not api_key:
                raise InvalidApplicationRequestError(
                    f"missing API key environment variable {config.model_provider.api_key_env}"
                )
            add_model_evaluation(
                container,
                config.model_provider,
                OpenAICompatibleModelProviderCredentials(api_key),
            )
            evaluator = container.resolve(BenchmarkEvaluator)
    except (OSError, ValidationError, yaml.YAMLError, BenchmarkApplicationError) as error:
        parser.error(str(error))
        return
    try:
        if evaluator is None:
            output = dataset_generator.generate().directory
        else:
            generated = dataset_generator.generate()
            evaluator.evaluate(generated)
            output = generated.directory
    except BenchmarkApplicationError as error:
        parser.error(str(error))
        return
    except GenerationError as error:
        parser.exit(1, f"generation failed: {error}\n")
        return
    print(output)


if __name__ == "__main__":
    main()
