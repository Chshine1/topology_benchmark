"""Validated YAML probability profile for surface problem generation."""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml

from topology_benchmark.core.probability import interpolate_anchors

type ConfigMap = dict[str, object]


@dataclass(frozen=True, slots=True)
class AnchoredValue:
    anchors: tuple[tuple[int, float], ...]

    def at(self, difficulty: int) -> float:
        return interpolate_anchors(self.anchors, difficulty)


@dataclass(frozen=True, slots=True)
class DifficultyProfile:
    global_question_weight: AnchoredValue
    classification_question_weight: AnchoredValue
    path_question_weight: AnchoredValue
    polygon_count_weights: dict[int, AnchoredValue]
    side_continuation: AnchoredValue
    gluing_density: AnchoredValue
    path_continuation: AnchoredValue
    path_maximum: AnchoredValue
    visual_budget: AnchoredValue


@dataclass(frozen=True, slots=True)
class SurfaceGenerationConfig:
    profile_version: str
    noise_probability: float
    retry_limit: int
    difficulty: DifficultyProfile
    object_questions: dict[str, tuple[tuple[str, float], ...]]
    morphism_family_weights: dict[str, AnchoredValue]
    morphism_affinity: dict[str, dict[str, float]]

    def __post_init__(self) -> None:
        if not self.profile_version:
            raise ValueError("generation.profile_version must not be empty")
        if not 0 <= self.noise_probability <= 1:
            raise ValueError("generation.noise_probability must be a probability")
        if self.retry_limit < 1:
            raise ValueError("generation.retry_limit must be positive")
        probability_profiles = (
            self.difficulty.side_continuation,
            self.difficulty.gluing_density,
            self.difficulty.path_continuation,
        )
        if any(
            not 0 <= value <= 1 for profile in probability_profiles for _, value in profile.anchors
        ):
            raise ValueError("generation probability profiles must stay between zero and one")
        if not self.difficulty.polygon_count_weights or any(
            not 1 <= count <= 4 for count in self.difficulty.polygon_count_weights
        ):
            raise ValueError("polygon counts must stay between one and four")
        if any(not 1 <= value <= 7 for _, value in self.difficulty.path_maximum.anchors):
            raise ValueError("path maxima must stay between one and seven")
        expected_families = {
            "full-disk-boundary",
            "attachment",
            "partial-intercomponent",
            "self-boundary",
            "annulus-closure",
        }
        if set(self.morphism_family_weights) != expected_families:
            raise ValueError("generation profile must configure every morphism family")


def load_generation_config(override_path: str | Path | None = None) -> SurfaceGenerationConfig:
    default_path = Path(__file__).parent.parent / "generation.yaml"
    merged = _read_yaml(default_path)
    if override_path is not None:
        merged = _deep_merge(merged, _read_yaml(Path(override_path)))
    root = _section(merged, "generation")
    difficulty = _section(root, "difficulty")
    question_weights = _section(difficulty, "question_family_weights")
    polygon_counts = _section(difficulty, "polygon_count_weights")
    scalar = _section(difficulty, "scalar_profiles")
    questions = _section(root, "questions")
    morphisms = _section(root, "morphisms")
    return SurfaceGenerationConfig(
        _string(root, "profile_version"),
        _number(root, "noise_probability"),
        _integer(root, "retry_limit"),
        DifficultyProfile(
            _anchors(question_weights, "global"),
            _anchors(question_weights, "classification"),
            _anchors(question_weights, "path"),
            {
                int(key): _anchors_value(value, f"polygon_count_weights.{key}")
                for key, value in polygon_counts.items()
            },
            _anchors(scalar, "side_continuation"),
            _anchors(scalar, "gluing_density"),
            _anchors(scalar, "path_continuation"),
            _anchors(scalar, "path_maximum"),
            _anchors(scalar, "visual_budget"),
        ),
        _question_groups(_section(questions, "object")),
        {
            key: _anchors_value(value, f"morphisms.families.{key}")
            for key, value in _section(morphisms, "families").items()
        },
        {
            question: {
                family: _number_value(weight, f"morphisms.affinity.{question}.{family}")
                for family, weight in _mapping(value, question).items()
            }
            for question, value in _section(morphisms, "affinity").items()
        },
    )


def _question_groups(mapping: ConfigMap) -> dict[str, tuple[tuple[str, float], ...]]:
    return {
        group: tuple(
            (kind, _number_value(weight, f"questions.{group}.{kind}"))
            for kind, weight in _mapping(value, group).items()
        )
        for group, value in mapping.items()
    }


def _anchors(mapping: ConfigMap, key: str) -> AnchoredValue:
    if key not in mapping:
        raise ValueError(f"missing generation profile: {key}")
    return _anchors_value(mapping[key], key)


def _anchors_value(value: object, name: str) -> AnchoredValue:
    mapping = _mapping(value, name)
    points = tuple(
        sorted(
            (int(level), _number_value(weight, f"{name}.{level}"))
            for level, weight in mapping.items()
        )
    )
    if not points or any(not 1 <= level <= 10 for level, _ in points):
        raise ValueError(f"{name} needs anchors between difficulties 1 and 10")
    return AnchoredValue(points)


def _read_yaml(path: Path) -> ConfigMap:
    with path.open(encoding="utf-8") as stream:
        return _mapping(cast(object, yaml.safe_load(stream)), str(path))


def _deep_merge(base: ConfigMap, override: ConfigMap) -> ConfigMap:
    result = dict(base)
    for key, value in override.items():
        current = result.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            result[key] = _deep_merge(dict(current), dict(value))
        else:
            result[key] = value
    return result


def _mapping(value: object, name: str) -> ConfigMap:
    if not isinstance(value, dict) or not all(isinstance(key, str | int) for key in value):
        raise ValueError(f"{name} must be a YAML mapping")
    return {str(key): item for key, item in value.items()}


def _section(mapping: ConfigMap, key: str) -> ConfigMap:
    if key not in mapping:
        raise ValueError(f"missing generation configuration section: {key}")
    return _mapping(mapping[key], key)


def _number(mapping: ConfigMap, key: str) -> float:
    return _number_value(mapping.get(key), key)


def _number_value(value: object, key: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{key} must be a nonnegative number")
    return float(value)


def _integer(mapping: ConfigMap, key: str) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _string(mapping: ConfigMap, key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a nonempty string")
    return value
