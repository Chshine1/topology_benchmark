from abc import ABC, abstractmethod
from dataclasses import dataclass
from random import Random
from typing import override

from topology_benchmark.core.errors import GenerationExhaustedError
from topology_benchmark.core.probability.sampling import SamplingSession
from topology_benchmark.core.problem.models import GenerationRequest, Problem
from topology_benchmark.core.problem.recipe import IProblemRecipe
from topology_benchmark.domains.polyhedral_nets.abstractions import (
    IPolyhedralNetGenerator,
    IPolyhedralNetRepresentation,
    PolyhedralAnswer,
)
from topology_benchmark.domains.polyhedral_nets.generation.completion import (
    ObservableCompletionEnumerator,
)
from topology_benchmark.domains.polyhedral_nets.models.net import (
    EdgePair,
    PolyhedralFolding,
    PolyhedralNet,
)


@dataclass(frozen=True, slots=True)
class PolyhedralProblemDraft:
    prompt: str
    answer: PolyhedralAnswer
    observed: PolyhedralNet


class PolyhedralProblemRecipe(IProblemRecipe[PolyhedralAnswer], ABC):
    id = ""
    attempts: int
    profile_version = "polyhedral-nets-v8"

    def __init__(
        self,
        net_generator: IPolyhedralNetGenerator,
        completions: ObservableCompletionEnumerator,
        representation: IPolyhedralNetRepresentation,
    ) -> None:
        self._net_generator = net_generator
        self._completions = completions
        self._representation = representation

    @override
    def generate(self, request: GenerationRequest) -> Problem[PolyhedralAnswer]:
        sampling = SamplingSession(request.seed, self.profile_version)
        for attempt in range(self.attempts):
            folding = self._net_generator.generate(
                request, sampling.rng(f"object.{self.id}.{attempt}")
            )
            solutions = self._completions.enumerate(folding.net)
            if not solutions:
                continue
            draft = self._build(
                folding,
                solutions,
                request.difficulty,
                sampling.rng(f"recipe.{self.id}.{attempt}"),
            )
            if draft is None:
                continue
            section = self._representation.render(draft.observed, request, sampling.rng("render"))
            return Problem(draft.prompt, (section,), draft.answer, request.seed, self.id)
        raise GenerationExhaustedError(
            "polyhedral-nets", f"generate a certified {self.id} problem", self.attempts
        )

    @abstractmethod
    def _build(
        self,
        folding: PolyhedralFolding,
        solutions: tuple[tuple[EdgePair, ...], ...],
        difficulty: int,
        rng: Random,
    ) -> PolyhedralProblemDraft | None: ...
