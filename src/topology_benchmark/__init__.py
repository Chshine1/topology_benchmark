"""Composable topology and geometry benchmark generation."""

from topology_benchmark.application.bootstrap import build_container
from topology_benchmark.application.services import SurfaceBenchmark
from topology_benchmark.core.models import Problem

__all__ = ["Problem", "SurfaceBenchmark", "build_container"]
