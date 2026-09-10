import json

from topology_benchmark import (
    PolyhedralNetBenchmark,
    SurfaceBenchmark,
    TorusSlicesBenchmark,
    build_container,
)
from topology_benchmark.application.demo import DemoApplication


def test_demo_serializes_any_problem_provider() -> None:
    benchmark = build_container().resolve(SurfaceBenchmark)
    demo = DemoApplication(benchmark)

    payload = json.loads(demo.problem_json(seed=12, difficulty=7))

    assert payload["seed"] == 12
    assert payload["question"]
    assert payload["prompts"]
    assert all(prompt["media_type"] == "image/svg+xml" for prompt in payload["prompts"])


def test_demo_page_has_regeneration_and_generic_media_rendering() -> None:
    page = DemoApplication.index_html().decode()

    assert "New random problem" in page
    assert '<select id="domain">' in page
    assert "/api/problem?domain=" in page
    assert "prompt.media_type.startsWith('image/')" in page
    assert "prompt.media_type.startsWith('audio/')" in page
    assert "Reveal ground truth" in page


def test_demo_can_switch_between_registered_domains() -> None:
    container = build_container()
    surfaces = container.resolve(SurfaceBenchmark)
    polyhedral_nets = container.resolve(PolyhedralNetBenchmark)
    torus_slices = container.resolve(TorusSlicesBenchmark)
    demo = DemoApplication(
        surfaces,
        providers={
            "surfaces": surfaces,
            "polyhedral-nets": polyhedral_nets,
            "torus-slices": torus_slices,
        },
        default_domain="surfaces",
    )

    surface = json.loads(demo.problem_json(seed=5, difficulty=4, domain="surfaces"))
    net = json.loads(demo.problem_json(seed=5, difficulty=4, domain="polyhedral-nets"))
    tori = json.loads(demo.problem_json(seed=5, difficulty=4, domain="torus-slices"))

    assert surface["metadata"].get("domain") != "polyhedral-nets"
    assert net["metadata"]["domain"] == "polyhedral-nets"
    assert tori["metadata"]["domain"] == "torus-slices"
    assert demo.domains == ("surfaces", "polyhedral-nets", "torus-slices")
