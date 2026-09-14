from lagom import Container, Singleton

from topology_benchmark.core.problem.recipe_distribution import DifficultyProblemRecipeWeight
from topology_benchmark.domains.torus_slices.abstractions import (
    ITorusSliceGenerator,
    ITorusSliceRepresentation,
    TorusProblemRecipeCatalog,
    TorusProblemRecipeDistribution,
)
from topology_benchmark.domains.torus_slices.config import (
    TorusCountConfig,
    TorusDomainConfig,
    TorusLinkConfig,
)
from topology_benchmark.domains.torus_slices.generation.torus_slice_generator import (
    RandomTorusSliceGenerator,
)
from topology_benchmark.domains.torus_slices.recipes import (
    CompletelyUnlinkedProblemRecipe,
    LinkedPairCountProblemRecipe,
    LinkedProblemRecipe,
    TorusCountProblemRecipe,
)
from topology_benchmark.domains.torus_slices.rendering.svg_renderer import TorusSliceSvgRenderer
from topology_benchmark.domains.torus_slices.services.torus_family_analyzer import (
    TorusFamilyAnalyzer,
)


def add_torus_slices_domain(container: Container, config: TorusDomainConfig) -> Container:
    container[RandomTorusSliceGenerator] = RandomTorusSliceGenerator
    container[ITorusSliceGenerator] = RandomTorusSliceGenerator
    container[TorusFamilyAnalyzer] = Singleton(TorusFamilyAnalyzer)
    container[TorusSliceSvgRenderer] = TorusSliceSvgRenderer
    container[ITorusSliceRepresentation] = TorusSliceSvgRenderer
    container[TorusDomainConfig] = config
    container[TorusCountConfig] = config.count
    container[TorusLinkConfig] = config.link
    torus_count = container.resolve(TorusCountProblemRecipe)
    linked = container.resolve(LinkedProblemRecipe)
    completely_unlinked = container.resolve(CompletelyUnlinkedProblemRecipe)
    linked_pair_count = container.resolve(LinkedPairCountProblemRecipe)
    recipes = (torus_count, linked, completely_unlinked, linked_pair_count)
    container[TorusProblemRecipeCatalog] = TorusProblemRecipeCatalog(recipes)
    container[TorusProblemRecipeDistribution] = TorusProblemRecipeDistribution(
        (
            DifficultyProblemRecipeWeight(
                torus_count, ((1, 1.0), (2, 1.0), (3, 0.35), (5, 0.35), (6, 0.0))
            ),
            DifficultyProblemRecipeWeight(
                linked, ((1, 0.0), (2, 0.0), (3, 0.65), (5, 0.65), (6, 0.0))
            ),
            DifficultyProblemRecipeWeight(
                completely_unlinked,
                ((1, 0.0), (5, 0.0), (6, 0.5), (7, 0.5), (8, 0.25), (10, 0.28)),
            ),
            DifficultyProblemRecipeWeight(
                linked_pair_count,
                ((1, 0.0), (5, 0.0), (6, 0.5), (7, 0.5), (8, 0.75), (10, 0.72)),
            ),
        )
    )
    return container
