from typing import Any

from topology_benchmark.pipeline.evaluation.answer_scorer import ScorableAnswer


def serialize_answer(answer: ScorableAnswer) -> dict[str, Any]:
    if isinstance(answer, bool):
        return {"type": "boolean", "value": answer}
    if isinstance(answer, int):
        return {"type": "integer", "value": answer}
    if isinstance(answer, str):
        return {"type": "text", "value": answer}
    if isinstance(answer, tuple) and all(
        isinstance(item, int) and not isinstance(item, bool) for item in answer
    ):
        return {"type": "integer-tuple", "value": list(answer)}
    raise TypeError(f"unsupported answer type: {type(answer).__name__}")


def deserialize_answer(record: object) -> ScorableAnswer:
    if not isinstance(record, dict):
        raise ValueError("a persisted answer must be an object")
    kind = record.get("type")
    value = record.get("value")
    if kind == "boolean" and isinstance(value, bool):
        return value
    if kind == "integer" and isinstance(value, int) and not isinstance(value, bool):
        return value
    if kind == "text" and isinstance(value, str):
        return value
    if (
        kind == "integer-tuple"
        and isinstance(value, list)
        and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    ):
        return tuple(value)
    raise ValueError(f"invalid persisted {kind!r} answer")
