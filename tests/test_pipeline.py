import json
from dataclasses import dataclass
from pathlib import Path
from typing import override

import pytest

from topology_benchmark.application.bootstrap import build_container
from topology_benchmark.application.errors import UnknownDomainError, UnknownQuestionError
from topology_benchmark.core.models import QuestionSection
from topology_benchmark.pipeline import (
    BenchmarkDatasetGenerator,
    PipelineConfig,
    load_pipeline_config,
)
from topology_benchmark.pipeline.evaluator import BenchmarkEvaluator
from topology_benchmark.pipeline.model_provider import (
    ModelProvider,
    OpenAICompatibleModelProviderCredentials,
)
from topology_benchmark.pipeline.registration import add_pipeline_domain


@dataclass(slots=True)
class FixedModelProvider(ModelProvider):
    response: str

    @override
    def answer(self, question: str, sections: tuple[QuestionSection, ...]) -> str:
        del question, sections
        return self.response


def _evaluate_with_fixed_provider(config: PipelineConfig) -> Path:
    container = build_container()
    add_pipeline_domain(container, config)
    container[ModelProvider] = FixedModelProvider("FINAL_ANSWER: 0")
    container[BenchmarkEvaluator] = BenchmarkEvaluator
    generated = container.resolve(BenchmarkDatasetGenerator).generate()
    container.resolve(BenchmarkEvaluator).evaluate(generated)
    return generated.directory


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
""",
        encoding="utf-8",
    )
    config = load_pipeline_config(config_file)
    container = build_container()
    add_pipeline_domain(container, config)
    generator = container.resolve(BenchmarkDatasetGenerator)
    first = generator.generate_items(123)
    second = generator.generate_items(123)

    assert first == second
    output = _evaluate_with_fixed_provider(config)
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
    assert set(private[0]) == {"id", "answer", "generator_seed", "question_id"}
    assert (output / public[0]["media"][0]["path"]).exists()
    assert (output / "summary.json").exists()
    manifest = json.loads((output / "manifest.private.json").read_text())
    assert "generator_profiles" not in manifest


def test_answer_extraction_and_typed_scoring() -> None:
    response = "Working here.\nFINAL_ANSWER: yes"
    extract_final_answer = BenchmarkEvaluator._extract_final_answer
    score_answer = BenchmarkEvaluator._score_answer
    assert extract_final_answer(response) == "yes"
    assert score_answer(True, response)
    assert score_answer(3, "FINAL_ANSWER: 3")
    assert not score_answer(3, "FINAL_ANSWER: 3.0")


def test_model_provider_credentials_reject_a_blank_api_key() -> None:
    with pytest.raises(ValueError, match="cannot be blank"):
        OpenAICompatibleModelProviderCredentials("   ")


def test_pipeline_rejects_unregistered_domains_and_recipes_before_generation(
    tmp_path: Path,
) -> None:
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
        config = load_pipeline_config(unknown_recipe)
        container = build_container()
        add_pipeline_domain(container, config)
        container.resolve(BenchmarkDatasetGenerator)

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
        config = load_pipeline_config(unknown_domain)
        container = build_container()
        add_pipeline_domain(container, config)
        container.resolve(BenchmarkDatasetGenerator)


def test_dataset_generation_does_not_require_a_model_provider(tmp_path: Path) -> None:
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
    config = load_pipeline_config(config_file)
    container = build_container()
    add_pipeline_domain(container, config)

    output = container.resolve(BenchmarkDatasetGenerator).generate().directory

    assert output.exists()
    assert not (output / "summary.json").exists()
