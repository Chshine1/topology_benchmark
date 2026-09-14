from typing import override

from topology_benchmark.core.probability.sampling import SamplingSession
from topology_benchmark.core.problem.models import GenerationRequest, Problem
from topology_benchmark.core.problem.provider import IProblemProvider
from topology_benchmark.core.problem.question_distribution import (
    QuestionCatalog,
    QuestionDistribution,
)
from topology_benchmark.domains.torus_slices.questions.question import TorusAnswer, TorusQuestion


class TorusQuestionCatalog(QuestionCatalog[TorusQuestion]):
    pass


class TorusSlicesBenchmark(IProblemProvider[TorusQuestion, TorusAnswer]):
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
