import argparse

import yaml
from pydantic import ValidationError

from topology_benchmark.application.bootstrap import build_container
from topology_benchmark.application.catalog import BenchmarkCatalog
from topology_benchmark.application.errors import BenchmarkApplicationError
from topology_benchmark.core.errors import GenerationError
from topology_benchmark.pipeline import BenchmarkPipeline, load_pipeline_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="pipeline YAML configuration")
    parser.add_argument(
        "--generate-only", action="store_true", help="generate artifacts without calling a model"
    )
    args = parser.parse_args()
    try:
        config = load_pipeline_config(args.config)
        container = build_container()
        pipeline = BenchmarkPipeline(config, container.resolve(BenchmarkCatalog))
    except (OSError, ValidationError, yaml.YAMLError, BenchmarkApplicationError) as error:
        parser.error(str(error))
        return
    try:
        output = pipeline.run(evaluate=not args.generate_only)
    except BenchmarkApplicationError as error:
        parser.error(str(error))
        return
    except GenerationError as error:
        parser.exit(1, f"generation failed: {error}\n")
        return
    print(output)


if __name__ == "__main__":
    main()
