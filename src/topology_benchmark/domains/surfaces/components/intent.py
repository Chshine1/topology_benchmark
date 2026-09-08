"""Probabilistic selection of a question before its mathematical instance."""

from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.core.probability import (
    BernoulliDistribution,
    FiniteDistribution,
    SamplingSession,
    WeightedValue,
)
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
    """Select subject and question with smoothly difficulty-dependent weights."""

    def __init__(self, config: SurfaceGenerationConfig) -> None:
        self.config = config

    def sample(self, request: GenerationRequest, sampling: SamplingSession) -> SurfaceProblemIntent:
        is_morphism = sampling.sample(
            "intent.is-morphism",
            BernoulliDistribution(
                self.config.difficulty.morphism_probability.at(request.difficulty)
            ),
        )
        if is_morphism:
            return self._morphism_intent(sampling)
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
        kind = sampling.sample(
            "intent.question-kind", self._question_distribution("object", family)
        )
        return SurfaceProblemIntent(
            ProblemSubject.OBJECT,
            kind,
            QuestionFocus(family),
        )

    def _morphism_intent(self, sampling: SamplingSession) -> SurfaceProblemIntent:
        target_only = sampling.sample(
            "intent.target-only",
            BernoulliDistribution(self.config.noise_probability),
            noise=True,
        )
        family = "target-only" if target_only else "relational"
        kind = sampling.sample(
            "intent.question-kind", self._question_distribution("morphism", family)
        )
        return SurfaceProblemIntent(
            ProblemSubject.MORPHISM,
            kind,
            QuestionFocus(family),
            noise=target_only,
        )

    def _question_distribution(self, subject: str, family: str) -> FiniteDistribution[str]:
        groups = (
            self.config.object_questions if subject == "object" else self.config.morphism_questions
        )
        return FiniteDistribution(
            tuple(WeightedValue(kind, weight) for kind, weight in groups[family])
        )
