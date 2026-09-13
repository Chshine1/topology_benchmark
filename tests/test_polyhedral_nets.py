from fractions import Fraction
from itertools import pairwise
from random import Random

from attrs import evolve

from topology_benchmark import build_container
from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.domains.polyhedral_nets import (
    EdgePair,
    FaceCorner,
    NetEdge,
    PolygonFace,
    PolyhedralFolding,
    PolyhedralNet,
    PolyhedralNetAnalyzer,
    RegularFace,
    VertexType,
)
from topology_benchmark.domains.polyhedral_nets.benchmark import PolyhedralNetsBenchmark
from topology_benchmark.domains.polyhedral_nets.distributions import (
    PolyhedralDefaultQuestionDistribution,
)
from topology_benchmark.domains.polyhedral_nets.generation import RandomPolyhedralNetGenerator
from topology_benchmark.domains.polyhedral_nets.question_services import (
    NetQuestionCertifier,
    PolyhedralCellGraphAnalyzer,
)
from topology_benchmark.domains.polyhedral_nets.representation import PolyhedralNetSvgRenderer


def _generate_default(benchmark, distribution, seed: int, difficulty: int):
    return benchmark.generate(
        request=GenerationRequest(seed, difficulty),
        distribution=distribution.at(difficulty),
    )


def _bipyramid(size: int, *, seed: int = 3):
    top, bottom = 0, 1
    ring = tuple(range(2, size + 2))
    face_vertices = tuple(
        (top, vertex, ring[(index + 1) % size]) for index, vertex in enumerate(ring)
    ) + tuple((bottom, ring[(index + 1) % size], vertex) for index, vertex in enumerate(ring))
    faces = tuple(RegularFace(f"F{index + 1}", 3) for index in range(len(face_vertices)))
    pairs = RandomPolyhedralNetGenerator._edge_pairs(face_vertices)
    by_edges = {pair.unordered: pair for pair in pairs}

    def pair(first: NetEdge, second: NetEdge) -> EdgePair:
        return by_edges[frozenset((first, second))]

    hinges = [pair(NetEdge(index, 1), NetEdge(size + index, 1)) for index in range(size)]
    rng = Random(seed)
    first_diamond = rng.randrange(size)
    order = tuple((first_diamond + offset) % size for offset in range(size))
    use_top_first = bool(rng.randrange(2))
    for position, (current, following) in enumerate(pairwise(order)):
        if (position % 2 == 0) == use_top_first:
            hinges.append(pair(NetEdge(current, 2), NetEdge(following, 0)))
        else:
            hinges.append(pair(NetEdge(size + current, 0), NetEdge(size + following, 2)))
    hinge_pairs = tuple(hinges)
    hinge_set = {item.unordered for item in hinge_pairs}
    seams = tuple(item for item in pairs if item.unordered not in hinge_set)
    return PolyhedralFolding(
        PolyhedralNet(f"triangular {size}-bipyramid", faces, hinge_pairs), seams
    )


def test_local_angle_classification_is_exact() -> None:
    analyzer = PolyhedralNetAnalyzer()

    assert analyzer.classify_angle(Fraction(359)) is VertexType.CONVEX
    assert analyzer.classify_angle(Fraction(360)) is VertexType.FLAT
    assert analyzer.classify_angle(Fraction(361)) is VertexType.SADDLE


def test_bipyramid_foldings_are_closed_spheres_with_expected_apex_geometry() -> None:
    analyzer = PolyhedralNetAnalyzer()

    convex = analyzer.analyze(_bipyramid(5))
    flat = analyzer.analyze(_bipyramid(6))
    saddle = PolyhedralNetAnalyzer().analyze(_bipyramid(7))

    assert convex.euler_characteristic == 2
    assert convex.vertex_neighborhoods_are_disks
    assert convex.admits_convex_realization
    assert VertexType.FLAT in flat.vertex_types
    assert not flat.admits_convex_realization
    assert VertexType.SADDLE in saddle.vertex_types
    assert not saddle.admits_convex_realization


def test_renderer_hides_matches_but_labels_boundary_edges() -> None:
    net = _bipyramid(4)
    section = PolyhedralNetSvgRenderer().render(net.net, GenerationRequest(8, 5), Random(8))

    assert section.media_type == "image/svg+xml"
    assert "Equal-colored dots" not in section.content
    assert "e1" in section.content
    assert "unit side length" in section.content
    assert PolyhedralNetAnalyzer().seam_answer(net)
    solutions = PolyhedralNetAnalyzer().enumerate_locally_convex_pairings(net.net)
    assert len(solutions) == 1
    assert frozenset(solutions[0]) == frozenset(net.seams)


def test_benchmark_is_reproducible_and_wired_into_container() -> None:
    container = build_container()
    benchmark = container.resolve(PolyhedralNetsBenchmark)
    distribution = container.resolve(PolyhedralDefaultQuestionDistribution)
    first = _generate_default(benchmark, distribution, 42, 10)
    second = _generate_default(benchmark, distribution, 42, 10)

    assert first == second
    assert first.question_id
    assert first.question
    assert first.sections


def test_different_cuts_of_same_solid_are_intrinsically_isometric() -> None:
    generator = RandomPolyhedralNetGenerator()
    analyzer = PolyhedralNetAnalyzer()
    request = GenerationRequest(2, 8)
    first = _bipyramid(5, seed=1)
    second = _bipyramid(5, seed=2)
    different = _bipyramid(4, seed=2)

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
        assert PolyhedralNetAnalyzer().analyze(folding).admits_convex_realization


def test_v6_benchmark_uses_certified_sparse_observations_without_answer_leakage() -> None:
    container = build_container()
    benchmark = container.resolve(PolyhedralNetsBenchmark)
    distribution = container.resolve(PolyhedralDefaultQuestionDistribution)

    problems = [_generate_default(benchmark, distribution, seed, 10) for seed in range(25)]

    assert all("diagram drawn to scale" in problem.sections[0].content for problem in problems)
    assert len({problem.question_id for problem in problems}) >= 5
    assert all(problem.question_id != "highest-vertex" for problem in problems)
    assert all(problem.question_id != "isometric" for problem in problems)
    assert all(problem.question_id != "corner-coincidence" for problem in problems)
    assert all(problem.question_id != "face-relation" for problem in problems)


def test_renderer_only_shows_v2_labels_selected_by_the_question() -> None:
    generator = RandomPolyhedralNetGenerator()
    folding = generator.generate(GenerationRequest(3, 7), Random(11))
    first_boundary = folding.net.boundary_edges[0]
    observed = evolve(
        folding.net,
        edge_labels=((first_boundary, "A"),),
    )

    section = PolyhedralNetSvgRenderer().render(observed, GenerationRequest(3, 7), Random(4))

    assert ">A</text>" in section.content
    assert ">F1</text>" not in section.content


def test_adaptive_hint_makes_an_ambiguous_observation_answerable() -> None:
    generator = RandomPolyhedralNetGenerator()
    analyzer = PolyhedralNetAnalyzer()
    folding = generator.generate(GenerationRequest(61, 7), Random(61))
    solutions = analyzer.enumerate_locally_convex_pairings(folding.net)
    first = FaceCorner(0, 2)
    second = FaceCorner(2, 2)

    def answer(seams):
        return any(
            first in group and second in group
            for group in analyzer.analyze(folding.net, seams).vertices
        )

    assert len(solutions) == 2
    assert {answer(solution) for solution in solutions} == {False, True}
    certificate = NetQuestionCertifier().certify(folding.seams, solutions, answer, difficulty=7)
    assert certificate is not None
    hints, expected = certificate
    assert len(hints) == 1
    observed = evolve(folding.net, seam_hints=hints)
    assert {
        answer(solution) for solution in analyzer.enumerate_locally_convex_pairings(observed)
    } == {expected}


def test_visual_tolerance_preserves_pairings_hidden_by_exact_metrics() -> None:
    generator = RandomPolyhedralNetGenerator()
    analyzer = PolyhedralNetAnalyzer()
    folding = generator.generate(GenerationRequest(127, 10), Random(127))

    exact = analyzer.enumerate_locally_convex_pairings(folding.net)
    visually_compatible = analyzer.enumerate_locally_convex_pairings(
        folding.net, relative_length_tolerance=0.04
    )

    assert len(exact) == 1
    assert len(visually_compatible) == 3


def test_curvature_questions_show_all_corner_angles_and_have_a_margin() -> None:
    container = build_container()
    benchmark = container.resolve(PolyhedralNetsBenchmark)
    distribution = container.resolve(PolyhedralDefaultQuestionDistribution)
    problem = next(
        problem
        for seed in range(100)
        if (problem := _generate_default(benchmark, distribution, seed, 10)).question_id
        == "curvature-order"
    )

    assert "nearest degree" in problem.question
    assert "°" in problem.sections[0].content
    assert problem.answer in {"A", "B"}


def test_cell_distance_unifies_face_incidence_and_shortest_path_count() -> None:
    folding = _bipyramid(4)
    graph = PolyhedralCellGraphAnalyzer(PolyhedralNetAnalyzer())
    face_cells = [("face", face, -1) for face in range(len(folding.net.faces))]
    statistics = {
        graph.statistics(folding.net, folding.seams, first, second)
        for first_index, first in enumerate(face_cells)
        for second in face_cells[first_index + 1 :]
    }

    assert (0, 1) in statistics  # faces sharing only one vertex
    assert (0, 2) in statistics  # faces sharing one edge
    assert any(distance > 0 for distance, _ in statistics)


def test_vertex_partition_replaces_binary_corner_coincidence() -> None:
    container = build_container()
    benchmark = container.resolve(PolyhedralNetsBenchmark)
    distribution = container.resolve(PolyhedralDefaultQuestionDistribution)
    problem = next(
        problem
        for seed in range(60)
        if (problem := _generate_default(benchmark, distribution, seed, 10)).question_id
        == "vertex-partition"
    )

    assert isinstance(problem.answer, str)
    groups = problem.answer.split("|")
    assert "".join(sorted("".join(groups))) == "ABCDE"
    assert all(group == "".join(sorted(group)) for group in groups)
    assert any(len(group) > 1 for group in groups)


def test_comparison_rendering_can_use_one_scale_and_matched_face_inventories() -> None:
    generator = RandomPolyhedralNetGenerator()
    renderer = PolyhedralNetSvgRenderer()
    request = GenerationRequest(9, 10)
    first, second = generator.generate_isometry_pair(request, Random(9), isometric=False)
    scale = renderer.common_scale((first.net, second.net))

    first_section = renderer.render(first.net, request, Random(1), scale=scale)
    second_section = renderer.render(second.net, request, Random(2), scale=scale)

    assert tuple(face.sides for face in first.net.faces) == tuple(
        face.sides for face in second.net.faces
    )
    scale_bar_end = f'x2="{14 + scale:.3f}"'
    assert scale_bar_end in first_section.content
    assert scale_bar_end in second_section.content
    assert "1 unit" in first_section.content
