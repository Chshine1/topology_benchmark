import re
from typing import Protocol, override


class IAnswerScorer(Protocol):
    def extract(self, response: str) -> str: ...

    def score(self, expected: object, response: str) -> bool: ...


class AnswerScorer(IAnswerScorer):
    @override
    def extract(self, response: str) -> str:
        matches = re.findall(r"FINAL_ANSWER:\s*(.+?)\s*$", response, flags=re.IGNORECASE)
        return matches[-1].strip() if matches else response.strip()

    @override
    def score(self, expected: object, response: str) -> bool:
        candidate = self.extract(response)
        if isinstance(expected, bool):
            aliases = {"true": True, "yes": True, "false": False, "no": False}
            return aliases.get(candidate.casefold()) is expected
        if isinstance(expected, int):
            return bool(re.fullmatch(r"[-+]?\d+", candidate)) and int(candidate) == expected
        return _normalize_text(candidate) == _normalize_text(str(expected))


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())
