import hashlib
import json
import shutil
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from topology_benchmark.pipeline.config import PipelineConfig
from topology_benchmark.pipeline.dataset.models import GeneratedBenchmarkRun, GeneratedItem
from topology_benchmark.pipeline.serialization.json_writer import write_json, write_jsonl

DATASET_SCHEMA_VERSION = 2


class DatasetArtifactWriter:
    def write(
        self,
        config: PipelineConfig,
        root_seed: int,
        items: tuple[GeneratedItem, ...],
    ) -> GeneratedBenchmarkRun:
        run_id = _run_id(config, root_seed)
        run_directory = config.output_dir / run_id
        config.output_dir.mkdir(parents=True, exist_ok=True)
        if run_directory.exists():
            raise FileExistsError(f"benchmark run already exists: {run_directory}")
        staging_directory = Path(
            tempfile.mkdtemp(prefix=f".{run_id}-", suffix=".tmp", dir=config.output_dir)
        )
        try:
            media_directory = staging_directory / "media"
            media_directory.mkdir()
            self._write_dataset(staging_directory, media_directory, items)
            write_json(
                staging_directory / "manifest.private.json",
                _manifest(config, root_seed, run_id, items),
            )
            staging_directory.rename(run_directory)
        except BaseException:
            shutil.rmtree(staging_directory, ignore_errors=True)
            raise
        return GeneratedBenchmarkRun(run_directory, items)

    @staticmethod
    def _write_dataset(
        run_directory: Path,
        media_directory: Path,
        items: tuple[GeneratedItem, ...],
    ) -> None:
        public_records = []
        private_records = []
        for item in items:
            media = []
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
                    "answer": item.problem.answer,
                    "generator_seed": item.problem.seed,
                    "recipe_id": item.problem.recipe_id,
                }
            )
        write_jsonl(run_directory / "dataset.public.jsonl", public_records)
        write_jsonl(run_directory / "ground_truth.private.jsonl", private_records)


def _manifest(
    config: PipelineConfig,
    root_seed: int,
    run_id: str,
    items: tuple[GeneratedItem, ...],
) -> dict[str, Any]:
    combinations = Counter((item.domain, item.problem.recipe_id) for item in items)
    return {
        "schema_version": DATASET_SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "root_seed": root_seed,
        "size": len(items),
        "realized_distribution": {
            f"{domain}/{recipe_id}": count
            for (domain, recipe_id), count in sorted(combinations.items())
        },
        "resolved_config": _manifest_config(config),
    }


def _run_id(config: PipelineConfig, root_seed: int) -> str:
    run_configuration = _manifest_config(config)
    run_configuration["output_dir"] = "<excluded>"
    serialized = json.dumps(run_configuration, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(
        f"run:v{DATASET_SCHEMA_VERSION}:{root_seed}:{serialized}".encode()
    ).hexdigest()[:16]


def _manifest_config(config: PipelineConfig) -> dict[str, Any]:
    value = _jsonable(config.model_dump())
    provider = value.get("model_provider")
    if isinstance(provider, dict):
        provider["extra_headers"] = {key: "<redacted>" for key in provider.get("extra_headers", {})}
    return value


def _media_suffix(media_type: str) -> str:
    return {"image/svg+xml": ".svg", "image/png": ".png", "text/plain": ".txt"}.get(
        media_type, ".bin"
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    return value
