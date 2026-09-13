import hashlib
import math
from collections.abc import Callable
from itertools import pairwise
from random import Random
from typing import Protocol, override

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

    @override
    def sample(self, rng: Random) -> T:
        threshold = rng.random() * sum(item.weight for item in self.values)
        cumulative = 0.0
        for item in self.values:
            cumulative += item.weight
            if threshold < cumulative:
                return item.value
        return self.values[-1].value

    @property
    def total_weight(self) -> float:
        return sum(item.weight for item in self.values)

    def probability(self, predicate: Callable[[T], bool]) -> float:
        """Return the exact probability of a predicate on this finite support."""

        matching = sum(item.weight for item in self.values if predicate(item.value))
        return matching / self.total_weight

    def expectation(self, observable: Callable[[T], float]) -> float:
        """Return the exact expectation of a numeric observable."""

        weighted_total = sum(item.weight * observable(item.value) for item in self.values)
        if not math.isfinite(weighted_total):
            raise ValueError("a finite-distribution expectation must be finite")
        return weighted_total / self.total_weight

    def map[ResultT](self, transform: Callable[[T], ResultT]) -> FiniteDistribution[ResultT]:
        """Compute the exact pushforward, coalescing equal resulting values."""

        pushed: list[WeightedValue[ResultT]] = []
        for item in self.values:
            result = transform(item.value)
            for index, existing in enumerate(pushed):
                if existing.value == result:
                    pushed[index] = WeightedValue(result, existing.weight + item.weight)
                    break
            else:
                pushed.append(WeightedValue(result, item.weight))
        return FiniteDistribution(tuple(pushed))

    def bind[ResultT](
        self,
        conditional: Callable[[T], FiniteDistribution[ResultT]],
    ) -> FiniteDistribution[ResultT]:
        """Compute an exact dependent composition of finite distributions."""

        joint: list[WeightedValue[ResultT]] = []
        for outer in self.values:
            if outer.weight == 0:
                continue
            inner_distribution = conditional(outer.value)
            for inner in inner_distribution.values:
                if inner.weight == 0:
                    continue
                joint.append(
                    WeightedValue(
                        inner.value,
                        outer.weight * inner.weight / inner_distribution.total_weight,
                    )
                )
        return FiniteDistribution(tuple(joint)).map(lambda value: value)

    def condition(self, predicate: Callable[[T], bool]) -> FiniteDistribution[T]:
        """Return the exact conditional law on a nonempty event."""

        selected = tuple(item for item in self.values if predicate(item.value))
        if not selected or not any(item.weight for item in selected):
            raise ValueError("cannot condition on an event with zero probability")
        return FiniteDistribution(selected)


@frozen
class BernoulliDistribution(Distribution[bool]):
    probability: float = field(
        validator=number_range(
            minimum=0.0,
            maximum=1.0,
            message="a probability must lie between zero and one",
        )
    )

    @override
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

    @override
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
