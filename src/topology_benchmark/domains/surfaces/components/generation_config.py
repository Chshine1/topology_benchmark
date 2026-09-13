from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Self, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from topology_benchmark.core.probability import interpolate_anchors
from topology_benchmark.domains.surfaces.generation import (
    MorphismFamily,
    MorphismFamilyAffinity,
)

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
    relational_question_weight: AnchoredValue
    target_only_question_weight: AnchoredValue
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
    subject_weights: dict[str, AnchoredValue]
    morphism_questions: dict[str, tuple[tuple[str, float], ...]]
    morphism_family_weights: dict[MorphismFamily, AnchoredValue]
    morphism_affinity: dict[str, MorphismFamilyAffinity]

    def affinity_for(self, question_id: str) -> MorphismFamilyAffinity:
        return self.morphism_affinity.get(question_id, MorphismFamilyAffinity())


class _QuestionFamilyWeights(_StrictConfigModel):
    global_: Anchors = Field(alias="global")
    classification: Anchors
    path: Anchors
    relational: Anchors
    target_only: Anchors = Field(alias="target-only")


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
    morphism: dict[str, dict[str, Nonnegative]]

    @model_validator(mode="after")
    def _uses_known_nonempty_families(self) -> Self:
        expected_object = {"global", "classification", "path"}
        expected_morphism = {"relational", "target-only"}
        if set(self.object) != expected_object or set(self.morphism) != expected_morphism:
            raise ValueError("questions must configure every known subject family")
        groups = (*self.object.values(), *self.morphism.values())
        if any(not group or not any(group.values()) for group in groups):
            raise ValueError("each question family needs a positive recipe weight")
        ids = [recipe for group in groups for recipe in group]
        if len(ids) != len(set(ids)):
            raise ValueError("recipe IDs must be unique across question families")
        return self


class _SubjectsInput(_StrictConfigModel):
    object: Anchors
    morphism: Anchors


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
    subjects: _SubjectsInput
    morphisms: _MorphismsInput

    @model_validator(mode="after")
    def _affinities_reference_registered_ids(self) -> Self:
        recipes = {recipe for group in self.questions.morphism.values() for recipe in group}
        families = set(self.morphisms.families)
        if set(self.morphisms.affinity) - recipes:
            raise ValueError("morphism affinity references an unknown recipe")
        if any(set(weights) - families for weights in self.morphisms.affinity.values()):
            raise ValueError("morphism affinity references an unknown family")
        return self


class _GenerationDocument(_StrictConfigModel):
    generation: _GenerationInput


def load_generation_config(
    default_path: str | Path,
    override_path: str | Path | None = None,
) -> SurfaceGenerationConfig:
    merged = _read_yaml(Path(default_path))
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
            relational_question_weight=_anchored(question_weights.relational),
            target_only_question_weight=_anchored(question_weights.target_only),
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
        subject_weights={
            "object": _anchored(source.subjects.object),
            "morphism": _anchored(source.subjects.morphism),
        },
        morphism_questions={
            group: tuple(weights.items()) for group, weights in source.questions.morphism.items()
        },
        morphism_family_weights={
            MorphismFamily(family): _anchored(anchors)
            for family, anchors in source.morphisms.families.items()
        },
        morphism_affinity={
            recipe: MorphismFamilyAffinity(
                **{family.replace("-", "_"): weight for family, weight in family_weights.items()}
            )
            for recipe, family_weights in source.morphisms.affinity.items()
        },
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
