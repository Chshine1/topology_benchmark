import math
from fractions import Fraction
from random import Random
from typing import override

from topology_benchmark.core.errors import GenerationExhaustedError
from topology_benchmark.core.problem.models import GenerationRequest
from topology_benchmark.domains.polyhedral_nets.models.net import (
    EdgePair,
    NetEdge,
    Point2,
    Point3,
    PolygonFace,
    PolyhedralFolding,
    PolyhedralNet,
    Polyhedron3D,
)
from topology_benchmark.domains.polyhedral_nets.ports import IPolyhedralNetGenerator


def _sub(first: Point3, second: Point3) -> Point3:
    return (
        first[0] - second[0],
        first[1] - second[1],
        first[2] - second[2],
    )


def _dot(first: Point3, second: Point3) -> Fraction:
    return sum((a * b for a, b in zip(first, second, strict=True)), Fraction())


def _cross(first: Point3, second: Point3) -> Point3:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


class RandomPolyhedralNetGenerator(IPolyhedralNetGenerator):
    """Generate planar developments from validated, exact-coordinate 3D sources."""

    @override
    def generate(self, request: GenerationRequest, rng: Random) -> PolyhedralFolding:
        families = [self._parallelepiped, self._triangular_prism]
        if request.difficulty >= 4:
            families.append(self._pyramid)
        if request.difficulty >= 7:
            families.extend((self._octahedron, self._quadrilateral_bipyramid))
        for _ in range(40):
            source = rng.choice(families)(rng)
            try:
                folding = self._unfold(source, rng)
            except ValueError:
                continue
            return folding
        raise GenerationExhaustedError("polyhedral-nets", "find a non-overlapping development", 40)

    def generate_isometry_pair(
        self, request: GenerationRequest, rng: Random, *, isometric: bool
    ) -> tuple[PolyhedralFolding, PolyhedralFolding]:
        first = self.generate(request, rng)
        if isometric and first.source is not None:
            return first, self._unfold(first.source, rng)
        for _ in range(20):
            second = self.generate(request, rng)
            same_visible_inventory = (
                first.source is not None
                and second.source is not None
                and first.source.name == second.source.name
                and tuple(map(len, first.source.faces)) == tuple(map(len, second.source.faces))
            )
            if same_visible_inventory and self._source_signature(
                first.source
            ) != self._source_signature(second.source):
                return first, second
        raise GenerationExhaustedError(
            "polyhedral-nets", "generate distinct sources with matching face inventories", 20
        )

    @staticmethod
    def _source_signature(source: Polyhedron3D | None) -> tuple[object, ...]:
        if source is None:
            return ()
        edges = {
            tuple(sorted((start, face[(index + 1) % len(face)])))
            for face in source.faces
            for index, start in enumerate(face)
        }
        lengths = tuple(
            sorted(
                _dot(
                    _sub(source.vertices[a], source.vertices[b]),
                    _sub(source.vertices[a], source.vertices[b]),
                )
                for a, b in edges
            )
        )
        return len(source.vertices), tuple(sorted(map(len, source.faces))), lengths

    def _parallelepiped(self, rng: Random) -> Polyhedron3D:
        points = tuple(
            (Fraction(x), Fraction(y), Fraction(z))
            for x, y, z in (
                (0, 0, 0),
                (2, 0, 0),
                (2, 2, 0),
                (0, 2, 0),
                (0, 0, 2),
                (2, 0, 2),
                (2, 2, 2),
                (0, 2, 2),
            )
        )
        faces = ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0))
        return self._affine("irregular parallelepiped", points, faces, rng)

    def _triangular_prism(self, rng: Random) -> Polyhedron3D:
        points = tuple(
            (Fraction(x), Fraction(y), Fraction(z))
            for x, y, z in ((0, 0, 0), (3, 0, 0), (0, 2, 0), (1, 1, 3), (4, 1, 3), (1, 3, 3))
        )
        faces = ((0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5))
        return self._affine("irregular triangular prism", points, faces, rng)

    def _pyramid(self, rng: Random) -> Polyhedron3D:
        points = tuple(
            (Fraction(x), Fraction(y), Fraction(z))
            for x, y, z in ((-2, -1, 0), (2, -1, 0), (2, 1, 0), (-2, 1, 0), (0, 0, 3))
        )
        faces = ((0, 3, 2, 1), (0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4))
        return self._affine("irregular quadrilateral pyramid", points, faces, rng)

    def _octahedron(self, rng: Random) -> Polyhedron3D:
        points = tuple(
            (Fraction(x), Fraction(y), Fraction(z))
            for x, y, z in ((0, 0, 2), (0, 0, -2), (2, 0, 0), (0, 2, 0), (-2, 0, 0), (0, -2, 0))
        )
        faces = (
            (0, 2, 3),
            (0, 3, 4),
            (0, 4, 5),
            (0, 5, 2),
            (1, 3, 2),
            (1, 4, 3),
            (1, 5, 4),
            (1, 2, 5),
        )
        return self._affine("irregular octahedron", points, faces, rng)

    def _quadrilateral_bipyramid(self, rng: Random) -> Polyhedron3D:
        points = tuple(
            (Fraction(x), Fraction(y), Fraction(z))
            for x, y, z in ((0, 0, 3), (0, 0, -2), (3, 0, 0), (0, 2, 0), (-3, 0, 0), (0, -2, 0))
        )
        faces = (
            (0, 2, 3),
            (0, 3, 4),
            (0, 4, 5),
            (0, 5, 2),
            (1, 3, 2),
            (1, 4, 3),
            (1, 5, 4),
            (1, 2, 5),
        )
        return self._affine("irregular quadrilateral bipyramid", points, faces, rng)

    @staticmethod
    def _affine(
        name: str,
        vertices: tuple[Point3, ...],
        faces: tuple[tuple[int, ...], ...],
        rng: Random,
    ) -> Polyhedron3D:
        sx, sy, sz = (Fraction(rng.randint(3, 7), 3) for _ in range(3))
        xy, xz, yz = (Fraction(rng.randint(-2, 2), 5) for _ in range(3))
        transformed = tuple(
            (sx * x + xy * y + xz * z, sy * y + yz * z, sz * z) for x, y, z in vertices
        )
        centroid: Point3 = (
            sum((point[0] for point in transformed), Fraction()) / len(transformed),
            sum((point[1] for point in transformed), Fraction()) / len(transformed),
            sum((point[2] for point in transformed), Fraction()) / len(transformed),
        )
        oriented: list[tuple[int, ...]] = []
        for face in faces:
            first, second, third = (transformed[face[index]] for index in range(3))
            normal = _cross(_sub(second, first), _sub(third, first))
            face_center: Point3 = (
                sum((transformed[vertex][0] for vertex in face), Fraction()) / len(face),
                sum((transformed[vertex][1] for vertex in face), Fraction()) / len(face),
                sum((transformed[vertex][2] for vertex in face), Fraction()) / len(face),
            )
            oriented.append(
                face if _dot(normal, _sub(face_center, centroid)) > 0 else tuple(reversed(face))
            )
        source = Polyhedron3D(name, transformed, tuple(oriented))
        RandomPolyhedralNetGenerator.validate_source(source)
        return source

    @staticmethod
    def validate_source(source: Polyhedron3D) -> None:
        occurrences: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for face in source.faces:
            first, second, third = (source.vertices[face[index]] for index in range(3))
            normal = _cross(_sub(second, first), _sub(third, first))
            if _dot(normal, normal) == 0:
                raise ValueError("source face is degenerate")
            for vertex in face:
                if _dot(normal, _sub(source.vertices[vertex], first)) != 0:
                    raise ValueError("source face is not planar")
            for vertex in source.vertices:
                if _dot(normal, _sub(vertex, first)) > 0:
                    raise ValueError("source face is not an outward convex support face")
            for edge, start in enumerate(face):
                end = face[(edge + 1) % len(face)]
                key = (min(start, end), max(start, end))
                occurrences.setdefault(key, []).append((start, end))
        if any(len(items) != 2 or items[0] != items[1][::-1] for items in occurrences.values()):
            raise ValueError("source edges must have two opposite face occurrences")
        vertices, edges, faces = len(source.vertices), len(occurrences), len(source.faces)
        if vertices - edges + faces != 2:
            raise ValueError("source boundary must be a topological sphere")
        volume_six = Fraction()
        for face in source.faces:
            origin = source.vertices[face[0]]
            for index in range(1, len(face) - 1):
                volume_six += _dot(
                    origin,
                    _cross(
                        source.vertices[face[index]],
                        source.vertices[face[index + 1]],
                    ),
                )
        if volume_six <= 0:
            raise ValueError("source polyhedron must have positive volume")

    def _unfold(self, source: Polyhedron3D, rng: Random) -> PolyhedralFolding:
        all_pairs = self._edge_pairs(source.faces)
        for _ in range(160):
            hinges = self._spanning_tree(len(source.faces), all_pairs, rng)
            layouts = self._develop(source, hinges)
            if self._has_overlap(layouts):
                continue
            faces = tuple(
                self._polygon_face(source, index, points) for index, points in enumerate(layouts)
            )
            hinge_set = {pair.unordered for pair in hinges}
            seams = tuple(pair for pair in all_pairs if pair.unordered not in hinge_set)
            net = PolyhedralNet("unfolded convex polyhedron", faces, hinges)
            return PolyhedralFolding(net, seams, source, 0)
        raise ValueError("no non-overlapping edge development found")

    def _polygon_face(
        self, source: Polyhedron3D, index: int, points: tuple[Point2, ...]
    ) -> PolygonFace:
        cycle = source.faces[index]
        metrics: list[Fraction] = []
        angles: list[float] = []
        for corner, vertex in enumerate(cycle):
            previous = source.vertices[cycle[corner - 1]]
            current = source.vertices[vertex]
            following = source.vertices[cycle[(corner + 1) % len(cycle)]]
            incoming, outgoing = _sub(previous, current), _sub(following, current)
            metrics.append(_dot(outgoing, outgoing))
            cross = _cross(incoming, outgoing)
            angles.append(
                math.degrees(
                    math.atan2(
                        math.sqrt(float(_dot(cross, cross))), float(_dot(incoming, outgoing))
                    )
                )
            )
        return PolygonFace(f"F{index + 1}", points, tuple(metrics), tuple(angles), cycle)

    @staticmethod
    def _edge_pairs(face_vertices: tuple[tuple[int, ...], ...]) -> tuple[EdgePair, ...]:
        occurrences: dict[tuple[int, int], list[NetEdge]] = {}
        for face_index, vertices in enumerate(face_vertices):
            for edge, start in enumerate(vertices):
                end = vertices[(edge + 1) % len(vertices)]
                key = (min(start, end), max(start, end))
                occurrences.setdefault(key, []).append(NetEdge(face_index, edge))
        if any(len(edges) != 2 for edges in occurrences.values()):
            raise ValueError("source faces must form a closed two-manifold")
        return tuple(EdgePair(edges[0], edges[1]) for edges in occurrences.values())

    @staticmethod
    def _spanning_tree(
        face_count: int, pairs: tuple[EdgePair, ...], rng: Random
    ) -> tuple[EdgePair, ...]:
        candidates = list(pairs)
        rng.shuffle(candidates)
        parent = list(range(face_count))

        def find(item: int) -> int:
            while parent[item] != item:
                parent[item] = parent[parent[item]]
                item = parent[item]
            return item

        result: list[EdgePair] = []
        for pair in candidates:
            first, second = find(pair.first.face), find(pair.second.face)
            if first == second:
                continue
            parent[first] = second
            result.append(pair)
            if len(result) == face_count - 1:
                return tuple(result)
        raise ValueError("the dual face graph is disconnected")

    def _develop(
        self, source: Polyhedron3D, hinges: tuple[EdgePair, ...]
    ) -> tuple[tuple[Point2, ...], ...]:
        layouts: list[tuple[Point2, ...] | None] = [None] * len(source.faces)
        layouts[0] = self._place_root(source, 0)
        pending = list(hinges)
        while pending:
            progress = False
            for pair in tuple(pending):
                if layouts[pair.first.face] is not None and layouts[pair.second.face] is None:
                    parent, child = pair.first, pair.second
                elif layouts[pair.second.face] is not None and layouts[pair.first.face] is None:
                    parent, child = pair.second, pair.first
                else:
                    continue
                parent_points = layouts[parent.face]
                assert parent_points is not None
                start = parent_points[(parent.edge + 1) % len(parent_points)]
                end = parent_points[parent.edge]
                layouts[child.face] = self._place_face(source, child.face, child.edge, start, end)
                pending.remove(pair)
                progress = True
            if not progress:
                raise ValueError("hinge graph cannot be developed")
        return tuple(points for points in layouts if points is not None)

    def _place_root(self, source: Polyhedron3D, face: int) -> tuple[Point2, ...]:
        cycle = source.faces[face]
        first, second = source.vertices[cycle[0]], source.vertices[cycle[1]]
        length = math.sqrt(float(_dot(_sub(second, first), _sub(second, first))))
        return self._place_face(source, face, 0, (0.0, 0.0), (length, 0.0))

    @staticmethod
    def _place_face(
        source: Polyhedron3D, face: int, edge: int, start: Point2, end: Point2
    ) -> tuple[Point2, ...]:
        cycle = source.faces[face]
        a, b = source.vertices[cycle[edge]], source.vertices[cycle[(edge + 1) % len(cycle)]]
        edge3 = _sub(b, a)
        length = math.sqrt(float(_dot(edge3, edge3)))
        u3 = tuple(float(value) / length for value in edge3)
        p1, p2, p3 = (source.vertices[cycle[index]] for index in range(3))
        normal_raw = _cross(_sub(p2, p1), _sub(p3, p1))
        normal_length = math.sqrt(float(_dot(normal_raw, normal_raw)))
        normal = tuple(float(value) / normal_length for value in normal_raw)
        v3 = (
            normal[1] * u3[2] - normal[2] * u3[1],
            normal[2] * u3[0] - normal[0] * u3[2],
            normal[0] * u3[1] - normal[1] * u3[0],
        )
        ux, uy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
        vx, vy = -uy, ux
        result: list[Point2] = []
        for vertex in cycle:
            delta = _sub(source.vertices[vertex], a)
            x = sum(float(value) * axis for value, axis in zip(delta, u3, strict=True))
            y = sum(float(value) * axis for value, axis in zip(delta, v3, strict=True))
            result.append((start[0] + x * ux + y * vx, start[1] + x * uy + y * vy))
        return tuple(result)

    @classmethod
    def _has_overlap(cls, polygons: tuple[tuple[Point2, ...], ...]) -> bool:
        return any(
            cls._positive_area_overlap(first, second)
            for index, first in enumerate(polygons)
            for second in polygons[index + 1 :]
        )

    @staticmethod
    def _positive_area_overlap(first: tuple[Point2, ...], second: tuple[Point2, ...]) -> bool:
        for polygon in (first, second):
            for index, point in enumerate(polygon):
                following = polygon[(index + 1) % len(polygon)]
                axis = (-(following[1] - point[1]), following[0] - point[0])
                a = [x * axis[0] + y * axis[1] for x, y in first]
                b = [x * axis[0] + y * axis[1] for x, y in second]
                if min(max(a), max(b)) - max(min(a), min(b)) <= 1e-8:
                    return False
        return True
