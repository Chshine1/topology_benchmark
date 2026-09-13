from dataclasses import dataclass
from random import Random
from typing import Protocol, override

from attrs import evolve, field, frozen, validators

from topology_benchmark.core.recipes import RegisteredQuestion
from topology_benchmark.domains.polyhedral_nets.analysis import PolyhedralNetAnalyzer
from topology_benchmark.domains.polyhedral_nets.models import (
    EdgePair,
    FaceCorner,
    PolyhedralFolding,
    PolyhedralNet,
)
from topology_benchmark.domains.polyhedral_nets.question_services import (
    MarkedNetCell,
    NetObservationBuilder,
    NetQuestionCertifier,
    PolyhedralAnswer,
    PolyhedralCellGraphAnalyzer,
)


@dataclass(frozen=True, slots=True)
class PolyhedralQuestionDraft:
    question: str
    answer: PolyhedralAnswer
    observed: PolyhedralNet


class PolyhedralQuestion(RegisteredQuestion, Protocol):
    attempts: int

    def build(
        self,
        folding: PolyhedralFolding,
        solutions: tuple[tuple[EdgePair, ...], ...],
        difficulty: int,
        rng: Random,
    ) -> PolyhedralQuestionDraft | None: ...


@frozen
class VertexPartitionConfig:
    attempts: int = field(default=30, validator=validators.ge(1))
    easy_mark_count: int = field(default=4, validator=validators.ge(1))
    hard_mark_count: int = field(default=5, validator=validators.ge(1))
    hard_from: int = field(default=6, validator=validators.ge(1))


@frozen
class VertexDegreeConfig:
    attempts: int = field(default=30, validator=validators.ge(1))


@frozen
class CurvatureOrderConfig:
    attempts: int = field(default=30, validator=validators.ge(1))
    exact_margin: float = field(default=8.0, validator=validators.ge(0.0))
    visible_margin: int = field(default=6, validator=validators.ge(0))


@frozen
class SeamMatchConfig:
    attempts: int = field(default=30, validator=validators.ge(1))
    candidate_count: int = field(default=3, validator=validators.ge(1))


@frozen
class CellDistanceConfig:
    attempts: int = field(default=30, validator=validators.ge(1))
    edge_cells_from: int = field(default=4, validator=validators.ge(1))
    vertex_cells_from: int = field(default=7, validator=validators.ge(1))
    candidate_limit: int = field(default=24, validator=validators.ge(1))


class VertexPartitionQuestion(PolyhedralQuestion):
    id = "vertex-partition"

    def __init__(
        self,
        analyzer: PolyhedralNetAnalyzer,
        certifier: NetQuestionCertifier,
        config: VertexPartitionConfig,
    ) -> None:
        self._analyzer = analyzer
        self._certifier = certifier
        self.config = config
        self.attempts = config.attempts

    @override
    def build(
        self,
        folding: PolyhedralFolding,
        solutions: tuple[tuple[EdgePair, ...], ...],
        difficulty: int,
        rng: Random,
    ) -> PolyhedralQuestionDraft | None:
        corner_classes = list(self._analyzer.analyze(folding).vertices)
        repeated = [group for group in corner_classes if len(group) >= 2]
        if not repeated or len(corner_classes) < 2:
            return None
        count = (
            self.config.easy_mark_count
            if difficulty < self.config.hard_from
            else self.config.hard_mark_count
        )
        first_group = rng.choice(repeated)
        second_group = rng.choice([group for group in corner_classes if group != first_group])
        selected = [*rng.sample(first_group, 2), rng.choice(second_group)]
        remaining = [
            corner for group in corner_classes for corner in group if corner not in selected
        ]
        rng.shuffle(remaining)
        selected.extend(remaining[: count - len(selected)])
        if len(selected) != count:
            return None
        rng.shuffle(selected)
        labels = tuple((corner, chr(ord("A") + index)) for index, corner in enumerate(selected))

        def answer(seams: tuple[EdgePair, ...]) -> str:
            vertices = self._analyzer.analyze(folding.net, seams).vertices
            groups = [
                "".join(sorted(label for corner, label in labels if corner in vertex))
                for vertex in vertices
            ]
            return "|".join(sorted(group for group in groups if group))

        certified = self._certifier.certify(folding.seams, solutions, answer, difficulty)
        if certified is None:
            return None
        hints, value = certified
        return PolyhedralQuestionDraft(
            "Partition marked corners A through "
            f"{chr(ord('A') + count - 1)} by the folded vertex they become. Write letters in "
            "each group alphabetically and separate the groups with |, for example AC|B|D.",
            value,
            evolve(folding.net, seam_hints=hints, corner_labels=labels),
        )


class VertexDegreeQuestion(PolyhedralQuestion):
    id = "vertex-degree"

    def __init__(
        self,
        analyzer: PolyhedralNetAnalyzer,
        certifier: NetQuestionCertifier,
        config: VertexDegreeConfig,
    ) -> None:
        self._analyzer = analyzer
        self._certifier = certifier
        self.config = config
        self.attempts = config.attempts

    @override
    def build(
        self,
        folding: PolyhedralFolding,
        solutions: tuple[tuple[EdgePair, ...], ...],
        difficulty: int,
        rng: Random,
    ) -> PolyhedralQuestionDraft | None:
        corner = rng.choice(rng.choice(self._analyzer.analyze(folding).vertices))

        def answer(seams: tuple[EdgePair, ...]) -> int:
            vertex = next(
                group
                for group in self._analyzer.analyze(folding.net, seams).vertices
                if corner in group
            )
            return len({item.face for item in vertex})

        certified = self._certifier.certify(folding.seams, solutions, answer, difficulty)
        if certified is None:
            return None
        hints, value = certified
        return PolyhedralQuestionDraft(
            "How many faces meet at the folded vertex containing marked corner A?",
            value,
            evolve(folding.net, seam_hints=hints, corner_labels=((corner, "A"),)),
        )


class CurvatureOrderQuestion(PolyhedralQuestion):
    id = "curvature-order"

    def __init__(
        self,
        analyzer: PolyhedralNetAnalyzer,
        certifier: NetQuestionCertifier,
        config: CurvatureOrderConfig,
    ) -> None:
        self._analyzer = analyzer
        self._certifier = certifier
        self.config = config
        self.attempts = config.attempts

    @override
    def build(
        self,
        folding: PolyhedralFolding,
        solutions: tuple[tuple[EdgePair, ...], ...],
        difficulty: int,
        rng: Random,
    ) -> PolyhedralQuestionDraft | None:
        net = folding.net
        first_class, second_class = rng.sample(list(self._analyzer.analyze(folding).vertices), 2)
        first, second = rng.choice(first_class), rng.choice(second_class)

        def answer(seams: tuple[EdgePair, ...]) -> str:
            vertices = self._analyzer.analyze(net, seams).vertices
            group_a = next(group for group in vertices if first in group)
            group_b = next(group for group in vertices if second in group)
            difference = sum(round(float(net.corner_angle_degrees(c))) for c in group_a) - sum(
                round(float(net.corner_angle_degrees(c))) for c in group_b
            )
            return "A" if difference < 0 else "B" if difference > 0 else "equal"

        exact_difference = float(
            sum(net.corner_angle_degrees(c) for c in first_class)
            - sum(net.corner_angle_degrees(c) for c in second_class)
        )
        visible_difference = sum(
            round(float(net.corner_angle_degrees(c))) for c in first_class
        ) - sum(round(float(net.corner_angle_degrees(c))) for c in second_class)
        if (
            abs(exact_difference) < self.config.exact_margin
            or abs(visible_difference) < self.config.visible_margin
            or exact_difference * visible_difference <= 0
        ):
            return None
        certified = self._certifier.certify(folding.seams, solutions, answer, difficulty)
        if certified is None:
            return None
        hints, value = certified
        angles = tuple(
            (
                FaceCorner(face, corner),
                f"{round(float(net.corner_angle_degrees(FaceCorner(face, corner))))}°",
            )
            for face, shape in enumerate(net.faces)
            for corner in range(shape.sides)
        )
        observed = evolve(
            net,
            seam_hints=hints,
            corner_labels=((first, "A"), (second, "B")),
            corner_angle_labels=angles,
        )
        return PolyhedralQuestionDraft(
            "Corner angles are shown to the nearest degree. Which folded vertex has greater "
            "angular defect (discrete curvature): A or B?",
            value,
            observed,
        )


class SeamMatchQuestion(PolyhedralQuestion):
    id = "seam-match"

    def __init__(self, certifier: NetQuestionCertifier, config: SeamMatchConfig) -> None:
        self._certifier = certifier
        self.config = config
        self.attempts = config.attempts

    @override
    def build(
        self,
        folding: PolyhedralFolding,
        solutions: tuple[tuple[EdgePair, ...], ...],
        difficulty: int,
        rng: Random,
    ) -> PolyhedralQuestionDraft | None:
        net = folding.net
        target_pair = rng.choice(folding.seams)
        target, mate = target_pair.first, target_pair.second
        distractors = [edge for edge in net.boundary_edges if edge not in (target, mate)]
        rng.shuffle(distractors)
        same = [edge for edge in distractors if net.edge_metric(edge) == net.edge_metric(target)]
        others = [edge for edge in distractors if edge not in same]
        distractor_count = self.config.candidate_count - 1
        same = same[:distractor_count]
        candidates = [
            mate,
            *same,
            *others[: self.config.candidate_count - 1 - len(same)],
        ]
        rng.shuffle(candidates)
        labels = ((target, "A"), *((edge, chr(66 + i)) for i, edge in enumerate(candidates)))

        def answer(seams: tuple[EdgePair, ...]) -> str:
            pair = next((pair for pair in seams if target in pair.unordered), None)
            if pair is None:
                return "none"
            partner = next(edge for edge in pair.unordered if edge != target)
            return dict(labels).get(partner, "none")

        certified = self._certifier.certify(
            folding.seams,
            solutions,
            answer,
            difficulty,
            forbidden_hints=(target_pair,),
        )
        if certified is None:
            return None
        hints, value = certified
        return PolyhedralQuestionDraft(
            "When the convex polyhedron is reconstructed, which labelled boundary edge is "
            "glued to edge A?",
            value,
            evolve(net, seam_hints=hints, edge_labels=labels),
        )


class CellDistanceQuestion(PolyhedralQuestion):
    id = "cell-distance"
    count_paths = False

    def __init__(
        self,
        analyzer: PolyhedralNetAnalyzer,
        graph: PolyhedralCellGraphAnalyzer,
        certifier: NetQuestionCertifier,
        observations: NetObservationBuilder,
        config: CellDistanceConfig,
    ) -> None:
        self._analyzer = analyzer
        self._graph = graph
        self._certifier = certifier
        self._observations = observations
        self.config = config
        self.attempts = config.attempts

    @override
    def build(
        self,
        folding: PolyhedralFolding,
        solutions: tuple[tuple[EdgePair, ...], ...],
        difficulty: int,
        rng: Random,
    ) -> PolyhedralQuestionDraft | None:
        kinds = ("face",) if difficulty < self.config.edge_cells_from else ("face", "edge")
        if difficulty >= self.config.vertex_cells_from:
            kinds = ("face", "edge", "vertex")
        cells: list[MarkedNetCell] = []
        if "face" in kinds:
            cells.extend(("face", face, -1) for face in range(len(folding.net.faces)))
        if "edge" in kinds:
            cells.extend(("edge", edge.face, edge.edge) for edge in folding.net.boundary_edges)
        if "vertex" in kinds:
            cells.extend(
                ("vertex", corner.face, corner.corner)
                for vertex in self._analyzer.analyze(folding).vertices
                for corner in (rng.choice(vertex),)
            )
        candidates = [
            (first, second) for index, first in enumerate(cells) for second in cells[index + 1 :]
        ]
        rng.shuffle(candidates)
        prefer_zero = bool(rng.randrange(2))
        preferred = [
            pair
            for pair in candidates
            if (self._graph.statistics(folding.net, folding.seams, *pair)[0] == 0) == prefer_zero
        ]
        for first, second in (preferred or candidates)[: self.config.candidate_limit]:

            def answer(
                seams: tuple[EdgePair, ...],
                a: MarkedNetCell = first,
                b: MarkedNetCell = second,
            ) -> int:
                distance, paths = self._graph.statistics(folding.net, seams, a, b)
                return paths if self.count_paths else distance

            certified = self._certifier.certify(folding.seams, solutions, answer, difficulty)
            if certified is None:
                continue
            hints, value = certified
            a = self._observations.cell_name(first, "A")
            b = self._observations.cell_name(second, "B")
            question = (
                f"How many shortest vertex paths in the folded 1-skeleton connect {a} to {b}? "
                "Path length is the number of edges. Distinct paths have different vertex "
                "sequences; each common vertex gives one zero-edge path."
                if self.count_paths
                else f"What is the minimum number of edges in a vertex path through the folded "
                f"1-skeleton connecting {a} to {b}?"
            )
            return PolyhedralQuestionDraft(
                question,
                value,
                self._observations.mark_cells(folding.net, hints, first, second),
            )
        return None


class ShortestPathCountQuestion(CellDistanceQuestion):
    id = "cell-shortest-path-count"
    count_paths = True
