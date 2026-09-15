from topology_benchmark.domains.surfaces.rendering.diagram_planner import (
    SurfaceDiagramPlanner,
    LinePattern,
    PathSegmentGeometry,
    OrderDisplay,
)
import io
import math
from typing import override

from adjustText import adjust_text
from matplotlib import rc_context
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch
from matplotlib.patches import Polygon as PolygonPatch
from matplotlib.text import Text

from topology_benchmark.core.problem.models import GenerationRequest, QuestionSection
from topology_benchmark.domains.surfaces.abstractions import ISurfaceRenderBackend
from topology_benchmark.domains.surfaces.models import EdgeRef, SurfacePresentation
from topology_benchmark.domains.surfaces.rendering.config import MatplotlibVisualStyleConfig
from topology_benchmark.domains.surfaces.rendering.diagram_planner import DiagramPlan
from topology_benchmark.utils.planer_vector import Point


class MatplotlibSurfaceRenderBackend(ISurfaceRenderBackend):
    @override
    def render(
        self,
        obj: SurfacePresentation,
        plan: DiagramPlan,
        request: GenerationRequest,
    ) -> QuestionSection:
        profile = self._profile(plan)
        figure = Figure(
            figsize=(plan.width / 72, plan.height / 72),
            dpi=72,
            facecolor=profile.canvas_color,
            layout=None,
        )
        canvas = FigureCanvasSVG(figure)
        axes = figure.add_axes((0, 0, 1, 1))
        self._configure_axes(axes, plan)
        self._draw_grid(axes, plan)
        labels = self._draw_polygons(axes, obj, plan)
        labels.extend(self._draw_edge_labels(axes, plan, obj.edge_labels))
        for curve in plan.curves:
            labels.extend(
                self._draw_path_curve(
                    axes,
                    curve,
                    plan,
                    obj.paths[curve.segment.path_index].name,
                )
            )
        self._adjust_labels(axes, labels, plan)

        output = io.StringIO()
        with rc_context({"svg.hashsalt": f"topology_benchmark:{request.seed}"}):
            canvas.print_svg(
                output,
                metadata={
                    "Date": None,
                    "Creator": "topology_benchmark",
                    "Description": f"surface visual style: {profile.id}",
                },
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
    ) -> list[Text]:
        profile = plan.style.visual.profile
        palette = plan.style.visual.palette
        color = palette.path_colors[0]
        texts = []
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
            arrow = FancyArrowPatch(
                arrow_start,
                arrow_end,
                arrowstyle="-|>",
                mutation_scale=profile.arrows.path_size,
                color=color,
                linewidth=1.35,
                shrinkA=0,
                shrinkB=0,
                zorder=7,
            )
            self._apply_sketch(arrow, plan)
            axes.add_patch(arrow)
            texts.append(
                axes.text(
                    midpoint[0] + 24 * inward[0],
                    midpoint[1] + 24 * inward[1],
                    label,
                    color=color,
                    fontsize=profile.labels.path_size,
                    fontfamily=profile.labels.font_family,
                    fontweight="bold",
                    ha="center",
                    va="center",
                    bbox={
                        "facecolor": profile.canvas_color,
                        "edgecolor": "none",
                        "pad": 0.8,
                        "alpha": 0.9,
                    },
                    zorder=8,
                )
            )
        return texts

    @staticmethod
    def _configure_axes(axes: Axes, plan: DiagramPlan) -> None:
        axes.set_xlim(0, plan.width)
        axes.set_ylim(plan.height, 0)
        axes.set_aspect("equal", adjustable="box")
        axes.set_facecolor(plan.style.visual.profile.canvas_color)
        axes.set_axis_off()

    @staticmethod
    def _draw_grid(axes: Axes, plan: DiagramPlan) -> None:
        grid = MatplotlibSurfaceRenderBackend._profile(plan).grid
        if grid is None:
            return
        for axis_limit, vertical in ((plan.width, True), (plan.height, False)):
            position = 0.0
            index = 0
            while position <= axis_limit:
                alpha = min(1.0, grid.alpha * (2.2 if index % grid.major_every == 0 else 1.0))
                coordinates = (
                    ((position, position), (0, plan.height))
                    if vertical
                    else (
                        (0, plan.width),
                        (position, position),
                    )
                )
                axes.plot(
                    *coordinates,
                    color=grid.color,
                    linewidth=grid.width * (1.6 if index % grid.major_every == 0 else 1.0),
                    alpha=alpha,
                    zorder=0,
                )
                position += grid.spacing
                index += 1

    def _draw_polygons(
        self, axes: Axes, surface: SurfacePresentation, plan: DiagramPlan
    ) -> list[Text]:
        profile = plan.style.visual.profile
        palette = plan.style.visual.palette
        ink = palette.ink
        texts = []
        for polygon, layout in zip(surface.polygons, plan.polygons, strict=True):
            axes.add_patch(
                PolygonPatch(
                    layout.vertices,
                    closed=True,
                    facecolor=palette.fill,
                    edgecolor="none",
                    zorder=1,
                )
            )
            axes.scatter(
                [point[0] for point in layout.vertices],
                [point[1] for point in layout.vertices],
                s=profile.stroke.vertex_size,
                color=ink,
                zorder=4,
            )
            texts.append(
                axes.text(
                    *layout.center,
                    polygon.name,
                    color=ink,
                    fontsize=profile.labels.polygon_size,
                    fontfamily=profile.labels.font_family,
                    ha="center",
                    va="center",
                    zorder=2,
                )
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
                pattern = SurfaceDiagramPlanner.edge_pattern(
                    surface, edge, plan.style.boundary_pattern
                )
                line_style: str | tuple[int, tuple[float, ...]] = (
                    "-" if pattern is LinePattern.SOLID else (0, profile.stroke.dotted_pattern)
                )
                self._plot_stroke(
                    axes,
                    (start[0], end[0]),
                    (start[1], end[1]),
                    ink,
                    profile.stroke.polygon_width,
                    plan,
                    line_style,
                    3,
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
                    profile.arrows.gluing_size,
                    plan,
                )
                midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
                outward = self._unit(midpoint[0] - layout.center[0], midpoint[1] - layout.center[1])
                texts.append(
                    axes.text(
                        midpoint[0] + profile.labels.gluing_offset * outward[0],
                        midpoint[1] + profile.labels.gluing_offset * outward[1],
                        gluing.label,
                        color=ink,
                        fontsize=profile.labels.gluing_size,
                        fontfamily=profile.labels.font_family,
                        fontweight="bold",
                        ha="center",
                        va="center",
                        zorder=6,
                    )
                )
        return texts

    def _draw_path_curve(
        self, axes: Axes, curve: PathSegmentGeometry, plan: DiagramPlan, path_name: str
    ) -> list[Text]:
        profile = plan.style.visual.profile
        texts = []
        x_values, y_values = zip(*curve.points, strict=True)
        self._plot_stroke(
            axes,
            x_values,
            y_values,
            curve.style.color,
            profile.stroke.path_width,
            plan,
            "-",
            5,
        )
        arrow_count = (
            curve.segment.order if curve.style.order_display is OrderDisplay.ARROW_COUNT else 1
        )
        self._arrows(
            axes,
            curve.points,
            curve.style.color,
            arrow_count,
            profile.arrows.path_size,
            plan,
        )
        if curve.style.order_display is OrderDisplay.NUMBER_TAG:
            if curve.tag_position is None:
                raise ValueError("a numbered path curve needs a planned tag position")
            texts.append(
                axes.text(
                    *curve.tag_position,
                    str(curve.segment.order),
                    color=curve.style.color,
                    fontsize=profile.labels.order_size,
                    fontfamily=profile.labels.font_family,
                    fontweight="bold",
                    ha="center",
                    va="center",
                    bbox={
                        "boxstyle": "circle,pad=0.22",
                        "facecolor": profile.canvas_color,
                        "edgecolor": curve.style.color,
                        "linewidth": 1.2,
                    },
                    zorder=8,
                )
            )
        if curve.segment.order == 1:
            if curve.name_position is None:
                raise ValueError("a path's first curve needs a planned name position")
            texts.append(
                axes.text(
                    *curve.name_position,
                    path_name,
                    color=curve.style.color,
                    fontsize=profile.labels.path_size,
                    fontfamily=profile.labels.font_family,
                    ha="center",
                    va="center",
                    fontstyle="italic",
                    fontweight="bold",
                    zorder=8,
                )
            )
        return texts

    @classmethod
    def _adjust_labels(cls, axes: Axes, texts: list[Text], plan: DiagramPlan) -> None:
        if not texts:
            return
        obstacles = cls._label_obstacles(plan)
        x_values, y_values = zip(*obstacles, strict=True)
        adjust_text(
            texts,
            x=x_values,
            y=y_values,
            ax=axes,
            expand=(1.08, 1.16),
            force_text=(0.18, 0.24),
            force_static=(0.12, 0.18),
            force_pull=(0.015, 0.015),
            max_move=(8, 8),
            ensure_inside_axes=True,
            prevent_crossings=True,
            iter_lim=200,
        )

    @classmethod
    def _label_obstacles(cls, plan: DiagramPlan) -> tuple[Point, ...]:
        profile = cls._profile(plan)
        spacing = max(4.0, min(profile.labels.gluing_size, profile.labels.path_size) * 0.7)
        polygon_edges = (
            point
            for layout in plan.polygons
            for edge_index in range(len(layout.vertices))
            for point in cls._sample_line(*layout.edge(edge_index), spacing)
        )
        return *polygon_edges, *(point for curve in plan.curves for point in curve.points)

    @staticmethod
    def _sample_line(start: Point, end: Point, spacing: float) -> tuple[Point, ...]:
        intervals = max(1, math.ceil(math.dist(start, end) / spacing))
        return tuple(
            (
                start[0] + (end[0] - start[0]) * index / intervals,
                start[1] + (end[1] - start[1]) * index / intervals,
            )
            for index in range(intervals + 1)
        )

    def _arrows(
        self,
        axes: Axes,
        curve: tuple[Point, ...],
        color: str,
        count: int,
        mutation_scale: float,
        plan: DiagramPlan,
    ) -> None:
        arrows = plan.style.visual.profile.arrows
        for index in range(count):
            start = arrows.spread_start
            end = arrows.spread_end
            fraction = (
                (start + end) / 2 if count == 1 else start + index * (end - start) / (count - 1)
            )
            span = arrows.tangent_span
            previous = self._point_at_fraction(curve, max(0.0, fraction - span))
            point = self._point_at_fraction(curve, min(1.0, fraction + span))
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
            self._apply_sketch(arrow, plan)
            axes.add_patch(arrow)

    @staticmethod
    def _apply_sketch(artist: Artist, plan: DiagramPlan) -> None:
        sketch = MatplotlibSurfaceRenderBackend._profile(plan).stroke.sketch
        if sketch is not None:
            artist.set_sketch_params(sketch.scale, sketch.length, sketch.randomness)

    @classmethod
    def _plot_stroke(
        cls,
        axes: Axes,
        x_values: tuple[float, ...] | list[float],
        y_values: tuple[float, ...] | list[float],
        color: str,
        width: float,
        plan: DiagramPlan,
        line_style: str | tuple[int, tuple[float, ...]],
        zorder: int,
    ) -> None:
        for glow in cls._profile(plan).stroke.glow_layers:
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
        cls._apply_sketch(line, plan)

    @staticmethod
    def _profile(plan: DiagramPlan) -> MatplotlibVisualStyleConfig:
        profile = plan.style.visual.profile
        if not isinstance(profile, MatplotlibVisualStyleConfig):
            raise ValueError(f"the Matplotlib backend cannot render {profile.backend!r} styles")
        return profile

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
