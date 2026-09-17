from typing import Annotated, Literal, Self

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from topology_benchmark.utils.matplotlib import ArrowConfig, GlowLayerConfig, SketchConfig


def _yaml_tuple(value: object) -> object:
    return tuple(value) if isinstance(value, list) else value


type YamlTuple[T] = Annotated[tuple[T, ...], BeforeValidator(_yaml_tuple)]


class _StrictConfigModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid", allow_inf_nan=False)


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


class _CommonStrokeConfig(_StrictConfigModel):
    polygon_width: float = Field(gt=0)
    path_width: float = Field(gt=0)
    vertex_size: float = Field(gt=0)
    dotted_pattern: YamlTuple[Annotated[float, Field(gt=0)]]

    @model_validator(mode="after")
    def _validate_common_strokes(self) -> Self:
        if self.path_width > self.polygon_width:
            raise ValueError("a visual style's path_width must not exceed polygon_width")
        if not self.dotted_pattern:
            raise ValueError("a visual style's dotted_pattern must not be empty")
        return self


class StrokeConfig(_CommonStrokeConfig):
    sketch: SketchConfig | None
    glow_layers: YamlTuple[GlowLayerConfig]

    @model_validator(mode="after")
    def _validate_glow_layers(self) -> Self:
        widths = tuple(layer.width_factor for layer in self.glow_layers)
        if tuple(sorted(widths, reverse=True)) != widths:
            raise ValueError("glow layers must be ordered from widest to narrowest")
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
    font_family: str = Field(min_length=1)


class PaletteConfig(_StrictConfigModel):
    fill: str = Field(min_length=1)
    ink: str = Field(min_length=1)
    path_colors: YamlTuple[Annotated[str, Field(min_length=1)]]

    @model_validator(mode="after")
    def _has_path_colors(self) -> Self:
        if not self.path_colors:
            raise ValueError("each rendering palette needs path colors")
        return self


class GridConfig(_StrictConfigModel):
    spacing: float = Field(gt=0)
    color: str = Field(min_length=1)
    width: float = Field(gt=0)
    alpha: float = Field(gt=0, le=1)
    major_every: int = Field(ge=1)


class SurfaceVisualStyleConfig(_StrictConfigModel):
    backend: Literal["matplotlib-svg"]
    stroke: StrokeConfig
    grid: GridConfig | None
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    weight: float = Field(ge=0)
    canvas_color: str = Field(min_length=1)
    palettes: YamlTuple[PaletteConfig]
    arrows: ArrowConfig
    labels: LabelConfig

    @model_validator(mode="after")
    def _has_palettes(self) -> Self:
        if not self.palettes:
            raise ValueError("each visual style needs at least one palette")
        return self


class SurfaceRenderingConfig(_StrictConfigModel):
    canvas: CanvasConfig
    geometry: GeometryConfig
    styles: YamlTuple[SurfaceVisualStyleConfig]

    @model_validator(mode="after")
    def _has_unique_styles(self) -> Self:
        if not self.styles:
            raise ValueError("rendering.styles must not be empty")
        if not any(style.weight > 0 for style in self.styles):
            raise ValueError("rendering.styles needs at least one positive weight")
        ids = tuple(style.id for style in self.styles)
        if len(set(ids)) != len(ids):
            raise ValueError("rendering style IDs must be unique")
        return self
