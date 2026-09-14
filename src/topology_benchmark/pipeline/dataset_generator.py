import hashlib
import json
import secrets
from random import Random

from topology_benchmark.application.catalog import BenchmarkCatalog
from topology_benchmark.core.problem.models import GenerationRequest, Problem
from topology_benchmark.pipeline.config import PipelineConfig
from topology_benchmark.pipeline.dataset.artifact_writer import DatasetArtifactWriter
from topology_benchmark.pipeline.dataset.models import GeneratedBenchmarkRun, GeneratedItem


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

    def _validate_configuration(self) -> None:
        for domain, config in self._config.domains.items():
            self._catalog.require_domain(domain)
            for recipe in config.recipes:
                self._catalog.require_question(domain, recipe)

    def generate(self) -> GeneratedBenchmarkRun:
        root_seed = self._config.seed if self._config.seed is not None else secrets.randbits(128)
        items = self.generate_items(root_seed)
        return self._artifact_writer.write(self._config, root_seed, items)

    def generate_items(self, root_seed: int) -> tuple[GeneratedItem, ...]:
        scheduler = Random(_derive_seed(root_seed, "schedule"))
        generated = []
        for index in range(self._config.size):
            domain = _weighted_choice(
                scheduler, {key: value.weight for key, value in self._config.domains.items()}
            )
            domain_config = self._config.domains[domain]
            level = _weighted_choice(scheduler, domain_config.generation_levels)
            seed = _derive_seed(root_seed, f"item:{index}:{domain}")
            request = GenerationRequest(seed=seed, difficulty=int(level))
            if domain_config.recipes:
                problem = self._catalog.generate_recipe(
                    domain=domain,
                    request=request,
                    recipe_id=_weighted_choice(scheduler, domain_config.recipes),
                )
            else:
                problem = self._catalog.generate(domain=domain, request=request)
            item_id = _problem_id(index, domain, problem)
            generated.append(GeneratedItem(item_id, domain, problem))
        return tuple(generated)


def _weighted_choice[ValueT](rng: Random, weights: dict[ValueT, float]) -> ValueT:
    point = rng.random() * sum(weights.values())
    cumulative = 0.0
    for value, weight in weights.items():
        cumulative += weight
        if point < cumulative:
            return value
    return next(reversed(weights))


def _derive_seed(root_seed: int, label: str) -> int:
    digest = hashlib.blake2b(f"{root_seed}:{label}".encode(), digest_size=16).digest()
    return int.from_bytes(digest)


def _problem_id(index: int, domain: str, problem: Problem[object]) -> str:
    visible = {
        "position": index,
        "domain": domain,
        "question": problem.question,
        "sections": [
            {"media_type": section.media_type, "content": section.content}
            for section in problem.sections
        ],
    }
    serialized = json.dumps(visible, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()[:20]
