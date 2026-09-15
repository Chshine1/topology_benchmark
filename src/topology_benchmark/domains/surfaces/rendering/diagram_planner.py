from topology_benchmark.utils.planer_vector import unit
from topology_benchmark.utils.planer_vector import quadratic
from topology_benchmark.utils.planer_vector import Point
import itertools
import math
from dataclasses import dataclass
from enum import Enum
from random import Random
from typing import Iterable

from topology_benchmark.domains.surfaces.models import (
    EdgeRef,
    OrientedEdge,
    SurfacePath,
    SurfacePresentation,
)
from topology_benchmark.domains.surfaces.models.utils.surface_representation import edges_connected
from topology_benchmark.domains.surfaces.rendering.config import CanvasConfig
from topology_benchmark.domains.surfaces.rendering.config import SurfaceRenderingConfig
from topology_benchmark.domains.surfaces.rendering.visual_style import (
    SelectedVisualStyle,
    SurfaceVisualStyleSelector,
)


class LinePattern(Enum):
    SOLID = "solid"
    DOTTED = "dotted"


class OrderDisplay(Enum):
    NUMBER_TAG = "number-tag"
    ARROW_COUNT = "arrow-count"


@dataclass(frozen=True, slots=True)
class DiagramStyle:
    visual: SelectedVisualStyle
    boundary_pattern: LinePattern


@dataclass(frozen=True, slots=True)
class PathStyle:
    color: str
    order_display: OrderDisplay


@dataclass(frozen=True, slots=True)
class PolygonLayout:
    center: Point
    vertices: tuple[Point, ...]
    path_segment_groups: tuple[StyledSegmentsGroup, ...]

    def edge(self, index: int) -> tuple[Point, Point]:
        return self.vertices[index], self.vertices[(index + 1) % len(self.vertices)]


@dataclass(frozen=True, slots=True)
class PathSegmentGeometry:
    points: tuple[Point, ...]
    curvature: float
    tag_position: Point | None = None
    name_position: Point | None = None


@dataclass(frozen=True, slots=True)
class PathSegment:
    path_index: int
    polygon: int
    edges: tuple[OrientedEdge, ...]
    order: int
    geometry: PathSegmentGeometry


@dataclass(frozen=True, slots=True)
class StyledSegmentsGroup:
    segments: tuple[PathSegment, ...]
    style: PathStyle


@dataclass(frozen=True, slots=True)
class DiagramPlan:
    width: int
    height: int
    polygons: tuple[PolygonLayout, ...]
    style: DiagramStyle


@dataclass(frozen=True, slots=True)
class _RawPathSegment:
    path_index: int
    polygon: int
    edges: tuple[OrientedEdge, ...]
    order: int


type _RawSegmentsGroup = tuple[_RawPathSegment, ...]


class SurfaceDiagramPlanner:
    def __init__(
        self,
        config: SurfaceRenderingConfig,
        style_selector: SurfaceVisualStyleSelector,
    ) -> None:
        self._config = config
        self._style_selector = style_selector

    def plan(self, surface: SurfacePresentation, rng: Random) -> DiagramPlan:
        canvas_config = self._config.canvas
        columns = min(canvas_config.max_columns, len(surface.polygons))
        rows = math.ceil(len(surface.polygons) / columns)
        width = round(2 * canvas_config.margin_x + columns * canvas_config.cell_width)
        height = round(2 * canvas_config.margin_y + rows * canvas_config.cell_height)
        selected_style = self._style_selector.select(rng)
        layouts = self._get_polygon_layouts(canvas_config, selected_style, columns, surface, rng)
        return DiagramPlan(width, height, layouts, DiagramStyle(selected_style, LinePattern.SOLID))

    @staticmethod
    def edge_pattern(
        surface: SurfacePresentation, edge: EdgeRef, boundary_pattern: LinePattern
    ) -> LinePattern:
        for gluing in surface.gluings:
            if edge == gluing.first:
                return (
                    LinePattern.DOTTED
                    if gluing.second.polygon != edge.polygon
                    else LinePattern.SOLID
                )
            if edge == gluing.second:
                return (
                    LinePattern.DOTTED
                    if gluing.first.polygon != edge.polygon
                    else LinePattern.SOLID
                )
        return boundary_pattern

    @staticmethod
    def _generate_styled_paths(
        selected_style: SelectedVisualStyle, paths: tuple[SurfacePath, ...], rng: Random
    ) -> Iterable[tuple[SurfacePath, PathStyle]]:
        limit = selected_style.profile.arrows.path_count_limit

        return (
            (
                path,
                PathStyle(
                    color=rng.choice(selected_style.palette.path_colors),
                    order_display=OrderDisplay.NUMBER_TAG
                    if len(path.edges) > limit
                    else rng.choice((OrderDisplay.NUMBER_TAG, OrderDisplay.ARROW_COUNT)),
                ),
            )
            for path in paths
        )

    @staticmethod
    def _collect_segments_by_polygon(
        surface: SurfacePresentation, styled_paths: Iterable[tuple[SurfacePath, PathStyle]]
    ) -> dict[int, list[tuple[_RawSegmentsGroup, PathStyle]]]:
        result: dict[int, list[tuple[_RawSegmentsGroup, PathStyle]]] = {}

        for path, style in styled_paths:
            edges_tuple = tuple(path.edges)
            segment_index = 0

            for polygon, group in itertools.groupby(edges_tuple, key=lambda e: e.edge.polygon):
                edges_in_polygon = tuple(group)
                segments: list[_RawPathSegment] = []
                edges_in_segment = [edges_in_polygon[0]]

                for edge_index in range(len(edges_in_polygon) - 1):
                    if edges_connected(
                        surface.polygons[polygon].sides,
                        edges_in_polygon[edge_index],
                        edges_in_polygon[edge_index + 1],
                    ):
                        edges_in_segment.append(edges_in_polygon[edge_index + 1])
                        continue
                    segments.append(_RawPathSegment(-1, -1, tuple(edges_in_segment), segment_index))
                    segment_index += 1
                    edges_in_segment = [edges_in_polygon[edge_index + 1]]

                segments.append(_RawPathSegment(-1, -1, tuple(edges_in_segment), segment_index))
                segment_index += 1

                result.setdefault(polygon, []).append((tuple(segments), style))

        return result

    def _compute_geometry_for_segments(
        self,
        center_vec: Point,
        vertices_vec: tuple[Point, ...],
        segments_in_polygon: Iterable[_RawPathSegment],
    ) -> dict[_RawPathSegment, PathSegmentGeometry]:
        polygon_sides = len(vertices_vec)

        def key_selector(segment: _RawPathSegment) -> tuple[int, int]:
            return segment.edges[0].edge.edge, (
                segment.edges[-1].edge.edge + (1 if segment.edges[-1].forward else -1)
            ) % polygon_sides

        ordered = sorted(
            (segment for segment in segments_in_polygon),
            key=key_selector,
        )
        result: dict[_RawPathSegment, PathSegmentGeometry] = {}

        for endpoints, segments_group in itertools.groupby(ordered, key_selector):
            tuple_group = tuple(segments_group)

            endpoints_diff = (endpoints[1] - endpoints[0]) % polygon_sides
            lies_on_edge = endpoints_diff == 1 or endpoints_diff == polygon_sides - 1
            start_vec, end_vec = sorted((vertices_vec[endpoints[0]], vertices_vec[endpoints[1]]))
            midpoint_vec = ((start_vec[0] + end_vec[0]) / 2, (start_vec[1] + end_vec[1]) / 2)

            direction: tuple[float, float]
            curvature_base_offset: float
            curvature_step: float

            if lies_on_edge:
                direction = unit(midpoint_vec[0] - center_vec[0], midpoint_vec[1] - center_vec[1])
                curvature_base_offset = self._config.geometry.curvature.edge_base
                curvature_step = self._config.geometry.curvature.edge_step
            else:
                direction = unit(
                    -(end_vec[1] - start_vec[1]),
                    end_vec[0] - start_vec[0],
                )
                curvature_base_offset = (
                    -(len(tuple_group) - 1) * self._config.geometry.curvature.interior_step / 2
                )
                curvature_step = self._config.geometry.curvature.interior_step

            for i, segment in enumerate(tuple_group):
                curvature = curvature_base_offset + curvature_step * i
                control = (
                    midpoint_vec[0] + direction[0] * curvature,
                    midpoint_vec[1] + direction[1] * curvature,
                )
                samples = self._config.geometry.curve_samples
                points = tuple(
                    quadratic(start_vec, control, end_vec, step / samples)
                    for step in range(samples + 1)
                )
                result[segment] = PathSegmentGeometry(points, curvature)

        return result

    def _get_polygon_layouts(
        self,
        canvas_config: CanvasConfig,
        selected_style: SelectedVisualStyle,
        columns: int,
        surface: SurfacePresentation,
        rng: Random,
    ) -> tuple[PolygonLayout, ...]:
        layouts: list[PolygonLayout] = []
        styled_paths = self._generate_styled_paths(selected_style, surface.paths, rng)
        polygon_segment_groups = self._collect_segments_by_polygon(surface, styled_paths)

        for index, polygon in enumerate(surface.polygons):
            sides = polygon.sides
            radius = self._config.geometry.side_length / (2 * math.sin(math.pi / sides))
            center_vec = (
                canvas_config.margin_x + (index % columns + 0.5) * canvas_config.cell_width,
                canvas_config.margin_y + (index // columns + 0.5) * canvas_config.cell_height,
            )
            phase = rng.uniform(-math.pi, math.pi)
            vertices_vec = tuple(
                (
                    center_vec[0] + radius * math.cos(phase + 2 * math.pi * side / sides),
                    center_vec[1] + radius * math.sin(phase + 2 * math.pi * side / sides),
                )
                for side in range(sides)
            )
            styled_groups_in_polygon = polygon_segment_groups[index]
            geometry_of_segments = self._compute_geometry_for_segments(
                center_vec,
                vertices_vec,
                (segment for group, _ in styled_groups_in_polygon for segment in group),
            )

            layouts.append(
                PolygonLayout(
                    center_vec,
                    vertices_vec,
                    tuple(
                        StyledSegmentsGroup(
                            tuple(
                                PathSegment(
                                    path_index=s.path_index,
                                    polygon=s.polygon,
                                    edges=s.edges,
                                    order=s.order,
                                    geometry=geometry_of_segments[s],
                                )
                                for s in raw_segments
                            ),
                            style,
                        )
                        for raw_segments, style in styled_groups_in_polygon
                    ),
                )
            )

        return tuple(layouts)
