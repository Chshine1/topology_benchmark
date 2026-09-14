from typing import override

from topology_benchmark.core.errors import GenerationExhaustedError
from topology_benchmark.core.probability.sampling import SamplingSession
from topology_benchmark.core.problem.models import GenerationRequest, Problem
from topology_benchmark.core.problem.provider import IProblemProvider
from topology_benchmark.core.problem.question_distribution import (
    QuestionCatalog,
    QuestionDistribution,
)
from topology_benchmark.domains.polyhedral_nets.generation.completion import (
    ObservableCompletionEnumerator,
)
from topology_benchmark.domains.polyhedral_nets.ports import (
    IPolyhedralNetGenerator,
    IPolyhedralNetRepresentation,
    PolyhedralAnswer,
)
from topology_benchmark.domains.polyhedral_nets.questions.question import IPolyhedralQuestion


class PolyhedralQuestionCatalog(QuestionCatalog[IPolyhedralQuestion]):
    pass


class PolyhedralNetsBenchmark(IProblemProvider[IPolyhedralQuestion, PolyhedralAnswer]):
    profile_version = "polyhedral-nets-v8"

    def __init__(
        self,
        generator: IPolyhedralNetGenerator,
        completions: ObservableCompletionEnumerator,
        representation: IPolyhedralNetRepresentation,
    ) -> None:
        self._generator = generator
        self._completions = completions
        self._representation = representation

    @override
    def generate(
        self,
        *,
        request: GenerationRequest,
        distribution: QuestionDistribution[IPolyhedralQuestion],
    ) -> Problem[PolyhedralAnswer]:
        sampling = SamplingSession(request.seed, self.profile_version)
        question = distribution.sample(sampling.rng("question-selection"))
        selected = question.id
        for attempt in range(question.attempts):
            folding = self._generator.generate(
                request, sampling.rng(f"object.{selected}.{attempt}")
            )
            solutions = self._completions.enumerate(folding.net)
            if not solutions:
                continue
            draft = question.build(
                folding,
                solutions,
                request.difficulty,
                sampling.rng(f"question.{selected}.{attempt}"),
            )
            if draft is None:
                continue
            section = self._representation.render(draft.observed, request, sampling.rng("render"))
            return Problem(draft.question, (section,), draft.answer, request.seed, selected)
        raise GenerationExhaustedError(
            "polyhedral-nets", f"generate a certified {selected} question", question.attempts
        )
