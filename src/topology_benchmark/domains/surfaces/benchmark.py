from typing import override

from topology_benchmark.core.models import GenerationRequest, Problem
from topology_benchmark.core.probability import SamplingSession
from topology_benchmark.core.protocols import ProblemProvider
from topology_benchmark.core.recipes import (
    QuestionCatalog,
    QuestionDistribution,
)
from topology_benchmark.domains.surfaces.components.generation_config import SurfaceGenerationConfig
from topology_benchmark.domains.surfaces.ports import SurfaceAnswer
from topology_benchmark.domains.surfaces.questions import SurfaceQuestion


class SurfaceQuestionCatalog(QuestionCatalog[SurfaceQuestion]):
    pass


class SurfaceBenchmark(ProblemProvider[SurfaceQuestion, SurfaceAnswer]):
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
