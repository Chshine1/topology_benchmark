"""Lagom composition root; this is the only module aware of concrete adapters."""

from pathlib import Path

from lagom import Container

from topology_benchmark.core.composer import DefaultProblemComposer
from topology_benchmark.core.protocols import ProblemComposer
from topology_benchmark.domains.surfaces.components.display import SurfaceDiagramPlanner
from topology_benchmark.domains.surfaces.components.generation_config import (
    SurfaceGenerationConfig,
    load_generation_config,
)
from topology_benchmark.domains.surfaces.components.generator import (
    RandomSurfaceMorphismGenerator,
    RandomSurfacePresentationGenerator,
)
from topology_benchmark.domains.surfaces.components.intent import RandomSurfaceIntentGenerator
from topology_benchmark.domains.surfaces.components.rendering_config import (
    SurfaceRenderingConfig,
    load_rendering_config,
)
from topology_benchmark.domains.surfaces.components.representation import (
    MatplotlibGluingDiagramRenderer,
)
from topology_benchmark.domains.surfaces.ports import (
    SurfaceGenerator,
    SurfaceIntentGenerator,
    SurfaceMorphismGenerator,
    SurfaceRepresentation,
)


def build_container(
    rendering_config: str | Path | None = None,
    generation_config: str | Path | None = None,
) -> Container:
    rendering = load_rendering_config(rendering_config)
    generation = load_generation_config(generation_config)
    container = Container()
    container[SurfaceRenderingConfig] = rendering
    container[SurfaceGenerationConfig] = generation
    container[SurfaceDiagramPlanner] = SurfaceDiagramPlanner
    container[ProblemComposer] = DefaultProblemComposer
    container[SurfaceIntentGenerator] = RandomSurfaceIntentGenerator(generation)
    container[SurfaceGenerator] = RandomSurfacePresentationGenerator(generation)
    container[SurfaceMorphismGenerator] = RandomSurfaceMorphismGenerator(generation)
    container[SurfaceRepresentation] = MatplotlibGluingDiagramRenderer
    return container
