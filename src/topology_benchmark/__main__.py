import argparse
import json
from dataclasses import asdict

import yaml
from pydantic import ValidationError

from topology_benchmark.application.bootstrap import build_container
from topology_benchmark.application.catalog import BenchmarkCatalog
from topology_benchmark.application.configuration import (
    POLYHEDRAL_DOMAIN_CONFIG,
    SURFACE_DOMAIN_CONFIG,
    TORUS_DOMAIN_CONFIG,
)
from topology_benchmark.application.demo import serve_demo
from topology_benchmark.application.errors import BenchmarkApplicationError
from topology_benchmark.core.errors import ConfigurationError, GenerationError
from topology_benchmark.core.problem.models import GenerationRequest


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
    parser.add_argument("--surface-config", help="complete surface-domain YAML configuration")
    parser.add_argument("--polyhedral-config", help="complete polyhedral-domain YAML configuration")
    parser.add_argument("--torus-config", help="complete torus-domain YAML configuration")
    args = parser.parse_args()
    try:
        container = build_container(
            surface_config=args.surface_config or SURFACE_DOMAIN_CONFIG,
            polyhedral_config=args.polyhedral_config or POLYHEDRAL_DOMAIN_CONFIG,
            torus_config=args.torus_config or TORUS_DOMAIN_CONFIG,
        )
    except (OSError, ConfigurationError, ValidationError, yaml.YAMLError) as error:
        parser.error(str(error))
        return
    catalog = container.resolve(BenchmarkCatalog)
    try:
        catalog.require_domain(args.domain)
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
    except BenchmarkApplicationError as error:
        parser.error(str(error))
        return
    except GenerationError as error:
        parser.exit(1, f"generation failed: {error}\n")
        return
    print(json.dumps(asdict(problem), indent=2))


if __name__ == "__main__":
    main()
