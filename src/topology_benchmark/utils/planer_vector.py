import math

type Point = tuple[float, float]


def quadratic(a: Point, c: Point, b: Point, t: float) -> Point:
    return (
        (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t**2 * b[0],
        (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t**2 * b[1],
    )


def unit(x: float, y: float) -> Point:
    length = max(1e-9, math.hypot(x, y))
    return x / length, y / length
