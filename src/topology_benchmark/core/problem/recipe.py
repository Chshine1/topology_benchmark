from collections.abc import Iterator, Mapping
from types import MappingProxyType
from typing import Protocol, override

from topology_benchmark.core.problem.models import GenerationRequest, Problem


class IProblemRecipe[AnswerT](Protocol):
    """A registered, independently selectable problem-producing capability."""

    @property
    def id(self) -> str: ...

    def generate(self, request: GenerationRequest) -> Problem[AnswerT]: ...


class ProblemRecipeCatalog[RecipeT: IProblemRecipe[object]](Mapping[str, RecipeT]):
    def __init__(self, recipes: tuple[RecipeT, ...]) -> None:
        indexed: dict[str, RecipeT] = {}
        for recipe in recipes:
            recipe_id = recipe.id
            if not recipe_id:
                raise ValueError("problem recipes need a nonempty string ID")
            if recipe_id in indexed:
                raise ValueError(f"duplicate problem recipe ID: {recipe_id}")
            indexed[recipe_id] = recipe
        if not indexed:
            raise ValueError("a problem recipe catalog must not be empty")
        self._recipes = MappingProxyType(indexed)

    @override
    def __getitem__(self, recipe_id: str) -> RecipeT:
        return self._recipes[recipe_id]

    @override
    def __iter__(self) -> Iterator[str]:
        return iter(self._recipes)

    @override
    def __len__(self) -> int:
        return len(self._recipes)
