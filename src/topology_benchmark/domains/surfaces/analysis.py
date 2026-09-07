"""Derive topology from polygon quotients; no classification data is stored on objects."""

from dataclasses import dataclass

from topology_benchmark.domains.surfaces.models import (
    DirectedEdgeMark,
    EdgeRef,
    PathDrawing,
    SurfacePresentation,
)


class _DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, first: int, second: int) -> None:
        first_root, second_root = self.find(first), self.find(second)
        if first_root != second_root:
            self.parent[second_root] = first_root


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


class SurfaceAnalyzer:
    """Analyze the finite CW complex induced by the edge identifications."""

    def analyze(self, surface: SurfacePresentation) -> SurfaceFacts:
        offsets = self._vertex_offsets(surface)
        vertex_dsu = _DisjointSet(offsets[-1])
        polygon_dsu = _DisjointSet(len(surface.polygons))
        pairs = self._mark_pairs(surface)
        for first, second in pairs.values():
            polygon_dsu.union(first.edge.polygon, second.edge.polygon)
            first_start, first_end = self._arrow_vertices(surface, offsets, first)
            second_start, second_end = self._arrow_vertices(surface, offsets, second)
            vertex_dsu.union(first_start, second_start)
            vertex_dsu.union(first_end, second_end)

        self._validate_vertex_links(surface, offsets, vertex_dsu, pairs)

        polygon_groups: dict[int, list[int]] = {}
        for polygon in range(len(surface.polygons)):
            polygon_groups.setdefault(polygon_dsu.find(polygon), []).append(polygon)

        component_facts = []
        for polygon_indices in polygon_groups.values():
            component_facts.append(
                self._component_facts(surface, offsets, vertex_dsu, pairs, tuple(polygon_indices))
            )
        component_facts.sort(key=lambda facts: facts.polygons[0])
        vertex_roots = {vertex_dsu.find(vertex) for vertex in range(offsets[-1])}
        total_edges = sum(len(polygon.vertices) for polygon in surface.polygons) - len(pairs)
        return SurfaceFacts(
            tuple(component_facts), len(vertex_roots), total_edges, len(surface.polygons)
        )

    def path_is_cycle(self, surface: SurfacePresentation, path: PathDrawing) -> bool:
        del surface
        # A signed edge word denotes based edge loops: the deterministic spanning
        # forest supplies the routes from the base vertex to each marked edge.
        return path.closed

    def path_representative(
        self, surface: SurfacePresentation, path: PathDrawing
    ) -> tuple[int, ...]:
        basis = self.cycle_basis(surface)
        coefficients = dict.fromkeys(basis, 0)
        for word, coefficient in path.edge_word:
            if word in coefficients:
                coefficients[word] += coefficient
        return tuple(coefficients[label] for label in basis)

    def cycle_basis(self, surface: SurfacePresentation) -> tuple[str, ...]:
        """Return a deterministic fundamental-cycle basis of the quotient 1-skeleton."""

        offsets = self._vertex_offsets(surface)
        vertex_dsu = _DisjointSet(offsets[-1])
        pairs = self._mark_pairs(surface)
        for first, second in pairs.values():
            first_start, first_end = self._arrow_vertices(surface, offsets, first)
            second_start, second_end = self._arrow_vertices(surface, offsets, second)
            vertex_dsu.union(first_start, second_start)
            vertex_dsu.union(first_end, second_end)
        vertex_roots = sorted({vertex_dsu.find(vertex) for vertex in range(offsets[-1])})
        indices = {root: index for index, root in enumerate(vertex_roots)}
        graph_dsu = _DisjointSet(len(vertex_roots))
        edges: list[tuple[str, int, int]] = []
        for word, pair in pairs.items():
            start, end = self._arrow_vertices(surface, offsets, pair[0])
            edges.append((word, indices[vertex_dsu.find(start)], indices[vertex_dsu.find(end)]))
        for edge in surface.unmarked_edges:
            sides = len(surface.polygons[edge.polygon].vertices)
            start = offsets[edge.polygon] + edge.edge
            end = offsets[edge.polygon] + (edge.edge + 1) % sides
            edges.append(
                (
                    f"boundary:{edge.polygon}:{edge.edge}",
                    indices[vertex_dsu.find(start)],
                    indices[vertex_dsu.find(end)],
                )
            )
        basis = []
        for name, start, end in sorted(edges):
            if graph_dsu.find(start) == graph_dsu.find(end):
                basis.append(name)
            else:
                graph_dsu.union(start, end)
        return tuple(basis)

    def _component_facts(
        self,
        surface: SurfacePresentation,
        offsets: tuple[int, ...],
        vertex_dsu: _DisjointSet,
        pairs: dict[str, tuple[DirectedEdgeMark, DirectedEdgeMark]],
        polygons: tuple[int, ...],
    ) -> ComponentFacts:
        polygon_set = set(polygons)
        vertices = {
            vertex_dsu.find(offsets[p] + vertex)
            for p in polygons
            for vertex in range(len(surface.polygons[p].vertices))
        }
        unmarked = [edge for edge in surface.unmarked_edges if edge.polygon in polygon_set]
        boundary_count = self._boundary_count(surface, offsets, vertex_dsu, unmarked)
        paired_edges = sum(pair[0].edge.polygon in polygon_set for pair in pairs.values())
        edge_count = paired_edges + len(unmarked)
        chi = len(vertices) - edge_count + len(polygons)
        orientable = self._is_orientable(pairs, polygon_set)
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
    def _boundary_count(
        surface: SurfacePresentation,
        offsets: tuple[int, ...],
        vertex_dsu: _DisjointSet,
        unmarked: list[EdgeRef],
    ) -> int:
        if not unmarked:
            return 0
        roots = sorted(
            {
                vertex_dsu.find(offsets[edge.polygon] + endpoint)
                for edge in unmarked
                for endpoint in (
                    edge.edge,
                    (edge.edge + 1) % len(surface.polygons[edge.polygon].vertices),
                )
            }
        )
        root_index = {root: index for index, root in enumerate(roots)}
        boundary_dsu = _DisjointSet(len(roots))
        degree = dict.fromkeys(roots, 0)
        for edge in unmarked:
            sides = len(surface.polygons[edge.polygon].vertices)
            start = vertex_dsu.find(offsets[edge.polygon] + edge.edge)
            end = vertex_dsu.find(offsets[edge.polygon] + (edge.edge + 1) % sides)
            boundary_dsu.union(root_index[start], root_index[end])
            degree[start] += 1
            degree[end] += 1
        if any(value != 2 for value in degree.values()):
            raise ValueError("unglued edges do not form boundary circles")
        return len({boundary_dsu.find(index) for index in range(len(roots))})

    @staticmethod
    def _is_orientable(
        pairs: dict[str, tuple[DirectedEdgeMark, DirectedEdgeMark]], polygons: set[int]
    ) -> bool:
        signs: dict[int, int] = {}
        adjacency: dict[int, list[tuple[int, int]]] = {polygon: [] for polygon in polygons}
        for first, second in pairs.values():
            if first.edge.polygon not in polygons:
                continue
            native_direction = 1 if first.forward == second.forward else -1
            relation = -native_direction
            adjacency[first.edge.polygon].append((second.edge.polygon, relation))
            adjacency[second.edge.polygon].append((first.edge.polygon, relation))
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
    def _validate_vertex_links(
        surface: SurfacePresentation,
        offsets: tuple[int, ...],
        vertex_dsu: _DisjointSet,
        pairs: dict[str, tuple[DirectedEdgeMark, DirectedEdgeMark]],
    ) -> None:
        edge_offsets = [0]
        for polygon in surface.polygons:
            edge_offsets.append(edge_offsets[-1] + len(polygon.vertices))
        link_dsu = _DisjointSet(2 * edge_offsets[-1])

        def link_endpoint(mark: DirectedEdgeMark, arrow_start: bool) -> int:
            native_start = arrow_start == mark.forward
            occurrence = edge_offsets[mark.edge.polygon] + mark.edge.edge
            return 2 * occurrence + (0 if native_start else 1)

        for first, second in pairs.values():
            link_dsu.union(link_endpoint(first, True), link_endpoint(second, True))
            link_dsu.union(link_endpoint(first, False), link_endpoint(second, False))

        links_by_vertex: dict[int, list[tuple[int, int]]] = {}
        for polygon_index, polygon in enumerate(surface.polygons):
            sides = len(polygon.vertices)
            for corner in range(sides):
                previous = edge_offsets[polygon_index] + (corner - 1) % sides
                following = edge_offsets[polygon_index] + corner
                first = link_dsu.find(2 * previous + 1)
                second = link_dsu.find(2 * following)
                vertex = vertex_dsu.find(offsets[polygon_index] + corner)
                links_by_vertex.setdefault(vertex, []).append((first, second))

        for segments in links_by_vertex.values():
            adjacency: dict[int, list[int]] = {}
            degree: dict[int, int] = {}
            for first, second in segments:
                adjacency.setdefault(first, []).append(second)
                adjacency.setdefault(second, []).append(first)
                degree[first] = degree.get(first, 0) + 1
                degree[second] = degree.get(second, 0) + 1
            start = next(iter(adjacency))
            reached = {start}
            stack = [start]
            while stack:
                current = stack.pop()
                for neighbor in adjacency[current]:
                    if neighbor not in reached:
                        reached.add(neighbor)
                        stack.append(neighbor)
            degrees = sorted(degree.values())
            circle = all(value == 2 for value in degrees)
            interval = degrees.count(1) == 2 and all(value in (1, 2) for value in degrees)
            if len(reached) != len(adjacency) or not (circle or interval):
                raise ValueError("a quotient vertex has a non-manifold link")

    @staticmethod
    def _vertex_offsets(surface: SurfacePresentation) -> tuple[int, ...]:
        offsets = [0]
        for polygon in surface.polygons:
            offsets.append(offsets[-1] + len(polygon.vertices))
        return tuple(offsets)

    @staticmethod
    def _mark_pairs(
        surface: SurfacePresentation,
    ) -> dict[str, tuple[DirectedEdgeMark, DirectedEdgeMark]]:
        occurrences: dict[str, list[DirectedEdgeMark]] = {}
        for mark in surface.marks:
            occurrences.setdefault(mark.word, []).append(mark)
        return {word: (marks[0], marks[1]) for word, marks in occurrences.items()}

    @staticmethod
    def _arrow_vertices(
        surface: SurfacePresentation,
        offsets: tuple[int, ...],
        mark: DirectedEdgeMark,
    ) -> tuple[int, int]:
        sides = len(surface.polygons[mark.edge.polygon].vertices)
        native_start = offsets[mark.edge.polygon] + mark.edge.edge
        native_end = offsets[mark.edge.polygon] + (mark.edge.edge + 1) % sides
        return (native_start, native_end) if mark.forward else (native_end, native_start)
