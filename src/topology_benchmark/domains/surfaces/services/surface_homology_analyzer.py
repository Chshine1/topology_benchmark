from collections import deque
from itertools import groupby
from itertools import tee, chain
from typing import Iterator

from topology_benchmark.domains.surfaces.models import (
    CellularHomology,
    EdgeRef,
    SurfacePresentation,
)
from topology_benchmark.domains.surfaces.services.surface_basic_topology_analyzer import (
    SurfaceBasicTopologyAnalyzer,
)
from topology_benchmark.utils.disjoint_set_union import DisjointSetUnion
from topology_benchmark.utils.integer_linear_algebra import IntegralMatrix
from topology_benchmark.utils.integer_linear_algebra import smith_normal_decomposition


class SurfaceHomologyAnalyzer:
    def __init__(
        self, surface: SurfacePresentation, basic_topology_analyzer: SurfaceBasicTopologyAnalyzer
    ) -> None:
        self._surface = surface
        self._surface_facts = basic_topology_analyzer.analyze(self._surface)

    def compute_cellular_homology(self) -> CellularHomology:
        quotient = self._surface.quotient

        vertex_representatives = sorted(
            {quotient.vertices.find(vertex) for vertex in range(self._surface.vertex_offsets[-1])}
        )
        vertex_pos = {root: index for index, root in enumerate(vertex_representatives)}

        forest = DisjointSetUnion(len(vertex_representatives))

        edge_representatives = sorted(
            {quotient.edges.find(edge)[0] for edge in range(self._surface.vertex_offsets[-1])},
        )

        chord_iter, tree_iter = tee(
            (
                (
                    forest.union(vertex_pos[start_vertex], vertex_pos[end_vertex]),
                    edge_rep,
                    start_vertex,
                    end_vertex,
                )
                for edge_rep, start_vertex, end_vertex in (
                    map(
                        self._compute_endpoints,
                        edge_representatives,
                    )
                )
            )
        )

        chords = tuple(chord for connected, chord, _, _ in chord_iter if not connected)

        chord_pos = {chord: i for i, chord in enumerate(chords)}

        columns = len(self._surface.polygons)
        partial_flat = [0] * (len(chords) * columns)

        for col, polygon in enumerate(self._surface.polygons):
            base = self._surface.vertex_offsets[col]
            for s in range(polygon.sides):
                global_edge = base + s
                rep, sign = quotient.edges.find(global_edge)

                if rep in chord_pos:
                    row = chord_pos[rep]
                    partial_flat[row * columns + col] = partial_flat[row * columns + col] + sign

        partial = IntegralMatrix(tuple(partial_flat), columns=columns)

        normalized, u, _ = smith_normal_decomposition(partial)

        projection, completion = self._compute_chord_cycle_correspondence(
            edge_representatives, chords, self._build_generating_tree_adj(tree_iter)
        )

        return CellularHomology(
            normalized_partial2=normalized,
            chord_base_change=u,
            chord_projection=projection,
            cycle_completion=completion,
        )

    def _compute_endpoints(self, native_starting_vertex: int) -> tuple[int, int, int]:
        quotient_vertices = self._surface.quotient.vertices
        polygon_index, vertex = self._surface.inverse_native_vertex(native_starting_vertex)
        _, native_ending_vertex = self._surface.native_edge_vertices(EdgeRef(polygon_index, vertex))
        return (
            native_starting_vertex,
            quotient_vertices.find(native_starting_vertex),
            quotient_vertices.find(native_ending_vertex),
        )

    @staticmethod
    def _build_generating_tree_adj(
        tree_iter: Iterator[tuple[bool, int, int, int]],
    ) -> dict[int, tuple[tuple[int, int, int], ...]]:
        def key_selector(pair: tuple[int, tuple[int, int, int]]) -> int:
            return pair[0]

        def select_edge_adj(
            edge_rep: int, start_vertex: int, end_vertex: int
        ) -> tuple[tuple[int, tuple[int, int, int]], ...]:
            return (start_vertex, (end_vertex, 1, edge_rep)), (
                end_vertex,
                (start_vertex, -1, edge_rep),
            )

        return {
            vertex: tuple(edge for _, edge in edges)
            for vertex, edges in groupby(
                sorted(
                    chain.from_iterable(
                        (
                            select_edge_adj(edge_rep, start_vertex, end_vertex)
                            for connected, edge_rep, start_vertex, end_vertex in tree_iter
                            if connected
                        )
                    ),
                    key=key_selector,
                ),
                key=key_selector,
            )
        }

    @staticmethod
    def _find_reversed_tree_path(
        tree_adj: dict[int, tuple[tuple[int, int, int], ...]], start_vertex: int, end_vertex: int
    ) -> list[tuple[int, int]]:
        parent: dict[int, tuple[int | None, tuple[int, int] | None]] = {
            start_vertex: (None, None)
        }  # vertex -> (prev_vertex, (edge_rep, sign))
        queue = deque([start_vertex])
        while len(queue) > 0:
            u = queue.popleft()
            if u == end_vertex:
                break
            for v, sign, edge_rep in tree_adj[u]:
                if v not in parent:
                    parent[v] = (u, (edge_rep, sign))
                    queue.append(v)

        path: list[tuple[int, int]] = []
        cur = end_vertex
        while cur != start_vertex:
            prev, edge = parent[cur]
            assert prev is not None and edge is not None
            edge_rep, sign = edge
            path.append((edge_rep, -sign))
            cur = prev
        return path

    def _compute_chord_cycle_correspondence(
        self,
        edge_representatives: list[int],
        chords: tuple[int, ...],
        tree_adj: dict[int, tuple[tuple[int, int, int], ...]],
    ) -> tuple[IntegralMatrix, IntegralMatrix]:
        pos_edge_representatives = {rep: i for i, rep in enumerate(edge_representatives)}
        completion_rows, completion_columns = len(pos_edge_representatives), len(chords)
        completion_flat = [0] * (completion_rows * completion_columns)
        for i in range(completion_columns):
            chord = chords[i]
            _, start_vertex, end_vertex = self._compute_endpoints(chord)
            for edge, coefficient in chain(
                self._find_reversed_tree_path(tree_adj, start_vertex, end_vertex),
                ((chord, 1),),
            ):
                completion_flat[pos_edge_representatives[edge] * completion_columns + i] = (
                    coefficient
                )

        projection_flat = [0] * (completion_columns * completion_rows)
        pos_chords = {chord: i for i, chord in enumerate(chords)}
        for i in range(completion_rows):
            edge_rep = edge_representatives[i]
            pos_chord = pos_chords.get(edge_rep, None)
            if pos_chord is not None:
                projection_flat[pos_chord * completion_rows + i] = 1

        return (
            IntegralMatrix(tuple(projection_flat), columns=completion_rows),
            IntegralMatrix(tuple(completion_flat), columns=completion_columns),
        )
