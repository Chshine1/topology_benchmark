import math

type Point = tuple[float, float]


def quadratic(a: Point, c: Point, b: Point, t: float) -> Point:
    return (
        (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t**2 * b[0],
        (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t**2 * b[1],
    )


def point_at_fraction(curve: tuple[Point, ...], fraction: float) -> Point:
    position = fraction * (len(curve) - 1)
    lower = min(len(curve) - 2, int(position))
    local = position - lower
    start, end = curve[lower], curve[lower + 1]
    return (
        start[0] + (end[0] - start[0]) * local,
        start[1] + (end[1] - start[1]) * local,
    )


def unit(x: float, y: float) -> Point:
    length = max(1e-9, math.hypot(x, y))
    return x / length, y / length
