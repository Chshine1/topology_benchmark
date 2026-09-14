import math
import random
from pathlib import Path
from typing import Any

import pytest

from topology_benchmark import BenchmarkCatalog, build_container
from topology_benchmark.application.configuration import (
    SURFACE_GENERATION_DEFAULTS,
    SURFACE_RENDERING_DEFAULTS,
)
from topology_benchmark.core.probability.sampling import SamplingSession
from topology_benchmark.core.problem.models import GenerationRequest
from topology_benchmark.domains.surfaces.benchmark import SurfaceQuestionCatalog
from topology_benchmark.domains.surfaces.generation.config import load_generation_config
from topology_benchmark.domains.surfaces.generation.context.object import (
    SurfaceObjectGenerationContext,
)
from topology_benchmark.domains.surfaces.generation.generator.morphism import (
    RandomSurfaceMorphismGenerator,
)
from topology_benchmark.domains.surfaces.generation.generator.object import (
    RandomSurfacePresentationGenerator,
)
from topology_benchmark.domains.surfaces.models import (
    EdgeGluing,
    EdgeRef,
    OrientedEdge,
    Polygon,
    SurfacePath,
    SurfacePresentation,
)
from topology_benchmark.domains.surfaces.questions.answers import integral_homology
from topology_benchmark.domains.surfaces.rendering.config import (
    SurfaceRenderingConfig,
    load_rendering_config,
)
from topology_benchmark.domains.surfaces.rendering.diagram import (
    DiagramStyle,
    LinePattern,
    OrderDisplay,
    Palette,
    SurfaceDiagramPlanner,
)
from topology_benchmark.domains.surfaces.rendering.renderer import (
    MatplotlibGluingDiagramRenderer,
)
from topology_benchmark.domains.surfaces.services import SurfaceAnalyzer


def _question(question_id: str) -> Any:
    return build_container().resolve(SurfaceQuestionCatalog)[question_id]


def test_generated_quotients_are_compact_surfaces_without_stored_invariants() -> None:
    analyzer = SurfaceAnalyzer()
    generator = RandomSurfacePresentationGenerator(
        (config := load_generation_config(SURFACE_GENERATION_DEFAULTS)), analyzer
    )
    for seed in range(80):
        request = GenerationRequest(seed, 8)
        sampling = SamplingSession(seed, config.profile_version)
        surface = generator.generate_for(
            SurfaceObjectGenerationContext(
                request,
                config.object_law_for("euler-characteristic"),
                sampling,
            )
        )
        facts = analyzer.analyze(surface)
        assert facts.components
        assert facts.euler_characteristic == (
            facts.vertex_count - facts.edge_count + facts.face_count
        )
        assert not hasattr(surface, "topology")


def test_boundary_gluing_is_a_first_class_quotient_map() -> None:
    analyzer = SurfaceAnalyzer()
    morphism = RandomSurfaceMorphismGenerator(
        load_generation_config(SURFACE_GENERATION_DEFAULTS), analyzer
    )._glue_two_disks(random.Random(2), 5)
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
    analyzer = SurfaceAnalyzer()
    generator = RandomSurfaceMorphismGenerator(
        load_generation_config(SURFACE_GENERATION_DEFAULTS), analyzer
    )
    targets = [
        analyzer.analyze(generator._close_annulus(random.Random(seed)).target) for seed in range(8)
    ]

    assert all(facts.euler_characteristic == 0 for facts in targets)
    assert all(facts.boundary_components == 0 for facts in targets)
    assert {facts.components[0].orientable for facts in targets} == {True, False}
    homologies = {
        integral_homology(analyzer, generator._close_annulus(random.Random(seed)).target)
        for seed in range(8)
    }
    assert homologies == {
        "H_0=Z; H_1=Z^2; H_2=Z",
        "H_0=Z; H_1=Z ⊕ Z/2; H_2=0",
    }


def test_morphism_invariants_are_computed_from_source_and_target() -> None:
    analyzer = SurfaceAnalyzer()
    morphism = RandomSurfaceMorphismGenerator(
        load_generation_config(SURFACE_GENERATION_DEFAULTS), analyzer
    )._glue_two_disks(random.Random(4), 3)

    assert _question("euler-change")._answer(morphism) == 0
    assert _question("boundary-change")._answer(morphism) == -2
    assert _question("component-change")._answer(morphism) == -1
    assert _question("map-injective")._answer(morphism) is False
    assert _question("map-surjective")._answer(morphism) is True
    assert _question("homology-isomorphism")._answer(morphism) is False
    assert _question("target-homology")._answer(morphism) == "H_0=Z; H_1=0; H_2=Z"


def test_renderer_is_deterministic() -> None:
    request = GenerationRequest(3, 5)
    generation_config = load_generation_config(SURFACE_GENERATION_DEFAULTS)
    surface = RandomSurfacePresentationGenerator(generation_config, SurfaceAnalyzer()).generate_for(
        SurfaceObjectGenerationContext(
            request,
            generation_config.object_law_for("euler-characteristic"),
            SamplingSession(request.seed, generation_config.profile_version),
        )
    )
    config = load_rendering_config(SURFACE_RENDERING_DEFAULTS)
    renderer = MatplotlibGluingDiagramRenderer(SurfaceDiagramPlanner(config), config)

    assert renderer.render(surface, request, random.Random(1)) == renderer.render(
        surface, request, random.Random(999)
    )


def test_diagram_plan_uses_regular_polygons_with_one_shared_side_length() -> None:
    surface = SurfacePresentation((Polygon("T", 3), Polygon("O", 8)), ())
    plan = SurfaceDiagramPlanner(load_rendering_config(SURFACE_RENDERING_DEFAULTS)).plan(
        surface, random.Random(12)
    )
    lengths = [
        pytest.approx(layout.side_length) for layout in plan.polygons for _ in layout.vertices
    ]

    assert all(
        math.dist(*layout.edge(edge)) == lengths[0]
        for layout in plan.polygons
        for edge in range(len(layout.vertices))
    )
    assert plan.style.path_width <= plan.style.polygon_width


def test_cross_polygon_gluings_are_always_dotted() -> None:
    gluing = EdgeGluing(EdgeRef(0, 0), EdgeRef(1, 1), "a")
    surface = SurfacePresentation((Polygon("P", 4), Polygon("Q", 4)), (gluing,))

    for boundary_pattern in LinePattern:
        assert (
            SurfaceDiagramPlanner.edge_pattern(surface, gluing.first, boundary_pattern)
            is LinePattern.DOTTED
        )
        assert (
            SurfaceDiagramPlanner.edge_pattern(surface, gluing.second, boundary_pattern)
            is LinePattern.DOTTED
        )


def test_stacked_paths_get_the_required_curvature_lanes_and_display_styles() -> None:
    interior = (
        OrientedEdge(EdgeRef(0, 0)),
        OrientedEdge(EdgeRef(0, 1)),
    )
    edge = (OrientedEdge(EdgeRef(0, 2)),)
    surface = SurfacePresentation(
        (Polygon("P", 4),),
        (),
        (
            SurfacePath("p", interior),
            SurfacePath("q", interior),
            SurfacePath("r", edge),
            SurfacePath("s", edge),
        ),
    )
    config = load_rendering_config(SURFACE_RENDERING_DEFAULTS)
    plan = SurfaceDiagramPlanner(config).plan(surface, random.Random(4))
    interior_curvatures = [
        curve.curvature for curve in plan.curves if not curve.segment.lies_on_edge
    ]
    edge_curvatures = [curve.curvature for curve in plan.curves if curve.segment.lies_on_edge]

    assert interior_curvatures == [-32.0, 32.0]
    assert edge_curvatures == [32.0, 54.0]
    assert {curve.style.order_display for curve in plan.curves[:2]} == set(OrderDisplay)
    assert plan.curves[0].style.color != plan.curves[1].style.color


def test_diagram_style_rejects_paths_heavier_than_polygon_edges() -> None:
    with pytest.raises(ValueError, match="no wider"):
        DiagramStyle(Palette("white", "black", ("red",)), LinePattern.SOLID, 2, 3)


def test_contractible_polygon_local_loop_is_drawn_as_its_directed_edge_run() -> None:
    edge = EdgeRef(0, 0)
    surface = SurfacePresentation(
        (Polygon("P", 4),),
        (),
        (SurfacePath("p", (OrientedEdge(edge), OrientedEdge(edge, False))),),
    )
    plan = SurfaceDiagramPlanner(load_rendering_config(SURFACE_RENDERING_DEFAULTS)).plan(
        surface, random.Random(9)
    )

    assert len(plan.curves) == 2
    assert all(curve.segment.lies_on_edge for curve in plan.curves)
    assert [curve.segment.order for curve in plan.curves] == [1, 2]
    assert [curve.curvature for curve in plan.curves] == [32.0, 54.0]


def test_yaml_rendering_overrides_are_injected_through_the_container() -> None:
    override = Path(__file__).with_name("rendering_override.yaml")
    container = build_container(override)

    config = container.resolve(SurfaceRenderingConfig)
    planner = container.resolve(SurfaceDiagramPlanner)

    assert config.geometry.side_length == 150
    assert config.stroke.path_width == 1.1
    assert planner.config is config


def test_benchmark_generates_registered_object_and_morphism_recipes() -> None:
    catalog = build_container().resolve(BenchmarkCatalog)
    problems = [
        catalog.generate(domain="surfaces", request=GenerationRequest(seed, 8))
        for seed in range(40)
    ]

    assert all(section.media_type == "image/svg+xml" for p in problems for section in p.sections)
    assert {len(problem.sections) for problem in problems} == {1, 2}
    morphism = catalog.generate_recipe(
        domain="surfaces",
        request=GenerationRequest(7, 8),
        recipe_id="boundary-change",
    )
    assert len(morphism.sections) == 2
    assert "first diagram is the source" in morphism.question
    assert catalog.generate(domain="surfaces", request=GenerationRequest(7, 8)) == catalog.generate(
        domain="surfaces", request=GenerationRequest(7, 8)
    )


def test_polygon_attachment_is_a_first_class_inclusion() -> None:
    analyzer = SurfaceAnalyzer()
    morphism = RandomSurfaceMorphismGenerator(
        load_generation_config(SURFACE_GENERATION_DEFAULTS), analyzer
    )._attach_polygon(random.Random(5))

    assert morphism.name == "polygon-attachment-inclusion"
    assert len(morphism.target.polygons) == len(morphism.source.polygons) + 1
    assert analyzer.analyze(morphism.source).euler_characteristic == 1
    assert analyzer.analyze(morphism.target).euler_characteristic == 1
    assert _question("map-injective")._answer(morphism) is True
    assert _question("map-surjective")._answer(morphism) is False
    assert _question("homology-isomorphism")._answer(morphism) is True


def test_difficulty_is_validated() -> None:
    with pytest.raises(ValueError, match="difficulty"):
        GenerationRequest(seed=0, difficulty=11)


def test_domain_model_contains_only_combinatorial_data() -> None:
    presentation = SurfacePresentation((Polygon("P", 5),), ())

    assert presentation.polygons[0].sides == 5
    assert not hasattr(presentation, "palette")
    assert not hasattr(presentation.polygons[0], "vertices")


def test_path_adjacency_and_homology_use_quotient_vertices() -> None:
    torus = SurfacePresentation(
        (Polygon("P", 4),),
        (
            EdgeGluing(EdgeRef(0, 0), EdgeRef(0, 2), "a", False),
            EdgeGluing(EdgeRef(0, 1), EdgeRef(0, 3), "b", False),
        ),
        (SurfacePath("p", (OrientedEdge(EdgeRef(0, 0)),)),),
    )
    analyzer = SurfaceAnalyzer()
    homology = analyzer.cellular_homology(torus)

    assert torus.is_closed
    assert analyzer.path_is_cycle(torus, torus.paths[0])
    assert homology.h1_rank == 2
    assert homology.h1_torsion == ()
    assert len(analyzer.path_representative(torus, torus.paths[0])) == len(homology.cycle_basis)


def test_path_coordinates_use_tagged_edges_and_an_explicit_homology_basis() -> None:
    torus = SurfacePresentation(
        (Polygon("P", 4),),
        (
            EdgeGluing(EdgeRef(0, 0), EdgeRef(0, 2), "a", False),
            EdgeGluing(EdgeRef(0, 1), EdgeRef(0, 3), "b", False),
        ),
        (SurfacePath("p", (OrientedEdge(EdgeRef(0, 0)),)),),
    )
    analyzer = SurfaceAnalyzer()
    assert analyzer.h1_edge_generators(torus) == (((1, 0), None), ((0, 1), None))
    assert _question("path-representative")._answer(torus) == (1, 0)

    problem = next(
        problem
        for seed in range(80)
        if (
            problem := build_container()
            .resolve(BenchmarkCatalog)
            .generate(domain="surfaces", request=GenerationRequest(seed, 10))
        ).question_id
        == "path-representative"
    )
    assert isinstance(problem.answer, tuple)
    assert "ordered generators" in problem.question
    assert "<!-- e1 -->" in problem.sections[0].content
    assert "c1" not in problem.sections[0].content


def test_an_edge_cannot_be_used_by_two_gluings() -> None:
    with pytest.raises(ValueError, match="at most once"):
        SurfacePresentation(
            (Polygon("P", 4),),
            (
                EdgeGluing(EdgeRef(0, 0), EdgeRef(0, 1), "a"),
                EdgeGluing(EdgeRef(0, 0), EdgeRef(0, 2), "b"),
            ),
        )
