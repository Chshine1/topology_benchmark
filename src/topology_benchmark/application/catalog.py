from collections.abc import Mapping
from dataclasses import dataclass
from random import Random
from typing import Any

from topology_benchmark.application.errors import UnknownDomainError, UnknownProblemRecipeError
from topology_benchmark.core.probability.distribution import FiniteDistribution
from topology_benchmark.core.problem.models import GenerationRequest, Problem
from topology_benchmark.core.problem.recipe import IProblemRecipe, ProblemRecipeCatalog
from topology_benchmark.core.problem.recipe_distribution import (
    IProblemRecipeDistribution,
)


@dataclass(frozen=True, slots=True)
class BenchmarkRegistration:
    id: str
    recipes: ProblemRecipeCatalog[Any]
    default_distribution: IProblemRecipeDistribution[Any]
    configuration_fingerprint: str


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

    def require_recipe(self, domain: str, recipe_id: str) -> None:
        registration = self._get_required_registration(domain)
        self._get_required_recipe(registration, recipe_id)

    def configuration_fingerprint(self, domain: str) -> str:
        return self._get_required_registration(domain).configuration_fingerprint

    def generate(
        self,
        *,
        domain: str,
        request: GenerationRequest,
    ) -> Problem[Any]:
        registration = self._get_required_registration(domain)
        distribution = registration.default_distribution.at(request.difficulty)
        return distribution.sample(Random(request.seed)).generate(request)

    def recipe_distribution(
        self,
        *,
        domain: str,
        difficulty: int,
    ) -> FiniteDistribution[IProblemRecipe[object]]:
        registration = self._get_required_registration(domain)
        return registration.default_distribution.at(difficulty)

    def configured_recipe_distribution(
        self,
        *,
        domain: str,
        weights: Mapping[str, float],
    ) -> FiniteDistribution[IProblemRecipe[object]]:
        registration = self._get_required_registration(domain)
        return FiniteDistribution.weighted(
            (self._get_required_recipe(registration, recipe_id), weight)
            for recipe_id, weight in weights.items()
        )

    def generate_recipe(
        self,
        *,
        domain: str,
        request: GenerationRequest,
        recipe_id: str,
    ) -> Problem[Any]:
        registration = self._get_required_registration(domain)
        return self._get_required_recipe(registration, recipe_id).generate(request)

    @staticmethod
    def _get_required_recipe(
        registration: BenchmarkRegistration, recipe_id: str
    ) -> IProblemRecipe[Any]:
        try:
            return registration.recipes[recipe_id]
        except KeyError as error:
            raise UnknownProblemRecipeError(
                registration.id, recipe_id, tuple(sorted(registration.recipes))
            ) from error

    def _get_required_registration(self, domain: str) -> BenchmarkRegistration:
        try:
            return self._registrations[domain]
        except KeyError as error:
            raise UnknownDomainError(domain, tuple(self._registrations)) from error
