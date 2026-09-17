from typing import Self

from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.patches import FancyArrowPatch
from pydantic import BaseModel, ConfigDict, Field, model_validator

from topology_benchmark.utils.planer_vector import point_at_fraction, Point


class _StrictConfigModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid", allow_inf_nan=False)


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
            raise ValueError("visual style arrow spread_start must not exceed spread_end")
        return self


class SketchConfig(_StrictConfigModel):
    scale: float = Field(gt=0)
    length: float = Field(gt=0)
    randomness: float = Field(gt=0)


class GlowLayerConfig(_StrictConfigModel):
    width_factor: float = Field(gt=1)
    alpha: float = Field(gt=0, le=1)


def apply_sketch(
    artist: Artist,
    sketch_config: SketchConfig | None,
) -> None:
    if sketch_config is not None:
        artist.set_sketch_params(
            sketch_config.scale, sketch_config.length, sketch_config.randomness
        )


def draw_arrows_for_curve(
    axes: Axes,
    curve: tuple[Point, ...],
    color: str,
    count: int,
    mutation_scale: float,
    arrow_config: ArrowConfig,
    sketch_config: SketchConfig | None,
) -> None:
    for index in range(count):
        start, end = arrow_config.spread_start, arrow_config.spread_end
        fraction = (start + end) / 2 if count == 1 else start + index * (end - start) / (count - 1)
        span = arrow_config.tangent_span
        previous = point_at_fraction(curve, max(0.0, fraction - span))
        point = point_at_fraction(curve, min(1.0, fraction + span))
        arrow = FancyArrowPatch(
            previous,
            point,
            arrowstyle="-|>",
            mutation_scale=mutation_scale,
            color=color,
            linewidth=0,
            shrinkA=0,
            shrinkB=0,
            zorder=7,
        )
        apply_sketch(arrow, sketch_config)
        axes.add_patch(arrow)


def plot_stroke(
    axes: Axes,
    x_values: tuple[float, ...] | list[float],
    y_values: tuple[float, ...] | list[float],
    color: str,
    width: float,
    line_style: str | tuple[int, tuple[float, ...]],
    zorder: int,
    glow_config: tuple[GlowLayerConfig, ...],
    sketch_config: SketchConfig | None,
) -> None:
    for glow in glow_config:
        axes.plot(
            x_values,
            y_values,
            color=color,
            linewidth=width * glow.width_factor,
            linestyle=line_style,
            alpha=glow.alpha,
            solid_capstyle="round",
            dash_capstyle="round",
            zorder=zorder - 0.2,
        )
    (line,) = axes.plot(
        x_values,
        y_values,
        color=color,
        linewidth=width,
        linestyle=line_style,
        solid_capstyle="round",
        dash_capstyle="round",
        zorder=zorder,
    )
    apply_sketch(line, sketch_config)
