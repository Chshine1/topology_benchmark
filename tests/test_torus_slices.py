from random import Random

from topology_benchmark import TorusSlicesBenchmark, build_container
from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.domains.torus_slices import (
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
    generator = RandomTorusSliceGenerator()
    request = GenerationRequest(31, 9)
    first = generator.generate(request, Random(31), count=4, linked=True)
    second = generator.generate(request, Random(31), count=4, linked=True)

    assert first == second
    assert TorusFamilyAnalyzer.certify_disjoint(first.family)
    assert len(TorusFamilyAnalyzer().linked_pairs(first.family)) == 2
    assert len(first.levels) == 9


def test_benchmark_is_wired_and_hides_equations_and_core_circles() -> None:
    benchmark = build_container().resolve(TorusSlicesBenchmark)
    first = benchmark.generate(seed=8, difficulty=8)
    second = benchmark.generate(seed=8, difficulty=8)

    assert first == second
    assert first.metadata["domain"] == "torus-slices"
    assert first.metadata["pairwise_disjoint_certified"] is True
    assert first.prompts[0].media_type == "image/svg+xml"
    assert first.prompts[0].metadata["core_circles_shown"] is False
    assert first.prompts[0].metadata["equations_shown"] is False
    assert "Parallel level sections" in first.prompts[0].content
