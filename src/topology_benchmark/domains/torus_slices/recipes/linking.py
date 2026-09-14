from typing import override

from topology_benchmark.core.probability.distribution import (
    FiniteDistribution,
    WeightedValue,
)
from topology_benchmark.core.problem.models import GenerationRequest
from topology_benchmark.domains.torus_slices.abstractions import (
    ITorusSliceGenerator,
    ITorusSliceRepresentation,
    TorusAnswer,
)
from topology_benchmark.domains.torus_slices.config import TorusLinkConfig
from topology_benchmark.domains.torus_slices.generation.context import (
    ChainLinkedTorusFamily,
    CompletelyLinkedTorusFamily,
    PairLinkedTorusFamily,
    TorusFamilyCondition,
    UnlinkedTorusFamily,
)
from topology_benchmark.domains.torus_slices.models.torus import TorusSliceObservation
from topology_benchmark.domains.torus_slices.recipes.base import TorusProblemRecipe
from topology_benchmark.domains.torus_slices.services.torus_family_analyzer import (
    TorusFamilyAnalyzer,
)


class LinkedProblemRecipe(TorusProblemRecipe):
    id = "linked"
    prompt = (
        "These aligned sections come from exactly two pairwise-disjoint elliptic tori. Are their "
        "core curves linked?"
    )

    @override
    def _law(self, _request: GenerationRequest, /) -> FiniteDistribution[TorusFamilyCondition]:
        return FiniteDistribution(
            (
                WeightedValue(UnlinkedTorusFamily(2), 1.0),
                WeightedValue(PairLinkedTorusFamily(2), 1.0),
            )
        )

    @override
    def _answer(self, observation: TorusSliceObservation, /) -> TorusAnswer:
        return bool(self._analyzer.linked_pairs(observation.family))


class _ConfiguredLinkProblemRecipe(TorusProblemRecipe):
    def __init__(
        self,
        generator: ITorusSliceGenerator,
        analyzer: TorusFamilyAnalyzer,
        representation: ITorusSliceRepresentation,
        config: TorusLinkConfig,
    ) -> None:
        super().__init__(generator, analyzer, representation)
        self.config = config

    @override
    def _law(self, request: GenerationRequest, /) -> FiniteDistribution[TorusFamilyCondition]:
        values: list[WeightedValue[TorusFamilyCondition]] = []
        for count in range(self.config.minimum_count, self.config.maximum_count + 1):
            values.append(WeightedValue(UnlinkedTorusFamily(count), 0.5))
            if count < 3 or request.difficulty < 7:
                values.append(WeightedValue(PairLinkedTorusFamily(count), 0.5))
                continue
            values.extend(
                (
                    WeightedValue(
                        PairLinkedTorusFamily(count),
                        0.5
                        * (1 - self.config.chain_probability - self.config.complete_probability),
                    ),
                    WeightedValue(
                        ChainLinkedTorusFamily(count), 0.5 * self.config.chain_probability
                    ),
                    WeightedValue(
                        CompletelyLinkedTorusFamily(count),
                        0.5 * self.config.complete_probability,
                    ),
                )
            )
        return FiniteDistribution(tuple(values))


class CompletelyUnlinkedProblemRecipe(_ConfiguredLinkProblemRecipe):
    id = "completely-unlinked"
    prompt = (
        "In the hidden generated family, does every pair of core curves have linking number zero?"
    )

    @override
    def _answer(self, observation: TorusSliceObservation, /) -> TorusAnswer:
        return not self._analyzer.linked_pairs(observation.family)


class LinkedPairCountProblemRecipe(_ConfiguredLinkProblemRecipe):
    id = "linked-pair-count"
    prompt = (
        "How many unordered pairs of the hidden tori have core curves with nonzero linking number?"
    )

    @override
    def _answer(self, observation: TorusSliceObservation, /) -> TorusAnswer:
        return len(self._analyzer.linked_pairs(observation.family))
