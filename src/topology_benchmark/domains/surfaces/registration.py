from lagom import Container, Singleton

from topology_benchmark.domains.surfaces.benchmark import (
    SurfaceBenchmark,
    SurfaceQuestionCatalog,
)
from topology_benchmark.domains.surfaces.generation.config import SurfaceGenerationConfig
from topology_benchmark.domains.surfaces.generation.generator.morphism import (
    RandomSurfaceMorphismGenerator,
)
from topology_benchmark.domains.surfaces.generation.generator.object import (
    RandomSurfacePresentationGenerator,
)
from topology_benchmark.domains.surfaces.ports import (
    ISurfaceGenerator,
    ISurfaceMorphismGenerator,
    ISurfaceRepresentation,
)
from topology_benchmark.domains.surfaces.question_distribution import SurfaceQuestionDistribution
from topology_benchmark.domains.surfaces.questions import (
    BoundaryChangeQuestion,
    BoundaryComponentsQuestion,
    ComponentChangeQuestion,
    ConnectedComponentsQuestion,
    EulerChangeQuestion,
    EulerCharacteristicQuestion,
    HomologyGroupsQuestion,
    HomologyIsomorphismQuestion,
    MapInjectiveQuestion,
    MapSurjectiveQuestion,
    OrientableQuestion,
    PathIsCycleQuestion,
    PathRepresentativeQuestion,
    TargetHomologyQuestion,
    TargetOrientableQuestion,
)
from topology_benchmark.domains.surfaces.rendering.config import SurfaceRenderingConfig
from topology_benchmark.domains.surfaces.rendering.diagram import SurfaceDiagramPlanner
from topology_benchmark.domains.surfaces.rendering.renderer import (
    MatplotlibGluingDiagramRenderer,
)
from topology_benchmark.domains.surfaces.services import SurfaceAnalyzer


def add_surface_domain(
    container: Container,
    generation_config: SurfaceGenerationConfig,
    rendering_config: SurfaceRenderingConfig,
) -> Container:
    container[SurfaceGenerationConfig] = generation_config
    container[SurfaceRenderingConfig] = rendering_config
    container[SurfaceAnalyzer] = Singleton(SurfaceAnalyzer)
    container[SurfaceDiagramPlanner] = SurfaceDiagramPlanner
    container[RandomSurfacePresentationGenerator] = RandomSurfacePresentationGenerator
    container[ISurfaceGenerator] = RandomSurfacePresentationGenerator
    container[RandomSurfaceMorphismGenerator] = RandomSurfaceMorphismGenerator
    container[ISurfaceMorphismGenerator] = RandomSurfaceMorphismGenerator
    container[MatplotlibGluingDiagramRenderer] = MatplotlibGluingDiagramRenderer
    container[ISurfaceRepresentation] = MatplotlibGluingDiagramRenderer
    question_types = (
        EulerCharacteristicQuestion,
        BoundaryComponentsQuestion,
        ConnectedComponentsQuestion,
        OrientableQuestion,
        HomologyGroupsQuestion,
        PathIsCycleQuestion,
        PathRepresentativeQuestion,
        EulerChangeQuestion,
        BoundaryChangeQuestion,
        ComponentChangeQuestion,
        TargetHomologyQuestion,
        MapInjectiveQuestion,
        MapSurjectiveQuestion,
        HomologyIsomorphismQuestion,
        TargetOrientableQuestion,
    )
    container[SurfaceQuestionCatalog] = SurfaceQuestionCatalog(
        tuple(container.resolve(question_type) for question_type in question_types)
    )
    container[SurfaceQuestionDistribution] = SurfaceQuestionDistribution(
        container.resolve(SurfaceQuestionCatalog), generation_config
    )
    container[SurfaceBenchmark] = SurfaceBenchmark
    return container
