"""Deterministic SVG rendering of metric nets without revealing seam matches."""

import html
import math
from random import Random

from topology_benchmark.core.models import GenerationRequest, PromptData
from topology_benchmark.domains.polyhedral_nets.models import (
    FaceCorner,
    NetEdge,
    PolygonFace,
    PolyhedralNet,
)

type Point = tuple[float, float]


class PolyhedralNetSvgRenderer:
    def render(self, obj: PolyhedralNet, request: GenerationRequest, rng: Random) -> PromptData:
        del request
        layouts = self._layout(obj)
        points = [point for polygon in layouts for point in polygon]
        min_x, max_x = min(x for x, _ in points), max(x for x, _ in points)
        min_y, max_y = min(y for _, y in points), max(y for _, y in points)
        scale = min(
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
        for face_index, (face, polygon) in enumerate(zip(obj.faces, layouts, strict=True)):
            vertices = " ".join(f"{x:.3f},{y:.3f}" for x, y in map(screen, polygon))
            chunks.append(
                f'<polygon points="{vertices}" fill="{fill}" fill-opacity="0.88" '
                'stroke="#263746" stroke-width="2.3" stroke-linejoin="round"/>'
            )
            center = screen(
                (
                    sum(x for x, _ in polygon) / len(polygon),
                    sum(y for _, y in polygon) / len(polygon),
                )
            )
            shown_face_labels = dict(obj.face_labels)
            face_label = shown_face_labels.get(face_index)
            if face_label is None and not isinstance(face, PolygonFace):
                face_label = face.name
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
                if isinstance(face, PolygonFace) and edge not in explicit_labels:
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
        if obj.marked_corner is not None and not obj.corner_labels:
            marked_points = self._marked_points(obj, layouts, obj.marked_corner)
            for point in marked_points:
                x, y = screen(point)
                chunks.append(
                    f'<circle cx="{x:.3f}" cy="{y:.3f}" r="5.5" fill="#d93025" '
                    'stroke="white" stroke-width="1.5"/>'
                )
            chunks.append(
                '<text x="14" y="24" font-family="sans-serif" font-size="13" fill="#d93025">'
                "The red corner belongs to the queried folded vertex.</text>"
            )
        footer = (
            "rigid faces · diagram drawn to scale"
            if any(isinstance(face, PolygonFace) for face in obj.faces)
            else "regular faces · unit side length"
        )
        chunks.append(
            f'<text x="{width - 12:.3f}" y="{height - 12:.3f}" text-anchor="end" '
            'font-family="sans-serif" font-size="11" fill="#68737d">'
            f"{footer}</text>"
        )
        chunks.append("</svg>")
        return PromptData(
            "image/svg+xml",
            "".join(chunks),
            {
                "representation": "metric-polyhedral-net-svg",
                "face_count": len(obj.faces),
                "boundary_edge_count": len(obj.boundary_edges),
                "seam_matches_shown": bool(obj.seam_hints),
                "regular_faces": all(not isinstance(face, PolygonFace) for face in obj.faces),
                "seeded_renderer": True,
            },
        )

    def _layout(self, net: PolyhedralNet) -> tuple[tuple[Point, ...], ...]:
        if all(isinstance(face, PolygonFace) for face in net.faces):
            return tuple(face.points for face in net.faces if isinstance(face, PolygonFace))
        layouts: list[tuple[Point, ...] | None] = [None] * len(net.faces)
        layouts[0] = self._regular_polygon(net.faces[0].sides)
        pending = list(net.hinges)
        while pending:
            progress = False
            for pair in tuple(pending):
                if layouts[pair.first.face] is not None and layouts[pair.second.face] is None:
                    parent, child = pair.first, pair.second
                elif layouts[pair.second.face] is not None and layouts[pair.first.face] is None:
                    parent, child = pair.second, pair.first
                else:
                    continue
                parent_polygon = layouts[parent.face]
                if parent_polygon is None:
                    raise AssertionError("parent layout disappeared")
                layouts[child.face] = self._attach_polygon(
                    net.faces[child.face].sides,
                    child.edge,
                    parent_polygon[parent.edge],
                    parent_polygon[(parent.edge + 1) % len(parent_polygon)],
                )
                pending.remove(pair)
                progress = True
            if not progress:
                raise ValueError("hinge graph cannot be laid out")
        return tuple(layout for layout in layouts if layout is not None)

    @staticmethod
    def _regular_polygon(sides: int) -> tuple[Point, ...]:
        radius = 1 / (2 * math.sin(math.pi / sides))
        start = -math.pi / 2 - math.pi / sides
        return tuple(
            (
                radius * math.cos(start + 2 * math.pi * index / sides),
                radius * math.sin(start + 2 * math.pi * index / sides),
            )
            for index in range(sides)
        )

    @staticmethod
    def _attach_polygon(
        sides: int, edge_index: int, parent_start: Point, parent_end: Point
    ) -> tuple[Point, ...]:
        vertices: list[Point | None] = [None] * sides
        # Paired face boundaries run in opposite directions.
        vertices[edge_index] = parent_end
        vertices[(edge_index + 1) % sides] = parent_start
        direction = math.atan2(parent_start[1] - parent_end[1], parent_start[0] - parent_end[0])
        current = parent_start
        for step in range(1, sides - 1):
            direction += 2 * math.pi / sides
            current = (current[0] + math.cos(direction), current[1] + math.sin(direction))
            vertices[(edge_index + 1 + step) % sides] = current
        if any(vertex is None for vertex in vertices):
            raise AssertionError("incomplete regular polygon layout")
        return tuple(vertex for vertex in vertices if vertex is not None)

    @staticmethod
    def _marked_points(
        net: PolyhedralNet,
        layouts: tuple[tuple[Point, ...], ...],
        marked: FaceCorner,
    ) -> tuple[Point, ...]:
        del net
        return (layouts[marked.face][marked.corner],)
