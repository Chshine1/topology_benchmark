from random import Random
from typing import override

from attrs import evolve

from topology_benchmark.domains.polyhedral_nets.abstractions import (
    IPolyhedralNetGenerator,
    IPolyhedralNetRepresentation,
)
from topology_benchmark.domains.polyhedral_nets.config import SeamMatchConfig
from topology_benchmark.domains.polyhedral_nets.generation.completion import (
    NetQuestionCertifier,
    ObservableCompletionEnumerator,
)
from topology_benchmark.domains.polyhedral_nets.models.net import EdgePair, PolyhedralFolding
from topology_benchmark.domains.polyhedral_nets.recipes.base import (
    PolyhedralProblemDraft,
    PolyhedralProblemRecipe,
)


class SeamMatchProblemRecipe(PolyhedralProblemRecipe):
    id = "seam-match"

    def __init__(
        self,
        certifier: NetQuestionCertifier,
        config: SeamMatchConfig,
        net_generator: IPolyhedralNetGenerator,
        completions: ObservableCompletionEnumerator,
        representation: IPolyhedralNetRepresentation,
    ) -> None:
        super().__init__(net_generator, completions, representation)
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
        return PolyhedralProblemDraft(
            "When the convex polyhedron is reconstructed, which labelled boundary edge is "
            "glued to edge A?",
            value,
            evolve(net, seam_hints=hints, edge_labels=labels),
        )
