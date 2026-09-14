from typing import Protocol

from topology_benchmark.core.problem.models import GenerationRequest, Problem
from topology_benchmark.core.problem.question_distribution import IRegisteredQuestion


class IProblemRecipe[AnswerT](IRegisteredQuestion, Protocol):
    """A registered, independently selectable problem-producing capability."""

    def generate(self, request: GenerationRequest) -> Problem[AnswerT]: ...
