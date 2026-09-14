from typing import override

from topology_benchmark.core.probability.sampling import SamplingSession
from topology_benchmark.core.problem.models import GenerationRequest, Problem
from topology_benchmark.core.problem.provider import IProblemProvider
from topology_benchmark.core.problem.question_distribution import (
    QuestionCatalog,
    QuestionDistribution,
)
from topology_benchmark.domains.surfaces.generation.config import SurfaceGenerationConfig
from topology_benchmark.domains.surfaces.ports import SurfaceAnswer
from topology_benchmark.domains.surfaces.questions import SurfaceQuestion


class SurfaceQuestionCatalog(QuestionCatalog[SurfaceQuestion]):
    pass


class SurfaceBenchmark(IProblemProvider[SurfaceQuestion, SurfaceAnswer]):
    def __init__(
        self,
        generation_config: SurfaceGenerationConfig,
    ) -> None:
        self._profile_version = generation_config.profile_version

    @override
    def generate(
        self,
        *,
        request: GenerationRequest,
        distribution: QuestionDistribution[SurfaceQuestion],
    ) -> Problem[SurfaceAnswer]:
        sampling = SamplingSession(request.seed, self._profile_version)
        question = distribution.sample(sampling.rng("question-selection"))
        return question.generate(request)
