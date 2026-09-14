import math

from attrs import Attribute, field, frozen

from topology_benchmark.core.validation import nonempty, number_range

type Vector3 = tuple[float, float, float]


def _unit_vector(message: str):
    def validate(_: object, __: Attribute[Vector3], value: Vector3) -> None:
        if not math.isclose(norm(value), 1.0, abs_tol=1e-8):
            raise ValueError(message)

    return validate


def _strictly_increasing(
    _: object,
    __: Attribute[tuple[float, ...]],
    value: tuple[float, ...],
) -> None:
    if len(value) < 2 or tuple(sorted(set(value))) != value:
        raise ValueError("levels must be strictly increasing")


def dot(first: Vector3, second: Vector3) -> float:
    return sum(a * b for a, b in zip(first, second, strict=True))


def add(first: Vector3, second: Vector3) -> Vector3:
    return first[0] + second[0], first[1] + second[1], first[2] + second[2]


def subtract(first: Vector3, second: Vector3) -> Vector3:
    return first[0] - second[0], first[1] - second[1], first[2] - second[2]


def scale(value: float, vector: Vector3) -> Vector3:
    return value * vector[0], value * vector[1], value * vector[2]


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


@frozen
class RoundCircle:
    """``normal`` orients increasing ``point(parameter)`` by the right-hand rule."""

    center: Vector3
    normal: Vector3 = field(
        validator=_unit_vector("a circle needs a positive radius and unit normal")
    )
    radius: float = field(
        validator=number_range(
            minimum_exclusive=0.0,
            message="a circle needs a positive radius and unit normal",
        )
    )

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


type CoreCurve = RoundCircle


@frozen
class RoundTorus:
    core: CoreCurve
    tube_radius: float = field(
        validator=number_range(
            minimum_exclusive=0.0,
            message="the tube radius must be smaller than the core radius",
        )
    )

    def __attrs_post_init__(self) -> None:
        if self.tube_radius >= self.core.radius:
            raise ValueError("the tube radius must be smaller than the core radius")

    def implicit_value(self, point: Vector3) -> float:
        offset = subtract(point, self.core.center)
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


@frozen
class EllipticTorus:
    """``profile_angle`` rotates the two semiaxes in the radial-axial plane."""

    core: RoundCircle
    first_radius: float = field(
        validator=number_range(
            minimum_exclusive=0.0,
            message="elliptic profile semiaxes must be positive",
        )
    )
    second_radius: float = field(
        validator=number_range(
            minimum_exclusive=0.0,
            message="elliptic profile semiaxes must be positive",
        )
    )
    profile_angle: float = 0.0

    def __attrs_post_init__(self) -> None:
        if self.clearance_radius >= self.core.radius:
            raise ValueError("the elliptic profile must be smaller than the core radius")

    def implicit_value(self, point: Vector3) -> float:
        offset = subtract(point, self.core.center)
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


@frozen
class TorusFamily:
    """Generators certify pairwise disjointness; this container does not."""

    tori: tuple[TorusComponent, ...] = field(validator=nonempty("a torus family cannot be empty"))


@frozen
class TorusSliceObservation:
    """Each level renders the plane ``dot(point, height_direction) == level``."""

    family: TorusFamily
    height_direction: Vector3 = field(
        validator=_unit_vector("height direction must be a unit vector")
    )
    levels: tuple[float, ...] = field(validator=_strictly_increasing)
