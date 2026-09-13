from typing import override

from topology_benchmark.core.models import GenerationRequest, Problem
from topology_benchmark.core.probability import SamplingSession
from topology_benchmark.core.protocols import ProblemProvider
from topology_benchmark.core.recipes import (
    QuestionCatalog,
    QuestionDistribution,
)
from topology_benchmark.domains.torus_slices.questions import TorusAnswer, TorusQuestion


class TorusQuestionCatalog(QuestionCatalog[TorusQuestion]):
    pass


class TorusSlicesBenchmark(ProblemProvider[TorusQuestion, TorusAnswer]):
    @override
    def generate(
        self,
        *,
        request: GenerationRequest,
        distribution: QuestionDistribution[TorusQuestion],
    ) -> Problem[TorusAnswer]:
        sampling = SamplingSession(request.seed, TorusQuestion.profile_version)
        question = distribution.sample(sampling.rng("question-selection"))
        return question.generate(request)
