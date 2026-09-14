import math
from random import Random

import pytest

from topology_benchmark import build_container
from topology_benchmark.core.probability.sampling import SamplingSession
from topology_benchmark.core.problem.models import GenerationRequest
from topology_benchmark.domains.torus_slices import (
    ChainLinkedTorusFamily,
    CompletelyLinkedTorusFamily,
    EllipticTorus,
    PairLinkedTorusFamily,
    RandomTorusSliceGenerator,
    RoundCircle,
    TorusFamilyAnalyzer,
    TorusGenerationContext,
)
from topology_benchmark.domains.torus_slices.abstractions import (
    TorusProblemRecipeDistribution,
)


def test_disk_intersection_computes_hopf_link_and_unlink() -> None:
    analyzer = TorusFamilyAnalyzer()
    horizontal = RoundCircle((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 2.0)
    linked = RoundCircle((2.0, 0.0, 0.0), (0.0, 1.0, 0.0), 2.0)
    separate = RoundCircle((6.0, 0.0, 0.0), (0.0, 0.0, 1.0), 2.0)

    assert abs(analyzer.linking_number(horizontal, linked)) == 1
    assert analyzer.linking_number(horizontal, separate) == 0


def test_generator_certifies_disjoint_tubes_and_reproducible_slices() -> None:
    generator = RandomTorusSliceGenerator(TorusFamilyAnalyzer())
    request = GenerationRequest(31, 9)
    condition = PairLinkedTorusFamily(4)
    first = generator.generate_for(
        TorusGenerationContext(request, condition, SamplingSession(31, "test"))
    )
    second = generator.generate_for(
        TorusGenerationContext(request, condition, SamplingSession(31, "test"))
    )

    assert first == second
    assert TorusFamilyAnalyzer.certify_disjoint(first.family)
    assert len(TorusFamilyAnalyzer().linked_pairs(first.family)) == 2
    assert len(first.levels) == 9


def test_elliptic_torus_sweeps_a_rotated_ellipse_around_a_circle() -> None:
    core = RoundCircle((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 2.0)
    torus = EllipticTorus(core, 0.3, 0.15, 0.4)
    radial = 0.3 * math.cos(0.4)
    axial = 0.3 * math.sin(0.4)

    assert torus.implicit_value((2.0 + radial, 0.0, axial)) == pytest.approx(0.0)


def test_connected_chain_links_all_consecutive_tori() -> None:
    generator = RandomTorusSliceGenerator(TorusFamilyAnalyzer())
    request = GenerationRequest(17, 10)
    observation = generator.generate_for(
        TorusGenerationContext(request, ChainLinkedTorusFamily(4), SamplingSession(17, "test"))
    )

    assert all(isinstance(torus, EllipticTorus) for torus in observation.family.tori)
    assert TorusFamilyAnalyzer().linked_pairs(observation.family) == ((0, 1), (1, 2), (2, 3))


def test_complete_hopf_link_has_every_pair_linked() -> None:
    generator = RandomTorusSliceGenerator(TorusFamilyAnalyzer())
    request = GenerationRequest(23, 10)
    observation = generator.generate_for(
        TorusGenerationContext(request, CompletelyLinkedTorusFamily(4), SamplingSession(23, "test"))
    )

    assert len(TorusFamilyAnalyzer().linked_pairs(observation.family)) == 6
    assert TorusFamilyAnalyzer.certify_disjoint(observation.family)


def test_scored_profile_does_not_emit_ambiguous_observation_puzzles() -> None:
    distribution = build_container().resolve(TorusProblemRecipeDistribution)
    kinds = {distribution.at(10).sample(Random(index)).id for index in range(100)}

    assert "slice-order" not in kinds
    assert "omitted-level-count" not in kinds
    assert kinds == {"linked-pair-count", "completely-unlinked"}


def test_benchmark_is_wired_and_hides_equations_and_core_circles() -> None:
    container = build_container()
    distribution = container.resolve(TorusProblemRecipeDistribution).at(8)
    recipe = distribution.sample(Random(8))
    first = recipe.generate(GenerationRequest(8, 8))
    second = recipe.generate(GenerationRequest(8, 8))

    assert first == second
    assert first.recipe_id in {"linked-pair-count", "completely-unlinked"}
    assert first.sections[0].media_type == "image/svg+xml"
    assert "Parallel level sections" in first.sections[0].content
