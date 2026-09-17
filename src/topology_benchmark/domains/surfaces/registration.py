from lagom import Container, Singleton

from topology_benchmark.core.errors import ConfigurationError
from topology_benchmark.core.problem.recipe_distribution import DifficultyProblemRecipeWeight
from topology_benchmark.domains.surfaces.abstractions import (
    ISurfaceGenerator,
    ISurfaceMorphismGenerator,
    ISurfaceRenderBackend,
    ISurfaceRepresentation,
    SurfaceProblemRecipeCatalog,
    SurfaceProblemRecipeDistribution,
)
from topology_benchmark.domains.surfaces.config import SurfaceDomainConfig
from topology_benchmark.domains.surfaces.generation.config import SurfaceGenerationConfig
from topology_benchmark.domains.surfaces.generation.generator.morphism import (
    RandomSurfaceMorphismGenerator,
)
from topology_benchmark.domains.surfaces.generation.generator.object import (
    RandomSurfacePresentationGenerator,
)
from topology_benchmark.domains.surfaces.recipes import (
    BoundaryChangeProblemRecipe,
    BoundaryComponentsProblemRecipe,
    ComponentChangeProblemRecipe,
    ConnectedComponentsProblemRecipe,
    EulerChangeProblemRecipe,
    EulerCharacteristicProblemRecipe,
    HomologyGroupsProblemRecipe,
    HomologyIsomorphismProblemRecipe,
    MapInjectiveProblemRecipe,
    MapSurjectiveProblemRecipe,
    OrientableProblemRecipe,
    PathIsCycleProblemRecipe,
    PathRepresentativeProblemRecipe,
    TargetHomologyProblemRecipe,
    TargetOrientableProblemRecipe,
)
from topology_benchmark.domains.surfaces.rendering.backend.matplotlib_svg import (
    MatplotlibSurfaceRenderBackend,
)
from topology_benchmark.domains.surfaces.rendering.config import SurfaceRenderingConfig
from topology_benchmark.domains.surfaces.rendering.diagram_planner import SurfaceDiagramPlanner
from topology_benchmark.domains.surfaces.rendering.representation import (
    SurfaceRepresentation,
)
from topology_benchmark.domains.surfaces.services import SurfaceAnalyzer


def add_surface_domain(
    container: Container,
    config: SurfaceDomainConfig,
) -> Container:
    generation_config = config.generation
    rendering_config = config.rendering
    container[SurfaceDomainConfig] = config
    container[SurfaceGenerationConfig] = generation_config
    container[SurfaceRenderingConfig] = rendering_config
    container[SurfaceAnalyzer] = Singleton(SurfaceAnalyzer)
    container[SurfaceDiagramPlanner] = SurfaceDiagramPlanner
    container[RandomSurfacePresentationGenerator] = RandomSurfacePresentationGenerator
    container[ISurfaceGenerator] = RandomSurfacePresentationGenerator
    container[RandomSurfaceMorphismGenerator] = RandomSurfaceMorphismGenerator
    container[ISurfaceMorphismGenerator] = RandomSurfaceMorphismGenerator
    container[MatplotlibSurfaceRenderBackend] = MatplotlibSurfaceRenderBackend
    container[ISurfaceRenderBackend] = MatplotlibSurfaceRenderBackend
    container[SurfaceRepresentation] = SurfaceRepresentation
    container[ISurfaceRepresentation] = SurfaceRepresentation
    recipe_types = (
        EulerCharacteristicProblemRecipe,
        BoundaryComponentsProblemRecipe,
        ConnectedComponentsProblemRecipe,
        OrientableProblemRecipe,
        HomologyGroupsProblemRecipe,
        PathIsCycleProblemRecipe,
        PathRepresentativeProblemRecipe,
        EulerChangeProblemRecipe,
        BoundaryChangeProblemRecipe,
        ComponentChangeProblemRecipe,
        TargetHomologyProblemRecipe,
        MapInjectiveProblemRecipe,
        MapSurjectiveProblemRecipe,
        HomologyIsomorphismProblemRecipe,
        TargetOrientableProblemRecipe,
    )
    catalog = SurfaceProblemRecipeCatalog(
        tuple(container.resolve(recipe_type) for recipe_type in recipe_types)
    )
    configured_ids = set(generation_config.recipe_weights)
    registered_ids = set(catalog)
    if configured_ids != registered_ids:
        missing = registered_ids - configured_ids
        unknown = configured_ids - registered_ids
        raise ConfigurationError(
            f"surface distribution and catalog disagree; missing={sorted(missing)}, "
            f"unknown={sorted(unknown)}"
        )
    container[SurfaceProblemRecipeCatalog] = catalog
    container[SurfaceProblemRecipeDistribution] = SurfaceProblemRecipeDistribution(
        tuple(
            DifficultyProblemRecipeWeight(catalog[recipe_id], weights.anchors)
            for recipe_id, weights in generation_config.recipe_weights.items()
        )
    )
    return container
