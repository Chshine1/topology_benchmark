from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from topology_benchmark.core.configuration import load_yaml_config

type PositiveFloat = Annotated[float, Field(gt=0, allow_inf_nan=False)]
type Difficulty = Annotated[int, Field(ge=1, le=10)]


class _StrictConfigModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        allow_inf_nan=False,
    )


class WeightedConfig(_StrictConfigModel):
    weight: PositiveFloat
    generation_levels: dict[Difficulty, PositiveFloat]
    recipes: dict[Annotated[str, Field(min_length=1)], PositiveFloat]

    @model_validator(mode="after")
    def _has_generation_levels(self) -> Self:
        if not self.generation_levels:
            raise ValueError("generation_levels must not be empty")
        return self


class OpenAICompatibleModelProviderConfig(_StrictConfigModel):
    model: Annotated[str, Field(min_length=1)]
    base_url: Annotated[str, Field(min_length=1)]
    api_key_env: Annotated[str, Field(min_length=1)]
    timeout_seconds: PositiveFloat
    extra_headers: dict[str, str]


class EvaluationConfig(_StrictConfigModel):
    max_retries: Annotated[int, Field(ge=0)]


class DatasetConfig(_StrictConfigModel):
    size: Annotated[int, Field(gt=0)]
    output_dir: Path
    domains: dict[str, WeightedConfig]
    seed: int | None

    @model_validator(mode="after")
    def _has_domains(self) -> Self:
        if not self.domains:
            raise ValueError("at least one domain must be configured")
        return self


class ModelEvaluationConfig(_StrictConfigModel):
    evaluation: EvaluationConfig
    model_provider: OpenAICompatibleModelProviderConfig


class _RunConfig(_StrictConfigModel):
    seed: int | None
    size: Annotated[int, Field(gt=0)]
    output_dir: Annotated[str, Field(min_length=1)]


class _GenerationConfig(_StrictConfigModel):
    domains: dict[str, WeightedConfig]


class _DatasetDocument(_StrictConfigModel):
    run: _RunConfig
    generation: _GenerationConfig


class _EvaluationDocument(_StrictConfigModel):
    evaluation: EvaluationConfig
    model_provider: OpenAICompatibleModelProviderConfig


def load_dataset_config(path: str | Path) -> DatasetConfig:
    config_path = Path(path)
    document = load_yaml_config(config_path, _DatasetDocument)
    output = Path(document.run.output_dir)
    if not output.is_absolute():
        output = config_path.parent / output
    return DatasetConfig(
        size=document.run.size,
        output_dir=output.resolve(),
        domains=document.generation.domains,
        seed=document.run.seed,
    )


def load_evaluation_config(path: str | Path) -> ModelEvaluationConfig:
    config_path = Path(path)
    document = load_yaml_config(config_path, _EvaluationDocument)
    return ModelEvaluationConfig(
        evaluation=document.evaluation,
        model_provider=document.model_provider,
    )
