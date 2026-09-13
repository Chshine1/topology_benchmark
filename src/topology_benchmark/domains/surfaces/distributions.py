from typing import override

from topology_benchmark.core.recipes import (
    QuestionCatalog,
    QuestionChoice,
    QuestionDistribution,
    QuestionDistributionResolver,
)
from topology_benchmark.domains.surfaces.generation.config import SurfaceGenerationConfig
from topology_benchmark.domains.surfaces.questions import SurfaceQuestion


class SurfaceDefaultQuestionDistribution(QuestionDistributionResolver[SurfaceQuestion]):
    def __init__(
        self, questions: QuestionCatalog[SurfaceQuestion], config: SurfaceGenerationConfig
    ) -> None:
        configured_ids = {
            question_id
            for groups in (config.object_questions, config.morphism_questions)
            for choices in groups.values()
            for question_id, _ in choices
        }
        registered_ids = set(questions)
        if configured_ids != registered_ids:
            missing = registered_ids - configured_ids
            unknown = configured_ids - registered_ids
            raise ValueError(
                f"surface distribution and catalog disagree; missing={sorted(missing)}, "
                f"unknown={sorted(unknown)}"
            )
        self._questions = questions
        self._config = config

    @property
    def profile_version(self) -> str:
        return self._config.profile_version

    @override
    def at(self, difficulty: int) -> QuestionDistribution[SurfaceQuestion]:
        profile = self._config.difficulty
        families = {
            "object": (
                ("global", profile.global_question_weight.at(difficulty)),
                ("classification", profile.classification_question_weight.at(difficulty)),
                ("path", profile.path_question_weight.at(difficulty)),
            ),
            "morphism": (
                ("relational", profile.relational_question_weight.at(difficulty)),
                ("target-only", profile.target_only_question_weight.at(difficulty)),
            ),
        }
        configured = {
            "object": self._config.object_questions,
            "morphism": self._config.morphism_questions,
        }
        choices = []
        for subject, subject_weight in _normalized(
            tuple(
                (name, weight.at(difficulty))
                for name, weight in self._config.subject_weights.items()
            )
        ):
            for family, family_weight in _normalized(families[subject]):
                for question_id, question_weight in _normalized(configured[subject][family]):
                    choices.append(
                        QuestionChoice(
                            self._questions[question_id],
                            subject_weight * family_weight * question_weight,
                        )
                    )
        return QuestionDistribution(tuple(choices))


def _normalized[ValueT](
    weighted: tuple[tuple[ValueT, float], ...],
) -> tuple[tuple[ValueT, float], ...]:
    total = sum(weight for _, weight in weighted)
    if total <= 0:
        raise ValueError("distribution weights need a positive total")
    return tuple((value, weight / total) for value, weight in weighted)
