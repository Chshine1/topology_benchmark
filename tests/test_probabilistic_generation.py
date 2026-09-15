from collections import Counter
from pathlib import Path
from random import Random
from typing import cast

import pytest
import yaml

from topology_benchmark import build_container
from topology_benchmark.application.configuration import SURFACE_DOMAIN_CONFIG
from topology_benchmark.core.probability.distribution import (
    FiniteDistribution,
    TruncatedGeometricDistribution,
    WeightedValue,
)
from topology_benchmark.core.probability.interpolation import interpolate_anchors
from topology_benchmark.core.probability.sampling import SamplingSession
from topology_benchmark.core.problem.models import GenerationRequest
from topology_benchmark.domains.surfaces.abstractions import (
    ISurfaceGenerator,
    ISurfaceMorphismGenerator,
    SurfaceProblemRecipeDistribution,
)
from topology_benchmark.domains.surfaces.config import load_surface_domain_config
from topology_benchmark.domains.surfaces.generation.config import SurfaceGenerationConfig
from topology_benchmark.domains.surfaces.generation.context.object import (
    DistinguishedSurfacePaths,
    NoSurfacePaths,
    SurfaceObjectCondition,
    SurfaceObjectGenerationContext,
)
from topology_benchmark.domains.surfaces.generation.generator.morphism import (
    RandomSurfaceMorphismGenerator,
)
from topology_benchmark.domains.surfaces.generation.generator.object import (
    RandomSurfacePresentationGenerator,
)
from topology_benchmark.domains.surfaces.services import SurfaceAnalyzer


def _generation_config() -> SurfaceGenerationConfig:
    return load_surface_domain_config(SURFACE_DOMAIN_CONFIG).generation


def test_named_random_streams_are_reproducible_and_independent() -> None:
    first = SamplingSession(41, "v1")
    expected = first.sample(
        "relevant", FiniteDistribution((WeightedValue("a", 1), WeightedValue("b", 2)))
    )

    second = SamplingSession(41, "v1")
    second.sample("unrelated", TruncatedGeometricDistribution(1, 7, 0.6))
    actual = second.sample(
        "relevant", FiniteDistribution((WeightedValue("a", 1), WeightedValue("b", 2)))
    )

    assert actual == expected
    assert SamplingSession(41, "v2").rng("relevant").random() != first.rng("relevant").random()


def test_difficulty_profiles_interpolate_smoothly() -> None:
    anchors = ((1, 0.1), (4, 0.4), (10, 1.0))

    assert interpolate_anchors(anchors, 1) == 0.1
    assert interpolate_anchors(anchors, 3) == pytest.approx(0.3)
    assert interpolate_anchors(anchors, 7) == pytest.approx(0.7)
    assert interpolate_anchors(anchors, 10) == 1.0


def test_default_recipe_distribution_follows_configured_cohort_weights() -> None:
    config = _generation_config()
    distribution = build_container().resolve(SurfaceProblemRecipeDistribution)

    def cohort(difficulty: int) -> Counter[str]:
        return Counter(distribution.at(difficulty).sample(Random(seed)).id for seed in range(2000))

    easy, hard = cohort(1), cohort(10)
    morphism_ids = set(config.morphism_laws)
    path_ids = {"path-is-cycle", "path-representative"}
    assert 0 < sum(easy[question] for question in morphism_ids) < 0.10 * 2000
    assert sum(hard[question] for question in morphism_ids) > 0.20 * 2000
    assert (
        sum(hard[question] for question in path_ids)
        > sum(easy[question] for question in path_ids) * 3
    )


def test_paths_are_question_aligned_but_allow_low_rate_noise() -> None:
    config = _generation_config()
    generator = RandomSurfacePresentationGenerator(config, SurfaceAnalyzer())
    incidental = 0
    cohort_size = 500
    for seed in range(cohort_size):
        request = GenerationRequest(seed, 7)
        sampling = SamplingSession(seed, config.profile_version)
        law = config.object_law_for("euler-characteristic")
        surface = generator.generate_for(SurfaceObjectGenerationContext(request, law, sampling))
        incidental += bool(surface.paths)
        assert all(len(path.edges) <= 7 for path in surface.paths)
        assert sum(len(path.edges) for path in surface.paths) <= 7

    path_law = config.object_law_for("path-representative")
    request = GenerationRequest(99, 10)
    surface = generator.generate_for(
        SurfaceObjectGenerationContext(
            request,
            path_law,
            SamplingSession(request.seed, config.profile_version),
        )
    )

    assert 0.04 < incidental / cohort_size < 0.12
    assert surface.paths
    assert len(surface.paths[0].edges) <= 7
    assert sum(len(path.edges) for path in surface.paths) <= 7


def test_surface_laws_support_exact_semantic_computation() -> None:
    config = _generation_config()
    cycle_law = config.object_law_for("path-is-cycle")

    assert cycle_law.probability(
        lambda outcome: isinstance(outcome.paths, DistinguishedSurfacePaths)
        and outcome.paths.count == 2
    ) == pytest.approx(0.075)
    assert cycle_law.probability(
        lambda outcome: isinstance(outcome.paths, DistinguishedSurfacePaths)
        and outcome.paths.first_closed
    ) == pytest.approx(0.55)
    assert cycle_law.map(
        lambda outcome: isinstance(outcome.paths, DistinguishedSurfacePaths)
        and outcome.paths.first_closed
    ).probability(lambda closed: closed) == pytest.approx(0.55)


def test_surface_conditions_validate_positive_counts_on_attrs_fields() -> None:
    with pytest.raises(ValueError, match="component count"):
        SurfaceObjectCondition(0, NoSurfacePaths())
    with pytest.raises(ValueError, match="path count"):
        DistinguishedSurfacePaths(0, False)


def test_simple_two_disk_spheres_are_rare_at_high_difficulty() -> None:
    config = _generation_config()
    families: Counter[str] = Counter()
    for seed in range(1000):
        request = GenerationRequest(seed, 10)
        sampling = SamplingSession(seed, config.profile_version)
        law = config.morphism_law_for("boundary-change").at(request.difficulty)
        condition = sampling.sample("morphism.condition", law)
        families[condition.family_id] += 1

    assert families["full-disk-boundary"] < 0.05 * 1000
    assert len(families) == 5


def test_complete_surface_yaml_is_injected(tmp_path: Path) -> None:
    document = yaml.safe_load(SURFACE_DOMAIN_CONFIG.read_text(encoding="utf-8"))
    document["generation"]["profile_version"] = "test-object-profile"
    override = tmp_path / "surfaces.yaml"
    override.write_text(cast(str, yaml.safe_dump(document)), encoding="utf-8")
    container = build_container(surface_config=override)
    config = container.resolve(SurfaceGenerationConfig)
    generator = container.resolve(ISurfaceGenerator)
    morphism_generator = container.resolve(ISurfaceMorphismGenerator)

    assert config.profile_version == "test-object-profile"
    assert config.difficulty.path_maximum.at(10) == 7
    assert isinstance(generator, RandomSurfacePresentationGenerator)
    assert isinstance(morphism_generator, RandomSurfaceMorphismGenerator)
    assert generator.config is config
    assert morphism_generator.config is config
    request = GenerationRequest(3, 1)
    recipe = container.resolve(SurfaceProblemRecipeDistribution).at(1).sample(Random(3))
    problem = recipe.generate(request)
    assert problem.recipe_id
    assert problem.sections
