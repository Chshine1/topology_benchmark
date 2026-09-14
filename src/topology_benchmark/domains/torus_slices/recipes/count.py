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
from topology_benchmark.domains.torus_slices.config import TorusCountConfig
from topology_benchmark.domains.torus_slices.generation.context import (
    PairLinkedTorusFamily,
    TorusFamilyCondition,
    UnlinkedTorusFamily,
)
from topology_benchmark.domains.torus_slices.models.torus import TorusSliceObservation
from topology_benchmark.domains.torus_slices.recipes.base import TorusProblemRecipe
from topology_benchmark.domains.torus_slices.services.torus_family_analyzer import (
    TorusFamilyAnalyzer,
)


class TorusCountProblemRecipe(TorusProblemRecipe):
    id = "torus-count"
    prompt = (
        "The panels are aligned horizontal sections of one hidden family of pairwise-disjoint "
        "tori with planar elliptic cores. How many tori are in the family?"
    )

    def __init__(
        self,
        generator: ITorusSliceGenerator,
        analyzer: TorusFamilyAnalyzer,
        representation: ITorusSliceRepresentation,
        config: TorusCountConfig,
    ) -> None:
        super().__init__(generator, analyzer, representation)
        self.config = config

    @override
    def _law(self, request: GenerationRequest, /) -> FiniteDistribution[TorusFamilyCondition]:
        maximum = (
            self.config.easy_maximum if request.difficulty <= 3 else self.config.standard_maximum
        )
        return FiniteDistribution(
            tuple(
                WeightedValue(condition, weight)
                for count in range(1, maximum + 1)
                for condition, weight in (
                    ((UnlinkedTorusFamily(count), 1.0),)
                    if count == 1
                    else (
                        (UnlinkedTorusFamily(count), 1 - self.config.linked_probability),
                        (PairLinkedTorusFamily(count), self.config.linked_probability),
                    )
                )
            )
        )

    @override
    def _answer(self, observation: TorusSliceObservation, /) -> TorusAnswer:
        return len(observation.family.tori)
