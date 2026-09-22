from topology_benchmark.domains.surfaces.models.fact import SurfaceQuotient
from topology_benchmark.domains.surfaces.models.object import SurfacePresentation
from topology_benchmark.utils.disjoint_set_union import (
    DisjointSetUnion,
    OrientedDisjointSetUnion,
    FrozenDisjointSetUnion,
    FrozenOrientedDisjointSetUnion,
)


class SurfaceQuotientAnalyzer:
    def __init__(self, surface: SurfacePresentation):
        self._surface = surface

    def get_quotient(self) -> SurfaceQuotient:
        surface = self._surface
        quotient_vertices = DisjointSetUnion(surface.vertex_offsets[-1])
        quotient_edges = OrientedDisjointSetUnion(
            sum(polygon.sides for polygon in surface.polygons)
        )
        connected_components = DisjointSetUnion(len(surface.polygons))
        for gluing in surface.gluings:
            connected_components.union(
                gluing.first_edge.polygon_index, gluing.second_edge.polygon_index
            )
            a0, a1 = surface.native_edge_vertices(gluing.first_edge)
            b0, b1 = surface.native_edge_vertices(gluing.second_edge)
            if gluing.same_direction:
                quotient_vertices.union(a0, b0)
                quotient_vertices.union(a1, b1)
                quotient_edges.union(a0, b0, 1)
            else:
                quotient_vertices.union(a0, b1)
                quotient_vertices.union(a1, b0)
                quotient_edges.union(a0, b0, -1)

        frozen_vertices = FrozenDisjointSetUnion.from_mutable(quotient_vertices)
        frozen_edges = FrozenOrientedDisjointSetUnion.from_mutable(quotient_edges)
        return SurfaceQuotient(
            vertices=frozen_vertices,
            vertex_representatives=tuple(
                sorted(
                    {frozen_vertices.find(vertex) for vertex in range(surface.vertex_offsets[-1])}
                )
            ),
            edges=frozen_edges,
            edge_representatives=tuple(
                sorted(
                    {
                        frozen_edges.find(edge)[0]
                        for edge in range(self._surface.vertex_offsets[-1])
                    },
                )
            ),
            components=FrozenDisjointSetUnion.from_mutable(connected_components),
        )
