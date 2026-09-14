import io
from random import Random
from typing import override

from matplotlib import rc_context
from matplotlib.axes import Axes
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch
from matplotlib.patches import Polygon as PolygonPatch

from topology_benchmark.core.problem.models import GenerationRequest, QuestionSection
from topology_benchmark.domains.surfaces.models import EdgeRef, SurfacePresentation
from topology_benchmark.domains.surfaces.ports import ISurfaceRepresentation
from topology_benchmark.domains.surfaces.rendering.config import (
    SurfaceRenderingConfig,
)
from topology_benchmark.domains.surfaces.rendering.diagram import (
    DiagramPlan,
    LinePattern,
    OrderDisplay,
    PathCurve,
    Point,
    SurfaceDiagramPlanner,
)


class MatplotlibGluingDiagramRenderer(ISurfaceRepresentation):
    def __init__(self, planner: SurfaceDiagramPlanner, config: SurfaceRenderingConfig) -> None:
        self._planner = planner
        self._config = config

    @override
    def render(
        self,
        obj: SurfacePresentation,
        request: GenerationRequest,
        rng: Random,
        *,
        edge_labels: tuple[tuple[EdgeRef, str], ...] = (),
    ) -> QuestionSection:
        del rng
        plan = self._planner.plan(obj, Random((request.seed << 8) ^ 0xA53C9E))
        figure = Figure(
            figsize=(plan.width / 72, plan.height / 72),
            dpi=72,
            facecolor="white",
            layout=None,
        )
        canvas = FigureCanvasSVG(figure)
        axes = figure.add_axes((0, 0, 1, 1))
        self._configure_axes(axes, plan)
        self._draw_polygons(axes, obj, plan)
        self._draw_edge_labels(axes, plan, edge_labels)
        for curve in plan.curves:
            self._draw_path_curve(
                axes,
                curve,
                plan.style.path_width,
                obj.paths[curve.segment.path_index].name,
            )

        output = io.StringIO()
        with rc_context({"svg.hashsalt": f"topology_benchmark:{request.seed}"}):
            canvas.print_svg(
                output,
                metadata={"Date": None, "Creator": "topology_benchmark"},
            )
        return QuestionSection(
            "image/svg+xml",
            output.getvalue(),
        )

    def _draw_edge_labels(
        self,
        axes: Axes,
        plan: DiagramPlan,
        edge_labels: tuple[tuple[EdgeRef, str], ...],
    ) -> None:
        color = "#9f1239"
        for edge, label in edge_labels:
            layout = plan.polygons[edge.polygon]
            start, end = layout.edge(edge.edge)
            midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
            inward = self._unit(layout.center[0] - midpoint[0], layout.center[1] - midpoint[1])
            offset = 10.0
            arrow_start = (
                start[0] + 0.22 * (end[0] - start[0]) + offset * inward[0],
                start[1] + 0.22 * (end[1] - start[1]) + offset * inward[1],
            )
            arrow_end = (
                start[0] + 0.78 * (end[0] - start[0]) + offset * inward[0],
                start[1] + 0.78 * (end[1] - start[1]) + offset * inward[1],
            )
            axes.add_patch(
                FancyArrowPatch(
                    arrow_start,
                    arrow_end,
                    arrowstyle="-|>",
                    mutation_scale=self._config.arrows.path_size,
                    color=color,
                    linewidth=1.35,
                    shrinkA=0,
                    shrinkB=0,
                    zorder=7,
                )
            )
            axes.text(
                midpoint[0] + 24 * inward[0],
                midpoint[1] + 24 * inward[1],
                label,
                color=color,
                fontsize=self._config.labels.path_size,
                fontweight="bold",
                ha="center",
                va="center",
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.8, "alpha": 0.9},
                zorder=8,
            )

    @staticmethod
    def _configure_axes(axes: Axes, plan: DiagramPlan) -> None:
        axes.set_xlim(0, plan.width)
        axes.set_ylim(plan.height, 0)
        axes.set_aspect("equal", adjustable="box")
        axes.set_axis_off()

    def _draw_polygons(self, axes: Axes, surface: SurfacePresentation, plan: DiagramPlan) -> None:
        ink = plan.style.palette.ink
        for polygon, layout in zip(surface.polygons, plan.polygons, strict=True):
            axes.add_patch(
                PolygonPatch(
                    layout.vertices,
                    closed=True,
                    facecolor=plan.style.palette.fill,
                    edgecolor="none",
                    zorder=1,
                )
            )
            axes.scatter(
                [point[0] for point in layout.vertices],
                [point[1] for point in layout.vertices],
                s=self._config.stroke.vertex_size,
                color=ink,
                zorder=4,
            )
            axes.text(
                *layout.center,
                polygon.name,
                color=ink,
                fontsize=self._config.labels.polygon_size,
                ha="center",
                va="center",
                zorder=2,
            )

        marked = {
            edge: (gluing, other)
            for gluing in surface.gluings
            for edge, other in ((gluing.first, gluing.second), (gluing.second, gluing.first))
        }
        for polygon_index, polygon in enumerate(surface.polygons):
            layout = plan.polygons[polygon_index]
            for side in range(polygon.sides):
                edge = EdgeRef(polygon_index, side)
                start, end = layout.edge(side)
                pattern = self._planner.edge_pattern(surface, edge, plan.style.boundary_pattern)
                line_style: str | tuple[int, tuple[float, ...]] = (
                    "-" if pattern is LinePattern.SOLID else (0, self._config.stroke.dotted_pattern)
                )
                axes.plot(
                    (start[0], end[0]),
                    (start[1], end[1]),
                    color=ink,
                    linewidth=plan.style.polygon_width,
                    linestyle=line_style,
                    solid_capstyle="round",
                    dash_capstyle="round",
                    zorder=3,
                )
                gluing_mark = marked.get(edge)
                if gluing_mark is None:
                    continue
                gluing, _ = gluing_mark
                forward = edge == gluing.first or gluing.same_direction
                self._arrows(
                    axes,
                    (start, end) if forward else (end, start),
                    ink,
                    1,
                    self._config.arrows.gluing_size,
                )
                midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
                outward = self._unit(midpoint[0] - layout.center[0], midpoint[1] - layout.center[1])
                axes.text(
                    midpoint[0] + self._config.labels.gluing_offset * outward[0],
                    midpoint[1] + self._config.labels.gluing_offset * outward[1],
                    gluing.label,
                    color=ink,
                    fontsize=self._config.labels.gluing_size,
                    fontweight="bold",
                    ha="center",
                    va="center",
                    zorder=6,
                )

    def _draw_path_curve(self, axes: Axes, curve: PathCurve, width: float, path_name: str) -> None:
        x_values, y_values = zip(*curve.points, strict=True)
        axes.plot(
            x_values,
            y_values,
            color=curve.style.color,
            linewidth=width,
            solid_capstyle="round",
            zorder=5,
        )
        arrow_count = (
            curve.segment.order if curve.style.order_display is OrderDisplay.ARROW_COUNT else 1
        )
        self._arrows(
            axes,
            curve.points,
            curve.style.color,
            arrow_count,
            self._config.arrows.path_size,
        )
        if curve.style.order_display is OrderDisplay.NUMBER_TAG:
            if curve.tag_position is None:
                raise ValueError("a numbered path curve needs a planned tag position")
            axes.text(
                *curve.tag_position,
                str(curve.segment.order),
                color=curve.style.color,
                fontsize=self._config.labels.order_size,
                fontweight="bold",
                ha="center",
                va="center",
                bbox={
                    "boxstyle": "circle,pad=0.22",
                    "facecolor": "white",
                    "edgecolor": curve.style.color,
                    "linewidth": 1.2,
                },
                zorder=8,
            )
        if curve.segment.order == 1:
            if curve.name_position is None:
                raise ValueError("a path's first curve needs a planned name position")
            axes.text(
                *curve.name_position,
                path_name,
                color=curve.style.color,
                fontsize=self._config.labels.path_size,
                ha="center",
                va="center",
                fontstyle="italic",
                fontweight="bold",
                zorder=8,
            )

    def _arrows(
        self,
        axes: Axes,
        curve: tuple[Point, ...],
        color: str,
        count: int,
        mutation_scale: float,
    ) -> None:
        for index in range(count):
            start = self._config.arrows.spread_start
            end = self._config.arrows.spread_end
            fraction = (
                (start + end) / 2 if count == 1 else start + index * (end - start) / (count - 1)
            )
            span = self._config.arrows.tangent_span
            previous = self._point_at_fraction(curve, max(0.0, fraction - span))
            point = self._point_at_fraction(curve, min(1.0, fraction + span))
            axes.add_patch(
                FancyArrowPatch(
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
            )

    @staticmethod
    def _point_at_fraction(curve: tuple[Point, ...], fraction: float) -> Point:
        position = fraction * (len(curve) - 1)
        lower = min(len(curve) - 2, int(position))
        local = position - lower
        start, end = curve[lower], curve[lower + 1]
        return (
            start[0] + (end[0] - start[0]) * local,
            start[1] + (end[1] - start[1]) * local,
        )

    @staticmethod
    def _unit(x: float, y: float) -> Point:
        length = max(1e-9, (x * x + y * y) ** 0.5)
        return x / length, y / length
