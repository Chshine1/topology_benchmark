from pathlib import Path

from lagom import Container

from topology_benchmark.domains.polyhedral_nets.registration import add_polyhedral_nets_domain
from topology_benchmark.domains.surfaces.components.generation_config import (
    load_generation_config,
)
from topology_benchmark.domains.surfaces.components.rendering_config import (
    load_rendering_config,
)
from topology_benchmark.domains.surfaces.registration import add_surface_domain
from topology_benchmark.domains.torus_slices.registration import add_torus_slices_domain


def build_container(
    rendering_config: str | Path | None = None,
    generation_config: str | Path | None = None,
) -> Container:
    container = Container()
    add_surface_domain(
        container,
        load_generation_config(generation_config),
        load_rendering_config(rendering_config),
    )
    add_polyhedral_nets_domain(container)
    add_torus_slices_domain(container)
    return container
