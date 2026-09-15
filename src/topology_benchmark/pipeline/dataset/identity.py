from pathlib import Path
from typing import Any

from topology_benchmark.core.problem.identity import canonical_hash


def dataset_content_id(
    root: Path,
    public_records: list[dict[str, Any]],
    private_records: list[dict[str, Any]],
) -> str:
    media_content = []
    for public in public_records:
        item_id = public.get("id")
        media = public.get("media")
        if not isinstance(item_id, str) or not isinstance(media, list):
            raise ValueError("invalid public dataset record")
        item_media = []
        for entry in media:
            if not isinstance(entry, dict):
                raise ValueError(f"invalid media record for item {item_id}")
            media_type = entry.get("media_type")
            relative_value = entry.get("path")
            if not isinstance(media_type, str) or not isinstance(relative_value, str):
                raise ValueError(f"invalid media record for item {item_id}")
            relative = Path(relative_value)
            path = (root / relative).resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError(f"media path escapes the dataset directory: {relative}")
            item_media.append((media_type, relative.as_posix(), path.read_bytes().hex()))
        media_content.append((item_id, tuple(item_media)))
    return canonical_hash((public_records, private_records, tuple(media_content)))
