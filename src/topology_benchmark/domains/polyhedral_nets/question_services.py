from collections import deque
from collections.abc import Callable
from dataclasses import replace

from topology_benchmark.domains.polyhedral_nets.analysis import PolyhedralNetAnalyzer
from topology_benchmark.domains.polyhedral_nets.models import (
    EdgePair,
    FaceCorner,
    NetEdge,
    PolyhedralNet,
)

type PolyhedralAnswer = int | str | bool
type MarkedNetCell = tuple[str, int, int]


class ObservableCompletionEnumerator:
    def __init__(self, analyzer: PolyhedralNetAnalyzer) -> None:
        self._analyzer = analyzer

    def enumerate(self, net: PolyhedralNet) -> tuple[tuple[EdgePair, ...], ...]:
        return self._analyzer.enumerate_locally_convex_pairings(net, relative_length_tolerance=0.04)


class NetQuestionCertifier:
    def certify[AnswerT](
        self,
        truth: tuple[EdgePair, ...],
        solutions: tuple[tuple[EdgePair, ...], ...],
        answer: Callable[[tuple[EdgePair, ...]], AnswerT],
        difficulty: int,
        *,
        require_unique: bool = False,
        forbidden_hints: tuple[EdgePair, ...] = (),
    ) -> tuple[tuple[EdgePair, ...], AnswerT] | None:
        candidates = list(solutions)
        hints: list[EdgePair] = []
        budget = 3 if difficulty <= 3 else 2 if difficulty <= 6 else 1
        target = answer(truth)
        while (
            len(candidates) != 1
            if require_unique
            else {answer(item) for item in candidates} != {target}
        ):
            if len(hints) >= budget:
                return None
            forbidden = {pair.unordered for pair in forbidden_hints}
            options = [
                pair for pair in truth if pair not in hints and pair.unordered not in forbidden
            ]
            scored = []
            for hint in options:
                remaining = [
                    solution
                    for solution in candidates
                    if any(pair.unordered == hint.unordered for pair in solution)
                ]
                if remaining:
                    scored.append(
                        (
                            (len({answer(item) for item in remaining}), len(remaining)),
                            hint,
                            remaining,
                        )
                    )
            if not scored:
                return None
            _, chosen, candidates = min(scored, key=lambda item: item[0])
            hints.append(chosen)
        return tuple(hints), target


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
            kind, face, item = cell
            if kind == "vertex":
                return {vertex_of[FaceCorner(face, item)]}
            if kind == "edge":
                return {
                    vertex_of[FaceCorner(face, item)],
                    vertex_of[FaceCorner(face, (item + 1) % net.faces[face].sides)],
                }
            return {vertex_of[FaceCorner(face, corner)] for corner in range(net.faces[face].sides)}

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


class NetObservationBuilder:
    def mark_cells(
        self,
        net: PolyhedralNet,
        hints: tuple[EdgePair, ...],
        first: MarkedNetCell,
        second: MarkedNetCell,
    ) -> PolyhedralNet:
        corners = []
        edges = []
        faces = []
        for cell, label in ((first, "A"), (second, "B")):
            kind, face, item = cell
            if kind == "vertex":
                corners.append((FaceCorner(face, item), label))
            elif kind == "edge":
                edges.append((NetEdge(face, item), label))
            else:
                faces.append((face, label))
        return replace(
            net,
            seam_hints=hints,
            corner_labels=tuple(corners),
            edge_labels=tuple(edges),
            face_labels=tuple(faces),
        )

    def cell_name(self, cell: MarkedNetCell, label: str) -> str:
        return {
            "vertex": f"the folded vertex containing corner {label}",
            "edge": f"the folded edge containing boundary edge {label}",
            "face": f"face {label}",
        }[cell[0]]
