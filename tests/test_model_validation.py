from pathlib import Path

import pytest
from attrs import exceptions
from pydantic import ValidationError

from topology_benchmark.application.configuration import SURFACE_RENDERING_DEFAULTS
from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.core.probability import (
    BernoulliDistribution,
    FiniteDistribution,
    WeightedValue,
)
from topology_benchmark.domains.surfaces.models import Polygon, SurfacePresentation
from topology_benchmark.domains.surfaces.rendering.config import load_rendering_config
from topology_benchmark.pipeline.config import load_pipeline_config


def test_attrs_models_use_declarative_domain_errors() -> None:
    with pytest.raises(ValueError, match="difficulty must be between"):
        GenerationRequest(seed=1, difficulty=11)
    with pytest.raises(ValueError, match="finite and nonnegative"):
        WeightedValue("invalid", float("inf"))
    with pytest.raises(ValueError, match="between zero and one"):
        BernoulliDistribution(1.1)


def test_finite_distribution_requires_a_positive_member() -> None:
    with pytest.raises(ValueError, match="positive total weight"):
        FiniteDistribution[object](())
    with pytest.raises(ValueError, match="positive total weight"):
        FiniteDistribution((WeightedValue("a", 0.0), WeightedValue("b", 0.0)))

    distribution = FiniteDistribution((WeightedValue("a", 0.0), WeightedValue("b", 1.0)))

    assert distribution.values[-1].value == "b"


def test_finite_distribution_composes_and_conditions_exactly() -> None:
    outer = FiniteDistribution((WeightedValue("a", 1.0), WeightedValue("b", 3.0)))

    joint = outer.bind(
        lambda value: FiniteDistribution(
            (
                WeightedValue((value, False), 1.0),
                WeightedValue((value, True), 1.0),
            )
        )
    )
    conditioned = joint.condition(lambda outcome: outcome[1])

    assert outer.expectation(lambda value: {"a": 1.0, "b": 5.0}[value]) == 4.0
    assert joint.probability(lambda outcome: outcome == ("b", True)) == 0.375
    assert (
        conditioned.map(lambda outcome: outcome[0]).probability(lambda value: value == "b") == 0.75
    )
    with pytest.raises(ValueError, match="zero probability"):
        outer.condition(lambda _value: False)


def test_attrs_models_are_frozen_and_generated_init_runs_invariants() -> None:
    presentation = SurfacePresentation((Polygon("P", 3),), ())
    with pytest.raises(exceptions.FrozenInstanceError):
        presentation.__setattr__("paths", ())
    with pytest.raises(ValueError, match="at least one polygon"):
        SurfacePresentation((), ())


def test_rendering_yaml_is_strict(tmp_path: Path) -> None:
    override = tmp_path / "rendering.yaml"
    override.write_text("rendering:\n  geometry:\n    curve_samples: '96'\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="curve_samples"):
        load_rendering_config(SURFACE_RENDERING_DEFAULTS, override)


def test_pipeline_yaml_rejects_unknown_fields(tmp_path: Path) -> None:
    config = tmp_path / "pipeline.yaml"
    config.write_text(
        "generation:\n  domains:\n    surfaces: {}\nunknown: true\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="unknown"):
        load_pipeline_config(config)
