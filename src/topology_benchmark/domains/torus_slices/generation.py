import math
from dataclasses import dataclass
from random import Random
from typing import Literal, override

from topology_benchmark.core.errors import GenerationExhaustedError
from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.domains.torus_slices.analysis import TorusFamilyAnalyzer
from topology_benchmark.domains.torus_slices.models import (
    EllipticTorus,
    RoundCircle,
    TorusFamily,
    TorusSliceObservation,
    Vector3,
    add,
    cross,
    dot,
    scale,
    unit,
)
from topology_benchmark.domains.torus_slices.ports import TorusSliceGenerator


@dataclass(frozen=True, slots=True)
class TorusGenerationSpec:
    count: int
    linked: bool
    link_pattern: Literal["pairs", "chain", "complete"]

    def __post_init__(self) -> None:
        if not 1 <= self.count <= 4:
            raise ValueError("generated families support one through four tori")
        if self.linked and self.count < 2:
            raise ValueError("a linked family needs at least two tori")


class RandomTorusSliceGenerator(TorusSliceGenerator):
    def __init__(self, analyzer: TorusFamilyAnalyzer) -> None:
        self._analyzer = analyzer

    @override
    def generate(
        self,
        request: GenerationRequest,
        rng: Random,
        spec: TorusGenerationSpec,
    ) -> TorusSliceObservation:
        count = spec.count
        linked = spec.linked
        major = rng.uniform(1.65, 2.15)
        tube = rng.uniform(0.16, 0.23)
        pattern = spec.link_pattern
        if linked:
            if pattern == "complete":
                cores = self._complete_hopf_link(count, major, rng)
            elif pattern == "chain":
                cores = self._connected_chain(count, major)
            else:
                cores = self._linked_pairs(count, major)
        else:
            cores = self._unlink(count, major)
        angle = rng.uniform(-0.65, 0.65)
        tilt = rng.uniform(-0.38, 0.38)
        translation = (rng.uniform(-0.4, 0.4), rng.uniform(-0.35, 0.35), rng.uniform(-0.3, 0.3))
        if linked and pattern == "complete":
            expected_links = count * (count - 1) // 2
        elif linked and pattern == "chain":
            expected_links = count - 1
        else:
            expected_links = count // 2 if linked else 0
        family = self._elliptic_family(cores, angle, tilt, translation, tube, expected_links, rng)
        direction: Vector3 = (0.0, 0.0, 1.0)
        low, high = self._height_bounds(family, direction)
        level_count = 5 + min(4, request.difficulty // 2)
        padding = 0.04 * (high - low)
        levels = tuple(
            low - padding + (high - low + 2 * padding) * index / (level_count - 1)
            for index in range(level_count)
        )
        return TorusSliceObservation(family, direction, levels)

    @staticmethod
    def _linked_pairs(count: int, radius: float) -> tuple[RoundCircle, ...]:
        circles: list[RoundCircle] = []
        for index in range(0, count, 2):
            offset = 6 * radius * (index // 2)
            circles.append(RoundCircle((offset, 0.0, 0.0), (0.0, 0.0, 1.0), radius))
            if index + 1 < count:
                circles.append(RoundCircle((offset + radius, 0.0, 0.0), (0.0, 1.0, 0.0), radius))
        return tuple(circles)

    @staticmethod
    def _connected_chain(count: int, radius: float) -> tuple[RoundCircle, ...]:
        """Alternate horizontal and vertical rings so each consecutive pair is Hopf-linked."""
        centers = [0.0]
        for index in range(1, count):
            centers.append(centers[-1] + (1.0 if index % 2 else 1.35) * radius)
        return tuple(
            RoundCircle(
                (center, 0.0, 0.0),
                (0.0, 0.0, 1.0) if index % 2 == 0 else (0.0, 1.0, 0.0),
                radius,
            )
            for index, center in enumerate(centers)
        )

    @classmethod
    def _complete_hopf_link(
        cls, count: int, target_radius: float, rng: Random
    ) -> tuple[RoundCircle, ...]:
        """Return stereographic Hopf fibers, every pair of which has linking number one."""
        if count < 2:
            return (RoundCircle((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), target_radius),)
        base_etas = (0.28, 0.53, 0.78, 1.01)
        base_phases = (0.0, 1.65, 3.35, 5.0)
        circles = tuple(
            cls._hopf_fiber_circle(
                eta + rng.uniform(-0.035, 0.035),
                phase + rng.uniform(-0.16, 0.16),
            )
            for eta, phase in zip(base_etas[:count], base_phases[:count], strict=True)
        )
        mean_radius = sum(circle.radius for circle in circles) / count
        factor = target_radius / mean_radius
        return tuple(
            RoundCircle(scale(factor, circle.center), circle.normal, factor * circle.radius)
            for circle in circles
        )

    @classmethod
    def _hopf_fiber_circle(cls, eta: float, phase: float) -> RoundCircle:
        points = tuple(
            cls._stereographic_hopf_point(eta, phase, 2 * math.pi * index / 3) for index in range(3)
        )
        first: Vector3 = tuple(  # type: ignore[assignment]
            b - a for a, b in zip(points[0], points[1], strict=True)
        )
        second: Vector3 = tuple(  # type: ignore[assignment]
            b - a for a, b in zip(points[0], points[2], strict=True)
        )
        perpendicular = cross(first, second)
        denominator = 2 * dot(perpendicular, perpendicular)
        center = add(
            points[0],
            scale(
                1 / denominator,
                add(
                    scale(dot(first, first), cross(second, perpendicular)),
                    scale(dot(second, second), cross(perpendicular, first)),
                ),
            ),
        )
        return RoundCircle(center, unit(perpendicular), math.dist(center, points[0]))

    @staticmethod
    def _stereographic_hopf_point(eta: float, phase: float, parameter: float) -> Vector3:
        cosine, sine = math.cos(eta), math.sin(eta)
        denominator = 1 - sine * math.sin(parameter + phase)
        return (
            cosine * math.cos(parameter) / denominator,
            cosine * math.sin(parameter) / denominator,
            sine * math.cos(parameter + phase) / denominator,
        )

    def _elliptic_family(
        self,
        cores: tuple[RoundCircle, ...],
        angle: float,
        tilt: float,
        translation: Vector3,
        tube: float,
        expected_links: int,
        rng: Random,
    ) -> TorusFamily:
        for _ in range(32):
            tori = tuple(
                EllipticTorus(
                    RoundCircle(
                        self._transform(circle.center, angle, tilt, translation),
                        unit(self._rotate(circle.normal, angle, tilt)),
                        circle.radius,
                    ),
                    tube * rng.uniform(0.72, 1.28),
                    tube * rng.uniform(0.72, 1.28),
                    rng.uniform(0.0, math.pi),
                )
                for circle in cores
            )
            family = TorusFamily(tori)
            if len(self._analyzer.linked_pairs(family)) == expected_links and (
                self._analyzer.certify_disjoint(family)
            ):
                return family
        raise GenerationExhaustedError(
            "torus-slices", "certify a disjoint elliptic realization of the link", 32
        )

    @staticmethod
    def _unlink(count: int, radius: float) -> tuple[RoundCircle, ...]:
        spacing = 2.8 * radius
        origin = -spacing * (count - 1) / 2
        return tuple(
            RoundCircle(
                (origin + spacing * index, 0.0, 0.18 * (-1) ** index),
                (0.0, 0.0, 1.0),
                radius,
            )
            for index in range(count)
        )

    @staticmethod
    def _rotate(point: Vector3, angle: float, tilt: float) -> Vector3:
        x, y, z = point
        x, y = math.cos(angle) * x - math.sin(angle) * y, math.sin(angle) * x + math.cos(angle) * y
        y, z = math.cos(tilt) * y - math.sin(tilt) * z, math.sin(tilt) * y + math.cos(tilt) * z
        return x, y, z

    @classmethod
    def _transform(cls, point: Vector3, angle: float, tilt: float, translation: Vector3) -> Vector3:
        return tuple(
            value + shift
            for value, shift in zip(cls._rotate(point, angle, tilt), translation, strict=True)
        )  # type: ignore[return-value]

    @staticmethod
    def _height_bounds(family: TorusFamily, direction: Vector3) -> tuple[float, float]:
        bounds = []
        for torus in family.tori:
            center = sum(a * b for a, b in zip(torus.core.center, direction, strict=True))
            major, minor = torus.core.basis()
            core_extent = math.hypot(
                torus.core.radius * sum(a * b for a, b in zip(major, direction, strict=True)),
                torus.core.radius * sum(a * b for a, b in zip(minor, direction, strict=True)),
            )
            bounds.append(
                (
                    center - core_extent - torus.clearance_radius,
                    center + core_extent + torus.clearance_radius,
                )
            )
        return min(low for low, _ in bounds), max(high for _, high in bounds)
