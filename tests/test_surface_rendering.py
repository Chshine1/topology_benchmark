from random import Random
from typing import Any, cast

import pytest
from pydantic import TypeAdapter, ValidationError

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
from topology_benchmark.domains.surfaces.rendering.config import (
    SurfaceVisualStyleConfig,
    SurfaceVisualStyleDistribution,
)
from topology_benchmark.domains.surfaces.rendering.diagram_planner import SurfaceDiagramPlanner


@pytest.mark.parametrize("style_id", ["classic", "hand-drawn", "blueprint", "neon"])
def test_surface_styles_render_reproducible_svg(style_id: str) -> None:
    container = build_container()
    config = load_surface_domain_config(SURFACE_DOMAIN_CONFIG)
    styles_model = cast(Any, config.rendering.styles)
    styles = tuple(item.value for item in styles_model.distribution.values)
    assert {style.id for style in styles} == {
        "classic",
        "hand-drawn",
        "blueprint",
        "neon",
    }
    style = next(style for style in styles if style.id == style_id)
    selected_styles = TypeAdapter(SurfaceVisualStyleDistribution).validate_python(
        [{**style.model_dump(), "$weight": 1.0}]
    )
    rendering = config.rendering.model_copy(update={"styles": selected_styles})
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
    styles_model = cast(Any, config.rendering.styles)
    document = styles_model.distribution.values[0].value.model_dump()
    document["backend"] = "unsupported"
    with pytest.raises(ValidationError, match="backend"):
        SurfaceVisualStyleConfig.model_validate(document)


def test_surface_styles_and_palettes_are_configured_distributions() -> None:
    rendering = load_surface_domain_config(SURFACE_DOMAIN_CONFIG).rendering

    styles_model = cast(Any, rendering.styles)
    assert styles_model.distribution.probability(lambda style: style.id == "neon") == pytest.approx(
        0.2
    )
    classic = next(
        item.value for item in styles_model.distribution.values if item.value.id == "classic"
    )
    assert classic.palettes.distribution.probability(
        lambda palette: palette.fill == "#f8f5ed"
    ) == pytest.approx(1 / 3)
