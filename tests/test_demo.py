import json
from io import BytesIO
from unittest.mock import MagicMock

import pytest

from topology_benchmark import BenchmarkCatalog, build_container
from topology_benchmark.application.demo import DemoApplication, serve_demo
from topology_benchmark.core.errors import GenerationError
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


@pytest.mark.parametrize(
    ("error", "status"),
    [(ValueError("render failed"), 500), (GenerationError("attempts exhausted"), 503)],
)
def test_demo_logs_server_failures_with_tracebacks(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
    status: int,
) -> None:
    catalog = build_container().resolve(BenchmarkCatalog)
    monkeypatch.setattr(DemoApplication, "problem_json", MagicMock(side_effect=error))
    server_factory = MagicMock()
    monkeypatch.setattr("topology_benchmark.application.demo.ThreadingHTTPServer", server_factory)
    serve_demo(catalog=catalog, default_domain="surfaces")
    handler = server_factory.call_args.args[1]
    response = BytesIO()
    connection = MagicMock()
    connection.makefile.return_value = BytesIO(
        b"GET /api/problem?domain=surfaces&seed=12 HTTP/1.0\r\n\r\n"
    )
    connection.sendall.side_effect = response.write

    handler(connection, ("127.0.0.1", 12345), server_factory.return_value)

    assert response.getvalue().startswith(f"HTTP/1.0 {status}".encode())
    assert (
        f'"GET /api/problem?domain=surfaces&seed=12 HTTP/1.0" {status}' in capsys.readouterr().err
    )
    assert "Problem generation failed for /api/problem?domain=surfaces&seed=12" in caplog.text
    assert "Traceback (most recent call last)" in caplog.text
    exception_info = caplog.records[-1].exc_info
    assert exception_info is not None
    assert exception_info[1] is error
    if status == 500:
        assert b'{"error": "internal server error"}' in response.getvalue()


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
