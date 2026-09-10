"""Aligned SVG panels showing only parallel sections of a hidden torus family."""

import io
import math
from random import Random

from matplotlib import rc_context
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure

from topology_benchmark.core.models import GenerationRequest, PromptData
from topology_benchmark.domains.torus_slices.models import (
    TorusSliceObservation,
    Vector3,
    add,
    circle_basis,
    dot,
    scale,
)


class TorusSliceSvgRenderer:
    """Render implicit plane intersections without exposing core-circle parameters."""

    def render(
        self, obj: TorusSliceObservation, request: GenerationRequest, rng: Random
    ) -> PromptData:
        del rng
        columns = 3
        rows = math.ceil(len(obj.levels) / columns)
        figure = Figure(figsize=(9.2, 2.75 * rows + 0.55), dpi=90, facecolor="#f8fafc")
        canvas = FigureCanvasSVG(figure)
        first, second = circle_basis(obj.height_direction)
        min_x, max_x, min_y, max_y = self._bounds(obj, first, second)
        x_values = [min_x + (max_x - min_x) * index / 119 for index in range(120)]
        y_values = [min_y + (max_y - min_y) * index / 119 for index in range(120)]
        for panel, level in enumerate(obj.levels):
            axes = figure.add_subplot(rows, columns, panel + 1)
            axes.set_facecolor("white")
            values = [
                [
                    min(
                        torus.implicit_value(
                            add(
                                add(scale(x, first), scale(y, second)),
                                scale(level, obj.height_direction),
                            )
                        )
                        for torus in obj.family.tori
                    )
                    for x in x_values
                ]
                for y in y_values
            ]
            flat_values = [value for row in values for value in row]
            if min(flat_values) <= 0 <= max(flat_values):
                axes.contour(
                    x_values,
                    y_values,
                    values,
                    levels=(0.0,),
                    colors=("#075985",),
                    linewidths=(2.0,),
                )
            axes.set_xlim(min_x, max_x)
            axes.set_ylim(min_y, max_y)
            axes.set_aspect("equal", adjustable="box")
            axes.set_title(f"h = {level:+.2f}", fontsize=10, color="#334155", pad=5)
            axes.set_xticks(())
            axes.set_yticks(())
            for spine in axes.spines.values():
                spine.set_color("#cbd5e1")
        figure.suptitle(
            "Parallel level sections of the hidden torus family  ·  ↑ increasing h",
            fontsize=12,
            color="#0f172a",
            y=0.985,
        )
        figure.subplots_adjust(
            left=0.025,
            right=0.975,
            bottom=0.035,
            top=0.91,
            wspace=0.08,
            hspace=0.22,
        )
        output = io.StringIO()
        with rc_context({"svg.hashsalt": f"torus-slices:{request.seed}"}):
            canvas.print_svg(output, metadata={"Date": None, "Creator": "topology_benchmark"})
        return PromptData(
            "image/svg+xml",
            output.getvalue(),
            {
                "representation": "aligned-torus-level-sections",
                "level_count": len(obj.levels),
                "common_scale": True,
                "core_circles_shown": False,
                "equations_shown": False,
                "seeded_renderer": True,
            },
        )

    @staticmethod
    def _bounds(
        obj: TorusSliceObservation, first: Vector3, second: Vector3
    ) -> tuple[float, float, float, float]:
        projected = []
        for torus in obj.family.tori:
            extent = torus.core.radius + torus.tube_radius
            projected.append(
                (
                    dot(torus.core.center, first) - extent,
                    dot(torus.core.center, first) + extent,
                    dot(torus.core.center, second) - extent,
                    dot(torus.core.center, second) + extent,
                )
            )
        min_x = min(item[0] for item in projected)
        max_x = max(item[1] for item in projected)
        min_y = min(item[2] for item in projected)
        max_y = max(item[3] for item in projected)
        padding = 0.08 * max(max_x - min_x, max_y - min_y)
        return min_x - padding, max_x + padding, min_y - padding, max_y + padding
