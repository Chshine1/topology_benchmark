"""Composable topology and geometry benchmark generation."""

from topology_benchmark.application.bootstrap import build_container
from topology_benchmark.application.services import (
    PolyhedralNetBenchmark,
    PolyhedralNetsBenchmark,
    SurfaceBenchmark,
)
from topology_benchmark.core.models import Problem
from topology_benchmark.domains.torus_slices.benchmark import TorusSlicesBenchmark

__all__ = [
    "PolyhedralNetBenchmark",
    "PolyhedralNetsBenchmark",
    "Problem",
    "SurfaceBenchmark",
    "TorusSlicesBenchmark",
    "build_container",
]
