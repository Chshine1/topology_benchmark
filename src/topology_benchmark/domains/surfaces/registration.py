from lagom import Container, Singleton

from topology_benchmark.domains.surfaces.analysis import SurfaceAnalyzer
from topology_benchmark.domains.surfaces.components.display import SurfaceDiagramPlanner
from topology_benchmark.domains.surfaces.components.generation_config import (
    SurfaceGenerationConfig,
)
from topology_benchmark.domains.surfaces.components.generator import (
    RandomSurfaceMorphismGenerator,
    RandomSurfacePresentationGenerator,
)
from topology_benchmark.domains.surfaces.components.intent import RandomSurfaceIntentGenerator
from topology_benchmark.domains.surfaces.components.rendering_config import (
    SurfaceRenderingConfig,
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


def add_surface_domain(
    container: Container,
    generation_config: SurfaceGenerationConfig,
    rendering_config: SurfaceRenderingConfig,
) -> Container:
    container[SurfaceGenerationConfig] = generation_config
    container[SurfaceRenderingConfig] = rendering_config
    container[SurfaceAnalyzer] = Singleton(SurfaceAnalyzer)
    container[SurfaceDiagramPlanner] = SurfaceDiagramPlanner
    container[SurfaceIntentGenerator] = RandomSurfaceIntentGenerator
    container[SurfaceGenerator] = RandomSurfacePresentationGenerator
    container[SurfaceMorphismGenerator] = RandomSurfaceMorphismGenerator
    container[SurfaceRepresentation] = MatplotlibGluingDiagramRenderer
    return container
