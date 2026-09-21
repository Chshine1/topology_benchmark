from topology_benchmark.domains.surfaces.models import (
    CellularHomology,
    EdgeRef,
    SurfaceFacts,
    SurfacePresentation,
)
from topology_benchmark.domains.surfaces.models.object import OrientedEdge
from topology_benchmark.domains.surfaces.services.surface_basic_topology_analyzer import (
    SurfaceBasicTopologyAnalyzer,
)
from topology_benchmark.domains.surfaces.services.surface_homology_analyzer import (
    SurfaceHomologyAnalyzer,
)
from topology_benchmark.utils.disjoint_set_union import DisjointSetUnion


class SurfaceAnalyzer:
    @staticmethod
    def analyze(surface: SurfacePresentation) -> SurfaceFacts:
        return SurfaceBasicTopologyAnalyzer().analyze(surface)

    @staticmethod
    def cellular_homology(surface: SurfacePresentation) -> CellularHomology:
        return SurfaceHomologyAnalyzer(SurfaceBasicTopologyAnalyzer()).cellular_homology(surface)

    @staticmethod
    def path_is_cycle(surface: SurfacePresentation, path: tuple[OrientedEdge, ...]) -> bool:
        quotient = surface.quotient_vertices()
        return surface.path_endpoint(path[0], True, quotient) == surface.path_endpoint(
            path[-1], False, quotient
        )

    def path_representative(
        self, surface: SurfacePresentation, path: SurfacePath
    ) -> tuple[int, ...]:
        if not self.path_is_cycle(surface, path):
            raise ValueError("an open path has no homology class")
        homology = self.cellular_homology(surface)
        _, occurrence = self._quotient_edges(surface)
        chord_indices = [
            homology.edge_basis.index(self._parse_edge_name(name)) for name in homology.cycle_basis
        ]
        chain = [0] * len(homology.edge_basis)
        for directed in path.edges:
            index, sign = occurrence[directed.edge]
            chain[index] += sign if directed.forward else -sign
        return tuple(chain[index] for index in chord_indices)

    def path_homology_class(
        self, surface: SurfacePresentation, path: SurfacePath
    ) -> tuple[int, ...]:
        """Smith-basis coordinates, with torsion coordinates reduced modulo their orders."""

        cycle = self.path_representative(surface, path)
        homology = self.cellular_homology(surface)
        smith = tuple(
            sum(row[column] * cycle[column] for column in range(len(cycle)))
            for row in homology.smith_coordinate_map
        )
        return tuple(
            0 if diagonal == 1 else value % diagonal if diagonal > 1 else value
            for value, diagonal in zip(
                smith,
                (
                    *homology.smith_diagonal,
                    *(0 for _ in range(len(smith) - len(homology.smith_diagonal))),
                ),
                strict=True,
            )
        )

    @staticmethod
    def _tree_path(
        start: int, end: int, adjacency: dict[int, list[tuple[int, int, bool]]]
    ) -> tuple[tuple[int, bool], ...]:
        if start == end:
            return ()
        previous: dict[int, tuple[int, int, bool]] = {}
        pending = [start]
        reached = {start}
        while pending:
            current = pending.pop()
            if current == end:
                break
            for neighbor, edge_index, forward in adjacency[current]:
                if neighbor in reached:
                    continue
                reached.add(neighbor)
                previous[neighbor] = (current, edge_index, forward)
                pending.append(neighbor)
        if end not in reached:
            raise ValueError("cycle endpoints are disconnected in the spanning forest")
        result: list[tuple[int, bool]] = []
        current = end
        while current != start:
            parent, edge_index, forward = previous[current]
            result.append((edge_index, forward))
            current = parent
        result.reverse()
        return tuple(result)

    def _fundamental_cycle_chains(
        self, surface: SurfacePresentation
    ) -> tuple[tuple[int, ...], ...]:
        """The graph-cycle basis expressed as oriented quotient-edge chains."""

        vertex_dsu, _ = surface.quotient
        edge_basis, _ = self._quotient_edges(surface)
        vertex_roots = sorted(
            {vertex_dsu.find(vertex) for vertex in range(surface.vertex_offsets[-1])}
        )
        vertex_index = {root: index for index, root in enumerate(vertex_roots)}
        endpoints = []
        for edge in edge_basis:
            start, end = surface.native_edge_vertices(edge)
            endpoints.append(
                (vertex_index[vertex_dsu.find(start)], vertex_index[vertex_dsu.find(end)])
            )

        forest = DisjointSetUnion(len(vertex_roots))
        adjacency: dict[int, list[tuple[int, int, bool]]] = {
            vertex: [] for vertex in range(len(vertex_roots))
        }
        chords: list[tuple[int, int, int]] = []
        for edge_index, (start, end) in enumerate(endpoints):
            if forest.union(start, end):
                adjacency[start].append((end, edge_index, True))
                adjacency[end].append((start, edge_index, False))
            else:
                chords.append((edge_index, start, end))

        component_root = {
            component: min(
                vertex for vertex in range(len(vertex_roots)) if forest.find(vertex) == component
            )
            for component in {forest.find(vertex) for vertex in range(len(vertex_roots))}
        }

        chains = []
        for edge_index, start, end in chords:
            root = component_root[forest.find(start)]
            edges = (
                *self._tree_path(root, start, adjacency),
                (edge_index, True),
                *self._tree_path(end, root, adjacency),
            )
            chain = [0] * len(edge_basis)
            for quotient_edge, forward in edges:
                chain[quotient_edge] += 1 if forward else -1
            chains.append(tuple(chain))
        return tuple(chains)

    def h1_generators(
        self, surface: SurfacePresentation
    ) -> tuple[tuple[tuple[int, ...], int | None], ...]:
        """Smith generators as cycle-basis coefficients, paired with finite orders."""

        homology = self.cellular_homology(surface)
        diagonal = (
            *homology.smith_diagonal,
            *(0 for _ in range(len(homology.smith_basis) - len(homology.smith_diagonal))),
        )
        return tuple(
            (generator, value if value > 1 else None)
            for generator, value in zip(homology.smith_basis, diagonal, strict=True)
            if value != 1
        )

    def h1_edge_generators(
        self, surface: SurfacePresentation
    ) -> tuple[tuple[tuple[int, ...], int | None], ...]:
        """Smith generators as oriented quotient-edge chains, paired with finite orders."""

        homology = self.cellular_homology(surface)
        cycle_chains = self._fundamental_cycle_chains(surface)
        return tuple(
            (
                tuple(
                    sum(
                        cycle_coefficient * cycle_chains[cycle][edge]
                        for cycle, cycle_coefficient in enumerate(generator)
                    )
                    for edge in range(len(homology.edge_basis))
                ),
                order,
            )
            for generator, order in self.h1_generators(surface)
        )

    def path_homology_coefficients(
        self, surface: SurfacePresentation, path: SurfacePath
    ) -> tuple[int, ...]:
        """Path coordinates after omitting Smith factors equal to one."""

        homology = self.cellular_homology(surface)
        coordinates = self.path_homology_class(surface, path)
        diagonal = (
            *homology.smith_diagonal,
            *(0 for _ in range(len(coordinates) - len(homology.smith_diagonal))),
        )
        return tuple(
            coordinate
            for coordinate, value in zip(coordinates, diagonal, strict=True)
            if value != 1
        )

    @staticmethod
    def _quotient_edges(
        surface: SurfacePresentation,
    ) -> tuple[list[EdgeRef], dict[EdgeRef, tuple[int, int]]]:
        paired: dict[EdgeRef, tuple[EdgeRef, int]] = {}
        for gluing in surface.gluings:
            sign = 1 if gluing.same_direction else -1
            paired[gluing.first_edge] = (gluing.second_edge, sign)
            paired[gluing.second_edge] = (gluing.first_edge, sign)
        basis: list[EdgeRef] = []
        occurrence: dict[EdgeRef, tuple[int, int]] = {}
        for p, polygon in enumerate(surface.polygons):
            for side in range(polygon.sides):
                edge = EdgeRef(p, side)
                if edge in occurrence:
                    continue
                index = len(basis)
                basis.append(edge)
                occurrence[edge] = (index, 1)
                if edge in paired:
                    mate, sign = paired[edge]
                    occurrence[mate] = (index, sign)
        return basis, occurrence

    @staticmethod
    def _edge_name(edge: EdgeRef) -> str:
        return f"e{edge.polygon}:{edge.edge}"

    @staticmethod
    def _parse_edge_name(name: str) -> EdgeRef:
        polygon, edge = name[1:].split(":")
        return EdgeRef(int(polygon), int(edge))
