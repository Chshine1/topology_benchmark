from dataclasses import dataclass
from pathlib import Path
from typing import Any

from topology_benchmark.core.problem.models import Problem


@dataclass(frozen=True, slots=True)
class GeneratedItem:
    item_id: str
    domain: str
    problem: Problem[Any]


@dataclass(frozen=True, slots=True)
class GeneratedBenchmarkRun:
    directory: Path
    items: tuple[GeneratedItem, ...]
