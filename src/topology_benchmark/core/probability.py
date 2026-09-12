import hashlib
from itertools import pairwise
from random import Random
from typing import Protocol

from attrs import field, frozen

from topology_benchmark.core.validation import any_member, number_range


class Distribution[T](Protocol):
    def sample(self, rng: Random) -> T: ...


@frozen
class WeightedValue[T]:
    value: T
    weight: float = field(
        validator=number_range(
            minimum=0.0,
            finite=True,
            message="distribution weights must be finite and nonnegative",
        )
    )


def _has_positive_weight[T](item: WeightedValue[T]) -> bool:
    return item.weight > 0


@frozen
class FiniteDistribution[T](Distribution[T]):
    values: tuple[WeightedValue[T], ...] = field(
        validator=any_member(
            _has_positive_weight,
            message="a finite distribution needs positive total weight",
        )
    )

    def sample(self, rng: Random) -> T:
        threshold = rng.random() * sum(item.weight for item in self.values)
        cumulative = 0.0
        for item in self.values:
            cumulative += item.weight
            if threshold < cumulative:
                return item.value
        return self.values[-1].value


@frozen
class BernoulliDistribution(Distribution[bool]):
    probability: float = field(
        validator=number_range(
            minimum=0.0,
            maximum=1.0,
            message="a probability must lie between zero and one",
        )
    )

    def sample(self, rng: Random) -> bool:
        return rng.random() < self.probability


@frozen
class TruncatedGeometricDistribution(Distribution[int]):
    minimum: int = field(
        validator=number_range(
            minimum=0,
            message="invalid truncated geometric bounds",
        )
    )
    maximum: int
    continuation_probability: float = field(
        validator=number_range(
            minimum=0.0,
            maximum=1.0,
            message="a continuation probability must lie between zero and one",
        )
    )

    def __attrs_post_init__(self) -> None:
        if self.maximum < self.minimum:
            raise ValueError("invalid truncated geometric bounds")

    def sample(self, rng: Random) -> int:
        value = self.minimum
        while value < self.maximum and rng.random() < self.continuation_probability:
            value += 1
        return value


class SamplingSession:
    """Each namespace gets an independent RNG derived from the profile and seed."""

    def __init__(self, seed: int, profile_version: str) -> None:
        self.seed = seed
        self.profile_version = profile_version

    def rng(self, namespace: str) -> Random:
        material = f"{self.profile_version}\0{self.seed}\0{namespace}".encode()
        digest = hashlib.blake2b(material, digest_size=16).digest()
        return Random(int.from_bytes(digest, "big"))

    def sample[T](self, namespace: str, distribution: Distribution[T]) -> T:
        return distribution.sample(self.rng(namespace))


def interpolate_anchors(anchors: tuple[tuple[int, float], ...], difficulty: int) -> float:
    if not anchors:
        raise ValueError("an interpolated profile needs anchors")
    ordered = tuple(sorted(anchors))
    if difficulty <= ordered[0][0]:
        return ordered[0][1]
    if difficulty >= ordered[-1][0]:
        return ordered[-1][1]
    for (left_level, left), (right_level, right) in pairwise(ordered):
        if left_level <= difficulty <= right_level:
            fraction = (difficulty - left_level) / (right_level - left_level)
            return left + fraction * (right - left)
    raise AssertionError("difficulty was not bracketed")


def blended_weight(aligned: float, baseline: float, noise_probability: float) -> float:
    if min(aligned, baseline) < 0 or not 0 <= noise_probability <= 1:
        raise ValueError("weights must be nonnegative and noise must be a probability")
    return (1 - noise_probability) * aligned + noise_probability * baseline
