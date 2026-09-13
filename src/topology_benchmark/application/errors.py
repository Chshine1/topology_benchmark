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


class UnknownQuestionError(BenchmarkApplicationError, LookupError):
    def __init__(self, domain: str, question: str, choices: tuple[str, ...]) -> None:
        self.domain = domain
        self.question = question
        self.choices = choices
        super().__init__(
            f"unknown question {question!r} for {domain}; choose one of: {', '.join(choices)}"
        )
