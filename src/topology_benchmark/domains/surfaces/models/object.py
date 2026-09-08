from dataclasses import dataclass

from topology_benchmark.utils import DisjointSet


@dataclass(frozen=True, slots=True)
class Polygon:
    """A topological disc with cyclically ordered sides."""

    name: str
    sides: int

    def __post_init__(self) -> None:
        if self.sides < 3:
            raise ValueError("a polygon needs at least three edges")


@dataclass(frozen=True, slots=True, order=True)
class EdgeRef:
    polygon: int
    edge: int


@dataclass(frozen=True, slots=True)
class OrientedEdge:
    """A polygon side traversed in (or against) its boundary orientation."""

    edge: EdgeRef
    forward: bool = True


@dataclass(frozen=True, slots=True)
class EdgeGluing:
    """Identification of two complete sides.

    ``same_direction`` maps native start to native start. False maps native
    start to native end. The label is display notation, not mathematical ID.
    """

    first: EdgeRef
    second: EdgeRef
    label: str
    same_direction: bool = False

    def __post_init__(self) -> None:
        if self.first == self.second:
            raise ValueError("an edge cannot be glued to itself")
        if not self.label.strip():
            raise ValueError("a gluing label cannot be empty")


@dataclass(frozen=True, slots=True)
class SurfacePath:
    """A directed edge walk, with adjacency understood in the quotient."""

    name: str
    edges: tuple[OrientedEdge, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a path name cannot be empty")
        if not self.edges:
            raise ValueError("a path needs at least one directed edge")


@dataclass(frozen=True, slots=True, init=False)
class SurfacePresentation:
    """All mathematical data needed to specify a polygonal surface quotient."""

    polygons: tuple[Polygon, ...]
    gluings: tuple[EdgeGluing, ...]
    paths: tuple[SurfacePath, ...] = ()

    def __init__(
        self,
        polygons: tuple[Polygon, ...],
        gluings: tuple[EdgeGluing, ...],
        paths: tuple[SurfacePath, ...] = (),
    ) -> None:
        object.__setattr__(self, "polygons", polygons)
        object.__setattr__(self, "gluings", gluings)
        object.__setattr__(self, "paths", paths)
        self.__post_init__()

    def __post_init__(self) -> None:
        if not self.polygons:
            raise ValueError("a surface presentation needs at least one polygon")
        used: set[EdgeRef] = set()
        labels: set[str] = set()
        for gluing in self.gluings:
            self._validate_edge(gluing.first)
            self._validate_edge(gluing.second)
            if gluing.first in used or gluing.second in used:
                raise ValueError("each edge can be glued at most once")
            if gluing.label in labels:
                raise ValueError("gluing labels must be unique")
            used.update((gluing.first, gluing.second))
            labels.add(gluing.label)

        quotient_vertices = self._quotient_vertices()
        for path in self.paths:
            for directed in path.edges:
                self._validate_edge(directed.edge)
            for first, second in zip(path.edges, path.edges[1:], strict=False):
                if self._path_endpoint(first, False, quotient_vertices) != self._path_endpoint(
                    second, True, quotient_vertices
                ):
                    raise ValueError("neighboring path edges are not connected in the quotient")

    def _validate_edge(self, edge: EdgeRef) -> None:
        if not 0 <= edge.polygon < len(self.polygons):
            raise ValueError("edge references an unknown polygon")
        if not 0 <= edge.edge < self.polygons[edge.polygon].sides:
            raise ValueError("edge references an unknown polygon side")

    def vertex_offsets(self) -> tuple[int, ...]:
        result = [0]
        for polygon in self.polygons:
            result.append(result[-1] + polygon.sides)
        return tuple(result)

    def _quotient_vertices(self) -> tuple[int, ...]:
        offsets = self.vertex_offsets()
        dsu = DisjointSet(offsets[-1])
        for gluing in self.gluings:
            a0, a1 = self.native_edge_vertices(gluing.first, offsets)
            b0, b1 = self.native_edge_vertices(gluing.second, offsets)
            if gluing.same_direction:
                dsu.union(a0, b0)
                dsu.union(a1, b1)
            else:
                dsu.union(a0, b1)
                dsu.union(a1, b0)
        return tuple(dsu.find(vertex) for vertex in range(offsets[-1]))

    def native_edge_vertices(
        self, edge: EdgeRef, offsets: tuple[int, ...] | None = None
    ) -> tuple[int, int]:
        offsets = offsets or self.vertex_offsets()
        start = offsets[edge.polygon] + edge.edge
        end = offsets[edge.polygon] + ((edge.edge + 1) % self.polygons[edge.polygon].sides)
        return start, end

    def _path_endpoint(
        self, directed: OrientedEdge, start: bool, quotient_vertices: tuple[int, ...]
    ) -> int:
        native_start, native_end = self.native_edge_vertices(directed.edge)
        vertex = native_start if start == directed.forward else native_end
        return quotient_vertices[vertex]

    @property
    def unglued_edges(self) -> tuple[EdgeRef, ...]:
        glued = {edge for gluing in self.gluings for edge in (gluing.first, gluing.second)}
        return tuple(
            EdgeRef(polygon_index, edge)
            for polygon_index, polygon in enumerate(self.polygons)
            for edge in range(polygon.sides)
            if EdgeRef(polygon_index, edge) not in glued
        )

    @property
    def unmarked_edges(self) -> tuple[EdgeRef, ...]:
        return self.unglued_edges

    @property
    def is_closed(self) -> bool:
        return not self.unglued_edges
