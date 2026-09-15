from pathlib import Path

from lagom import Container

from topology_benchmark.application.catalog import BenchmarkCatalog, BenchmarkRegistration
from topology_benchmark.application.configuration import (
    POLYHEDRAL_DOMAIN_CONFIG,
    SURFACE_DOMAIN_CONFIG,
    TORUS_DOMAIN_CONFIG,
)
from topology_benchmark.core.problem.identity import canonical_hash
from topology_benchmark.domains.polyhedral_nets.abstractions import (
    PolyhedralProblemRecipeCatalog,
    PolyhedralProblemRecipeDistribution,
)
from topology_benchmark.domains.polyhedral_nets.config import load_polyhedral_domain_config
from topology_benchmark.domains.polyhedral_nets.registration import add_polyhedral_nets_domain
from topology_benchmark.domains.surfaces.abstractions import (
    SurfaceProblemRecipeCatalog,
    SurfaceProblemRecipeDistribution,
)
from topology_benchmark.domains.surfaces.config import load_surface_domain_config
from topology_benchmark.domains.surfaces.registration import add_surface_domain
from topology_benchmark.domains.surfaces.rendering.backend.blender import BlenderRuntimeConfig
from topology_benchmark.domains.torus_slices.abstractions import (
    TorusProblemRecipeCatalog,
    TorusProblemRecipeDistribution,
)
from topology_benchmark.domains.torus_slices.config import load_torus_domain_config
from topology_benchmark.domains.torus_slices.registration import add_torus_slices_domain


def build_container(
    surface_config: str | Path = SURFACE_DOMAIN_CONFIG,
    polyhedral_config: str | Path = POLYHEDRAL_DOMAIN_CONFIG,
    torus_config: str | Path = TORUS_DOMAIN_CONFIG,
    blender_executable: str = "blender",
    blender_timeout_seconds: float = 120.0,
) -> Container:
    container = Container()
    surface_domain_config = load_surface_domain_config(surface_config)
    polyhedral_domain_config = load_polyhedral_domain_config(polyhedral_config)
    torus_domain_config = load_torus_domain_config(torus_config)
    add_surface_domain(
        container,
        surface_domain_config,
        BlenderRuntimeConfig(blender_executable, blender_timeout_seconds),
    )
    add_polyhedral_nets_domain(container, polyhedral_domain_config)
    add_torus_slices_domain(container, torus_domain_config)
    container[BenchmarkCatalog] = BenchmarkCatalog(
        (
            BenchmarkRegistration(
                "surfaces",
                container.resolve(SurfaceProblemRecipeCatalog),
                container.resolve(SurfaceProblemRecipeDistribution),
                canonical_hash(surface_domain_config),
            ),
            BenchmarkRegistration(
                "polyhedral-nets",
                container.resolve(PolyhedralProblemRecipeCatalog),
                container.resolve(PolyhedralProblemRecipeDistribution),
                canonical_hash(polyhedral_domain_config),
            ),
            BenchmarkRegistration(
                "torus-slices",
                container.resolve(TorusProblemRecipeCatalog),
                container.resolve(TorusProblemRecipeDistribution),
                canonical_hash(torus_domain_config),
            ),
        )
    )
    return container
