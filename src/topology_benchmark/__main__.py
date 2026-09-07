"""Generate a sample problem from the command line."""

import argparse
import json
from dataclasses import asdict

from topology_benchmark.application.bootstrap import build_container
from topology_benchmark.application.demo import serve_demo
from topology_benchmark.application.services import SurfaceBenchmark


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--difficulty", type=int, choices=range(1, 11), default=1)
    parser.add_argument("--serve", action="store_true", help="run the local visual demo")
    parser.add_argument("--host", default="127.0.0.1", help="demo bind address")
    parser.add_argument("--port", type=int, default=8000, help="demo TCP port")
    args = parser.parse_args()
    benchmark = build_container().resolve(SurfaceBenchmark)
    if args.serve:
        serve_demo(benchmark, host=args.host, port=args.port)
        return
    problem = benchmark.generate(seed=args.seed, difficulty=args.difficulty)
    print(json.dumps(asdict(problem), indent=2))


if __name__ == "__main__":
    main()
