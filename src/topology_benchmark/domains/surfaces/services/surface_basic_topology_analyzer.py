from topology_benchmark.utils.disjoint_set_union import FrozenDisjointSetUnion
from topology_benchmark.domains.surfaces.services.surface_quotient_analyzer import (
    SurfaceQuotientAnalyzer,
)
from topology_benchmark.domains.surfaces import SurfacePresentation, EdgeGluing
from topology_benchmark.domains.surfaces.models import SurfaceFacts, ComponentFacts
from topology_benchmark.utils.disjoint_set_union import DisjointSetUnion


class SurfaceBasicTopologyAnalyzer:
    def analyze(self, surface: SurfacePresentation) -> SurfaceFacts:
        quotient = SurfaceQuotientAnalyzer(surface).get_quotient()
        quotient_vertices, connected_components = quotient.vertices, quotient.components
        polygon_indices_by_components: dict[int, list[int]] = {}
        for polygon_index in range(len(surface.polygons)):
            polygon_indices_by_components.setdefault(
                connected_components.find(polygon_index), []
            ).append(polygon_index)

        def key_selector(facts: ComponentFacts) -> int:
            return facts.polygon_indices[0]

        components = tuple(
            sorted(
                (
                    self._analyze_component_facts(
                        surface, quotient_vertices, tuple(polygon_indices)
                    )
                    for polygon_indices in polygon_indices_by_components.values()
                ),
                key=key_selector,
            )
        )
        return SurfaceFacts(components)

    def _analyze_component_facts(
        self,
        surface: SurfacePresentation,
        quotient_vertices: FrozenDisjointSetUnion,
        component_polygon_indices: tuple[int, ...],
    ) -> ComponentFacts:
        vertices = {
            quotient_vertices.find(surface.vertex_offsets[p] + v)
            for p in component_polygon_indices
            for v in range(surface.polygons[p].sides)
        }
        boundary_edges = tuple(
            edge
            for edge in surface.unglued_edges
            if edge.polygon_index in component_polygon_indices
        )
        boundary_count = self._compute_boundary_count(surface, quotient_vertices, boundary_edges)
        orientable = self._is_orientable(surface.gluings, component_polygon_indices)
        non_boundary_edges_count = sum(
            gluing.first_edge.polygon_index in component_polygon_indices
            for gluing in surface.gluings
        )
        euler_characteristic = (
            len(vertices)
            - non_boundary_edges_count
            - len(boundary_edges)
            + len(component_polygon_indices)
        )
        return ComponentFacts(
            component_polygon_indices, orientable, euler_characteristic, boundary_count
        )

    @staticmethod
    def _compute_boundary_count(
        surface: SurfacePresentation,
        quotient_vertices: FrozenDisjointSetUnion,
        unglued_edges: tuple,
    ) -> int:
        if len(unglued_edges) == 0:
            return 0
        boundary_vertices = sorted(
            {
                quotient_vertices.find(v)
                for edge in unglued_edges
                for v in surface.native_edge_vertices(edge)
            }
        )
        inv = {root: i for i, root in enumerate(boundary_vertices)}
        boundary_components = DisjointSetUnion(len(boundary_vertices))
        for edge in unglued_edges:
            edge_a, edge_b = (quotient_vertices.find(v) for v in surface.native_edge_vertices(edge))
            boundary_components.union(inv[edge_a], inv[edge_b])
        return len({boundary_components.find(i) for i in range(len(boundary_vertices))})

    @staticmethod
    def _is_orientable(gluings: tuple[EdgeGluing, ...], polygon_indices: tuple[int, ...]) -> bool:
        adjacency: dict[int, list[tuple[int, int]]] = {p: [] for p in polygon_indices}
        for gluing in gluings:
            if gluing.first_edge.polygon_index not in polygon_indices:
                continue
            relation = -1 if gluing.same_direction else 1
            adjacency[gluing.first_edge.polygon_index].append(
                (gluing.second_edge.polygon_index, relation)
            )
            adjacency[gluing.second_edge.polygon_index].append(
                (gluing.first_edge.polygon_index, relation)
            )
        signs: dict[int, int] = {}
        for start in polygon_indices:
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
