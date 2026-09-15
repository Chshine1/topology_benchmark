import re
from typing import Protocol, override

type ScorableAnswer = bool | int | str | tuple[int, ...]
ANSWER_SCORER_VERSION = "typed-answer-scorer-v1"


class IAnswerScorer(Protocol):
    def extract(self, response: str) -> str: ...

    def score(self, expected: ScorableAnswer, response: str) -> bool: ...


class AnswerScorer(IAnswerScorer):
    @override
    def extract(self, response: str) -> str:
        matches = re.findall(r"FINAL_ANSWER:\s*(.+?)\s*$", response, flags=re.IGNORECASE)
        return matches[-1].strip() if matches else response.strip()

    @override
    def score(self, expected: ScorableAnswer, response: str) -> bool:
        candidate = self.extract(response)
        if isinstance(expected, bool):
            return _parse_boolean(candidate) is expected
        if isinstance(expected, int):
            parsed = _parse_integer(candidate)
            return parsed is not None and parsed == expected
        if isinstance(expected, tuple):
            parsed = _parse_integer_tuple(candidate)
            return parsed is not None and parsed == expected
        if isinstance(expected, str):
            return _equivalent_text(expected, candidate)
        raise TypeError(f"unsupported expected answer type: {type(expected).__name__}")


def _parse_boolean(value: str) -> bool | None:
    return {"true": True, "yes": True, "false": False, "no": False}.get(value.casefold())


def _parse_integer(value: str) -> int | None:
    return int(value) if re.fullmatch(r"[-+]?\d+", value) else None


def _parse_integer_tuple(value: str) -> tuple[int, ...] | None:
    match = re.fullmatch(r"\s*[\[(]\s*(.*?)\s*[\])]\s*", value)
    if match is None:
        return None
    contents = match.group(1)
    if not contents:
        return ()
    parts = [part.strip() for part in contents.split(",")]
    if parts[-1] == "" and len(parts) > 1:
        parts.pop()
    parsed = tuple(_parse_integer(part) for part in parts)
    if any(item is None for item in parsed):
        return None
    return tuple(item for item in parsed if item is not None)


def _equivalent_text(expected: str, candidate: str) -> bool:
    expected_partition = _parse_partition(expected)
    if expected_partition is not None:
        return _parse_partition(candidate) == expected_partition
    expected_homology = _parse_homology(expected)
    if expected_homology is not None:
        return _parse_homology(candidate) == expected_homology
    return _normalize_text(candidate) == _normalize_text(expected)


def _parse_partition(value: str) -> frozenset[frozenset[str]] | None:
    compact = re.sub(r"\s+", "", value).upper()
    if "|" not in compact:
        return None
    groups = compact.split("|")
    if any(not re.fullmatch(r"[A-Z]+", group) for group in groups):
        return None
    letters = "".join(groups)
    if len(set(letters)) != len(letters):
        return None
    return frozenset(frozenset(group) for group in groups)


type AbelianGroup = tuple[int, tuple[tuple[int, int], ...]]


def _parse_homology(value: str) -> tuple[AbelianGroup, AbelianGroup, AbelianGroup] | None:
    compact = (
        re.sub(r"\s+", "", value)
        .replace("\N{DOUBLE-STRUCK CAPITAL Z}", "Z")
        .replace("{", "")
        .replace("}", "")
    )
    parts = compact.split(";")
    if len(parts) != 3:
        return None
    groups: dict[int, AbelianGroup] = {}
    for part in parts:
        match = re.fullmatch(r"H_?([012])=(.+)", part, flags=re.IGNORECASE)
        if match is None:
            return None
        group = _parse_abelian_group(match.group(2))
        if group is None:
            return None
        groups[int(match.group(1))] = group
    if groups.keys() != {0, 1, 2}:
        return None
    return groups[0], groups[1], groups[2]


def _parse_abelian_group(value: str) -> AbelianGroup | None:
    if value == "0":
        return 0, ()
    free_rank = 0
    torsion: dict[int, int] = {}
    for term in re.split(r"[⊕+]", value):
        free = re.fullmatch(r"Z(?:\^(\d+))?", term, flags=re.IGNORECASE)
        if free is not None:
            free_rank += int(free.group(1) or 1)
            continue
        finite = re.fullmatch(r"\(?Z/(\d+)\)?(?:\^(\d+))?", term, flags=re.IGNORECASE)
        if finite is None:
            return None
        order = int(finite.group(1))
        multiplicity = int(finite.group(2) or 1)
        if order < 2 or multiplicity < 1:
            return None
        torsion[order] = torsion.get(order, 0) + multiplicity
    return free_rank, tuple(sorted(torsion.items()))


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())
