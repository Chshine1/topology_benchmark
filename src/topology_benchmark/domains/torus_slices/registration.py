from lagom import Container, Singleton

from topology_benchmark.core.errors import ConfigurationError
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
    generation = config.generation
    container[RandomTorusSliceGenerator] = RandomTorusSliceGenerator
    container[ITorusSliceGenerator] = RandomTorusSliceGenerator
    container[TorusFamilyAnalyzer] = Singleton(TorusFamilyAnalyzer)
    container[TorusSliceSvgRenderer] = TorusSliceSvgRenderer
    container[ITorusSliceRepresentation] = TorusSliceSvgRenderer
    container[TorusDomainConfig] = config
    container[TorusCountConfig] = generation.count
    container[TorusLinkConfig] = generation.link
    torus_count = container.resolve(TorusCountProblemRecipe)
    linked = container.resolve(LinkedProblemRecipe)
    completely_unlinked = container.resolve(CompletelyUnlinkedProblemRecipe)
    linked_pair_count = container.resolve(LinkedPairCountProblemRecipe)
    recipes = (torus_count, linked, completely_unlinked, linked_pair_count)
    catalog = TorusProblemRecipeCatalog(recipes)
    configured_ids = set(generation.recipe_weights)
    registered_ids = set(catalog)
    if configured_ids != registered_ids:
        raise ConfigurationError(
            "torus distribution and catalog disagree; "
            f"missing={sorted(registered_ids - configured_ids)}, "
            f"unknown={sorted(configured_ids - registered_ids)}"
        )
    container[TorusProblemRecipeCatalog] = catalog
    container[TorusProblemRecipeDistribution] = TorusProblemRecipeDistribution(
        tuple(
            DifficultyProblemRecipeWeight(catalog[recipe_id], tuple(sorted(weights.items())))
            for recipe_id, weights in generation.recipe_weights.items()
        )
    )
    return container
