from dataclasses import dataclass
from pathlib import Path
from typing import Any

from topology_benchmark.core.probability.distribution import FiniteDistribution
from topology_benchmark.core.problem.models import Problem
from topology_benchmark.core.problem.recipe import IProblemRecipe


@dataclass(frozen=True, slots=True)
class GenerationSelection:
    domain: str
    difficulty: int
    recipe: IProblemRecipe[object]


@dataclass(frozen=True, slots=True)
class SelectionProbability:
    domain: str
    difficulty: int
    recipe_id: str
    probability: float


@dataclass(frozen=True, slots=True)
class DatasetSpecification:
    schema_version: int
    root_seed: int
    size: int
    selection: tuple[SelectionProbability, ...]
    domain_fingerprints: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class DatasetPlan:
    output_directory: Path
    dataset_id: str
    specification: DatasetSpecification
    generation_distribution: FiniteDistribution[GenerationSelection]


@dataclass(frozen=True, slots=True)
class GeneratedItem:
    item_id: str
    domain: str
    problem: Problem[Any]


@dataclass(frozen=True, slots=True)
class GeneratedBenchmarkRun:
    directory: Path
    dataset_id: str
    content_id: str
    items: tuple[GeneratedItem, ...]
