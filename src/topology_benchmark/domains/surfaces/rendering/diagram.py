import math
from dataclasses import dataclass
from enum import Enum
from random import Random

from attrs import field, frozen

from topology_benchmark.core.validation import nonempty, number_range
from topology_benchmark.domains.surfaces.models import (
    EdgeRef,
    OrientedEdge,
    SurfacePath,
    SurfacePresentation,
)
from topology_benchmark.domains.surfaces.rendering.config import (
    SurfaceRenderingConfig,
)

type Point = tuple[float, float]


class LinePattern(Enum):
    SOLID = "solid"
    DOTTED = "dotted"


class OrderDisplay(Enum):
    NUMBER_TAG = "number-tag"
    ARROW_COUNT = "arrow-count"


@frozen
class Palette:
    fill: str
    ink: str
    path_colors: tuple[str, ...] = field(
        validator=nonempty("a palette needs at least one path color")
    )


@frozen
class DiagramStyle:
    palette: Palette
    boundary_pattern: LinePattern
    polygon_width: float = 2.6
    path_width: float = field(
        default=2.2,
        validator=number_range(
            minimum=1.0,
            message="line widths must be positive",
        ),
    )

    def __attrs_post_init__(self) -> None:
        if self.path_width > self.polygon_width:
            raise ValueError("paths must be no wider than polygon edges")


@dataclass(frozen=True, slots=True)
class PathStyle:
    color: str
    order_display: OrderDisplay


@dataclass(frozen=True, slots=True)
class PolygonLayout:
    center: Point
    vertices: tuple[Point, ...]

    def edge(self, index: int) -> tuple[Point, Point]:
        return self.vertices[index], self.vertices[(index + 1) % len(self.vertices)]

    @property
    def side_length(self) -> float:
        return math.dist(*self.edge(0))


@dataclass(frozen=True, slots=True)
class PathSegment:
    path_index: int
    polygon: int
    edges: tuple[OrientedEdge, ...]
    order: int

    @property
    def lies_on_edge(self) -> bool:
        return len(self.edges) == 1


@dataclass(frozen=True, slots=True)
class PathCurve:
    segment: PathSegment
    style: PathStyle
    points: tuple[Point, ...]
    curvature: float
    tag_position: Point | None = None
    name_position: Point | None = None


@dataclass(frozen=True, slots=True)
class DiagramPlan:
    width: int
    height: int
    polygons: tuple[PolygonLayout, ...]
    curves: tuple[PathCurve, ...]
    style: DiagramStyle


@dataclass(frozen=True, slots=True)
class _StackKey:
    polygon: int
    first_vertex: int
    second_vertex: int
    lies_on_edge: bool


class SurfaceDiagramPlanner:
    def __init__(self, config: SurfaceRenderingConfig) -> None:
        self.config = config

    def plan(self, surface: SurfacePresentation, rng: Random) -> DiagramPlan:
        canvas = self.config.canvas
        columns = min(canvas.max_columns, len(surface.polygons))
        rows = math.ceil(len(surface.polygons) / columns)
        width = round(2 * canvas.margin_x + columns * canvas.cell_width)
        height = round(2 * canvas.margin_y + rows * canvas.cell_height)
        layouts = tuple(
            self._regular_polygon(
                (
                    canvas.margin_x + (index % columns + 0.5) * canvas.cell_width,
                    canvas.margin_y + (index // columns + 0.5) * canvas.cell_height,
                ),
                polygon.sides,
                rng.uniform(-math.pi, math.pi),
            )
            for index, polygon in enumerate(surface.polygons)
        )
        configured_palette = rng.choice(self.config.palettes)
        style = DiagramStyle(
            Palette(
                configured_palette.fill,
                configured_palette.ink,
                configured_palette.path_colors,
            ),
            LinePattern.SOLID,
            self.config.stroke.polygon_width,
            self.config.stroke.path_width,
        )
        raw_segments = tuple(
            segment
            for path_index, path in enumerate(surface.paths)
            for segment in self._segments(surface, path, path_index, rng)
        )
        segments = self._drawable_segments(layouts, raw_segments)
        path_styles = self._path_styles(len(surface.paths), segments, style.palette, rng)
        curves = self._place_labels(layouts, self._curves(layouts, segments, path_styles))
        return DiagramPlan(width, height, layouts, curves, style)

    @classmethod
    def _drawable_segments(
        cls,
        layouts: tuple[PolygonLayout, ...],
        segments: tuple[PathSegment, ...],
    ) -> tuple[PathSegment, ...]:
        """Split polygon-local loops so they are drawn along their actual boundary edges."""
        result: list[PathSegment] = []
        orders: dict[int, int] = {}
        for segment in segments:
            sides = len(layouts[segment.polygon].vertices)
            closed_in_face = len(set(cls._endpoint_indices(segment, sides))) == 1
            edge_groups = (
                ((edge,) for edge in segment.edges) if closed_in_face else (segment.edges,)
            )
            for edges in edge_groups:
                order = orders.get(segment.path_index, 0) + 1
                orders[segment.path_index] = order
                result.append(PathSegment(segment.path_index, segment.polygon, edges, order))
        return tuple(result)

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

    def _regular_polygon(self, center: Point, sides: int, phase: float) -> PolygonLayout:
        radius = self.config.geometry.side_length / (2 * math.sin(math.pi / sides))
        vertices = tuple(
            (
                center[0] + radius * math.cos(phase + 2 * math.pi * side / sides),
                center[1] + radius * math.sin(phase + 2 * math.pi * side / sides),
            )
            for side in range(sides)
        )
        return PolygonLayout(center, vertices)

    def _path_styles(
        self,
        count: int,
        segments: tuple[PathSegment, ...],
        palette: Palette,
        rng: Random,
    ) -> tuple[PathStyle, ...]:
        first_display = rng.choice(tuple(OrderDisplay))
        displays = (first_display, next(item for item in OrderDisplay if item != first_display))
        color_offset = rng.randrange(len(palette.path_colors))
        segment_counts = tuple(
            sum(segment.path_index == path_index for segment in segments)
            for path_index in range(count)
        )
        selected = [
            displays[index % len(displays)]
            if segment_counts[index] <= self.config.arrows.path_count_limit
            else OrderDisplay.NUMBER_TAG
            for index in range(count)
        ]
        eligible = [
            index
            for index, segment_count in enumerate(segment_counts)
            if segment_count <= self.config.arrows.path_count_limit
        ]
        if eligible and OrderDisplay.ARROW_COUNT not in selected:
            selected[min(eligible, key=segment_counts.__getitem__)] = OrderDisplay.ARROW_COUNT
        return tuple(
            PathStyle(
                palette.path_colors[(color_offset + index) % len(palette.path_colors)],
                selected[index],
            )
            for index in range(count)
        )

    def _curves(
        self,
        layouts: tuple[PolygonLayout, ...],
        segments: tuple[PathSegment, ...],
        styles: tuple[PathStyle, ...],
    ) -> tuple[PathCurve, ...]:
        groups: dict[_StackKey, list[PathSegment]] = {}
        for segment in segments:
            key = self._stack_key(segment, len(layouts[segment.polygon].vertices))
            groups.setdefault(key, []).append(segment)

        lane: dict[PathSegment, tuple[int, int]] = {}
        for stacked in groups.values():
            for rank, segment in enumerate(stacked):
                lane[segment] = rank, len(stacked)

        curves = []
        for segment in segments:
            layout = layouts[segment.polygon]
            start_index, end_index = self._endpoint_indices(segment, len(layout.vertices))
            start, end = layout.vertices[start_index], layout.vertices[end_index]
            midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
            rank, count = lane[segment]
            if segment.lies_on_edge:
                direction = self._unit(
                    midpoint[0] - layout.center[0], midpoint[1] - layout.center[1]
                )
                curvature = (
                    self.config.geometry.curvature.edge_base
                    + self.config.geometry.curvature.edge_step * rank
                )
            else:
                canonical_start, canonical_end = sorted((start, end))
                direction = self._unit(
                    -(canonical_end[1] - canonical_start[1]),
                    canonical_end[0] - canonical_start[0],
                )
                curvature = (rank - (count - 1) / 2) * self.config.geometry.curvature.interior_step
            control = (
                midpoint[0] + direction[0] * curvature,
                midpoint[1] + direction[1] * curvature,
            )
            samples = self.config.geometry.curve_samples
            points = tuple(
                self._quadratic(start, control, end, step / samples) for step in range(samples + 1)
            )
            curves.append(PathCurve(segment, styles[segment.path_index], points, curvature))
        return tuple(curves)

    def _place_labels(
        self,
        layouts: tuple[PolygonLayout, ...],
        curves: tuple[PathCurve, ...],
    ) -> tuple[PathCurve, ...]:
        fixed_obstacles = [layout.center for layout in layouts]
        fixed_obstacles.extend(point for layout in layouts for point in layout.vertices)
        fixed_obstacles.extend(
            (
                (start[0] + end[0]) / 2,
                (start[1] + end[1]) / 2,
            )
            for layout in layouts
            for start, end in (layout.edge(edge) for edge in range(len(layout.vertices)))
        )
        placed: list[Point] = []
        result = []
        for curve in curves:
            obstacles = [
                *fixed_obstacles,
                *(point for other in curves if other is not curve for point in other.points[::12]),
                *placed,
            ]
            tag_position = (
                self._choose_label_position(curve, self.config.labels.tag_offset, obstacles)
                if curve.style.order_display is OrderDisplay.NUMBER_TAG
                else None
            )
            if tag_position is not None:
                placed.append(tag_position)
                obstacles.append(tag_position)
            name_position = (
                self._choose_label_position(curve, self.config.labels.path_offset, obstacles)
                if curve.segment.order == 1
                else None
            )
            if name_position is not None:
                placed.append(name_position)
            result.append(
                PathCurve(
                    curve.segment,
                    curve.style,
                    curve.points,
                    curve.curvature,
                    tag_position,
                    name_position,
                )
            )
        return tuple(result)

    def _choose_label_position(
        self, curve: PathCurve, offset: float, obstacles: list[Point]
    ) -> Point:
        candidates = self._label_candidates(curve, offset)
        scored = tuple(
            (
                min(math.dist(candidate, obstacle) for obstacle in obstacles),
                candidate,
            )
            for candidate in candidates
        )
        clear = tuple(
            candidate
            for distance, candidate in scored
            if distance >= self.config.labels.tag_clearance
        )
        return clear[0] if clear else max(scored)[1]

    def _label_candidates(self, curve: PathCurve, offset: float) -> tuple[Point, ...]:
        result = []
        for fraction in (0.5, 0.35, 0.65, 0.22, 0.78):
            index = max(
                1,
                min(len(curve.points) - 2, round(fraction * (len(curve.points) - 1))),
            )
            previous, point, following = curve.points[index - 1 : index + 2]
            tangent = self._unit(following[0] - previous[0], following[1] - previous[1])
            normal = (-tangent[1], tangent[0])
            result.extend(
                (
                    point[0] + sign * offset * normal[0],
                    point[1] + sign * offset * normal[1],
                )
                for sign in (-1, 1)
            )
        return tuple(result)

    @classmethod
    def _stack_key(cls, segment: PathSegment, sides: int) -> _StackKey:
        start, end = cls._endpoint_indices(segment, sides)
        first, second = sorted((start, end))
        return _StackKey(segment.polygon, first, second, segment.lies_on_edge)

    @staticmethod
    def _endpoint_indices(segment: PathSegment, sides: int) -> tuple[int, int]:
        first, last = segment.edges[0], segment.edges[-1]
        start = first.edge.edge if first.forward else (first.edge.edge + 1) % sides
        end = (last.edge.edge + 1) % sides if last.forward else last.edge.edge
        return start, end

    def _segments(
        self,
        surface: SurfacePresentation,
        path: SurfacePath,
        path_index: int,
        rng: Random,
    ) -> tuple[PathSegment, ...]:
        choices = [self._representatives(surface, edge) for edge in path.edges]
        states: list[list[tuple[int, int | None]]] = [
            [(0, None) for _ in options] for options in choices
        ]
        for index in range(1, len(choices)):
            for current_index, current in enumerate(choices[index]):
                scored = [
                    (
                        states[index - 1][previous_index][0]
                        + int(self._native_connected(surface, previous, current)),
                        previous_index,
                    )
                    for previous_index, previous in enumerate(choices[index - 1])
                ]
                best = max(score for score, _ in scored)
                predecessors = [previous for score, previous in scored if score == best]
                states[index][current_index] = (best, rng.choice(predecessors))
        best = max(score for score, _ in states[-1])
        final = rng.choice([i for i, (score, _) in enumerate(states[-1]) if score == best])
        lifted: list[OrientedEdge] = []
        for index in range(len(choices) - 1, -1, -1):
            lifted.append(choices[index][final])
            predecessor = states[index][final][1]
            if predecessor is not None:
                final = predecessor
        lifted.reverse()
        groups: list[list[OrientedEdge]] = [[lifted[0]]]
        for edge in lifted[1:]:
            if self._native_connected(surface, groups[-1][-1], edge):
                groups[-1].append(edge)
            else:
                groups.append([edge])
        return tuple(
            PathSegment(path_index, group[0].edge.polygon, tuple(group), order + 1)
            for order, group in enumerate(groups)
        )

    @staticmethod
    def _representatives(
        surface: SurfacePresentation, edge: OrientedEdge
    ) -> tuple[OrientedEdge, ...]:
        for gluing in surface.gluings:
            if edge.edge == gluing.first:
                return edge, OrientedEdge(
                    gluing.second, edge.forward if gluing.same_direction else not edge.forward
                )
            if edge.edge == gluing.second:
                return edge, OrientedEdge(
                    gluing.first, edge.forward if gluing.same_direction else not edge.forward
                )
        return (edge,)

    @staticmethod
    def _native_connected(
        surface: SurfacePresentation, first: OrientedEdge, second: OrientedEdge
    ) -> bool:
        if first.edge.polygon != second.edge.polygon:
            return False
        a0, a1 = surface.native_edge_vertices(first.edge)
        b0, b1 = surface.native_edge_vertices(second.edge)
        return (a1 if first.forward else a0) == (b0 if second.forward else b1)

    @staticmethod
    def _quadratic(a: Point, c: Point, b: Point, t: float) -> Point:
        return (
            (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t**2 * b[0],
            (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t**2 * b[1],
        )

    @staticmethod
    def _unit(x: float, y: float) -> Point:
        length = max(1e-9, math.hypot(x, y))
        return x / length, y / length
