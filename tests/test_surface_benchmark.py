import base64
import io
import math
import random
import shutil
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest
import yaml
from matplotlib import image as matplotlib_image

from topology_benchmark import BenchmarkCatalog, build_container
from topology_benchmark.application.configuration import SURFACE_DOMAIN_CONFIG
from topology_benchmark.core.probability.sampling import SamplingSession
from topology_benchmark.core.problem.models import GenerationRequest
from topology_benchmark.domains.surfaces.abstractions import SurfaceProblemRecipeCatalog
from topology_benchmark.domains.surfaces.config import load_surface_domain_config
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
from topology_benchmark.domains.surfaces.recipes.homology import integral_homology
from topology_benchmark.domains.surfaces.rendering.backend.blender import (
    BlenderRuntimeConfig,
    BlenderSurfaceRenderBackend,
)
from topology_benchmark.domains.surfaces.rendering.backend.matplotlib_svg import (
    MatplotlibSurfaceRenderBackend,
)
from topology_benchmark.domains.surfaces.rendering.config import (
    SurfaceRenderingConfig,
)
from topology_benchmark.domains.surfaces.rendering.diagram_planner import (
    LinePattern,
    OrderDisplay,
    SurfaceDiagramPlanner,
)
from topology_benchmark.domains.surfaces.rendering.visual_style import SurfaceVisualStyleSelector
from topology_benchmark.domains.surfaces.services import SurfaceAnalyzer


def _domain_config():
    return load_surface_domain_config(SURFACE_DOMAIN_CONFIG)


def _recipe(recipe_id: str) -> Any:
    return build_container().resolve(SurfaceProblemRecipeCatalog)[recipe_id]


def _planner(config: SurfaceRenderingConfig) -> SurfaceDiagramPlanner:
    return SurfaceDiagramPlanner(config, SurfaceVisualStyleSelector(config))


def test_generated_quotients_are_compact_surfaces_without_stored_invariants() -> None:
    analyzer = SurfaceAnalyzer()
    generator = RandomSurfacePresentationGenerator(
        (config := _domain_config().generation), analyzer
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
        _domain_config().generation, analyzer
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
    generator = RandomSurfaceMorphismGenerator(_domain_config().generation, analyzer)
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
        _domain_config().generation, analyzer
    )._glue_two_disks(random.Random(4), 3)

    assert _recipe("euler-change")._answer(morphism) == 0
    assert _recipe("boundary-change")._answer(morphism) == -2
    assert _recipe("component-change")._answer(morphism) == -1
    assert _recipe("map-injective")._answer(morphism) is False
    assert _recipe("map-surjective")._answer(morphism) is True
    assert _recipe("homology-isomorphism")._answer(morphism) is False
    assert _recipe("target-homology")._answer(morphism) == "H_0=Z; H_1=0; H_2=Z"


def test_renderer_is_deterministic() -> None:
    request = GenerationRequest(3, 5)
    generation_config = _domain_config().generation
    surface = RandomSurfacePresentationGenerator(generation_config, SurfaceAnalyzer()).generate_for(
        SurfaceObjectGenerationContext(
            request,
            generation_config.object_law_for("euler-characteristic"),
            SamplingSession(request.seed, generation_config.profile_version),
        )
    )
    config = _domain_config().rendering
    planner = _planner(config)
    renderer = MatplotlibSurfaceRenderBackend()
    first_plan = planner.plan(surface, random.Random((request.seed << 8) ^ 0xA53C9E))
    second_plan = planner.plan(surface, random.Random((request.seed << 8) ^ 0xA53C9E))

    assert renderer.render(surface, first_plan, request) == renderer.render(
        surface, second_plan, request
    )


def test_matplotlib_renderer_adjusts_all_labels_away_from_sampled_strokes() -> None:
    config = _domain_config().rendering
    style = next(style for style in config.styles if style.id == "classic")
    planner = _planner(config.model_copy(update={"styles": (style,)}))
    surface = SurfacePresentation(
        (Polygon("P", 5),),
        (),
        (SurfacePath("p", (OrientedEdge(EdgeRef(0, 1)),)),),
        ((EdgeRef(0, 3), "A"),),
    )
    request = GenerationRequest(29, 5)
    plan = planner.plan(surface, random.Random(29))

    with patch(
        "topology_benchmark.domains.surfaces.rendering.backend.matplotlib_svg.adjust_text"
    ) as adjust:
        MatplotlibSurfaceRenderBackend().render(surface, plan, request)

    texts = adjust.call_args.args[0]
    assert {text.get_text() for text in texts} >= {"P", "p", "A"}
    assert len(adjust.call_args.kwargs["x"]) == len(adjust.call_args.kwargs["y"])
    assert len(adjust.call_args.kwargs["x"]) > len(plan.curves[0].points)
    assert adjust.call_args.kwargs["iter_lim"] == 200


def test_visual_styles_form_an_exact_configured_distribution() -> None:
    selector = SurfaceVisualStyleSelector(_domain_config().rendering)

    assert {item.value.id for item in selector.distribution.values} == {
        "classic",
        "hand-drawn",
        "blueprint",
        "neon",
        "pencil-study",
        "ink-crosshatch",
    }
    assert selector.distribution.probability(lambda style: style.id == "neon") == pytest.approx(0.2)


@pytest.mark.parametrize("style_id", ["classic", "hand-drawn", "blueprint", "neon"])
def test_each_visual_style_renders_without_style_specific_dispatch(style_id: str) -> None:
    config = _domain_config().rendering
    style = next(style for style in config.styles if style.id == style_id)
    single_style_config = config.model_copy(update={"styles": (style,)})
    planner = _planner(single_style_config)
    renderer = MatplotlibSurfaceRenderBackend()
    surface = SurfacePresentation(
        (Polygon("P", 5),),
        (),
        (SurfacePath("p", (OrientedEdge(EdgeRef(0, 1)),)),),
    )
    request = GenerationRequest(19, 4)
    plan = planner.plan(surface, random.Random((request.seed << 8) ^ 0xA53C9E))

    section = renderer.render(surface, plan, request)

    assert section.media_type == "image/svg+xml"
    assert f"surface visual style: {style_id}" in section.content
    assert style.canvas_color.lower() in section.content.lower()


@pytest.mark.skipif(shutil.which("blender") is None, reason="Blender is not installed")
@pytest.mark.parametrize("style_id", ["pencil-study", "ink-crosshatch"])
def test_blender_styles_render_headless_png(style_id: str) -> None:
    config = _domain_config().rendering
    style = next(style for style in config.styles if style.id == style_id)
    enabled_style = style.model_copy(update={"weight": 1.0})
    single_style_config = config.model_copy(update={"styles": (enabled_style,)})
    planner = _planner(single_style_config)
    surface = SurfacePresentation(
        (Polygon("P", 5),),
        (),
        (SurfacePath("p", (OrientedEdge(EdgeRef(0, 1)),)),),
    )
    request = GenerationRequest(23, 5)
    plan = planner.plan(surface, random.Random((request.seed << 8) ^ 0xA53C9E))
    backend = BlenderSurfaceRenderBackend(BlenderRuntimeConfig("blender", 120.0))

    section = backend.render(surface, plan, request)

    assert section.media_type == "image/png"
    assert base64.b64decode(section.content).startswith(b"\x89PNG\r\n\x1a\n")
    pixels = matplotlib_image.imread(io.BytesIO(base64.b64decode(section.content)))
    assert pixels.shape == (plan.height, plan.width, 4)
    assert float(pixels.std()) > 0.01
    if style_id == "pencil-study":
        repeated = backend.render(surface, plan, request)
        repeated_pixels = matplotlib_image.imread(io.BytesIO(base64.b64decode(repeated.content)))
        assert (pixels == repeated_pixels).all()
        assert repeated == section


def test_diagram_plan_uses_regular_polygons_with_one_shared_side_length() -> None:
    surface = SurfacePresentation((Polygon("T", 3), Polygon("O", 8)), ())
    plan = _planner(_domain_config().rendering).plan(surface, random.Random(12))
    lengths = [
        pytest.approx(math.dist(*layout.edge(0)))
        for layout in plan.polygons
        for _ in layout.vertices
    ]

    assert all(
        math.dist(*layout.edge(edge)) == lengths[0]
        for layout in plan.polygons
        for edge in range(len(layout.vertices))
    )
    assert (
        plan.style.visual.profile.stroke.path_width
        <= plan.style.visual.profile.stroke.polygon_width
    )


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
    config = _domain_config().rendering
    plan = _planner(config).plan(surface, random.Random(4))
    interior_curvatures = [
        curve.curvature for curve in plan.curves if not len(curve.segment.edges) == 1
    ]
    edge_curvatures = [curve.curvature for curve in plan.curves if len(curve.segment.edges) == 1]

    assert interior_curvatures == [-32.0, 32.0]
    assert edge_curvatures == [32.0, 54.0]
    assert {curve.style.order_display for curve in plan.curves[:2]} == set(OrderDisplay)
    assert plan.curves[0].style.color != plan.curves[1].style.color


def test_contractible_polygon_local_loop_is_drawn_as_its_directed_edge_run() -> None:
    edge = EdgeRef(0, 0)
    surface = SurfacePresentation(
        (Polygon("P", 4),),
        (),
        (SurfacePath("p", (OrientedEdge(edge), OrientedEdge(edge, False))),),
    )
    plan = _planner(_domain_config().rendering).plan(surface, random.Random(9))

    assert len(plan.curves) == 2
    assert all(len(curve.segment.edges) == 1 for curve in plan.curves)
    assert [curve.segment.order for curve in plan.curves] == [1, 2]
    assert [curve.curvature for curve in plan.curves] == [32.0, 54.0]


def test_complete_surface_yaml_is_injected_through_the_container(tmp_path: Path) -> None:
    document = yaml.safe_load(SURFACE_DOMAIN_CONFIG.read_text(encoding="utf-8"))
    document["rendering"]["geometry"]["side_length"] = 150
    document["rendering"]["styles"][0]["stroke"]["path_width"] = 1.1
    override = tmp_path / "surfaces.yaml"
    override.write_text(cast(str, yaml.safe_dump(document)), encoding="utf-8")
    container = build_container(surface_config=override)

    config = container.resolve(SurfaceRenderingConfig)
    planner = container.resolve(SurfaceDiagramPlanner)

    assert config.geometry.side_length == 150
    assert config.styles[0].stroke.path_width == 1.1
    assert planner._config is config


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
    assert "first diagram is the source" in morphism.prompt
    assert catalog.generate(domain="surfaces", request=GenerationRequest(7, 8)) == catalog.generate(
        domain="surfaces", request=GenerationRequest(7, 8)
    )


def test_polygon_attachment_is_a_first_class_inclusion() -> None:
    analyzer = SurfaceAnalyzer()
    morphism = RandomSurfaceMorphismGenerator(
        _domain_config().generation, analyzer
    )._attach_polygon(random.Random(5))

    assert morphism.name == "polygon-attachment-inclusion"
    assert len(morphism.target.polygons) == len(morphism.source.polygons) + 1
    assert analyzer.analyze(morphism.source).euler_characteristic == 1
    assert analyzer.analyze(morphism.target).euler_characteristic == 1
    assert _recipe("map-injective")._answer(morphism) is True
    assert _recipe("map-surjective")._answer(morphism) is False
    assert _recipe("homology-isomorphism")._answer(morphism) is True


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
    assert _recipe("path-representative")._answer(torus) == (1, 0)

    problem = next(
        problem
        for seed in range(80)
        if (
            problem := build_container()
            .resolve(BenchmarkCatalog)
            .generate(domain="surfaces", request=GenerationRequest(seed, 10))
        ).recipe_id
        == "path-representative"
    )
    assert isinstance(problem.answer, tuple)
    assert "ordered generators" in problem.prompt
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
