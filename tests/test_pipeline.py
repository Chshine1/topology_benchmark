import json
from pathlib import Path

import pytest

from topology_benchmark.application.bootstrap import build_container
from topology_benchmark.application.catalog import BenchmarkCatalog
from topology_benchmark.application.errors import (
    InvalidApplicationRequestError,
    UnknownDomainError,
    UnknownQuestionError,
)
from topology_benchmark.pipeline import BenchmarkPipeline, load_pipeline_config
from topology_benchmark.pipeline.scoring import extract_final_answer, score_answer


def test_catalog_exposes_structured_application_lookup_errors() -> None:
    catalog = build_container().resolve(BenchmarkCatalog)

    with pytest.raises(UnknownDomainError) as caught:
        catalog.validate_domain("not-registered")

    assert caught.value.domain == "not-registered"
    assert caught.value.choices == ("surfaces", "polyhedral-nets", "torus-slices")


def test_pipeline_generates_separated_reproducible_artifacts(tmp_path: Path) -> None:
    config_file = tmp_path / "pipeline.yaml"
    config_file.write_text(
        """
run:
  seed: 123
  size: 2
  output_dir: output
generation:
  domains:
    surfaces:
      generation_levels: {4: 1}
      recipes: {euler-characteristic: 1}
provider:
  kind: fixed
  fixed_response: "FINAL_ANSWER: 0"
""",
        encoding="utf-8",
    )
    config = load_pipeline_config(config_file)
    catalog = build_container().resolve(BenchmarkCatalog)
    first = BenchmarkPipeline(config, catalog)._generate(123)
    second = BenchmarkPipeline(config, catalog)._generate(123)

    assert first == second
    output = BenchmarkPipeline(config, catalog).run()
    public = [
        json.loads(line) for line in (output / "dataset.public.jsonl").read_text().splitlines()
    ]
    private = [
        json.loads(line)
        for line in (output / "ground_truth.private.jsonl").read_text().splitlines()
    ]
    assert len(public) == len(private) == 2
    assert "answer" not in public[0]
    assert "generator_seed" not in public[0]
    assert set(private[0]) == {"id", "answer", "generator_seed", "question_kind"}
    assert (output / public[0]["media"][0]["path"]).exists()
    assert (output / "summary.json").exists()
    manifest = json.loads((output / "manifest.private.json").read_text())
    assert "generator_profiles" not in manifest


def test_answer_extraction_and_typed_scoring() -> None:
    response = "Working here.\nFINAL_ANSWER: yes"
    assert extract_final_answer(response) == "yes"
    assert score_answer(True, response)
    assert score_answer(3, "FINAL_ANSWER: 3")
    assert not score_answer(3, "FINAL_ANSWER: 3.0")


def test_pipeline_rejects_unregistered_domains_and_recipes_before_generation(
    tmp_path: Path,
) -> None:
    catalog = build_container().resolve(BenchmarkCatalog)
    unknown_recipe = tmp_path / "unknown-recipe.yaml"
    unknown_recipe.write_text(
        """
generation:
  domains:
    surfaces:
      recipes: {not-registered: 1}
""",
        encoding="utf-8",
    )

    with pytest.raises(UnknownQuestionError, match="unknown question"):
        BenchmarkPipeline(load_pipeline_config(unknown_recipe), catalog)

    unknown_domain = tmp_path / "unknown-domain.yaml"
    unknown_domain.write_text(
        """
generation:
  domains:
    not-registered: {}
""",
        encoding="utf-8",
    )

    with pytest.raises(UnknownDomainError, match="unknown benchmark domain"):
        BenchmarkPipeline(load_pipeline_config(unknown_domain), catalog)


def test_pipeline_validates_evaluation_before_creating_output(tmp_path: Path) -> None:
    config_file = tmp_path / "generate-only.yaml"
    config_file.write_text(
        """
run:
  output_dir: output
generation:
  domains:
    surfaces: {}
""",
        encoding="utf-8",
    )
    pipeline = BenchmarkPipeline(
        load_pipeline_config(config_file), build_container().resolve(BenchmarkCatalog)
    )

    with pytest.raises(InvalidApplicationRequestError, match="no provider"):
        pipeline.run(evaluate=True)

    assert not (tmp_path / "output").exists()
