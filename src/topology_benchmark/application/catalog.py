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

    def validate_domain(self, domain: str) -> None:
        self._require_domain(domain)

    def validate_recipe(self, domain: str, recipe: str) -> None:
        registration = self._require_domain(domain)
        self._require_question(registration, domain, recipe)

    def generate(
        self,
        *,
        domain: str,
        request: GenerationRequest,
    ) -> Problem[Any]:
        registration = self._require_domain(domain)
        distribution = registration.default_distribution.at(request.difficulty)
        return registration.provider.generate(request=request, distribution=distribution)

    def generate_recipe(
        self,
        *,
        domain: str,
        request: GenerationRequest,
        recipe_id: str,
    ) -> Problem[Any]:
        registration = self._require_domain(domain)
        question = self._require_question(registration, domain, recipe_id)
        distribution = QuestionDistribution.concentrated(question)
        return registration.provider.generate(request=request, distribution=distribution)

    def _require_domain(self, domain: str) -> BenchmarkRegistration:
        try:
            return self._registrations[domain]
        except KeyError as error:
            raise UnknownDomainError(domain, tuple(self._registrations)) from error

    @staticmethod
    def _require_question(registration: BenchmarkRegistration, domain: str, recipe_id: str) -> Any:
        try:
            return registration.questions[recipe_id]
        except KeyError as error:
            raise UnknownQuestionError(
                domain, recipe_id, tuple(sorted(registration.questions))
            ) from error
