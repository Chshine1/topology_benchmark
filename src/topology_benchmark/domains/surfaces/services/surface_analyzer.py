from topology_benchmark.domains.surfaces.services.surface_quotient_analyzer import (
    SurfaceQuotientAnalyzer,
)
from typing import cast

from topology_benchmark.domains.surfaces.models import (
    CellularHomology,
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
from topology_benchmark.utils.integer_linear_algebra import IntegralMatrix


class SurfaceAnalyzer:
    @staticmethod
    def analyze(surface: SurfacePresentation) -> SurfaceFacts:
        return SurfaceBasicTopologyAnalyzer().analyze(surface)

    @staticmethod
    def cellular_homology(surface: SurfacePresentation) -> CellularHomology:
        return SurfaceHomologyAnalyzer(
            surface, SurfaceBasicTopologyAnalyzer()
        ).compute_cellular_homology()

    @staticmethod
    def path_is_cycle(surface: SurfacePresentation, path: tuple[OrientedEdge, ...]) -> bool:
        quotient = surface.quotient_vertices()
        return surface.path_endpoint(path[0], True, quotient) == surface.path_endpoint(
            path[-1], False, quotient
        )

    def get_path_homology_coefficients(
        self, surface: SurfacePresentation, path: tuple[OrientedEdge, ...]
    ) -> tuple[int, ...]:
        quotient = SurfaceQuotientAnalyzer(surface).get_quotient()

        if not self.path_is_cycle(surface, path):
            raise ValueError("an open path has no homology class")
        homology = SurfaceHomologyAnalyzer(
            surface, SurfaceBasicTopologyAnalyzer()
        ).compute_cellular_homology()

        path_coordinate_flat = [0] * homology.chord_projection.columns

        pos_edge_reps = {rep: i for i, rep in enumerate(quotient.edge_representatives)}
        for edge in path:
            edge_rep, _ = surface.native_edge_vertices(edge.edge)
            pos = pos_edge_reps[edge_rep]
            _, direction = quotient.edges.find(pos)
            path_coordinate_flat[pos] += edge.forward * direction

        path_coordinate = IntegralMatrix.column_vector(path_coordinate_flat)
        chord_coordinate = homology.chord_projection * path_coordinate
        normalized_coordinate = homology.chord_base_change * chord_coordinate
        rank = min(homology.normalized_partial2.rows, homology.normalized_partial2.columns)

        def basis_coordinate_iterator():
            for i in range(normalized_coordinate.rows):
                d = cast(int, homology.normalized_partial2[i, i]) if i < rank else 0
                if d != 1:
                    yield (
                        normalized_coordinate.flat[i] % d
                        if d > 0
                        else normalized_coordinate.flat[i]
                    )

        return tuple(basis_coordinate_iterator())
