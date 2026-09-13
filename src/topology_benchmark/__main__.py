import argparse
import json
from dataclasses import asdict

import yaml
from pydantic import ValidationError

from topology_benchmark.application.bootstrap import build_container
from topology_benchmark.application.catalog import BenchmarkCatalog
from topology_benchmark.application.demo import serve_demo
from topology_benchmark.application.errors import BenchmarkApplicationError
from topology_benchmark.core.errors import GenerationError
from topology_benchmark.core.models import GenerationRequest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--difficulty", type=int, choices=range(1, 11), default=1)
    parser.add_argument(
        "--domain",
        default="surfaces",
        help="mathematical problem domain",
    )
    parser.add_argument("--serve", action="store_true", help="run the local visual demo")
    parser.add_argument("--host", default="127.0.0.1", help="demo bind address")
    parser.add_argument("--port", type=int, default=8000, help="demo TCP port")
    parser.add_argument(
        "--rendering-config",
        help="YAML file layered over the default surface rendering configuration",
    )
    parser.add_argument(
        "--generation-config",
        help="YAML file layered over the default surface generation profile",
    )
    args = parser.parse_args()
    try:
        container = build_container(
            rendering_config=args.rendering_config,
            generation_config=args.generation_config,
        )
    except (OSError, ValidationError, yaml.YAMLError) as error:
        parser.error(str(error))
        return
    try:
        catalog = container.resolve(BenchmarkCatalog)
    except BenchmarkApplicationError as error:
        parser.error(str(error))
        return
    if args.serve:
        serve_demo(
            host=args.host,
            port=args.port,
            catalog=catalog,
            default_domain=args.domain,
        )
        return
    try:
        problem = catalog.generate(
            domain=args.domain,
            request=GenerationRequest(seed=args.seed, difficulty=args.difficulty),
        )
    except GenerationError as error:
        parser.exit(1, f"generation failed: {error}\n")
        return
    print(json.dumps(asdict(problem), indent=2))


if __name__ == "__main__":
    main()
