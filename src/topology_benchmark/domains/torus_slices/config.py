from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from topology_benchmark.core.configuration import load_yaml_config

type Probability = Annotated[float, Field(ge=0, le=1)]
type Difficulty = Annotated[int, Field(ge=1, le=10)]
type Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
type RecipeWeights = Annotated[dict[Difficulty, Nonnegative], Field(min_length=1)]


class _StrictConfigModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class TorusCountConfig(_StrictConfigModel):
    easy_maximum: Annotated[int, Field(ge=1)]
    standard_maximum: Annotated[int, Field(ge=1)]
    linked_probability: Probability


class TorusLinkConfig(_StrictConfigModel):
    minimum_count: Annotated[int, Field(ge=2, le=4)]
    maximum_count: Annotated[int, Field(ge=2, le=4)]
    chain_probability: Probability
    complete_probability: Probability

    @model_validator(mode="after")
    def _has_valid_range_and_probabilities(self) -> Self:
        if self.minimum_count > self.maximum_count:
            raise ValueError("torus link counts must lie between two and four")
        if self.chain_probability + self.complete_probability > 1:
            raise ValueError("torus link pattern probabilities are invalid")
        return self


class TorusGenerationConfig(_StrictConfigModel):
    profile_version: Annotated[str, Field(min_length=1)]
    count: TorusCountConfig
    link: TorusLinkConfig
    recipe_weights: dict[str, RecipeWeights]

    @model_validator(mode="after")
    def _has_positive_recipe_weights(self) -> Self:
        if not self.recipe_weights or any(
            not any(weights.values()) for weights in self.recipe_weights.values()
        ):
            raise ValueError("each torus recipe needs a positive weight")
        return self


class TorusDomainConfig(_StrictConfigModel):
    generation: TorusGenerationConfig


def load_torus_domain_config(path: str | Path) -> TorusDomainConfig:
    return load_yaml_config(path, TorusDomainConfig)
