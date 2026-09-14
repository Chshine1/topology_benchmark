from lagom import Container, Singleton

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
    container[VertexPartitionConfig] = config.vertex_partition
    container[VertexDegreeConfig] = config.vertex_degree
    container[CurvatureOrderConfig] = config.curvature_order
    container[SeamMatchConfig] = config.seam_match
    container[CellDistanceConfig] = config.cell_distance
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
    container[PolyhedralProblemRecipeCatalog] = PolyhedralProblemRecipeCatalog(recipes)
    container[PolyhedralProblemRecipeDistribution] = PolyhedralProblemRecipeDistribution(
        (
            DifficultyProblemRecipeWeight(seam_match, ((1, 1.0), (4, 1.0))),
            DifficultyProblemRecipeWeight(vertex_partition, ((1, 1.0), (4, 1.0))),
            DifficultyProblemRecipeWeight(cell_distance, ((1, 1.0), (4, 1.0))),
            DifficultyProblemRecipeWeight(vertex_degree, ((1, 0.0), (3, 0.0), (4, 1.0))),
            DifficultyProblemRecipeWeight(curvature_order, ((1, 0.0), (3, 0.0), (4, 1.0))),
            DifficultyProblemRecipeWeight(shortest_path_count, ((1, 0.0), (3, 0.0), (4, 1.0))),
        )
    )
    return container
