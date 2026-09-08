"""Validated, layered YAML configuration for surface diagrams."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml

type ConfigMap = dict[str, object]


@dataclass(frozen=True, slots=True)
class CanvasConfig:
    max_columns: int
    cell_width: float
    cell_height: float
    margin_x: float
    margin_y: float

    def __post_init__(self) -> None:
        if (
            self.max_columns < 1
            or min(self.cell_width, self.cell_height, self.margin_x, self.margin_y) <= 0
        ):
            raise ValueError("rendering.canvas values must be positive")


@dataclass(frozen=True, slots=True)
class CurvatureConfig:
    edge_base: float
    edge_step: float
    interior_step: float

    def __post_init__(self) -> None:
        if min(self.edge_base, self.edge_step, self.interior_step) < 0:
            raise ValueError("rendering.geometry.curvature values must be nonnegative")


@dataclass(frozen=True, slots=True)
class GeometryConfig:
    side_length: float
    curve_samples: int
    curvature: CurvatureConfig

    def __post_init__(self) -> None:
        if self.side_length <= 0 or self.curve_samples < 8:
            raise ValueError("rendering.geometry needs positive size and at least 8 samples")


@dataclass(frozen=True, slots=True)
class StrokeConfig:
    polygon_width: float
    path_width: float
    vertex_size: float
    dotted_pattern: tuple[float, ...]

    def __post_init__(self) -> None:
        if min(self.polygon_width, self.path_width, self.vertex_size) <= 0:
            raise ValueError("rendering.stroke values must be positive")
        if self.path_width > self.polygon_width:
            raise ValueError("rendering.stroke.path_width must not exceed polygon_width")
        if not self.dotted_pattern or min(self.dotted_pattern) <= 0:
            raise ValueError("rendering.stroke.dotted_pattern values must be positive")


@dataclass(frozen=True, slots=True)
class ArrowConfig:
    gluing_size: float
    path_size: float
    path_count_limit: int
    spread_start: float
    spread_end: float
    tangent_span: float

    def __post_init__(self) -> None:
        if min(self.gluing_size, self.path_size, self.tangent_span) <= 0:
            raise ValueError("rendering.arrows sizes must be positive")
        if self.path_count_limit < 1:
            raise ValueError("rendering.arrows.path_count_limit must be positive")
        if not 0 <= self.spread_start <= self.spread_end <= 1:
            raise ValueError("rendering.arrows spread must lie between zero and one")


@dataclass(frozen=True, slots=True)
class LabelConfig:
    polygon_size: float
    gluing_size: float
    path_size: float
    order_size: float
    tag_offset: float
    tag_clearance: float
    gluing_offset: float
    path_offset: float

    def __post_init__(self) -> None:
        if (
            min(
                self.polygon_size,
                self.gluing_size,
                self.path_size,
                self.order_size,
                self.tag_offset,
                self.tag_clearance,
                self.gluing_offset,
                self.path_offset,
            )
            <= 0
        ):
            raise ValueError("rendering.labels values must be positive")


@dataclass(frozen=True, slots=True)
class PaletteConfig:
    fill: str
    ink: str
    path_colors: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.fill or not self.ink or not self.path_colors:
            raise ValueError("each rendering palette needs fill, ink, and path colors")


@dataclass(frozen=True, slots=True)
class SurfaceRenderingConfig:
    canvas: CanvasConfig
    geometry: GeometryConfig
    stroke: StrokeConfig
    arrows: ArrowConfig
    labels: LabelConfig
    palettes: tuple[PaletteConfig, ...]

    def __post_init__(self) -> None:
        if not self.palettes:
            raise ValueError("rendering.palettes must not be empty")


def load_rendering_config(override_path: str | Path | None = None) -> SurfaceRenderingConfig:
    """Load defaults and recursively overlay an optional user YAML file."""
    default_path = Path(__file__).parent.parent / "rendering.yaml"
    merged = _read_yaml(default_path)
    if override_path is not None:
        merged = _deep_merge(merged, _read_yaml(Path(override_path)))
    root = _section(merged, "rendering")
    canvas = _section(root, "canvas")
    geometry = _section(root, "geometry")
    curvature = _section(geometry, "curvature")
    stroke = _section(root, "stroke")
    arrows = _section(root, "arrows")
    labels = _section(root, "labels")
    palettes = _list(root, "palettes")
    return SurfaceRenderingConfig(
        CanvasConfig(
            _integer(canvas, "max_columns"),
            _number(canvas, "cell_width"),
            _number(canvas, "cell_height"),
            _number(canvas, "margin_x"),
            _number(canvas, "margin_y"),
        ),
        GeometryConfig(
            _number(geometry, "side_length"),
            _integer(geometry, "curve_samples"),
            CurvatureConfig(
                _number(curvature, "edge_base"),
                _number(curvature, "edge_step"),
                _number(curvature, "interior_step"),
            ),
        ),
        StrokeConfig(
            _number(stroke, "polygon_width"),
            _number(stroke, "path_width"),
            _number(stroke, "vertex_size"),
            tuple(
                _number_value(value, "rendering.stroke.dotted_pattern")
                for value in _list(stroke, "dotted_pattern")
            ),
        ),
        ArrowConfig(
            _number(arrows, "gluing_size"),
            _number(arrows, "path_size"),
            _integer(arrows, "path_count_limit"),
            _number(arrows, "spread_start"),
            _number(arrows, "spread_end"),
            _number(arrows, "tangent_span"),
        ),
        LabelConfig(
            _number(labels, "polygon_size"),
            _number(labels, "gluing_size"),
            _number(labels, "path_size"),
            _number(labels, "order_size"),
            _number(labels, "tag_offset"),
            _number(labels, "tag_clearance"),
            _number(labels, "gluing_offset"),
            _number(labels, "path_offset"),
        ),
        tuple(
            PaletteConfig(
                _string(item, "fill"),
                _string(item, "ink"),
                tuple(
                    _string_value(color, "rendering.palettes.path_colors")
                    for color in _list(item, "path_colors")
                ),
            )
            for value in palettes
            for item in (_mapping(value, "rendering.palettes[]"),)
        ),
    )


def _read_yaml(path: Path) -> ConfigMap:
    with path.open(encoding="utf-8") as stream:
        value = cast(object, yaml.safe_load(stream))
    return _mapping(value, str(path))


def _deep_merge(base: ConfigMap, override: ConfigMap) -> ConfigMap:
    result = dict(base)
    for key, value in override.items():
        current = result.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            result[key] = _deep_merge(dict(current), dict(value))
        else:
            result[key] = value
    return result


def _mapping(value: object, name: str) -> ConfigMap:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{name} must be a YAML mapping")
    return cast(ConfigMap, value)


def _section(mapping: ConfigMap, key: str) -> ConfigMap:
    if key not in mapping:
        raise ValueError(f"missing rendering configuration section: {key}")
    return _mapping(mapping[key], key)


def _list(mapping: ConfigMap, key: str) -> list[object]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a YAML list")
    return cast(list[object], value)


def _number(mapping: ConfigMap, key: str) -> float:
    return _number_value(mapping.get(key), key)


def _number_value(value: object, key: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{key} must be a number")
    return float(value)


def _integer(mapping: ConfigMap, key: str) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _string(mapping: ConfigMap, key: str) -> str:
    return _string_value(mapping.get(key), key)


def _string_value(value: object, key: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a nonempty string")
    return value
