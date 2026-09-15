import hashlib
import json
from random import Random

from topology_benchmark.core.problem.models import GenerationRequest, Problem
from topology_benchmark.pipeline.dataset.artifact_writer import DatasetArtifactWriter
from topology_benchmark.pipeline.dataset.models import (
    DatasetPlan,
    GeneratedBenchmarkRun,
    GeneratedItem,
)
from topology_benchmark.pipeline.dataset.planner import DatasetPlanner


class BenchmarkDatasetGenerator:
    def __init__(
        self,
        planner: DatasetPlanner,
        artifact_writer: DatasetArtifactWriter,
    ) -> None:
        self._planner = planner
        self._artifact_writer = artifact_writer

    def generate(self) -> GeneratedBenchmarkRun:
        plan = self._planner.create()
        items = self._generate_items(plan)
        return self._artifact_writer.write(plan, items)

    def _generate_items(self, plan: DatasetPlan) -> tuple[GeneratedItem, ...]:
        root_seed = plan.specification.root_seed
        scheduler = Random(_derive_seed(root_seed, "schedule"))
        generated = []
        for index in range(plan.specification.size):
            choice = plan.generation_distribution.sample(scheduler)
            seed = _derive_seed(root_seed, f"item:{index}:{choice.domain}:{choice.recipe.id}")
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


def _derive_seed(root_seed: int, label: str) -> int:
    digest = hashlib.blake2b(f"{root_seed}:{label}".encode(), digest_size=16).digest()
    return int.from_bytes(digest)
