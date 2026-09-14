from pathlib import Path

from lagom import Container

from topology_benchmark.application.catalog import BenchmarkCatalog, BenchmarkRegistration
from topology_benchmark.application.configuration import (
    SURFACE_GENERATION_DEFAULTS,
    SURFACE_RENDERING_DEFAULTS,
)
from topology_benchmark.domains.polyhedral_nets.benchmark import (
    PolyhedralNetsBenchmark,
    PolyhedralQuestionCatalog,
)
from topology_benchmark.domains.polyhedral_nets.config import PolyhedralDomainConfig
from topology_benchmark.domains.polyhedral_nets.question_distribution import (
    PolyhedralQuestionDistribution,
)
from topology_benchmark.domains.polyhedral_nets.registration import add_polyhedral_nets_domain
from topology_benchmark.domains.surfaces.benchmark import SurfaceBenchmark, SurfaceQuestionCatalog
from topology_benchmark.domains.surfaces.generation.config import load_generation_config
from topology_benchmark.domains.surfaces.question_distribution import SurfaceQuestionDistribution
from topology_benchmark.domains.surfaces.registration import add_surface_domain
from topology_benchmark.domains.surfaces.rendering.config import load_rendering_config
from topology_benchmark.domains.torus_slices.benchmark import (
    TorusQuestionCatalog,
    TorusSlicesBenchmark,
)
from topology_benchmark.domains.torus_slices.config import TorusDomainConfig
from topology_benchmark.domains.torus_slices.question_distribution import (
    TorusQuestionDistribution,
)
from topology_benchmark.domains.torus_slices.registration import add_torus_slices_domain


def build_container(
    rendering_config: str | Path | None = None,
    generation_config: str | Path | None = None,
) -> Container:
    container = Container()
    add_surface_domain(
        container,
        load_generation_config(SURFACE_GENERATION_DEFAULTS, generation_config),
        load_rendering_config(SURFACE_RENDERING_DEFAULTS, rendering_config),
    )
    add_polyhedral_nets_domain(container, PolyhedralDomainConfig())
    add_torus_slices_domain(container, TorusDomainConfig())
    container[BenchmarkCatalog] = BenchmarkCatalog(
        (
            BenchmarkRegistration(
                "surfaces",
                container.resolve(SurfaceBenchmark),
                container.resolve(SurfaceQuestionCatalog),
                container.resolve(SurfaceQuestionDistribution),
            ),
            BenchmarkRegistration(
                "polyhedral-nets",
                container.resolve(PolyhedralNetsBenchmark),
                container.resolve(PolyhedralQuestionCatalog),
                container.resolve(PolyhedralQuestionDistribution),
            ),
            BenchmarkRegistration(
                "torus-slices",
                container.resolve(TorusSlicesBenchmark),
                container.resolve(TorusQuestionCatalog),
                container.resolve(TorusQuestionDistribution),
            ),
        )
    )
    return container
