from pathlib import Path

from lagom import Container

from topology_benchmark.application.catalog import BenchmarkCatalog, BenchmarkRegistration
from topology_benchmark.application.configuration import (
    SURFACE_GENERATION_DEFAULTS,
    SURFACE_RENDERING_DEFAULTS,
)
from topology_benchmark.domains.polyhedral_nets.abstractions import (
    PolyhedralProblemRecipeCatalog,
    PolyhedralProblemRecipeDistribution,
)
from topology_benchmark.domains.polyhedral_nets.config import PolyhedralDomainConfig
from topology_benchmark.domains.polyhedral_nets.registration import add_polyhedral_nets_domain
from topology_benchmark.domains.surfaces.abstractions import (
    SurfaceProblemRecipeCatalog,
    SurfaceProblemRecipeDistribution,
)
from topology_benchmark.domains.surfaces.generation.config import load_generation_config
from topology_benchmark.domains.surfaces.registration import add_surface_domain
from topology_benchmark.domains.surfaces.rendering.config import load_rendering_config
from topology_benchmark.domains.torus_slices.abstractions import (
    TorusProblemRecipeCatalog,
    TorusProblemRecipeDistribution,
)
from topology_benchmark.domains.torus_slices.config import TorusDomainConfig
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
                container.resolve(SurfaceProblemRecipeCatalog),
                container.resolve(SurfaceProblemRecipeDistribution),
            ),
            BenchmarkRegistration(
                "polyhedral-nets",
                container.resolve(PolyhedralProblemRecipeCatalog),
                container.resolve(PolyhedralProblemRecipeDistribution),
            ),
            BenchmarkRegistration(
                "torus-slices",
                container.resolve(TorusProblemRecipeCatalog),
                container.resolve(TorusProblemRecipeDistribution),
            ),
        )
    )
    return container
