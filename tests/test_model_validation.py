from pathlib import Path
from typing import cast

import pytest
import yaml
from attrs import exceptions
from pydantic import ValidationError

from topology_benchmark import build_container
from topology_benchmark.application.catalog import BenchmarkCatalog
from topology_benchmark.application.configuration import SURFACE_DOMAIN_CONFIG
from topology_benchmark.core.probability.distribution import (
    BernoulliDistribution,
    FiniteDistribution,
    WeightedValue,
)
from topology_benchmark.core.problem.identity import canonical_hash
from topology_benchmark.core.problem.models import GenerationRequest
from topology_benchmark.domains.polyhedral_nets.config import PolyhedralDomainConfig
from topology_benchmark.domains.surfaces.config import (
    SurfaceDomainConfig,
    load_surface_domain_config,
)
from topology_benchmark.domains.surfaces.models import EdgeRef, Polygon, SurfacePresentation
from topology_benchmark.domains.torus_slices.config import TorusDomainConfig
from topology_benchmark.pipeline.config import load_dataset_config


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
    with pytest.raises(ValueError, match="display edge labels"):
        SurfacePresentation(
            (Polygon("P", 3),),
            (),
            edge_labels=((EdgeRef(0, 0), "A"), (EdgeRef(0, 1), "A")),
        )


def test_rendering_yaml_is_strict(tmp_path: Path) -> None:
    document = yaml.safe_load(SURFACE_DOMAIN_CONFIG.read_text(encoding="utf-8"))
    document["rendering"]["geometry"]["curve_samples"] = "96"
    override = tmp_path / "surfaces.yaml"
    override.write_text(cast(str, yaml.safe_dump(document)), encoding="utf-8")

    with pytest.raises(ValidationError, match="curve_samples"):
        load_surface_domain_config(override)


def test_visual_style_ids_are_unique_and_profiles_are_complete(tmp_path: Path) -> None:
    document = yaml.safe_load(SURFACE_DOMAIN_CONFIG.read_text(encoding="utf-8"))
    document["rendering"]["styles"][1]["id"] = document["rendering"]["styles"][0]["id"]
    override = tmp_path / "surfaces.yaml"
    override.write_text(cast(str, yaml.safe_dump(document)), encoding="utf-8")

    with pytest.raises(ValidationError, match="style IDs must be unique"):
        load_surface_domain_config(override)

    document["rendering"]["styles"][1]["id"] = "hand-drawn"
    del document["rendering"]["styles"][1]["stroke"]["sketch"]
    incomplete = tmp_path / "incomplete-surfaces.yaml"
    incomplete.write_text(cast(str, yaml.safe_dump(document)), encoding="utf-8")

    with pytest.raises(ValidationError, match="sketch"):
        load_surface_domain_config(incomplete)


def test_domain_yaml_requires_every_section(tmp_path: Path) -> None:
    incomplete = tmp_path / "surfaces.yaml"
    incomplete.write_text("rendering: {}\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="generation"):
        load_surface_domain_config(incomplete)


def test_domain_fingerprints_hash_each_complete_domain_config() -> None:
    container = build_container()
    catalog = container.resolve(BenchmarkCatalog)

    assert catalog.configuration_fingerprint("surfaces") == canonical_hash(
        container.resolve(SurfaceDomainConfig)
    )
    assert catalog.configuration_fingerprint("polyhedral-nets") == canonical_hash(
        container.resolve(PolyhedralDomainConfig)
    )
    assert catalog.configuration_fingerprint("torus-slices") == canonical_hash(
        container.resolve(TorusDomainConfig)
    )


def test_pipeline_yaml_rejects_unknown_fields(tmp_path: Path) -> None:
    config = tmp_path / "pipeline.yaml"
    config.write_text(
        "run:\n  seed: null\n  size: 1\n  output_dir: output\n"
        "generation:\n  domains:\n    surfaces:\n      weight: 1\n"
        "      generation_levels: {5: 1}\n      recipes: {}\nunknown: true\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="unknown"):
        load_dataset_config(config)


def test_pipeline_yaml_does_not_fill_missing_values(tmp_path: Path) -> None:
    config = tmp_path / "dataset.yaml"
    config.write_text(
        "run:\n  seed: null\n  output_dir: output\n"
        "generation:\n  domains:\n    surfaces:\n      weight: 1\n"
        "      generation_levels: {5: 1}\n      recipes: {}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="size"):
        load_dataset_config(config)
