"""Deterministic extraction and grading for current answer types."""

import re
from typing import Any


def extract_final_answer(response: str) -> str:
    matches = re.findall(r"(?im)^\s*FINAL_ANSWER\s*:\s*(.*?)\s*$", response)
    return matches[-1] if matches else response.strip()


def score_answer(expected: Any, response: str) -> bool:
    candidate = extract_final_answer(response)
    if isinstance(expected, bool):
        normalized = candidate.casefold().strip(" .")
        aliases = {True: {"true", "yes"}, False: {"false", "no"}}
        return normalized in aliases[expected]
    if isinstance(expected, int):
        return bool(re.fullmatch(r"[+-]?\d+", candidate.strip())) and int(candidate) == expected
    return _normalize_text(candidate) == _normalize_text(str(expected))


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold().strip(".")
