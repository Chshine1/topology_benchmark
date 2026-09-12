import argparse

from topology_benchmark.pipeline import BenchmarkPipeline, load_pipeline_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="pipeline YAML configuration")
    parser.add_argument(
        "--generate-only", action="store_true", help="generate artifacts without calling a model"
    )
    args = parser.parse_args()
    pipeline = BenchmarkPipeline(load_pipeline_config(args.config))
    output = pipeline.run(evaluate=not args.generate_only)
    print(output)


if __name__ == "__main__":
    main()
