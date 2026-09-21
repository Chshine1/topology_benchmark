from topology_benchmark.domains.surfaces.services.surface_basic_topology_analyzer import (
    SurfaceBasicTopologyAnalyzer,
)
from collections import deque
from itertools import groupby
from itertools import tee, chain
from typing import cast

from sympy import Matrix
from sympy.polys.matrices.domainmatrix import DomainMatrix
from sympy.polys.matrices.normalforms import smith_normal_decomp

from topology_benchmark.domains.surfaces.models import (
    CellularHomology,
    EdgeRef,
    SurfacePresentation,
)
from topology_benchmark.domains.surfaces.models.fact import DimensionOneHomologyElement
from topology_benchmark.utils.disjoint_set_union import DisjointSetUnion


class SurfaceHomologyAnalyzer:
    def __init__(self, basic_topology_analyzer: SurfaceBasicTopologyAnalyzer) -> None:
        self._basic_topology_analyzer = basic_topology_analyzer

    def cellular_homology(self, surface: SurfacePresentation) -> CellularHomology:
        facts = self._basic_topology_analyzer.analyze(surface)
        quotient_vertices, quotient_edges, _ = surface.quotient

        vertex_representatives = sorted(
            {quotient_vertices.find(vertex) for vertex in range(surface.vertex_offsets[-1])}
        )
        inv_vertex = {root: index for index, root in enumerate(vertex_representatives)}

        forest = DisjointSetUnion(len(vertex_representatives))

        def compute_endpoints(native_starting_vertex: int) -> tuple[int, int, int]:
            polygon_index, vertex = surface.inverse_native_vertex(native_starting_vertex)
            _, native_ending_vertex = surface.native_edge_vertices(EdgeRef(polygon_index, vertex))
            return (
                native_starting_vertex,
                quotient_vertices.find(native_starting_vertex),
                quotient_vertices.find(native_ending_vertex),
            )

        edge_representatives = map(
            compute_endpoints,
            sorted(
                {quotient_edges.find(edge)[0] for edge in range(surface.vertex_offsets[-1])},
            ),
        )

        tree_iter, chord_iter = tee(
            (
                (forest.union(inv_vertex[start], inv_vertex[end]), representative, start, end)
                for representative, start, end in edge_representatives
            )
        )

        def edge_adj_selector(
            edge: int, start: int, end: int
        ) -> tuple[tuple[int, tuple[int, int, int]], ...]:
            return (start, (end, edge, 1)), (end, (start, edge, -1))

        chords = tuple(chord for connected, chord, _, _ in chord_iter if not connected)

        chord_pos = {chord: i for i, chord in enumerate(chords)}

        partial = Matrix.zeros(len(chords), len(surface.polygons))

        for col, polygon in enumerate(surface.polygons):
            base = surface.vertex_offsets[col]
            for s in range(polygon.sides):
                global_edge = base + s
                rep, sign = quotient_edges.find(global_edge)

                if rep in chord_pos:
                    row = chord_pos[rep]
                    partial[row, col] = partial[row, col] + sign

        normalized, u, v = smith_normal_decomp(partial)

        n, m = partial.rows, partial.cols
        u_inv = u.inv()

        def key_selector(pair: tuple[int, tuple[int, int, int]]) -> int:
            return pair[0]

        tree_adj = dict(
            groupby(
                sorted(
                    chain.from_iterable(
                        (
                            edge_adj_selector(edge, start, end)
                            for connected, edge, start, end in tree_iter
                            if connected
                        )
                    ),
                    key=key_selector,
                ),
                key=key_selector,
            )
        )

        def find_reversed_tree_path(start: int, end: int):
            parent: dict[int, tuple[int | None, tuple[int, int] | None]] = {
                start: (None, None)
            }  # vertex -> (prev_vertex, (edge_rep, sign))
            queue = deque([start])
            while len(queue) > 0:
                u = queue.popleft()
                if u == end:
                    break
                for _, (v, rep, sign) in tree_adj[u]:
                    if v not in parent:
                        parent[v] = (u, (rep, sign))
                        queue.append(v)

            path: list[tuple[int, int]] = []
            cur = end
            while cur != start:
                prev, edge = parent[cur]
                assert prev is not None and edge is not None
                rep, sign = edge
                path.append((rep, -sign))
                cur = prev
            path.reverse()
            return path

        def get_cycle_for_chord(
            chord_with_coefficient: tuple[int, int],
        ) -> tuple[tuple[int, int], ...]:
            chord, coefficient = chord_with_coefficient
            if coefficient == 0:
                return ()
            _, start, end = compute_endpoints(chord)

            def scale_by_coefficient(item: tuple[int, int]) -> tuple[int, int]:
                return item[0], coefficient * item[1]

            return tuple(
                chain(
                    map(scale_by_coefficient, find_reversed_tree_path(start, end)),
                    ((chord, coefficient),),
                )
            )

        h1_basis: list[DimensionOneHomologyElement] = []

        for i in range(n):
            d = 0
            if i < min(normalized.shape):
                d = abs(int(normalized.getitem_sympy(i, i)))
            if d == 1:
                continue
            chord_coordinates: list[int] = cast(DomainMatrix, u_inv[:, i]).to_list_flat()

            def key_sel(pair: tuple[int, int]) -> int:
                return pair[0]

            coefficients = tuple(
                (coefficient, EdgeRef(*surface.inverse_native_vertex(edge)))
                for edge, group in groupby(
                    sorted(
                        chain.from_iterable(
                            map(get_cycle_for_chord, zip(chords, chord_coordinates))
                        ),
                        key=key_sel,
                    ),
                    key=key_sel,
                )
                if (coefficient := sum(v for _, v in group)) != 0
            )

            h1_basis.append(
                DimensionOneHomologyElement(
                    edges_representative=coefficients, order=d if d > 1 else None
                )
            )

        return CellularHomology(
            len(facts.components),
            tuple(h1_basis),
            sum(c.orientable and c.boundary_count == 0 for c in facts.components),
        )
