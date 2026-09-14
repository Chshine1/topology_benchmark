import json

from topology_benchmark import BenchmarkCatalog, build_container
from topology_benchmark.application.demo import DemoApplication
from topology_benchmark.core.problem.models import GenerationRequest
from topology_benchmark.domains.polyhedral_nets.services.polyhedral_net_analyzer import (
    PolyhedralNetAnalyzer,
)
from topology_benchmark.domains.surfaces.generation.generator.morphism import (
    RandomSurfaceMorphismGenerator,
)
from topology_benchmark.domains.surfaces.generation.generator.object import (
    RandomSurfacePresentationGenerator,
)
from topology_benchmark.domains.surfaces.services import SurfaceAnalyzer
from topology_benchmark.domains.torus_slices.generation.torus_slice_generator import (
    RandomTorusSliceGenerator,
)
from topology_benchmark.domains.torus_slices.services.torus_family_analyzer import (
    TorusFamilyAnalyzer,
)


def test_demo_serializes_any_problem_provider() -> None:
    catalog = build_container().resolve(BenchmarkCatalog)
    demo = DemoApplication(catalog, "surfaces")

    payload = json.loads(demo.problem_json(request=GenerationRequest(12, 7)))

    assert payload["seed"] == 12
    assert payload["prompt"]
    assert payload["sections"]
    assert all(section["media_type"] == "image/svg+xml" for section in payload["sections"])


def test_demo_page_has_regeneration_and_generic_media_rendering() -> None:
    container = build_container()
    page = DemoApplication(container.resolve(BenchmarkCatalog), "surfaces").index_html().decode()

    assert "New random problem" in page
    assert '<select id="domain">' in page
    assert "/api/problem?domain=" in page
    assert "section.media_type.startsWith('image/')" in page
    assert "section.media_type.startsWith('audio/')" in page
    assert "Reveal ground truth" in page


def test_demo_can_switch_between_registered_domains() -> None:
    container = build_container()
    demo = DemoApplication(container.resolve(BenchmarkCatalog), "surfaces")

    request = GenerationRequest(5, 4)
    surface = json.loads(demo.problem_json(request=request, domain="surfaces"))
    net = json.loads(demo.problem_json(request=request, domain="polyhedral-nets"))
    tori = json.loads(demo.problem_json(request=request, domain="torus-slices"))

    assert surface["recipe_id"]
    assert net["recipe_id"]
    assert tori["recipe_id"]
    assert "metadata" not in surface
    assert "metadata" not in net
    assert "metadata" not in tori
    assert demo.domains == ("surfaces", "polyhedral-nets", "torus-slices")


def test_stateless_analyzers_are_singletons_injected_into_generators() -> None:
    container = build_container()
    surface_analyzer = container.resolve(SurfaceAnalyzer)
    torus_analyzer = container.resolve(TorusFamilyAnalyzer)

    assert container.resolve(SurfaceAnalyzer) is surface_analyzer
    assert container.resolve(PolyhedralNetAnalyzer) is container.resolve(PolyhedralNetAnalyzer)
    assert container.resolve(TorusFamilyAnalyzer) is torus_analyzer
    assert container.resolve(RandomSurfacePresentationGenerator)._analyzer is surface_analyzer
    assert container.resolve(RandomSurfaceMorphismGenerator)._analyzer is surface_analyzer
    assert container.resolve(RandomTorusSliceGenerator)._analyzer is torus_analyzer
