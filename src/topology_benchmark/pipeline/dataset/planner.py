import secrets

from topology_benchmark.application.catalog import BenchmarkCatalog
from topology_benchmark.core.probability.distribution import FiniteDistribution
from topology_benchmark.core.problem.identity import canonical_hash
from topology_benchmark.core.problem.recipe import IProblemRecipe
from topology_benchmark.pipeline.config import DatasetConfig
from topology_benchmark.pipeline.dataset.models import (
    DatasetPlan,
    DatasetSpecification,
    GenerationSelection,
    SelectionProbability,
)

DATASET_SCHEMA_VERSION = 3


class DatasetPlanner:
    def __init__(self, config: DatasetConfig, catalog: BenchmarkCatalog) -> None:
        self._config = config
        self._catalog = catalog
        self._validate_configuration()
        self._generation_distribution = self._build_generation_distribution()

    def create(self) -> DatasetPlan:
        root_seed = self._config.seed if self._config.seed is not None else secrets.randbits(128)
        specification = DatasetSpecification(
            schema_version=DATASET_SCHEMA_VERSION,
            root_seed=root_seed,
            size=self._config.size,
            selection=self._selection_probabilities(),
            domain_fingerprints=tuple(
                (domain, self._catalog.configuration_fingerprint(domain))
                for domain in sorted(self._config.domains)
            ),
        )
        return DatasetPlan(
            output_directory=self._config.output_dir,
            dataset_id=canonical_hash(specification)[:16],
            specification=specification,
            generation_distribution=self._generation_distribution,
        )

    def _validate_configuration(self) -> None:
        for domain, config in self._config.domains.items():
            self._catalog.require_domain(domain)
            for recipe in config.recipes:
                self._catalog.require_recipe(domain, recipe)

    def _build_generation_distribution(self) -> FiniteDistribution[GenerationSelection]:
        domains: FiniteDistribution[str] = FiniteDistribution.weighted(
            (domain, config.weight) for domain, config in self._config.domains.items()
        )

        def recipes_for(domain: str, difficulty: int) -> FiniteDistribution[IProblemRecipe[object]]:
            recipes = self._config.domains[domain].recipes
            if recipes:
                return self._catalog.configured_recipe_distribution(domain=domain, weights=recipes)
            return self._catalog.recipe_distribution(domain=domain, difficulty=difficulty)

        def within_domain(domain: str) -> FiniteDistribution[GenerationSelection]:
            config = self._config.domains[domain]
            difficulties = FiniteDistribution.weighted(config.generation_levels.items())
            return difficulties.bind(
                lambda difficulty: recipes_for(domain, difficulty).map(
                    lambda recipe: GenerationSelection(domain, difficulty, recipe)
                )
            )

        return domains.bind(within_domain)

    def _selection_probabilities(self) -> tuple[SelectionProbability, ...]:
        total = self._generation_distribution.total_weight
        return tuple(
            SelectionProbability(
                item.value.domain,
                item.value.difficulty,
                item.value.recipe.id,
                item.weight / total,
            )
            for item in sorted(
                self._generation_distribution.values,
                key=lambda item: (
                    item.value.domain,
                    item.value.difficulty,
                    item.value.recipe.id,
                ),
            )
        )
