from collections import deque

from attrs import field, frozen

from topology_benchmark.core.validation import number_range
from topology_benchmark.domains.polyhedral_nets.models.net import (
    EdgePair,
    FaceCorner,
    PolyhedralNet,
)
from topology_benchmark.domains.polyhedral_nets.services.polyhedral_net_analyzer import (
    PolyhedralNetAnalyzer,
)


@frozen
class MarkedVertex:
    face: int = field(validator=number_range(minimum=0, message="face indices cannot be negative"))
    corner: int = field(
        validator=number_range(minimum=0, message="corner indices cannot be negative")
    )


@frozen
class MarkedEdge:
    face: int = field(validator=number_range(minimum=0, message="face indices cannot be negative"))
    edge: int = field(validator=number_range(minimum=0, message="edge indices cannot be negative"))


@frozen
class MarkedFace:
    face: int = field(validator=number_range(minimum=0, message="face indices cannot be negative"))


type MarkedNetCell = MarkedVertex | MarkedEdge | MarkedFace


class PolyhedralCellGraphAnalyzer:
    def __init__(self, analyzer: PolyhedralNetAnalyzer) -> None:
        self._analyzer = analyzer

    def statistics(
        self,
        net: PolyhedralNet,
        seams: tuple[EdgePair, ...],
        first: MarkedNetCell,
        second: MarkedNetCell,
    ) -> tuple[int, int]:
        analysis = self._analyzer.analyze(net, seams)
        vertex_of = {
            corner: vertex for vertex, corners in enumerate(analysis.vertices) for corner in corners
        }
        adjacency = [set() for _ in analysis.vertices]
        for face_index, face in enumerate(net.faces):
            for edge in range(face.sides):
                start = vertex_of[FaceCorner(face_index, edge)]
                end = vertex_of[FaceCorner(face_index, (edge + 1) % face.sides)]
                if start != end:
                    adjacency[start].add(end)
                    adjacency[end].add(start)

        def vertices(cell: MarkedNetCell) -> set[int]:
            if isinstance(cell, MarkedVertex):
                return {vertex_of[FaceCorner(cell.face, cell.corner)]}
            if isinstance(cell, MarkedEdge):
                return {
                    vertex_of[FaceCorner(cell.face, cell.edge)],
                    vertex_of[FaceCorner(cell.face, (cell.edge + 1) % net.faces[cell.face].sides)],
                }
            return {
                vertex_of[FaceCorner(cell.face, corner)]
                for corner in range(net.faces[cell.face].sides)
            }

        sources, targets = vertices(first), vertices(second)
        common = sources & targets
        if common:
            return 0, len(common)
        distances = {vertex: 0 for vertex in sources}
        ways = dict.fromkeys(sources, 1)
        pending = deque(sources)
        while pending:
            current = pending.popleft()
            for neighbor in adjacency[current]:
                candidate = distances[current] + 1
                if neighbor not in distances:
                    distances[neighbor] = candidate
                    ways[neighbor] = ways[current]
                    pending.append(neighbor)
                elif distances[neighbor] == candidate:
                    ways[neighbor] += ways[current]
        distance = min(distances[target] for target in targets)
        return distance, sum(ways[target] for target in targets if distances[target] == distance)
