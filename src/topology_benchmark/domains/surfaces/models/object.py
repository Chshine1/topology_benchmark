from attrs import field, frozen

from topology_benchmark.core.structures.disjoint_set import DisjointSet
from topology_benchmark.core.validation import nonblank, nonempty, number_range


@frozen
class Polygon:
    name: str
    sides: int = field(
        validator=number_range(
            minimum=3,
            message="a polygon needs at least three edges",
        )
    )


@frozen(order=True)
class EdgeRef:
    """Side ``edge`` of ``SurfacePresentation.polygons[polygon]``.

    Both indices are zero-based. Side ``i`` runs from vertex ``i`` to vertex
    ``(i + 1) % sides``.
    """

    polygon: int
    edge: int


@frozen
class OrientedEdge:
    """A side traversal; ``forward`` selects ``i -> i + 1`` or its reverse."""

    edge: EdgeRef
    forward: bool = True


@frozen
class EdgeGluing:
    """Identification of two sides.

    ``same_direction`` pairs their two starts and their two ends; otherwise it
    pairs each start with the other end.
    """

    first: EdgeRef
    second: EdgeRef

    label: str = field(validator=nonblank("a gluing label cannot be empty"))
    same_direction: bool = False

    def __attrs_post_init__(self) -> None:
        if self.first == self.second:
            raise ValueError("an edge cannot be glued to itself")


@frozen
class SurfacePath:
    """An edge walk whose consecutive endpoints agree after gluing."""

    name: str = field(validator=nonblank("a path name cannot be empty"))
    edges: tuple[OrientedEdge, ...] = field(
        validator=nonempty("a path needs at least one directed edge")
    )


@frozen
class SurfacePresentation:
    """Polygons whose paired sides are identified; unpaired sides form the boundary."""

    polygons: tuple[Polygon, ...] = field(
        validator=nonempty("a surface presentation needs at least one polygon")
    )
    gluings: tuple[EdgeGluing, ...]
    paths: tuple[SurfacePath, ...] = ()
    edge_labels: tuple[tuple[EdgeRef, str], ...] = ()

    def __attrs_post_init__(self) -> None:
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

        labelled_edges: set[EdgeRef] = set()
        display_labels: set[str] = set()
        for edge, label in self.edge_labels:
            self._validate_edge(edge)
            if edge in labelled_edges:
                raise ValueError("each edge can have at most one display label")
            if not label.strip() or label in display_labels:
                raise ValueError("display edge labels must be nonblank and unique")
            labelled_edges.add(edge)
            display_labels.add(label)

        quotient_vertices = self.quotient_vertices()
        for path in self.paths:
            for directed in path.edges:
                self._validate_edge(directed.edge)
            for first, second in zip(path.edges, path.edges[1:], strict=False):
                if self.path_endpoint(first, False, quotient_vertices) != self.path_endpoint(
                    second, True, quotient_vertices
                ):
                    raise ValueError("neighboring path edges are not connected in the quotient")

    def _validate_edge(self, edge: EdgeRef) -> None:
        if not 0 <= edge.polygon < len(self.polygons):
            raise ValueError("edge references an unknown polygon")
        if not 0 <= edge.edge < self.polygons[edge.polygon].sides:
            raise ValueError("edge references an unknown polygon side")

    def vertex_offsets(self) -> tuple[int, ...]:
        """Return offsets mapping ``(polygon, vertex)`` to one global vertex index."""
        result = [0]
        for polygon in self.polygons:
            result.append(result[-1] + polygon.sides)
        return tuple(result)

    def quotient_vertices(self) -> tuple[int, ...]:
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
        """Return the side's start and end as pre-gluing global vertex indices."""
        offsets = offsets or self.vertex_offsets()
        start = offsets[edge.polygon] + edge.edge
        end = offsets[edge.polygon] + ((edge.edge + 1) % self.polygons[edge.polygon].sides)
        return start, end

    def path_endpoint(
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
    def is_closed(self) -> bool:
        return not self.unglued_edges
