from topology_benchmark.core.structures.disjoint_set import DisjointSet
from topology_benchmark.domains.surfaces.models import (
    CellularHomology,
    ComponentFacts,
    EdgeGluing,
    EdgeRef,
    SurfaceFacts,
    SurfacePath,
    SurfacePresentation,
)
from topology_benchmark.domains.surfaces.services.integer_linear_algebra import (
    smith_normal_form,
    unimodular_inverse,
)


class SurfaceAnalyzer:
    def analyze(self, surface: SurfacePresentation) -> SurfaceFacts:
        offsets, vertex_dsu, polygon_dsu = self._quotient(surface)
        self._validate_vertex_links(surface, vertex_dsu)
        groups: dict[int, list[int]] = {}
        for polygon in range(len(surface.polygons)):
            groups.setdefault(polygon_dsu.find(polygon), []).append(polygon)
        components = tuple(
            sorted(
                (
                    self._component_facts(surface, offsets, vertex_dsu, tuple(group))
                    for group in groups.values()
                ),
                key=lambda facts: facts.polygons[0],
            )
        )
        vertices = {vertex_dsu.find(vertex) for vertex in range(offsets[-1])}
        edges = sum(polygon.sides for polygon in surface.polygons) - len(surface.gluings)
        return SurfaceFacts(components, len(vertices), edges, len(surface.polygons))

    def cellular_homology(self, surface: SurfacePresentation) -> CellularHomology:
        facts = self.analyze(surface)
        offsets, vertex_dsu, _ = self._quotient(surface)
        edge_basis, occurrence = self._quotient_edges(surface)
        vertex_roots = sorted({vertex_dsu.find(vertex) for vertex in range(offsets[-1])})
        vertex_index = {root: index for index, root in enumerate(vertex_roots)}

        endpoints: list[tuple[int, int]] = []
        for edge in edge_basis:
            start, end = surface.native_edge_vertices(edge, offsets)
            endpoints.append(
                (vertex_index[vertex_dsu.find(start)], vertex_index[vertex_dsu.find(end)])
            )

        forest = DisjointSet(len(vertex_roots))
        chords: list[int] = []
        for index, (start, end) in enumerate(endpoints):
            if not forest.union(start, end):
                chords.append(index)
        # In a graph, chord coefficients are coordinates in its fundamental-cycle basis.
        cycle_basis = tuple(self._edge_name(edge_basis[index]) for index in chords)
        relations: list[tuple[int, ...]] = []
        for polygon_index, polygon in enumerate(surface.polygons):
            chain = [0] * len(edge_basis)
            for side in range(polygon.sides):
                quotient_edge, sign = occurrence[EdgeRef(polygon_index, side)]
                chain[quotient_edge] += sign
            relations.append(tuple(chain[index] for index in chords))

        relation_matrix = [list(row) for row in zip(*relations, strict=False)]
        smith, coordinate_map = smith_normal_form(relation_matrix, len(chords))
        inverse_map = unimodular_inverse(coordinate_map)
        smith_basis = tuple(tuple(column) for column in zip(*inverse_map, strict=False))
        nonzero = tuple(value for value in smith if value)
        torsion = tuple(value for value in nonzero if value > 1)
        h1_rank = len(chords) - len(nonzero)
        return CellularHomology(
            tuple(edge_basis),
            cycle_basis,
            tuple(relations),
            smith,
            smith_basis,
            coordinate_map,
            len(facts.components),
            h1_rank,
            torsion,
            sum(c.orientable and c.boundary_components == 0 for c in facts.components),
        )

    @staticmethod
    def path_is_cycle(surface: SurfacePresentation, path: SurfacePath) -> bool:
        quotient = surface.quotient_vertices()
        return surface.path_endpoint(path.edges[0], True, quotient) == surface.path_endpoint(
            path.edges[-1], False, quotient
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

    def cycle_basis(self, surface: SurfacePresentation) -> tuple[str, ...]:
        return self.cellular_homology(surface).cycle_basis

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

        offsets, vertex_dsu, _ = self._quotient(surface)
        edge_basis, _ = self._quotient_edges(surface)
        vertex_roots = sorted({vertex_dsu.find(vertex) for vertex in range(offsets[-1])})
        vertex_index = {root: index for index, root in enumerate(vertex_roots)}
        endpoints = []
        for edge in edge_basis:
            start, end = surface.native_edge_vertices(edge, offsets)
            endpoints.append(
                (vertex_index[vertex_dsu.find(start)], vertex_index[vertex_dsu.find(end)])
            )

        forest = DisjointSet(len(vertex_roots))
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

    def _component_facts(
        self,
        surface: SurfacePresentation,
        offsets: tuple[int, ...],
        vertex_dsu: DisjointSet,
        polygons: tuple[int, ...],
    ) -> ComponentFacts:
        polygon_set = set(polygons)
        vertices = {
            vertex_dsu.find(offsets[p] + v)
            for p in polygons
            for v in range(surface.polygons[p].sides)
        }
        boundary = [edge for edge in surface.unglued_edges if edge.polygon in polygon_set]
        boundary_count = self._boundary_count(surface, offsets, vertex_dsu, boundary)
        paired = sum(gluing.first.polygon in polygon_set for gluing in surface.gluings)
        chi = len(vertices) - paired - len(boundary) + len(polygons)
        orientable = self._is_orientable(surface.gluings, polygon_set)
        numerator = 2 - boundary_count - chi
        if orientable:
            if numerator < 0 or numerator % 2:
                raise ValueError("edge quotient is not a compact orientable surface")
            genus = numerator // 2
        else:
            if numerator <= 0:
                raise ValueError("edge quotient is not a compact non-orientable surface")
            genus = numerator
        return ComponentFacts(polygons, orientable, chi, boundary_count, genus)

    @staticmethod
    def _quotient(surface: SurfacePresentation) -> tuple[tuple[int, ...], DisjointSet, DisjointSet]:
        offsets = surface.vertex_offsets()
        vertices = DisjointSet(offsets[-1])
        polygons = DisjointSet(len(surface.polygons))
        for gluing in surface.gluings:
            polygons.union(gluing.first.polygon, gluing.second.polygon)
            a0, a1 = surface.native_edge_vertices(gluing.first, offsets)
            b0, b1 = surface.native_edge_vertices(gluing.second, offsets)
            if gluing.same_direction:
                vertices.union(a0, b0)
                vertices.union(a1, b1)
            else:
                vertices.union(a0, b1)
                vertices.union(a1, b0)
        return offsets, vertices, polygons

    @staticmethod
    def _boundary_count(
        surface: SurfacePresentation,
        offsets: tuple[int, ...],
        vertices: DisjointSet,
        edges: list[EdgeRef],
    ) -> int:
        if not edges:
            return 0
        roots = sorted(
            {
                vertices.find(v)
                for edge in edges
                for v in surface.native_edge_vertices(edge, offsets)
            }
        )
        index = {root: i for i, root in enumerate(roots)}
        components = DisjointSet(len(roots))
        degree = dict.fromkeys(roots, 0)
        for edge in edges:
            a, b = (vertices.find(v) for v in surface.native_edge_vertices(edge, offsets))
            components.union(index[a], index[b])
            degree[a] += 1
            degree[b] += 1
        if any(value != 2 for value in degree.values()):
            raise ValueError("unglued edges do not form boundary circles")
        return len({components.find(i) for i in range(len(roots))})

    @staticmethod
    def _is_orientable(gluings: tuple[EdgeGluing, ...], polygons: set[int]) -> bool:
        adjacency: dict[int, list[tuple[int, int]]] = {p: [] for p in polygons}
        for gluing in gluings:
            if gluing.first.polygon not in polygons:
                continue
            relation = -1 if gluing.same_direction else 1
            adjacency[gluing.first.polygon].append((gluing.second.polygon, relation))
            adjacency[gluing.second.polygon].append((gluing.first.polygon, relation))
        signs: dict[int, int] = {}
        for start in polygons:
            if start in signs:
                continue
            signs[start] = 1
            stack = [start]
            while stack:
                current = stack.pop()
                for neighbor, relation in adjacency[current]:
                    required = signs[current] * relation
                    if neighbor in signs and signs[neighbor] != required:
                        return False
                    if neighbor not in signs:
                        signs[neighbor] = required
                        stack.append(neighbor)
        return True

    @staticmethod
    def _validate_vertex_links(surface: SurfacePresentation, vertex_dsu: DisjointSet) -> None:
        offsets = surface.vertex_offsets()
        edge_offsets = [0]
        for polygon in surface.polygons:
            edge_offsets.append(edge_offsets[-1] + polygon.sides)
        links = DisjointSet(2 * edge_offsets[-1])
        for gluing in surface.gluings:
            for at_start in (True, False):
                a = 2 * (edge_offsets[gluing.first.polygon] + gluing.first.edge) + (
                    0 if at_start else 1
                )
                b_start = at_start if gluing.same_direction else not at_start
                b = 2 * (edge_offsets[gluing.second.polygon] + gluing.second.edge) + (
                    0 if b_start else 1
                )
                links.union(a, b)
        by_vertex: dict[int, list[tuple[int, int]]] = {}
        for p, polygon in enumerate(surface.polygons):
            for corner in range(polygon.sides):
                previous = edge_offsets[p] + (corner - 1) % polygon.sides
                following = edge_offsets[p] + corner
                by_vertex.setdefault(vertex_dsu.find(offsets[p] + corner), []).append(
                    (links.find(2 * previous + 1), links.find(2 * following))
                )
        for segments in by_vertex.values():
            adjacency: dict[int, list[int]] = {}
            degree: dict[int, int] = {}
            for a, b in segments:
                adjacency.setdefault(a, []).append(b)
                adjacency.setdefault(b, []).append(a)
                degree[a] = degree.get(a, 0) + 1
                degree[b] = degree.get(b, 0) + 1
            reached = {next(iter(adjacency))}
            stack = list(reached)
            while stack:
                for neighbor in adjacency[stack.pop()]:
                    if neighbor not in reached:
                        reached.add(neighbor)
                        stack.append(neighbor)
            values = sorted(degree.values())
            if len(reached) != len(adjacency) or not (
                all(v == 2 for v in values)
                or (values.count(1) == 2 and all(v in (1, 2) for v in values))
            ):
                raise ValueError("a quotient vertex has a non-manifold link")

    @staticmethod
    def _quotient_edges(
        surface: SurfacePresentation,
    ) -> tuple[list[EdgeRef], dict[EdgeRef, tuple[int, int]]]:
        paired: dict[EdgeRef, tuple[EdgeRef, int]] = {}
        for gluing in surface.gluings:
            sign = 1 if gluing.same_direction else -1
            paired[gluing.first] = (gluing.second, sign)
            paired[gluing.second] = (gluing.first, sign)
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
