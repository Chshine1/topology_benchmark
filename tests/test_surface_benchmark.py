import random

import pytest

from topology_benchmark import SurfaceBenchmark, build_container
from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.domains.surfaces.analysis import SurfaceAnalyzer
from topology_benchmark.domains.surfaces.components.generator import (
    RandomSurfaceMorphismGenerator,
    RandomSurfacePresentationGenerator,
)
from topology_benchmark.domains.surfaces.components.invariant import (
    integral_homology,
    morphism_answer,
)
from topology_benchmark.domains.surfaces.components.representation import SvgGluingDiagramRenderer
from topology_benchmark.domains.surfaces.models import (
    BoundaryGluingMorphism,
    DirectedEdgeMark,
    EdgeIdentification,
    EdgeRef,
    Point,
    Polygon,
    SurfacePresentation,
)


def _polygon(name: str = "P", sides: int = 4) -> Polygon:
    points = (Point(0, 0), Point(1, 0), Point(1, 1), Point(0, 1))
    return Polygon(name, points[:sides])


def test_topology_is_derived_from_the_presentation() -> None:
    disk = SurfacePresentation((_polygon(sides=3),), ())
    facts = SurfaceAnalyzer().analyze(disk)

    assert facts.euler_characteristic == 1
    assert facts.boundary_components == 1
    assert len(facts.components) == 1
    assert facts.components[0].orientable
    assert facts.components[0].genus == 0
    assert integral_homology(disk) == "H_0=Z; H_1=0; H_2=0"


def test_a_square_word_is_computed_as_a_torus() -> None:
    torus = SurfacePresentation(
        (_polygon(),),
        (
            DirectedEdgeMark(EdgeRef(0, 0), "a", True),
            DirectedEdgeMark(EdgeRef(0, 2), "a", False),
            DirectedEdgeMark(EdgeRef(0, 1), "b", True),
            DirectedEdgeMark(EdgeRef(0, 3), "b", False),
        ),
    )
    facts = SurfaceAnalyzer().analyze(torus)

    assert facts.euler_characteristic == 0
    assert facts.boundary_components == 0
    assert facts.components[0].orientable
    assert facts.components[0].genus == 1
    assert integral_homology(torus) == "H_0=Z; H_1=Z^2; H_2=Z"


def test_generated_quotients_are_compact_surfaces_without_stored_invariants() -> None:
    generator = RandomSurfacePresentationGenerator()
    analyzer = SurfaceAnalyzer()
    for seed in range(80):
        surface = generator.generate(GenerationRequest(seed, 8), random.Random(seed))
        facts = analyzer.analyze(surface)
        assert facts.components
        assert facts.euler_characteristic == (
            facts.vertex_count - facts.edge_count + facts.face_count
        )
        assert not hasattr(surface, "topology")


def test_boundary_gluing_is_a_first_class_quotient_map() -> None:
    morphism = RandomSurfaceMorphismGenerator()._glue_two_disks(random.Random(2), 5)
    analyzer = SurfaceAnalyzer()
    source, target = analyzer.analyze(morphism.source), analyzer.analyze(morphism.target)

    assert morphism.source is not morphism.target
    assert len(morphism.identifications) == 5
    assert len(source.components) == 2
    assert source.boundary_components == 2
    assert len(target.components) == 1
    assert target.boundary_components == 0
    assert target.euler_characteristic == 2
    assert target.components[0].genus == 0


def test_gluing_the_annulus_boundaries_constructs_torus_or_klein_bottle() -> None:
    generator = RandomSurfaceMorphismGenerator()
    analyzer = SurfaceAnalyzer()
    targets = [
        analyzer.analyze(generator._close_annulus(random.Random(seed)).target) for seed in range(8)
    ]

    assert all(facts.euler_characteristic == 0 for facts in targets)
    assert all(facts.boundary_components == 0 for facts in targets)
    assert {facts.components[0].orientable for facts in targets} == {True, False}
    homologies = {
        integral_homology(generator._close_annulus(random.Random(seed)).target) for seed in range(8)
    }
    assert homologies == {
        "H_0=Z; H_1=Z^2; H_2=Z",
        "H_0=Z; H_1=Z ⊕ Z/2; H_2=0",
    }


def test_morphism_invariants_are_computed_from_source_and_target() -> None:
    morphism = RandomSurfaceMorphismGenerator()._glue_two_disks(random.Random(4), 3)

    assert morphism_answer(morphism, "euler-change") == 0
    assert morphism_answer(morphism, "boundary-change") == -2
    assert morphism_answer(morphism, "component-change") == -1
    assert morphism_answer(morphism, "map-injective") is False
    assert morphism_answer(morphism, "map-surjective") is True
    assert morphism_answer(morphism, "homology-isomorphism") is False
    assert morphism_answer(morphism, "target-homology") == "H_0=Z; H_1=0; H_2=Z"


def test_renderer_is_deterministic() -> None:
    request = GenerationRequest(3, 5)
    surface = RandomSurfacePresentationGenerator().generate(request, random.Random(3))
    renderer = SvgGluingDiagramRenderer()

    assert renderer.render(surface, request, random.Random(1)) == renderer.render(
        surface, request, random.Random(999)
    )


def test_benchmark_generates_object_and_morphism_questions() -> None:
    benchmark = build_container().resolve(SurfaceBenchmark)
    problems = [benchmark.generate(seed=seed, difficulty=8) for seed in range(40)]

    assert {problem.metadata["subject"] for problem in problems} == {"object", "morphism"}
    assert all(prompt.media_type == "image/svg+xml" for p in problems for prompt in p.prompts)
    assert all(
        len(problem.prompts) == (2 if problem.metadata["subject"] == "morphism" else 1)
        for problem in problems
    )
    assert benchmark.generate(seed=7, difficulty=8) == benchmark.generate(seed=7, difficulty=8)


def test_incomplete_edge_identification_is_rejected() -> None:
    with pytest.raises(ValueError, match="exactly twice"):
        SurfacePresentation(
            (_polygon(sides=3),),
            (DirectedEdgeMark(EdgeRef(0, 0), "unpaired-mark", True),),
        )


def test_morphism_target_must_equal_its_declared_quotient() -> None:
    source = SurfacePresentation((_polygon("A", 3), _polygon("B", 3)), ())
    identification = EdgeIdentification(EdgeRef(0, 0), EdgeRef(1, 0), "g", False)
    with pytest.raises(ValueError, match="target is not the quotient"):
        BoundaryGluingMorphism(source, source, (identification,))


def test_polygon_attachment_is_a_first_class_inclusion() -> None:
    morphism = RandomSurfaceMorphismGenerator()._attach_polygon(random.Random(5))
    analyzer = SurfaceAnalyzer()

    assert morphism.name == "polygon-attachment-inclusion"
    assert len(morphism.target.polygons) == len(morphism.source.polygons) + 1
    assert analyzer.analyze(morphism.source).euler_characteristic == 1
    assert analyzer.analyze(morphism.target).euler_characteristic == 1
    assert morphism_answer(morphism, "map-injective") is True
    assert morphism_answer(morphism, "map-surjective") is False
    assert morphism_answer(morphism, "homology-isomorphism") is True


def test_difficulty_is_validated() -> None:
    with pytest.raises(ValueError, match="difficulty"):
        GenerationRequest(seed=0, difficulty=11)
