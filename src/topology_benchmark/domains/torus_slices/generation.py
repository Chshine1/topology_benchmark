"""Seeded construction of separated unlinks, Hopf links, and short link chains."""

import math
from random import Random

from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.domains.torus_slices.analysis import TorusFamilyAnalyzer
from topology_benchmark.domains.torus_slices.models import (
    RoundCircle,
    RoundTorus,
    TorusFamily,
    TorusSliceObservation,
    Vector3,
    unit,
)


class RandomTorusSliceGenerator:
    def generate(
        self,
        request: GenerationRequest,
        rng: Random,
        *,
        count: int | None = None,
        linked: bool | None = None,
    ) -> TorusSliceObservation:
        if count is None:
            maximum = 2 if request.difficulty <= 3 else 3 if request.difficulty <= 7 else 4
            count = rng.randint(1, maximum)
        if not 1 <= count <= 4:
            raise ValueError("generated families support one through four tori")
        linked = count >= 2 and (rng.random() < 0.58 if linked is None else linked)
        major = rng.uniform(1.65, 2.15)
        tube = rng.uniform(0.16, 0.23)
        cores = self._linked_chain(count, major) if linked else self._unlink(count, major)
        angle = rng.uniform(-0.65, 0.65)
        tilt = rng.uniform(-0.38, 0.38)
        translation = (rng.uniform(-0.4, 0.4), rng.uniform(-0.35, 0.35), rng.uniform(-0.3, 0.3))
        tori = tuple(
            RoundTorus(
                RoundCircle(
                    self._transform(circle.center, angle, tilt, translation),
                    unit(self._rotate(circle.normal, angle, tilt)),
                    circle.radius,
                ),
                tube,
            )
            for circle in cores
        )
        family = TorusFamily(tori)
        if not TorusFamilyAnalyzer.certify_disjoint(family):
            raise RuntimeError("constructed torus tubes were not certified disjoint")
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
    def _linked_chain(count: int, radius: float) -> tuple[RoundCircle, ...]:
        circles: list[RoundCircle] = []
        for index in range(0, count, 2):
            offset = 6 * radius * (index // 2)
            circles.append(RoundCircle((offset, 0.0, 0.0), (0.0, 0.0, 1.0), radius))
            if index + 1 < count:
                circles.append(RoundCircle((offset + radius, 0.0, 0.0), (0.0, 1.0, 0.0), radius))
        return tuple(circles)

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
            normal_projection = sum(
                a * b for a, b in zip(torus.core.normal, direction, strict=True)
            )
            core_extent = torus.core.radius * math.sqrt(max(0.0, 1 - normal_projection**2))
            bounds.append(
                (
                    center - core_extent - torus.tube_radius,
                    center + core_extent + torus.tube_radius,
                )
            )
        return min(low for low, _ in bounds), max(high for _, high in bounds)
