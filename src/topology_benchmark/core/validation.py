import math
from collections.abc import Callable

from attrs import Attribute

type Number = int | float
type Validator[T] = Callable[[object, Attribute[T], T], None]


def number_range[T: (int, float)](
    *,
    minimum: T | None = None,
    minimum_exclusive: T | None = None,
    maximum: T | None = None,
    maximum_exclusive: T | None = None,
    finite: bool = False,
    message: str,
) -> Validator[T]:
    def validate(_: object, __: Attribute[T], value: T) -> None:
        numeric = float(value)
        if (
            (finite and not math.isfinite(numeric))
            or (minimum is not None and numeric < float(minimum))
            or (minimum_exclusive is not None and numeric <= float(minimum_exclusive))
            or (maximum is not None and numeric > float(maximum))
            or (maximum_exclusive is not None and numeric >= float(maximum_exclusive))
        ):
            raise ValueError(message)

    return validate


def nonempty[T](message: str) -> Validator[T]:
    def validate(_: object, __: Attribute[T], value: T) -> None:
        if not value:
            raise ValueError(message)

    return validate


def any_member[T](
    predicate: Callable[[T], bool],
    *,
    message: str,
) -> Validator[tuple[T, ...]]:
    def validate(_: object, __: Attribute[tuple[T, ...]], value: tuple[T, ...]) -> None:
        if not any(predicate(item) for item in value):
            raise ValueError(message)

    return validate


def all_members[T](
    predicate: Callable[[T], bool],
    *,
    message: str,
) -> Validator[tuple[T, ...]]:
    def validate(_: object, __: Attribute[tuple[T, ...]], value: tuple[T, ...]) -> None:
        if not all(predicate(item) for item in value):
            raise ValueError(message)

    return validate


def nonblank(message: str) -> Validator[str]:
    def validate(_: object, __: Attribute[str], value: str) -> None:
        if not value.strip():
            raise ValueError(message)

    return validate
