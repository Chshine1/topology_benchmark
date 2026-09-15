import base64
import json
from pathlib import Path
from typing import Any

from topology_benchmark.core.problem.identity import canonical_hash
from topology_benchmark.core.problem.models import Problem, QuestionSection
from topology_benchmark.pipeline.dataset.answer_serialization import deserialize_answer
from topology_benchmark.pipeline.dataset.identity import dataset_content_id as calculate_content_id
from topology_benchmark.pipeline.dataset.models import GeneratedBenchmarkRun, GeneratedItem


class DatasetArtifactReader:
    def read(self, directory: str | Path) -> GeneratedBenchmarkRun:
        root = Path(directory).resolve()
        manifest = _read_json(root / "manifest.private.json")
        public_records = _read_jsonl(root / "dataset.public.jsonl")
        private_records = _read_jsonl(root / "ground_truth.private.jsonl")
        if manifest.get("schema_version") != 3:
            raise ValueError("unsupported dataset schema version")
        dataset_id = _required_string(manifest, "dataset_id")
        content_id = _required_string(manifest, "content_id")
        specification = manifest.get("specification")
        if not isinstance(specification, dict):
            raise ValueError("dataset manifest has no resolved specification")
        if canonical_hash(specification)[:16] != dataset_id:
            raise ValueError("dataset ID does not match its resolved specification")
        if root.name != dataset_id:
            raise ValueError("dataset directory name does not match its manifest")
        if calculate_content_id(root, public_records, private_records) != content_id:
            raise ValueError("dataset content does not match its manifest")
        public_ids = [_required_string(record, "id") for record in public_records]
        private_by_id = {_required_string(record, "id"): record for record in private_records}
        if len(set(public_ids)) != len(public_ids):
            raise ValueError("dataset contains duplicate public item IDs")
        if len(private_by_id) != len(private_records):
            raise ValueError("dataset contains duplicate private item IDs")
        if set(public_ids) != private_by_id.keys():
            raise ValueError("public and private dataset items do not match")
        if specification.get("size") != len(public_ids):
            raise ValueError("dataset size does not match its resolved specification")
        items = tuple(self._load_item(root, record, private_by_id) for record in public_records)
        return GeneratedBenchmarkRun(root, dataset_id, content_id, items)

    @staticmethod
    def _load_item(
        root: Path,
        public: dict[str, Any],
        private_by_id: dict[str, dict[str, Any]],
    ) -> GeneratedItem:
        item_id = _required_string(public, "id")
        try:
            private = private_by_id[item_id]
        except KeyError as error:
            raise ValueError(f"missing private record for item {item_id}") from error
        media = public.get("media")
        if not isinstance(media, list):
            raise ValueError(f"invalid media list for item {item_id}")
        sections = tuple(_load_section(root, item) for item in media)
        problem = Problem(
            prompt=_required_string(public, "question"),
            sections=sections,
            answer=deserialize_answer(private.get("answer")),
            seed=_required_integer(private, "generator_seed"),
            recipe_id=_required_string(private, "recipe_id"),
        )
        return GeneratedItem(item_id, _required_string(public, "domain"), problem)


def _load_section(root: Path, record: object) -> QuestionSection:
    if not isinstance(record, dict):
        raise ValueError("a media record must be an object")
    media_type = _required_string(record, "media_type")
    relative = Path(_required_string(record, "path"))
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"media path escapes the dataset directory: {relative}")
    if media_type == "image/png":
        return QuestionSection(media_type, base64.b64encode(path.read_bytes()).decode("ascii"))
    if media_type in {"image/svg+xml", "text/plain"}:
        return QuestionSection(media_type, path.read_text(encoding="utf-8"))
    raise ValueError(f"unsupported dataset media type: {media_type!r}")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not all(isinstance(record, dict) for record in records):
        raise ValueError(f"{path.name} must contain JSON objects")
    return records


def _required_string(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing or invalid {key}")
    return value


def _required_integer(record: dict[str, Any], key: str) -> int:
    value = record.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"missing or invalid {key}")
    return value
