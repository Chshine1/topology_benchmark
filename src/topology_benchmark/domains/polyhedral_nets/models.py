import math
from dataclasses import dataclass
from fractions import Fraction

from attrs import field, frozen, validators

from topology_benchmark.core.validation import nonblank, nonempty, number_range

type Point2 = tuple[float, float]
type Point3 = tuple[Fraction, Fraction, Fraction]
type EdgeMetric = Fraction | float


@frozen
class RegularFace:
    """Legacy regular face; retained for callers constructing abstract nets."""

    name: str = field(validator=nonblank("a face name cannot be empty"))
    sides: int = field(
        validator=number_range(minimum=3, message="a face needs at least three sides")
    )
    side_length: int = field(
        default=1,
        validator=number_range(minimum_exclusive=0, message="a side length must be positive"),
    )

    def corner_angle_degrees(self, corner: int) -> Fraction:
        if not 0 <= corner < self.sides:
            raise ValueError("corner is outside the face")
        return Fraction(180 * (self.sides - 2), self.sides)

    def edge_metric(self, edge: int) -> Fraction:
        if not 0 <= edge < self.sides:
            raise ValueError("edge is outside the face")
        return Fraction(self.side_length * self.side_length)


@frozen
class PolygonFace:
    """Geometry arrays share boundary index ``i``.

    ``points``, ``corner_angles``, and ``source_vertices`` describe corner ``i``;
    ``edge_squared_lengths[i]`` describes its side to corner ``(i + 1) % sides``.
    """

    name: str = field(validator=nonblank("a polygon face needs a name"))
    points: tuple[Point2, ...] = field(validator=validators.min_len(3))
    edge_squared_lengths: tuple[Fraction, ...] = field(
        validator=validators.deep_iterable(
            member_validator=number_range(
                minimum_exclusive=0,
                message="face edges must have positive length",
            )
        )
    )
    corner_angles: tuple[float, ...]
    source_vertices: tuple[int, ...]

    def __attrs_post_init__(self) -> None:
        size = len(self.points)
        if not (
            len(self.edge_squared_lengths)
            == len(self.corner_angles)
            == len(self.source_vertices)
            == size
        ):
            raise ValueError("face geometry arrays must have the same length")

    @property
    def sides(self) -> int:
        return len(self.points)

    def corner_angle_degrees(self, corner: int) -> float:
        return self.corner_angles[corner]

    def edge_metric(self, edge: int) -> Fraction:
        return self.edge_squared_lengths[edge]


type NetFace = RegularFace | PolygonFace


@dataclass(frozen=True, slots=True, order=True)
class NetEdge:
    """Side ``edge`` of ``faces[face]``, from that corner to the next; indices are zero-based."""

    face: int
    edge: int


@dataclass(frozen=True, slots=True, order=True)
class FaceCorner:
    """Corner ``corner`` of ``PolyhedralNet.faces[face]``; both indices are zero-based."""

    face: int
    corner: int


@frozen
class EdgePair:
    """Two sides identified start-to-end as one folded edge."""

    first: NetEdge
    second: NetEdge

    def __attrs_post_init__(self) -> None:
        if self.first == self.second:
            raise ValueError("an edge cannot be paired with itself")

    @property
    def unordered(self) -> frozenset[NetEdge]:
        return frozenset((self.first, self.second))


@frozen
class Polyhedron3D:
    """Each face is an outward-oriented cycle of indices into ``vertices``."""

    name: str
    vertices: tuple[Point3, ...]
    faces: tuple[tuple[int, ...], ...]

    def __attrs_post_init__(self) -> None:
        if not self.name.strip() or len(self.vertices) < 4 or len(self.faces) < 4:
            raise ValueError("a source polyhedron needs vertices and faces")
        for face in self.faces:
            if len(face) < 3 or len(set(face)) != len(face):
                raise ValueError("source faces must be simple cycles")
            if any(vertex < 0 or vertex >= len(self.vertices) for vertex in face):
                raise ValueError("source face references an unknown vertex")


@frozen
class PolyhedralNet:
    """``hinges`` form the uncut face-spanning tree; other sides are boundary edges."""

    name: str = field(validator=nonblank("a polyhedral net needs a name and at least one face"))
    faces: tuple[NetFace, ...] = field(
        validator=nonempty("a polyhedral net needs a name and at least one face")
    )
    hinges: tuple[EdgePair, ...]
    seam_hints: tuple[EdgePair, ...] = ()
    edge_labels: tuple[tuple[NetEdge, str], ...] = ()
    corner_labels: tuple[tuple[FaceCorner, str], ...] = ()
    face_labels: tuple[tuple[int, str], ...] = ()
    corner_angle_labels: tuple[tuple[FaceCorner, str], ...] = ()

    def __attrs_post_init__(self) -> None:
        used: set[NetEdge] = set()
        for pair in self.hinges:
            for edge in (pair.first, pair.second):
                self._validate_edge(edge)
                if edge in used:
                    raise ValueError("each face edge must occur in exactly one hinge pair")
                used.add(edge)
            if self.edge_metric(pair.first) != self.edge_metric(pair.second):
                raise ValueError("paired edges must have equal length")
        if len(self.hinges) != len(self.faces) - 1:
            raise ValueError("the uncut hinges must form a face spanning tree")
        self._validate_hinge_tree()
        boundary = set(self.boundary_edges)
        hinted: set[NetEdge] = set()
        for pair in self.seam_hints:
            for edge in (pair.first, pair.second):
                self._validate_edge(edge)
                if edge not in boundary or edge in hinted:
                    raise ValueError("seam hints must be disjoint boundary-edge pairs")
                hinted.add(edge)
            if self.edge_metric(pair.first) != self.edge_metric(pair.second):
                raise ValueError("hinted seams must have equal lengths")
        for edge, label in self.edge_labels:
            self._validate_edge(edge)
            if edge not in boundary or not label.strip():
                raise ValueError("display edge labels must name boundary edges")
        for corner, label in self.corner_labels:
            self._validate_corner(corner)
            if not label.strip():
                raise ValueError("corner labels cannot be empty")
        for corner, label in self.corner_angle_labels:
            self._validate_corner(corner)
            if not label.strip():
                raise ValueError("corner-angle labels cannot be empty")
        for face, label in self.face_labels:
            if not 0 <= face < len(self.faces) or not label.strip():
                raise ValueError("face labels must reference known faces")

    def _validate_edge(self, edge: NetEdge) -> None:
        if not 0 <= edge.face < len(self.faces):
            raise ValueError("edge references an unknown face")
        if not 0 <= edge.edge < self.faces[edge.face].sides:
            raise ValueError("edge references an unknown face side")

    def _validate_corner(self, corner: FaceCorner) -> None:
        if not 0 <= corner.face < len(self.faces):
            raise ValueError("corner references an unknown face")
        if not 0 <= corner.corner < self.faces[corner.face].sides:
            raise ValueError("corner references an unknown face corner")

    def _validate_hinge_tree(self) -> None:
        reached = {0}
        while True:
            expanded = reached | {
                edge.face
                for pair in self.hinges
                for edge, other in ((pair.first, pair.second), (pair.second, pair.first))
                if other.face in reached
            }
            if expanded == reached:
                break
            reached = expanded
        if len(reached) != len(self.faces):
            raise ValueError("hinges must connect all faces")

    def edge_metric(self, edge: NetEdge) -> EdgeMetric:
        return self.faces[edge.face].edge_metric(edge.edge)

    def edge_length(self, edge: NetEdge) -> float:
        return math.sqrt(float(self.edge_metric(edge)))

    def corner_angle_degrees(self, corner: FaceCorner) -> Fraction | float:
        return self.faces[corner.face].corner_angle_degrees(corner.corner)

    @property
    def boundary_edges(self) -> tuple[NetEdge, ...]:
        hinged = {edge for pair in self.hinges for edge in (pair.first, pair.second)}
        return tuple(
            edge
            for face_index, face in enumerate(self.faces)
            for edge in (NetEdge(face_index, side) for side in range(face.sides))
            if edge not in hinged
        )

    def boundary_label(self, edge: NetEdge) -> str:
        explicit = dict(self.edge_labels)
        if edge in explicit:
            return explicit[edge]
        try:
            return f"e{self.boundary_edges.index(edge) + 1}"
        except ValueError as error:
            raise ValueError("only cut boundary edges have displayed labels") from error


@frozen
class PolyhedralFolding:
    """Adds the hidden closing seams and optional 3D source to an observed net."""

    net: PolyhedralNet
    seams: tuple[EdgePair, ...]
    source: Polyhedron3D | None = None
    root_face: int = 0

    def __attrs_post_init__(self) -> None:
        used = {edge for pair in self.net.hinges for edge in (pair.first, pair.second)}
        for pair in self.seams:
            for edge in (pair.first, pair.second):
                self.net._validate_edge(edge)
                if edge in used:
                    raise ValueError("each face edge must occur in exactly one pair")
                used.add(edge)
            if self.net.edge_metric(pair.first) != self.net.edge_metric(pair.second):
                raise ValueError("paired edges must have equal length")
        expected = {
            NetEdge(face_index, edge)
            for face_index, face in enumerate(self.net.faces)
            for edge in range(face.sides)
        }
        if used != expected:
            raise ValueError("hinges and seams must partition all face edges")
        if not 0 <= self.root_face < len(self.net.faces):
            raise ValueError("root face is outside the net")
