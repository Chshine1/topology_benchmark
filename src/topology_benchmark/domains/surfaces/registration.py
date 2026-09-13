from lagom import Container, Singleton

from topology_benchmark.domains.surfaces.analysis import SurfaceAnalyzer
from topology_benchmark.domains.surfaces.benchmark import (
    SurfaceBenchmark,
    SurfaceQuestionCatalog,
)
from topology_benchmark.domains.surfaces.components.display import SurfaceDiagramPlanner
from topology_benchmark.domains.surfaces.components.generation_config import (
    SurfaceGenerationConfig,
)
from topology_benchmark.domains.surfaces.components.generator import (
    RandomSurfaceMorphismGenerator,
    RandomSurfacePresentationGenerator,
)
from topology_benchmark.domains.surfaces.components.rendering_config import (
    SurfaceRenderingConfig,
)
from topology_benchmark.domains.surfaces.components.representation import (
    MatplotlibGluingDiagramRenderer,
)
from topology_benchmark.domains.surfaces.distributions import SurfaceDefaultQuestionDistribution
from topology_benchmark.domains.surfaces.ports import (
    SurfaceGenerator,
    SurfaceMorphismGenerator,
    SurfaceRepresentation,
)
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
    container[SurfaceGenerator] = RandomSurfacePresentationGenerator
    container[RandomSurfaceMorphismGenerator] = RandomSurfaceMorphismGenerator
    container[SurfaceMorphismGenerator] = RandomSurfaceMorphismGenerator
    container[MatplotlibGluingDiagramRenderer] = MatplotlibGluingDiagramRenderer
    container[SurfaceRepresentation] = MatplotlibGluingDiagramRenderer
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
    container[SurfaceDefaultQuestionDistribution] = SurfaceDefaultQuestionDistribution(
        container.resolve(SurfaceQuestionCatalog), generation_config
    )
    container[SurfaceBenchmark] = SurfaceBenchmark
    return container
