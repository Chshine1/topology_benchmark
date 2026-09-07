"""A pure SVG renderer for directed polygon gluings and curved paths."""

from html import escape
from random import Random
from typing import ClassVar

from topology_benchmark.core.models import GenerationRequest, PromptData
from topology_benchmark.domains.surfaces.analysis import SurfaceAnalyzer
from topology_benchmark.domains.surfaces.models import EdgeRef, Point, SurfacePresentation
from topology_benchmark.domains.surfaces.ports import SurfaceRepresentation


class SvgGluingDiagramRenderer(SurfaceRepresentation):
    """Render stored parameters only; all random choices belong to generation."""

    _PALETTES: ClassVar[dict[str, tuple[str, str, str]]] = {
        "ink": ("#f8f5ed", "#263238", "#c62828"),
        "ocean": ("#e8f4f8", "#164e63", "#be123c"),
        "clay": ("#fff1e6", "#5d4037", "#1565c0"),
    }

    def render(
        self, obj: SurfacePresentation, request: GenerationRequest, rng: Random
    ) -> PromptData:
        del request, rng
        presentation = obj
        fill, ink, accent = self._PALETTES[presentation.palette]
        max_x = max(point.x for polygon in presentation.polygons for point in polygon.vertices)
        max_y = max(point.y for polygon in presentation.polygons for point in polygon.vertices)
        width, height = int(max(520.0, max_x + 90)), int(max(330.0, max_y + 80))
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="polygon gluing diagram">',
            '<defs><marker id="arrow" markerWidth="8" markerHeight="8" '
            'refX="4" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" '
            f'fill="{ink}"/></marker></defs>',
            '<rect width="100%" height="100%" fill="white"/>',
        ]
        marks_by_edge = {mark.edge: mark for mark in presentation.marks}
        for polygon_index, polygon in enumerate(presentation.polygons):
            points = " ".join(f"{p.x:.1f},{p.y:.1f}" for p in polygon.vertices)
            parts.append(
                f'<polygon points="{points}" fill="{fill}" stroke="{ink}" stroke-width="2.5"/>'
            )
            cx = sum(p.x for p in polygon.vertices) / len(polygon.vertices)
            cy = sum(p.y for p in polygon.vertices) / len(polygon.vertices)
            parts.append(
                f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" '
                f'font-family="sans-serif" font-size="15" fill="{ink}">'
                f"{escape(polygon.name)}</text>"
            )
            for edge in range(len(polygon.vertices)):
                start = polygon.vertices[edge]
                end = polygon.vertices[(edge + 1) % len(polygon.vertices)]
                mark = marks_by_edge.get(EdgeRef(polygon_index, edge))
                if mark is None:
                    parts.append(
                        f'<line x1="{start.x:.1f}" y1="{start.y:.1f}" x2="{end.x:.1f}" '
                        f'y2="{end.y:.1f}" stroke="#777" stroke-width="5" '
                        'stroke-dasharray="5 5"/>'
                    )
                    continue
                arrow_start, arrow_end = (start, end) if mark.forward else (end, start)
                parts.append(self._marked_edge(arrow_start, arrow_end, mark.word, ink))

        for path in presentation.paths:
            p0, p1, p2, p3 = path.controls
            dash = "" if path.closed else ' stroke-dasharray="7 4"'
            parts.append(
                f'<path d="M {p0.x:.1f},{p0.y:.1f} C {p1.x:.1f},{p1.y:.1f} '
                f'{p2.x:.1f},{p2.y:.1f} {p3.x:.1f},{p3.y:.1f}" fill="none" '
                f'stroke="{accent}" stroke-width="4"{dash}/>'
            )
            if not path.closed:
                for point in (p0, p3):
                    parts.append(
                        f'<circle cx="{point.x:.1f}" cy="{point.y:.1f}" r="5" fill="white" '
                        f'stroke="{accent}" stroke-width="3"/>'
                    )
            parts.append(
                f'<text x="{p1.x:.1f}" y="{float(p1.y - 7.0):.1f}" font-family="sans-serif" '
                f'font-weight="bold" font-size="16" fill="{accent}">{escape(path.name)}</text>'
            )
            word = " · ".join(
                label if exponent == 1 else f"{label}^{exponent}"
                for label, exponent in path.edge_word
            )
            if word:
                parts.append(
                    f'<text x="{p1.x:.1f}" y="{float(p1.y + 10.0):.1f}" font-family="sans-serif" '
                    f'font-size="11" fill="{accent}">{escape(word)}</text>'
                )
        basis = ", ".join(SurfaceAnalyzer().cycle_basis(presentation)) or "empty"
        parts.append(
            f'<text x="16" y="{height - 36}" font-family="sans-serif" font-size="12" '
            f'fill="{ink}">Spanning-forest cycle basis: {escape(basis)}</text>'
        )
        parts.append(
            f'<text x="16" y="{height - 18}" font-family="sans-serif" font-size="13" '
            f'fill="{ink}">Dashed polygon edges are unglued boundary; matching words and '
            "arrows are glued.</text>"
        )
        parts.append("</svg>")
        return PromptData(
            media_type="image/svg+xml",
            content="".join(parts),
            metadata={
                "representation": "directed-polygon-gluing-diagram",
                "polygon_count": len(presentation.polygons),
                "path_count": len(presentation.paths),
                "deterministic_renderer": True,
            },
        )

    @staticmethod
    def _marked_edge(start: Point, end: Point, word: str, ink: str) -> str:
        mx, my = (start.x + end.x) / 2, (start.y + end.y) / 2
        ax, ay = (2 * start.x + end.x) / 3, (2 * start.y + end.y) / 3
        bx, by = (start.x + 2 * end.x) / 3, (start.y + 2 * end.y) / 3
        return (
            f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
            f'stroke="{ink}" stroke-width="2" marker-end="url(#arrow)"/>'
            f'<text x="{mx:.1f}" y="{float(my - 7.0):.1f}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="12" fill="{ink}">{escape(word)}</text>'
        )


PolygonWordRepresentation = SvgGluingDiagramRenderer
