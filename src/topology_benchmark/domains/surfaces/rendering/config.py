from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Self, cast

import yaml
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from topology_benchmark.core.errors import ConfigurationError

type ConfigMap = dict[str, object]


def _yaml_tuple(value: object) -> object:
    return tuple(value) if isinstance(value, list) else value


type YamlTuple[T] = Annotated[tuple[T, ...], BeforeValidator(_yaml_tuple)]


class _StrictConfigModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        allow_inf_nan=False,
    )


class CanvasConfig(_StrictConfigModel):
    max_columns: int = Field(ge=1)
    cell_width: float = Field(gt=0)
    cell_height: float = Field(gt=0)
    margin_x: float = Field(gt=0)
    margin_y: float = Field(gt=0)


class CurvatureConfig(_StrictConfigModel):
    edge_base: float = Field(ge=0)
    edge_step: float = Field(ge=0)
    interior_step: float = Field(ge=0)


class GeometryConfig(_StrictConfigModel):
    side_length: float = Field(gt=0)
    curve_samples: int = Field(ge=8)
    curvature: CurvatureConfig


class StrokeConfig(_StrictConfigModel):
    polygon_width: float = Field(gt=0)
    path_width: float = Field(gt=0)
    vertex_size: float = Field(gt=0)
    dotted_pattern: YamlTuple[Annotated[float, Field(gt=0)]]

    @model_validator(mode="after")
    def _path_not_wider_than_polygon(self) -> Self:
        if self.path_width > self.polygon_width:
            raise ValueError("rendering.stroke.path_width must not exceed polygon_width")
        if not self.dotted_pattern:
            raise ValueError("rendering.stroke.dotted_pattern must not be empty")
        return self


class ArrowConfig(_StrictConfigModel):
    gluing_size: float = Field(gt=0)
    path_size: float = Field(gt=0)
    path_count_limit: int = Field(ge=1)
    spread_start: float = Field(ge=0, le=1)
    spread_end: float = Field(ge=0, le=1)
    tangent_span: float = Field(gt=0)

    @model_validator(mode="after")
    def _spread_is_ordered(self) -> Self:
        if self.spread_start > self.spread_end:
            raise ValueError("rendering.arrows spread_start must not exceed spread_end")
        return self


class LabelConfig(_StrictConfigModel):
    polygon_size: float = Field(gt=0)
    gluing_size: float = Field(gt=0)
    path_size: float = Field(gt=0)
    order_size: float = Field(gt=0)
    tag_offset: float = Field(gt=0)
    tag_clearance: float = Field(gt=0)
    gluing_offset: float = Field(gt=0)
    path_offset: float = Field(gt=0)


class PaletteConfig(_StrictConfigModel):
    fill: str = Field(min_length=1)
    ink: str = Field(min_length=1)
    path_colors: YamlTuple[Annotated[str, Field(min_length=1)]]

    @model_validator(mode="after")
    def _has_path_colors(self) -> Self:
        if not self.path_colors:
            raise ValueError("each rendering palette needs path colors")
        return self


class SurfaceRenderingConfig(_StrictConfigModel):
    canvas: CanvasConfig
    geometry: GeometryConfig
    stroke: StrokeConfig
    arrows: ArrowConfig
    labels: LabelConfig
    palettes: YamlTuple[PaletteConfig]

    @model_validator(mode="after")
    def _has_palettes(self) -> Self:
        if not self.palettes:
            raise ValueError("rendering.palettes must not be empty")
        return self


class _RenderingDocument(_StrictConfigModel):
    rendering: SurfaceRenderingConfig


def load_rendering_config(
    default_path: str | Path,
    override_path: str | Path | None = None,
) -> SurfaceRenderingConfig:
    """Recursively overlay an optional file on the supplied defaults."""

    merged = _read_yaml(Path(default_path))
    if override_path is not None:
        merged = _deep_merge(merged, _read_yaml(Path(override_path)))
    return _RenderingDocument.model_validate(merged).rendering


def _read_yaml(path: Path) -> ConfigMap:
    with path.open(encoding="utf-8") as stream:
        value = cast(object, yaml.safe_load(stream))
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ConfigurationError(f"{path} must be a YAML mapping with string keys")
    return cast(ConfigMap, value)


def _deep_merge(base: ConfigMap, override: ConfigMap) -> ConfigMap:
    result = dict(base)
    for key, value in override.items():
        current = result.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            result[key] = _deep_merge(dict(current), dict(value))
        else:
            result[key] = value
    return result
