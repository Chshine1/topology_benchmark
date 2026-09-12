from pathlib import Path

import pytest
from attrs import exceptions
from pydantic import ValidationError

from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.core.probability import (
    BernoulliDistribution,
    FiniteDistribution,
    WeightedValue,
)
from topology_benchmark.domains.surfaces.components.rendering_config import (
    load_rendering_config,
)
from topology_benchmark.domains.surfaces.models import Polygon, SurfacePresentation
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
        load_rendering_config(override)


def test_pipeline_yaml_rejects_unknown_fields(tmp_path: Path) -> None:
    config = tmp_path / "pipeline.yaml"
    config.write_text(
        "generation:\n  domains:\n    surfaces: {}\nunknown: true\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="unknown"):
        load_pipeline_config(config)
