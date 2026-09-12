import argparse
import json
from dataclasses import asdict

from topology_benchmark.application.bootstrap import build_container
from topology_benchmark.application.demo import serve_demo
from topology_benchmark.application.services import PolyhedralNetsBenchmark, SurfaceBenchmark
from topology_benchmark.domains.torus_slices.benchmark import TorusSlicesBenchmark


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--difficulty", type=int, choices=range(1, 11), default=1)
    parser.add_argument(
        "--domain",
        choices=("surfaces", "polyhedral-nets", "torus-slices"),
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
    container = build_container(
        rendering_config=args.rendering_config,
        generation_config=args.generation_config,
    )
    providers = {
        "surfaces": container.resolve(SurfaceBenchmark),
        "polyhedral-nets": container.resolve(PolyhedralNetsBenchmark),
        "torus-slices": container.resolve(TorusSlicesBenchmark),
    }
    benchmark = providers[args.domain]
    if args.serve:
        serve_demo(
            host=args.host,
            port=args.port,
            providers=providers,
            default_domain=args.domain,
        )
        return
    problem = benchmark.generate(seed=args.seed, difficulty=args.difficulty)
    print(json.dumps(asdict(problem), indent=2))


if __name__ == "__main__":
    main()
