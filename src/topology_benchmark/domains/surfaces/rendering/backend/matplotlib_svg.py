import io
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
from topology_benchmark.domains.surfaces.models import SurfacePresentation
from topology_benchmark.domains.surfaces.rendering.config import MatplotlibVisualStyleConfig
from topology_benchmark.domains.surfaces.rendering.diagram_planner import DiagramPlan
from topology_benchmark.domains.surfaces.rendering.diagram_planner import (
    LineStyle,
    OrderDisplay,
)
from topology_benchmark.utils.planer_vector import Point, point_at_fraction, unit


class MatplotlibSurfaceRenderBackend(ISurfaceRenderBackend):
    @override
    def render(
        self,
        surface: SurfacePresentation,
        plan: DiagramPlan,
        request: GenerationRequest,
    ) -> QuestionSection:
        visual_style = self._get_compatible_visual_style(plan)
        figure = Figure(
            figsize=(plan.width / 72, plan.height / 72),
            dpi=72,
            facecolor=visual_style.canvas_color,
            layout=None,
        )
        canvas = FigureCanvasSVG(figure)
        axes = figure.add_axes((0, 0, 1, 1))

        self._configure_axes(axes, plan)
        self._draw_grid(axes, plan)

        labels = self._draw_polygons(axes, plan)

        output = io.StringIO()
        with rc_context({"svg.hashsalt": f"topology_benchmark:{request.seed}"}):
            canvas.print_svg(
                output,
                metadata={
                    "Date": None,
                    "Creator": "topology_benchmark",
                    "Description": f"surface visual style: {visual_style.id}",
                },
            )
        return QuestionSection(
            "image/svg+xml",
            output.getvalue(),
        )

    @staticmethod
    def _configure_axes(axes: Axes, plan: DiagramPlan) -> None:
        axes.set_xlim(0, plan.width)
        axes.set_ylim(plan.height, 0)
        axes.set_aspect("equal", adjustable="box")
        axes.set_facecolor(plan.style.visual.canvas_color)
        axes.set_axis_off()

    @classmethod
    def _draw_grid(cls, axes: Axes, plan: DiagramPlan) -> None:
        grid_config = cls._get_compatible_visual_style(plan).grid
        if grid_config is None:
            return
        for axis_limit, vertical in ((plan.width, True), (plan.height, False)):
            position = 0.0
            index = 0
            while position <= axis_limit:
                alpha = min(
                    1.0, grid_config.alpha * (2.2 if index % grid_config.major_every == 0 else 1.0)
                )
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
                    color=grid_config.color,
                    linewidth=grid_config.width
                    * (1.6 if index % grid_config.major_every == 0 else 1.0),
                    alpha=alpha,
                    zorder=0,
                )
                position += grid_config.spacing
                index += 1

    def _draw_polygons(self, axes: Axes, plan: DiagramPlan) -> list[Text]:
        visual_style = plan.style.visual
        palette = plan.style.palette
        ink = palette.ink
        texts = []
        for polygon_view in plan.polygon_views:
            axes.add_patch(
                PolygonPatch(
                    polygon_view.vertices,
                    closed=True,
                    facecolor=palette.fill,
                    edgecolor="none",
                    zorder=1,
                )
            )
            axes.scatter(
                [point[0] for point in polygon_view.vertices],
                [point[1] for point in polygon_view.vertices],
                s=visual_style.stroke.vertex_size,
                color=ink,
                zorder=4,
            )
            texts.append(
                axes.text(
                    *polygon_view.center,
                    polygon_view.label,
                    color=ink,
                    fontsize=visual_style.labels.polygon_size,
                    fontfamily=visual_style.labels.font_family,
                    ha="center",
                    va="center",
                    zorder=2,
                )
            )

            sides = len(polygon_view.vertices)
            for index in range(sides):
                start, end = (
                    polygon_view.vertices[index],
                    polygon_view.vertices[(index + 1) % sides],
                )
                glued_edge_view = polygon_view.edge_views.get(index)
                line_style: str | tuple[int, tuple[float, ...]] = (
                    (0, visual_style.stroke.dotted_pattern)
                    if glued_edge_view is not None
                    and glued_edge_view.line_style_override is LineStyle.DOTTED
                    else "-"
                )
                self._plot_stroke(
                    axes,
                    (start[0], end[0]),
                    (start[1], end[1]),
                    ink,
                    visual_style.stroke.polygon_width,
                    plan,
                    line_style,
                    3,
                )
                if glued_edge_view is None:
                    continue
                self._draw_arrows_for_curve(
                    axes,
                    (start, end) if glued_edge_view.preserve_orientation else (end, start),
                    ink,
                    1,
                    visual_style.arrows.gluing_size,
                    plan,
                )
                midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
                outward = unit(
                    midpoint[0] - polygon_view.center[0], midpoint[1] - polygon_view.center[1]
                )
                texts.append(
                    axes.text(
                        midpoint[0] + visual_style.labels.gluing_offset * outward[0],
                        midpoint[1] + visual_style.labels.gluing_offset * outward[1],
                        glued_edge_view.label,
                        color=ink,
                        fontsize=visual_style.labels.gluing_size,
                        fontfamily=visual_style.labels.font_family,
                        fontweight="bold",
                        ha="center",
                        va="center",
                        zorder=6,
                    )
                )

                basis_label = polygon_view.homology_basis.get(index)
                if basis_label is None:
                    continue

                visual_style = plan.style.visual
                palette = plan.style.palette
                color = palette.path_colors[0]

                midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
                inward = unit(
                    polygon_view.center[0] - midpoint[0], polygon_view.center[1] - midpoint[1]
                )
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
                    mutation_scale=visual_style.arrows.path_size,
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
                        basis_label,
                        color=color,
                        fontsize=visual_style.labels.path_size,
                        fontfamily=visual_style.labels.font_family,
                        fontweight="bold",
                        ha="center",
                        va="center",
                        bbox={
                            "facecolor": visual_style.canvas_color,
                            "edgecolor": "none",
                            "pad": 0.8,
                            "alpha": 0.9,
                        },
                        zorder=8,
                    )
                )

            for group in polygon_view.path_segment_groups:
                for segment in group.segments:
                    x_values, y_values = zip(*segment.geometry.points, strict=True)
                    self._plot_stroke(
                        axes,
                        x_values,
                        y_values,
                        group.style.color,
                        visual_style.stroke.path_width,
                        plan,
                        "-",
                        5,
                    )
                    arrow_count = (
                        segment.order
                        if group.style.order_display is OrderDisplay.ARROW_COUNT
                        else 1
                    )
                    self._draw_arrows_for_curve(
                        axes,
                        segment.geometry.points,
                        group.style.color,
                        arrow_count,
                        visual_style.arrows.path_size,
                        plan,
                    )
        return texts

    @classmethod
    def _draw_arrows_for_curve(
        cls,
        axes: Axes,
        curve: tuple[Point, ...],
        color: str,
        count: int,
        mutation_scale: float,
        plan: DiagramPlan,
    ) -> None:
        arrows = plan.style.visual.arrows
        for index in range(count):
            start, end = arrows.spread_start, arrows.spread_end
            fraction = (
                (start + end) / 2 if count == 1 else start + index * (end - start) / (count - 1)
            )
            span = arrows.tangent_span
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
            cls._apply_sketch(arrow, plan)
            axes.add_patch(arrow)

    @classmethod
    def _apply_sketch(cls, artist: Artist, plan: DiagramPlan) -> None:
        sketch_config = cls._get_compatible_visual_style(plan).stroke.sketch
        if sketch_config is not None:
            artist.set_sketch_params(
                sketch_config.scale, sketch_config.length, sketch_config.randomness
            )

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
        for glow in cls._get_compatible_visual_style(plan).stroke.glow_layers:
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
    def _get_compatible_visual_style(plan: DiagramPlan) -> MatplotlibVisualStyleConfig:
        visual_style = plan.style.visual
        if not isinstance(visual_style, MatplotlibVisualStyleConfig):
            raise ValueError(
                f"the Matplotlib backend cannot render {visual_style.backend!r} styles"
            )
        return visual_style
