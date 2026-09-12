from dataclasses import dataclass
from math import gcd

from topology_benchmark.domains.surfaces.models import (
    EdgeGluing,
    EdgeRef,
    SurfacePath,
    SurfacePresentation,
)
from topology_benchmark.utils import DisjointSet


@dataclass(frozen=True, slots=True)
class ComponentFacts:
    polygons: tuple[int, ...]
    orientable: bool
    euler_characteristic: int
    boundary_components: int
    genus: int

    @property
    def first_betti_number(self) -> int:
        if self.orientable:
            return 2 * self.genus + max(0, self.boundary_components - 1)
        return self.genus - 1 + self.boundary_components


@dataclass(frozen=True, slots=True)
class SurfaceFacts:
    components: tuple[ComponentFacts, ...]
    vertex_count: int
    edge_count: int
    face_count: int

    @property
    def euler_characteristic(self) -> int:
        return self.vertex_count - self.edge_count + self.face_count

    @property
    def boundary_components(self) -> int:
        return sum(component.boundary_components for component in self.components)


@dataclass(frozen=True, slots=True)
class CellularHomology:
    """``relations`` are d2 columns in the fundamental ``cycle_basis`` of ker(d1).

    ``smith_coordinate_map`` converts coordinates in that basis to the Smith basis.
    """

    edge_basis: tuple[EdgeRef, ...]
    cycle_basis: tuple[str, ...]
    relations: tuple[tuple[int, ...], ...]
    smith_diagonal: tuple[int, ...]
    smith_basis: tuple[tuple[int, ...], ...]
    smith_coordinate_map: tuple[tuple[int, ...], ...]
    h0_rank: int
    h1_rank: int
    h1_torsion: tuple[int, ...]
    h2_rank: int


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
        smith, coordinate_map = self._smith_normal_form(relation_matrix, len(chords))
        inverse_map = self._unimodular_inverse(coordinate_map)
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

    def path_is_cycle(self, surface: SurfacePresentation, path: SurfacePath) -> bool:
        quotient = surface._quotient_vertices()
        return surface._path_endpoint(path.edges[0], True, quotient) == surface._path_endpoint(
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

        def tree_path(start: int, end: int) -> tuple[tuple[int, bool], ...]:
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

        chains = []
        for edge_index, start, end in chords:
            root = component_root[forest.find(start)]
            edges = (
                *tree_path(root, start),
                (edge_index, True),
                *tree_path(end, root),
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

    def _quotient(
        self, surface: SurfacePresentation
    ) -> tuple[tuple[int, ...], DisjointSet, DisjointSet]:
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

    @classmethod
    def _smith_invariants(
        cls, relations: tuple[tuple[int, ...], ...], dimension: int
    ) -> tuple[int, ...]:
        """Smith factors via determinantal divisors (small benchmark matrices)."""
        if not relations or dimension == 0:
            return ()
        matrix = [list(row) for row in zip(*relations, strict=False)]  # cycle rank x faces
        rank = cls._rational_rank(matrix)
        if rank == 0:
            return ()
        divisors = [1]
        from itertools import combinations

        for size in range(1, rank + 1):
            value = 0
            for rows in combinations(range(len(matrix)), size):
                for cols in combinations(range(len(matrix[0])), size):
                    value = gcd(
                        value,
                        abs(cls._det([[matrix[r][c] for c in cols] for r in rows])),
                    )
            divisors.append(value)
        return tuple(divisors[i] // divisors[i - 1] for i in range(1, len(divisors)))

    @staticmethod
    def _smith_normal_form(
        source: list[list[int]], row_count: int
    ) -> tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]:
        """Return D's nonzero diagonal and U where U * source * V = D."""

        column_count = len(source[0]) if source else 0
        matrix = [row[:] for row in source] if source else [[] for _ in range(row_count)]
        transform = [[int(i == j) for j in range(row_count)] for i in range(row_count)]

        def swap_rows(first: int, second: int) -> None:
            matrix[first], matrix[second] = matrix[second], matrix[first]
            transform[first], transform[second] = transform[second], transform[first]

        def add_row(target: int, source_row: int, multiple: int) -> None:
            matrix[target] = [
                value + multiple * other
                for value, other in zip(matrix[target], matrix[source_row], strict=True)
            ]
            transform[target] = [
                value + multiple * other
                for value, other in zip(transform[target], transform[source_row], strict=True)
            ]

        def swap_columns(first: int, second: int) -> None:
            for row in matrix:
                row[first], row[second] = row[second], row[first]

        pivot = 0
        while pivot < row_count and pivot < column_count:
            locations = [
                (abs(matrix[row][column]), row, column)
                for row in range(pivot, row_count)
                for column in range(pivot, column_count)
                if matrix[row][column]
            ]
            if not locations:
                break
            _, row, column = min(locations)
            swap_rows(pivot, row)
            swap_columns(pivot, column)
            while True:
                changed = False
                for row in range(pivot + 1, row_count):
                    if matrix[row][pivot]:
                        quotient = matrix[row][pivot] // matrix[pivot][pivot]
                        add_row(row, pivot, -quotient)
                        if matrix[row][pivot]:
                            swap_rows(row, pivot)
                        changed = True
                        break
                if changed:
                    continue
                for column in range(pivot + 1, column_count):
                    if matrix[pivot][column]:
                        quotient = matrix[pivot][column] // matrix[pivot][pivot]
                        for row in matrix:
                            row[column] -= quotient * row[pivot]
                        if matrix[pivot][column]:
                            swap_columns(column, pivot)
                        changed = True
                        break
                if changed:
                    continue
                offender = next(
                    (
                        (row, column)
                        for row in range(pivot + 1, row_count)
                        for column in range(pivot + 1, column_count)
                        if matrix[row][column] % matrix[pivot][pivot]
                    ),
                    None,
                )
                if offender is None:
                    break
                add_row(pivot, offender[0], 1)
            if matrix[pivot][pivot] < 0:
                add_row(pivot, pivot, -2)
            pivot += 1
        diagonal = tuple(
            abs(matrix[index][index])
            for index in range(min(row_count, column_count))
            if matrix[index][index]
        )
        return diagonal, tuple(tuple(row) for row in transform)

    @staticmethod
    def _unimodular_inverse(matrix: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
        from fractions import Fraction

        size = len(matrix)
        augmented = [
            [*(Fraction(value) for value in row), *(Fraction(int(i == j)) for j in range(size))]
            for i, row in enumerate(matrix)
        ]
        for column in range(size):
            pivot = next(row for row in range(column, size) if augmented[row][column])
            augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
            divisor = augmented[column][column]
            augmented[column] = [value / divisor for value in augmented[column]]
            for row in range(size):
                if row != column and augmented[row][column]:
                    multiple = augmented[row][column]
                    augmented[row] = [
                        value - multiple * other
                        for value, other in zip(augmented[row], augmented[column], strict=True)
                    ]
        return tuple(tuple(int(value) for value in row[size:]) for row in augmented)

    @staticmethod
    def _rational_rank(matrix: list[list[int]]) -> int:
        from fractions import Fraction

        a = [[Fraction(value) for value in row] for row in matrix]
        rank = 0
        for column in range(len(a[0]) if a else 0):
            pivot = next((r for r in range(rank, len(a)) if a[r][column]), None)
            if pivot is None:
                continue
            a[rank], a[pivot] = a[pivot], a[rank]
            divisor = a[rank][column]
            a[rank] = [value / divisor for value in a[rank]]
            for row in range(len(a)):
                if row != rank and a[row][column]:
                    factor = a[row][column]
                    a[row] = [x - factor * y for x, y in zip(a[row], a[rank], strict=False)]
            rank += 1
        return rank

    @classmethod
    def _det(cls, matrix: list[list[int]]) -> int:
        if not matrix:
            return 1
        if len(matrix) == 1:
            return matrix[0][0]
        return sum(
            (-1) ** col * value * cls._det([row[:col] + row[col + 1 :] for row in matrix[1:]])
            for col, value in enumerate(matrix[0])
        )

    @staticmethod
    def _edge_name(edge: EdgeRef) -> str:
        return f"e{edge.polygon}:{edge.edge}"

    @staticmethod
    def _parse_edge_name(name: str) -> EdgeRef:
        polygon, edge = name[1:].split(":")
        return EdgeRef(int(polygon), int(edge))
