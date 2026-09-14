from random import Random
from typing import override

from attrs import evolve

from topology_benchmark.domains.polyhedral_nets.abstractions import (
    IPolyhedralNetGenerator,
    IPolyhedralNetRepresentation,
)
from topology_benchmark.domains.polyhedral_nets.config import (
    CurvatureOrderConfig,
    VertexDegreeConfig,
    VertexPartitionConfig,
)
from topology_benchmark.domains.polyhedral_nets.generation.completion import (
    NetQuestionCertifier,
    ObservableCompletionEnumerator,
)
from topology_benchmark.domains.polyhedral_nets.models.net import (
    EdgePair,
    FaceCorner,
    PolyhedralFolding,
)
from topology_benchmark.domains.polyhedral_nets.recipes.base import (
    PolyhedralProblemDraft,
    PolyhedralProblemRecipe,
)
from topology_benchmark.domains.polyhedral_nets.services.polyhedral_net_analyzer import (
    PolyhedralNetAnalyzer,
)


class VertexPartitionProblemRecipe(PolyhedralProblemRecipe):
    id = "vertex-partition"

    def __init__(
        self,
        analyzer: PolyhedralNetAnalyzer,
        certifier: NetQuestionCertifier,
        config: VertexPartitionConfig,
        net_generator: IPolyhedralNetGenerator,
        completions: ObservableCompletionEnumerator,
        representation: IPolyhedralNetRepresentation,
    ) -> None:
        super().__init__(net_generator, completions, representation)
        self._analyzer = analyzer
        self._certifier = certifier
        self.config = config
        self.attempts = config.attempts

    @override
    def _build(
        self,
        folding: PolyhedralFolding,
        solutions: tuple[tuple[EdgePair, ...], ...],
        difficulty: int,
        rng: Random,
    ) -> PolyhedralProblemDraft | None:
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
        return PolyhedralProblemDraft(
            "Partition marked corners A through "
            f"{chr(ord('A') + count - 1)} by the folded vertex they become. Write letters in "
            "each group alphabetically and separate the groups with |, for example AC|B|D.",
            value,
            evolve(folding.net, seam_hints=hints, corner_labels=labels),
        )


class VertexDegreeProblemRecipe(PolyhedralProblemRecipe):
    id = "vertex-degree"

    def __init__(
        self,
        analyzer: PolyhedralNetAnalyzer,
        certifier: NetQuestionCertifier,
        config: VertexDegreeConfig,
        net_generator: IPolyhedralNetGenerator,
        completions: ObservableCompletionEnumerator,
        representation: IPolyhedralNetRepresentation,
    ) -> None:
        super().__init__(net_generator, completions, representation)
        self._analyzer = analyzer
        self._certifier = certifier
        self.config = config
        self.attempts = config.attempts

    @override
    def _build(
        self,
        folding: PolyhedralFolding,
        solutions: tuple[tuple[EdgePair, ...], ...],
        difficulty: int,
        rng: Random,
    ) -> PolyhedralProblemDraft | None:
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
        return PolyhedralProblemDraft(
            "How many faces meet at the folded vertex containing marked corner A?",
            value,
            evolve(folding.net, seam_hints=hints, corner_labels=((corner, "A"),)),
        )


class CurvatureOrderProblemRecipe(PolyhedralProblemRecipe):
    id = "curvature-order"

    def __init__(
        self,
        analyzer: PolyhedralNetAnalyzer,
        certifier: NetQuestionCertifier,
        config: CurvatureOrderConfig,
        net_generator: IPolyhedralNetGenerator,
        completions: ObservableCompletionEnumerator,
        representation: IPolyhedralNetRepresentation,
    ) -> None:
        super().__init__(net_generator, completions, representation)
        self._analyzer = analyzer
        self._certifier = certifier
        self.config = config
        self.attempts = config.attempts

    @override
    def _build(
        self,
        folding: PolyhedralFolding,
        solutions: tuple[tuple[EdgePair, ...], ...],
        difficulty: int,
        rng: Random,
    ) -> PolyhedralProblemDraft | None:
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
        return PolyhedralProblemDraft(
            "Corner angles are shown to the nearest degree. Which folded vertex has greater "
            "angular defect (discrete curvature): A or B?",
            value,
            observed,
        )
