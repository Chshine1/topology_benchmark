import math
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from itertools import permutations, product

from topology_benchmark.domains.polyhedral_nets.models import (
    EdgePair,
    FaceCorner,
    NetEdge,
    PolyhedralFolding,
    PolyhedralNet,
)
from topology_benchmark.utils import DisjointSet

type MetricFaceCycle = tuple[tuple[int, float, object], ...]


class VertexType(Enum):
    POSITIVE_DEFECT = "positive-defect"
    ZERO_DEFECT = "zero-defect"
    NEGATIVE_DEFECT = "negative-defect"

    # Compatibility aliases for the v1 public API.
    CONVEX = POSITIVE_DEFECT
    FLAT = ZERO_DEFECT
    SADDLE = NEGATIVE_DEFECT


@dataclass(frozen=True, slots=True)
class NetAnalysis:
    vertices: tuple[tuple[FaceCorner, ...], ...]
    angle_sums: tuple[Fraction | float, ...]
    vertex_types: tuple[VertexType, ...]
    euler_characteristic: int
    vertex_neighborhoods_are_disks: bool
    positive_curvature_metric: bool
    admits_convex_realization: bool


class PolyhedralNetAnalyzer:
    """Uses declared hinges and seams, never rendered coordinates."""

    def analyze(
        self,
        subject: PolyhedralFolding | PolyhedralNet,
        seams: tuple[EdgePair, ...] | None = None,
    ) -> NetAnalysis:
        if isinstance(subject, PolyhedralFolding):
            if seams is not None:
                raise ValueError("do not override seams on a complete folding")
            net, closing_seams = subject.net, subject.seams
        else:
            net, closing_seams = subject, seams or ()
        pairs = (*net.hinges, *closing_seams)
        corners, roots = self._corner_classes(net, pairs)
        vertices = tuple(
            tuple(corner for corner, root in zip(corners, roots, strict=True) if root == candidate)
            for candidate in sorted(set(roots))
        )
        angle_sums = tuple(self._angle_sum(net, vertex) for vertex in vertices)
        kinds = tuple(self.classify_angle(angle) for angle in angle_sums)
        edge_count = len(pairs)
        chi = len(vertices) - edge_count + len(net.faces)
        closed = len(pairs) * 2 == sum(face.sides for face in net.faces)
        manifold = self._vertex_links_are_circles(net, pairs, vertices)
        locally_convex = bool(kinds) and all(kind is VertexType.POSITIVE_DEFECT for kind in kinds)
        return NetAnalysis(
            vertices,
            angle_sums,
            kinds,
            chi,
            manifold,
            locally_convex,
            closed and manifold and chi == 2 and locally_convex,
        )

    @staticmethod
    def classify_angle(angle_degrees: Fraction | float) -> VertexType:
        if angle_degrees < 360 - 1e-9:
            return VertexType.POSITIVE_DEFECT
        if angle_degrees <= 360 + 1e-9:
            return VertexType.ZERO_DEFECT
        return VertexType.NEGATIVE_DEFECT

    @staticmethod
    def _angle_sum(net: PolyhedralNet, vertex: tuple[FaceCorner, ...]) -> Fraction | float:
        angles = tuple(net.corner_angle_degrees(corner) for corner in vertex)
        if all(isinstance(angle, Fraction) for angle in angles):
            return sum(angles, Fraction())
        return math.fsum(float(angle) for angle in angles)

    def marked_vertex_type(self, folding: PolyhedralFolding) -> VertexType:
        net = folding.net
        if net.marked_corner is None:
            raise ValueError("the net has no marked folded vertex")
        analysis = self.analyze(folding)
        return next(
            kind
            for vertex, kind in zip(analysis.vertices, analysis.vertex_types, strict=True)
            if net.marked_corner in vertex
        )

    def seam_answer(self, folding: PolyhedralFolding) -> str:
        return self.pairing_answer(folding.net, folding.seams)

    @staticmethod
    def pairing_answer(net: PolyhedralNet, seams: tuple[EdgePair, ...]) -> str:
        labels = (
            tuple(sorted((net.boundary_label(pair.first), net.boundary_label(pair.second))))
            for pair in seams
        )
        return ", ".join(f"{first}-{second}" for first, second in sorted(labels))

    def isometric(self, first: PolyhedralFolding, second: PolyhedralFolding) -> bool:
        """Compare complete metric cell complexes up to relabelling and reflection."""
        first_data = self._cell_complex(first)
        second_data = self._cell_complex(second)
        first_vertices, first_faces = first_data
        second_vertices, second_faces = second_data
        if len(first_vertices) != len(second_vertices) or len(first_faces) != len(second_faces):
            return False
        first_groups: dict[tuple[object, ...], list[int]] = {}
        second_groups: dict[tuple[object, ...], list[int]] = {}
        for vertex, signature in enumerate(first_vertices):
            first_groups.setdefault(signature, []).append(vertex)
        for vertex, signature in enumerate(second_vertices):
            second_groups.setdefault(signature, []).append(vertex)
        if {key: len(value) for key, value in first_groups.items()} != {
            key: len(value) for key, value in second_groups.items()
        }:
            return False
        keys = sorted(first_groups, key=repr)
        choices = (permutations(second_groups[key]) for key in keys)
        expected = sorted(second_faces)
        for selected in product(*choices):
            mapping = {
                first_vertex: second_vertex
                for key, targets in zip(keys, selected, strict=True)
                for first_vertex, second_vertex in zip(first_groups[key], targets, strict=True)
            }
            if sorted(self._map_face(face, mapping) for face in first_faces) == expected:
                return True
        return False

    def enumerate_locally_convex_pairings(
        self,
        net: PolyhedralNet,
        *,
        max_solutions: int | None = None,
        relative_length_tolerance: float = 0.0,
    ) -> tuple[tuple[EdgePair, ...], ...]:
        """Find locally convex closures without simulating collision-free folding.

        A positive length tolerance treats visually indistinguishable edges as equal.
        """
        if relative_length_tolerance < 0:
            raise ValueError("relative length tolerance cannot be negative")
        hinted_edges = {edge for pair in net.seam_hints for edge in (pair.first, pair.second)}
        boundary = tuple(edge for edge in net.boundary_edges if edge not in hinted_edges)
        if len(boundary) % 2:
            return ()
        solutions: list[tuple[EdgePair, ...]] = []

        def visit(remaining: tuple[NetEdge, ...], chosen: tuple[EdgePair, ...]) -> None:
            if max_solutions is not None and len(solutions) >= max_solutions:
                return
            if not remaining:
                result = self.analyze(net, (*net.seam_hints, *chosen))
                if result.admits_convex_realization:
                    solutions.append((*net.seam_hints, *chosen))
                return
            first = remaining[0]
            for index in range(1, len(remaining)):
                second = remaining[index]
                first_length = net.edge_length(first)
                second_length = net.edge_length(second)
                tolerance = relative_length_tolerance * max(first_length, second_length)
                if abs(first_length - second_length) > tolerance:
                    continue
                visit(
                    remaining[1:index] + remaining[index + 1 :],
                    (*chosen, EdgePair(first, second)),
                )

        visit(boundary, ())
        return tuple(solutions)

    def _cell_complex(
        self, folding: PolyhedralFolding
    ) -> tuple[tuple[tuple[object, ...], ...], tuple[MetricFaceCycle, ...]]:
        net = folding.net
        analysis = self.analyze(folding)
        vertex_of = {
            corner: vertex for vertex, corners in enumerate(analysis.vertices) for corner in corners
        }
        incident_lengths: list[list[object]] = [[] for _ in analysis.vertices]
        incident_faces: list[list[int]] = [[] for _ in analysis.vertices]
        for face_index, face in enumerate(net.faces):
            for corner in range(face.sides):
                vertex = vertex_of[FaceCorner(face_index, corner)]
                incident_lengths[vertex].append(net.edge_metric(NetEdge(face_index, corner)))
                incident_faces[vertex].append(face.sides)
        vertices = tuple(
            (
                round(float(angle), 10),
                tuple(sorted(lengths)),
                tuple(sorted(faces)),
            )
            for angle, lengths, faces in zip(
                analysis.angle_sums, incident_lengths, incident_faces, strict=True
            )
        )
        faces = tuple(
            self._canonical_face(
                tuple(
                    (
                        vertex_of[FaceCorner(face_index, corner)],
                        round(float(net.corner_angle_degrees(FaceCorner(face_index, corner))), 10),
                        net.edge_metric(NetEdge(face_index, corner)),
                    )
                    for corner in range(face.sides)
                )
            )
            for face_index, face in enumerate(net.faces)
        )
        return vertices, faces

    @classmethod
    def _canonical_face(cls, face: MetricFaceCycle) -> MetricFaceCycle:
        size = len(face)
        variants = []
        for start in range(size):
            variants.append(tuple(face[(start + offset) % size] for offset in range(size)))
            variants.append(
                tuple(
                    (
                        face[(start - offset) % size][0],
                        face[(start - offset) % size][1],
                        face[(start - offset - 1) % size][2],
                    )
                    for offset in range(size)
                )
            )
        return min(variants, key=repr)

    @classmethod
    def _map_face(
        cls,
        face: MetricFaceCycle,
        mapping: dict[int, int],
    ) -> MetricFaceCycle:
        return cls._canonical_face(
            tuple((mapping[vertex], angle, length) for vertex, angle, length in face)
        )

    @staticmethod
    def _vertex_links_are_circles(
        net: PolyhedralNet,
        pairs: tuple[EdgePair, ...],
        vertices: tuple[tuple[FaceCorner, ...], ...],
    ) -> bool:
        adjacency: dict[FaceCorner, set[FaceCorner]] = {
            corner: set() for vertex in vertices for corner in vertex
        }
        degrees = dict.fromkeys(adjacency, 0)

        def corners(edge: NetEdge) -> tuple[FaceCorner, FaceCorner]:
            return (
                FaceCorner(edge.face, edge.edge),
                FaceCorner(edge.face, (edge.edge + 1) % net.faces[edge.face].sides),
            )

        def connect(first: FaceCorner, second: FaceCorner) -> None:
            degrees[first] += 1
            degrees[second] += 1
            adjacency[first].add(second)
            adjacency[second].add(first)

        for pair in pairs:
            first_start, first_end = corners(pair.first)
            second_start, second_end = corners(pair.second)
            connect(first_start, second_end)
            connect(first_end, second_start)

        for vertex in vertices:
            if any(degrees[corner] != 2 for corner in vertex):
                return False
            reached = {vertex[0]}
            frontier = [vertex[0]]
            while frontier:
                current = frontier.pop()
                for neighbor in adjacency[current]:
                    if neighbor not in reached:
                        reached.add(neighbor)
                        frontier.append(neighbor)
            if reached != set(vertex):
                return False
        return True

    @staticmethod
    def _corner_classes(
        net: PolyhedralNet, pairs: tuple[EdgePair, ...]
    ) -> tuple[tuple[FaceCorner, ...], tuple[int, ...]]:
        offsets = [0]
        for face in net.faces:
            offsets.append(offsets[-1] + face.sides)
        dsu = DisjointSet(offsets[-1])

        def endpoints(edge: NetEdge) -> tuple[int, int]:
            start = offsets[edge.face] + edge.edge
            end = offsets[edge.face] + (edge.edge + 1) % net.faces[edge.face].sides
            return start, end

        for pair in pairs:
            first_start, first_end = endpoints(pair.first)
            second_start, second_end = endpoints(pair.second)
            dsu.union(first_start, second_end)
            dsu.union(first_end, second_start)
        corners = tuple(
            FaceCorner(face_index, corner)
            for face_index, face in enumerate(net.faces)
            for corner in range(face.sides)
        )
        roots = tuple(dsu.find(index) for index in range(offsets[-1]))
        return corners, roots
