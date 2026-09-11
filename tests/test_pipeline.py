import json
from pathlib import Path

from topology_benchmark.pipeline import BenchmarkPipeline, load_pipeline_config
from topology_benchmark.pipeline.scoring import extract_final_answer, score_answer


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
      question_kinds: {euler-characteristic: 1}
provider:
  kind: fixed
  fixed_response: "FINAL_ANSWER: 0"
""",
        encoding="utf-8",
    )
    config = load_pipeline_config(config_file)
    first = BenchmarkPipeline(config)._generate(123)
    second = BenchmarkPipeline(config)._generate(123)

    assert first == second
    output = BenchmarkPipeline(config).run()
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
    assert "answer" in private[0]
    assert (output / public[0]["media"][0]["path"]).exists()
    assert (output / "summary.json").exists()


def test_answer_extraction_and_typed_scoring() -> None:
    response = "Working here.\nFINAL_ANSWER: yes"
    assert extract_final_answer(response) == "yes"
    assert score_answer(True, response)
    assert score_answer(3, "FINAL_ANSWER: 3")
    assert not score_answer(3, "FINAL_ANSWER: 3.0")
