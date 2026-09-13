from pathlib import Path
from typing import Annotated, Self, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

type PositiveFloat = Annotated[float, Field(gt=0)]
type Difficulty = Annotated[int, Field(ge=1, le=10)]


class _StrictConfigModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        validate_default=True,
    )


class WeightedConfig(_StrictConfigModel):
    weight: PositiveFloat = 1.0
    generation_levels: dict[Difficulty, PositiveFloat] = Field(default_factory=lambda: {5: 1.0})
    recipes: dict[Annotated[str, Field(min_length=1)], PositiveFloat] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _has_generation_levels(self) -> Self:
        if not self.generation_levels:
            raise ValueError("generation_levels must not be empty")
        return self


class OpenAICompatibleModelProviderConfig(_StrictConfigModel):
    model: Annotated[str, Field(min_length=1)]
    base_url: Annotated[str, Field(min_length=1)]
    api_key_env: str = "BENCHMARK_API_KEY"
    timeout_seconds: PositiveFloat = 60.0
    extra_headers: dict[str, str] = Field(default_factory=dict)


class EvaluationConfig(_StrictConfigModel):
    max_retries: Annotated[int, Field(ge=0)] = 2


class PipelineConfig(_StrictConfigModel):
    size: Annotated[int, Field(gt=0)]
    output_dir: Path
    domains: dict[str, WeightedConfig]
    seed: int | None = None
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    model_provider: OpenAICompatibleModelProviderConfig | None = None

    @model_validator(mode="after")
    def _has_domains(self) -> Self:
        if not self.domains:
            raise ValueError("at least one domain must be configured")
        return self


class _RunConfig(_StrictConfigModel):
    seed: int | None = None
    size: Annotated[int, Field(gt=0)] = 100
    output_dir: str = "benchmark-runs"


class _GenerationConfig(_StrictConfigModel):
    domains: dict[str, WeightedConfig]


class _PipelineDocument(_StrictConfigModel):
    run: _RunConfig = Field(default_factory=_RunConfig)
    generation: _GenerationConfig
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    model_provider: OpenAICompatibleModelProviderConfig | None = None


def load_pipeline_config(path: str | Path) -> PipelineConfig:
    config_path = Path(path)
    raw = cast(object, yaml.safe_load(config_path.read_text(encoding="utf-8")))
    document = _PipelineDocument.model_validate(raw)
    output = Path(document.run.output_dir)
    if not output.is_absolute():
        output = config_path.parent / output
    return PipelineConfig(
        size=document.run.size,
        output_dir=output.resolve(),
        domains=document.generation.domains,
        seed=document.run.seed,
        evaluation=document.evaluation,
        model_provider=document.model_provider,
    )
