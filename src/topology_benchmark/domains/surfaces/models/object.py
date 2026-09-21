from bisect import bisect_right

from topology_benchmark.utils.disjoint_set_union import OrientedDisjointSetUnion
from functools import cached_property
from attrs import field, frozen

from topology_benchmark.core.validation import nonempty, number_range
from topology_benchmark.utils.disjoint_set_union import DisjointSetUnion


@frozen
class Polygon:
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

    polygon_index: int
    starting_vertex: int


@frozen
class OrientedEdge:
    """A side traversal; ``forward`` selects ``i -> i + 1`` or its reverse."""

    edge: EdgeRef
    forward: bool


@frozen
class EdgeGluing:
    """Identification of two sides.

    ``same_direction`` pairs their two starts and their two ends; otherwise it
    pairs each start with the other end.
    """

    first_edge: EdgeRef
    second_edge: EdgeRef

    same_direction: bool

    def __attrs_post_init__(self) -> None:
        if self.first_edge == self.second_edge:
            raise ValueError("an edge cannot be glued to itself")


@frozen
class SurfacePresentation:
    """Polygons whose paired sides are identified; unpaired sides form the boundary."""

    polygons: tuple[Polygon, ...] = field(
        validator=nonempty("a surface presentation needs at least one polygon")
    )
    gluings: tuple[EdgeGluing, ...]
    paths: tuple[tuple[OrientedEdge, ...], ...]

    def __attrs_post_init__(self) -> None:
        glued_edges: set[EdgeRef] = set()
        for gluing in self.gluings:
            self._validate_edge(gluing.first_edge)
            self._validate_edge(gluing.second_edge)
            if gluing.first_edge in glued_edges or gluing.second_edge in glued_edges:
                raise ValueError("each edge can be glued at most once")
            glued_edges.update((gluing.first_edge, gluing.second_edge))

        quotient_vertices = self.quotient_vertices()
        for path in self.paths:
            for directed_edge in path:
                self._validate_edge(directed_edge.edge)
            for first, second in zip(path, path[1:], strict=False):
                if self.path_endpoint(first, False, quotient_vertices) != self.path_endpoint(
                    second, True, quotient_vertices
                ):
                    raise ValueError("neighboring path edges are not connected in the quotient")

    def _validate_edge(self, edge: EdgeRef) -> None:
        if not 0 <= edge.polygon_index < len(self.polygons):
            raise ValueError("edge references an unknown polygon")
        if not 0 <= edge.starting_vertex < self.polygons[edge.polygon_index].sides:
            raise ValueError("edge references an unknown polygon side")

    @cached_property
    def quotient(self) -> tuple[DisjointSetUnion, OrientedDisjointSetUnion, DisjointSetUnion]:
        quotient_vertices = DisjointSetUnion(self.vertex_offsets[-1])
        quotient_edges = OrientedDisjointSetUnion(sum(polygon.sides for polygon in self.polygons))
        connected_components = DisjointSetUnion(len(self.polygons))
        for gluing in self.gluings:
            connected_components.union(
                gluing.first_edge.polygon_index, gluing.second_edge.polygon_index
            )
            a0, a1 = self.native_edge_vertices(gluing.first_edge)
            b0, b1 = self.native_edge_vertices(gluing.second_edge)
            if gluing.same_direction:
                quotient_vertices.union(a0, b0)
                quotient_vertices.union(a1, b1)
                quotient_edges.union(a0, b0, 1)
            else:
                quotient_vertices.union(a0, b1)
                quotient_vertices.union(a1, b0)
                quotient_edges.union(a0, b0, -1)
        return quotient_vertices, quotient_edges, connected_components

    @cached_property
    def vertex_offsets(self) -> tuple[int, ...]:
        """Return offsets mapping ``(polygon, vertex)`` to one global vertex index."""
        result = [0]
        for polygon in self.polygons:
            result.append(result[-1] + polygon.sides)
        return tuple(result)

    def inverse_native_vertex(self, vertex: int) -> tuple[int, int]:
        offsets = self.vertex_offsets
        if not 0 <= vertex < offsets[-1]:
            raise ValueError("native vertex out of range")

        polygon_index = bisect_right(offsets, vertex) - 1
        local_vertex = vertex - offsets[polygon_index]
        return polygon_index, local_vertex

    def quotient_vertices(self) -> tuple[int, ...]:
        offsets = self.vertex_offsets
        dsu = DisjointSetUnion(offsets[-1])
        for gluing in self.gluings:
            a0, a1 = self.native_edge_vertices(gluing.first_edge)
            b0, b1 = self.native_edge_vertices(gluing.second_edge)
            if gluing.same_direction:
                dsu.union(a0, b0)
                dsu.union(a1, b1)
            else:
                dsu.union(a0, b1)
                dsu.union(a1, b0)
        return tuple(dsu.find(vertex) for vertex in range(offsets[-1]))

    def native_edge_vertices(self, edge: EdgeRef) -> tuple[int, int]:
        """Return the side's start and end as pre-gluing global vertex indices."""
        offsets = self.vertex_offsets
        start = offsets[edge.polygon_index] + edge.starting_vertex
        end = offsets[edge.polygon_index] + (
            (edge.starting_vertex + 1) % self.polygons[edge.polygon_index].sides
        )
        return start, end

    def path_endpoint(
        self, directed: OrientedEdge, start: bool, quotient_vertices: tuple[int, ...]
    ) -> int:
        native_start, native_end = self.native_edge_vertices(directed.edge)
        vertex = native_start if start == directed.forward else native_end
        return quotient_vertices[vertex]

    @cached_property
    def unglued_edges(self) -> tuple[EdgeRef, ...]:
        glued = {
            edge for gluing in self.gluings for edge in (gluing.first_edge, gluing.second_edge)
        }
        return tuple(
            EdgeRef(polygon_index, edge)
            for polygon_index, polygon in enumerate(self.polygons)
            for edge in range(polygon.sides)
            if EdgeRef(polygon_index, edge) not in glued
        )
