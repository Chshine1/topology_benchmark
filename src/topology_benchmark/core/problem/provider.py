from typing import Protocol

from topology_benchmark.core.problem.models import GenerationRequest, Problem
from topology_benchmark.core.problem.question_distribution import QuestionDistribution


class IProblemProvider[QuestionT, AnswerT](Protocol):
    def generate(
        self,
        *,
        request: GenerationRequest,
        distribution: QuestionDistribution[QuestionT],
    ) -> Problem[AnswerT]: ...
