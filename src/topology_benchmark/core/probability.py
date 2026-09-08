"""Composable, reproducible probability primitives for generation pipelines."""

import hashlib
import json
import math
from dataclasses import dataclass
from itertools import pairwise
from random import Random
from typing import Protocol


class Distribution[T](Protocol):
    def sample(self, rng: Random) -> T: ...


@dataclass(frozen=True, slots=True)
class WeightedValue[T]:
    value: T
    weight: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.weight) or self.weight < 0:
            raise ValueError("distribution weights must be finite and nonnegative")


@dataclass(frozen=True, slots=True)
class FiniteDistribution[T]:
    values: tuple[WeightedValue[T], ...]

    def __post_init__(self) -> None:
        if not self.values or not any(item.weight > 0 for item in self.values):
            raise ValueError("a finite distribution needs positive total weight")

    def sample(self, rng: Random) -> T:
        threshold = rng.random() * sum(item.weight for item in self.values)
        cumulative = 0.0
        for item in self.values:
            cumulative += item.weight
            if threshold < cumulative:
                return item.value
        return self.values[-1].value


@dataclass(frozen=True, slots=True)
class BernoulliDistribution:
    probability: float

    def __post_init__(self) -> None:
        if not 0 <= self.probability <= 1:
            raise ValueError("a probability must lie between zero and one")

    def sample(self, rng: Random) -> bool:
        return rng.random() < self.probability


@dataclass(frozen=True, slots=True)
class TruncatedGeometricDistribution:
    minimum: int
    maximum: int
    continuation_probability: float

    def __post_init__(self) -> None:
        if self.minimum < 0 or self.maximum < self.minimum:
            raise ValueError("invalid truncated geometric bounds")
        if not 0 <= self.continuation_probability <= 1:
            raise ValueError("a continuation probability must lie between zero and one")

    def sample(self, rng: Random) -> int:
        value = self.minimum
        while value < self.maximum and rng.random() < self.continuation_probability:
            value += 1
        return value


@dataclass(frozen=True, slots=True)
class SamplingEvent:
    name: str
    value: str
    noise: bool = False


class SamplingSession:
    """Named random streams stable against unrelated pipeline changes."""

    def __init__(self, seed: int, profile_version: str) -> None:
        self.seed = seed
        self.profile_version = profile_version
        self._events: list[SamplingEvent] = []

    def rng(self, namespace: str) -> Random:
        material = f"{self.profile_version}\0{self.seed}\0{namespace}".encode()
        digest = hashlib.blake2b(material, digest_size=16).digest()
        return Random(int.from_bytes(digest, "big"))

    def sample[T](self, namespace: str, distribution: Distribution[T], *, noise: bool = False) -> T:
        value = distribution.sample(self.rng(namespace))
        self._events.append(SamplingEvent(namespace, _trace_value(value), noise and bool(value)))
        return value

    def note(self, namespace: str, value: object, *, noise: bool = False) -> None:
        self._events.append(SamplingEvent(namespace, _trace_value(value), noise))

    @property
    def events(self) -> tuple[SamplingEvent, ...]:
        return tuple(self._events)

    def trace_json(self) -> str:
        return json.dumps(
            [
                {"name": event.name, "value": event.value, "noise": event.noise}
                for event in self._events
            ],
            separators=(",", ":"),
        )


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


def _trace_value(value: object) -> str:
    raw = getattr(value, "value", value)
    return str(raw)
