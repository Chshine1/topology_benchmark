from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from topology_benchmark.core.configuration import load_yaml_config

type PositiveInteger = Annotated[int, Field(ge=1)]
type Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
type Difficulty = Annotated[int, Field(ge=1, le=10)]
type RecipeWeights = Annotated[dict[Difficulty, Nonnegative], Field(min_length=1)]


class _StrictConfigModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class VertexPartitionConfig(_StrictConfigModel):
    attempts: PositiveInteger
    easy_mark_count: PositiveInteger
    hard_mark_count: PositiveInteger
    hard_from: PositiveInteger


class VertexDegreeConfig(_StrictConfigModel):
    attempts: PositiveInteger


class CurvatureOrderConfig(_StrictConfigModel):
    attempts: PositiveInteger
    exact_margin: Nonnegative
    visible_margin: Annotated[int, Field(ge=0)]


class SeamMatchConfig(_StrictConfigModel):
    attempts: PositiveInteger
    candidate_count: PositiveInteger


class CellDistanceConfig(_StrictConfigModel):
    attempts: PositiveInteger
    edge_cells_from: PositiveInteger
    vertex_cells_from: PositiveInteger
    candidate_limit: PositiveInteger


class PolyhedralGenerationConfig(_StrictConfigModel):
    profile_version: Annotated[str, Field(min_length=1)]
    vertex_partition: VertexPartitionConfig
    vertex_degree: VertexDegreeConfig
    curvature_order: CurvatureOrderConfig
    seam_match: SeamMatchConfig
    cell_distance: CellDistanceConfig
    recipe_weights: dict[str, RecipeWeights]

    @model_validator(mode="after")
    def _has_positive_recipe_weights(self) -> Self:
        if not self.recipe_weights or any(
            not any(weights.values()) for weights in self.recipe_weights.values()
        ):
            raise ValueError("each polyhedral recipe needs a positive weight")
        return self


class PolyhedralDomainConfig(_StrictConfigModel):
    generation: PolyhedralGenerationConfig


def load_polyhedral_domain_config(path: str | Path) -> PolyhedralDomainConfig:
    return load_yaml_config(path, PolyhedralDomainConfig)
