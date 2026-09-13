from lagom import Container, Singleton

from topology_benchmark.core.recipes import DifficultyQuestionChoice
from topology_benchmark.domains.torus_slices.analysis import TorusFamilyAnalyzer
from topology_benchmark.domains.torus_slices.benchmark import (
    TorusQuestionCatalog,
    TorusSlicesBenchmark,
)
from topology_benchmark.domains.torus_slices.distributions import TorusDefaultQuestionDistribution
from topology_benchmark.domains.torus_slices.generation import RandomTorusSliceGenerator
from topology_benchmark.domains.torus_slices.ports import (
    TorusSliceGenerator,
    TorusSliceRepresentation,
)
from topology_benchmark.domains.torus_slices.questions import (
    CompletelyUnlinkedQuestion,
    LinkedPairCountQuestion,
    LinkedQuestion,
    TorusCountConfig,
    TorusCountQuestion,
    TorusLinkConfig,
)
from topology_benchmark.domains.torus_slices.representation import TorusSliceSvgRenderer


def add_torus_slices_domain(container: Container) -> Container:
    container[RandomTorusSliceGenerator] = RandomTorusSliceGenerator
    container[TorusSliceGenerator] = RandomTorusSliceGenerator
    container[TorusFamilyAnalyzer] = Singleton(TorusFamilyAnalyzer)
    container[TorusSliceSvgRenderer] = TorusSliceSvgRenderer
    container[TorusSliceRepresentation] = TorusSliceSvgRenderer
    container[TorusCountConfig] = TorusCountConfig()
    container[TorusLinkConfig] = TorusLinkConfig()
    torus_count = container.resolve(TorusCountQuestion)
    linked = container.resolve(LinkedQuestion)
    completely_unlinked = container.resolve(CompletelyUnlinkedQuestion)
    linked_pair_count = container.resolve(LinkedPairCountQuestion)
    questions = (torus_count, linked, completely_unlinked, linked_pair_count)
    container[TorusQuestionCatalog] = TorusQuestionCatalog(questions)
    container[TorusDefaultQuestionDistribution] = TorusDefaultQuestionDistribution(
        (
            DifficultyQuestionChoice(
                torus_count, ((1, 1.0), (2, 1.0), (3, 0.35), (5, 0.35), (6, 0.0))
            ),
            DifficultyQuestionChoice(linked, ((1, 0.0), (2, 0.0), (3, 0.65), (5, 0.65), (6, 0.0))),
            DifficultyQuestionChoice(
                completely_unlinked,
                ((1, 0.0), (5, 0.0), (6, 0.5), (7, 0.5), (8, 0.25), (10, 0.28)),
            ),
            DifficultyQuestionChoice(
                linked_pair_count,
                ((1, 0.0), (5, 0.0), (6, 0.5), (7, 0.5), (8, 0.75), (10, 0.72)),
            ),
        )
    )
    container[TorusSlicesBenchmark] = TorusSlicesBenchmark
    return container
