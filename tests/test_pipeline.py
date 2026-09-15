import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast, override

import pytest
import yaml

from topology_benchmark.application.bootstrap import build_container
from topology_benchmark.application.configuration import SURFACE_DOMAIN_CONFIG
from topology_benchmark.application.errors import UnknownDomainError, UnknownProblemRecipeError
from topology_benchmark.core.problem.models import Problem, QuestionSection
from topology_benchmark.pipeline import (
    BenchmarkDatasetGenerator,
    DatasetConfig,
    EvaluationConfig,
    ModelEvaluationConfig,
    OpenAICompatibleModelProviderConfig,
    load_dataset_config,
)
from topology_benchmark.pipeline.config import WeightedConfig
from topology_benchmark.pipeline.dataset.artifact_reader import DatasetArtifactReader
from topology_benchmark.pipeline.dataset.artifact_writer import DatasetArtifactWriter
from topology_benchmark.pipeline.dataset.models import GeneratedItem
from topology_benchmark.pipeline.dataset.planner import DatasetPlanner
from topology_benchmark.pipeline.evaluation import model_provider as model_provider_module
from topology_benchmark.pipeline.evaluation.answer_scorer import AnswerScorer
from topology_benchmark.pipeline.evaluation.artifact_store import EvaluationArtifactStore
from topology_benchmark.pipeline.evaluation.model_provider import (
    IModelProvider,
    OpenAICompatibleModelProvider,
    OpenAICompatibleModelProviderCredentials,
)
from topology_benchmark.pipeline.evaluator import BenchmarkEvaluator
from topology_benchmark.pipeline.registration import add_dataset_generation


def _weighted_config() -> WeightedConfig:
    return WeightedConfig(weight=1.0, generation_levels={5: 1.0}, recipes={})


def _provider_config(model: str) -> OpenAICompatibleModelProviderConfig:
    return OpenAICompatibleModelProviderConfig(
        model=model,
        base_url="https://example.invalid/v1",
        api_key_env="BENCHMARK_API_KEY",
        timeout_seconds=60.0,
        extra_headers={},
    )


def _evaluation_config(model: str = "fixed") -> ModelEvaluationConfig:
    return ModelEvaluationConfig(
        evaluation=EvaluationConfig(max_retries=2),
        model_provider=_provider_config(model),
    )


@dataclass(slots=True)
class FixedModelProvider(IModelProvider):
    response: str

    @override
    def answer(self, question: str, sections: tuple[QuestionSection, ...]) -> str:
        del question, sections
        return self.response


@dataclass(slots=True)
class InterruptingModelProvider(IModelProvider):
    calls: int = 0

    @override
    def answer(self, question: str, sections: tuple[QuestionSection, ...]) -> str:
        del question, sections
        self.calls += 1
        if self.calls == 2:
            raise KeyboardInterrupt
        return "FINAL_ANSWER: 0"


@dataclass(slots=True)
class CountingModelProvider(IModelProvider):
    calls: int = 0

    @override
    def answer(self, question: str, sections: tuple[QuestionSection, ...]) -> str:
        del question, sections
        self.calls += 1
        return "FINAL_ANSWER: 0"


def _evaluate_with_fixed_provider(config: DatasetConfig) -> tuple[Path, Path]:
    container = build_container()
    add_dataset_generation(container, config)
    generated = container.resolve(BenchmarkDatasetGenerator).generate()
    evaluation = _evaluation_config()
    evaluator = BenchmarkEvaluator(
        evaluation.evaluation,
        FixedModelProvider("FINAL_ANSWER: 0"),
        EvaluationArtifactStore(evaluation),
        AnswerScorer(),
    )
    evaluation_directory = evaluator.evaluate(generated)
    return generated.directory, evaluation_directory


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
      weight: 1
      generation_levels: {4: 1}
      recipes: {euler-characteristic: 1}
""",
        encoding="utf-8",
    )
    config = load_dataset_config(config_file)
    container = build_container()
    add_dataset_generation(container, config)
    generator = container.resolve(BenchmarkDatasetGenerator)
    first_plan = container.resolve(DatasetPlanner).create()
    second_plan = container.resolve(DatasetPlanner).create()
    first = generator._generate_items(first_plan)
    second = generator._generate_items(second_plan)

    assert first == second
    output, evaluation_output = _evaluate_with_fixed_provider(config)
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
    assert set(private[0]) == {"id", "answer", "generator_seed", "recipe_id"}
    assert private[0]["answer"]["type"] == "integer"
    assert (output / public[0]["media"][0]["path"]).exists()
    assert (evaluation_output / "summary.json").exists()
    manifest = json.loads((output / "manifest.private.json").read_text())
    assert manifest["schema_version"] == 3
    assert manifest["dataset_id"] == output.name
    assert len(manifest["specification"]["domain_fingerprints"]) == 1
    assert DatasetArtifactReader().read(output).items == first


def test_png_sections_are_persisted_as_binary_and_restored_as_base64(tmp_path: Path) -> None:
    config = DatasetConfig(
        size=1,
        output_dir=tmp_path,
        seed=4,
        domains={"surfaces": _weighted_config()},
    )
    container = build_container()
    add_dataset_generation(container, config)
    plan = container.resolve(DatasetPlanner).create()
    png = b"\x89PNG\r\n\x1a\nsynthetic-test-data"
    encoded = base64.b64encode(png).decode("ascii")
    item = GeneratedItem(
        "item-1",
        "surfaces",
        Problem(
            prompt="question",
            sections=(QuestionSection("image/png", encoded),),
            answer=0,
            seed=4,
            recipe_id="euler-characteristic",
        ),
    )

    generated = DatasetArtifactWriter().write(plan, (item,))
    media_path = next((generated.directory / "media").iterdir())

    assert media_path.read_bytes() == png
    assert DatasetArtifactReader().read(generated.directory).items == (item,)


def test_pipeline_exposes_the_composed_generation_distribution(tmp_path: Path) -> None:
    config = DatasetConfig(
        size=1,
        output_dir=tmp_path,
        seed=None,
        domains={
            "surfaces": WeightedConfig(
                weight=2,
                generation_levels={4: 1, 8: 3},
                recipes={"euler-characteristic": 1, "orientable": 1},
            ),
            "torus-slices": WeightedConfig(
                weight=1,
                generation_levels={8: 1},
                recipes={"completely-unlinked": 1},
            ),
        },
    )
    container = build_container()
    add_dataset_generation(container, config)

    distribution = container.resolve(DatasetPlanner)._generation_distribution

    assert distribution.probability(
        lambda selection: selection.domain == "surfaces"
        and selection.difficulty == 8
        and selection.recipe.id == "euler-characteristic"
    ) == pytest.approx(0.25)
    assert distribution.probability(
        lambda selection: selection.domain == "torus-slices"
        and selection.recipe.id == "completely-unlinked"
    ) == pytest.approx(1 / 3)


def test_dataset_identity_uses_normalized_selection_probabilities(tmp_path: Path) -> None:
    def plan(domain_weight: float, recipe_weight: float):
        config = DatasetConfig(
            size=2,
            output_dir=tmp_path,
            seed=81,
            domains={
                "surfaces": WeightedConfig(
                    weight=domain_weight,
                    generation_levels={4: domain_weight},
                    recipes={"euler-characteristic": recipe_weight},
                )
            },
        )
        container = build_container()
        add_dataset_generation(container, config)
        return container.resolve(DatasetPlanner).create()

    assert plan(1, 1).dataset_id == plan(10, 20).dataset_id


def test_dataset_identity_includes_domain_rendering_configuration(tmp_path: Path) -> None:
    config = DatasetConfig(
        size=1,
        output_dir=tmp_path,
        seed=81,
        domains={"surfaces": _weighted_config()},
    )
    default_container = build_container()
    add_dataset_generation(default_container, config)
    document = yaml.safe_load(SURFACE_DOMAIN_CONFIG.read_text(encoding="utf-8"))
    document["rendering"]["geometry"]["side_length"] = 150
    surface_config = tmp_path / "surfaces.yaml"
    surface_config.write_text(cast(str, yaml.safe_dump(document)), encoding="utf-8")
    overridden_container = build_container(surface_config=surface_config)
    add_dataset_generation(overridden_container, config)

    default = default_container.resolve(DatasetPlanner).create()
    overridden = overridden_container.resolve(DatasetPlanner).create()

    assert default.dataset_id != overridden.dataset_id


def test_evaluation_resumes_from_atomic_item_checkpoints(tmp_path: Path) -> None:
    config = DatasetConfig(
        size=2,
        output_dir=tmp_path,
        seed=19,
        domains={
            "surfaces": WeightedConfig(
                weight=1, generation_levels={4: 1}, recipes={"euler-characteristic": 1}
            )
        },
    )
    container = build_container()
    add_dataset_generation(container, config)
    dataset = container.resolve(BenchmarkDatasetGenerator).generate()
    evaluation = _evaluation_config()
    store = EvaluationArtifactStore(evaluation)
    interrupted = InterruptingModelProvider()
    evaluator = BenchmarkEvaluator(evaluation.evaluation, interrupted, store, AnswerScorer())

    with pytest.raises(KeyboardInterrupt):
        evaluator.evaluate(dataset)

    resumed = CountingModelProvider()
    output = BenchmarkEvaluator(evaluation.evaluation, resumed, store, AnswerScorer()).evaluate(
        DatasetArtifactReader().read(dataset.directory)
    )

    assert resumed.calls == 1
    assert len(tuple((output / "predictions").glob("*.json"))) == 2
    assert len((output / "predictions.jsonl").read_text().splitlines()) == 2


def test_models_get_separate_evaluations_of_one_dataset(tmp_path: Path) -> None:
    config = DatasetConfig(
        size=1,
        output_dir=tmp_path,
        seed=23,
        domains={"surfaces": _weighted_config()},
    )
    container = build_container()
    add_dataset_generation(container, config)
    dataset = container.resolve(BenchmarkDatasetGenerator).generate()

    outputs = []
    for model in ("model-a", "model-b"):
        evaluation = _evaluation_config(model)
        outputs.append(
            BenchmarkEvaluator(
                evaluation.evaluation,
                FixedModelProvider("FINAL_ANSWER: 0"),
                EvaluationArtifactStore(evaluation),
                AnswerScorer(),
            ).evaluate(dataset)
        )

    assert outputs[0] != outputs[1]
    assert all(output.parent.parent == dataset.directory for output in outputs)


def test_dataset_reader_detects_changed_media(tmp_path: Path) -> None:
    config = DatasetConfig(
        size=1,
        output_dir=tmp_path,
        seed=27,
        domains={
            "surfaces": WeightedConfig(
                weight=1, generation_levels={4: 1}, recipes={"euler-characteristic": 1}
            )
        },
    )
    container = build_container()
    add_dataset_generation(container, config)
    dataset = container.resolve(BenchmarkDatasetGenerator).generate()
    public = json.loads((dataset.directory / "dataset.public.jsonl").read_text().splitlines()[0])
    media_path = dataset.directory / public["media"][0]["path"]
    media_path.write_text(media_path.read_text(encoding="utf-8") + "changed", encoding="utf-8")

    with pytest.raises(ValueError, match="content does not match"):
        DatasetArtifactReader().read(dataset.directory)


def test_answer_extraction_and_typed_scoring() -> None:
    response = "Working here.\nFINAL_ANSWER: yes"
    scorer = AnswerScorer()
    assert scorer.extract(response) == "yes"
    assert scorer.score(True, response)
    assert scorer.score(3, "FINAL_ANSWER: 3")
    assert not scorer.score(3, "FINAL_ANSWER: 3.0")
    assert scorer.score((1, -2), "FINAL_ANSWER: (1,-2)")
    assert scorer.score((1,), "FINAL_ANSWER: [1]")
    assert not scorer.score((1, 2), "FINAL_ANSWER: (1, 3)")


def test_typed_scoring_compares_partitions_and_homology_semantically() -> None:
    scorer = AnswerScorer()

    assert scorer.score("AC|B|D", "FINAL_ANSWER: d | ca | b")
    assert not scorer.score("AC|B|D", "FINAL_ANSWER: A|BC|D")
    assert scorer.score(
        "H_0=Z; H_1=Z ⊕ (Z/2)^2; H_2=0",
        "FINAL_ANSWER: H0 = Z; H1 = Z/2 + Z + Z/2; H2 = 0",
    )
    assert not scorer.score(
        "H_0=Z; H_1=Z/2; H_2=0",
        "FINAL_ANSWER: H_0=Z; H_1=Z/3; H_2=0",
    )


def test_typed_scoring_rejects_unsupported_expected_values() -> None:
    with pytest.raises(TypeError, match="unsupported expected answer type"):
        AnswerScorer().score(1.5, "FINAL_ANSWER: 1.5")  # type: ignore[arg-type]


def test_model_provider_credentials_reject_a_blank_api_key() -> None:
    with pytest.raises(ValueError, match="cannot be blank"):
        OpenAICompatibleModelProviderCredentials("   ")


def test_model_provider_dispatches_text_and_image_sections(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        @staticmethod
        def read() -> bytes:
            return b'{"choices":[{"message":{"content":"ok"}}]}'

    def urlopen(request, timeout: float):
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(model_provider_module, "urlopen", urlopen)
    provider = OpenAICompatibleModelProvider(
        _provider_config("test"),
        OpenAICompatibleModelProviderCredentials("secret"),
    )

    assert (
        provider.answer(
            "question",
            (
                QuestionSection("text/plain", "context"),
                QuestionSection("image/svg+xml", "<svg/>"),
                QuestionSection("image/png", "iVBORw0KGgo="),
            ),
        )
        == "ok"
    )
    body = cast(dict[str, object], captured["body"])
    messages = cast(list[dict[str, object]], body["messages"])
    message = cast(list[dict[str, object]], messages[0]["content"])
    assert [part["type"] for part in message] == ["text", "text", "image_url", "image_url"]
    assert cast(dict[str, object], message[-1]["image_url"])["url"] == (
        "data:image/png;base64,iVBORw0KGgo="
    )
    assert captured["timeout"] == 60.0

    with pytest.raises(ValueError, match="does not support"):
        provider.answer("question", (QuestionSection("audio/wav", "content"),))


def test_dataset_writer_removes_failed_staging_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = DatasetConfig(
        size=1,
        output_dir=tmp_path,
        domains={"surfaces": _weighted_config()},
        seed=1,
    )

    def fail(*_args: object) -> None:
        raise OSError("write failed")

    monkeypatch.setattr(DatasetArtifactWriter, "_write_dataset", fail)
    container = build_container()
    add_dataset_generation(container, config)
    plan = container.resolve(DatasetPlanner).create()
    with pytest.raises(OSError, match="write failed"):
        DatasetArtifactWriter().write(plan, ())

    assert not tuple(tmp_path.iterdir())


def test_dataset_writer_rejects_an_existing_reproducible_run(tmp_path: Path) -> None:
    config = DatasetConfig(
        size=1,
        output_dir=tmp_path,
        domains={"surfaces": _weighted_config()},
        seed=1,
    )
    container = build_container()
    add_dataset_generation(container, config)
    plan = container.resolve(DatasetPlanner).create()
    writer = DatasetArtifactWriter()
    writer.write(plan, ())

    with pytest.raises(FileExistsError, match="benchmark dataset already exists"):
        writer.write(plan, ())


def test_pipeline_config_rejects_nonfinite_weights() -> None:
    with pytest.raises(ValueError):
        WeightedConfig(weight=float("inf"), generation_levels={5: 1}, recipes={})


def test_pipeline_rejects_unregistered_domains_and_recipes_before_generation(
    tmp_path: Path,
) -> None:
    unknown_recipe = tmp_path / "unknown-recipe.yaml"
    unknown_recipe.write_text(
        """
run:
  seed: 1
  size: 1
  output_dir: output
generation:
  domains:
    surfaces:
      weight: 1
      generation_levels: {5: 1}
      recipes: {not-registered: 1}
""",
        encoding="utf-8",
    )

    with pytest.raises(UnknownProblemRecipeError, match="unknown problem recipe"):
        config = load_dataset_config(unknown_recipe)
        container = build_container()
        add_dataset_generation(container, config)
        container.resolve(BenchmarkDatasetGenerator)

    unknown_domain = tmp_path / "unknown-domain.yaml"
    unknown_domain.write_text(
        """
run:
  seed: 1
  size: 1
  output_dir: output
generation:
  domains:
    not-registered:
      weight: 1
      generation_levels: {5: 1}
      recipes: {}
""",
        encoding="utf-8",
    )

    with pytest.raises(UnknownDomainError, match="unknown benchmark domain"):
        config = load_dataset_config(unknown_domain)
        container = build_container()
        add_dataset_generation(container, config)
        container.resolve(BenchmarkDatasetGenerator)


def test_dataset_generation_does_not_require_a_model_provider(tmp_path: Path) -> None:
    config_file = tmp_path / "generate-only.yaml"
    config_file.write_text(
        """
run:
  seed: null
  size: 1
  output_dir: output
generation:
  domains:
    surfaces:
      weight: 1
      generation_levels: {5: 1}
      recipes: {}
""",
        encoding="utf-8",
    )
    config = load_dataset_config(config_file)
    container = build_container()
    add_dataset_generation(container, config)

    output = container.resolve(BenchmarkDatasetGenerator).generate().directory

    assert output.exists()
    assert not (output / "summary.json").exists()
