"""Circular core links, elliptic tube profiles, and parallel-plane sections."""

import math
from dataclasses import dataclass

type Vector3 = tuple[float, float, float]


def dot(first: Vector3, second: Vector3) -> float:
    return sum(a * b for a, b in zip(first, second, strict=True))


def add(first: Vector3, second: Vector3) -> Vector3:
    return tuple(a + b for a, b in zip(first, second, strict=True))  # type: ignore[return-value]


def scale(value: float, vector: Vector3) -> Vector3:
    return tuple(value * coordinate for coordinate in vector)  # type: ignore[return-value]


def cross(first: Vector3, second: Vector3) -> Vector3:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def norm(vector: Vector3) -> float:
    return math.sqrt(dot(vector, vector))


def unit(vector: Vector3) -> Vector3:
    length = norm(vector)
    if length <= 1e-12:
        raise ValueError("a direction cannot be zero")
    return scale(1 / length, vector)


def circle_basis(normal: Vector3) -> tuple[Vector3, Vector3]:
    """Choose a deterministic oriented orthonormal basis of a circle plane."""
    reference: Vector3 = (0.0, 0.0, 1.0)
    if abs(dot(normal, reference)) > 0.9:
        reference = (0.0, 1.0, 0.0)
    first = unit(cross(reference, normal))
    return first, cross(normal, first)


@dataclass(frozen=True, slots=True)
class RoundCircle:
    """A Euclidean circle embedded in R^3."""

    center: Vector3
    normal: Vector3
    radius: float

    def __post_init__(self) -> None:
        if self.radius <= 0 or not math.isclose(norm(self.normal), 1.0, abs_tol=1e-8):
            raise ValueError("a circle needs a positive radius and unit normal")

    def point(self, parameter: float) -> Vector3:
        first, second = circle_basis(self.normal)
        return add(
            self.center,
            scale(
                self.radius,
                add(scale(math.cos(parameter), first), scale(math.sin(parameter), second)),
            ),
        )

    def basis(self) -> tuple[Vector3, Vector3]:
        return circle_basis(self.normal)

    @property
    def semi_major(self) -> float:
        return self.radius

    @property
    def semi_minor(self) -> float:
        return self.radius

    @property
    def max_radius(self) -> float:
        return self.radius


type CoreCurve = RoundCircle


@dataclass(frozen=True, slots=True)
class RoundTorus:
    """The boundary of a constant-radius tube around a round core circle."""

    core: CoreCurve
    tube_radius: float

    def __post_init__(self) -> None:
        if not 0 < self.tube_radius < self.core.radius:
            raise ValueError("the tube radius must be smaller than the core radius")

    def implicit_value(self, point: Vector3) -> float:
        offset: Vector3 = tuple(a - b for a, b in zip(point, self.core.center, strict=True))  # type: ignore[assignment]
        axial = dot(offset, self.core.normal)
        radial_squared = max(0.0, dot(offset, offset) - axial * axial)
        return (
            axial * axial
            + (math.sqrt(radial_squared) - self.core.radius) ** 2
            - self.tube_radius**2
        )

    @property
    def clearance_radius(self) -> float:
        return self.tube_radius


@dataclass(frozen=True, slots=True)
class EllipticTorus:
    """A rotated elliptical profile swept around a round planar core circle."""

    core: RoundCircle
    first_radius: float
    second_radius: float
    profile_angle: float = 0.0

    def __post_init__(self) -> None:
        if min(self.first_radius, self.second_radius) <= 0:
            raise ValueError("elliptic profile semiaxes must be positive")
        if self.clearance_radius >= self.core.radius:
            raise ValueError("the elliptic profile must be smaller than the core radius")

    def implicit_value(self, point: Vector3) -> float:
        offset: Vector3 = tuple(a - b for a, b in zip(point, self.core.center, strict=True))  # type: ignore[assignment]
        axial = dot(offset, self.core.normal)
        radial_squared = max(0.0, dot(offset, offset) - axial * axial)
        radial_offset = math.sqrt(radial_squared) - self.core.radius
        cosine, sine = math.cos(self.profile_angle), math.sin(self.profile_angle)
        first = cosine * radial_offset + sine * axial
        second = -sine * radial_offset + cosine * axial
        return (first / self.first_radius) ** 2 + (second / self.second_radius) ** 2 - 1

    @property
    def clearance_radius(self) -> float:
        return max(self.first_radius, self.second_radius)


type TorusComponent = RoundTorus | EllipticTorus


@dataclass(frozen=True, slots=True)
class TorusFamily:
    """A finite collection of pairwise-disjoint rigid round tori."""

    tori: tuple[TorusComponent, ...]

    def __post_init__(self) -> None:
        if not self.tori:
            raise ValueError("a torus family cannot be empty")


@dataclass(frozen=True, slots=True)
class TorusSliceObservation:
    """Ground-truth family together with the only planes exposed to the answerer."""

    family: TorusFamily
    height_direction: Vector3
    levels: tuple[float, ...]

    def __post_init__(self) -> None:
        if not math.isclose(norm(self.height_direction), 1.0, abs_tol=1e-8):
            raise ValueError("height direction must be a unit vector")
        if len(self.levels) < 2 or tuple(sorted(set(self.levels))) != self.levels:
            raise ValueError("levels must be strictly increasing")
