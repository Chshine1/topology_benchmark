from collections import Counter
from pathlib import Path

import pytest

from topology_benchmark import SurfaceBenchmark, build_container
from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.core.probability import (
    FiniteDistribution,
    SamplingSession,
    TruncatedGeometricDistribution,
    WeightedValue,
    interpolate_anchors,
)
from topology_benchmark.domains.surfaces.analysis import SurfaceAnalyzer
from topology_benchmark.domains.surfaces.components.generation_config import (
    SurfaceGenerationConfig,
    load_generation_config,
)
from topology_benchmark.domains.surfaces.components.generator import (
    RandomSurfaceMorphismGenerator,
    RandomSurfacePresentationGenerator,
)
from topology_benchmark.domains.surfaces.components.intent import (
    RandomSurfaceIntentGenerator,
)
from topology_benchmark.domains.surfaces.generation import (
    ProblemSubject,
    QuestionFocus,
    SurfaceGenerationContext,
    SurfaceProblemIntent,
)
from topology_benchmark.domains.surfaces.ports import SurfaceGenerator, SurfaceMorphismGenerator


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


def test_intent_cohorts_follow_difficulty_and_keep_noise_rare() -> None:
    config = load_generation_config()
    generator = RandomSurfaceIntentGenerator(config)

    def cohort(difficulty: int) -> Counter[str]:
        return Counter(
            generator.sample(
                GenerationRequest(seed, difficulty),
                SamplingSession(seed, config.profile_version),
            ).focus.value
            for seed in range(2000)
        )

    easy, hard = cohort(1), cohort(10)
    assert easy["relational"] + easy["target-only"] == 0
    assert hard["relational"] + hard["target-only"] == 0
    assert hard["path"] > easy["path"] * 3


def test_paths_are_question_aligned_but_allow_low_rate_noise() -> None:
    config = load_generation_config()
    generator = RandomSurfacePresentationGenerator(config, SurfaceAnalyzer())
    incidental = 0
    cohort_size = 500
    for seed in range(cohort_size):
        request = GenerationRequest(seed, 7)
        sampling = SamplingSession(seed, config.profile_version)
        intent = SurfaceProblemIntent(
            ProblemSubject.OBJECT,
            "connected-components",
            QuestionFocus.GLOBAL,
        )
        surface = generator.generate_for(SurfaceGenerationContext(request, intent, sampling))
        incidental += bool(surface.paths)
        assert all(len(path.edges) <= 7 for path in surface.paths)
        assert sum(len(path.edges) for path in surface.paths) <= 7

    path_intent = SurfaceProblemIntent(
        ProblemSubject.OBJECT,
        "path-representative",
        QuestionFocus.PATH,
    )
    request = GenerationRequest(99, 10)
    surface = generator.generate_for(
        SurfaceGenerationContext(
            request,
            path_intent,
            SamplingSession(request.seed, config.profile_version),
        )
    )

    assert 0.04 < incidental / cohort_size < 0.12
    assert surface.paths
    assert len(surface.paths[0].edges) <= 7
    assert sum(len(path.edges) for path in surface.paths) <= 7


def test_simple_two_disk_spheres_are_rare_at_high_difficulty() -> None:
    config = load_generation_config()
    generator = RandomSurfaceMorphismGenerator(config, SurfaceAnalyzer())
    families: Counter[str] = Counter()
    intent = SurfaceProblemIntent(
        ProblemSubject.MORPHISM,
        "boundary-change",
        QuestionFocus.RELATIONAL,
    )
    for seed in range(1000):
        request = GenerationRequest(seed, 10)
        sampling = SamplingSession(seed, config.profile_version)
        context = SurfaceGenerationContext(request, intent, sampling)
        families[generator._family(context)] += 1

    assert families["full-disk-boundary"] < 0.05 * 1000
    assert len(families) == 5


def test_generation_yaml_is_layered_and_injected() -> None:
    override = Path(__file__).with_name("generation_override.yaml")
    container = build_container(generation_config=override)
    config = container.resolve(SurfaceGenerationConfig)
    benchmark = container.resolve(SurfaceBenchmark)
    generator = container.resolve(SurfaceGenerator)
    morphism_generator = container.resolve(SurfaceMorphismGenerator)

    assert config.profile_version == "test-object-profile"
    assert config.difficulty.path_maximum.at(10) == 7
    assert isinstance(generator, RandomSurfacePresentationGenerator)
    assert isinstance(morphism_generator, RandomSurfaceMorphismGenerator)
    assert generator.config is config
    assert morphism_generator.config is config
    problem = benchmark.generate(seed=3, difficulty=1)
    assert problem.question_kind
    assert problem.sections
