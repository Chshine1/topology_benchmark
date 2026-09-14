import hashlib
import json
import secrets
from dataclasses import dataclass
from random import Random

from topology_benchmark.application.catalog import BenchmarkCatalog
from topology_benchmark.core.probability.distribution import FiniteDistribution
from topology_benchmark.core.problem.models import GenerationRequest, Problem
from topology_benchmark.core.problem.recipe import IProblemRecipe
from topology_benchmark.pipeline.config import PipelineConfig
from topology_benchmark.pipeline.dataset.artifact_writer import DatasetArtifactWriter
from topology_benchmark.pipeline.dataset.models import GeneratedBenchmarkRun, GeneratedItem


@dataclass(frozen=True, slots=True)
class GenerationSelection:
    domain: str
    difficulty: int
    recipe: IProblemRecipe[object]


class BenchmarkDatasetGenerator:
    def __init__(
        self,
        config: PipelineConfig,
        catalog: BenchmarkCatalog,
        artifact_writer: DatasetArtifactWriter,
    ) -> None:
        self._config = config
        self._catalog = catalog
        self._artifact_writer = artifact_writer
        self._validate_configuration()
        self._generation_distribution = self._build_generation_distribution()

    def _validate_configuration(self) -> None:
        for domain, config in self._config.domains.items():
            self._catalog.require_domain(domain)
            for recipe in config.recipes:
                self._catalog.require_recipe(domain, recipe)

    def generate(self) -> GeneratedBenchmarkRun:
        root_seed = self._config.seed if self._config.seed is not None else secrets.randbits(128)
        items = self._generate_items(root_seed)
        return self._artifact_writer.write(self._config, root_seed, items)

    def _generate_items(self, root_seed: int) -> tuple[GeneratedItem, ...]:
        scheduler = Random(_derive_seed(root_seed, "schedule"))
        generated = []
        for index in range(self._config.size):
            choice = self._generation_distribution.sample(scheduler)
            seed = _derive_seed(root_seed, f"item:{index}:{choice.domain}")
            request = GenerationRequest(seed=seed, difficulty=choice.difficulty)
            problem = choice.recipe.generate(request)
            item_id = self._get_problem_id(index, choice.domain, problem)
            generated.append(GeneratedItem(item_id, choice.domain, problem))
        return tuple(generated)

    @staticmethod
    def _get_problem_id(index: int, domain: str, problem: Problem[object]) -> str:
        visible = {
            "position": index,
            "domain": domain,
            "question": problem.prompt,
            "sections": [
                {"media_type": section.media_type, "content": section.content}
                for section in problem.sections
            ],
        }
        serialized = json.dumps(visible, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode()).hexdigest()[:20]

    def _build_generation_distribution(self) -> FiniteDistribution[GenerationSelection]:
        domains: FiniteDistribution[str] = FiniteDistribution.weighted(
            (domain, config.weight) for domain, config in self._config.domains.items()
        )

        def recipes_for(domain: str, difficulty: int) -> FiniteDistribution[IProblemRecipe[object]]:
            recipes = self._config.domains[domain].recipes
            if recipes:
                return self._catalog.configured_recipe_distribution(domain=domain, weights=recipes)
            return self._catalog.recipe_distribution(domain=domain, difficulty=difficulty)

        def distribution_within_domain(domain: str) -> FiniteDistribution[GenerationSelection]:
            config = self._config.domains[domain]
            difficulties = FiniteDistribution.weighted(config.generation_levels.items())
            return difficulties.bind(
                lambda difficulty: recipes_for(domain, difficulty).map(
                    lambda recipe: GenerationSelection(domain, difficulty, recipe)
                )
            )

        return domains.bind(distribution_within_domain)


def _derive_seed(root_seed: int, label: str) -> int:
    digest = hashlib.blake2b(f"{root_seed}:{label}".encode(), digest_size=16).digest()
    return int.from_bytes(digest)
