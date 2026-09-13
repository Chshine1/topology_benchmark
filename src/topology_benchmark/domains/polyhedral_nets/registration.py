from lagom import Container, Singleton

from topology_benchmark.core.recipes import DifficultyQuestionChoice
from topology_benchmark.domains.polyhedral_nets.analysis import PolyhedralNetAnalyzer
from topology_benchmark.domains.polyhedral_nets.benchmark import (
    PolyhedralNetsBenchmark,
    PolyhedralQuestionCatalog,
)
from topology_benchmark.domains.polyhedral_nets.distributions import (
    PolyhedralDefaultQuestionDistribution,
)
from topology_benchmark.domains.polyhedral_nets.generation import RandomPolyhedralNetGenerator
from topology_benchmark.domains.polyhedral_nets.ports import (
    PolyhedralNetGenerator,
    PolyhedralNetRepresentation,
)
from topology_benchmark.domains.polyhedral_nets.question_services import (
    NetObservationBuilder,
    NetQuestionCertifier,
    ObservableCompletionEnumerator,
    PolyhedralCellGraphAnalyzer,
)
from topology_benchmark.domains.polyhedral_nets.questions import (
    CellDistanceConfig,
    CellDistanceQuestion,
    CurvatureOrderConfig,
    CurvatureOrderQuestion,
    SeamMatchConfig,
    SeamMatchQuestion,
    ShortestPathCountQuestion,
    VertexDegreeConfig,
    VertexDegreeQuestion,
    VertexPartitionConfig,
    VertexPartitionQuestion,
)
from topology_benchmark.domains.polyhedral_nets.representation import PolyhedralNetSvgRenderer


def add_polyhedral_nets_domain(container: Container) -> Container:
    container[RandomPolyhedralNetGenerator] = RandomPolyhedralNetGenerator
    container[PolyhedralNetGenerator] = RandomPolyhedralNetGenerator
    container[PolyhedralNetAnalyzer] = Singleton(PolyhedralNetAnalyzer)
    container[PolyhedralNetSvgRenderer] = PolyhedralNetSvgRenderer
    container[PolyhedralNetRepresentation] = PolyhedralNetSvgRenderer
    container[ObservableCompletionEnumerator] = Singleton(ObservableCompletionEnumerator)
    container[NetQuestionCertifier] = Singleton(NetQuestionCertifier)
    container[PolyhedralCellGraphAnalyzer] = Singleton(PolyhedralCellGraphAnalyzer)
    container[NetObservationBuilder] = Singleton(NetObservationBuilder)
    container[VertexPartitionConfig] = VertexPartitionConfig()
    container[VertexDegreeConfig] = VertexDegreeConfig()
    container[CurvatureOrderConfig] = CurvatureOrderConfig()
    container[SeamMatchConfig] = SeamMatchConfig()
    container[CellDistanceConfig] = CellDistanceConfig()
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
    container[PolyhedralDefaultQuestionDistribution] = PolyhedralDefaultQuestionDistribution(
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
