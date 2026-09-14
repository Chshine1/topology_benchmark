from abc import ABC, abstractmethod
from typing import override

from topology_benchmark.core.probability.distribution import (
    FiniteDistribution,
    WeightedValue,
)
from topology_benchmark.core.probability.sampling import SamplingSession
from topology_benchmark.core.problem.models import GenerationRequest, Problem
from topology_benchmark.core.problem.recipe import IProblemRecipe
from topology_benchmark.domains.torus_slices.config import TorusCountConfig, TorusLinkConfig
from topology_benchmark.domains.torus_slices.generation.context import (
    ChainLinkedTorusFamily,
    CompletelyLinkedTorusFamily,
    PairLinkedTorusFamily,
    TorusFamilyCondition,
    TorusGenerationContext,
    UnlinkedTorusFamily,
)
from topology_benchmark.domains.torus_slices.models.torus import TorusSliceObservation
from topology_benchmark.domains.torus_slices.ports import (
    ITorusSliceGenerator,
    ITorusSliceRepresentation,
)
from topology_benchmark.domains.torus_slices.services.torus_family_analyzer import (
    TorusFamilyAnalyzer,
)

type TorusAnswer = int | bool


class TorusQuestion(IProblemRecipe[TorusAnswer], ABC):
    id = ""
    prompt = ""
    profile_version = "torus-slices-v5"

    def __init__(
        self,
        generator: ITorusSliceGenerator,
        analyzer: TorusFamilyAnalyzer,
        representation: ITorusSliceRepresentation,
    ) -> None:
        self._generator = generator
        self._analyzer = analyzer
        self._representation = representation

    @override
    def generate(self, request: GenerationRequest) -> Problem[TorusAnswer]:
        sampling = SamplingSession(request.seed, self.profile_version)
        context = TorusGenerationContext(
            request,
            sampling.sample("parameters", self._law(request)),
            sampling,
        )
        observation = self._generator.generate_for(context)
        section = self._representation.render(
            observation, request, sampling.rng("render.level-sections")
        )
        return Problem(
            self.prompt,
            (section,),
            self._answer(observation),
            request.seed,
            self.id,
        )

    @abstractmethod
    def _law(self, request: GenerationRequest, /) -> FiniteDistribution[TorusFamilyCondition]: ...

    @abstractmethod
    def _answer(self, observation: TorusSliceObservation, /) -> TorusAnswer: ...

    def _linked_family_law(
        self, request: GenerationRequest, config: TorusLinkConfig
    ) -> FiniteDistribution[TorusFamilyCondition]:
        values: list[WeightedValue[TorusFamilyCondition]] = []
        for count in range(config.minimum_count, config.maximum_count + 1):
            values.append(WeightedValue(UnlinkedTorusFamily(count), 0.5))
            if count < 3 or request.difficulty < 7:
                values.append(WeightedValue(PairLinkedTorusFamily(count), 0.5))
                continue
            values.extend(
                (
                    WeightedValue(
                        PairLinkedTorusFamily(count),
                        0.5 * (1 - config.chain_probability - config.complete_probability),
                    ),
                    WeightedValue(ChainLinkedTorusFamily(count), 0.5 * config.chain_probability),
                    WeightedValue(
                        CompletelyLinkedTorusFamily(count),
                        0.5 * config.complete_probability,
                    ),
                )
            )
        return FiniteDistribution(tuple(values))


class TorusCountQuestion(TorusQuestion):
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


class LinkedQuestion(TorusQuestion):
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


class CompletelyUnlinkedQuestion(TorusQuestion):
    id = "completely-unlinked"
    prompt = (
        "In the hidden generated family, does every pair of core curves have linking number zero?"
    )

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
        return self._linked_family_law(request, self.config)

    @override
    def _answer(self, observation: TorusSliceObservation, /) -> TorusAnswer:
        return not self._analyzer.linked_pairs(observation.family)


class LinkedPairCountQuestion(TorusQuestion):
    id = "linked-pair-count"
    prompt = (
        "How many unordered pairs of the hidden tori have core curves with nonzero linking number?"
    )

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
        return self._linked_family_law(request, self.config)

    @override
    def _answer(self, observation: TorusSliceObservation, /) -> TorusAnswer:
        return len(self._analyzer.linked_pairs(observation.family))
