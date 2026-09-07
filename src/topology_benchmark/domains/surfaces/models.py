"""Combinatorial surface objects and their deterministic drawing parameters."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Polygon:
    """A closed 2-cell whose vertices also parameterise its drawing."""

    name: str
    vertices: tuple[Point, ...]

    def __post_init__(self) -> None:
        if len(self.vertices) < 3:
            raise ValueError("a polygon needs at least three vertices")


@dataclass(frozen=True, slots=True, order=True)
class EdgeRef:
    polygon: int
    edge: int


@dataclass(frozen=True, slots=True)
class DirectedEdgeMark:
    """Equal words identify two edges in their indicated arrow directions."""

    edge: EdgeRef
    word: str
    forward: bool


@dataclass(frozen=True, slots=True)
class PathDrawing:
    """A displayed path; its signed edge word determines its cellular 1-chain."""

    name: str
    polygon: int
    controls: tuple[Point, Point, Point, Point]
    closed: bool
    edge_word: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True, slots=True)
class SurfacePresentation:
    """A compact surface presented as a quotient of finitely many polygons.

    This is the sole source of mathematical truth. Geometry, palette, and Bezier
    controls are representation parameters stored on the same generated object.
    """

    polygons: tuple[Polygon, ...]
    marks: tuple[DirectedEdgeMark, ...]
    paths: tuple[PathDrawing, ...] = ()
    palette: str = "ink"

    def __post_init__(self) -> None:
        if not self.polygons:
            raise ValueError("a surface presentation needs at least one polygon")
        occupied: set[EdgeRef] = set()
        counts: dict[str, int] = {}
        for mark in self.marks:
            self._validate_edge(mark.edge)
            if mark.edge in occupied:
                raise ValueError("an edge can carry at most one gluing mark")
            occupied.add(mark.edge)
            counts[mark.word] = counts.get(mark.word, 0) + 1
        if any(count != 2 for count in counts.values()):
            raise ValueError("every gluing word must occur exactly twice")
        for path in self.paths:
            if not 0 <= path.polygon < len(self.polygons):
                raise ValueError("path references an unknown polygon")
            if any(word not in counts for word, _ in path.edge_word):
                raise ValueError("path word references an unknown glued edge")

    def _validate_edge(self, edge: EdgeRef) -> None:
        if not 0 <= edge.polygon < len(self.polygons):
            raise ValueError("edge mark references an unknown polygon")
        if not 0 <= edge.edge < len(self.polygons[edge.polygon].vertices):
            raise ValueError("edge mark references an unknown edge")

    @property
    def unmarked_edges(self) -> tuple[EdgeRef, ...]:
        marked = {mark.edge for mark in self.marks}
        return tuple(
            EdgeRef(polygon_index, edge)
            for polygon_index, polygon in enumerate(self.polygons)
            for edge in range(len(polygon.vertices))
            if EdgeRef(polygon_index, edge) not in marked
        )


@dataclass(frozen=True, slots=True)
class EdgeIdentification:
    """One new equivalence imposed by a quotient morphism."""

    first: EdgeRef
    second: EdgeRef
    word: str
    same_direction: bool


@dataclass(frozen=True, slots=True)
class BoundaryGluingMorphism:
    """The quotient map obtained by identifying complete boundary edges."""

    source: SurfacePresentation
    target: SurfacePresentation
    identifications: tuple[EdgeIdentification, ...]

    @property
    def name(self) -> str:
        return "boundary-gluing-quotient"

    def __post_init__(self) -> None:
        if not self.identifications:
            raise ValueError("a boundary gluing needs at least one identification")
        available = set(self.source.unmarked_edges)
        used: set[EdgeRef] = set()
        for gluing in self.identifications:
            if gluing.first not in available or gluing.second not in available:
                raise ValueError("a boundary gluing must use unmarked source edges")
            if gluing.first == gluing.second or gluing.first in used or gluing.second in used:
                raise ValueError("new edge identifications must be disjoint")
            used.update((gluing.first, gluing.second))
        expected_additions = {
            mark
            for gluing in self.identifications
            for mark in (
                DirectedEdgeMark(gluing.first, gluing.word, True),
                DirectedEdgeMark(gluing.second, gluing.word, gluing.same_direction),
            )
        }
        if (
            self.target.polygons != self.source.polygons
            or self.target.paths != self.source.paths
            or self.target.palette != self.source.palette
            or set(self.target.marks) != {*self.source.marks, *expected_additions}
        ):
            raise ValueError("target is not the quotient specified by the identifications")


@dataclass(frozen=True, slots=True)
class PolygonAttachmentMorphism:
    """The inclusion after attaching a new polygon along one boundary edge."""

    source: SurfacePresentation
    target: SurfacePresentation
    attachment: EdgeIdentification
    new_polygon: int

    @property
    def name(self) -> str:
        return "polygon-attachment-inclusion"

    @property
    def identifications(self) -> tuple[EdgeIdentification, ...]:
        return (self.attachment,)

    def __post_init__(self) -> None:
        if self.attachment.first not in self.source.unmarked_edges:
            raise ValueError("an attachment must use an unmarked source edge")
        if self.new_polygon != len(self.source.polygons):
            raise ValueError("the attached polygon must be new")
        if self.attachment.second.polygon != self.new_polygon:
            raise ValueError("attachment must identify an edge of the new polygon")
        expected_marks = {
            *self.source.marks,
            DirectedEdgeMark(self.attachment.first, self.attachment.word, True),
            DirectedEdgeMark(
                self.attachment.second,
                self.attachment.word,
                self.attachment.same_direction,
            ),
        }
        if (
            self.target.polygons[:-1] != self.source.polygons
            or self.target.paths != self.source.paths
            or self.target.palette != self.source.palette
            or set(self.target.marks) != expected_marks
        ):
            raise ValueError("target is not the declared polygon attachment")


type SurfaceMorphism = BoundaryGluingMorphism | PolygonAttachmentMorphism
