from lagom import Container, Singleton

from topology_benchmark.core.problem.question_distribution import DifficultyQuestionChoice
from topology_benchmark.domains.polyhedral_nets.benchmark import (
    PolyhedralNetsBenchmark,
    PolyhedralQuestionCatalog,
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
from topology_benchmark.domains.polyhedral_nets.ports import (
    IPolyhedralNetGenerator,
    IPolyhedralNetRepresentation,
)
from topology_benchmark.domains.polyhedral_nets.question_distribution import (
    PolyhedralQuestionDistribution,
)
from topology_benchmark.domains.polyhedral_nets.questions.question import (
    CellDistanceQuestion,
    CurvatureOrderQuestion,
    SeamMatchQuestion,
    ShortestPathCountQuestion,
    VertexDegreeQuestion,
    VertexPartitionQuestion,
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
    seam_match = container.resolve(SeamMatchQuestion)
    vertex_partition = container.resolve(VertexPartitionQuestion)
    cell_distance = container.resolve(CellDistanceQuestion)
    vertex_degree = container.resolve(VertexDegreeQuestion)
    curvature_order = container.resolve(CurvatureOrderQuestion)
    shortest_path_count = container.resolve(ShortestPathCountQuestion)
    questions = (
        seam_match,
        vertex_partition,
        cell_distance,
        vertex_degree,
        curvature_order,
        shortest_path_count,
    )
    container[PolyhedralQuestionCatalog] = PolyhedralQuestionCatalog(questions)
    container[PolyhedralQuestionDistribution] = PolyhedralQuestionDistribution(
        (
            DifficultyQuestionChoice(seam_match, ((1, 1.0), (4, 1.0))),
            DifficultyQuestionChoice(vertex_partition, ((1, 1.0), (4, 1.0))),
            DifficultyQuestionChoice(cell_distance, ((1, 1.0), (4, 1.0))),
            DifficultyQuestionChoice(vertex_degree, ((1, 0.0), (3, 0.0), (4, 1.0))),
            DifficultyQuestionChoice(curvature_order, ((1, 0.0), (3, 0.0), (4, 1.0))),
            DifficultyQuestionChoice(shortest_path_count, ((1, 0.0), (3, 0.0), (4, 1.0))),
        )
    )
    container[PolyhedralNetsBenchmark] = PolyhedralNetsBenchmark
    return container
