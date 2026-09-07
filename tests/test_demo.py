import json

from topology_benchmark import SurfaceBenchmark, build_container
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
    assert "/api/problem?seed=" in page
    assert "prompt.media_type.startsWith('image/')" in page
    assert "prompt.media_type.startsWith('audio/')" in page
    assert "Reveal ground truth" in page
