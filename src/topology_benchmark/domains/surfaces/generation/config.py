from collections.abc import Mapping
from typing import Annotated, Literal, Self

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
from topology_benchmark.utils.distribution_model import (
    create_distribution_model,
    finite_distribution_from_config,
)

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
        arbitrary_types_allowed=True,
    )


class AnchoredValue(_StrictConfigModel):
    anchors: tuple[tuple[int, float], ...]

    def at(self, difficulty: int) -> float:
        return interpolate_anchors(self.anchors, difficulty)


class DifficultyProfile(_StrictConfigModel):
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
    component_count: Annotated[int, Field(ge=1, le=4)]
    paths: SurfacePathsConfig


SurfaceObjectOutcomeDistribution = create_distribution_model(SurfaceObjectOutcomeConfig)


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
    recipe_weights: dict[str, AnchoredValue]
    object_laws: dict[str, FiniteDistribution[SurfaceObjectCondition]]
    morphism_laws: dict[str, SurfaceMorphismLawProfile]

    def object_law_for(self, recipe_id: str) -> FiniteDistribution[SurfaceObjectCondition]:
        try:
            return self.object_laws[recipe_id]
        except KeyError as error:
            raise ConfigurationError(
                f"no surface-object law is configured for {recipe_id!r}"
            ) from error

    def morphism_law_for(self, recipe_id: str) -> SurfaceMorphismLawProfile:
        try:
            return self.morphism_laws[recipe_id]
        except KeyError as error:
            raise ConfigurationError(
                f"no surface-morphism law is configured for {recipe_id!r}"
            ) from error


class _RecipeFamilyWeights(_StrictConfigModel):
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
    recipe_family_weights: _RecipeFamilyWeights
    polygon_count_weights: Annotated[
        dict[PolygonCount, Anchors],
        Field(min_length=1),
    ]
    scalar_profiles: _ScalarProfiles


class _RecipesInput(_StrictConfigModel):
    object: dict[str, dict[str, Nonnegative]]
    morphism: dict[str, dict[str, Nonnegative]]

    @model_validator(mode="after")
    def _uses_known_nonempty_families(self) -> Self:
        expected_object = {"global", "classification", "path"}
        expected_morphism = {"relational", "target-only"}
        if set(self.object) != expected_object or set(self.morphism) != expected_morphism:
            raise ValueError("recipes must configure every known subject family")
        groups = (*self.object.values(), *self.morphism.values())
        if any(not group or not any(group.values()) for group in groups):
            raise ValueError("each recipe family needs a positive recipe weight")
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


class SurfaceGenerationInput(_StrictConfigModel):
    profile_version: Annotated[str, Field(min_length=1)]
    noise_probability: Probability
    retry_limit: Annotated[int, Field(ge=1)]
    morphism_retry_limit: Annotated[int, Field(ge=1)]
    difficulty: _DifficultyInput
    recipes: _RecipesInput
    object_laws: dict[str, SurfaceObjectOutcomeDistribution]
    subjects: _SubjectsInput
    morphisms: _MorphismsInput

    @model_validator(mode="after")
    def _has_complete_morphism_laws(self) -> Self:
        recipes = {recipe for group in self.recipes.morphism.values() for recipe in group}
        families = set(self.morphisms.families)
        if set(self.morphisms.affinity) != recipes:
            raise ValueError("morphism affinities must configure every morphism recipe ID")
        if any(set(weights) != families for weights in self.morphisms.affinity.values()):
            raise ValueError("each morphism affinity must configure every morphism family")
        return self

    @model_validator(mode="after")
    def _has_a_nonempty_law_for_every_object_recipe(self) -> Self:
        recipes = {recipe for group in self.recipes.object.values() for recipe in group}
        if set(self.object_laws) != recipes:
            raise ValueError("object laws must configure every object recipe ID")
        return self


def resolve_surface_generation_config(
    source: SurfaceGenerationInput,
) -> SurfaceGenerationConfig:
    scalar = source.difficulty.scalar_profiles
    return SurfaceGenerationConfig(
        profile_version=source.profile_version,
        noise_probability=source.noise_probability,
        retry_limit=source.retry_limit,
        morphism_retry_limit=source.morphism_retry_limit,
        difficulty=DifficultyProfile(
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
        recipe_weights=_recipe_weight_profiles(source),
        object_laws={
            recipe_id: finite_distribution_from_config(outcomes).map(
                lambda outcome: SurfaceObjectCondition(
                    outcome.component_count,
                    _surface_paths(outcome.paths),
                )
            )
            for recipe_id, outcomes in source.object_laws.items()
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


def _recipe_weight_profiles(source: SurfaceGenerationInput) -> dict[str, AnchoredValue]:
    recipe_ids = tuple(
        recipe_id
        for groups in (source.recipes.object, source.recipes.morphism)
        for recipes in groups.values()
        for recipe_id in recipes
    )
    anchors = {recipe_id: [] for recipe_id in recipe_ids}
    for difficulty in range(1, 11):
        distribution = _recipe_id_distribution(source, difficulty)
        for recipe_id in recipe_ids:
            anchors[recipe_id].append(
                (
                    difficulty,
                    _recipe_probability(distribution, recipe_id),
                )
            )
    return {
        recipe_id: AnchoredValue(anchors=tuple(weights)) for recipe_id, weights in anchors.items()
    }


def _recipe_probability(distribution: FiniteDistribution[str], recipe_id: str) -> float:
    return distribution.probability(lambda value: value == recipe_id)


def _recipe_id_distribution(
    source: SurfaceGenerationInput, difficulty: int
) -> FiniteDistribution[str]:
    family_weights = source.difficulty.recipe_family_weights
    families = {
        "object": (
            ("global", _weight_at(family_weights.global_, difficulty)),
            ("classification", _weight_at(family_weights.classification, difficulty)),
            ("path", _weight_at(family_weights.path, difficulty)),
        ),
        "morphism": (
            ("relational", _weight_at(family_weights.relational, difficulty)),
            ("target-only", _weight_at(family_weights.target_only, difficulty)),
        ),
    }
    configured = {
        "object": source.recipes.object,
        "morphism": source.recipes.morphism,
    }
    subjects = FiniteDistribution.weighted(
        (
            ("object", _weight_at(source.subjects.object, difficulty)),
            ("morphism", _weight_at(source.subjects.morphism, difficulty)),
        )
    )
    return subjects.bind(
        lambda subject: FiniteDistribution.weighted(families[subject]).bind(
            lambda family: FiniteDistribution.weighted(configured[subject][family].items())
        )
    )


def _weight_at(anchors: Anchors, difficulty: int) -> float:
    return interpolate_anchors(tuple(anchors.items()), difficulty)


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
