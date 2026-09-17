from random import Random

import pytest
from pydantic import ValidationError

from topology_benchmark import build_container
from topology_benchmark.application.configuration import SURFACE_DOMAIN_CONFIG
from topology_benchmark.core.probability.sampling import SamplingSession
from topology_benchmark.core.problem.models import GenerationRequest
from topology_benchmark.domains.surfaces.abstractions import (
    ISurfaceGenerator,
    ISurfaceRenderBackend,
)
from topology_benchmark.domains.surfaces.config import load_surface_domain_config
from topology_benchmark.domains.surfaces.generation.context.object import (
    SurfaceObjectGenerationContext,
)
from topology_benchmark.domains.surfaces.rendering.backend.matplotlib_svg import (
    MatplotlibSurfaceRenderBackend,
)
from topology_benchmark.domains.surfaces.rendering.config import SurfaceVisualStyleConfig
from topology_benchmark.domains.surfaces.rendering.diagram_planner import SurfaceDiagramPlanner


@pytest.mark.parametrize("style_id", ["classic", "hand-drawn", "blueprint", "neon"])
def test_surface_styles_render_reproducible_svg(style_id: str) -> None:
    container = build_container()
    config = load_surface_domain_config(SURFACE_DOMAIN_CONFIG)
    assert {style.id for style in config.rendering.styles} == {
        "classic",
        "hand-drawn",
        "blueprint",
        "neon",
    }
    style = next(style for style in config.rendering.styles if style.id == style_id)
    rendering = config.rendering.model_copy(update={"styles": (style,)})
    planner = SurfaceDiagramPlanner(rendering)
    backend = container.resolve(ISurfaceRenderBackend)
    assert isinstance(backend, MatplotlibSurfaceRenderBackend)
    request = GenerationRequest(seed=42, difficulty=1)
    surface = container.resolve(ISurfaceGenerator).generate_for(
        SurfaceObjectGenerationContext(
            request,
            config.generation.object_law_for("euler-characteristic"),
            SamplingSession(request.seed, config.generation.profile_version),
        )
    )
    plan = planner.plan(surface, Random(42))
    first = backend.render(surface, plan, request)
    assert first.media_type == "image/svg+xml"
    assert "<svg" in first.content
    assert backend.render(surface, plan, request) == first


def test_surface_style_rejects_unsupported_backend() -> None:
    config = load_surface_domain_config(SURFACE_DOMAIN_CONFIG)
    document = config.rendering.styles[0].model_dump()
    document["backend"] = "unsupported"
    with pytest.raises(ValidationError, match="backend"):
        SurfaceVisualStyleConfig.model_validate(document)
