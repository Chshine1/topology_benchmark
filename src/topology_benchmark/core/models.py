"""Immutable values exchanged by framework components."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PromptData:
    """A model-ready representation of a mathematical object."""

    media_type: str
    content: str
    metadata: dict[str, str | int | bool] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Problem[AnswerT]:
    """A generated question together with its reproducible ground truth."""

    question: str
    prompts: tuple[PromptData, ...]
    answer: AnswerT
    seed: int
    metadata: dict[str, str | int | bool] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """Cross-domain controls understood by the application layer."""

    seed: int
    difficulty: int = 1

    def __post_init__(self) -> None:
        if not 1 <= self.difficulty <= 10:
            raise ValueError("difficulty must be between 1 and 10")
