import html
import math
from random import Random
from typing import override

from topology_benchmark.core.problem.models import GenerationRequest, QuestionSection
from topology_benchmark.domains.polyhedral_nets.models.net import (
    NetEdge,
    PolyhedralNet,
)
from topology_benchmark.domains.polyhedral_nets.ports import IPolyhedralNetRepresentation

type Point = tuple[float, float]


class PolyhedralNetSvgRenderer(IPolyhedralNetRepresentation):
    def common_scale(self, objects: tuple[PolyhedralNet, ...]) -> float:
        """Return one pixels-per-unit scale that fits every net in a comparison."""
        limits = []
        for obj in objects:
            points = [point for polygon in self._layout(obj) for point in polygon]
            min_x, max_x = min(x for x, _ in points), max(x for x, _ in points)
            min_y, max_y = min(y for _, y in points), max(y for _, y in points)
            limits.append(
                min(
                    86.0,
                    1000.0 / max(1e-9, max_x - min_x),
                    720.0 / max(1e-9, max_y - min_y),
                )
            )
        return min(limits)

    @override
    def render(
        self,
        obj: PolyhedralNet,
        request: GenerationRequest,
        rng: Random,
        *,
        scale: float | None = None,
    ) -> QuestionSection:
        del request
        layouts = self._layout(obj)
        points = [point for polygon in layouts for point in polygon]
        min_x, max_x = min(x for x, _ in points), max(x for x, _ in points)
        min_y, max_y = min(y for _, y in points), max(y for _, y in points)
        scale = scale or min(
            86.0,
            1000.0 / max(1e-9, max_x - min_x),
            720.0 / max(1e-9, max_y - min_y),
        )
        margin = 62.0
        width = (max_x - min_x) * scale + 2 * margin
        height = (max_y - min_y) * scale + 2 * margin

        def screen(point: Point) -> Point:
            return (
                margin + (point[0] - min_x) * scale,
                margin + (max_y - point[1]) * scale,
            )

        palette = rng.choice(
            (("#eef5ff", "#174ea6"), ("#f3f8ee", "#376b2d"), ("#fff5e8", "#9a5417"))
        )
        fill, accent = palette
        chunks = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
            f'viewBox="0 0 {width:.3f} {height:.3f}">',
            '<defs><pattern id="grid" width="21.5" height="21.5" patternUnits="userSpaceOnUse">'
            '<path d="M 21.5 0 L 0 0 0 21.5" fill="none" stroke="#dfe6ee" '
            'stroke-width="0.7"/></pattern></defs>',
            '<rect width="100%" height="100%" fill="white"/>'
            '<rect width="100%" height="100%" fill="url(#grid)"/>',
        ]
        labelled_face_fills = ("#e8f0fe", "#e6f4ea", "#fef7e0", "#fce8e6", "#f3e8fd", "#e0f7fa")
        shown_face_labels = dict(obj.face_labels)
        for face_index, (face, polygon) in enumerate(zip(obj.faces, layouts, strict=True)):
            vertices = " ".join(f"{x:.3f},{y:.3f}" for x, y in map(screen, polygon))
            face_fill = (
                labelled_face_fills[face_index % len(labelled_face_fills)]
                if face_index in shown_face_labels
                else fill
            )
            chunks.append(
                f'<polygon points="{vertices}" fill="{face_fill}" fill-opacity="0.88" '
                'stroke="#263746" stroke-width="2.3" stroke-linejoin="round"/>'
            )
            center = screen(
                (
                    sum(x for x, _ in polygon) / len(polygon),
                    sum(y for _, y in polygon) / len(polygon),
                )
            )
            face_label = shown_face_labels.get(face_index)
            if face_label is not None:
                chunks.append(
                    f'<text x="{center[0]:.3f}" y="{center[1]:.3f}" text-anchor="middle" '
                    f'dominant-baseline="middle" font-family="sans-serif" font-size="13" '
                    f'font-weight="bold" fill="#425466">{html.escape(face_label)}</text>'
                )
            for edge_index in range(face.sides):
                edge = NetEdge(face_index, edge_index)
                if edge not in obj.boundary_edges:
                    continue
                start, end = (
                    screen(polygon[edge_index]),
                    screen(polygon[(edge_index + 1) % face.sides]),
                )
                midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
                direction = (midpoint[0] - center[0], midpoint[1] - center[1])
                norm = max(1e-9, math.hypot(*direction))
                explicit_labels = dict(obj.edge_labels)
                if edge not in explicit_labels:
                    continue
                label = explicit_labels.get(edge, obj.boundary_label(edge))
                chunks.append(
                    f'<text x="{midpoint[0] + 13 * direction[0] / norm:.3f}" '
                    f'y="{midpoint[1] + 13 * direction[1] / norm:.3f}" text-anchor="middle" '
                    f'dominant-baseline="middle" font-family="sans-serif" font-size="11" '
                    f'font-weight="bold" fill="{accent}">{label}</text>'
                )
        hint_palette = ("#8e44ad", "#00897b", "#ef6c00", "#5c6bc0")
        for hint_index, pair in enumerate(obj.seam_hints):
            color = hint_palette[hint_index % len(hint_palette)]
            for edge in (pair.first, pair.second):
                polygon = layouts[edge.face]
                start = screen(polygon[edge.edge])
                end = screen(polygon[(edge.edge + 1) % len(polygon)])
                midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
                chunks.append(
                    f'<circle cx="{midpoint[0]:.3f}" cy="{midpoint[1]:.3f}" r="4.3" '
                    f'fill="{color}" stroke="white" stroke-width="1.2"/>'
                )
        if obj.seam_hints:
            chunks.append(
                '<text x="14" y="24" font-family="sans-serif" font-size="12" '
                'fill="#5f6368">Equal-colored dots mark boundary edges that must be glued.</text>'
            )
        corner_palette = ("#d93025", "#1967d2", "#188038", "#9334e6")
        for index, (corner, label) in enumerate(obj.corner_labels):
            x, y = screen(layouts[corner.face][corner.corner])
            color = corner_palette[index % len(corner_palette)]
            chunks.append(
                f'<circle cx="{x:.3f}" cy="{y:.3f}" r="6" fill="{color}" '
                'stroke="white" stroke-width="1.5"/>'
                f'<text x="{x + 9:.3f}" y="{y - 9:.3f}" font-family="sans-serif" '
                f'font-size="13" font-weight="bold" fill="{color}">{html.escape(label)}</text>'
            )
        for corner, label in obj.corner_angle_labels:
            point = screen(layouts[corner.face][corner.corner])
            polygon = tuple(map(screen, layouts[corner.face]))
            center = (
                sum(x for x, _ in polygon) / len(polygon),
                sum(y for _, y in polygon) / len(polygon),
            )
            direction = (center[0] - point[0], center[1] - point[1])
            norm = max(1e-9, math.hypot(*direction))
            x = point[0] + 17 * direction[0] / norm
            y = point[1] + 17 * direction[1] / norm
            chunks.append(
                f'<text x="{x:.3f}" y="{y:.3f}" text-anchor="middle" '
                'dominant-baseline="middle" font-family="sans-serif" font-size="8.5" '
                f'fill="#5f6368">{html.escape(label)}</text>'
            )
        chunks.append(
            f'<text x="{width - 12:.3f}" y="{height - 12:.3f}" text-anchor="end" '
            'font-family="sans-serif" font-size="11" fill="#68737d">'
            "rigid faces · diagram drawn to scale</text>"
        )
        bar_x = 14.0
        bar_y = height - 16.0
        chunks.append(
            f'<line x1="{bar_x:.3f}" y1="{bar_y:.3f}" x2="{bar_x + scale:.3f}" '
            f'y2="{bar_y:.3f}" stroke="#68737d" stroke-width="2"/>'
            f'<text x="{bar_x + scale / 2:.3f}" y="{bar_y - 5:.3f}" text-anchor="middle" '
            'font-family="sans-serif" font-size="9" fill="#68737d">1 unit</text>'
        )
        chunks.append("</svg>")
        return QuestionSection(
            "image/svg+xml",
            "".join(chunks),
        )

    def _layout(self, net: PolyhedralNet) -> tuple[tuple[Point, ...], ...]:
        return tuple(face.points for face in net.faces)
