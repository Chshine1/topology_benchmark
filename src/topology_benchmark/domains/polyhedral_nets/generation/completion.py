from collections.abc import Callable

from topology_benchmark.domains.polyhedral_nets.models.net import EdgePair, PolyhedralNet
from topology_benchmark.domains.polyhedral_nets.services.polyhedral_net_analyzer import (
    PolyhedralNetAnalyzer,
)


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
