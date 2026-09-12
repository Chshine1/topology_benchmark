from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Self, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from topology_benchmark.core.probability import interpolate_anchors

type ConfigMap = dict[str, object]
type Difficulty = Annotated[int, Field(ge=1, le=10)]
type PolygonCount = Annotated[int, Field(ge=1, le=4)]
type Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
type Probability = Annotated[float, Field(ge=0, le=1)]
type PathMaximum = Annotated[float, Field(ge=1, le=7)]
type Anchors = Annotated[dict[Difficulty, Nonnegative], Field(min_length=1)]
type ProbabilityAnchors = Annotated[dict[Difficulty, Probability], Field(min_length=1)]
type PathMaximumAnchors = Annotated[dict[Difficulty, PathMaximum], Field(min_length=1)]


class _StrictConfigModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        validate_default=True,
    )


class AnchoredValue(_StrictConfigModel):
    anchors: tuple[tuple[int, float], ...]

    def at(self, difficulty: int) -> float:
        return interpolate_anchors(self.anchors, difficulty)


class DifficultyProfile(_StrictConfigModel):
    global_question_weight: AnchoredValue
    classification_question_weight: AnchoredValue
    path_question_weight: AnchoredValue
    polygon_count_weights: dict[int, AnchoredValue]
    side_continuation: AnchoredValue
    gluing_density: AnchoredValue
    path_continuation: AnchoredValue
    path_maximum: AnchoredValue
    visual_budget: AnchoredValue


class SurfaceGenerationConfig(_StrictConfigModel):
    profile_version: str
    noise_probability: float
    retry_limit: int
    difficulty: DifficultyProfile
    object_questions: dict[str, tuple[tuple[str, float], ...]]
    morphism_family_weights: dict[str, AnchoredValue]
    morphism_affinity: dict[str, dict[str, float]]


class _QuestionFamilyWeights(_StrictConfigModel):
    global_: Anchors = Field(alias="global")
    classification: Anchors
    path: Anchors


class _ScalarProfiles(_StrictConfigModel):
    side_continuation: ProbabilityAnchors
    gluing_density: ProbabilityAnchors
    path_continuation: ProbabilityAnchors
    path_maximum: PathMaximumAnchors
    visual_budget: Anchors


class _DifficultyInput(_StrictConfigModel):
    question_family_weights: _QuestionFamilyWeights
    polygon_count_weights: Annotated[
        dict[PolygonCount, Anchors],
        Field(min_length=1),
    ]
    scalar_profiles: _ScalarProfiles


class _QuestionsInput(_StrictConfigModel):
    object: dict[str, dict[str, Nonnegative]]


class _MorphismsInput(_StrictConfigModel):
    families: dict[str, Anchors]
    affinity: dict[str, dict[str, Nonnegative]]

    @model_validator(mode="after")
    def _has_every_family(self) -> Self:
        expected = {
            "full-disk-boundary",
            "attachment",
            "partial-intercomponent",
            "self-boundary",
            "annulus-closure",
        }
        if set(self.families) != expected:
            raise ValueError("generation profile must configure every morphism family")
        return self


class _GenerationInput(_StrictConfigModel):
    profile_version: Annotated[str, Field(min_length=1)]
    noise_probability: Probability
    retry_limit: Annotated[int, Field(ge=1)]
    difficulty: _DifficultyInput
    questions: _QuestionsInput
    morphisms: _MorphismsInput


class _GenerationDocument(_StrictConfigModel):
    generation: _GenerationInput


def load_generation_config(override_path: str | Path | None = None) -> SurfaceGenerationConfig:
    default_path = Path(__file__).parent.parent / "generation.yaml"
    merged = _read_yaml(default_path)
    if override_path is not None:
        merged = _deep_merge(merged, _read_yaml(Path(override_path)))
    source = _GenerationDocument.model_validate(merged).generation
    question_weights = source.difficulty.question_family_weights
    scalar = source.difficulty.scalar_profiles
    return SurfaceGenerationConfig(
        profile_version=source.profile_version,
        noise_probability=source.noise_probability,
        retry_limit=source.retry_limit,
        difficulty=DifficultyProfile(
            global_question_weight=_anchored(question_weights.global_),
            classification_question_weight=_anchored(question_weights.classification),
            path_question_weight=_anchored(question_weights.path),
            polygon_count_weights={
                count: _anchored(anchors)
                for count, anchors in source.difficulty.polygon_count_weights.items()
            },
            side_continuation=_anchored(scalar.side_continuation),
            gluing_density=_anchored(scalar.gluing_density),
            path_continuation=_anchored(scalar.path_continuation),
            path_maximum=_anchored(scalar.path_maximum),
            visual_budget=_anchored(scalar.visual_budget),
        ),
        object_questions={
            group: tuple(weights.items()) for group, weights in source.questions.object.items()
        },
        morphism_family_weights={
            family: _anchored(anchors) for family, anchors in source.morphisms.families.items()
        },
        morphism_affinity=source.morphisms.affinity,
    )


def _anchored(values: Mapping[int, float]) -> AnchoredValue:
    return AnchoredValue(anchors=tuple(sorted(values.items())))


def _read_yaml(path: Path) -> ConfigMap:
    with path.open(encoding="utf-8") as stream:
        value = cast(object, yaml.safe_load(stream))
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{path} must be a YAML mapping with string keys")
    return cast(ConfigMap, value)


def _deep_merge(base: ConfigMap, override: ConfigMap) -> ConfigMap:
    result = dict(base)
    for key, value in override.items():
        current = result.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            result[key] = _deep_merge(dict(current), dict(value))
        else:
            result[key] = value
    return result
