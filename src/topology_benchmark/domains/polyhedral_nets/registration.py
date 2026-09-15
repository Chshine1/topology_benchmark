from lagom import Container, Singleton

from topology_benchmark.core.errors import ConfigurationError
from topology_benchmark.core.problem.recipe_distribution import DifficultyProblemRecipeWeight
from topology_benchmark.domains.polyhedral_nets.abstractions import (
    IPolyhedralNetGenerator,
    IPolyhedralNetRepresentation,
    PolyhedralProblemRecipeCatalog,
    PolyhedralProblemRecipeDistribution,
)
from topology_benchmark.domains.polyhedral_nets.config import (
    CellDistanceConfig,
    CurvatureOrderConfig,
    PolyhedralDomainConfig,
    SeamMatchConfig,
    VertexDegreeConfig,
    VertexPartitionConfig,
)
from topology_benchmark.domains.polyhedral_nets.generation.completion import (
    NetQuestionCertifier,
    ObservableCompletionEnumerator,
)
from topology_benchmark.domains.polyhedral_nets.generation.polyhedral_net_generator import (
    RandomPolyhedralNetGenerator,
)
from topology_benchmark.domains.polyhedral_nets.recipes import (
    CellDistanceProblemRecipe,
    CurvatureOrderProblemRecipe,
    SeamMatchProblemRecipe,
    ShortestPathCountProblemRecipe,
    VertexDegreeProblemRecipe,
    VertexPartitionProblemRecipe,
)
from topology_benchmark.domains.polyhedral_nets.rendering.svg_renderer import (
    PolyhedralNetSvgRenderer,
)
from topology_benchmark.domains.polyhedral_nets.services.net_observation_builder import (
    NetObservationBuilder,
)
from topology_benchmark.domains.polyhedral_nets.services.polyhedral_cell_graph_analyzer import (
    PolyhedralCellGraphAnalyzer,
)
from topology_benchmark.domains.polyhedral_nets.services.polyhedral_net_analyzer import (
    PolyhedralNetAnalyzer,
)


def add_polyhedral_nets_domain(container: Container, config: PolyhedralDomainConfig) -> Container:
    generation = config.generation
    container[RandomPolyhedralNetGenerator] = RandomPolyhedralNetGenerator
    container[IPolyhedralNetGenerator] = RandomPolyhedralNetGenerator
    container[PolyhedralNetAnalyzer] = Singleton(PolyhedralNetAnalyzer)
    container[PolyhedralNetSvgRenderer] = PolyhedralNetSvgRenderer
    container[IPolyhedralNetRepresentation] = PolyhedralNetSvgRenderer
    container[ObservableCompletionEnumerator] = Singleton(ObservableCompletionEnumerator)
    container[NetQuestionCertifier] = Singleton(NetQuestionCertifier)
    container[PolyhedralCellGraphAnalyzer] = Singleton(PolyhedralCellGraphAnalyzer)
    container[NetObservationBuilder] = Singleton(NetObservationBuilder)
    container[PolyhedralDomainConfig] = config
    container[VertexPartitionConfig] = generation.vertex_partition
    container[VertexDegreeConfig] = generation.vertex_degree
    container[CurvatureOrderConfig] = generation.curvature_order
    container[SeamMatchConfig] = generation.seam_match
    container[CellDistanceConfig] = generation.cell_distance
    seam_match = container.resolve(SeamMatchProblemRecipe)
    vertex_partition = container.resolve(VertexPartitionProblemRecipe)
    cell_distance = container.resolve(CellDistanceProblemRecipe)
    vertex_degree = container.resolve(VertexDegreeProblemRecipe)
    curvature_order = container.resolve(CurvatureOrderProblemRecipe)
    shortest_path_count = container.resolve(ShortestPathCountProblemRecipe)
    recipes = (
        seam_match,
        vertex_partition,
        cell_distance,
        vertex_degree,
        curvature_order,
        shortest_path_count,
    )
    catalog = PolyhedralProblemRecipeCatalog(recipes)
    configured_ids = set(generation.recipe_weights)
    registered_ids = set(catalog)
    if configured_ids != registered_ids:
        raise ConfigurationError(
            "polyhedral distribution and catalog disagree; "
            f"missing={sorted(registered_ids - configured_ids)}, "
            f"unknown={sorted(configured_ids - registered_ids)}"
        )
    container[PolyhedralProblemRecipeCatalog] = catalog
    container[PolyhedralProblemRecipeDistribution] = PolyhedralProblemRecipeDistribution(
        tuple(
            DifficultyProblemRecipeWeight(catalog[recipe_id], tuple(sorted(weights.items())))
            for recipe_id, weights in generation.recipe_weights.items()
        )
    )
    return container
