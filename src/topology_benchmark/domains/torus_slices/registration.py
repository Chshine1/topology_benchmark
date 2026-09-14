from lagom import Container, Singleton

from topology_benchmark.core.problem.question_distribution import DifficultyQuestionChoice
from topology_benchmark.domains.torus_slices.benchmark import (
    TorusQuestionCatalog,
    TorusSlicesBenchmark,
)
from topology_benchmark.domains.torus_slices.config import (
    TorusCountConfig,
    TorusDomainConfig,
    TorusLinkConfig,
)
from topology_benchmark.domains.torus_slices.generation.torus_slice_generator import (
    RandomTorusSliceGenerator,
)
from topology_benchmark.domains.torus_slices.ports import (
    ITorusSliceGenerator,
    ITorusSliceRepresentation,
)
from topology_benchmark.domains.torus_slices.question_distribution import TorusQuestionDistribution
from topology_benchmark.domains.torus_slices.questions.question import (
    CompletelyUnlinkedQuestion,
    LinkedPairCountQuestion,
    LinkedQuestion,
    TorusCountQuestion,
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
    torus_count = container.resolve(TorusCountQuestion)
    linked = container.resolve(LinkedQuestion)
    completely_unlinked = container.resolve(CompletelyUnlinkedQuestion)
    linked_pair_count = container.resolve(LinkedPairCountQuestion)
    questions = (torus_count, linked, completely_unlinked, linked_pair_count)
    container[TorusQuestionCatalog] = TorusQuestionCatalog(questions)
    container[TorusQuestionDistribution] = TorusQuestionDistribution(
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
