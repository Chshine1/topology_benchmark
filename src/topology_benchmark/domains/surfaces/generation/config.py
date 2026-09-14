from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Literal, Self, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from topology_benchmark.core.errors import ConfigurationError
from topology_benchmark.core.probability.distribution import (
    FiniteDistribution,
    WeightedValue,
)
from topology_benchmark.core.probability.interpolation import blended_weight, interpolate_anchors
from topology_benchmark.domains.surfaces.generation.context.morphism import (
    AnnulusClosureCondition,
    AttachmentCondition,
    FullDiskBoundaryCondition,
    PartialIntercomponentCondition,
    SelfBoundaryCondition,
    SurfaceMorphismCondition,
)
from topology_benchmark.domains.surfaces.generation.context.object import (
    DistinguishedSurfacePaths,
    NontrivialHomologySurfacePath,
    NoSurfacePaths,
    SurfaceObjectCondition,
    SurfacePathCondition,
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
type MorphismFamilyId = Literal[
    "full-disk-boundary",
    "attachment",
    "partial-intercomponent",
    "self-boundary",
    "annulus-closure",
]


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


class NoSurfacePathsConfig(_StrictConfigModel):
    kind: Literal["none"]


class DistinguishedSurfacePathsConfig(_StrictConfigModel):
    kind: Literal["distinguished"]
    count: Annotated[int, Field(ge=1, le=2)]
    first_closed: bool


class NontrivialHomologySurfacePathConfig(_StrictConfigModel):
    kind: Literal["nontrivial-homology"]


type SurfacePathsConfig = Annotated[
    NoSurfacePathsConfig | DistinguishedSurfacePathsConfig | NontrivialHomologySurfacePathConfig,
    Field(discriminator="kind"),
]


class SurfaceObjectOutcomeConfig(_StrictConfigModel):
    weight: Nonnegative
    component_count: Annotated[int, Field(ge=1, le=4)]
    paths: SurfacePathsConfig


class MorphismLawChoice(_StrictConfigModel):
    family: MorphismFamilyId
    weights: AnchoredValue
    affinity: Nonnegative


class SurfaceMorphismLawProfile(_StrictConfigModel):
    choices: tuple[MorphismLawChoice, ...]
    noise_probability: Probability

    def at(self, difficulty: int) -> FiniteDistribution[SurfaceMorphismCondition]:
        return FiniteDistribution(
            tuple(
                WeightedValue(
                    _morphism_condition(choice.family),
                    blended_weight(
                        choice.weights.at(difficulty) * choice.affinity,
                        choice.weights.at(difficulty),
                        self.noise_probability,
                    ),
                )
                for choice in self.choices
            )
        )


class SurfaceGenerationConfig(_StrictConfigModel):
    profile_version: str
    noise_probability: float
    retry_limit: int
    morphism_retry_limit: int
    difficulty: DifficultyProfile
    object_questions: dict[str, tuple[tuple[str, float], ...]]
    object_laws: dict[str, tuple[SurfaceObjectOutcomeConfig, ...]]
    subject_weights: dict[str, AnchoredValue]
    morphism_questions: dict[str, tuple[tuple[str, float], ...]]
    morphism_laws: dict[str, SurfaceMorphismLawProfile]

    def object_law_for(self, question_id: str) -> FiniteDistribution[SurfaceObjectCondition]:
        try:
            outcomes = self.object_laws[question_id]
        except KeyError as error:
            raise ConfigurationError(
                f"no surface-object law is configured for {question_id!r}"
            ) from error
        return FiniteDistribution(
            tuple(
                WeightedValue(
                    SurfaceObjectCondition(
                        outcome.component_count,
                        _surface_paths(outcome.paths),
                    ),
                    outcome.weight,
                )
                for outcome in outcomes
            )
        )

    def morphism_law_for(self, question_id: str) -> SurfaceMorphismLawProfile:
        try:
            return self.morphism_laws[question_id]
        except KeyError as error:
            raise ConfigurationError(
                f"no surface-morphism law is configured for {question_id!r}"
            ) from error


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
    families: dict[MorphismFamilyId, Anchors]
    affinity: dict[str, dict[MorphismFamilyId, Nonnegative]]

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
    morphism_retry_limit: Annotated[int, Field(ge=1)]
    difficulty: _DifficultyInput
    questions: _QuestionsInput
    object_laws: dict[str, dict[str, SurfaceObjectOutcomeConfig]]
    subjects: _SubjectsInput
    morphisms: _MorphismsInput

    @model_validator(mode="after")
    def _has_complete_morphism_laws(self) -> Self:
        recipes = {recipe for group in self.questions.morphism.values() for recipe in group}
        families = set(self.morphisms.families)
        if set(self.morphisms.affinity) != recipes:
            raise ValueError("morphism affinities must configure every morphism question ID")
        if any(set(weights) != families for weights in self.morphisms.affinity.values()):
            raise ValueError("each morphism affinity must configure every morphism family")
        return self

    @model_validator(mode="after")
    def _has_a_nonempty_law_for_every_object_question(self) -> Self:
        recipes = {recipe for group in self.questions.object.values() for recipe in group}
        if set(self.object_laws) != recipes:
            raise ValueError("object laws must configure every object question ID")
        if any(
            not outcomes or not any(item.weight for item in outcomes.values())
            for outcomes in self.object_laws.values()
        ):
            raise ValueError("each surface-object law needs positive total weight")
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
        morphism_retry_limit=source.morphism_retry_limit,
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
        object_laws={
            question_id: tuple(outcomes.values())
            for question_id, outcomes in source.object_laws.items()
        },
        subject_weights={
            "object": _anchored(source.subjects.object),
            "morphism": _anchored(source.subjects.morphism),
        },
        morphism_questions={
            group: tuple(weights.items()) for group, weights in source.questions.morphism.items()
        },
        morphism_laws={
            recipe: SurfaceMorphismLawProfile(
                choices=tuple(
                    MorphismLawChoice(
                        family=family,
                        weights=_anchored(source.morphisms.families[family]),
                        affinity=affinity,
                    )
                    for family, affinity in family_affinities.items()
                ),
                noise_probability=source.noise_probability,
            )
            for recipe, family_affinities in source.morphisms.affinity.items()
        },
    )


def _surface_paths(value: SurfacePathsConfig) -> SurfacePathCondition:
    if isinstance(value, NoSurfacePathsConfig):
        return NoSurfacePaths()
    if isinstance(value, DistinguishedSurfacePathsConfig):
        return DistinguishedSurfacePaths(value.count, value.first_closed)
    return NontrivialHomologySurfacePath()


def _morphism_condition(family: MorphismFamilyId) -> SurfaceMorphismCondition:
    return {
        "full-disk-boundary": FullDiskBoundaryCondition(),
        "attachment": AttachmentCondition(),
        "partial-intercomponent": PartialIntercomponentCondition(),
        "self-boundary": SelfBoundaryCondition(),
        "annulus-closure": AnnulusClosureCondition(),
    }[family]


def _anchored(values: Mapping[int, float]) -> AnchoredValue:
    return AnchoredValue(anchors=tuple(sorted(values.items())))


def _read_yaml(path: Path) -> ConfigMap:
    with path.open(encoding="utf-8") as stream:
        value = cast(object, yaml.safe_load(stream))
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ConfigurationError(f"{path} must be a YAML mapping with string keys")
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
