"""Seeded generators for polygon quotients and boundary-gluing quotient maps."""

import math
from dataclasses import dataclass
from random import Random

from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.domains.surfaces.analysis import SurfaceAnalyzer
from topology_benchmark.domains.surfaces.models import (
    BoundaryGluingMorphism,
    DirectedEdgeMark,
    EdgeIdentification,
    EdgeRef,
    PathDrawing,
    Point,
    Polygon,
    PolygonAttachmentMorphism,
    SurfaceMorphism,
    SurfacePresentation,
)
from topology_benchmark.domains.surfaces.ports import SurfaceGenerator, SurfaceMorphismGenerator


@dataclass(frozen=True, slots=True)
class _ComponentRecipe:
    """Ephemeral generation parameters, never stored as surface ground truth."""

    orientable: bool
    genus: int
    boundary: int


class RandomSurfacePresentationGenerator(SurfaceGenerator):
    def generate(self, request: GenerationRequest, rng: Random) -> SurfacePresentation:
        count = rng.randint(1, min(3, 1 + request.difficulty // 4))
        recipes = tuple(self._recipe(request, rng) for _ in range(count))
        polygons: list[Polygon] = []
        marks: list[DirectedEdgeMark] = []
        polygon_components: list[int] = []
        for component, recipe in enumerate(recipes):
            specs = self._edge_specs(recipe, component)
            if not specs:  # two discs with their complete rims glued present S^2
                first = len(polygons)
                polygons.extend(
                    (
                        self._polygon("P", 3, first, rng),
                        self._polygon("Q", 3, first + 1, rng),
                    )
                )
                polygon_components.extend((component, component))
                for edge in range(3):
                    word = f"s{component}_{edge}"
                    marks.extend(
                        (
                            DirectedEdgeMark(EdgeRef(first, edge), word, True),
                            DirectedEdgeMark(EdgeRef(first + 1, 2 - edge), word, True),
                        )
                    )
                continue
            polygon_index = len(polygons)
            polygons.append(self._polygon(chr(80 + component), len(specs), polygon_index, rng))
            polygon_components.append(component)
            for edge, spec in enumerate(specs):
                if spec is not None:
                    word, forward = spec
                    marks.append(DirectedEdgeMark(EdgeRef(polygon_index, edge), word, forward))

        base = SurfacePresentation(
            tuple(polygons), tuple(marks), palette=rng.choice(("ink", "ocean", "clay"))
        )
        paths = self._paths(base, polygon_components, request, rng)
        result = SurfacePresentation(base.polygons, base.marks, paths, base.palette)
        SurfaceAnalyzer().analyze(result)  # reject generator bugs at the data boundary
        return result

    @staticmethod
    def _recipe(request: GenerationRequest, rng: Random) -> _ComponentRecipe:
        orientable = rng.choice((True, False))
        genus = rng.randint(0 if orientable else 1, max(1, 1 + request.difficulty // 3))
        boundary = rng.randint(0, min(3, 1 + request.difficulty // 3))
        return _ComponentRecipe(orientable, genus, boundary)

    @staticmethod
    def _edge_specs(recipe: _ComponentRecipe, component: int) -> list[tuple[str, bool] | None]:
        prefix = f"c{component}"
        specs: list[tuple[str, bool] | None] = []
        if recipe.orientable:
            for handle in range(recipe.genus):
                a, b = f"{prefix}a{handle + 1}", f"{prefix}b{handle + 1}"
                specs.extend(((a, True), (b, True), (a, False), (b, False)))
        else:
            for crosscap in range(recipe.genus):
                word = f"{prefix}x{crosscap + 1}"
                specs.extend(((word, True), (word, True)))
        for boundary in range(max(0, recipe.boundary - 1)):
            word = f"{prefix}d{boundary + 1}"
            specs.extend(((word, True), None, (word, False)))
        if recipe.boundary:
            specs.append(None)
        if specs and len(specs) < 3:
            word = f"{prefix}q"
            specs.extend(((word, True), (word, False)))
        return specs

    @staticmethod
    def _polygon(name: str, sides: int, slot: int, rng: Random) -> Polygon:
        radius = min(105.0, 48.0 + sides * 5.0)
        center_x, center_y = 145.0 + 245.0 * (slot % 3), 145.0 + 235.0 * (slot // 3)
        phase = rng.uniform(-math.pi, math.pi)
        return Polygon(
            name,
            tuple(
                Point(
                    center_x
                    + radius
                    * rng.uniform(0.86, 1.08)
                    * math.cos(phase + 2 * math.pi * index / sides),
                    center_y
                    + radius
                    * rng.uniform(0.86, 1.08)
                    * math.sin(phase + 2 * math.pi * index / sides),
                )
                for index in range(sides)
            ),
        )

    @staticmethod
    def _paths(
        surface: SurfacePresentation,
        polygon_components: list[int],
        request: GenerationRequest,
        rng: Random,
    ) -> tuple[PathDrawing, ...]:
        result = []
        for index in range(1 if request.difficulty < 4 else 2):
            polygon_index = rng.randrange(len(surface.polygons))
            polygon = surface.polygons[polygon_index]
            component = polygon_components[polygon_index]
            labels = sorted(
                {
                    mark.word
                    for mark in surface.marks
                    if polygon_components[mark.edge.polygon] == component
                    and not mark.word.endswith("q")
                    and not mark.word.startswith("s")
                }
            )
            closed = bool(labels) and rng.random() > 0.22
            word = (
                tuple((label, exponent) for label in labels if (exponent := rng.randint(-2, 2)))
                if closed
                else ()
            )
            cx = sum(point.x for point in polygon.vertices) / len(polygon.vertices)
            cy = sum(point.y for point in polygon.vertices) / len(polygon.vertices)
            start = Point(cx - rng.uniform(22, 48), cy + rng.uniform(-20, 20))
            end = start if closed else Point(cx + rng.uniform(20, 48), cy + rng.uniform(-25, 25))
            result.append(
                PathDrawing(
                    chr(112 + index),
                    polygon_index,
                    (
                        start,
                        Point(cx + rng.uniform(-55, 5), cy - rng.uniform(25, 65)),
                        Point(cx + rng.uniform(5, 55), cy + rng.uniform(25, 65)),
                        end,
                    ),
                    closed,
                    word,
                )
            )
        return tuple(result)


class RandomSurfaceMorphismGenerator(SurfaceMorphismGenerator):
    """Generate inclusion and quotient arrows with their precise construction members."""

    def generate(self, request: GenerationRequest, rng: Random) -> SurfaceMorphism:
        choice = rng.random()
        if request.difficulty >= 4 and choice < 0.34:
            return self._attach_polygon(rng)
        if request.difficulty < 5 or choice < 0.67:
            return self._glue_two_disks(rng, min(7, 3 + request.difficulty // 2))
        return self._close_annulus(rng)

    @staticmethod
    def _attach_polygon(rng: Random) -> PolygonAttachmentMorphism:
        polygon = RandomSurfacePresentationGenerator._polygon("D", 4, 0, rng)
        source = SurfacePresentation((polygon,), (), palette=rng.choice(("ink", "ocean", "clay")))
        edge = rng.randrange(4)
        first = EdgeRef(0, edge)
        a, b = polygon.vertices[edge], polygon.vertices[(edge + 1) % 4]
        midpoint = Point((a.x + b.x) / 2, (a.y + b.y) / 2)
        dx, dy = b.x - a.x, b.y - a.y
        length = max(1.0, math.hypot(dx, dy))
        tip = Point(midpoint.x + 55 * dy / length, midpoint.y - 55 * dx / length)
        triangle = Polygon("A", (b, a, tip))
        attachment = EdgeIdentification(first, EdgeRef(1, 0), "attach", False)
        target = SurfacePresentation(
            (polygon, triangle),
            (
                DirectedEdgeMark(first, "attach", True),
                DirectedEdgeMark(EdgeRef(1, 0), "attach", False),
            ),
            palette=source.palette,
        )
        analyzer = SurfaceAnalyzer()
        analyzer.analyze(source)
        analyzer.analyze(target)
        return PolygonAttachmentMorphism(source, target, attachment, 1)

    @staticmethod
    def _glue_two_disks(rng: Random, sides: int) -> BoundaryGluingMorphism:
        polygons = (
            RandomSurfacePresentationGenerator._polygon("D1", sides, 0, rng),
            RandomSurfacePresentationGenerator._polygon("D2", sides, 1, rng),
        )
        source = SurfacePresentation(polygons, (), palette=rng.choice(("ink", "ocean", "clay")))
        identifications = tuple(
            EdgeIdentification(EdgeRef(0, edge), EdgeRef(1, sides - 1 - edge), f"g{edge}", False)
            for edge in range(sides)
        )
        return RandomSurfaceMorphismGenerator._build(source, identifications)

    @staticmethod
    def _close_annulus(rng: Random) -> BoundaryGluingMorphism:
        polygon = RandomSurfacePresentationGenerator._polygon("C", 4, 0, rng)
        source = SurfacePresentation(
            (polygon,),
            (
                DirectedEdgeMark(EdgeRef(0, 0), "a", True),
                DirectedEdgeMark(EdgeRef(0, 2), "a", False),
            ),
            palette=rng.choice(("ink", "ocean", "clay")),
        )
        same_direction = rng.choice((True, False))
        identification = EdgeIdentification(
            EdgeRef(0, 1), EdgeRef(0, 3), "boundary", same_direction
        )
        return RandomSurfaceMorphismGenerator._build(source, (identification,))

    @staticmethod
    def _build(
        source: SurfacePresentation, identifications: tuple[EdgeIdentification, ...]
    ) -> BoundaryGluingMorphism:
        additions = tuple(
            mark
            for gluing in identifications
            for mark in (
                DirectedEdgeMark(gluing.first, gluing.word, True),
                DirectedEdgeMark(gluing.second, gluing.word, gluing.same_direction),
            )
        )
        target = SurfacePresentation(
            source.polygons, (*source.marks, *additions), source.paths, source.palette
        )
        analyzer = SurfaceAnalyzer()
        analyzer.analyze(source)
        analyzer.analyze(target)
        return BoundaryGluingMorphism(source, target, identifications)
