"""Certified geometric and linking calculations for round core circles."""

import math

from topology_benchmark.domains.torus_slices.models import (
    RoundCircle,
    TorusFamily,
    Vector3,
    add,
    circle_basis,
    dot,
    scale,
)


class TorusFamilyAnalyzer:
    """Analyze core-circle topology without using the rendered level sets."""

    @staticmethod
    def linking_number(first: RoundCircle, second: RoundCircle) -> int:
        """Compute linking as the intersection number with the first circle's disk."""
        basis_a, basis_b = circle_basis(second.normal)
        center_offset: Vector3 = tuple(
            a - b for a, b in zip(second.center, first.center, strict=True)
        )  # type: ignore[assignment]
        constant = dot(center_offset, first.normal)
        cosine = second.radius * dot(basis_a, first.normal)
        sine = second.radius * dot(basis_b, first.normal)
        amplitude = math.hypot(cosine, sine)
        if amplitude <= 1e-10:
            return 0
        ratio = -constant / amplitude
        if abs(ratio) >= 1 - 1e-9:
            return 0
        phase = math.atan2(sine, cosine)
        angle = math.acos(max(-1.0, min(1.0, ratio)))
        total = 0
        for parameter in (phase + angle, phase - angle):
            point = second.point(parameter)
            displacement: Vector3 = tuple(a - b for a, b in zip(point, first.center, strict=True))  # type: ignore[assignment]
            in_plane = add(displacement, scale(-dot(displacement, first.normal), first.normal))
            if dot(in_plane, in_plane) >= first.radius**2 - 1e-8:
                continue
            tangent = add(
                scale(-second.radius * math.sin(parameter), basis_a),
                scale(second.radius * math.cos(parameter), basis_b),
            )
            crossing = dot(tangent, first.normal)
            total += 1 if crossing > 0 else -1
        return total

    def linked_pairs(self, family: TorusFamily) -> tuple[tuple[int, int], ...]:
        return tuple(
            (first, second)
            for first in range(len(family.tori))
            for second in range(first + 1, len(family.tori))
            if self.linking_number(family.tori[first].core, family.tori[second].core)
        )

    @staticmethod
    def certify_disjoint(family: TorusFamily, *, samples: int = 180) -> bool:
        """Prove separation using a sampled upper estimate and a Lipschitz error bound."""
        for first_index, first in enumerate(family.tori):
            for second in family.tori[first_index + 1 :]:
                first_points = tuple(
                    first.core.point(2 * math.pi * index / samples) for index in range(samples)
                )
                second_points = tuple(
                    second.core.point(2 * math.pi * index / samples) for index in range(samples)
                )
                sampled = min(
                    math.dist(first_point, second_point)
                    for first_point in first_points
                    for second_point in second_points
                )
                error = math.pi * (first.core.radius + second.core.radius) / samples
                if sampled - error <= first.tube_radius + second.tube_radius:
                    return False
        return True
