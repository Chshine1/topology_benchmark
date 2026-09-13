from dataclasses import dataclass
from typing import Any

from topology_benchmark.application.errors import UnknownDomainError, UnknownQuestionError
from topology_benchmark.core.models import GenerationRequest, Problem
from topology_benchmark.core.protocols import ProblemProvider
from topology_benchmark.core.recipes import (
    QuestionCatalog,
    QuestionDistribution,
    QuestionDistributionResolver,
)


@dataclass(frozen=True, slots=True)
class BenchmarkRegistration:
    id: str
    provider: ProblemProvider[Any, Any]
    questions: QuestionCatalog[Any]
    default_distribution: QuestionDistributionResolver[Any]


class BenchmarkCatalog:
    def __init__(self, registrations: tuple[BenchmarkRegistration, ...]) -> None:
        indexed: dict[str, BenchmarkRegistration] = {}
        for registration in registrations:
            if not registration.id:
                raise ValueError("benchmark domain IDs must not be empty")
            if registration.id in indexed:
                raise ValueError(f"duplicate benchmark domain ID: {registration.id}")
            indexed[registration.id] = registration
        if not indexed:
            raise ValueError("at least one benchmark domain must be registered")
        self._registrations = indexed

    @property
    def domains(self) -> tuple[str, ...]:
        return tuple(self._registrations)

    def require_domain(self, domain: str) -> None:
        self._get_required_registration(domain)

    def require_question(self, domain: str, question_id: str) -> None:
        registration = self._get_required_registration(domain)
        try:
            registration.questions[question_id]
        except KeyError as error:
            raise UnknownQuestionError(
                domain, question_id, tuple(sorted(registration.questions))
            ) from error

    def generate(
        self,
        *,
        domain: str,
        request: GenerationRequest,
    ) -> Problem[Any]:
        registration = self._get_required_registration(domain)
        distribution = registration.default_distribution.at(request.difficulty)
        return registration.provider.generate(request=request, distribution=distribution)

    def generate_recipe(
        self,
        *,
        domain: str,
        request: GenerationRequest,
        recipe_id: str,
    ) -> Problem[Any]:
        registration = self._get_required_registration(domain)
        try:
            question = registration.questions[recipe_id]
        except KeyError as error:
            raise UnknownQuestionError(
                domain, recipe_id, tuple(sorted(registration.questions))
            ) from error
        distribution = QuestionDistribution.concentrated(question)
        return registration.provider.generate(request=request, distribution=distribution)

    def _get_required_registration(self, domain: str) -> BenchmarkRegistration:
        try:
            return self._registrations[domain]
        except KeyError as error:
            raise UnknownDomainError(domain, tuple(self._registrations)) from error
