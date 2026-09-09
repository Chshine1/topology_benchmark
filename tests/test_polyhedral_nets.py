from dataclasses import replace
from fractions import Fraction
from random import Random

from topology_benchmark import PolyhedralNetBenchmark, build_container
from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.domains.polyhedral_nets import (
    FaceCorner,
    PolygonFace,
    PolyhedralNetAnalyzer,
    VertexType,
)
from topology_benchmark.domains.polyhedral_nets.generation import RandomPolyhedralNetGenerator
from topology_benchmark.domains.polyhedral_nets.representation import PolyhedralNetSvgRenderer


def _bipyramid(size: int, *, marked: bool = False, seed: int = 3):
    return RandomPolyhedralNetGenerator()._bipyramid(size, Random(seed), marked_vertex=marked)


def test_local_angle_classification_is_exact() -> None:
    analyzer = PolyhedralNetAnalyzer()

    assert analyzer.classify_angle(Fraction(359)) is VertexType.CONVEX
    assert analyzer.classify_angle(Fraction(360)) is VertexType.FLAT
    assert analyzer.classify_angle(Fraction(361)) is VertexType.SADDLE


def test_bipyramid_foldings_are_closed_spheres_with_expected_apex_geometry() -> None:
    analyzer = PolyhedralNetAnalyzer()

    convex = analyzer.analyze(_bipyramid(5, marked=True))
    flat = analyzer.analyze(_bipyramid(6, marked=True))
    saddle = PolyhedralNetAnalyzer().analyze(_bipyramid(7, marked=True))

    assert convex.euler_characteristic == 2
    assert convex.vertex_neighborhoods_are_disks
    assert convex.closes_to_convex_polyhedron
    assert VertexType.FLAT in flat.vertex_types
    assert not flat.closes_to_convex_polyhedron
    assert VertexType.SADDLE in saddle.vertex_types
    assert not saddle.closes_to_convex_polyhedron


def test_renderer_hides_matches_but_labels_boundary_edges() -> None:
    net = _bipyramid(4)
    prompt = PolyhedralNetSvgRenderer().render(net.net, GenerationRequest(8, 5), Random(8))

    assert prompt.media_type == "image/svg+xml"
    assert prompt.metadata["seam_matches_shown"] is False
    assert "e1" in prompt.content
    assert "unit side length" in prompt.content
    assert PolyhedralNetAnalyzer().seam_answer(net)
    solutions = PolyhedralNetAnalyzer().enumerate_locally_convex_pairings(net.net)
    assert len(solutions) == 1
    assert frozenset(solutions[0]) == frozenset(net.seams)


def test_benchmark_is_reproducible_and_wired_into_container() -> None:
    benchmark = build_container().resolve(PolyhedralNetBenchmark)

    first = benchmark.generate(seed=42, difficulty=10)
    second = benchmark.generate(seed=42, difficulty=10)

    assert first == second
    assert first.metadata["domain"] == "polyhedral-nets"
    assert first.question
    assert first.prompts


def test_different_cuts_of_same_solid_are_intrinsically_isometric() -> None:
    generator = RandomPolyhedralNetGenerator()
    analyzer = PolyhedralNetAnalyzer()
    request = GenerationRequest(2, 8)
    first = generator._bipyramid(5, Random(1))
    second = generator._bipyramid(5, Random(2))
    different = generator._bipyramid(4, Random(2))

    assert first.net.hinges != second.net.hinges
    assert analyzer.isometric(first, second)
    assert not analyzer.isometric(first, different)
    pair = generator.generate_isometry_pair(request, Random(4), isometric=True)
    assert analyzer.isometric(*pair)


def test_v2_sources_are_real_irregular_polyhedra_with_nonoverlapping_developments() -> None:
    generator = RandomPolyhedralNetGenerator()

    for difficulty in (1, 4, 7, 10):
        folding = generator.generate(GenerationRequest(19, difficulty), Random(difficulty))

        assert folding.source is not None
        generator.validate_source(folding.source)
        assert all(isinstance(face, PolygonFace) for face in folding.net.faces)
        assert any(
            len(set(face.edge_squared_lengths)) > 1
            for face in folding.net.faces
            if isinstance(face, PolygonFace)
        )
        layouts = tuple(face.points for face in folding.net.faces if isinstance(face, PolygonFace))
        assert not generator._has_overlap(layouts)
        assert PolyhedralNetAnalyzer().analyze(folding).closes_to_convex_polyhedron


def test_v2_benchmark_uses_certified_sparse_observations_without_answer_leakage() -> None:
    benchmark = build_container().resolve(PolyhedralNetBenchmark)

    problems = [benchmark.generate(seed=seed, difficulty=10) for seed in range(25)]

    assert all(
        problem.metadata["generation_profile"] == "polyhedral-nets-v2" for problem in problems
    )
    assert all(problem.metadata["source_is_real_3d"] is True for problem in problems)
    assert all("local_geometry" not in problem.metadata for problem in problems)
    assert all("source_name" not in problem.metadata for problem in problems)
    assert all("diagram drawn to scale" in problem.prompts[0].content for problem in problems)
    assert any(problem.metadata["question_kind"] == "highest-vertex" for problem in problems)
    assert len({problem.metadata["question_kind"] for problem in problems}) >= 5


def test_renderer_only_shows_v2_labels_selected_by_the_question() -> None:
    generator = RandomPolyhedralNetGenerator()
    folding = generator.generate(GenerationRequest(3, 7), Random(11))
    first_boundary = folding.net.boundary_edges[0]
    observed = replace(
        folding.net,
        edge_labels=((first_boundary, "A"),),
    )

    prompt = PolyhedralNetSvgRenderer().render(observed, GenerationRequest(3, 7), Random(4))

    assert ">A</text>" in prompt.content
    assert ">F1</text>" not in prompt.content
    assert prompt.metadata["regular_faces"] is False


def test_adaptive_hint_makes_an_ambiguous_observation_answerable() -> None:
    generator = RandomPolyhedralNetGenerator()
    analyzer = PolyhedralNetAnalyzer()
    benchmark = build_container().resolve(PolyhedralNetBenchmark)
    folding = generator.generate(GenerationRequest(61, 7), Random(61))
    solutions = analyzer.enumerate_locally_convex_pairings(folding.net)
    first = FaceCorner(0, 2)
    second = FaceCorner(2, 2)

    def answer(seams):
        return benchmark._same_vertex(folding.net, seams, first, second)

    assert len(solutions) == 2
    assert {answer(solution) for solution in solutions} == {False, True}
    certificate = benchmark._certify(folding.net, folding.seams, solutions, answer, difficulty=7)
    assert certificate is not None
    hints, expected = certificate
    assert len(hints) == 1
    observed = replace(folding.net, seam_hints=hints)
    assert {
        answer(solution) for solution in analyzer.enumerate_locally_convex_pairings(observed)
    } == {expected}
