from pathlib import Path

from pydantic import BaseModel, ConfigDict

from topology_benchmark.core.configuration import load_yaml_config
from topology_benchmark.domains.surfaces.generation.config import (
    SurfaceGenerationConfig,
    SurfaceGenerationInput,
    resolve_surface_generation_config,
)
from topology_benchmark.domains.surfaces.rendering.config import SurfaceRenderingConfig


class SurfaceDomainConfig(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    generation: SurfaceGenerationConfig
    rendering: SurfaceRenderingConfig


class _SurfaceDomainDocument(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    generation: SurfaceGenerationInput
    rendering: SurfaceRenderingConfig


def load_surface_domain_config(path: str | Path) -> SurfaceDomainConfig:
    document = load_yaml_config(path, _SurfaceDomainDocument)
    return SurfaceDomainConfig(
        generation=resolve_surface_generation_config(document.generation),
        rendering=document.rendering,
    )
