from abc import ABC, abstractmethod
from typing import override

from topology_benchmark.core.probability.distribution import FiniteDistribution
from topology_benchmark.core.probability.sampling import SamplingSession
from topology_benchmark.core.problem.models import GenerationRequest, Problem
from topology_benchmark.core.problem.recipe import IProblemRecipe
from topology_benchmark.domains.torus_slices.abstractions import (
    ITorusSliceGenerator,
    ITorusSliceRepresentation,
    TorusAnswer,
)
from topology_benchmark.domains.torus_slices.generation.context import (
    TorusFamilyCondition,
    TorusGenerationContext,
)
from topology_benchmark.domains.torus_slices.models.torus import TorusSliceObservation
from topology_benchmark.domains.torus_slices.services.torus_family_analyzer import (
    TorusFamilyAnalyzer,
)


class TorusProblemRecipe(IProblemRecipe[TorusAnswer], ABC):
    id = ""
    prompt = ""
    profile_version = "torus-slices-v6"

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
