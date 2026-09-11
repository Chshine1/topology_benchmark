"""Validated YAML configuration for benchmark runs."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class WeightedConfig:
    weight: float = 1.0
    generation_levels: dict[int, float] = field(default_factory=lambda: {5: 1.0})
    question_kinds: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError("domain weight must be positive")
        if not self.generation_levels or any(
            not 1 <= level <= 10 or weight <= 0 for level, weight in self.generation_levels.items()
        ):
            raise ValueError("generation_levels need positive weights at levels 1 through 10")
        if any(not kind or weight <= 0 for kind, weight in self.question_kinds.items()):
            raise ValueError("question_kinds need nonempty names and positive weights")


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    kind: str = "fixed"
    model: str = ""
    base_url: str = ""
    api_key_env: str = "BENCHMARK_API_KEY"
    fixed_response: str = ""
    timeout_seconds: float = 60.0
    max_retries: int = 2
    extra_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in {"fixed", "openai-compatible"}:
            raise ValueError("provider kind must be 'fixed' or 'openai-compatible'")
        if self.kind == "openai-compatible" and (not self.model or not self.base_url):
            raise ValueError("an OpenAI-compatible provider needs model and base_url")
        if self.timeout_seconds <= 0:
            raise ValueError("provider timeout_seconds must be positive")
        if self.max_retries < 0:
            raise ValueError("provider max_retries cannot be negative")


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    size: int
    output_dir: Path
    domains: dict[str, WeightedConfig]
    seed: int | None = None
    max_generation_attempts: int = 100
    provider: ProviderConfig | None = None

    def __post_init__(self) -> None:
        known = {"surfaces", "polyhedral-nets", "torus-slices"}
        if self.size <= 0:
            raise ValueError("size must be positive")
        if not self.domains or set(self.domains) - known:
            raise ValueError(f"domains must be selected from {sorted(known)}")
        if self.max_generation_attempts <= 0:
            raise ValueError("max_generation_attempts must be positive")


def load_pipeline_config(path: str | Path) -> PipelineConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("pipeline configuration must be a YAML mapping")
    run = _mapping(raw.get("run", {}), "run")
    generation = _mapping(raw.get("generation", {}), "generation")
    raw_domains = _mapping(generation.get("domains", {}), "generation.domains")
    domains: dict[str, WeightedConfig] = {}
    for name, value in raw_domains.items():
        item = _mapping(value, f"generation.domains.{name}")
        levels = _numeric_weights(item.get("generation_levels", {5: 1.0}), "generation_levels")
        kinds = {
            str(key): float(weight)
            for key, weight in _mapping(item.get("question_kinds", {}), "question_kinds").items()
        }
        domains[str(name)] = WeightedConfig(float(item.get("weight", 1.0)), levels, kinds)
    provider_raw = raw.get("provider")
    provider = None
    if provider_raw is not None:
        item = _mapping(provider_raw, "provider")
        provider = ProviderConfig(
            kind=str(item.get("kind", "fixed")),
            model=str(item.get("model", "")),
            base_url=str(item.get("base_url", "")),
            api_key_env=str(item.get("api_key_env", "BENCHMARK_API_KEY")),
            fixed_response=str(item.get("fixed_response", "")),
            timeout_seconds=float(item.get("timeout_seconds", 60)),
            max_retries=int(item.get("max_retries", 2)),
            extra_headers={
                str(key): str(value)
                for key, value in _mapping(item.get("extra_headers", {}), "extra_headers").items()
            },
        )
    output = Path(str(run.get("output_dir", "benchmark-runs")))
    if not output.is_absolute():
        output = config_path.parent / output
    seed_value = run.get("seed")
    return PipelineConfig(
        size=int(run.get("size", 100)),
        output_dir=output.resolve(),
        domains=domains,
        seed=None if seed_value is None else int(seed_value),
        max_generation_attempts=int(generation.get("max_attempts_per_item", 100)),
        provider=provider,
    )


def _mapping(value: Any, name: str) -> dict[Any, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a YAML mapping")
    return value


def _numeric_weights(value: Any, name: str) -> dict[int, float]:
    return {int(key): float(weight) for key, weight in _mapping(value, name).items()}
