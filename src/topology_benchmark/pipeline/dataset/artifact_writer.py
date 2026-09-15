import shutil
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from topology_benchmark.core.problem.identity import canonical_value
from topology_benchmark.pipeline.dataset.answer_serialization import serialize_answer
from topology_benchmark.pipeline.dataset.identity import dataset_content_id
from topology_benchmark.pipeline.dataset.models import (
    DatasetPlan,
    GeneratedBenchmarkRun,
    GeneratedItem,
)
from topology_benchmark.pipeline.serialization.json_writer import write_json, write_jsonl


class DatasetArtifactWriter:
    def write(
        self,
        plan: DatasetPlan,
        items: tuple[GeneratedItem, ...],
    ) -> GeneratedBenchmarkRun:
        run_directory = plan.output_directory / plan.dataset_id
        plan.output_directory.mkdir(parents=True, exist_ok=True)
        if run_directory.exists():
            raise FileExistsError(f"benchmark dataset already exists: {run_directory}")
        staging_directory = Path(
            tempfile.mkdtemp(
                prefix=f".{plan.dataset_id}-", suffix=".tmp", dir=plan.output_directory
            )
        )
        try:
            media_directory = staging_directory / "media"
            media_directory.mkdir()
            public_records, private_records = self._write_dataset(
                staging_directory, media_directory, items
            )
            content_id = dataset_content_id(staging_directory, public_records, private_records)
            write_json(
                staging_directory / "manifest.private.json",
                _manifest(plan, content_id, items),
            )
            staging_directory.rename(run_directory)
        except BaseException:
            shutil.rmtree(staging_directory, ignore_errors=True)
            raise
        return GeneratedBenchmarkRun(run_directory, plan.dataset_id, content_id, items)

    @staticmethod
    def _write_dataset(
        run_directory: Path,
        media_directory: Path,
        items: tuple[GeneratedItem, ...],
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        public_records: list[dict[str, object]] = []
        private_records: list[dict[str, object]] = []
        for item in items:
            media: list[dict[str, str]] = []
            for index, section in enumerate(item.problem.sections):
                path = (
                    media_directory / f"{item.item_id}-{index}{_media_suffix(section.media_type)}"
                )
                path.write_text(section.content, encoding="utf-8")
                media.append(
                    {
                        "media_type": section.media_type,
                        "path": path.relative_to(run_directory).as_posix(),
                    }
                )
            public_records.append(
                {
                    "id": item.item_id,
                    "domain": item.domain,
                    "question": item.problem.prompt,
                    "media": media,
                }
            )
            private_records.append(
                {
                    "id": item.item_id,
                    "answer": serialize_answer(item.problem.answer),
                    "generator_seed": item.problem.seed,
                    "recipe_id": item.problem.recipe_id,
                }
            )
        write_jsonl(run_directory / "dataset.public.jsonl", public_records)
        write_jsonl(run_directory / "ground_truth.private.jsonl", private_records)
        return public_records, private_records


def _manifest(
    plan: DatasetPlan,
    content_id: str,
    items: tuple[GeneratedItem, ...],
) -> dict[str, object]:
    combinations = Counter((item.domain, item.problem.recipe_id) for item in items)
    return {
        "schema_version": plan.specification.schema_version,
        "dataset_id": plan.dataset_id,
        "content_id": content_id,
        "created_at": datetime.now(UTC).isoformat(),
        "specification": canonical_value(plan.specification),
        "realized_distribution": {
            f"{domain}/{recipe_id}": count
            for (domain, recipe_id), count in sorted(combinations.items())
        },
    }


def _media_suffix(media_type: str) -> str:
    return {"image/svg+xml": ".svg", "image/png": ".png", "text/plain": ".txt"}.get(
        media_type, ".bin"
    )
