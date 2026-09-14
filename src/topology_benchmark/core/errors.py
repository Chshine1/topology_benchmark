class ConfigurationError(ValueError):
    """External configuration cannot be loaded into the application."""


class GenerationError(RuntimeError):
    """A valid generation request could not be completed."""


class GenerationExhaustedError(GenerationError):
    def __init__(self, domain: str, operation: str, attempts: int) -> None:
        self.domain = domain
        self.operation = operation
        self.attempts = attempts
        super().__init__(f"{domain} could not {operation} after {attempts} attempts")
