import math
from random import Random

import pytest

from topology_benchmark import TorusSlicesBenchmark, build_container
from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.domains.torus_slices import (
    EllipticTorus,
    RandomTorusSliceGenerator,
    RoundCircle,
    TorusFamilyAnalyzer,
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
    first = generator.generate(request, Random(31), count=4, linked=True)
    second = generator.generate(request, Random(31), count=4, linked=True)

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
    observation = generator.generate(
        GenerationRequest(17, 10),
        Random(17),
        count=4,
        linked=True,
        link_pattern="chain",
    )

    assert all(isinstance(torus, EllipticTorus) for torus in observation.family.tori)
    assert TorusFamilyAnalyzer().linked_pairs(observation.family) == ((0, 1), (1, 2), (2, 3))


def test_complete_hopf_link_has_every_pair_linked() -> None:
    generator = RandomTorusSliceGenerator(TorusFamilyAnalyzer())
    observation = generator.generate(
        GenerationRequest(23, 10),
        Random(23),
        count=4,
        linked=True,
        link_pattern="complete",
    )

    assert len(TorusFamilyAnalyzer().linked_pairs(observation.family)) == 6
    assert TorusFamilyAnalyzer.certify_disjoint(observation.family)


def test_scored_profile_does_not_emit_ambiguous_observation_puzzles() -> None:
    kinds = {TorusSlicesBenchmark._question_kind(10, index / 100) for index in range(100)}

    assert "slice-order" not in kinds
    assert "omitted-level-count" not in kinds
    assert kinds == {"linked-pair-count", "completely-unlinked"}


def test_benchmark_is_wired_and_hides_equations_and_core_circles() -> None:
    benchmark = build_container().resolve(TorusSlicesBenchmark)
    first = benchmark.generate(seed=8, difficulty=8)
    second = benchmark.generate(seed=8, difficulty=8)

    assert first == second
    assert first.question_kind in {"linked-pair-count", "completely-unlinked"}
    assert first.sections[0].media_type == "image/svg+xml"
    assert "Parallel level sections" in first.sections[0].content
