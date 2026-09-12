from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.core.probability import FiniteDistribution, SamplingSession, WeightedValue
from topology_benchmark.domains.surfaces.components.generation_config import (
    SurfaceGenerationConfig,
)
from topology_benchmark.domains.surfaces.generation import (
    ProblemSubject,
    QuestionFocus,
    SurfaceProblemIntent,
)
from topology_benchmark.domains.surfaces.ports import SurfaceIntentGenerator


class RandomSurfaceIntentGenerator(SurfaceIntentGenerator):
    def __init__(self, config: SurfaceGenerationConfig) -> None:
        self.config = config

    def sample(self, request: GenerationRequest, sampling: SamplingSession) -> SurfaceProblemIntent:
        # Morphism questions need explicit correspondences and induced-map answers first.
        return self._object_intent(request, sampling)

    def _object_intent(
        self, request: GenerationRequest, sampling: SamplingSession
    ) -> SurfaceProblemIntent:
        profile = self.config.difficulty
        family = sampling.sample(
            "intent.object-family",
            FiniteDistribution(
                (
                    WeightedValue("global", profile.global_question_weight.at(request.difficulty)),
                    WeightedValue(
                        "classification",
                        profile.classification_question_weight.at(request.difficulty),
                    ),
                    WeightedValue("path", profile.path_question_weight.at(request.difficulty)),
                )
            ),
        )
        kind = sampling.sample("intent.question-kind", self._question_distribution(family))
        return SurfaceProblemIntent(
            ProblemSubject.OBJECT,
            kind,
            QuestionFocus(family),
        )

    def _question_distribution(self, family: str) -> FiniteDistribution[str]:
        groups = self.config.object_questions
        return FiniteDistribution(
            tuple(WeightedValue(kind, weight) for kind, weight in groups[family])
        )
