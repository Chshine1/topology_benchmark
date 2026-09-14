class BenchmarkApplicationError(Exception):
    """A user-controlled application request cannot be satisfied."""


class InvalidApplicationRequestError(BenchmarkApplicationError, ValueError):
    pass


class UnknownDomainError(BenchmarkApplicationError, LookupError):
    def __init__(self, domain: str, choices: tuple[str, ...]) -> None:
        self.domain = domain
        self.choices = choices
        super().__init__(
            f"unknown benchmark domain {domain!r}; choose one of: {', '.join(choices)}"
        )


class UnknownProblemRecipeError(BenchmarkApplicationError, LookupError):
    def __init__(self, domain: str, recipe_id: str, choices: tuple[str, ...]) -> None:
        self.domain = domain
        self.recipe_id = recipe_id
        self.choices = choices
        super().__init__(
            f"unknown problem recipe {recipe_id!r} for {domain}; "
            f"choose one of: {', '.join(choices)}"
        )
