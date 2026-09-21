import itertools
import math
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from random import Random

from topology_benchmark.domains.surfaces.models import (
    EdgeRef,
    OrientedEdge,
    SurfacePresentation,
)
from topology_benchmark.domains.surfaces.rendering.config import (
    CanvasConfig,
    PaletteConfig,
    SurfaceRenderingConfig,
    SurfaceVisualStyleConfig,
)
from topology_benchmark.domains.surfaces.services import SurfaceAnalyzer
from topology_benchmark.utils.planer_vector import Point, quadratic, unit


class LineStyle(Enum):
    SOLID = "solid"
    DOTTED = "dotted"


class OrderDisplay(Enum):
    NUMBER_TAG = "number-tag"
    ARROW_COUNT = "arrow-count"


@dataclass(frozen=True, slots=True)
class DiagramStyle:
    visual: SurfaceVisualStyleConfig
    palette: PaletteConfig


@dataclass(frozen=True, slots=True)
class PathStyle:
    color: str
    order_display: OrderDisplay


@dataclass(frozen=True, slots=True)
class EdgeView:
    line_style_override: LineStyle
    label: str
    preserve_orientation: bool


@dataclass(frozen=True, slots=True)
class PolygonView:
    label: str
    center: Point
    vertices: tuple[Point, ...]
    edge_views: dict[int, EdgeView]
    homology_basis: dict[int, str]
    path_segment_groups: tuple[StyledSegmentsGroup, ...]

    def edge(self, index: int) -> tuple[Point, Point]:
        return self.vertices[index], self.vertices[(index + 1) % len(self.vertices)]


@dataclass(frozen=True, slots=True)
class PathSegmentGeometry:
    points: tuple[Point, ...]
    curvature: float


@dataclass(frozen=True, slots=True)
class PathSegment:
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
    polygon_views: tuple[PolygonView, ...]
    style: DiagramStyle


@dataclass(frozen=True, slots=True)
class _RawPathSegment:
    edges: tuple[OrientedEdge, ...]
    order: int


type _RawSegmentsGroup = tuple[_RawPathSegment, ...]


class SurfaceDiagramPlanner:
    def __init__(
        self,
        config: SurfaceRenderingConfig,
        analyzer: SurfaceAnalyzer,
    ) -> None:
        self._config = config
        self._analyzer = analyzer

    def plan(self, surface: SurfacePresentation, rng: Random) -> DiagramPlan:
        canvas_config = self._config.canvas

        columns = min(canvas_config.max_columns, len(surface.polygons))
        rows = math.ceil(len(surface.polygons) / columns)
        width = round(2 * canvas_config.margin_x + columns * canvas_config.cell_width)
        height = round(2 * canvas_config.margin_y + rows * canvas_config.cell_height)

        visual_style = self._config.styles.sample(rng)

        diagram_style = DiagramStyle(visual_style, visual_style.palettes.sample(rng))
        layouts = self._get_polygon_views(canvas_config, diagram_style, columns, surface, rng)
        return DiagramPlan(
            width,
            height,
            layouts,
            diagram_style,
        )

    @staticmethod
    def edge_pattern(
        surface: SurfacePresentation, edge: EdgeRef, boundary_pattern: LineStyle
    ) -> LineStyle:
        for gluing in surface.gluings:
            if edge == gluing.first_edge:
                return (
                    LineStyle.DOTTED
                    if gluing.second_edge.polygon_index != edge.polygon_index
                    else LineStyle.SOLID
                )
            if edge == gluing.second_edge:
                return (
                    LineStyle.DOTTED
                    if gluing.first_edge.polygon_index != edge.polygon_index
                    else LineStyle.SOLID
                )
        return boundary_pattern

    @staticmethod
    def _generate_styled_paths(
        style: DiagramStyle, paths: tuple[tuple[OrientedEdge, ...], ...], rng: Random
    ) -> Iterable[tuple[tuple[OrientedEdge, ...], PathStyle]]:
        limit = style.visual.arrows.path_count_limit

        return (
            (
                path,
                PathStyle(
                    color=rng.choice(style.palette.path_colors),
                    order_display=OrderDisplay.NUMBER_TAG
                    if len(path) > limit
                    else rng.choice((OrderDisplay.NUMBER_TAG, OrderDisplay.ARROW_COUNT)),
                ),
            )
            for path in paths
        )

    @staticmethod
    def _collect_segments_by_polygon(
        surface: SurfacePresentation,
        styled_paths: Iterable[tuple[tuple[OrientedEdge, ...], PathStyle]],
    ) -> dict[int, list[tuple[_RawSegmentsGroup, PathStyle]]]:
        result: dict[int, list[tuple[_RawSegmentsGroup, PathStyle]]] = {}

        for path, style in styled_paths:
            segment_index = 0

            for polygon, group in itertools.groupby(path, key=lambda e: e.edge.polygon):
                edges_in_polygon = tuple(group)
                segments: list[_RawPathSegment] = []
                edges_in_segment = [edges_in_polygon[0]]

                for edge_index in range(len(edges_in_polygon) - 1):
                    first_edge = edges_in_polygon[edge_index]
                    if (
                        first_edge.edge.starting_vertex + (1 if first_edge.forward else -1)
                    ) % surface.polygons[polygon].sides == edges_in_polygon[
                        edge_index + 1
                    ].edge.starting_vertex:
                        edges_in_segment.append(edges_in_polygon[edge_index + 1])
                        continue
                    segments.append(_RawPathSegment(tuple(edges_in_segment), segment_index))
                    segment_index += 1
                    edges_in_segment = [edges_in_polygon[edge_index + 1]]

                segments.append(_RawPathSegment(tuple(edges_in_segment), segment_index))
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
            return segment.edges[0].edge.starting_vertex, (
                segment.edges[-1].edge.starting_vertex + (1 if segment.edges[-1].forward else -1)
            ) % polygon_sides

        ordered = sorted(
            (segment for segment in segments_in_polygon),
            key=key_selector,
        )
        if len(ordered) == 0:
            return {}

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

    def _get_polygon_views(
        self,
        canvas_config: CanvasConfig,
        style: DiagramStyle,
        columns: int,
        surface: SurfacePresentation,
        rng: Random,
    ) -> tuple[PolygonView, ...]:
        views: list[PolygonView] = []
        styled_paths = self._generate_styled_paths(style, surface.paths, rng)
        polygon_segment_groups = self._collect_segments_by_polygon(surface, styled_paths)

        polygon_edges: dict[int, dict[int, EdgeView]] = {}

        for index, gluing in enumerate(surface.gluings):
            label = chr(ord("a") + index) if index < 26 else f"g{index - 25}"
            first_orientation = rng.choice([True, False])
            second_orientation = first_orientation == gluing.same_direction

            edge_line_style = (
                LineStyle.SOLID
                if gluing.first_edge.polygon_index == gluing.second_edge.polygon_index
                else LineStyle.DOTTED
            )
            polygon_edges.setdefault(gluing.first_edge.polygon_index, {})[
                gluing.second_edge.polygon_index
            ] = EdgeView(edge_line_style, label, first_orientation)
            polygon_edges.setdefault(gluing.first_edge.polygon_index, {})[
                gluing.second_edge.polygon_index
            ] = EdgeView(edge_line_style, label, second_orientation)

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
            styled_groups_in_polygon = polygon_segment_groups.get(index, [])
            geometry_of_segments = self._compute_geometry_for_segments(
                center_vec,
                vertices_vec,
                (segment for group, _ in styled_groups_in_polygon for segment in group),
            )

            used = {
                edge
                for coefficients, _ in self._analyzer.h1_edge_generators(surface)
                for edge, coefficient in enumerate(coefficients)
                if coefficient
            }
            basis = self._analyzer.cellular_homology(surface).h1_basis
            tuple((basis[edge], f"e{tag}") for tag, edge in enumerate(sorted(used), start=1))

            views.append(
                PolygonView(
                    label=chr(ord("P") + index),
                    center=center_vec,
                    vertices=vertices_vec,
                    edge_views=polygon_edges.get(index, {}),
                    homology_basis={},  # TODO
                    path_segment_groups=tuple(
                        StyledSegmentsGroup(
                            tuple(
                                PathSegment(
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

        return tuple(views)
