from abc import ABC, abstractmethod
from random import Random
from typing import Literal, override

from attrs import field, frozen, validators

from topology_benchmark.core.models import GenerationRequest, Problem
from topology_benchmark.core.probability import SamplingSession
from topology_benchmark.core.protocols import ProblemRecipe
from topology_benchmark.domains.torus_slices.analysis import TorusFamilyAnalyzer
from topology_benchmark.domains.torus_slices.generation import TorusGenerationSpec
from topology_benchmark.domains.torus_slices.models import TorusSliceObservation
from topology_benchmark.domains.torus_slices.ports import (
    TorusSliceGenerator,
    TorusSliceRepresentation,
)

type TorusAnswer = int | bool


@frozen
class TorusCountConfig:
    easy_maximum: int = field(default=2, validator=validators.ge(1))
    standard_maximum: int = field(default=3, validator=validators.ge(1))
    linked_probability: float = field(
        default=0.58,
        validator=validators.and_(validators.ge(0.0), validators.le(1.0)),
    )


@frozen
class TorusLinkConfig:
    minimum_count: int = field(
        default=2,
        validator=validators.and_(validators.ge(2), validators.le(4)),
    )
    maximum_count: int = field(
        default=4,
        validator=validators.and_(validators.ge(2), validators.le(4)),
    )
    chain_probability: float = field(
        default=0.4,
        validator=validators.and_(validators.ge(0.0), validators.le(1.0)),
    )
    complete_probability: float = field(
        default=0.4,
        validator=validators.and_(validators.ge(0.0), validators.le(1.0)),
    )

    def __attrs_post_init__(self) -> None:
        if self.minimum_count > self.maximum_count:
            raise ValueError("torus link counts must lie between two and four")
        if self.chain_probability + self.complete_probability > 1:
            raise ValueError("torus link pattern probabilities are invalid")


class TorusQuestion(ProblemRecipe[TorusAnswer], ABC):
    id = ""
    prompt = ""
    profile_version = "torus-slices-v4"

    def __init__(
        self,
        generator: TorusSliceGenerator,
        analyzer: TorusFamilyAnalyzer,
        representation: TorusSliceRepresentation,
    ) -> None:
        self._generator = generator
        self._analyzer = analyzer
        self._representation = representation

    @override
    def generate(self, request: GenerationRequest) -> Problem[TorusAnswer]:
        sampling = SamplingSession(request.seed, self.profile_version)
        observation = self._generator.generate(
            request, sampling.rng("object"), self._spec(request, sampling.rng("parameters"))
        )
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
    def _spec(self, request: GenerationRequest, rng: Random, /) -> TorusGenerationSpec: ...

    @abstractmethod
    def _answer(self, observation: TorusSliceObservation, /) -> TorusAnswer: ...

    def _linked_spec(
        self, request: GenerationRequest, rng: Random, config: TorusLinkConfig
    ) -> TorusGenerationSpec:
        count = rng.randint(config.minimum_count, config.maximum_count)
        linked = bool(rng.randrange(2))
        pattern: Literal["pairs", "chain", "complete"] = "pairs"
        if linked and count >= 3 and request.difficulty >= 7:
            choice = rng.random()
            if choice < config.chain_probability:
                pattern = "chain"
            elif choice < config.chain_probability + config.complete_probability:
                pattern = "complete"
        return TorusGenerationSpec(count, linked, pattern)


class TorusCountQuestion(TorusQuestion):
    id = "torus-count"
    prompt = (
        "The panels are aligned horizontal sections of one hidden family of pairwise-disjoint "
        "tori with planar elliptic cores. How many tori are in the family?"
    )

    def __init__(
        self,
        generator: TorusSliceGenerator,
        analyzer: TorusFamilyAnalyzer,
        representation: TorusSliceRepresentation,
        config: TorusCountConfig,
    ) -> None:
        super().__init__(generator, analyzer, representation)
        self.config = config

    @override
    def _spec(self, request: GenerationRequest, rng: Random, /) -> TorusGenerationSpec:
        maximum = (
            self.config.easy_maximum if request.difficulty <= 3 else self.config.standard_maximum
        )
        count = rng.randint(1, maximum)
        linked = count >= 2 and rng.random() < self.config.linked_probability
        return TorusGenerationSpec(count, linked, "pairs")

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
    def _spec(self, _request: GenerationRequest, rng: Random, /) -> TorusGenerationSpec:
        return TorusGenerationSpec(2, bool(rng.randrange(2)), "pairs")

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
        generator: TorusSliceGenerator,
        analyzer: TorusFamilyAnalyzer,
        representation: TorusSliceRepresentation,
        config: TorusLinkConfig,
    ) -> None:
        super().__init__(generator, analyzer, representation)
        self.config = config

    @override
    def _spec(self, request: GenerationRequest, rng: Random, /) -> TorusGenerationSpec:
        return self._linked_spec(request, rng, self.config)

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
        generator: TorusSliceGenerator,
        analyzer: TorusFamilyAnalyzer,
        representation: TorusSliceRepresentation,
        config: TorusLinkConfig,
    ) -> None:
        super().__init__(generator, analyzer, representation)
        self.config = config

    @override
    def _spec(self, request: GenerationRequest, rng: Random, /) -> TorusGenerationSpec:
        return self._linked_spec(request, rng, self.config)

    @override
    def _answer(self, observation: TorusSliceObservation, /) -> TorusAnswer:
        return len(self._analyzer.linked_pairs(observation.family))
